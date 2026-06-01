# Phase 7: Pydantic CLI Generator - Research

**Researched:** 2026-06-01
**Domain:** Python codegen (Pydantic BaseModel emitter), CLI framework (typer), fnmatch model selection
**Confidence:** HIGH — all claims verified against live project env or official docs

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 (Pydantic replaces TypedDict — breaking change):** The existing `CodeGenerator` in `codegen.py` is hard-replaced by a Pydantic-model emitter. TypedDict emitter and all tests asserting TypedDict output (~36 tests across `test_codegen.py` and `test_type_mapper.py`) are deleted. `type_mapper.py` migrated to Pydantic type forms. Breaking change to v0.2.0 INTRO-03, changelog-noted at release.

**CF-01:** Generated models subclass `OdooBaseModel` from `godoo.client._pydantic_transform`. The `@model_validator` in `OdooBaseModel` applies all wire transforms (False→None for non-bool, m2o→Ref, date-strings→datetime).

**CF-02:** Each generated model carries `__odoo_model__: ClassVar[str]` set to the Odoo technical name.

**CF-03:** Selection fields emit as `Literal[...]` for static known values; `str` for dynamic (empty selection list).

**CF-04:** Boolean fields emit as plain `bool` (default `False`) — the one non-Optional exception.

**CF-05:** one2many / many2many fields → `list[int]`.

**CF-06:** `pydantic>=2.13` and `typer>=0.26` are runtime deps of `godoo-introspection` (not extras). `[project.scripts]` entry `godoo-introspect` is greenfield.

**D-03 (model selection flags):** `--models pat1,pat2,...` XOR `--all`. Exactly one must be provided; violation → clear error, non-zero exit.

**D-04 (relation degradation):** Target in generated set → `Ref[TargetClass]` with cross-import. Not in set → `Ref[int]  # <odoo.model>`. No transitive auto-inclusion.

**D-05 (credential handling):** `config_from_env()` default; `--url/--db/--user/--password` override. Password never echoed or logged.

**D-06 (command name):** CLI entrypoint `godoo-introspect generate` (subcommand `generate`). `[project.scripts]` = `godoo-introspect = "godoo.introspection.cli:app"`.

### Claude's Discretion

- Exact typer argument/option names and help strings.
- Whether `--output` defaults to `./models/` or is required (required preferred — avoids accidental overwrites).
- Output dir existence validated before connecting to Odoo (fail fast).
- Error message wording for missing credentials or unknown model patterns.

### Deferred Ideas (OUT OF SCOPE)

- Nested relational fetch (TYPED-F1)
- Typed write/create paths (TYPED-F2)
- Re-generation cadence / schema freshness / cache invalidation
- Keeping any TypedDict codegen path alive
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TYPED-01 | Developer can generate a Pydantic model package from live Odoo via `godoo-introspection` CLI | typer app/command structure (D-06), asyncio.run bridge, Introspector consumption pattern |
| TYPED-02 | Generated models reflect instance-specific schema — custom fields, Literal, Ref[Model]/list[int], no nested fetch | Pydantic field rendering, type_mapper migration table, cross-import / degradation patterns |
</phase_requirements>

---

## Summary

Phase 7 extends `godoo-introspection` by replacing the existing TypedDict `CodeGenerator` with a Pydantic emitter and adding a `godoo-introspect generate` CLI entrypoint backed by typer. All core building blocks are verified to work: Pydantic 2.13.4 (already in the project venv via `python-semantic-release`) handles `ClassVar[str]` cleanly under `from __future__ import annotations`; the `asyncio.run()` bridge is the correct pattern since typer 0.26.5 does NOT natively execute async command functions; mutually exclusive `--models`/`--all` validation is straightforward typer Option logic with `raise typer.Exit(code=1)`.

The existing codebase provides most infrastructure needed. `_model_to_classname`, `_model_to_filename`, and the `write()` loop scaffold in `codegen.py` are repurposed verbatim. `Introspector.get_schemas(names)` is consumed unchanged — the CLI layer adds the "fetch all model names from `ir.model`" RPC and the fnmatch filter on top. The type mapping migration is a clean table substitution: every `T | Literal[False]` becomes `Optional[T] = None`; `many2one` becomes `Optional[Ref[TargetClass]] = None` or `Optional[Ref[int]] = None`.

The one structural decision with implementation consequence is the typer subcommand routing: with a single `@app.command()`, typer optimizes it into a single-command app (no dispatch prefix). To honour `godoo-introspect generate --output ...`, the app must have a `@app.callback()` to engage group mode. This is verified behaviour in typer 0.26.5.

