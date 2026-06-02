# Phase 10: Typed Relation Resolution - Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 5 (3 modified, 2 test files — 1 modified, 1 new)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/godoo-client/src/godoo/client/typed.py` | model/primitive | transform | self (frozen dataclass gains field) | exact |
| `packages/godoo-client/src/godoo/client/_pydantic_transform.py` | transform/utility | transform | self (`_annotation_mentions_ref` extended) | exact |
| `packages/godoo-client/src/godoo/client/client.py` | client/dispatcher | request-response (batched) | self (existing `@overload read()` block) | exact |
| `packages/godoo-client/tests/test_typed_dispatch.py` | test | request-response | self (TEST-02 wire-fidelity extension) | exact |
| `packages/godoo-client/tests/test_rel_resolution.py` | test | request-response | `packages/godoo-client/tests/test_typed_dispatch.py` | role-match |

---

## Pattern Assignments

### `packages/godoo-client/src/godoo/client/typed.py` (model/primitive, transform)

**Analog:** self — additive change to the `Ref[T]` frozen dataclass.

**Current `Ref[T]` definition** (lines 22–34):
```python
@dataclass(frozen=True)
class Ref[T]:
    """Typed many2one reference: numeric id + display name.

    ``name`` is ``str | None`` to handle restricted display names — Odoo
    returns ``[id, False]`` when the current user cannot read the related
    record's display name. The wire transform sets ``name=None`` in that case.
    """

    id: int
    name: str | None
```

**Pattern to apply — add `_target_cls` field after `name`:**
```python
from dataclasses import dataclass, field   # field is new import

@dataclass(frozen=True)
class Ref[T]:
    id: int
    name: str | None
    _target_cls: type | None = field(default=None, compare=False, hash=False, repr=False)
```

Key points:
- `compare=False, hash=False` — preserves existing equality and hash semantics (SC-4).
- `repr=False` — keeps `Ref(id=42, name='X')` repr clean.
- `field(default=None, ...)` pattern is already used throughout the codebase (e.g. `OdooClientConfig.safety`, `OdooClientConfig.timeout`).
- The existing `__all__ = ["OdooModel", "Ref"]` stays unchanged.

---

### `packages/godoo-client/src/godoo/client/_pydantic_transform.py` (transform/utility, transform)

**Analog:** self — two injection points.

**Injection point 1 — `_annotation_mentions_ref()` extension** (lines 38–49):

Current function returns `bool`. Must be extended (or a sibling helper added) to also extract the type arg. The `get_args()` import is already present at line 11:
```python
from typing import Any, ClassVar, get_args, get_origin
```

New sibling helper pattern (preferred over mutating `_annotation_mentions_ref` return type to avoid breaking existing callers):
```python
def _ref_target_class(annotation: Any) -> type | None:
    """Return the T in Ref[T] if annotation mentions Ref, else None.

    Mirrors _annotation_mentions_ref logic but extracts the type arg.
    Returns None for bare Ref, Ref[object], or when Ref is not present.
    """
    origin = get_origin(annotation)
    if origin is Ref:
        args = get_args(annotation)
        return args[0] if args and isinstance(args[0], type) else None
    for arg in get_args(annotation):
        if get_origin(arg) is Ref:
            inner = get_args(arg)
            return inner[0] if inner and isinstance(inner[0], type) else None
        if get_args(arg):
            result = _ref_target_class(arg)
            if result is not None:
                return result
    return None
```

**Injection point 2 — m2o tuple → `Ref` conversion** (lines 129–138):

Current code:
```python
if (
    isinstance(value, list)
    and len(value) == 2
    and isinstance(value[0], int)
    and (isinstance(value[1], str) or value[1] is False)
    and _annotation_mentions_ref(annotation)
):
    out[name] = Ref(id=value[0], name=None if value[1] is False else value[1])
    continue
```

