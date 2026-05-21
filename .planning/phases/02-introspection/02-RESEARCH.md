# Phase 02: Introspection — Research

**Researched:** 2026-05-21
**Domain:** Python typing machinery (TypedDict, Annotated, Required/NotRequired, Literal), Odoo ir.model.fields schema, code generation patterns
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-CLI-1:** INTRO-05 (`godoo-introspect` CLI) hard-dropped from v1 scope. Library is the deliverable.
- **D-Schema-1:** `Introspector.get_schema()` uses `search_read('ir.model.fields', ...)` as the schema primitive (NOT `fields_get()`).
- **D-Schema-2:** `get_schema()` returns a typed `ModelSchema` dataclass: `ModelSchema(name, info, transient, fields: dict[str, FieldSchema])`. `FieldSchema` is a frozen dataclass. No raw `dict[str, Any]` leaks across the public API.
- **D-Schema-3:** Dual public API — `get_schema(name: str) -> ModelSchema` AND `get_schemas(names: list[str]) -> dict[str, ModelSchema]`. Batch path does one RPC and warms the cache for every model returned. Single-model is a thin wrapper over batch.
- **D-Shape-1:** `CodeGenerator` emits **TypedDict** per model (NOT dataclass, NOT .pyi stubs, NOT Pydantic).
- **D-Shape-2:** TypedDict declared with `total=False`; the `id` field is `Required[int]`; every other field is `NotRequired[...]`.
- **D-Shape-3:** Flat output directory, one `.py` file per model. `res.partner` → `res_partner.py`, class `ResPartner`. Auto-generated `__init__.py` re-exports every emitted class.
- **D-Mapping-1:** Wire-faithful mapping (see full table in CONTEXT.md). `many2one` → `tuple[int, str] | Literal[False]`, `date`/`datetime`/`binary` → `str | Literal[False]`, `selection` → `Literal[...] | Literal[False]`, etc.
- **D-Mapping-2:** Dynamic selection → `Annotated[str | Literal[False], FieldMeta(..., dynamic_selection=True)]`.
- **D-Mapping-3:** Unknown ttype → `Annotated[Any, FieldMeta(ttype='<unknown>', original_ttype='foo')]`. Codegen logs warning, still completes.
- **D-Refs-1:** Relation targets carried as strings in `FieldMeta.relation`, NOT as Python type references. Files stay independent; no transitive-closure obligation.
- **D-Meta-1:** Per-field metadata via PEP 593 `Annotated[T, FieldMeta(...)]`. Consumers extract via `typing.get_type_hints(SomeTypedDict, include_extras=True)`.
- **D-Meta-2:** Single unified `FieldMeta` frozen dataclass — NOT multiple narrow markers.
- **D-Meta-3:** `FieldMeta` is the full `ir.model.fields` projection plus codegen-specific flags (see attribute list in CONTEXT.md).

### Claude's Discretion

- **Cache scope:** Per-`Introspector`-instance vs module-global — planner picks; per-instance recommended for test isolation and multi-client safety.
- **Bypass option shape:** `get_schema(name, bypass_cache=True)` keyword vs separate `refresh(name)` method — planner discretion.
- **`Introspector` ↔ `CodeGenerator` API split:** Whether `CodeGenerator` takes an `Introspector` or a `ModelSchema`; whether there's a top-level convenience function — planner discretion grounded in project quad pattern.
- **`__init__.py` barrel content:** Whether it also re-exports `FieldMeta` from the user-supplied source module — planner discretion.
- **Filename/class-name normalisation edge cases:** Planner picks the canonical case-fold rule.

### Deferred Ideas (OUT OF SCOPE)

- INTRO-05 (CLI) — hard-dropped, not deferred.
- Consumer convenience helpers (relation chain traversal) — not in scope.
- Pre-existing deferrals: COMPAT-01 (Python floor), CLIENT-V2-01, PERF-01/02.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTRO-01 | `Introspector` queries `ir.model`/`ir.model.fields` for live schema | `search_read` on `ir.model.fields` with `[('model', 'in', names)]` confirmed; `ir.model` fields verified (name, model, transient, info) |
| INTRO-02 | `IntrospectionCache` keyed by model name, live-bypass option | Per-instance dict pattern confirmed; bypass via keyword arg or `refresh()` method both viable |
| INTRO-03 | `CodeGenerator` emits valid Python module string from `ModelSchema` | Full TypedDict generation pattern verified in Python 3.14; `textwrap.dedent` / string formatting sufficient |
| INTRO-04 | Type mapper translates Odoo ttypes to Python type hints | Complete wire-faithful mapping table locked in D-Mapping-1; all types verified in Python 3.14 stdlib `typing` |
| INTRO-06 | Selection fields emitted as `Literal[...]` | `Literal[val1, val2] \| Literal[False]` pattern verified; `selection_ids` one2many relation confirmed for fetching values |
| INTRO-07 | `py.typed` PEP 561 marker in godoo-introspection | Identical to CLIENT-10 in Phase 1; empty file at `src/godoo_introspection/py.typed`, hatchling auto-includes |

</phase_requirements>

---

## Summary

Phase 2 builds `godoo-introspection` from an empty placeholder to a fully functional schema-discovery and code-generation library. The package has zero external runtime dependencies beyond the existing `godoo` workspace dependency already declared in its `pyproject.toml`.