**Primary recommendation:** Replace `codegen.py` + `type_mapper.py` content in-place; add `cli.py` as a new module; delete `markers.py` and the 36 TypedDict tests; wire `[project.scripts]` in `pyproject.toml`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CLI argument parsing and validation | CLI layer (`cli.py`) | — | typer owns option/flag parsing; mutual-exclusion logic lives here |
| Credential assembly | CLI layer (`cli.py`) | `godoo.client.config` (`config_from_env`) | CLI merges env + flag overrides then delegates to `OdooClientConfig` |
| Model name enumeration (`--all` / `--models`) | CLI layer (`cli.py`) | `Introspector` (RPC) | CLI decides which names to fetch; Introspector fetches schemas for named list |
| Schema fetching | `Introspector` (`introspector.py`) | `OdooClient` (RPC) | Unchanged; CLI layer calls `get_schemas(names)` |
| Python type annotation string generation | `type_mapper.py` | — | Stateless function: `FieldSchema` → annotation string |
| Pydantic class source generation | `codegen.py` (`CodeGenerator.generate()`) | `type_mapper.py` | Renders one model file string from `ModelSchema` + in-set relation set |
| File write + barrel generation | `codegen.py` (`CodeGenerator.write()`) | — | Loop + barrel `__init__.py` logic; repurposed from TypedDict era |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.13.4 [VERIFIED: project venv / PyPI] | Base class for generated models; wire transforms in `OdooBaseModel` | Decided in Phase 6; already in venv as transitive dep of `python-semantic-release` |
| typer | 0.26.5 [VERIFIED: project venv via `uv add --dev typer`] | CLI framework for `godoo-introspect generate` | Declared in CF-06; greenfield for `godoo-introspection` package |

### Supporting (stdlib only — no new packages)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fnmatch | stdlib | Model name glob matching (`project.*` vs `project.task`) | `--models` flag pattern evaluation |
| asyncio | stdlib | `asyncio.run()` bridge between sync typer command and async Introspector | Every CLI command that calls async code |
| pathlib | stdlib | `output_dir` as `Path`; already used in existing `write()` | Output directory handling |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| typer | click directly | click is lower-level; typer provides envvar, hide_input, help wiring via type annotations — lower boilerplate for this use case |
| typer | argparse | Same as click but without the ergonomics |
| asyncio.run() bridge | `anyio.from_thread.run_sync` | Over-engineering; asyncio.run() is sufficient for a CLI that runs once per invocation |

**Installation (pyproject.toml changes):**

```toml
# In packages/godoo-introspection/pyproject.toml:
dependencies = [
    "godoo-client>=0.1.0",
    "pydantic>=2.13",
    "typer>=0.26",
]

[project.scripts]
godoo-introspect = "godoo.introspection.cli:app"
```

**Version verification:** pydantic 2.13.4 confirmed in `.venv` via `uv pip show pydantic`. [VERIFIED: project venv] typer 0.26.5 confirmed via `uv add --dev typer` then `typer.__version__`. [VERIFIED: project venv]

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pydantic | PyPI | ~7 yrs (2017) | 100M+/wk | github.com/pydantic/pydantic | [OK] | Approved |
| typer | PyPI | ~6 yrs (2019-12-20) | 10M+/wk | github.com/fastapi/typer | [OK] | Approved |

slopcheck ran and returned `[OK]` for both packages. Both are widely deployed, well-maintained, and from known authors (pydantic/tiangolo). No postinstall scripts.

**Packages removed due to [SLOP]:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
godoo-introspect generate --output ./models/ --models "project.*,res.partner"
        │
        ▼
 cli.py: generate()  [sync typer command]
        │  1. validate output_dir exists (fail-fast before network)
        │  2. assemble OdooClientConfig (env + flag overrides)
        │  3. asyncio.run(_generate_async(...))
        │
        ▼ asyncio.run()
 _generate_async()  [async core]
        │  4. OdooClient.authenticate()
        │  5. fetch all model names: client.search_read("ir.model", domain, fields=["model"])
        │  6. apply fnmatch filter (--models patterns OR pass-all for --all)
        │  7. Introspector.get_schemas(filtered_names)
        │  8. compute in-set relation set (frozenset of generated model names)
        │  9. CodeGenerator(introspector).write(schemas, output_dir, in_set=...)
        │ 10. OdooClient.aclose()
        │
        ▼
 codegen.py: CodeGenerator.write()
        │  for each schema:
        │    a. CodeGenerator.generate(schema, in_set) → source string
        │    b. write res_partner.py
        │  write __init__.py barrel
        │
        ▼
 type_mapper.py: pydantic_type_str(field, in_set)
        │  FieldSchema.ttype → "Optional[str] = None"
        │                    → "bool = False"
        │                    → "Optional[Ref[ResCountry]] = None"
        │                    → "Optional[Ref[int]] = None  # res.country"
        │                    → "list[int] = []"
        │                    → "Optional[Literal['a','b']] = None"
        │
        ▼
 Output package (e.g. ./models/):
   res_partner.py, res_country.py, ..., __init__.py
```

### Recommended Project Structure (new files in godoo-introspection)

```
packages/godoo-introspection/
├── src/godoo/introspection/
│   ├── cli.py             # NEW: typer app, generate command, asyncio.run bridge
│   ├── codegen.py         # REPLACED: Pydantic emitter (same class name, new body)
│   ├── type_mapper.py     # REPLACED: Pydantic type forms
│   ├── introspector.py    # UNCHANGED
│   ├── types.py           # UNCHANGED
│   ├── markers.py         # DELETED (TypedDict-era artifact)
│   ├── __init__.py        # UPDATED: remove FieldMeta/CodeGenerator re-exports (or update)
│   └── py.typed           # UNCHANGED
└── tests/
    ├── test_codegen.py    # REPLACED: Pydantic output assertions
    ├── test_type_mapper.py # REPLACED: Pydantic type form assertions
    ├── test_introspector.py # UPDATED: remove FieldMeta imports/tests (2 tests deleted)
    └── test_cli.py        # NEW: typer command tests via CliRunner
