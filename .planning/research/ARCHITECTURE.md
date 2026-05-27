# Architecture Research — godoo-py v1.1

**Domain:** Python async Odoo SDK — adding typed models + browser transport to a shipped library
**Researched:** 2026-05-27
**Confidence:** HIGH — based on direct file inspection of the live codebase

---

## Existing Architecture Baseline (do not redesign)

### Namespace layout (PEP 420 implicit namespace packages)

```
packages/godoo/src/
└── godoo/                          # namespace root — NO __init__.py
    └── client/                     # dist: godoo-client
        ├── __init__.py             # barrel exports OdooClient, OdooClientConfig, errors, ...
        ├── client.py               # OdooClient facade
        ├── config.py               # config_from_env, create_client
        ├── errors.py               # OdooError hierarchy
        ├── safety/                 # SafetyContext, OperationInfo, infer_safety_level
        └── rpc/
            ├── transport.py        # JsonRpcTransport (sole httpx consumer)
            └── types.py            # OdooSessionInfo
        └── services/{name}/        # 8 domain services (quad: types/functions/service/__init__)

packages/godoo-introspection/src/
└── godoo/                          # namespace root — NO __init__.py
    └── introspection/              # dist: godoo-introspection
        ├── __init__.py             # barrel: CodeGenerator, Introspector, IntrospectionCache, ...
        ├── introspector.py         # Introspector + IntrospectionCache
        ├── codegen.py              # CodeGenerator → TypedDict module strings
        ├── type_mapper.py          # python_type_str() — 20-ttype mapper
        ├── markers.py              # FieldMeta dataclass (PEP 593 Annotated metadata)
        └── types.py                # FieldSchema, ModelSchema dataclasses

packages/godoo-testcontainers/src/
└── godoo/
    └── testcontainers/             # dist: godoo-testcontainers

packages/godoo-meta/                # dist: godoo (meta only, no code)
```

The `godoo/` directory at each `src/` root has NO `__init__.py` — that is the PEP 420 namespace
mechanism that lets all four packages contribute to the same `godoo.*` import tree.

### Key architectural constraints (hard)

- `httpx` is the ONLY runtime dep of `godoo-client`. Nothing else imports at runtime.
- `OdooClient` is imported under `TYPE_CHECKING` in all service files to prevent circular imports.
- Service classes are wired via `@cached_property` with local imports inside the property body.
- Dataclasses (not Pydantic) for all core types.
- `from __future__ import annotations` in every file.
- `mypy --strict` on all `src/` directories.

### Current state of the dir rename (Feature A)

The dist name is already `godoo-client` (confirmed in `packages/godoo/pyproject.toml:project.name`).
The **directory** is still `packages/godoo` — the rename to `packages/godoo-client` has NOT
happened yet in the filesystem, despite being listed as validated in PROJECT.md. This is the
discrepancy to close. The import namespace is already `godoo.client.*` — no user-visible change
is needed.

---

## Integration Points: New vs Modified Components

### Feature A — Dir Rename: `packages/godoo` → `packages/godoo-client`

**New components:** none.
**Modified files — complete enumeration:**

| File | Change |
|------|--------|
| `packages/godoo/` | Rename directory to `packages/godoo-client/` (git mv) |
| `packages/godoo/pyproject.toml` → `packages/godoo-client/pyproject.toml` | No content change — `[tool.hatch.build.targets.wheel] only-include = ["src/godoo/client"]` already correct; `project.name = "godoo-client"` already correct |
| `pyproject.toml` `[tool.mypy] mypy_path` line 35 | `"packages/godoo/src"` → `"packages/godoo-client/src"` |
| `pyproject.toml` `[tool.semantic_release] version_toml` line 63 | `"packages/godoo/pyproject.toml:project.version"` → `"packages/godoo-client/pyproject.toml:project.version"` |
| `.github/workflows/test.yml` line 24 | `mypy packages/godoo/src ...` → `mypy packages/godoo-client/src ...` |
| `mkdocs.yml` line 48 | `paths: [packages/godoo/src, ...]` → `paths: [packages/godoo-client/src, ...]` |
| `[tool.uv.workspace] members = ["packages/*"]` | No change — glob covers the renamed dir automatically |
| `.planning/codebase/ARCHITECTURE.md` and other `.planning/` docs | Planning-only files; update as documentation, not code |
| `CLAUDE.md` path references to `packages/godoo/src/godoo/...` | Update prose references |
| `CHANGELOG.md` | No change needed (historical paths stay accurate) |

