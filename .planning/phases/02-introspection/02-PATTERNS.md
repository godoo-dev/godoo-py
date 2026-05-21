# Phase 2: Introspection — Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 9 new files (src) + 3 test files
**Analogs found:** 9 / 9

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `src/godoo_introspection/markers.py` | model (frozen dataclass) | transform | `packages/godoo/src/godoo/rpc/types.py` + `safety/__init__.py` | role-match |
| `src/godoo_introspection/types.py` | model (dataclasses) | transform | `packages/godoo/src/godoo/services/cdc/types.py` | exact |
| `src/godoo_introspection/introspector.py` | service + cache | request-response + CRUD | `packages/godoo/src/godoo/services/urls/functions.py` + `services/cdc/field_cache.py` | exact |
| `src/godoo_introspection/type_mapper.py` | utility (pure function) | transform | `packages/godoo/src/godoo/services/cdc/resolver.py` | role-match |
| `src/godoo_introspection/codegen.py` | utility (code generator) | transform + file-I/O | `packages/godoo/src/godoo/services/accounting/functions.py` (string builders) | partial |
| `src/godoo_introspection/__init__.py` | config (barrel export) | — | `packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py` | exact |
| `src/godoo_introspection/py.typed` | config (PEP 561 marker) | — | (empty file — mechanical) | exact |
| `tests/test_introspector.py` | test | request-response (respx mock) | `packages/godoo/tests/test_cdc.py` + `test_urls.py` | exact |
| `tests/test_type_mapper.py` | test | transform (pure unit) | `packages/godoo/tests/test_accounting.py` (pure helper tests) | exact |
| `tests/test_codegen.py` | test | transform (string output) | `packages/godoo/tests/test_accounting.py` (assertion on return values) | role-match |
| `tests/__init__.py` | config | — | `packages/godoo/tests/__init__.py` (empty) | exact |

---

## Pattern Assignments

### `src/godoo_introspection/markers.py` (model, transform)

**Analog:** `packages/godoo/src/godoo/rpc/types.py` (frozen dataclass) and `packages/godoo/src/godoo/safety/__init__.py` (Literal type aliases, frozenset constants)

**Imports pattern** (`rpc/types.py` lines 1-6):
```python
from __future__ import annotations

from dataclasses import dataclass
```

**Frozen dataclass with scalar fields** (`rpc/types.py` lines 8-12):
```python
@dataclass
class OdooSessionInfo:
    uid: int
    session_id: str
    db: str
```

**Literal type alias pattern** (`safety/__init__.py` lines 9-10):
```python
SafetyLevel = Literal["READ", "WRITE", "DELETE"]
```

**Application to `markers.py`:**
- `FieldMeta` is `@dataclass(frozen=True)` with only scalar fields (`str`, `bool`, `int | None`, `tuple[str, ...]`, `tuple[int, int] | None`), making it fully hashable.
- Use `from dataclasses import dataclass` only — no `field()` needed since all defaults are scalars.
- The `ttype: str` attribute is the only required field (no default); all other attributes have project-conventional defaults.
- Module docstring: `"""PEP 593 Annotated metadata marker for generated TypedDict fields."""`
- No `TYPE_CHECKING` import needed — `markers.py` has no cross-package type references.

---

### `src/godoo_introspection/types.py` (model, transform)

**Analog:** `packages/godoo/src/godoo/services/cdc/types.py` (lines 1-66) — multiple dataclasses in one types module, `field(default_factory=...)` for mutable defaults.

**Imports pattern** (`cdc/types.py` lines 1-4):
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
```

**Plain dataclass with mutable default** (`cdc/types.py` lines 49-55):
```python
@dataclass
class GetHistoryOptions:
    field_names: list[str] | None = None
    limit: int | None = None
    since: str | None = None  # ISO date string
```

**Dataclass with `field(default_factory=list)`** (`cdc/types.py` lines 38-42):
```python
@dataclass
class CdcCheckResult:
    model: str
    has_tracking: bool
    tracked_fields: list[str] = field(default_factory=list)