```

---

### Pattern 1: Pydantic model file template (exact compile-correct shape)

```python
# Source: verified via compile() + importlib in live project venv
# AUTOGENERATED by godoo-introspection - do not edit manually.
# Model: res.partner

from __future__ import annotations

from datetime import date, datetime        # only if date/datetime fields present
from typing import ClassVar, Literal, Optional  # Literal only if selection fields

from godoo.client._pydantic_transform import OdooBaseModel
from godoo.client.typed import Ref         # only if any many2one fields

from .res_country import ResCountry        # per in-set many2one relation (one per target)


class ResPartner(OdooBaseModel):
    __odoo_model__: ClassVar[str] = "res.partner"

    # id: always required (no Optional, no default)
    id: int

    # char / text / html / image / reference / serialized → Optional[str]
    name: Optional[str] = None

    # boolean → plain bool, default False (non-Optional exception per CF-04)
    active: bool = False

    # integer → Optional[int]
    sequence: Optional[int] = None

    # float / monetary → Optional[float]
    credit: Optional[float] = None

    # date → Optional[date]
    date_order: Optional[date] = None

    # datetime → Optional[datetime]
    write_date: Optional[datetime] = None

    # selection (static) → Optional[Literal[...]]
    state: Optional[Literal["draft", "posted", "cancel"]] = None

    # selection (dynamic / empty) → Optional[str]
    lang: Optional[str] = None

    # many2one (target in generated set) → Optional[Ref[TargetClass]], with cross-import above
    country_id: Optional[Ref[ResCountry]] = None

    # many2one (target NOT in generated set) → Optional[Ref[int]] with trailing comment
    company_id: Optional[Ref[int]] = None  # res.company

    # one2many / many2many → list[int] (always list, never Ref, never Optional per CF-05)
    child_ids: list[int] = []

    # json / properties → Optional[dict[str, Any]]
    # Note: needs `from typing import Any` added if json/properties present
    meta: Optional[dict[str, Any]] = None

    # unknown ttype → Optional[Any]
    raw_val: Optional[Any] = None
```

**Typing imports note:** `Literal` is only added to the `from typing import ...` line when the model has ≥1 static selection field. `Any` is only added when the model has json/properties/unknown-ttype fields. The import line is assembled dynamically per model.

**`from __future__ import annotations` + Pydantic `ClassVar[str]` compatibility:** Verified working in Pydantic 2.13.4. [VERIFIED: project venv `uv run python` test]. Issue #10345 (bare `ClassVar` without type arg) was a concern in older pydantic versions; `ClassVar[str]` (with explicit type arg) is safe. Never use bare `ClassVar` without the type argument in generated files.

**`list[int] = []` in Pydantic:** Pydantic models make defensive copies of mutable defaults per instance (unlike dataclasses), so `list[int] = []` is safe and idiomatic. [VERIFIED: project venv test].

---

### Pattern 2: typer CLI structure for `godoo-introspect generate`

```python
# Source: verified via typer.testing.CliRunner in project venv (typer 0.26.5)
# Key finding: @app.callback() is REQUIRED to engage group/subcommand mode.
# Without it, a single @app.command() becomes the root command (no subcommand dispatch).

from __future__ import annotations

import asyncio
from typing import Annotated, Optional

import typer

from godoo.introspection.codegen import CodeGenerator
from godoo.introspection.introspector import Introspector

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _callback() -> None:
    """Odoo schema introspection tools."""


@app.command()
def generate(
    output: Annotated[str, typer.Option(help="Output directory for generated model files")],
    models: Annotated[
        Optional[str],
        typer.Option(help="Comma-separated fnmatch patterns, e.g. 'project.*,res.partner'"),
    ] = None,
    all: Annotated[bool, typer.Option("--all", help="Generate all installed models")] = False,
    url: Annotated[
        Optional[str], typer.Option(envvar="ODOO_URL", help="Odoo URL")
    ] = None,
    db: Annotated[
        Optional[str], typer.Option(envvar="ODOO_DB", help="Odoo database name")
    ] = None,
    user: Annotated[
        Optional[str], typer.Option(envvar="ODOO_USER", help="Odoo username")
    ] = None,
    password: Annotated[
        Optional[str],
        typer.Option(envvar="ODOO_PASSWORD", hide_input=True, help="Odoo password"),
    ] = None,
) -> None:
    """Generate Pydantic model files from a live Odoo instance schema."""
    # 1. Validate mutual exclusion
    if models and all:
        typer.echo("Error: --models and --all are mutually exclusive.", err=True)
        raise typer.Exit(code=1)
    if not models and not all:
        typer.echo("Error: provide --models PATTERNS or --all.", err=True)
        raise typer.Exit(code=1)

    # 2. Validate output dir before network (fail fast)
    from pathlib import Path
    output_path = Path(output)
    if not output_path.is_dir():
        typer.echo(f"Error: output directory {output!r} does not exist.", err=True)
        raise typer.Exit(code=1)

    # 3. asyncio bridge (Introspector is async; typer command is sync)
    asyncio.run(_generate_async(output_path, models, all, url, db, user, password))