**What does NOT change:** any Python import (`from godoo.client.client import OdooClient`, etc.) —
the import namespace is already `godoo.client.*` and the `src/godoo/client/` subtree stays
identical. No test files, no service files, no `__init__.py` files change.

**uv workspace:** `members = ["packages/*"]` uses a glob — the rename is transparent to uv.

**Hatchling wheel config:** `only-include = ["src/godoo/client"]` is relative to `sources = ["src"]`,
so it also stays correct after the directory rename.

---

### Feature B — Typed Models

#### B1: Protocol that lives in `godoo.client` (no pydantic dependency)

**New component:** `packages/godoo-client/src/godoo/client/typed.py`

This module ships in core (no pydantic import at module level) and defines:

```python
# godoo/client/typed.py
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

@runtime_checkable
class OdooModel(Protocol):
    """Protocol satisfied by every generated Pydantic model."""
    __odoo_model__: str   # class var — the technical model name e.g. "res.partner"

T = OdooModel  # convenience alias used in overloads
ModelT = TypeVar("ModelT", bound=OdooModel)
```

`runtime_checkable` makes `isinstance(x, OdooModel)` work — but dispatch uses
`hasattr(model, "__odoo_model__")` on the *class* (not instance), which never imports pydantic.
The Protocol is pure stdlib and imposes zero runtime cost on the raw path.

**Why in core:** generated model packages (`import ResPartner from mymodels.res_partner`) must
`from godoo.client.typed import OdooModel` to declare conformance. If the Protocol lived in
`godoo.introspection`, generated packages would depend on `godoo-introspection` — wrong direction.

#### B2: Dispatch placement in `client.py`

**Modified component:** `packages/godoo-client/src/godoo/client/client.py`

The `@overload` signatures sit directly on `OdooClient.read` and `OdooClient.search_read`.
The typed branch logic is extracted into a guarded helper to keep the raw path unaffected:

```python
# In client.py — imports section (TYPE_CHECKING only for ModelT)
if TYPE_CHECKING:
    from godoo.client.typed import ModelT

@overload
async def read(self, model: str, ids: int | list[int], ...) -> list[dict[str, Any]]: ...
@overload
async def read(self, model: type[ModelT], ids: int | list[int], ...) -> list[ModelT]: ...

async def read(self, model: str | type[Any], ids: int | list[int], ...) -> list[Any]:
    if hasattr(model, "__odoo_model__"):
        return await self._typed_read(model, ids, ...)  # lazy pydantic path
    id_list = [ids] if isinstance(ids, int) else ids
    ...  # existing raw path — untouched
```

`_typed_read` is a private async method on `OdooClient` that does the late import:

```python
async def _typed_read(self, model_cls: type[Any], ids: int | list[int], ...) -> list[Any]:
    from godoo.client._pydantic_transform import transform_records  # lazy import
    model_name: str = model_cls.__odoo_model__
    raw = await self._raw_read(model_name, ids, ...)
    return transform_records(model_cls, raw)
```

The `from godoo.client._pydantic_transform import transform_records` line executes only when
a model class is passed — never on `import godoo`. The raw path's hot loop is completely
untouched.

**mypy --strict typing:** The overload uses `type[ModelT]` where `ModelT` is `TypeVar(...,
bound=OdooModel)`. Because `OdooModel` is a `Protocol` with `runtime_checkable`, mypy resolves
the TypeVar correctly in both overloads. The implementation signature uses `type[Any]` to
avoid the overload conflict. The `hasattr(model, "__odoo_model__")` guard is a runtime check;
mypy needs a `TYPE_CHECKING` annotation for `ModelT` to keep the overloads strict.

#### B3: Import isolation — the `_pydantic_transform` helper

**New component:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py`

This is a private module. It is the ONLY file in `godoo-client` that imports pydantic.
It is never imported at module load time — only inside `_typed_read`.

```python
# _pydantic_transform.py
from __future__ import annotations
from typing import Any

def transform_records(model_cls: type[Any], raw: list[dict[str, Any]]) -> list[Any]:
    # pydantic import is local — never at module level
    try:
        import pydantic  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "godoo[typed] extra required: pip install godoo-client[typed]"
        ) from exc
    return [model_cls.model_validate(record) for record in raw]