```

**Application to `types.py`:**
- `FieldSchema` — `@dataclass(frozen=True)` is appropriate (all fields are scalars or `list[tuple[str, str]]`; note Pitfall 6: `list` in a frozen dataclass makes it non-hashable, which is acceptable since `FieldSchema` is never used as a dict key).
- `ModelSchema` — use plain `@dataclass` (NOT `frozen=True`) because `fields: dict[str, FieldSchema]` is unhashable (Pitfall 6 in RESEARCH.md). Alternatively use `@dataclass(frozen=True)` and accept non-hashability — the convention note in RESEARCH.md says either approach is fine since `ModelSchema` is not used as a dict key.
- `fields: dict[str, FieldSchema] = field(default_factory=dict)` on `ModelSchema`.
- `selection: list[tuple[str, str]] = field(default_factory=list)` on `FieldSchema`.
- Import `Any` only if needed (not needed for `types.py` which uses only concrete types).

---

### `src/godoo_introspection/introspector.py` (service + cache, request-response + CRUD)

**Analog 1:** `packages/godoo/src/godoo/services/urls/functions.py` — per-client module-level cache with force-refresh bypass, `search_read` calls, `TYPE_CHECKING` import of `OdooClient`.

**Analog 2:** `packages/godoo/src/godoo/services/cdc/field_cache.py` — cache dict, cache miss → RPC fallback pattern.

**Imports pattern** (`urls/functions.py` lines 1-13):
```python
from __future__ import annotations

from typing import TYPE_CHECKING

from godoo.services.urls.types import PortalUrlOptions, PortalUrlResult

if TYPE_CHECKING:
    from godoo.client import OdooClient

# Cache: client id() -> base_url
_base_url_cache: dict[int, str] = {}
```

**Cross-package TYPE_CHECKING import** (the critical pattern for godoo_introspection):
```python
from __future__ import annotations

from typing import TYPE_CHECKING

from godoo_introspection.types import FieldSchema, ModelSchema
from godoo.errors import OdooMissingError, OdooValidationError

if TYPE_CHECKING:
    from godoo.client import OdooClient
```

Note: `OdooMissingError` and `OdooValidationError` are imported at module level (NOT under `TYPE_CHECKING`) because they are raised at runtime, not just referenced in annotations.

**Per-instance cache class — pattern derived from `field_cache.py` (module-global) adapted to instance scope** (`field_cache.py` lines 12-29):
```python
# Module-global pattern (NOT to be copied directly — use per-instance instead):
_cache: dict[str, FieldMeta] = {}

def get_cached(model: str, field_name: str) -> FieldMeta | None:
    return _cache.get(cache_key(model, field_name))

def set_cached(model: str, field_name: str, meta: FieldMeta) -> None:
    _cache[cache_key(model, field_name)] = meta

def clear_cache() -> None:
    _cache.clear()
```

Adapt to per-instance `IntrospectionCache` class with identical method names but `self._cache: dict[str, ModelSchema]` as instance attribute. Expose `invalidate(name)` and `clear()` for test isolation.

**Cache miss → RPC → populate pattern** (`field_cache.py` lines 32-57):
```python
async def fetch_field_meta(client: OdooClient, model: str, field_name: str) -> FieldMeta:
    cached = get_cached(model, field_name)
    if cached is not None:
        return cached
    records = await client.search_read(
        "ir.model.fields",
        [("model", "=", model), ("name", "=", field_name)],
        fields=["name", "ttype", "relation", "selection_ids"],
        limit=1,
    )
    ...
    set_cached(model, field_name, meta)
    return meta
```

**Force-refresh bypass pattern** (`urls/functions.py` lines 16-23):
```python
async def get_base_url(client: OdooClient, *, force_refresh: bool = False) -> str:
    cid = id(client)
    if not force_refresh and cid in _base_url_cache:
        return _base_url_cache[cid]
    records = await client.search_read(
        "ir.config_parameter",
        [("key", "=", "web.base.url")],
        fields=["value"],
        limit=1,
    )
```

Adapt to `bypass_cache: bool = False` keyword argument on `get_schema()` and `get_schemas()`.

**Multi-model batch + cache warm pattern** (from RESEARCH.md code example — no existing analog for multi-model batch in codebase, but follows the `search_read` convention shown in `accounting/functions.py` lines 50-64):
```python
async def discover_cash_accounts(client: OdooClient) -> list[CashAccount]:
    journals = await client.search_read(
        "account.journal",
        [("type", "in", ["cash", "bank"])],
        fields=["id", "name", "code", "company_id"],
    )
    return [CashAccount(id=j["id"], name=j["name"], ...) for j in journals]