async def _generate_async(
    output_dir: "Path",
    models_arg: Optional[str],
    all_arg: bool,
    url_override: Optional[str],
    db_override: Optional[str],
    user_override: Optional[str],
    password_override: Optional[str],
) -> None:
    import fnmatch
    import os
    from pathlib import Path

    from godoo.client.client import OdooClient, OdooClientConfig
    from godoo.client.errors import OdooError

    # Build config: env defaults + CLI overrides
    url = url_override or os.environ.get("ODOO_URL")
    database = db_override or os.environ.get("ODOO_DB") or os.environ.get("ODOO_DATABASE")
    username = user_override or os.environ.get("ODOO_USER") or os.environ.get("ODOO_USERNAME")
    password = password_override or os.environ.get("ODOO_PASSWORD")

    missing = [k for k, v in [
        ("ODOO_URL", url), ("ODOO_DB", database), ("ODOO_USER", username), ("ODOO_PASSWORD", password)
    ] if not v]
    if missing:
        typer.echo(f"Error: missing required credentials: {', '.join(missing)}", err=True)
        raise typer.Exit(code=1)

    config = OdooClientConfig(url=url, database=database, username=username, password=password)  # type: ignore[arg-type]
    client = OdooClient(config)
    try:
        await client.authenticate()

        # Fetch all installed model names from ir.model
        domain = [] if all_arg else []  # --all: no filter (or add transient=False)
        if not all_arg:
            # transient=False to skip wizard models
            domain = [("transient", "=", False)]
        records = await client.search_read("ir.model", domain, fields=["model"])
        all_names: list[str] = [r["model"] for r in records if r.get("model")]

        # Apply fnmatch filter for --models
        if models_arg:
            patterns = [p.strip() for p in models_arg.split(",") if p.strip()]
            selected = [n for n in all_names if any(fnmatch.fnmatch(n, p) for p in patterns)]
        else:
            selected = all_names  # --all

        if not selected:
            typer.echo("Warning: no models matched the given patterns.", err=True)
            raise typer.Exit(code=1)

        introspector = Introspector(client)
        schemas = await introspector.get_schemas(selected)

        generator = CodeGenerator(introspector)
        generator.write(list(schemas.values()), output_dir)
        typer.echo(f"Generated {len(schemas)} model(s) to {output_dir}")
    finally:
        await client.aclose()
```

**Critical finding — typer async support:** Typer 0.26.5 does NOT natively execute `async def` commands. [VERIFIED: project venv `CliRunner` test — async command was registered but `coroutine 'X' was never awaited` warning confirmed]. The correct pattern is a sync `def` command that calls `asyncio.run(_async_core(...))`. [VERIFIED: project venv test — exit_code=0, output correct].

---

### Pattern 3: type_mapper.py migration — TypedDict → Pydantic type forms

The mapper signature changes: `python_type_str(field, in_set)` now also receives the set of generated model names to resolve m2o relations.

| `FieldSchema.ttype` | Old (TypedDict) | New (Pydantic) | Notes |
|---------------------|----------------|----------------|-------|
| `char`, `text`, `html`, `image`, `reference`, `serialized`, `binary` | `str \| Literal[False]` | `Optional[str] = None` | `= None` is the default expression, not part of the type string |
| `integer` | `int \| Literal[False]` | `Optional[int] = None` | |
| `float`, `monetary` | `float \| Literal[False]` | `Optional[float] = None` | |
| `boolean` | `bool` | `bool = False` | Non-Optional; `False` is the default |
| `date` | `str \| Literal[False]` | `Optional[date] = None` | Import `date` from `datetime` |
| `datetime` | `str \| Literal[False]` | `Optional[datetime] = None` | Import `datetime` from `datetime` |
| `many2one` (target in set) | `tuple[int, str] \| Literal[False]` | `Optional[Ref[TargetClass]] = None` | Cross-import + in-set check |
| `many2one` (target NOT in set) | `tuple[int, str] \| Literal[False]` | `Optional[Ref[int]] = None  # target.model` | Trailing comment |
| `one2many`, `many2many` | `list[int]` | `list[int] = []` | No Optional; empty list default |
| `selection` (static — has values) | `Literal['a','b'] \| Literal[False]` | `Optional[Literal['a','b']] = None` | `field.selection` list of `(value, label)` tuples |
| `selection` (dynamic — empty) | `str \| Literal[False]` | `Optional[str] = None` | `field.selection` is empty list |
| `json`, `properties` | `dict[str, Any] \| Literal[False]` | `Optional[dict[str, Any]] = None` | Import `Any` from `typing` |
| unknown ttype | `Any` | `Optional[Any] = None` | Log warning; import `Any` |

**New mapper signature:**

```python
# Source: derived from codegen analysis (ASSUMED - exact signature is planner discretion)
def pydantic_field_str(
    field: FieldSchema,
    in_set: frozenset[str],                    # set of generated model names
    classname_fn: Callable[[str], str],         # _model_to_classname
) -> tuple[str, str]:
    """Return (annotation_str, default_expr_str) for a Pydantic field line.

    e.g. ('Optional[str]', 'None')
         ('bool', 'False')
         ('Optional[Ref[ResCountry]]', 'None')
         ('Optional[Ref[int]]', 'None  # res.company')
         ('list[int]', '[]')
    """
```

The returned tuple is assembled as: `    {field_name}: {annotation_str} = {default_expr_str}`

The caller (`generate()` in `codegen.py`) is also responsible for collecting which imports are needed (date/datetime/Literal/Any/Ref/cross-model) by inspecting what the mapper returns.

---

### Pattern 4: cross-import and circular-import handling