```

`model_validate` is the Pydantic v2 API. The `ImportError` with a helpful message guides
users who call the typed path without installing the extra.

**Pydantic optional extra** declared in `packages/godoo-client/pyproject.toml`:

```toml
[project.optional-dependencies]
typed = ["pydantic>=2.0"]
```

Nothing else changes in the package — `dependencies = ["httpx>=0.27"]` stays as-is.

#### B4: Generated-package shape (emitted by the CLI generator)

A generated package (e.g. `myproject_models/`) has this layout:

```
myproject_models/
├── __init__.py          # barrel: from .res_partner import ResPartner, ...
├── res_partner.py       # one file per model
├── account_move.py
└── ...
```

Each model file:

```python
# AUTOGENERATED by godoo-introspection — do not edit manually.
# Model: res.partner
from __future__ import annotations
from typing import Literal
import pydantic
from godoo.client.typed import OdooModel  # Protocol conformance (structural, not base class)

class Ref(pydantic.BaseModel):
    id: int
    name: str

class ResPartner(pydantic.BaseModel):
    __odoo_model__ = "res.partner"  # class var — satisfies OdooModel Protocol

    id: int
    name: str | None = None
    active: bool = True
    parent_id: Ref | None = None    # many2one → Ref
    child_ids: list[int] = []       # one2many / many2many → list[int] (id-only, no fetch)
    # ... all fields with validators
```

Key design decisions for generated models:
- `pydantic.BaseModel` with `model_config = ConfigDict(from_attributes=False)` — input is dicts.
- Odoo's `False` wire value for unset fields is handled via a pydantic field validator
  (`@field_validator(..., mode="before")` that maps `False` → `None`).
- many2one (`[id, "Name"]` tuple/list) → `Ref` dataclass-like model.
- one2many / many2many → `list[int]` (id list; no nested fetch by design).
- selection → `Literal[...]` matching the existing type_mapper output, OR a pydantic enum.
- `__odoo_model__` is a class variable (`ClassVar[str]`), not a pydantic field.
- Generated models do NOT inherit from any godoo base class — they conform structurally to
  `OdooModel` Protocol via the presence of `__odoo_model__`.

**Where `Ref` lives:** Define `Ref` in `godoo.client.typed` (not in each generated file) to avoid
duplicating it. Generated models import it: `from godoo.client.typed import Ref`. This keeps
`Ref` in core, importable without pydantic (it is a stdlib dataclass at the Protocol level):

```python
# godoo/client/typed.py (addition)
from dataclasses import dataclass

@dataclass(frozen=True)
class Ref:
    """Typed reference for many2one fields: wire format is [id, 'Name']."""
    id: int
    name: str
```

The pydantic-model version of `Ref` used inside generated models can be a subclass or just
the same dataclass — pydantic v2 validates dataclasses fine via `model_validate`.

#### B5: CLI generator placement in `godoo-introspection`

**New component:** `packages/godoo-introspection/src/godoo/introspection/pydantic_codegen.py`

This is a NEW module alongside the existing `codegen.py` (which emits TypedDict — unchanged).
It reuses:
- `Introspector.get_schemas()` — unchanged, provides `ModelSchema` / `FieldSchema`
- `_model_to_classname()` / `_model_to_filename()` — can be extracted to a `_codegen_utils.py`
  shared by both codegen modules, OR duplicated (both are tiny, duplication is fine)
- `type_mapper.python_type_str()` — used as a starting point, but the Pydantic codegen
  needs a different mapper (Pydantic types vs TypedDict annotation strings differ: `Ref` vs
  `tuple[int, str] | Literal[False]`)

**New mapper:** `packages/godoo-introspection/src/godoo/introspection/pydantic_type_mapper.py`

A separate mapper from `type_mapper.py` — same ttype inputs, different outputs:

| ttype | TypedDict mapper output | Pydantic mapper output |
|-------|------------------------|------------------------|
| many2one | `tuple[int, str] \| Literal[False]` | `Ref \| None` |
| one2many / many2many | `list[int]` | `list[int]` |
| char/text/html | `str \| Literal[False]` | `str \| None` |
| integer | `int \| Literal[False]` | `int \| None` |
| boolean | `bool` | `bool` |
| date | `str \| Literal[False]` | `date \| None` (with validator) |
| datetime | `str \| Literal[False]` | `datetime \| None` (with validator) |
| selection | `Literal[...] \| Literal[False]` | `Literal[...] \| None` |

The `False` → `None` coercion is handled via a single `@model_validator(mode="before")` or
per-field `@field_validator` on the generated model — not in the type annotation.

**CLI entry point** declared in `packages/godoo-introspection/pyproject.toml`:

```toml
[project.scripts]
godoo-introspect = "godoo.introspection.cli:main"
```

**New component:** `packages/godoo-introspection/src/godoo/introspection/cli.py`

```python
# cli.py — thin argparse wrapper
async def _generate(url, db, user, password, models, output_dir, format_): ...