```

**Pre-condition validation before RPC** (pattern from `ARCHITECTURE.md` anti-patterns, example in `timesheets/functions.py` — not read, but confirmed by `errors.py` `OdooValidationError` usage):
```python
if not names:
    raise OdooValidationError("get_schemas() called with empty names list")
```

---

### `src/godoo_introspection/type_mapper.py` (utility, transform)

**Analog:** `packages/godoo/src/godoo/services/cdc/resolver.py` — pure functions taking typed inputs, returning typed outputs, no async, no RPC.

The resolver is not read in full but the pattern is clear from test usage in `test_cdc.py` lines 44-91: pure functions like `resolve_values(row, field_type)` taking a dict and returning typed results.

**Pure function module structure** (derived from `accounting/functions.py` helper section, lines 23-42):
```python
"""Type mapper — Odoo ttype to Python type hint strings."""

from __future__ import annotations

from godoo_introspection.types import FieldSchema


def python_type_str(field: FieldSchema) -> str:
    """Return the Python type hint string for embedding in generated code."""
    ...


def _annotated_str(field: FieldSchema, base_type: str) -> str:
    """Wrap base_type in Annotated[..., FieldMeta(...)] string form."""
    ...
```

**Application to `type_mapper.py`:**
- No `TYPE_CHECKING` guard needed — no cross-package class references in annotations.
- Import only `from godoo_introspection.types import FieldSchema` and `import logging`.
- Logger: `logger = logging.getLogger("godoo_introspection.codegen")` (log warning for unmapped ttypes per D-Mapping-3).
- The mapping table is a pure `match`/`if-elif` block — no external config or dict needed.
- No async, no RPC, fully synchronous.

---

### `src/godoo_introspection/codegen.py` (utility, transform + file-I/O)

**Analog:** No direct analog in codebase for code generation as a string builder. Closest structural match is `accounting/functions.py` for the class-with-methods shape, and `container.py` for the class-with-`start()` method that returns a complex result.

**Class-wrapper pattern** (`accounting/service.py` lines 1-62 — read above) — the `CodeGenerator` class follows the same thin-wrapper-over-functions pattern:
```python
class AccountingService:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def discover_cash_accounts(self) -> list[CashAccount]:
        return await discover_cash_accounts(self._client)
```

Adapt: `CodeGenerator` does NOT take `OdooClient` — it takes a `ModelSchema` per-call (or `Introspector` — planner discretion). It is NOT async (code generation is pure string work).

**Logging pattern for warnings** (`container.py` lines 20-21, 125):
```python
logger = logging.getLogger("godoo.testcontainers")
...
logger.error("Odoo container logs:\n%s", logs[-3000:])
```

Adapt: `logger = logging.getLogger("godoo_introspection.codegen")` — use `logger.warning(...)` for unmapped ttypes (D-Mapping-3).

**Application to `codegen.py`:**
```python
from __future__ import annotations

import logging
from pathlib import Path

from godoo_introspection.type_mapper import python_type_str
from godoo_introspection.types import ModelSchema

logger = logging.getLogger("godoo_introspection.codegen")
```

- `generate(schema: ModelSchema) -> str` — returns a valid Python module string.
- `write(schemas: list[ModelSchema], output_dir: Path) -> None` — thin convenience over `generate()`.
- `write()` must validate `output_dir` is a directory before writing (security pattern from RESEARCH.md).
- No `TYPE_CHECKING` guard needed — `ModelSchema` is a runtime import from within the same package.

---

### `src/godoo_introspection/__init__.py` (barrel export)

**Analog:** `packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py` (lines 1-10) — flat barrel with explicit `__all__`.

**Barrel pattern** (testcontainers `__init__.py` lines 1-10):
```python
from godoo_testcontainers.container import OdooTestContainer, StartedOdooContainer
from godoo_testcontainers.seed_resolver import SeedInfo, normalise_odoo_version, resolve_seed_info

__all__ = [
    "OdooTestContainer",
    "SeedInfo",
    "StartedOdooContainer",
    "normalise_odoo_version",
    "resolve_seed_info",
]
```

**Application to `godoo_introspection/__init__.py`:**
```python
from godoo_introspection.codegen import CodeGenerator
from godoo_introspection.introspector import IntrospectionCache, Introspector
from godoo_introspection.markers import FieldMeta
from godoo_introspection.types import FieldSchema, ModelSchema