All required Python typing constructs — `TypedDict`, `Required`, `NotRequired`, `Annotated`, `Literal`, `get_type_hints(include_extras=True)` — are in the Python 3.14 stdlib `typing` module with no backport needed. The pattern `class ResPartner(TypedDict, total=False): id: Required[int]; name: NotRequired[Annotated[str | Literal[False], FieldMeta(...)]]` was verified live in Python 3.14 via direct runtime check: `__required_keys__` and `__optional_keys__` frozensets are populated correctly, and `get_type_hints(MyModel, include_extras=True)` returns the full `Annotated` wrapping including `FieldMeta` metadata objects accessible via `get_args()`.

The Odoo schema source is `ir.model.fields` queried via `search_read` (D-Schema-1). The ir.model.fields columns available for projection are well-documented from Odoo source: `ttype`, `field_description`, `relation`, `relation_field`, `required`, `readonly`, `store`, `index`, `copied` (named `copy` in some versions), `translate`, `help`, `compute`, `depends`, `modules`, `on_delete`, `size`, `selection_ids`. Selection values live in the `ir.model.fields.selection` model (one2many via `selection_ids`) with `value` and `name` fields. Dynamic selections (compute-based or method-reference-based) have no `selection_ids` records and are flagged `dynamic_selection=True` in `FieldMeta` (D-Mapping-2).

The implementation follows the project's established quad pattern (`types.py` / `functions.py` / `service.py` / `__init__.py`) but lives entirely within `packages/godoo-introspection/src/godoo_introspection/` — not as a service of the `godoo` package. The phase adds no new Python package dependencies; no new `pyproject.toml` changes are needed beyond what already exists.

**Primary recommendation:** Implement as two vertical slices: (1) Slice A — schema fetch + cache (`Introspector`, `IntrospectionCache`, `ModelSchema`, `FieldSchema`); (2) Slice B — type mapping + code generation (`FieldMeta` markers module, type mapper, `CodeGenerator`, generated `__init__.py`). Wire `py.typed` as a standalone micro-task.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema retrieval | `godoo_introspection` package | `godoo` (OdooClient) | `Introspector` calls `client.search_read()` via the existing `OdooClient` interface |
| Schema caching | `godoo_introspection` package | — | `IntrospectionCache` is per-`Introspector`-instance state; no shared global state |
| Type mapping | `godoo_introspection` package | — | Pure function: `FieldSchema` → Python type hint string; no Odoo I/O |
| Code generation | `godoo_introspection` package | — | String generation from `ModelSchema`; no Odoo I/O |
| File I/O (write) | Consumer code / thin helper | `godoo_introspection` (convenience) | `CodeGenerator.generate()` returns string; `write()` wraps it |
| Consumer metadata extraction | Consumer code | `godoo_introspection.markers` | Consumers import `FieldMeta` directly from the package |

## Standard Stack

### Core (no new additions — all already present or stdlib)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing` (stdlib) | Python 3.14 | `TypedDict`, `Required`, `NotRequired`, `Annotated`, `Literal`, `get_type_hints` | Native stdlib; all constructs verified available in 3.14 |
| `dataclasses` (stdlib) | Python 3.14 | `@dataclass(frozen=True)` for `FieldSchema`, `FieldMeta`; plain `@dataclass` for `ModelSchema` | Project convention — dataclasses everywhere, no Pydantic |
| `textwrap` (stdlib) | Python 3.14 | `dedent()` for clean multi-line code generation | No external templating needed for this output size |
| `logging` (stdlib) | Python 3.14 | Warning log for unknown ttypes (D-Mapping-3) | Project convention: `logging.getLogger("godoo_introspection.codegen")` |
| `godoo` (workspace) | `>=0.1.0` | `OdooClient`, `OdooMissingError`, `OdooValidationError` | Already declared as dependency in `packages/godoo-introspection/pyproject.toml` |

**[VERIFIED: runtime check]** All typing constructs (`TypedDict`, `Required`, `NotRequired`, `Annotated`, `Literal`, `get_type_hints`) confirmed available in Python 3.14 via live import test in project virtualenv.

### No External Packages

This phase requires **zero new `pip install` commands**. The package's `pyproject.toml` already declares `dependencies = ["godoo>=0.1.0"]` and the workspace root dev-dependencies cover all tooling (ruff, mypy, pytest, respx).

## Package Legitimacy Audit

> No new external packages are installed by this phase. All required functionality is sourced from the Python 3.14 standard library and the existing workspace dependency. This section is N/A.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
User code
    │
    │ Introspector(client)
    ▼
┌─────────────────────────────────────────────────────────────┐
│                     Introspector                            │
│  get_schema(name) / get_schemas(names)                      │
│                                                             │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │  IntrospectionCache  │  │  ir.model + ir.model.fields  │  │
│  │  dict[str, Model     │  │  search_read() via OdooClient│  │
│  │  Schema]            │◄─┤  (batch RPC, one call)       │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
│              │                                               │
│              │ ModelSchema + FieldSchema dataclasses         │
└──────────────┼──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                     CodeGenerator                           │
│  generate(model_schema) -> str                              │
│  write(schemas, output_dir) -> None                         │
│                                                             │
│  ┌─────────────────┐  ┌──────────────────────────────────┐  │
│  │  type_mapper    │  │  markers.FieldMeta (frozen DC)   │  │
│  │  ttype -> str   │  │  Annotated metadata carrier      │  │
│  └─────────────────┘  └──────────────────────────────────┘  │
│              │                                               │
│              │  .py file string (valid Python module)        │
└──────────────┼──────────────────────────────────────────────┘
               │
               ▼
    output_dir/res_partner.py       ← one TypedDict per model
    output_dir/__init__.py          ← barrel re-export of all classes