def main() -> None:
    # parse args, call asyncio.run(_generate(...))
```

The CLI authenticates a client, constructs an `Introspector`, calls `get_schemas()`, then
dispatches to `CodeGenerator.write()` (TypedDict) or `PydanticCodeGenerator.write()` (Pydantic)
based on a `--format typeddict|pydantic` flag (default: `pydantic` for the v1.1 milestone).

**Modified component:** `packages/godoo-introspection/src/godoo/introspection/__init__.py`

Add `PydanticCodeGenerator` to `__all__` once the class exists.

**Pydantic as introspection dependency:** The `godoo-introspection` package generates pydantic
code — it does NOT need pydantic at runtime itself (it emits strings). Pydantic is NOT added
as a dep of `godoo-introspection`. The generated package's consumer installs pydantic.
If the CLI's `--format pydantic` is used, the generated output imports pydantic, but the CLI
itself only writes text files — no runtime pydantic import needed during generation.

---

### Feature C — Pyodide Transport Spike

#### Seam analysis

`JsonRpcTransport` in `packages/godoo-client/src/godoo/client/rpc/transport.py` is constructed
directly in `OdooClient.__init__`:

```python
self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)
```

The transport is consumed only through `self._transport.authenticate()`, `self._transport.call()`,
`self._transport.logout()`, and `self._transport.aclose()`.

**New component:** `packages/godoo-client/src/godoo/client/rpc/protocol.py`

Extract a `Transport` Protocol (structural typing, no ABC overhead):

```python
# rpc/protocol.py
from __future__ import annotations
from typing import Any, Protocol
from godoo.client.rpc.types import OdooSessionInfo