Pattern to apply — pass `_target_cls` via the new helper:
```python
if (
    isinstance(value, list)
    and len(value) == 2
    and isinstance(value[0], int)
    and (isinstance(value[1], str) or value[1] is False)
    and _annotation_mentions_ref(annotation)
):
    out[name] = Ref(
        id=value[0],
        name=None if value[1] is False else value[1],
        _target_cls=_ref_target_class(annotation),   # new kwarg
    )
    continue
```

The rest of `_odoo_wire_transforms` is UNCHANGED — additive only.

---

### `packages/godoo-client/src/godoo/client/client.py` (client/dispatcher, request-response/batched)

**Analog:** self — existing `@overload read()` block plus new `Ref` dispatch branch.

**Current imports block** (lines 1–21) — new items to add:
```python
from godoo.client.typed import OdooModel, Ref   # Ref added; OdooModel already there
```
`Ref` is in `godoo.client.typed` (stdlib-only, safe at module level — same as `OdooModel`).

**Existing TypeVar** (line 39):
```python
T = TypeVar("T", bound=OdooModel)
```
The new overloads reuse this same `T`.

**Existing `@overload` pattern** (lines 192–244) — copy signature style for new Ref overloads:
```python
@overload
async def read(
    self,
    model: type[T],
    ids: int | list[int],
    fields: list[str] | None = None,
    **kwargs: Any,
) -> list[T]: ...

@overload
async def read(
    self,
    model: str,
    ids: int | list[int],
    fields: list[str] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]: ...
```

**New overloads to add BEFORE the existing ones** (D-01):
```python
@overload
async def read(self, ref: Ref[T]) -> T: ...

@overload
async def read(self, refs: list[Ref[T]]) -> list[T]: ...
```

**Runtime dispatch — new branch to add at the top of `read()` body**, before the existing `hasattr(model, "__odoo_model__")` branch:

Pattern derived from the existing typed-dispatch branch (lines 220–239):
```python
# Ref / list[Ref] dispatch — D-01, D-02, D-03
if isinstance(model, Ref) or (isinstance(model, list) and model and isinstance(model[0], Ref)):
    # Collect refs, validate all up front (D-03)
    refs: list[Ref[Any]] = [model] if isinstance(model, Ref) else list(model)
    bad = [r for r in refs if r._target_cls is None]
    if bad:
        ids_str = ", ".join(str(r.id) for r in bad)
        raise OdooValidationError(
            f"Cannot resolve Ref(id={bad[0].id}): no target model known"
            f" — it came from an untyped many2one field."
        )
    # Group by target class, preserving order (D-02)
    from collections import defaultdict
    groups: dict[type[Any], list[int]] = defaultdict(list)
    for r in refs:
        assert r._target_cls is not None
        if r.id not in groups[r._target_cls]:
            groups[r._target_cls].append(r.id)
    # Fire one read() per distinct target model (batched)
    fetched: dict[tuple[type[Any], int], Any] = {}
    for target_cls, target_ids in groups.items():
        results = await self.read(target_cls, target_ids)
        for record in results:
            fetched[(target_cls, record.id)] = record
    # Stitch back in input order
    ordered = [fetched[(r._target_cls, r.id)] for r in refs]  # type: ignore[index]
    if isinstance(model, Ref):
        return ordered[0]   # type: ignore[return-value]
    return ordered          # type: ignore[return-value]
```

Note: the lazy `from godoo.client._pydantic_transform import ...` pattern (D-04) is already established in the typed branch (line 222); the Ref branch does NOT need this import because it calls `self.read(target_cls, ids)` recursively, which already handles it.

**Existing validation error pattern** (line 235) — copy directly for the untyped-ref guard:
```python
raise OdooValidationError(str(exc)) from exc
```

**Existing `except OdooRpcError` blocks** — the new branch fires before them; none are touched.

---

### `packages/godoo-client/tests/test_typed_dispatch.py` (test, request-response)

**Analog:** self — TEST-02 wire-fidelity additions extend this file.

**Existing fixture pattern** (lines 33–39) — reuse `auth_client` as-is:
```python
@pytest.fixture
async def auth_client() -> AsyncGenerator[OdooClient]:
    c = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await c.authenticate()
    yield c
```