**Non-circular case (A imports B):** Emit a regular import at the top of A's file:

```python
from .res_country import ResCountry
```

This is safe because `from __future__ import annotations` defers all annotation evaluation, so `Optional[Ref[ResCountry]]` is a string at class-definition time. [VERIFIED: project venv importlib roundtrip test]

**Circular case (A imports B AND B imports A):** Use `TYPE_CHECKING` guard in one of the files:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .res_partner import ResPartner
```

Odoo schemas frequently have mutual references (e.g. `res.partner` ↔ `res.company`). The codegen must detect cycles and apply `TYPE_CHECKING` guard on one side. The safe heuristic: **always use regular imports (not TYPE_CHECKING) for the model that appears first alphabetically; use TYPE_CHECKING for the model appearing second**. Because `from __future__ import annotations` is always active in generated files, the forward reference resolves correctly at class definition time regardless.

**Practical note:** In Pydantic 2.x with `from __future__ import annotations`, `TYPE_CHECKING` imports for the annotation side work without calling `model_rebuild()`. If runtime validation ever needs the forward ref resolved (e.g. for nested model construction), Pydantic's lazy rebuild handles it automatically on first model instantiation.

[VERIFIED: project venv — circular import via `TYPE_CHECKING` guard loaded without error]

---

### Pattern 5: fnmatch model selection

```python
# Source: verified via stdlib fnmatch in project venv
import fnmatch

def matches_any(model_name: str, patterns: list[str]) -> bool:
    """Return True if model_name matches any of the comma-separated fnmatch patterns."""
    return any(fnmatch.fnmatch(model_name, p) for p in patterns)