class Transport(Protocol):
    @property
    def session(self) -> OdooSessionInfo | None: ...
    def is_authenticated(self) -> bool: ...
    async def authenticate(self, username: str, password: str) -> OdooSessionInfo: ...
    async def call(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any: ...
    def logout(self) -> None: ...
    async def aclose(self) -> None: ...
```

**Modified component:** `OdooClientConfig` gets an optional `transport_factory` field:

```python
@dataclass
class OdooClientConfig:
    ...
    transport_factory: Callable[[str, str, float | None], Transport] | None = field(default=None)
```

`OdooClient.__init__` becomes:

```python
factory = config.transport_factory or JsonRpcTransport
self._transport = factory(config.url, config.database, config.timeout)
```

The `Transport` Protocol is the seam. `JsonRpcTransport` already satisfies it structurally —
no modification to `JsonRpcTransport` needed (it is a structural match, not a subclass).

**New component (spike only):** `packages/godoo-client/src/godoo/client/rpc/pyodide_transport.py`

```python
# pyodide_transport.py — NOT imported by default; only used in Pyodide env
class PyodideTransport:
    """fetch()-backed transport for Pyodide environments.
    Satisfies the Transport Protocol structurally.
    """
    def __init__(self, base_url: str, db: str, timeout: float | None = None) -> None: ...
    async def call_rpc(self, method: str, params: dict[str, Any]) -> Any:
        # Uses js.fetch (Pyodide's JS bridge) instead of httpx
        import js  # type: ignore[import]  # Pyodide-only
        ...
```

The `import js` line is Pyodide-specific and guarded — the module exists in the package but
is never imported unless explicitly constructed. CI runs in CPython so this file is never
exercised except in Pyodide testing.

**What does NOT change:** `JsonRpcTransport`, `OdooClient.call()`, all services, all tests.
The spike is purely additive: a new file + a new optional config field with a `None` default.

---

## Data-Flow Changes

### Raw read path (unchanged)

```
client.read("res.partner", [1])
  → OdooClient.read (str branch — hasattr guard is False)
  → OdooClient.call()
  → JsonRpcTransport.call()
  → Odoo JSON-RPC
  → list[dict[str, Any]]
```

### Typed read path (new)

```
client.read(ResPartner, [1])
  → OdooClient.read (type[ModelT] branch — hasattr guard is True)
  → OdooClient._typed_read()
  → lazy import: godoo.client._pydantic_transform.transform_records
  → OdooClient._raw_read("res.partner", [1])
  → OdooClient.call()
  → JsonRpcTransport.call()
  → Odoo JSON-RPC
  → list[dict] → transform_records(ResPartner, raw) → list[ResPartner]
```

### Code generation path (new)

```
CLI: godoo-introspect --url ... --models res.partner --output ./models/ --format pydantic
  → cli.py: asyncio.run(_generate(...))
  → OdooClient (authenticate)
  → Introspector.get_schemas(["res.partner"])
  → PydanticCodeGenerator.write([schema], output_dir)
  → ./models/res_partner.py (emits pydantic BaseModel source)
  → ./models/__init__.py (barrel)
```

---

## Build Order

The suggested build order respects hard dependencies between the three features:

### Step 1 — Dir rename (`packages/godoo` → `packages/godoo-client`)

**Why first:** every subsequent change touches files in this directory. Do the rename once
before any new files are added so all paths are correct from the start. The rename is a
pure filesystem + config update with no logic change — low risk, high payoff for clarity.

Files to update in one atomic commit (git mv + config edits):
1. `git mv packages/godoo packages/godoo-client`
2. `pyproject.toml` — update `mypy_path` and `version_toml`
3. `.github/workflows/test.yml` — update mypy invocation
4. `mkdocs.yml` — update `paths`
5. Verify `uv sync` and `uv run mypy ...` pass before proceeding

### Step 2 — Protocol + Transport seam (`godoo.client.rpc.protocol`, `Transport` field in config)

**Why before typed models:** the `Transport` Protocol and the `transport_factory` field in
`OdooClientConfig` are additive and zero-risk (no behaviour change). Establishing this seam
early also enables the Pyodide spike (Step 4) to proceed independently once the seam exists.
No pydantic involved.

### Step 3 — Typed models core (`godoo.client.typed`, `_pydantic_transform`, overloads in `client.py`)

**Why before the CLI generator:** the generated models import `godoo.client.typed.OdooModel`
and `Ref`. Core must exist before codegen can emit valid imports. Also the `godoo-client[typed]`
optional extra must be declared before the CLI generator's output is tested end-to-end.

Order within Step 3:
3a. Add `godoo/client/typed.py` (Protocol + `Ref`) — pure stdlib, no pydantic
3b. Add `godoo[typed]` optional extra to `packages/godoo-client/pyproject.toml`
3c. Add `godoo/client/_pydantic_transform.py` (lazy pydantic import)
3d. Add `@overload` signatures + dispatch guard to `client.py:read` and `search_read`
3e. Add tests: raw path unchanged; typed path returns model instances; missing pydantic gives clear error

### Step 4 — Pydantic CLI generator in `godoo-introspection`

**Why after Step 3:** `PydanticCodeGenerator` emits `from godoo.client.typed import OdooModel`
— the Protocol must exist. The CLI can be built and tested only after the core typed layer is
stable.

Order within Step 4:
4a. Add `godoo/introspection/pydantic_type_mapper.py`
4b. Add `godoo/introspection/pydantic_codegen.py` (PydanticCodeGenerator)
4c. Add `godoo/introspection/cli.py` + `[project.scripts]` entry point
4d. Integration test: CLI generates a model package from a live Odoo; `client.read(Model, ...)` validates

### Step 5 — Pyodide transport spike

**Why last:** it is explicitly a spike — the outcome determines whether to commit to a browser
build or not. The `Transport` Protocol seam from Step 2 is the prerequisite. The spike has
no dependencies on Steps 3/4. It can run in parallel with Step 4 if bandwidth allows, but
sequentially placing it last reduces risk: if the spike reveals breaking changes (e.g. httpx
cannot be made Pyodide-compatible, requiring a fork), those decisions are made after the higher-
value typed-models work ships.

Spike deliverable: a proof-of-concept `pyodide_transport.py` + a decision memo on whether
to commit to `godoo-client[pyodide]` as a supported configuration.

---

## Component Summary Table

| Component | New / Modified | Package | Path |
|-----------|---------------|---------|------|
| `packages/godoo` → `packages/godoo-client` | Modified (rename) | — | filesystem + config |
| `godoo/client/typed.py` | NEW | godoo-client | `src/godoo/client/typed.py` |
| `godoo/client/_pydantic_transform.py` | NEW | godoo-client | `src/godoo/client/_pydantic_transform.py` |
| `OdooClient.read` / `search_read` overloads | Modified | godoo-client | `src/godoo/client/client.py` |
| `OdooClient._typed_read` (private) | NEW method | godoo-client | `src/godoo/client/client.py` |
| `OdooClientConfig.transport_factory` | Modified (new field) | godoo-client | `src/godoo/client/client.py` |
| `godoo/client/rpc/protocol.py` | NEW | godoo-client | `src/godoo/client/rpc/protocol.py` |
| `godoo/client/rpc/pyodide_transport.py` | NEW (spike) | godoo-client | `src/godoo/client/rpc/pyodide_transport.py` |
| `packages/godoo-client/pyproject.toml` `[typed]` extra | Modified | godoo-client | `pyproject.toml` |
| `godoo/introspection/pydantic_type_mapper.py` | NEW | godoo-introspection | `src/godoo/introspection/pydantic_type_mapper.py` |
| `godoo/introspection/pydantic_codegen.py` | NEW | godoo-introspection | `src/godoo/introspection/pydantic_codegen.py` |
| `godoo/introspection/cli.py` | NEW | godoo-introspection | `src/godoo/introspection/cli.py` |
| `godoo/introspection/__init__.py` | Modified (add exports) | godoo-introspection | `src/godoo/introspection/__init__.py` |
| `packages/godoo-introspection/pyproject.toml` | Modified (add scripts) | godoo-introspection | `pyproject.toml` |
| `pyproject.toml` (root) | Modified (mypy_path, version_toml) | workspace | `pyproject.toml` |
| `.github/workflows/test.yml` | Modified (mypy invocation) | CI | `.github/workflows/test.yml` |
| `mkdocs.yml` | Modified (paths) | docs | `mkdocs.yml` |

**Unchanged:** `JsonRpcTransport`, all 8 services, `SafetyContext`, `errors.py`, `config.py`,
`godoo/introspection/codegen.py` (TypedDict path), `type_mapper.py`, `IntrospectionCache`,
`godoo-testcontainers/*`, `godoo-meta/*`.

---

## Import Isolation Pattern (authoritative)

```
import godoo                          # never imports pydantic
from godoo.client import OdooClient  # never imports pydantic

client.read("res.partner", [1])       # raw path — pydantic not imported

client.read(ResPartner, [1])          # typed path — pydantic imported HERE, lazily,
                                      # inside OdooClient._typed_read()
                                      # via: from godoo.client._pydantic_transform import ...
```

The `godoo.client.typed` module (Protocol + `Ref`) IS imported at module level from `client.py`
only under `TYPE_CHECKING` — never at runtime from `client.py` itself. The Protocol is available
at runtime only if the user imports `godoo.client.typed` explicitly, which is a no-op without
pydantic (typed.py has no pydantic dependency).

The `_pydantic_transform` module is NEVER in `__init__.py`, never in `__all__`, never imported
at module load. It is a private implementation detail gated behind `hasattr(model, "__odoo_model__")`.

---

## Anti-Patterns to Avoid

### Dispatch on `isinstance(model, type)` alone

`isinstance(model, type)` is True for any class including plain strings (no — strings are not
types) but also for any class the user passes accidentally. `hasattr(model, "__odoo_model__")`
is the correct guard: it is specific to godoo-generated models and does not touch pydantic.

### Importing `godoo.client.typed` at the top of `client.py`

Even though `typed.py` has no pydantic dependency, importing it unconditionally at the top of
`client.py` forces it into the module load path and adds a small overhead. Use `TYPE_CHECKING`
for the type annotation and `hasattr` for the runtime dispatch.

### Making `Ref` a pydantic model in core

`Ref` in `godoo.client.typed` must be a stdlib dataclass. Generated model files import it from
core. If core's `Ref` were a pydantic model, installing `godoo-client` without `[typed]` would
import pydantic at install time — breaking the isolation guarantee.

### Putting `PydanticCodeGenerator` in the same file as `CodeGenerator`

`codegen.py` emits TypedDict source; `pydantic_codegen.py` emits pydantic source. They have
different type mappers and different template logic. Keeping them separate preserves the single-
responsibility principle and prevents the TypedDict path from growing pydantic-aware conditionals.

### Subclassing `JsonRpcTransport` for Pyodide

The Pyodide transport is a completely different HTTP stack (`js.fetch` vs `httpx`). Subclassing
would inherit httpx internals that don't apply. Implement as a separate class satisfying the
`Transport` Protocol structurally — zero shared code with `JsonRpcTransport`.

---

*Architecture research for: godoo-py v1.1 — typed models + browser reach*
*Researched: 2026-05-27*
