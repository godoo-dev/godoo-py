# Phase 7: Pydantic CLI Generator - Pattern Map

**Mapped:** 2026-06-01
**Files analyzed:** 8 new/modified files
**Analogs found:** 7 / 8 (pyproject.toml `[project.scripts]` is greenfield — no existing analog)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/godoo-introspection/src/godoo/introspection/cli.py` | CLI entrypoint | request-response | `packages/godoo-client/src/godoo/client/config.py` | partial (same async-bridge + env-var credential pattern; no prior CLI in workspace) |
| `packages/godoo-introspection/src/godoo/introspection/codegen.py` | code emitter | transform | self (in-place replacement; scaffold repurposed) | exact (structural repurpose) |
| `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` | type mapper | transform | self (in-place replacement) | exact (structural repurpose) |
| `packages/godoo-introspection/src/godoo/introspection/__init__.py` | config / barrel | — | self (update re-exports) | exact |
| `packages/godoo-introspection/pyproject.toml` | packaging config | — | `packages/godoo-testcontainers/pyproject.toml` | role-match (same `[project]` structure; no `[project.scripts]` analog exists) |
| `packages/godoo-introspection/tests/test_codegen.py` | test | transform | self (in-place replacement; existing test structure repurposed) | exact |
| `packages/godoo-introspection/tests/test_type_mapper.py` | test | transform | self (in-place replacement) | exact |
| `packages/godoo-introspection/tests/test_cli.py` | test | request-response | `packages/godoo-introspection/tests/test_introspector.py` | role-match (mock fixtures + pytest-asyncio patterns reused) |

---

## Pattern Assignments

### `cli.py` (CLI entrypoint, request-response)

**Primary analog:** `packages/godoo-client/src/godoo/client/config.py`
**Secondary analog for asyncio bridge:** RESEARCH.md Pattern 2 (verified in venv)

**Imports pattern** — copy this header verbatim:
```python
# packages/godoo-client/src/godoo/client/config.py lines 1-11
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from godoo.client.errors import OdooError

if TYPE_CHECKING:
    from godoo.client.client import OdooClient, OdooClientConfig
```

For `cli.py`, swap to typer imports and add asyncio:
```python
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Annotated, Optional

import typer

from godoo.introspection.codegen import CodeGenerator
from godoo.introspection.introspector import Introspector

if TYPE_CHECKING:
    from godoo.client.client import OdooClient
```

**App/callback pattern** — required for subcommand dispatch (RESEARCH.md Pitfall 2):
```python
app = typer.Typer(no_args_is_help=True)

@app.callback()
def _callback() -> None:
    """Odoo schema introspection tools."""
```

**Credential assembly pattern** — copy from `config.py` lines 14-54, adapt for CLI override:
```python
# packages/godoo-client/src/godoo/client/config.py lines 25-41
def config_from_env(prefix: str = "ODOO") -> OdooClientConfig:
    url = os.environ.get(f"{prefix}_URL")
    database = os.environ.get(f"{prefix}_DB") or os.environ.get(f"{prefix}_DATABASE")
    username = os.environ.get(f"{prefix}_USER") or os.environ.get(f"{prefix}_USERNAME")
    password = os.environ.get(f"{prefix}_PASSWORD")

    missing: list[str] = []
    if not url:
        missing.append(f"{prefix}_URL")
    ...
    if missing:
        raise OdooError(f"Missing required environment variables: {', '.join(missing)}")
```

In `cli.py`, call `config_from_env()` as the base, then override with explicit flag values. Do NOT re-implement the env-var reading logic from scratch.

**asyncio.run bridge pattern** — sync command wrapping async core (RESEARCH.md Pattern 2, verified):
```python
@app.command()
def generate(...) -> None:
    """Generate Pydantic model files from a live Odoo instance schema."""
    # sync body: validate early, then delegate
    asyncio.run(_generate_async(output_path, ...))

async def _generate_async(...) -> None:
    # all async work here — authenticate, search_read, Introspector, CodeGenerator
    ...
```

**Mutual-exclusion + fail-fast validation** (from RESEARCH.md Pattern 2):
```python
if models and all:
    typer.echo("Error: --models and --all are mutually exclusive.", err=True)
    raise typer.Exit(code=1)
if not models and not all:
    typer.echo("Error: provide --models PATTERNS or --all.", err=True)
    raise typer.Exit(code=1)