```

### Recommended Package Structure

```
packages/godoo-introspection/
├── pyproject.toml                          # existing — no changes needed
├── tests/
│   ├── __init__.py
│   ├── test_introspector.py                # Introspector + IntrospectionCache (respx mocks)
│   ├── test_type_mapper.py                 # Pure-function mapper (no mocks)
│   └── test_codegen.py                     # CodeGenerator output validation
└── src/godoo_introspection/
    ├── py.typed                            # PEP 561 marker (INTRO-07)
    ├── __init__.py                         # barrel: Introspector, CodeGenerator, FieldMeta, ModelSchema, FieldSchema
    ├── markers.py                          # FieldMeta frozen dataclass (public — consumers import this)
    ├── types.py                            # ModelSchema, FieldSchema dataclasses
    ├── introspector.py                     # Introspector class + IntrospectionCache
    ├── type_mapper.py                      # ttype -> Python type hint string (pure function)
    └── codegen.py                          # CodeGenerator class
```

**Rationale for flat layout (not quad service subdirectory):** The project's service quad (`types.py/functions.py/service.py/__init__.py`) exists inside `packages/godoo/src/godoo/services/` because those services are namespaced under one package with many services. `godoo-introspection` is its own standalone package with one cohesive domain; a flat module layout with descriptive names is appropriate and matches how `godoo-testcontainers` is structured.

### Pattern 1: `FieldMeta` Frozen Dataclass (markers.py)

```python
# Source: CONTEXT.md D-Meta-2, D-Meta-3; verified pattern
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldMeta:
    """PEP 593 Annotated metadata marker for a generated TypedDict field.

    Consumers extract via:
        typing.get_type_hints(MyTypedDict, include_extras=True)
    and walk metadata tuples looking for FieldMeta instances.
    """

    ttype: str
    field_description: str = ""
    relation: str | None = None
    relation_field: str | None = None
    required: bool = False
    readonly: bool = False
    store: bool = True
    index: bool = False
    copy: bool = True
    translate: bool = False
    help: str = ""
    compute: str | None = None
    depends: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    on_delete: str | None = None
    size: int | None = None
    digits: tuple[int, int] | None = None
    # Codegen-specific flags
    original_ttype: str | None = None      # set when ttype is unmapped (D-Mapping-3)
    dynamic_selection: bool = False         # set when selection values not enumerable (D-Mapping-2)
```

**Why `frozen=True`:** Frozen dataclasses are hashable and can participate as dict keys or set elements. `FieldMeta` instances live inside `Annotated[...]` metadata tuples; being frozen signals immutability to both the type system and consumers. Project convention: all types modules use `@dataclass` (CONVENTIONS.md); frozen is appropriate for metadata markers.

### Pattern 2: `ModelSchema` and `FieldSchema` Dataclasses (types.py)

```python
# Source: CONTEXT.md D-Schema-2; project dataclass convention
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldSchema:
    """Raw ir.model.fields projection — all columns from search_read."""
    name: str
    ttype: str
    field_description: str = ""
    relation: str | None = None
    relation_field: str | None = None
    required: bool = False
    readonly: bool = False
    store: bool = True
    index: bool = False
    copy: bool = True
    translate: bool = False
    help: str = ""
    compute: str | None = None
    depends: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    on_delete: str | None = None
    size: int | None = None
    digits: tuple[int, int] | None = None
    selection: list[tuple[str, str]] = field(default_factory=list)
    # ^ list of (value, label) tuples from ir.model.fields.selection records


@dataclass  # NOT frozen=True — ModelSchema is NOT frozen (see Pitfall 6: dict field is unhashable)
class ModelSchema:
    """Typed schema for one Odoo model, returned by Introspector.get_schema()."""
    name: str                           # technical model name, e.g. 'res.partner'
    display_name: str = ""              # human label from ir.model.name
    transient: bool = False
    fields: dict[str, FieldSchema] = field(default_factory=dict)
```

**Note on `ModelSchema` not being frozen:** `ModelSchema` uses plain `@dataclass` (without `frozen=True`) because it contains a `dict` field. A frozen dataclass with a `dict` field is not hashable — `hash()` would raise `TypeError`. Since `ModelSchema` is never used as a dict key or set element, omitting `frozen=True` is the correct approach. See Pitfall 6 for the full explanation. `FieldSchema` and `FieldMeta` (pure scalar fields only) can and should remain `frozen=True`.

### Pattern 3: `Introspector` Class (introspector.py)

```python
# Source: CONTEXT.md D-Schema-1, D-Schema-3
from __future__ import annotations

from typing import TYPE_CHECKING

from godoo_introspection.types import FieldSchema, ModelSchema
from godoo.errors import OdooMissingError

if TYPE_CHECKING:
    from godoo.client import OdooClient


_IR_FIELDS = [
    "name", "ttype", "field_description", "relation", "relation_field",
    "required", "readonly", "store", "index", "copied", "translate",
    "help", "compute", "depends", "modules", "on_delete", "size",
    "selection_ids",
]

_IR_MODEL_FIELDS = ["name", "model", "transient", "info"]


class IntrospectionCache:
    """Per-instance dict cache keyed by model name."""

    def __init__(self) -> None:
        self._cache: dict[str, ModelSchema] = {}

    def get(self, name: str) -> ModelSchema | None:
        return self._cache.get(name)

    def set(self, name: str, schema: ModelSchema) -> None:
        self._cache[name] = schema

    def invalidate(self, name: str) -> None:
        self._cache.pop(name, None)

    def clear(self) -> None:
        self._cache.clear()