# Usage in CLI:
patterns = [p.strip() for p in models_arg.split(",") if p.strip()]
selected = [n for n in all_names if matches_any(n, patterns)]
```

`fnmatch.fnmatch` matches `*` against any characters **including dots**, so `project.*` matches `project.task` and `project.project`. [VERIFIED: project venv]

**`--all` implementation:** Query `ir.model` with domain `[("transient", "=", False)]` to skip transient models (wizard-style models that have no persistent schema), then pass all returned model names to `Introspector.get_schemas()`. [CITED: CONTEXT.md specifics section, confirmed by Introspector source inspection]

---

### Anti-Patterns to Avoid

- **`async def` typer command:** Typer 0.26.5 registers async command functions but does NOT await them — the coroutine is silently dropped. Always use a sync wrapper that calls `asyncio.run()`. [VERIFIED]
- **Bare `ClassVar` in generated files:** Use `ClassVar[str]`, never bare `ClassVar`. Bare `ClassVar` without a type argument is known to fail with `from __future__ import annotations` in some pydantic versions (issue #12151). `ClassVar[str]` is safe. [VERIFIED in 2.13.4]
- **Mutable defaults in dataclasses-style `field(default_factory=list)`:** Not needed for Pydantic — `list[int] = []` is idiomatic and Pydantic makes per-instance copies. [VERIFIED]
- **Injecting `FieldMeta` into generated Pydantic files:** `markers.py` and `FieldMeta` are TypedDict-era artifacts. Generated Pydantic files have no `Annotated` metadata — clean Pydantic field declarations only.
- **Password in help text or logs:** Use `typer.Option(hide_input=True)` on the `--password` flag and never pass the password value to `typer.echo()` or a logger. [CITED: typer docs exceptions section re `pretty_exceptions_show_locals`]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI arg parsing | Custom argparse / sys.argv | `typer` | envvar wiring, hide_input, help generation, type-safe options |
| Credential env-var reading | Manual `os.environ` in CLI | `config_from_env()` + `typer.Option(envvar=...)` | `config_from_env()` already handles prefix variants (`ODOO_DB`/`ODOO_DATABASE`); reuse it as the fallback layer |
| Pydantic wire transforms | Custom `__post_init__` per generated model | `OdooBaseModel` (from Phase 6) | False→None, m2o→Ref, date-strings all handled declaratively; not per-model |
| Model name → class name conversion | New regex | `_model_to_classname()` (existing `codegen.py:50`) | Already correct: `res.partner` → `ResPartner`, `account.move.line` → `AccountMoveLine` |
| Model name → filename conversion | New logic | `_model_to_filename()` (existing `codegen.py:55`) | Already correct: `res.partner` → `res_partner.py` |
| Output dir validation | New check | Reuse `write()` existing guard (`output_dir.is_dir()`) | T-02-05 already enforced; add the CLI pre-check at the output/credential stage |

**Key insight:** The Phase 7 implementation is mostly **substitution of existing scaffolding**, not new infrastructure. The generate-and-write loop, barrel `__init__.py`, identifier validation, and path helpers are all repurposed from the TypedDict era.

---

## Runtime State Inventory

*This is a replacement phase (TypedDict emitter → Pydantic emitter), not a rename/refactor/migration phase. No persistent stored data or OS-registered state is involved. Skip condition applies.*

- **Stored data:** None — the codegen does not store state; it reads from Odoo at invocation time and writes files.
- **Live service config:** None — no service configuration references `godoo-introspection` by name.
- **OS-registered state:** None — the `[project.scripts]` entry `godoo-introspect` is greenfield; no existing registration to update.
- **Secrets/env vars:** None changed — same `ODOO_*` env var names; no renaming.
- **Build artifacts:** After adding new runtime deps (`pydantic>=2.13`, `typer>=0.26`) to `packages/godoo-introspection/pyproject.toml`, `uv lock` and `uv sync` must regenerate `uv.lock`. The workspace lockfile already contains both packages (pydantic as transitive dep of `python-semantic-release`; typer added as dev dep during research). Adding them as production deps of `godoo-introspection` will update the lockfile — commit `uv.lock` with the `pyproject.toml` change.

---

## Common Pitfalls

### Pitfall 1: typer async command silently dropped

**What goes wrong:** `@app.command()` on an `async def` function. Typer 0.26.5 registers the coroutine but never awaits it — `RuntimeWarning: coroutine 'X' was never awaited`, all async work is skipped, exit code 0.

**Why it happens:** Typer delegates to click for execution; click calls the callback synchronously.

**How to avoid:** Always use a **sync** wrapper `def generate(...)` that calls `asyncio.run(_generate_async(...))`.

**Warning signs:** Test output is empty when it should have content; `RuntimeWarning: coroutine 'X' was never awaited` in test output.

### Pitfall 2: Single-command typer app skips subcommand dispatch

**What goes wrong:** `app = typer.Typer(); @app.command() def generate(...)`. User runs `godoo-introspect generate --output ...` and gets "No such command 'generate'" error.

**Why it happens:** When a Typer app has exactly one registered command and no callback, typer optimizes it into a single-command (root-level) app. The function IS the command; no dispatch prefix is needed.

**How to avoid:** Add `@app.callback()` (even an empty one) to force group mode. Confirmed working in typer 0.26.5 — with callback, `runner.invoke(app, ['generate', '--output', 'out'])` exits 0. [VERIFIED]

**Warning signs:** Tests show exit_code=2 for `['generate', '--option', '...']` invocations.

### Pitfall 3: Bare `ClassVar` in generated files under `from __future__ import annotations`

**What goes wrong:** `__odoo_model__: ClassVar = "res.partner"` (no `[str]`) fails in some pydantic versions with a `ForwardRef` resolution error.

**Why it happens:** Pydantic's namespace inspection treats bare `ClassVar` as a forward reference when future-annotations are active.

**How to avoid:** Always emit `ClassVar[str]` (with the explicit `str` type argument). [VERIFIED in 2.13.4 — `ClassVar[str]` passes cleanly]

**Warning signs:** `PydanticUserError: Unable to evaluate type annotation 'ClassVar'` at class definition time.

### Pitfall 4: Cross-import resolution order in barrel `__init__.py`

**What goes wrong:** The barrel `__init__.py` imports all generated classes. If model A imports model B and the barrel imports A before B is registered in `sys.modules`, a circular-import-style error can occur at barrel load time.

**Why it happens:** Python resolves relative imports lazily but the order in `__init__.py` matters when models have cross-dependencies.

**How to avoid:** Write barrel imports in **dependency order** (dependencies before dependents) OR rely on the fact that `from __future__ import annotations` defers annotation evaluation — which means the cross-imports in model files are not executed until the class body is evaluated. In practice, because the `from .res_country import ResCountry` at the TOP of `res_partner.py` IS executed at import time (not deferred), the barrel must import `ResCountry` before `ResPartner`. Sort barrel entries so models with no cross-imports come first.

**Warning signs:** `ImportError: cannot import name 'ResCountry' from partially initialized module`.

### Pitfall 5: Introspector.get_schemas() called with the full `--all` list at once

**What goes wrong:** Calling `get_schemas(all_1000_names)` in a single call issues one RPC for all 1000 `ir.model.fields` at once. This is within the existing API contract and Odoo handles it, but be aware the RPC payload can be large.

**Why it happens:** The existing Introspector batches all names into a single `search_read` call.

**How to avoid:** For Phase 7 v1, use the existing API as-is (single batch). Document that `--all` on large instances may be slow. No chunking needed for Phase 7.

**Warning signs:** Odoo `xmlrpc` timeout errors on very large instances with `--all`.

### Pitfall 6: `markers.py` deletion breaks `test_introspector.py`

**What goes wrong:** `test_introspector.py` imports `FieldMeta` from `godoo.introspection.markers` for 2 tests (`test_field_meta_hashable`, `test_field_meta_default_attrs`). Deleting `markers.py` breaks these tests.

**Why it happens:** `FieldMeta` was a TypedDict-era marker type that leaked into introspector tests.

**How to avoid:** Delete `test_field_meta_hashable` and `test_field_meta_default_attrs` from `test_introspector.py` alongside deleting `markers.py`. The Introspector itself does not use `FieldMeta` — these tests only test the FieldMeta dataclass in isolation.

---

## Code Examples

### Full generated file — minimal model (no relations)

```python
# Source: verified via compile() + importlib in project venv
# AUTOGENERATED by godoo-introspection - do not edit manually.
# Model: res.lang

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from godoo.client._pydantic_transform import OdooBaseModel


class ResLang(OdooBaseModel):
    __odoo_model__: ClassVar[str] = "res.lang"

    id: int
    name: Optional[str] = None
    active: bool = False
    direction: Optional[Literal["ltr", "rtl"]] = None
    date_format: Optional[str] = None
    decimal_point: Optional[str] = None
```

### Full generated file — model with relations

```python
# Source: verified via importlib roundtrip in project venv (cross-import test)
# AUTOGENERATED by godoo-introspection - do not edit manually.
# Model: res.partner