# validate output dir BEFORE opening network connection
output_path = Path(output)
if not output_path.is_dir():
    typer.echo(f"Error: output directory {output!r} does not exist.", err=True)
    raise typer.Exit(code=1)
```

**Password option — hide_input=True** (security, RESEARCH.md Anti-Patterns):
```python
password: Annotated[
    Optional[str],
    typer.Option(envvar="ODOO_PASSWORD", hide_input=True, help="Odoo password"),
] = None
```

**fnmatch filter pattern** (RESEARCH.md Pattern 5, stdlib only):
```python
import fnmatch
patterns = [p.strip() for p in models_arg.split(",") if p.strip()]
selected = [n for n in all_names if any(fnmatch.fnmatch(n, p) for p in patterns)]
```

**Logger pattern** — copy from `codegen.py` line 16:
```python
# packages/godoo-introspection/src/godoo/introspection/codegen.py line 16
logger = logging.getLogger("godoo_introspection.codegen")
# → in cli.py:
logger = logging.getLogger("godoo_introspection.cli")
```

---

### `codegen.py` (code emitter, transform — in-place replacement)

**Analog:** self (the existing file; scaffold is repurposed, TypedDict body is replaced)

**Preserve verbatim** (lines 50-57):
```python
# packages/godoo-introspection/src/godoo/introspection/codegen.py lines 50-57
def _model_to_classname(model: str) -> str:
    """Convert 'res.partner' → 'ResPartner', 'account.move.line' → 'AccountMoveLine'."""
    return "".join(part.capitalize() for part in model.replace(".", "_").split("_"))


def _model_to_filename(model: str) -> str:
    """Convert 'res.partner' → 'res_partner.py'."""
    return model.replace(".", "_") + ".py"
```

**Preserve verbatim — `write()` loop structure** (lines 185-220):
```python
# packages/godoo-introspection/src/godoo/introspection/codegen.py lines 185-220
def write(self, schemas: list[ModelSchema], output_dir: Path) -> None:
    # Security: validate output_dir before any write (T-02-05)
    if not output_dir.is_dir():
        raise ValueError(f"output_dir {output_dir!r} is not a directory")

    class_names: list[tuple[str, str]] = []  # (stem, class_name)

    for schema in schemas:
        source = self.generate(schema)          # <-- call signature changes: add in_set
        filename = _model_to_filename(schema.name)
        stem = filename[:-3]
        class_name = _model_to_classname(schema.name)
        (output_dir / filename).write_text(source, encoding="utf-8")
        class_names.append((stem, class_name))
        logger.debug("Wrote %s → %s", schema.name, filename)

    # barrel __init__.py — structure preserved, sort order may change (see Pitfall 4)
    barrel_lines = [
        "# AUTOGENERATED by godoo-introspection — do not edit manually.",
        "",
    ]
    for stem, class_name in class_names:
        barrel_lines.append(f"from .{stem} import {class_name}")
    barrel_lines.append("")
    barrel_lines.append("__all__ = [")
    for _, class_name in class_names:
        barrel_lines.append(f'    "{class_name}",')
    barrel_lines.append("]")
    barrel_lines.append("")

    (output_dir / "__init__.py").write_text("\n".join(barrel_lines), encoding="utf-8")
    logger.debug("Wrote __init__.py barrel with %d exports", len(class_names))
```

**Preserve — identifier validation guard** (line 170-172):
```python
# packages/godoo-introspection/src/godoo/introspection/codegen.py lines 170-172
if not field_name.isidentifier():
    logger.warning("Field name %r is not a valid Python identifier — skipping", field_name)
    continue
```

**DELETE entirely:**
- `_FIELD_META_DEFAULTS` dict (lines 23-42)
- `_annotated_field_meta_str()` function (lines 60-123)
- `from godoo.introspection.type_mapper import python_type_str` → replace with new mapper import
- TypedDict `generate()` body (lines 144-183) → replace with Pydantic emitter body

**New `generate()` signature** (must store `in_set` on instance per RESEARCH.md open question 1):
```python
class CodeGenerator:
    def __init__(self, introspector: Introspector, in_set: frozenset[str] = frozenset()) -> None:
        self._introspector = introspector
        self._in_set = in_set

    def generate(self, schema: ModelSchema) -> str:
        """Return a valid Python Pydantic module string for one model."""
        ...