**Model fixture to extend** — add a `Ref`-typed field to `TinyPartner` (lines 47–52):
```python
class TinyPartner(OdooBaseModel):
    __odoo_model__: ClassVar[str] = "res.partner"
    id: int
    name: str | None = None
    # Add for TEST-02:
    parent_id: Ref[TinyPartner] | None = None
```

**New test function structure** — follow existing `@respx.mock + @pytest.mark.asyncio` style (lines 60–70):
```python
@respx.mock
@pytest.mark.asyncio
async def test_read_typed_ref_field_populated(auth_client: OdooClient) -> None:
    """Ref-typed field is populated with _target_cls via wire transform (TEST-02)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "parent_id": [3, "Acme"]}]))
    )
    result = await auth_client.read(TinyPartner, [1])
    assert result[0].parent_id is not None
    assert result[0].parent_id.id == 3
    assert result[0].parent_id._target_cls is TinyPartner
```

---

### `packages/godoo-client/tests/test_rel_resolution.py` (test, request-response/batched) — NEW FILE

**Analog:** `packages/godoo-client/tests/test_typed_dispatch.py` — copy entire scaffold.

**File header pattern** (lines 1–19 of `test_typed_dispatch.py`):
```python
"""<docstring describing scope>"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import httpx
import pytest
import respx
from godoo.client._pydantic_transform import OdooBaseModel
from godoo.client.client import OdooClient, OdooClientConfig
from godoo.client.errors import OdooValidationError
from godoo.client.typed import Ref

BASE_URL = "http://odoo.test"
DB = "testdb"
```

**Helper + fixture pattern** (lines 23–39 of `test_typed_dispatch.py`) — copy verbatim:
```python
def _jsonrpc_result(result: object) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": 1, "result": result}

def _make_config(**kwargs: object) -> OdooClientConfig:
    defaults: dict[str, object] = dict(url=BASE_URL, database=DB, username="admin", password="admin")
    defaults.update(kwargs)
    return OdooClientConfig(**defaults)  # type: ignore[arg-type]

@pytest.fixture
async def auth_client() -> AsyncGenerator[OdooClient]:
    c = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await c.authenticate()
    yield c
```

**Model fixtures** — two typed models for cross-model tests:
```python
class TinyPartner(OdooBaseModel):
    __odoo_model__: ClassVar[str] = "res.partner"
    id: int
    name: str | None = None

class TinyMove(OdooBaseModel):
    __odoo_model__: ClassVar[str] = "account.move"
    id: int
    name: str | None = None
```

**Test function patterns** — four behavior areas (D-01..D-03, order preservation):

1. `read(ref)` single-ref resolution — one RPC call:
```python
@respx.mock
@pytest.mark.asyncio
async def test_read_single_ref_resolves(auth_client: OdooClient) -> None:
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 42, "name": "Acme"}]))
    )
    ref: Ref[TinyPartner] = Ref(id=42, name="Acme", _target_cls=TinyPartner)
    result = await auth_client.read(ref)
    assert isinstance(result, TinyPartner)
    assert result.id == 42
```

2. `read([ref_a, ref_b])` same-model list:
```python
@respx.mock
@pytest.mark.asyncio
async def test_read_homogeneous_list_resolves(auth_client: OdooClient) -> None:
    ...
```

3. `read([ref_partner, ref_move])` mixed-model list — two RPC calls, order preserved:
```python
@respx.mock
@pytest.mark.asyncio
async def test_read_heterogeneous_list_preserves_order(auth_client: OdooClient) -> None:
    # Two separate mock calls needed; use side_effect list pattern from respx
    ...
```

4. Untyped-ref guard raises `OdooValidationError` before any RPC (D-03):
```python
@respx.mock
@pytest.mark.asyncio
async def test_read_untyped_ref_raises_before_rpc(auth_client: OdooClient) -> None:
    untyped: Ref[int] = Ref(id=42, name="X")   # _target_cls=None
    with pytest.raises(OdooValidationError, match="no target model known"):
        await auth_client.read(untyped)
    # Verify no RPC was made
    assert not respx.calls
```