__all__ = [
    "CodeGenerator",
    "FieldMeta",
    "FieldSchema",
    "IntrospectionCache",
    "Introspector",
    "ModelSchema",
]
```

Note: `from __future__ import annotations` is NOT needed in `__init__.py` files that only contain imports and `__all__` — the testcontainers barrel omits it. Follow that precedent.

---

### `src/godoo_introspection/py.typed` (PEP 561 marker)

**Analog:** Mechanical empty file. Pattern: create an empty `py.typed` file at `src/godoo_introspection/py.typed`. Hatchling auto-includes it via the `packages = ["src/godoo_introspection"]` wheel target already in `pyproject.toml`.

No code pattern needed — it is a zero-byte marker file.

---

### `tests/test_introspector.py` (test, request-response via respx mock)

**Analog:** `packages/godoo/tests/test_cdc.py` (cache tests + multi-respx mock) and `packages/godoo/tests/test_urls.py` (caching + force-refresh tests).

**Module header** (`test_cdc.py` lines 1-14):
```python
"""Tests for the CDC service."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.services.cdc import CdcService, clear_cache, get_cached, set_cached
```

**Auth fixture pattern** (`test_cdc.py` lines 27-36):
```python
@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(2))
        await client.authenticate()
    clear_cache()
    yield client
    await client.aclose()
    clear_cache()
```

Adapt: replace `clear_cache()` calls with `introspector._cache.clear()` (per-instance, not module-global — no module-level cache to reset).

**RPC response helper** (`test_cdc.py` lines 19-21):
```python
def _rpc_response(result, id=1) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})
```

**Single respx.mock test** (`test_cdc.py` lines 117-131):
```python
@respx.mock
@pytest.mark.asyncio
async def test_check_model_has_tracking(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=_rpc_response([{"id": 1, "name": "state"}, ...])
    )
    svc = CdcService(auth_client)
    result = await svc.check("sale.order")
    assert result.has_tracking is True
```

**Caching + call-count verification** (`test_urls.py` lines 64-76):
```python
@respx.mock
@pytest.mark.asyncio
async def test_get_base_url_caching(auth_client):
    route = respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=_rpc_response([{"id": 1, "value": "https://myodoo.com"}])
    )
    svc = UrlService(auth_client)
    url1 = await svc.get_base_url()
    url2 = await svc.get_base_url()
    assert url1 == url2
    assert route.call_count == 1
```

**Multi-RPC mock note:** `Introspector.get_schemas()` fires 2-3 sequential `search_read` calls (ir.model → ir.model.fields → ir.model.fields.selection). The `respx.mock` decorator intercepts all calls to the single `/jsonrpc` endpoint. Use `side_effect` with a list of responses or `respx.route().mock(side_effect=iter([resp1, resp2, resp3]))` to sequence multiple responses. No existing test does this — the planner must document it explicitly in the test plan.

---

### `tests/test_type_mapper.py` (test, pure unit)

**Analog:** `packages/godoo/tests/test_accounting.py` (lines 43-77) — pure synchronous tests on helper functions, no fixtures, no respx.

**Pure function test pattern** (`test_accounting.py` lines 43-65):
```python
def test_m2o_id_list():
    assert _m2o_id([42, "Partner"]) == 42

def test_m2o_id_int():
    assert _m2o_id(7) == 7

def test_m2o_id_false():
    assert _m2o_id(False) is None
```

**Application to `test_type_mapper.py`:**
- No fixtures, no async, no respx.
- Build `FieldSchema` instances inline with minimal required fields.
- Assert on the string returned by `python_type_str(field)`.
- Cover every ttype in the D-Mapping-1 table: `char`, `text`, `html`, `integer`, `float`, `monetary`, `boolean`, `date`, `datetime`, `binary`, `many2one`, `one2many`, `many2many`, `reference`, `selection` (static), `selection` (dynamic, empty selection list), `json`, `properties`, `serialized`, unknown ttype.
- Test `boolean` does NOT include `| Literal[False]`.

---

### `tests/test_codegen.py` (test, transform)

**Analog:** `packages/godoo/tests/test_accounting.py` — assertion on return value shape; no async needed for pure `generate()` calls.

**Application to `test_codegen.py`:**
- `generate(schema)` returns a string — assert it contains the class name, `TypedDict`, `Required[int]` for `id`, `NotRequired[...]` for other fields, `from godoo_introspection.markers import FieldMeta`.
- Test `write()` using `tmp_path` (pytest built-in fixture) — assert the output `.py` file is created with the correct filename.
- Test that the generated string is valid Python via `compile(source, "<string>", "exec")`.
- Test the `__init__.py` barrel generation (re-exports all class names).
- No respx, no auth fixture needed.

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every module in the codebase — e.g., `packages/godoo/src/godoo/services/accounting/functions.py` line 3, `client.py` line 3.
**Apply to:** All `.py` source files in `src/godoo_introspection/` and all test files.
**Exception:** `__init__.py` barrel files that only import and define `__all__` — the testcontainers `__init__.py` omits it and that is the model to follow.

### `TYPE_CHECKING` import guard for `OdooClient`
**Source:** `packages/godoo/src/godoo/services/accounting/functions.py` lines 16-17 and `packages/godoo/src/godoo/services/cdc/field_cache.py` lines 9-10:
```python
if TYPE_CHECKING:
    from godoo.client import OdooClient
```
**Apply to:** `introspector.py` only — the only module in `godoo_introspection` that references `OdooClient` in a type annotation. All other modules (`markers.py`, `types.py`, `type_mapper.py`, `codegen.py`) have no `OdooClient` reference.

### Module-level logger
**Source:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` line 20:
```python
logger = logging.getLogger("godoo.testcontainers")
```
**Apply to:** `codegen.py` with `logger = logging.getLogger("godoo_introspection.codegen")`. Use `%s`-style format strings (not f-strings) in all log calls.

### Precondition validation before RPC
**Source:** `packages/godoo/src/godoo/errors.py` `OdooValidationError` — raised locally before any RPC (established project pattern from ARCHITECTURE.md).
**Apply to:** `Introspector.get_schemas()` — validate `names` is non-empty before issuing any `search_read` call.

### `search_read` call convention
**Source:** `packages/godoo/src/godoo/services/accounting/functions.py` lines 50-55:
```python
journals = await client.search_read(
    "account.journal",
    [("type", "in", ["cash", "bank"])],
    fields=["id", "name", "code", "company_id"],
)
```
**Apply to:** All three `search_read` calls in `Introspector.get_schemas()` (`ir.model`, `ir.model.fields`, `ir.model.fields.selection`). Always pass `fields=` as keyword argument. Use `[("model", "in", names)]` domain for multi-model batch.

### Error reuse (no new error types)
**Source:** `packages/godoo/src/godoo/errors.py` — `OdooMissingError` (line 100) and `OdooValidationError` (line 82).
**Apply to:** `introspector.py` raises `OdooMissingError` when a requested model is not in `ir.model` (mirrors `client.ref()` D-16 from Phase 1). Raises `OdooValidationError` for empty `names` list input. No new error classes in `godoo_introspection`.

### Dataclass `field()` for mutable defaults
**Source:** `packages/godoo/src/godoo/services/cdc/types.py` lines 39-42:
```python
tracked_fields: list[str] = field(default_factory=list)
```
**Apply to:** `FieldSchema.selection: list[tuple[str, str]] = field(default_factory=list)` and `ModelSchema.fields: dict[str, FieldSchema] = field(default_factory=dict)`.

### Test file structure (respx mock + auth fixture)
**Source:** `packages/godoo/tests/test_cdc.py` lines 1-36 — module docstring, `__future__` import, `BASE_URL`/`DB` constants, `_rpc_response()` helper, `_make_client()` helper, `auth_client` async fixture with yield and cleanup.
**Apply to:** `tests/test_introspector.py` — copy this exact structure, replacing CDC-specific imports with `godoo_introspection` imports.

---

## No Analog Found

All files have analogs. The `codegen.py` string-generation logic has no close analog (no existing code generator in the codebase), but its class/module structure follows the service/function conventions exactly. The RESEARCH.md `CodeGenerator` pattern section covers the implementation specifics.

| File | Role | Data Flow | Note |
|------|------|-----------|------|
| (none) | — | — | — |

---

## Metadata

**Analog search scope:** `packages/godoo/src/godoo/` (all services, rpc, safety, errors, client), `packages/godoo-testcontainers/src/`, `packages/godoo/tests/`
**Files scanned:** 14 source files + 14 test files
**Pattern extraction date:** 2026-05-21