```

**New `generate()` output template** (RESEARCH.md Pattern 1, verified compile-correct):
```python
# Header — always present
"# AUTOGENERATED by godoo-introspection - do not edit manually.",
f"# Model: {schema.name}",
"",
"from __future__ import annotations",
"",
# stdlib imports — assembled dynamically per model
# e.g. "from datetime import date, datetime"  (only if date/datetime fields present)
# typing imports — assembled dynamically
# e.g. "from typing import ClassVar, Literal, Optional"
# godoo imports
"from godoo.client._pydantic_transform import OdooBaseModel",
# "from godoo.client.typed import Ref"  — only if any many2one fields
# cross-imports — one per in-set many2one target
# e.g. "from .res_country import ResCountry"  (or TYPE_CHECKING guard for circular)
"",
"",
f"class {class_name}(OdooBaseModel):",
f'    __odoo_model__: ClassVar[str] = "{schema.name}"',
"",
"    id: int",
# ... per-field lines from type_mapper ...
```

**Cross-import pattern for circular relations** (RESEARCH.md Pattern 4):
```python
# Non-circular: regular import at top of file
"from .res_country import ResCountry"

# Circular (A↔B): TYPE_CHECKING guard in the alphabetically-second file
"from typing import TYPE_CHECKING"
"if TYPE_CHECKING:"
"    from .res_partner import ResPartner"
```

---

### `type_mapper.py` (type mapper, transform — in-place replacement)

**Analog:** self (existing file; function signature changes, all type-string values replaced)

**Preserve — module header, logger, TYPE_CHECKING import** (lines 1-11):
```python
# packages/godoo-introspection/src/godoo/introspection/type_mapper.py lines 1-11
"""Odoo ttype to Python type hint string mapper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from godoo.introspection.types import FieldSchema

logger = logging.getLogger("godoo_introspection.codegen")
```

**Preserve — frozenset grouping idiom** (lines 17-22), adapted for Pydantic ttypes:
```python
# Existing pattern to repurpose:
_STR_FALSE_TTYPES = frozenset({"char", "text", "html", "image", "date", "datetime", "binary", "serialized", "reference"})
# New equivalent:
_OPTIONAL_STR_TTYPES = frozenset({"char", "text", "html", "image", "binary", "serialized", "reference"})
_OPTIONAL_DATE_TTYPES = frozenset({"date"})   # or inline — separate for import tracking
_LIST_INT_TTYPES = frozenset({"one2many", "many2many"})  # preserved unchanged
```

**New function signature** — replaces `python_type_str(field: FieldSchema) -> str`:
```python
def pydantic_field_str(
    field: FieldSchema,
    in_set: frozenset[str],
    classname_fn: Callable[[str], str],
) -> tuple[str, str]:
    """Return (annotation_str, default_expr_str) for a Pydantic field line.

    Examples:
      ('Optional[str]', 'None')
      ('bool', 'False')
      ('Optional[Ref[ResCountry]]', 'None')
      ('Optional[Ref[int]]', 'None  # res.company')
      ('list[int]', '[]')
      ('Optional[Literal["draft", "posted"]]', 'None')
    """
```

**Full type-string migration table** (RESEARCH.md Pattern 3):

| `FieldSchema.ttype` | Old return | New `(annotation_str, default_expr)` |
|---------------------|-----------|--------------------------------------|
| `char`, `text`, `html`, `image`, `binary`, `serialized`, `reference` | `"str \| Literal[False]"` | `("Optional[str]", "None")` |
| `integer` | `"int \| Literal[False]"` | `("Optional[int]", "None")` |
| `float`, `monetary` | `"float \| Literal[False]"` | `("Optional[float]", "None")` |
| `boolean` | `"bool"` | `("bool", "False")` |
| `date` | `"str \| Literal[False]"` | `("Optional[date]", "None")` |
| `datetime` | `"str \| Literal[False]"` | `("Optional[datetime]", "None")` |
| `many2one` (target in `in_set`) | `"tuple[int, str] \| Literal[False]"` | `(f"Optional[Ref[{classname_fn(relation)}]]", "None")` |
| `many2one` (target NOT in `in_set`) | same | `("Optional[Ref[int]]", f"None  # {relation}")` |
| `one2many`, `many2many` | `"list[int]"` | `("list[int]", "[]")` |
| `selection` (static) | `"Literal[v1, v2] \| Literal[False]"` | `(f"Optional[Literal[{vals}]]", "None")` |
| `selection` (dynamic) | `"str \| Literal[False]"` | `("Optional[str]", "None")` |
| `json`, `properties` | `"dict[str, Any] \| Literal[False]"` | `("Optional[dict[str, Any]]", "None")` |
| unknown | `"Any"` | `("Optional[Any]", "None")` |

**Preserve — warning log for unknown ttype** (lines 72-73):
```python
# packages/godoo-introspection/src/godoo/introspection/type_mapper.py lines 72-73
logger.warning("Unknown Odoo ttype %r for field %r — falling back to Any", ttype, field.name)
```

---

### `__init__.py` (barrel, update)

**Analog:** self (lines 1-13)

**Current exports to modify:**
```python
# packages/godoo-introspection/src/godoo/introspection/__init__.py lines 1-13
from godoo.introspection.codegen import CodeGenerator
from godoo.introspection.introspector import IntrospectionCache, Introspector
from godoo.introspection.markers import FieldMeta          # DELETE this line
from godoo.introspection.types import FieldSchema, ModelSchema

__all__ = [
    "CodeGenerator",
    "FieldMeta",        # DELETE from __all__
    "FieldSchema",
    "IntrospectionCache",
    "Introspector",
    "ModelSchema",
]
```

**After change:** remove `FieldMeta` import and `__all__` entry. No other changes needed here.

---

### `pyproject.toml` (packaging config)

**Analog:** `packages/godoo-testcontainers/pyproject.toml` (same `[project]` structure; no `[project.scripts]` exists anywhere in the workspace — greenfield)

**Current `dependencies` line** (line 8):
```toml
# packages/godoo-introspection/pyproject.toml line 8
dependencies = ["godoo-client>=0.1.0"]
```

**After change:**
```toml
dependencies = [
    "godoo-client>=0.1.0",
    "pydantic>=2.13",
    "typer>=0.26",
]
```

**New `[project.scripts]` table** — greenfield, no analog in workspace. TOML convention:
```toml
[project.scripts]
godoo-introspect = "godoo.introspection.cli:app"
```

Place the `[project.scripts]` block immediately after `[project.urls]` and before `[build-system]`, following the same block order as `godoo-testcontainers/pyproject.toml`.

**Commit rule:** commit `pyproject.toml` + regenerated `uv.lock` in the same commit (lockfile-discipline).

---

### `tests/test_codegen.py` (test, transform — in-place replacement)

**Analog:** self (existing file; structure and fixture helpers are repurposed)

**Preserve — `_schema()` and `_char_field()` helper pattern** (lines 14-28):
```python
# packages/godoo-introspection/tests/test_codegen.py lines 14-28
def _schema(model_name: str = "res.partner", **fields: FieldSchema) -> ModelSchema:
    """Build a minimal ModelSchema for testing."""
    return ModelSchema(name=model_name, fields=dict(fields))

def _char_field(fname: str = "name") -> FieldSchema:
    return FieldSchema(name=fname, ttype="char")
```

**Preserve — `compile()` smoke-test pattern** (lines 76-85):
```python
# packages/godoo-introspection/tests/test_codegen.py lines 76-85
def test_generate_valid_python() -> None:
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema(...)
    result = gen.generate(schema)
    compile(result, "<string>", "exec")   # must not raise SyntaxError
```

**Preserve — importlib round-trip pattern** (lines 88-110):
```python
# packages/godoo-introspection/tests/test_codegen.py lines 88-110
def test_generate_get_type_hints_round_trip(tmp_path: Path) -> None:
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"))
    result = gen.generate(schema)
    mod_file = tmp_path / "res_partner.py"
    mod_file.write_text(result, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("res_partner_test", mod_file)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    ...
```

**Preserve — `write()` + dir-validation tests** (lines 123-155):
```python
# test_write_creates_files, test_write_creates_init, test_write_invalid_dir_raises,
# test_generate_empty_schema_pass — all structurally repurposable
```

**DELETE — TypedDict-specific assertions** (16 tests):
- `test_generate_class_name` (asserts `TypedDict, total=False`)
- `test_generate_id_required` (asserts `Required[int]`)
- `test_generate_field_notrequired` (asserts `NotRequired[`)
- `test_generate_field_meta_import` (asserts `FieldMeta` import)
- `test_generate_selection_literal` (only checks `Literal[` in old form)
- `test_generate_header` (asserts `from typing import` TypedDict form)

**New Pydantic-specific assertions to add** (from RESEARCH.md Code Examples):
```python
def test_generate_pydantic_class_name(tmp_path: Path) -> None:
    # assert "class ResPartner(OdooBaseModel):" in source

def test_generate_odoo_model_classvar(tmp_path: Path) -> None:
    # assert '__odoo_model__: ClassVar[str] = "res.partner"' in source

def test_generate_id_plain_int(tmp_path: Path) -> None:
    # assert "id: int" in source   (no Required[int], no Optional)

def test_generate_optional_char(tmp_path: Path) -> None:
    # assert "name: Optional[str] = None" in source

def test_generate_bool_non_optional(tmp_path: Path) -> None:
    # assert "active: bool = False" in source

def test_generate_no_field_meta(tmp_path: Path) -> None:
    # assert "FieldMeta" not in source
    # assert "markers" not in source
```

---

### `tests/test_type_mapper.py` (test, transform — in-place replacement)

**Analog:** self (existing file; `_field()` helper and per-ttype test pattern preserved)

**Preserve — `_field()` helper** (lines 15-17):
```python
# packages/godoo-introspection/tests/test_type_mapper.py lines 15-17
def _field(ttype: str, **kwargs: object) -> FieldSchema:
    """Build a minimal FieldSchema for testing."""
    return FieldSchema(name="f", ttype=ttype, **kwargs)  # type: ignore[arg-type]
```

**Preserve — per-ttype test structure:**
```python
def test_char() -> None:
    assert pydantic_field_str(_field("char"), frozenset(), _model_to_classname) == ("Optional[str]", "None")
```

**DELETE — all 22 old assertions** (every test asserting `str | Literal[False]`, `tuple[int, str] | Literal[False]`, `int | Literal[False]`, `float | Literal[False]`).

**New assertions to add:**

- `test_char` → `("Optional[str]", "None")`
- `test_integer` → `("Optional[int]", "None")`
- `test_float`, `test_monetary` → `("Optional[float]", "None")`
- `test_boolean_plain_bool` → `("bool", "False")`
- `test_date` → `("Optional[date]", "None")`
- `test_datetime` → `("Optional[datetime]", "None")`
- `test_many2one_in_set` → `("Optional[Ref[ResPartner]]", "None")` with `in_set=frozenset({"res.partner"})`
- `test_many2one_not_in_set` → annotation `"Optional[Ref[int]]"`, default `"None  # res.partner"`
- `test_one2many`, `test_many2many` → `("list[int]", "[]")`
- `test_selection_static` → `('Optional[Literal["draft", "done"]]', "None")`
- `test_selection_dynamic` → `("Optional[str]", "None")`
- `test_json`, `test_properties` → `("Optional[dict[str, Any]]", "None")`
- `test_unknown_ttype_returns_optional_any` → annotation contains `Optional[Any]`
- `test_unknown_ttype_logs_warning` — preserve existing caplog pattern unchanged

---

### `tests/test_cli.py` (test, request-response — NEW)

**Analog:** `packages/godoo-introspection/tests/test_introspector.py` (mock-based, respx fixture pattern)

**Runner setup pattern** (from RESEARCH.md Code Examples):
```python
# tests/test_cli.py — full header
from __future__ import annotations

from typer.testing import CliRunner
from godoo.introspection.cli import app

runner = CliRunner()
```

**Validation-only tests** (no network, no mock needed — cover mutual exclusion, dir check):
```python
# Pattern: runner.invoke + exit_code + output text assertions
def test_generate_requires_models_or_all(tmp_path) -> None:
    result = runner.invoke(app, ["generate", "--output", str(tmp_path)])
    assert result.exit_code == 1
    assert "provide --models" in result.output

def test_generate_models_and_all_mutually_exclusive(tmp_path) -> None:
    result = runner.invoke(app, ["generate", "--output", str(tmp_path),
                                  "--models", "res.*", "--all"])
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output

def test_generate_bad_output_dir() -> None:
    result = runner.invoke(app, ["generate", "--output", "/nonexistent/path", "--all"])
    assert result.exit_code == 1
    assert "does not exist" in result.output
```

**Network-mocked test pattern** — reuse `_rpc_response()` + `respx.mock` from `test_introspector.py` (lines 18-33):
```python
# packages/godoo-introspection/tests/test_introspector.py lines 18-33
def _rpc_response(result, id=1) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})

def _make_client() -> OdooClient:
    return OdooClient(OdooClientConfig(url=BASE_URL, database=DB, username="admin", password="admin"))

@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(2))
        await client.authenticate()
    yield client
    await client.aclose()
```

**Note on `test_cli.py` network tests:** Because `cli.py` calls `asyncio.run()` internally, CliRunner tests that go through the network path need `respx.mock` as context manager wrapping `runner.invoke`, or the network calls must be patched at the `OdooClient` level. Pattern from test_introspector.py line 83: `@respx.mock` decorator on async test functions applies cleanly.

---

### `tests/test_introspector.py` (partial update — DELETE 2 tests)

**Analog:** self

**DELETE** (lines 41-68 — both `FieldMeta` isolation tests):
```python
# DELETE lines 41-68:
def test_field_meta_hashable(): ...
def test_field_meta_default_attrs(): ...
```

**DELETE** the `FieldMeta` import (line 11):
```python
# DELETE:
from godoo.introspection.markers import FieldMeta
```

All other tests in this file are preserved unchanged.

---

## Shared Patterns

### `from __future__ import annotations` — every new file

**Apply to:** `cli.py`, updated `codegen.py`, updated `type_mapper.py`, `test_cli.py`, updated test files.

```python
# First line of every module (after module docstring if present)
from __future__ import annotations
```

### TYPE_CHECKING import guard — `OdooClient` in service/CLI modules

**Source:** `packages/godoo-introspection/src/godoo/introspection/codegen.py` lines 6-14
**Apply to:** `cli.py` (type-annotates `OdooClient`); `codegen.py` (already uses this; preserve)

```python
from typing import TYPE_CHECKING
...
if TYPE_CHECKING:
    from pathlib import Path
    from godoo.introspection.introspector import Introspector
    from godoo.introspection.types import FieldSchema, ModelSchema
```

### Logger-per-module pattern

**Source:** `packages/godoo-introspection/src/godoo/introspection/codegen.py` line 16
**Apply to:** `cli.py`, `codegen.py`, `type_mapper.py`

```python
logger = logging.getLogger("godoo_introspection.<module_name>")
```

### Output-dir validation before writes

**Source:** `packages/godoo-introspection/src/godoo/introspection/codegen.py` lines 188-190
**Apply to:** `codegen.py` (keep existing guard); `cli.py` (add pre-network check using same `Path.is_dir()`)

```python
if not output_dir.is_dir():
    raise ValueError(f"output_dir {output_dir!r} is not a directory")
```

### Identifier validation guard

**Source:** `packages/godoo-introspection/src/godoo/introspection/codegen.py` lines 170-172
**Apply to:** New `generate()` body in `codegen.py` — preserve this guard exactly.

```python
if not field_name.isidentifier():
    logger.warning("Field name %r is not a valid Python identifier — skipping", field_name)
    continue
```

### `repr()` for string values in generated code

**Source:** `packages/godoo-introspection/src/godoo/introspection/codegen.py` lines 67, 114
**Apply to:** `codegen.py` Pydantic emitter — model names, selection literal values, trailing comments.

```python
# Model name in ClassVar:
f'    __odoo_model__: ClassVar[str] = {schema.name!r}'
# Selection literal values:
vals = ", ".join(repr(v) for v, _ in field.selection)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pyproject.toml` `[project.scripts]` table | packaging | — | No `[project.scripts]` entry exists anywhere in the workspace (greenfield for this project). Use standard TOML: `godoo-introspect = "godoo.introspection.cli:app"`. |

---

## Deletions (files removed entirely — no replacement)

| File | Reason |
|------|--------|
| `packages/godoo-introspection/src/godoo/introspection/markers.py` | TypedDict-era `FieldMeta` marker; no Pydantic use case (D-01) |

---

## Metadata

**Analog search scope:** `packages/godoo-introspection/`, `packages/godoo-client/src/godoo/client/`
**Files read:** `codegen.py`, `type_mapper.py`, `introspector.py`, `types.py`, `markers.py`, `__init__.py`, `config.py`, `typed.py`, `_pydantic_transform.py`, all 3 test files, both pyproject.toml files
**Pattern extraction date:** 2026-06-01