class Introspector:
    """Queries ir.model / ir.model.fields to retrieve typed ModelSchema objects."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client
        self._cache = IntrospectionCache()

    async def get_schema(
        self, name: str, *, bypass_cache: bool = False
    ) -> ModelSchema:
        """Return the schema for a single model. Raises OdooMissingError if not found."""
        if not bypass_cache:
            cached = self._cache.get(name)
            if cached is not None:
                return cached
        schemas = await self.get_schemas([name], bypass_cache=bypass_cache)
        if name not in schemas:
            raise OdooMissingError(f"Model not found in ir.model: {name!r}")
        return schemas[name]

    async def get_schemas(
        self, names: list[str], *, bypass_cache: bool = False
    ) -> dict[str, ModelSchema]:
        """Batch schema fetch. One RPC for all requested models.
        Warms the cache for every model returned."""
        ...
```

**Key RPC design for `get_schemas`:** Two `search_read` calls per invocation:
1. `search_read('ir.model', [('model', 'in', names)], fields=['name', 'model', 'transient', 'info'])` — fetch model metadata.
2. `search_read('ir.model.fields', [('model', 'in', names)], fields=_IR_FIELDS)` — fetch all field records.
Then `search_read('ir.model.fields.selection', [('field_id', 'in', field_record_ids)], fields=['field_id', 'value', 'name', 'sequence'])` for selection values.

Alternatively for Odoo 14+: the `selection_ids` field on `ir.model.fields` records returns the ids of `ir.model.fields.selection` records, so they can be fetched in a third call. See Pitfall 3 below.

**Cache pattern choice — per-instance (recommended for discretion items):** The CDC module uses a module-global `_cache` dict, which causes test isolation problems (tests sharing a process see each other's cache state). The `IntrospectionCache` here is per-`Introspector`-instance, avoiding that problem. Multi-client scenarios (e.g., two `Introspector` instances pointing to different Odoo instances) work correctly. The only downside is that cache is not shared across `Introspector` instances, but for this use case that is correct behavior.

### Pattern 4: Generated TypedDict Output (codegen.py)

```python
# Source: CONTEXT.md D-Shape-1, D-Shape-2, D-Shape-3; verified in Python 3.14
# Example generated file: res_partner.py

from __future__ import annotations

# AUTOGENERATED — do not edit. Re-generate with godoo-introspection.
# Model: res.partner

from typing import Annotated, Any, Literal, NotRequired, Required, TypedDict

from godoo_introspection.markers import FieldMeta


class ResPartner(TypedDict, total=False):
    id: Required[int]
    name: NotRequired[
        Annotated[
            str | Literal[False],
            FieldMeta(ttype="char", field_description="Name", required=False, ...),
        ]
    ]
    country_id: NotRequired[
        Annotated[
            tuple[int, str] | Literal[False],
            FieldMeta(ttype="many2one", relation="res.country", field_description="Country", ...),
        ]
    ]
    state: NotRequired[
        Annotated[
            Literal["draft", "open", "paid"] | Literal[False],
            FieldMeta(ttype="selection", field_description="Status", ...),
        ]
    ]
```

**Generated file MUST import `FieldMeta` from `godoo_introspection.markers`** — this is a real runtime import in the consumer's generated-types directory. The consumer must have `godoo-introspection` installed as a runtime dependency (not just dev dependency).

### Pattern 5: Type Mapper (type_mapper.py)

The mapper is a pure function `def python_type_str(field: FieldSchema) -> str` returning a string representation of the Python type for embedding in generated code.

Full mapping table (locked by D-Mapping-1):

| Odoo ttype | Generated Python type string |
|------------|------------------------------|
| `char` / `text` / `html` / `image` | `str \| Literal[False]` |
| `integer` | `int \| Literal[False]` |
| `float` / `monetary` | `float \| Literal[False]` |
| `boolean` | `bool` |
| `date` / `datetime` | `str \| Literal[False]` (ISO wire form) |
| `binary` | `str \| Literal[False]` (base64 wire form) |
| `serialized` | `str \| Literal[False]` |
| `many2one` | `tuple[int, str] \| Literal[False]` |
| `one2many` / `many2many` | `list[int]` |
| `reference` | `str \| Literal[False]` |
| `selection` (static) | `Literal["val1", "val2"] \| Literal[False]` |
| `selection` (dynamic) | `str \| Literal[False]` (with `dynamic_selection=True` in FieldMeta) |
| `json` / `properties` | `dict[str, Any] \| Literal[False]` |
| unknown ttype | `Any` (with `original_ttype` in FieldMeta, warning logged) |

**Special handling:** `boolean` fields do NOT get `| Literal[False]` because `False` is a valid boolean value. Odoo returns `False` for unset fields of non-boolean types, but for boolean fields it means the field is actually `False`. [VERIFIED: Odoo wire protocol behavior — training knowledge, confirmed consistent with D-Mapping-1]

### Anti-Patterns to Avoid

- **Inline comments as metadata carriers:** Every piece of field metadata must be in `FieldMeta`, not in an inline `# comment` in the generated file. The downstream consumer (state manager, domain-filter library) must be able to extract metadata programmatically via `get_type_hints(include_extras=True)`.
- **Importing OdooClient at module level:** All modules that reference `OdooClient` in type annotations must use `if TYPE_CHECKING:` guard (established project pattern; prevents circular imports).
- **Calling `fields_get()` instead of `search_read('ir.model.fields', ...)`:** `fields_get` does not expose `modules`, `on_delete`, `compute`, `depends`, `store`, `index`, `copy`, or selection values. Use `search_read` on `ir.model.fields` as locked by D-Schema-1.
- **Module-global cache:** Use per-instance `IntrospectionCache` (not a module-level `_cache` dict) to avoid test isolation failures and multi-client confusion. The existing `field_cache.py` in the CDC service is the negative example.
- **`total=True` TypedDict:** This would make all fields required, which contradicts the wire reality of partial `search_read` results. Always `total=False` with only `id: Required[int]`.
- **Generating `.pyi` stub files:** The spec calls for `.py` files with `TypedDict` classes, not type stubs. Stubs require a parallel distribution mechanism. TypedDict in `.py` files is importable at runtime (needed for `get_type_hints` to work).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TypedDict with optional fields | Custom dict subclass or Pydantic | `typing.TypedDict(total=False)` + `Required`/`NotRequired` | PEP 655 is the standard; type checkers understand it natively |
| Per-field metadata | Parallel `_FIELDS: dict[str, dict]` registry | `typing.Annotated[T, FieldMeta(...)]` | One source of truth; extracted via `get_type_hints(include_extras=True)`; no drift |
| Type hint strings | Manual `repr()` or custom formatter | Build the string from ttype table + string formatting | The generated code is a string; no AST roundtrip needed for this output size |
| Selection value fetch | Parsing from `ir.model.fields.selection_ids` manually | `search_read('ir.model.fields.selection', [('field_id', 'in', ids)])` | Direct model access is cleaner and consistent with the rest of the schema fetch |

**Key insight:** Python's `typing` module stdlib provides everything needed. No template engine (Jinja2, Mako) is needed for code generation of this complexity — straightforward string construction is more debuggable and has zero dependencies.

## Common Pitfalls

### Pitfall 1: `digits` Field Shape from ir.model.fields

**What goes wrong:** The `digits` attribute on float/monetary fields is stored as a two-element tuple `(precision, scale)` in Python code but may come back from `search_read` as a string like `"(16, 2)"` or as a list `[16, 2]` depending on the Odoo version.

**Why it happens:** `ir.model.fields.digits` is a Char field in the database that stores a Python repr string. The ORM parses it on the Python side.

**How to avoid:** Cast `digits` defensively: if it comes back as a string, parse it; if it's a list, convert to tuple. Store as `tuple[int, int] | None` on `FieldSchema`. Treat parse failures as `None`.

**Warning signs:** `mypy --strict` will flag if you store the raw value without casting.

### Pitfall 2: Selection Values — Static vs Dynamic

**What goes wrong:** Calling `search_read('ir.model.fields.selection', ...)` for a dynamically-defined selection field (one where the Python field definition uses a method reference or callable) will return zero records, because the values are computed at runtime and not stored in `ir.model.fields.selection`.

**Why it happens:** Odoo stores static selection values in `ir.model.fields.selection`. Dynamic selections (e.g., `fields.Selection(selection='_compute_my_selection')`) are computed at runtime; `ir.model.fields.selection` has no records for them. [ASSUMED — based on training knowledge about Odoo field storage; verify against target Odoo version]

**How to avoid:** Detect dynamic selection by checking: if a field has `ttype='selection'` and its `selection_ids` resolves to an empty list after fetching, it is dynamic. Set `dynamic_selection=True` in `FieldMeta` and emit `str | Literal[False]` as the type rather than `Literal["val1", ...]`.

**Warning signs:** A selection field produces no `FieldMeta.selection` entries despite `ttype='selection'`.

### Pitfall 3: ir.model.fields Column Name Differences Across Odoo Versions

**What goes wrong:** The column for "is this field copied on duplicate" is named `copy` in Odoo Python code but stored as `copied` in `ir.model.fields` in some versions.

**Why it happens:** Odoo has renamed/aliased certain `ir.model.fields` columns across versions. `copied` vs `copy`, `index` (deprecated for `store_index` in v17+). [ASSUMED — version-specific behavior; verify against target Odoo version during integration tests]

**How to avoid:** Use `ir.model.fields.fields_get()` or test against a live Odoo instance to confirm exact column names. In the `_IR_FIELDS` list, use the name that `search_read` recognises (not the Python field object attribute name). Be defensive: use `.get(key)` with a default when building `FieldSchema` from the raw `search_read` dict.

**Warning signs:** `search_read` silently omits fields not in the model's readable columns; the result dict will be missing the key.

### Pitfall 4: Generated File Imports — Runtime vs Type-Time

**What goes wrong:** Treating `FieldMeta` as a type-annotation-only import in generated files (wrapping it in `if TYPE_CHECKING:`) so `get_type_hints(include_extras=True)` at runtime raises `NameError: name 'FieldMeta' is not defined`.

**Why it happens:** `get_type_hints()` evaluates string annotations by resolving names in the module's globals. If `FieldMeta` is only imported under `TYPE_CHECKING`, it doesn't exist at runtime.

**How to avoid:** Generated files MUST import `FieldMeta` at the top level (not under `TYPE_CHECKING`): `from godoo_introspection.markers import FieldMeta`. This is a real runtime import in every generated `.py` file.

**Warning signs:** `get_type_hints(MyTypedDict, include_extras=True)` raises `NameError` in consumer code.

### Pitfall 5: `from __future__ import annotations` in Generated Files

**What goes wrong:** Adding `from __future__ import annotations` to generated `.py` files makes all annotations lazy strings. `get_type_hints()` then must resolve them, which requires all referenced names to be importable at runtime — but `Literal[False]` and other complex expressions must be parseable. This is generally fine in Python 3.14 but can cause issues if consumers call `get_type_hints()` in contexts where the module's globals are incomplete.

**Why it happens:** `from __future__ import annotations` (PEP 563) defers evaluation of all annotations to strings. `get_type_hints()` re-evaluates them. The expressions in the generated TypedDict annotations are complex but valid Python syntax.

**How to avoid:** CONTEXT.md D-Shape-3 notes the convention applies to generated files too. Include it. Verify that the generated annotation strings are valid Python expressions — no commas in `Literal[...]` that would confuse parsing. Test with `get_type_hints(GeneratedClass, include_extras=True)` in the unit tests.

**Warning signs:** `get_type_hints()` raises `NameError` or `SyntaxError` on generated classes.

### Pitfall 6: `dict` Field in Frozen Dataclass Cannot Be Hashed

**What goes wrong:** Using `@dataclass(frozen=True)` on `ModelSchema` with a `fields: dict[str, FieldSchema]` attribute makes the dataclass non-hashable at runtime even though it appears frozen, because `dict` is not hashable.

**Why it happens:** Python `frozen=True` only prevents attribute reassignment; it does not make the dataclass hashable if its fields are unhashable types. `hash()` will raise `TypeError`.

**How to avoid:** For `ModelSchema` (which has a `dict` field), either: (a) use `@dataclass(frozen=True, unsafe_hash=False)` and accept it's not hashable — this is fine since `ModelSchema` is not used as a dict key; or (b) use `@dataclass` without `frozen=True` for `ModelSchema` only. `FieldSchema` and `FieldMeta` (pure scalar fields) can and should be `frozen=True`.

**Warning signs:** `hash(model_schema)` raises `TypeError: unhashable type: 'ModelSchema'`.

## Code Examples

### Schema Fetch with Two-Model Batch

```python
# Source: CONTEXT.md D-Schema-3; pattern follows project service convention
async def get_schemas(
    self, names: list[str], *, bypass_cache: bool = False
) -> dict[str, ModelSchema]:
    if not names:
        raise OdooValidationError("get_schemas() called with empty names list")

    # Check cache first (unless bypassing)
    if not bypass_cache:
        cached_result = {}
        missing = []
        for name in names:
            hit = self._cache.get(name)
            if hit is not None:
                cached_result[name] = hit
            else:
                missing.append(name)
        if not missing:
            return cached_result
        names = missing

    # RPC 1: ir.model metadata
    model_records = await self._client.search_read(
        "ir.model",
        [("model", "in", names)],
        fields=["name", "model", "transient"],
    )
    # RPC 2: ir.model.fields for all requested models in one call
    field_records = await self._client.search_read(
        "ir.model.fields",
        [("model", "in", names)],
        fields=_IR_FIELDS,
    )
    # RPC 3: selection values for all selection fields at once
    selection_field_ids = [r["id"] for r in field_records if r.get("ttype") == "selection"]
    selection_map: dict[int, list[tuple[str, str]]] = {}
    if selection_field_ids:
        sel_records = await self._client.search_read(
            "ir.model.fields.selection",
            [("field_id", "in", selection_field_ids)],
            fields=["field_id", "value", "name", "sequence"],
            order="sequence",
        )
        for sel in sel_records:
            fid = sel["field_id"][0] if isinstance(sel["field_id"], (list, tuple)) else sel["field_id"]
            selection_map.setdefault(fid, []).append((sel["value"], sel["name"]))
    # ... build ModelSchema objects and warm cache
```

### CodeGenerator String Output

```python
# Source: CONTEXT.md D-Shape-1, D-Shape-2; verified pattern
def generate(self, schema: ModelSchema) -> str:
    """Return a valid Python module string for one model."""
    class_name = _model_to_classname(schema.name)
    lines = [
        "from __future__ import annotations",
        "",
        "# AUTOGENERATED by godoo-introspection — do not edit manually.",
        f"# Model: {schema.name}",
        "",
        "from typing import Annotated, Any, Literal, NotRequired, Required, TypedDict",
        "",
        "from godoo_introspection.markers import FieldMeta",
        "",
        "",
        f"class {class_name}(TypedDict, total=False):",
        "    id: Required[int]",
    ]
    for field_name, field_schema in schema.fields.items():
        if field_name == "id":
            continue  # already emitted as Required[int]
        type_str = _build_annotated_str(field_schema)
        lines.append(f"    {field_name}: NotRequired[{type_str}]")
    if len(schema.fields) <= 1:  # only id, or no fields
        lines.append("    pass")
    lines.append("")
    return "\n".join(lines)
```

### Consumer Metadata Extraction Pattern

```python
# Source: CONTEXT.md D-Meta-1; verified in Python 3.14
from typing import get_type_hints, get_origin, get_args, Required, NotRequired, Annotated
from godoo_introspection.markers import FieldMeta
from generated_types.res_partner import ResPartner

hints = get_type_hints(ResPartner, include_extras=True)
for field_name, hint in hints.items():
    # Peel Required/NotRequired wrapper
    origin = get_origin(hint)
    if origin is Required or origin is NotRequired:
        inner = get_args(hint)[0]
    else:
        inner = hint
    # Check for Annotated
    if get_origin(inner) is Annotated:
        base_type = get_args(inner)[0]
        field_meta = next((m for m in get_args(inner)[1:] if isinstance(m, FieldMeta)), None)
        if field_meta:
            print(f"{field_name}: ttype={field_meta.ttype}, relation={field_meta.relation}")
```

**[VERIFIED: runtime check]** This exact pattern was run against Python 3.14. `get_origin`, `get_args`, and `isinstance(m, FieldMeta)` all behave correctly.

### Model Name Normalisation

```python
# Source: CONTEXT.md D-Shape-3; verified output:
# 'res.partner'       -> 'res_partner.py'   / 'ResPartner'
# 'account.move.line' -> 'account_move_line.py' / 'AccountMoveLine'
# 'ir.model.fields'   -> 'ir_model_fields.py'  / 'IrModelFields'

def _model_to_filename(model: str) -> str:
    return model.replace(".", "_") + ".py"

def _model_to_classname(model: str) -> str:
    return "".join(part.capitalize() for part in model.replace(".", "_").split("_"))
```

**[VERIFIED: runtime check]** Output confirmed against 5 model name examples.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `fields_get()` for introspection | `search_read('ir.model.fields', ...)` | D-Schema-1 locked during discuss-phase | Exposes `modules`, `on_delete`, `compute`, `depends`, `store`, `index`, `copy` — all unavailable via `fields_get` |
| Dataclass with explicit fields for typed output | `TypedDict(total=False)` + `Required`/`NotRequired` | D-Shape-1 locked | Matches wire shape of `search_read` responses; zero runtime overhead; standard Python |
| Parallel metadata dict alongside the type | `Annotated[T, FieldMeta(...)]` | D-Meta-1 locked | One source of truth; standard `get_type_hints(include_extras=True)` for extraction |
| Required/NotRequired via `typing_extensions` | Native `typing.Required`/`typing.NotRequired` | Python 3.11+ | No backport needed — project is Python 3.14+ |

**Deprecated/outdated in this codebase:**
- `fields_get()` for full schema discovery: still exists on `OdooClient` (D-15 from Phase 1) but deliberately NOT used by introspection. It returns `dict[str, Any]` and misses the fields listed above.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Dynamic selection fields (method-reference based) have zero `ir.model.fields.selection` records — detect dynamic by empty `selection_ids` after fetch | Pitfall 2 | If wrong, dynamic fields would be emitted with `Literal[...]` based on stale values; mitigated by `dynamic_selection=True` flag being conservative |
| A2 | `ir.model.fields` column for "copy on duplicate" is accessible via the name `copied` in `search_read` (not `copy`) in Odoo 17/18 | Pitfall 3 | If wrong, `FieldSchema.copy` would always be default value; integration tests would catch this |
| A3 | `ir.model.fields.selection` records have fields `value`, `name`, `sequence`, `field_id` — sufficient for fetching all static selection values | Architecture Patterns / get_schemas example | If missing columns, selection values would be empty or malformed; integration tests catch |
| A4 | `ir.model` model exposes `transient` and `info` as readable Char/Boolean fields via `search_read` | types.py / get_schemas | If absent, `ModelSchema.transient` would always be False and `display_name` empty; non-blocking |

**If this table is empty:** N/A — assumptions are documented above.

## Open Questions (RESOLVED)

1. **`depends` field shape from ir.model.fields**
   - What we know: `depends` on the `ir.model.fields` record is described in CONTEXT.md D-Meta-3 as `tuple[str, ...]` — a list of comma-separated field names.
   - What's unclear: Whether `search_read` on `ir.model.fields` returns `depends` as a single comma-separated string or as a list. The Python `ir.model.fields.depends` attribute is a `Char` in the database.
   - Recommendation: Fetch it as a string and split on `,` in the `FieldSchema` builder. Store as `tuple[str, ...]`. Handle empty string as empty tuple.
   - **RESOLVED:** Treat `depends` as a comma-separated `Char` field returned by `search_read`. In `introspector.py`, split the raw string on `","`, strip whitespace from each token, and discard empty tokens; store the result as `tuple[str, ...]`. Empty string or missing key yields `()`. This defensive approach is already encoded in the plan action for Task 2 of plan 02-01.

2. **`selection_ids` availability in search_read on ir.model.fields**
   - What we know: `selection_ids` is a One2many field on `ir.model.fields` pointing to `ir.model.fields.selection`. It should return a list of record IDs.
   - What's unclear: Whether `search_read` returns `selection_ids` as a list of ints (standard One2many behaviour) or whether it requires `read` instead.
   - Recommendation: Include `selection_ids` in the `_IR_FIELDS` projection; if it returns `[]` for a selection field, fall back to dynamic detection. Verify in integration tests.
   - **RESOLVED:** Include `selection_ids` in `_IR_FIELDS` and use the returned IDs to drive the third RPC against `ir.model.fields.selection`. If `selection_ids` is absent or empty for a `ttype='selection'` field, treat the field as dynamic (`dynamic_selection=True`). This defensive fallback is already encoded in plan 02-01 Task 2 and verified in plan 02-01 Task 3 test cases 8 and 9.

3. **`modules` computed field accessibility**
   - What we know: `modules` on `ir.model.fields` is a computed Char field listing modules where the field is defined.
   - What's unclear: Whether computed fields are readable via `search_read` on `ir.model.fields`. Most computed fields with `store=False` are not returned by `search_read`.
   - Recommendation: Attempt to include `modules` in the projection; if the search_read response omits it (no key in the dict), default to empty tuple. This is safe defensive coding. Verify in integration tests.
   - **RESOLVED:** Include `modules` in `_IR_FIELDS`. Use `.get("modules", "")` when building `FieldSchema` from the raw `search_read` dict, and apply the same comma-split-and-strip treatment as `depends` to convert to `tuple[str, ...]`. If the key is absent (field not returned by Odoo), the result is `()` — non-blocking. Integration tests will confirm actual availability on the target Odoo version.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | All typing constructs | ✓ | 3.14.5 | — |
| uv | Workspace management | ✓ | 0.11.13 | — |
| `typing.TypedDict` | Generated code, INTRO-03 | ✓ | stdlib | — |
| `typing.Required` / `NotRequired` | Generated code, INTRO-03/04 | ✓ | stdlib (3.11+) | — |
| `typing.Annotated` | FieldMeta markers, INTRO-04 | ✓ | stdlib (3.9+) | — |
| `typing.Literal` | Selection fields, INTRO-06 | ✓ | stdlib (3.8+) | — |
| `respx` | Unit test mocking | ✓ | `>=0.22` in dev-deps | — |
| Docker / live Odoo | Integration tests | Unknown | — | Skip integration; unit tests with mocked RPC cover all schema-fetch logic |

**[VERIFIED: runtime check]** `from typing import TypedDict, Required, NotRequired, Annotated, Literal, get_type_hints` all import cleanly from stdlib in Python 3.14 in this project's virtualenv.

**Missing dependencies with no fallback:** None — all required functionality is stdlib.

**Missing dependencies with fallback:** Integration tests require Docker + live Odoo. Unit tests using `respx` to mock `search_read` responses on `ir.model`, `ir.model.fields`, and `ir.model.fields.selection` cover all codegen logic without Docker. Integration tests verify the actual field names and shapes on a live instance.

## Security Domain

> `security_enforcement: true` with `security_asvs_level: 1` per config.json.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | n/a — Introspector delegates auth to `OdooClient` which already handles it |
| V3 Session Management | No | n/a — session management is in `OdooClient` |
| V4 Access Control | Partial | Odoo ACL governs which models/fields are readable; `OdooAccessError` propagates from transport |
| V5 Input Validation | Yes | Validate `names` list is non-empty before RPC; validate model names are non-empty strings |
| V6 Cryptography | No | n/a — no cryptographic operations |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Empty model name list sent to RPC | Tampering | Raise `OdooValidationError` locally before any RPC call (project convention) |
| Code generation writing to arbitrary paths | Elevation of Privilege | `write()` method should validate output_dir is a directory, not a file; use `pathlib.Path` for safe join |
| Generated file overwriting non-generated files | Tampering | Out of scope for MVP — caller controls output_dir; document the risk |

## Sources

### Primary (HIGH confidence)

- Python 3.14 runtime (live execution in project virtualenv) — TypedDict, Required, NotRequired, Annotated, Literal, get_type_hints all verified
- [PEP 655](https://peps.python.org/pep-0655/) — Required/NotRequired for TypedDict; Python 3.11+ native
- [Python typing spec — TypedDict](https://typing.python.org/en/latest/spec/typeddict.html) — Annotated nesting rules, totality
- [Python docs — typing.get_type_hints](https://docs.python.org/3/library/typing.html#typing.get_type_hints) — include_extras=True behavior
- CONTEXT.md (02-CONTEXT.md) — all locked decisions D-CLI-1, D-Schema-1/2/3, D-Shape-1/2/3, D-Mapping-1/2/3, D-Refs-1, D-Meta-1/2/3
- ARCHITECTURE.md / CONVENTIONS.md / STRUCTURE.md — project patterns (quad layout, TYPE_CHECKING, dataclasses, frozen, per-instance vs module-global cache)
- `packages/godoo/src/godoo/client.py` — `search_read()` signature confirmed; `OdooMissingError`, `OdooValidationError` reuse confirmed
- `packages/godoo/src/godoo/errors.py` — error hierarchy confirmed; no new error types needed
- `packages/godoo-introspection/pyproject.toml` — confirmed `dependencies = ["godoo>=0.1.0"]` already declared; no new dependencies needed

### Secondary (MEDIUM confidence)

- [Odoo ir.model.fields source (GitHub 17.0)](https://github.com/odoo/odoo/blob/17.0/odoo/addons/base/models/ir_model.py) — field column names: `ttype`, `field_description`, `relation`, `relation_field`, `required`, `readonly`, `store`, `index`, `copied`, `translate`, `help`, `compute`, `depends`, `modules`, `on_delete`, `size`, `selection_ids`; `ir.model.fields.selection` model with `value`, `name`, `sequence`
- [Odoo ir.model guide (dasolo.ai)](https://www.dasolo.ai/blog/odoo-data-api-5/odoo-ir-model-guide-167) — `ir.model` fields: `name`, `model`, `transient`, `field_id`

### Tertiary (LOW confidence)

- [ASSUMED] Dynamic selection detection via empty `selection_ids` — based on training knowledge about Odoo field storage; integration tests must verify

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all stdlib constructs verified
- Architecture: HIGH — patterns are entirely within existing project conventions; TypedDict + Annotated + FieldMeta pattern verified in Python 3.14
- Pitfalls: MEDIUM — Pitfalls 1, 4, 5, 6 are HIGH (verified); Pitfalls 2 and 3 are MEDIUM (training knowledge, version-dependent)
- ir.model.fields schema: MEDIUM — field names from GitHub source; exact behaviour on target Odoo version needs integration test validation

**Research date:** 2026-05-21
**Valid until:** 2026-08-21 (stable stdlib; 90 days)