from __future__ import annotations

from datetime import date
from typing import ClassVar, Literal, Optional

from godoo.client._pydantic_transform import OdooBaseModel
from godoo.client.typed import Ref

from .res_country import ResCountry  # in-set relation


class ResPartner(OdooBaseModel):
    __odoo_model__: ClassVar[str] = "res.partner"

    id: int
    name: Optional[str] = None
    active: bool = False
    date: Optional[date] = None
    type: Optional[Literal["contact", "invoice", "delivery", "other", "private"]] = None
    country_id: Optional[Ref[ResCountry]] = None
    company_id: Optional[Ref[int]] = None  # res.company
    child_ids: list[int] = []
```

### test_cli.py pattern (typer CliRunner)

```python
# Source: pattern verified in project venv
from __future__ import annotations

from typer.testing import CliRunner
from godoo.introspection.cli import app  # the typer.Typer() app

runner = CliRunner()

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

### test_codegen.py pattern (Pydantic output assertions)

```python
# Source: adapted from existing test_generate_valid_python pattern in test_codegen.py
from __future__ import annotations

import importlib.util
from pathlib import Path
from godoo.introspection.codegen import CodeGenerator
from godoo.introspection.types import FieldSchema, ModelSchema

def test_generate_pydantic_compiles(tmp_path: Path) -> None:
    schema = ModelSchema(name="res.partner", fields={
        "id": FieldSchema(name="id", ttype="integer"),
        "name": FieldSchema(name="name", ttype="char"),
        "active": FieldSchema(name="active", ttype="boolean"),
    })
    gen = CodeGenerator(None)  # introspector not needed for generate()
    source = gen.generate(schema, in_set=frozenset())
    compile(source, "<test>", "exec")  # must not raise SyntaxError
    assert "OdooBaseModel" in source
    assert '__odoo_model__: ClassVar[str] = "res.partner"' in source
    assert "id: int" in source
    assert "name: Optional[str] = None" in source
    assert "active: bool = False" in source

def test_generate_pydantic_importlib(tmp_path: Path) -> None:
    # Full importlib roundtrip (same pattern as existing test_generate_get_type_hints_round_trip)
    schema = ModelSchema(name="res.partner", fields={
        "id": FieldSchema(name="id", ttype="integer"),
        "name": FieldSchema(name="name", ttype="char"),
    })
    gen = CodeGenerator(None)
    source = gen.generate(schema, in_set=frozenset())
    mod_file = tmp_path / "res_partner.py"
    mod_file.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("res_partner_test", mod_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod.ResPartner, "__odoo_model__")
    assert mod.ResPartner.__odoo_model__ == "res.partner"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `str \| Literal[False]` for nullable fields (TypedDict era) | `Optional[T] = None` (Pydantic era) | Phase 7 | OdooBaseModel `@model_validator` handles False→None; no field-level union needed |
| `tuple[int, str] \| Literal[False]` for many2one | `Optional[Ref[TargetClass]] = None` | Phase 7 | Wire transform converts `[id, "Name"]` to `Ref(id, name)` in OdooBaseModel |
| `NotRequired[Annotated[T, FieldMeta(...)]]` | Plain Pydantic field annotation | Phase 7 | FieldMeta not embedded in generated files; FieldMeta / markers.py deleted |
| TypedDict `total=False` class | `OdooBaseModel` subclass | Phase 7 | Runtime validation + transforms; schema-based dispatch |

**Deprecated/outdated (Phase 7 removal list):**

- `markers.py` + `FieldMeta` dataclass: TypedDict annotation metadata carrier, no Pydantic use case.
- `_annotated_field_meta_str()` in `codegen.py`: TypedDict FieldMeta constructor builder, deleted.
- `_FIELD_META_DEFAULTS` dict in `codegen.py`: used only by `_annotated_field_meta_str`, deleted.
- All `str | Literal[False]` / `tuple[int,str] | Literal[False]` type forms in `type_mapper.py`: replaced by `Optional[T]`.
- 36 tests in `test_codegen.py` (14) and `test_type_mapper.py` (22): TypedDict output format, deleted.
- 2 tests in `test_introspector.py` (`test_field_meta_*`): FieldMeta isolation tests, deleted alongside `markers.py`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `generate()` signature extended with `in_set: frozenset[str]` parameter for m2o resolution | Architecture Patterns / Pattern 3 | Planner must choose the exact interface; `in_set` passed from `write()` is the natural design |
| A2 | `--all` domain uses `[("transient", "=", False)]` to skip transient models | Pattern 2 (CLI) | If `transient` field is unavailable on some Odoo versions, domain fails; safe fallback is empty domain `[]` |
| A3 | Barrel `__init__.py` must be sorted in dependency order (dependencies before dependents) | Pitfall 4 | If ordering is wrong, barrel import fails; could be worked around by lazy imports in barrel |
| A4 | `markers.py` / `FieldMeta` are deleted entirely (not kept for backward compat) | State of the Art / Don't Hand-Roll | If any external consumer imports `godoo.introspection.markers.FieldMeta`, it breaks; breaking change is accepted per D-01 |

---

## Open Questions (RESOLVED)

1. **`CodeGenerator.generate()` signature extension**
   - What we know: current signature is `generate(self, schema: ModelSchema) -> str`; Pydantic emitter needs the in-set relation set to resolve Ref[TargetClass] vs Ref[int].
   - What's unclear: should `in_set` be passed per `generate()` call or stored on the `CodeGenerator` instance at construction?
   - Recommendation: store on instance — `CodeGenerator(introspector, in_set=frozenset(names))` mirrors how `write()` already loops all schemas with knowledge of the full set.
   - **RESOLVED:** `in_set` is stored on the `CodeGenerator` instance at construction (`CodeGenerator(introspector, in_set=frozenset(...))`); `generate(self, schema) -> str` takes no `in_set` argument. This is the authoritative signature.

2. **`__init__.py` barrel: remove `FieldMeta` and `CodeGenerator` or update them?**
   - What we know: current `__init__.py` exports `CodeGenerator`, `FieldMeta`, `FieldSchema`, `IntrospectionCache`, `Introspector`, `ModelSchema`.
   - What's unclear: `FieldMeta` is deleted; `CodeGenerator` stays (new implementation); the public API is a breaking change regardless.
   - Recommendation: remove `FieldMeta` from `__all__`; keep `CodeGenerator` (renamed in body, same import path). Changelog notes the removal.
   - **RESOLVED:** Remove the `FieldMeta` export; keep/repurpose `CodeGenerator` under the same import path.

3. **`--models` with zero matches**
   - What we know: user might give a pattern that matches nothing (e.g. typo).
   - What's unclear: hard error (exit 1) vs warning + empty output?
   - Recommendation: exit 1 with clear message ("no models matched pattern X"). Generating an empty package with only an `__init__.py` is confusing.
   - **RESOLVED:** Exit 1 with a clear message when no models match the given patterns.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | All code | ✓ | 3.14 (project `requires-python`) | — |
| uv | workspace, lockfile | ✓ | latest (CI uses `astral-sh/setup-uv@v6`) | — |
| pydantic | OdooBaseModel, generated files | ✓ | 2.13.4 (in `.venv`) | — |
| typer | CLI entrypoint | ✓ | 0.26.5 (added as dev dep during research) | — |
| Docker | integration tests | external | — | unit tests skip Docker requirement |

**Missing dependencies with no fallback:** none.

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (CLI tool, not a service) | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes — model name patterns, output path | fnmatch (stdlib), `Path.is_dir()` guard already in `write()` |
| V6 Cryptography | no | — |

### Known Threat Patterns for CLI code generation tool

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `--output` | Tampering | `Path.is_dir()` guard before writing; `write()` already validates. CLI should also check `output_path` is an existing dir before connecting to Odoo (fail-fast). |
| Credential leakage via `--password` in logs | Information Disclosure | `typer.Option(hide_input=True)` on `--password`; never pass password to `typer.echo()` or `logger`; `pretty_exceptions_show_locals` defaults to False in typer (protects from accidental locals dump). |
| Code injection via model field names in generated output | Tampering | Existing `field_name.isidentifier()` guard in `codegen.py:170` must be preserved in Pydantic emitter. `repr()` for string values (selection literals, model names) already safe in existing code. |
| Arbitrary file overwrite via output dir | Tampering | `write()` writes only `{stem}.py` and `__init__.py`; no shell expansion; controlled by the generator loop. |

---

## Sources

### Primary (HIGH confidence)

- Live project venv (Python 3.14, pydantic 2.13.4, typer 0.26.5) — all pattern verification tests run via `uv run python -c` and `uv run pytest`
- `packages/godoo-introspection/src/` source files — read directly (codegen.py, type_mapper.py, introspector.py, types.py, markers.py)
- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — OdooBaseModel wire-transform behaviour verified
- `packages/godoo-client/src/godoo/client/typed.py` — Ref[T] dataclass verified
- `packages/godoo-client/src/godoo/client/config.py` — config_from_env signature verified
- `.planning/phases/07-pydantic-cli-generator/07-CONTEXT.md` — locked decisions CF-01 through CF-06, D-01 through D-06

### Secondary (MEDIUM confidence)

- [Pydantic BaseModel docs](https://pydantic.dev/docs/validation/latest/concepts/models/) — ClassVar, Optional, model_fields behaviour
- [typer terminating docs](https://typer.tiangolo.com/tutorial/terminating/) — `typer.Exit(code=N)` pattern
- [typer commands docs](https://typer.tiangolo.com/tutorial/commands/) — `@app.command()` structure
- [PyPI pydantic](https://pypi.org/pypi/pydantic/json) — latest version 2.13.4, confirmed
- [PyPI typer](https://pypi.org/pypi/typer/json) — first uploaded 2019-12-20; latest in registry was 0.25.0 per PyPI JSON, but 0.26.5 is what resolved in the workspace

### Tertiary (LOW confidence)

- GitHub issue #10345 and #12151 (pydantic/pydantic) — bare `ClassVar` forward ref issues; partially relevant context but not current-version verified; `ClassVar[str]` was verified safe independently.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pydantic 2.13.4 and typer 0.26.5 confirmed in project venv; all critical patterns verified via executable tests
- Architecture: HIGH — all patterns compile-tested; cross-import roundtrip verified; typer subcommand routing verified
- Pitfalls: HIGH for items 1/2/6 (verified in venv); MEDIUM for items 3/4/5 (reasoned from source inspection)

**Research date:** 2026-06-01
**Valid until:** 2026-07-01 (pydantic and typer are stable; 30-day window is safe)