**Side-effect pattern for multiple sequential mocks** (from `test_typed_dispatch.py` lines 178–185):
```python
responses = iter([
    httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Partner"}])),
    httpx.Response(200, json=_jsonrpc_result([{"id": 7, "name": "Move"}])),
])
respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=lambda req, route: next(responses))
```

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every file in `packages/godoo-client/src/godoo/`
**Apply to:** All modified and new files — first line of every module.

### `TYPE_CHECKING` guard for circular-import-prone types
**Source:** `client.py` lines 22–34
```python
if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from godoo.client.rpc.protocol import Transport
    ...
```
**Apply to:** Any new type annotation that would create an import cycle. `Ref` is in `typed.py` (stdlib-only), safe at module level — no guard needed for it.

### Lazy pydantic import (D-04)
**Source:** `client.py` lines 221–225
```python
try:
    from godoo.client._pydantic_transform import derive_partial_model
except ModuleNotFoundError as exc:
    raise OdooValidationError(
        "Typed reads require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
    ) from exc
```
**Apply to:** Any new branch in `client.py` that calls into `_pydantic_transform`. The Ref dispatch branch calls `self.read(target_cls, ids)` recursively — the lazy import guard fires in the recursive call's typed branch, not in the Ref branch itself.

### `OdooValidationError` for domain preconditions
**Source:** `client.py` lines 235, 399, 461; `errors.py` line 146
```python
raise OdooValidationError(f"<human-readable message>") from exc
```
**Apply to:** The untyped-ref fail-fast guard in the new Ref dispatch branch. Raise BEFORE any `self.call()` (atomic — no partial side effects).

### `@overload` signature style
**Source:** `client.py` lines 192–208 (existing `read` overloads)
```python
@overload
async def read(
    self,
    model: type[T],
    ids: int | list[int],
    fields: list[str] | None = None,
    **kwargs: Any,
) -> list[T]: ...
```
**Apply to:** New `Ref[T]` / `list[Ref[T]]` overloads for `read()`. Keep `@overload` lines adjacent, implementation body last.

### `field(default=None, compare=False, hash=False, repr=False)` dataclass field
**Source:** `client.py` line 90–92 (`OdooClientConfig.safety`); dataclass convention throughout
```python
safety: SafetyContext | None = field(default=None)
```
**Apply to:** `_target_cls` field on `Ref` — matches the "excluded from equality + hash + repr" need perfectly.

### Test file scaffold
**Source:** `test_typed_dispatch.py` lines 1–39
```python
"""..."""
from __future__ import annotations
# ... imports ...
BASE_URL = "http://odoo.test"
DB = "testdb"
def _jsonrpc_result(...): ...
def _make_config(...): ...
@pytest.fixture
async def auth_client(): ...
```
**Apply to:** `test_rel_resolution.py` — copy scaffold verbatim, change docstring.

### `@respx.mock` + `@pytest.mark.asyncio` test decorator order
**Source:** `test_typed_dispatch.py` lines 60–61
```python
@respx.mock
@pytest.mark.asyncio
async def test_...(auth_client: OdooClient) -> None:
```
**Apply to:** All async test functions in both test files.

### `setup_function` / cache clearing before tests
**Source:** `test_pydantic_transform.py` lines 33–35
```python
def setup_function(_fn: object) -> None:
    """Clear partial-model cache before each test to prevent state leakage."""
    clear_partial_model_cache()
```
**Apply to:** `test_rel_resolution.py` if tests use `derive_partial_model` indirectly. Not required for pure Ref-resolution tests.

---

## No Analog Found

None — all files have direct analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `packages/godoo-client/src/godoo/client/`, `packages/godoo-client/tests/`
**Files read:** 7 source files, 3 test files
**Pattern extraction date:** 2026-06-02
