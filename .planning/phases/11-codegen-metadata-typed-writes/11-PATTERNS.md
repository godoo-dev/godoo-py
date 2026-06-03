# Phase 11: Codegen Metadata + Typed Writes - Pattern Map

**Mapped:** 2026-06-03
**Files analyzed:** 6 (4 modified, 1 new function in existing file, 1 new test file)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` | utility/transform | transform | self (current 3-tuple; widen to 4-tuple) | self-extension |
| `packages/godoo-introspection/src/godoo/introspection/codegen.py` | utility/emitter | transform | self (current unpack + field assembly; conditional Field() emit) | self-extension |
| `packages/godoo-client/src/godoo/client/_pydantic_transform.py` | utility/transform | transform | `_odoo_wire_transforms` in same file (read-direction mirror) | exact |
| `packages/godoo-client/src/godoo/client/client.py` | service/facade | request-response | Phase 10 `read()` overload block (lines 212–316) | exact |
| `packages/godoo-introspection/tests/test_type_mapper.py` | test | transform | self (3-tuple unpack pattern; widen all unpacks to 4-tuple) | self-extension |
| `packages/godoo-client/tests/test_typed_writes.py` | test | request-response | `test_typed_dispatch.py` + `test_rel_resolution.py` | exact |

---

## Pattern Assignments

### `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` (utility, transform)

**Analog:** self — current file; GEN-01 widens the return tuple from 3 to 4 elements.

**Current signature** (`type_mapper.py` lines 25–29):
```python
def pydantic_field_str(
    field: FieldSchema,
    in_set: frozenset[str],
    classname_fn: Callable[[str], str],
) -> tuple[str, str, frozenset[str]]:
```

**New signature** (4-tuple):
```python
def pydantic_field_str(
    field: FieldSchema,
    in_set: frozenset[str],
    classname_fn: Callable[[str], str],
) -> tuple[str, str, frozenset[str], dict[str, bool]]:
```

**Metadata emission rule** — compute `extra_dict: dict[str, bool]` at the start of the function body before the ttype dispatch, then include it in every return:

```python
# Compute metadata once — all FieldSchema attributes already present (types.py lines 22-29)
extra: dict[str, bool] = {}
if field.readonly or (not field.store and field.compute is not None):
    extra["odoo_readonly"] = True
if field.ttype in ("one2many", "many2many"):
    extra["odoo_x2many"] = True
```

**Every existing `return` statement** gets `extra` appended as the 4th element:
```python
# Before (example, line 53):
return ("Optional[str]", "None", frozenset())
# After:
return ("Optional[str]", "None", frozenset(), extra)
```

**FieldSchema source fields** (`types.py` lines 22, 23, 28):
```python
readonly: bool = False      # line 22
store: bool = True          # line 23
compute: str | None = None  # line 28 — present in current FieldSchema, no new introspection needed
```

---

### `packages/godoo-introspection/src/godoo/introspection/codegen.py` (utility/emitter, transform)

**Analog:** self — existing field-assembly loop (lines 122–155) and header-assembly block (lines 157–220).

**Unpack update** (line 139 — the only caller of `pydantic_field_str`):
```python
# Before (line 139):
annotation, default, imports = pydantic_field_str(fs, self._in_set, _model_to_classname)
field_lines.append(f"    {field_name}: {annotation} = {default}")

# After:
annotation, default, imports, extra = pydantic_field_str(fs, self._in_set, _model_to_classname)
if extra:
    if default == "[]":
        default_expr = f"Field(default_factory=list, json_schema_extra={extra!r})"
    else:
        default_expr = f"Field(default={default}, json_schema_extra={extra!r})"
    need_field_import = True
else:
    default_expr = default
field_lines.append(f"    {field_name}: {annotation} = {default_expr}")
```

**`need_field_import` flag** — initialize at the top of `generate()` alongside the existing bool flags (lines 111–116):
```python
# Add alongside existing flags:
need_field_import = False   # set to True when any field carries extra metadata
```

**Header import injection** — insert after the `from godoo.client._pydantic_transform import OdooBaseModel` line (line 190) using the same conditional pattern as `need_ref` (lines 191–192):
```python
# Existing pattern to mirror (lines 191-192):
if need_ref:
    lines.append("from godoo.client.typed import Ref")

# New — insert immediately after:
if need_field_import:
    lines.append("from pydantic import Field")
```

**Mutable-default pitfall guard** — when `extra` is non-empty AND `default == "[]"`, the codegen must emit `Field(default_factory=list, ...)` not `Field(default=[], ...)`. Pydantic v2 rejects mutable defaults with `PydanticUserError`. The conditional `if default == "[]"` branch above handles this.

---

### `packages/godoo-client/src/godoo/client/_pydantic_transform.py` (utility/transform, transform)

**Analog:** `_odoo_wire_transforms` in the same file (lines 125–188) — the read-direction transform. The write serializer is its mirror: same per-field iteration logic, reverse value conversions.

**Module-level lazy-import rule** (line 1–6 module docstring): NEVER import this module at top of any other `godoo.client` submodule. Add `_serialize_for_write` here; it is already the only module that imports pydantic.

**Import additions** needed at top of file (add to existing imports at lines 8–15):
```python
# Already present — no additions needed for the serializer itself.
# from datetime import date, datetime  ← already line 10
# from typing import Any, ...          ← already line 11
# from godoo.client.typed import Ref   ← already line 14
# Lazy import of OdooValidationError inside the function body (same pattern as client.py dispatch)
```

**New function** — add after `clear_partial_model_cache()` (after line 246), following the same section-separator style:

```python
# ------------------------------------------------------------------
# Write serializer (mirror of _odoo_wire_transforms)
# ------------------------------------------------------------------


def _serialize_for_write(instance: OdooBaseModel) -> dict[str, Any]:
    """Serialize an OdooBaseModel instance to an Odoo write payload.

    Only fields in model_fields_set are included. Readonly fields
    (json_schema_extra odoo_readonly=True) are excluded. x2many fields
    (odoo_x2many=True) in the set raise OdooValidationError. Transformations:
      Ref  -> int (bare id)
      None -> False (Odoo wire convention for cleared fields)
      date/datetime -> ISO-format string
    """
    from godoo.client.errors import OdooValidationError  # lazy: avoids circular at module load

    payload: dict[str, Any] = {}
    for field_name in instance.model_fields_set:
        fi = instance.__class__.model_fields.get(field_name)
        if fi is None:
            continue
        extra = fi.json_schema_extra
        extra_dict: dict[str, object] = extra if isinstance(extra, dict) else {}

        # WRITE-04: skip readonly/computed fields unconditionally
        if extra_dict.get("odoo_readonly"):
            continue

        # WRITE-05: raise on x2many before any RPC
        if extra_dict.get("odoo_x2many"):
            raise OdooValidationError(
                f"Field {field_name!r} is an x2many relation and cannot be written via the "
                "typed path. Use client.write(model, ids, {field: [(6, 0, [ids])]}) with "
                "command tuples instead."
            )

        value = getattr(instance, field_name)

        # Ref -> bare int id
        if isinstance(value, Ref):
            payload[field_name] = value.id
            continue

        # None (explicitly set) -> Odoo False
        if value is None:
            payload[field_name] = False
            continue

        # datetime BEFORE date (datetime subclasses date — order matters, mirrors read-side)
        if isinstance(value, datetime):
            payload[field_name] = value.isoformat()
            continue
        if isinstance(value, date):
            payload[field_name] = value.isoformat()
            continue

        payload[field_name] = value

    return payload
```

**Key: `model_fields_set` is the ONLY correct iteration target.** Never call `instance.model_dump()` — it returns ALL fields including unset defaults, which would overwrite Odoo DB values with `None`/`False`.

---

### `packages/godoo-client/src/godoo/client/client.py` (facade, request-response)

**Analog:** Phase 10 `read()` overload block (lines 212–316) — same additive-overload pattern, same lazy-import dispatch guard, same `OdooValidationError` install-hint wrap.

**Import additions** — none needed at module level. The existing top-level imports already cover `overload`, `cast`, `Any`, `OdooValidationError` (line 13).

**Existing `create` signatures** (lines 512–534) to replace with overload block:
```python
# Current (lines 512-534):
@overload
async def create(self, model: str, values: dict[str, Any], **kwargs: Any) -> int: ...

@overload
async def create(self, model: str, values: list[dict[str, Any]], **kwargs: Any) -> list[int]: ...

async def create(
    self,
    model: str,
    values: dict[str, Any] | list[dict[str, Any]],
    **kwargs: Any,
) -> int | list[int]:
    ...body unchanged...
```

**New `create` overload block** (replace the above entirely):
```python
@overload
async def create(self, instance: OdooBaseModel) -> int: ...

@overload
async def create(self, model: str, values: dict[str, Any], **kwargs: Any) -> int: ...

@overload
async def create(self, model: str, values: list[dict[str, Any]], **kwargs: Any) -> list[int]: ...

async def create(  # type: ignore[misc]
    self,
    model: Any,
    values: Any = None,
    **kwargs: Any,
) -> int | list[int]:
    """Create one or more records.

    Typed path: pass an OdooBaseModel instance — returns new record id (int).
    Dict path: pass model str + single dict → int; list of dicts → list[int].
    Raises OdooValidationError locally if the list is empty (no RPC call made).
    """
    # Typed dispatch — duck-typed guard; never imports pydantic at module level (D-04)
    if hasattr(model, "__odoo_model__"):
        try:
            from godoo.client._pydantic_transform import _serialize_for_write
        except ModuleNotFoundError as exc:
            raise OdooValidationError(
                "Typed writes require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
            ) from exc
        payload = _serialize_for_write(model)
        return cast("int", await self.call(model.__odoo_model__, "create", [payload], kwargs))
    # Dict path — unchanged from v1.0
    if isinstance(values, list):
        if not values:
            raise OdooValidationError("Cannot create with empty list of values")
        return cast("list[int]", await self.call(model, "create", [values], kwargs))
    return cast("int", await self.call(model, "create", [values], kwargs))
```

**OdooBaseModel import for overload type annotation** — `OdooBaseModel` is pydantic-dependent; the `@overload` stub references it only as an annotation. With `from __future__ import annotations` all annotations are strings at runtime, so this is safe to place under `TYPE_CHECKING`:
```python
# In the TYPE_CHECKING block (lines 23–34), add:
if TYPE_CHECKING:
    from godoo.client._pydantic_transform import OdooBaseModel
```

**Existing `write` signature** (lines 536–545 — currently has NO overloads):
```python
# Current (lines 536-545):
async def write(
    self,
    model: str,
    ids: int | list[int],
    values: dict[str, Any],
    **kwargs: Any,
) -> bool:
    if isinstance(ids, int):
        ids = [ids]
    return cast("bool", await self.call(model, "write", [ids, values], kwargs))
```

**New `write` overload block** (replace the above entirely):
```python
@overload
async def write(self, instance: OdooBaseModel) -> bool: ...

@overload
async def write(
    self,
    model: str,
    ids: int | list[int],
    values: dict[str, Any],
    **kwargs: Any,
) -> bool: ...

async def write(  # type: ignore[misc]
    self,
    model: Any,
    ids: Any = None,
    values: Any = None,
    **kwargs: Any,
) -> bool:
    # Typed dispatch — duck-typed guard; never imports pydantic at module level (D-04)
    if hasattr(model, "__odoo_model__"):
        if model.id is None:
            raise OdooValidationError(
                f"Cannot write {model.__odoo_model__!r}: instance.id is None "
                "(record not yet created)."
            )
        try:
            from godoo.client._pydantic_transform import _serialize_for_write
        except ModuleNotFoundError as exc:
            raise OdooValidationError(
                "Typed writes require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
            ) from exc
        payload = _serialize_for_write(model)
        return cast("bool", await self.call(model.__odoo_model__, "write", [[model.id], payload], kwargs))
    # Dict path — unchanged from v1.0
    if isinstance(ids, int):
        ids = [ids]
    return cast("bool", await self.call(model, "write", [ids, values], kwargs))
```

**`# type: ignore[misc]`** — required on the implementation `def` line when multiple `@overload` stubs exist; matches the existing `read()` pattern at line 236.

---

### `packages/godoo-introspection/tests/test_type_mapper.py` (test, transform)

**Analog:** self — all existing tests unpack a 3-tuple; every test must be updated to a 4-tuple unpack.

**Current unpack pattern** (representative, line 26):
```python
ann, default, imports = pydantic_field_str(_field("char"), frozenset(), _fn)
```

**New unpack pattern** (all ~20 tests):
```python
ann, default, imports, extra = pydantic_field_str(_field("char"), frozenset(), _fn)
```

**New test cases** to add for GEN-01 metadata:
```python
def _field_ro(ttype: str, **kwargs: object) -> FieldSchema:
    """Build a FieldSchema with readonly=True."""
    return FieldSchema(name="f", ttype=ttype, readonly=True, **kwargs)  # type: ignore[arg-type]


def _field_computed_nonstored(ttype: str) -> FieldSchema:
    """Build a computed non-stored FieldSchema (D-03 rule)."""
    return FieldSchema(name="f", ttype=ttype, store=False, compute="_compute_f")


def test_readonly_field_emits_odoo_readonly_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field_ro("char"), frozenset(), _fn)
    assert extra == {"odoo_readonly": True}


def test_computed_nonstored_emits_odoo_readonly_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field_computed_nonstored("float"), frozenset(), _fn)
    assert extra == {"odoo_readonly": True}


def test_nonstored_without_compute_no_metadata() -> None:
    """Non-stored field without compute is NOT marked readonly (D-04 refinement)."""
    f = FieldSchema(name="f", ttype="char", store=False, compute=None)
    _, _, _, extra = pydantic_field_str(f, frozenset(), _fn)
    assert "odoo_readonly" not in extra


def test_one2many_emits_odoo_x2many_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field("one2many"), frozenset(), _fn)
    assert extra.get("odoo_x2many") is True


def test_many2many_emits_odoo_x2many_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field("many2many"), frozenset(), _fn)
    assert extra.get("odoo_x2many") is True


def test_plain_writable_field_no_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field("char"), frozenset(), _fn)
    assert extra == {}


def test_readonly_x2many_emits_both_flags() -> None:
    f = FieldSchema(name="f", ttype="one2many", readonly=True)
    _, _, _, extra = pydantic_field_str(f, frozenset(), _fn)
    assert extra.get("odoo_readonly") is True
    assert extra.get("odoo_x2many") is True
```

---

### `packages/godoo-client/tests/test_typed_writes.py` (test, request-response)

**Analog:** `test_typed_dispatch.py` (respx auth_client fixture + `_jsonrpc_result` helper + `@respx.mock` decorator pattern) and `test_rel_resolution.py` (same fixture structure, multi-call patterns).

**Boilerplate** — copy verbatim from `test_typed_dispatch.py` lines 1–41:
```python
"""Typed create/write dispatch tests (WRITE-01..05 + TEST-01 unit)."""

from __future__ import annotations

import json
import sys
from typing import ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import httpx
import pytest
import respx
from godoo.client._pydantic_transform import OdooBaseModel
from godoo.client.client import OdooClient, OdooClientConfig
from godoo.client.errors import OdooValidationError
from pydantic import Field

BASE_URL = "http://odoo.test"
DB = "testdb"


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

**Model fixtures** — inline test models with GEN-01 metadata:
```python
class WritePartner(OdooBaseModel):
    """Minimal model with metadata-bearing fields for write tests."""
    __odoo_model__: ClassVar[str] = "res.partner"
    id: int
    name: str | None = None
    comment: str | None = None
    state: str | None = Field(default=None, json_schema_extra={"odoo_readonly": True})
    line_ids: list[int] = Field(default_factory=list, json_schema_extra={"odoo_x2many": True})
```

**Payload inspection helper** — copy `_extract_rpc_fields` from `test_typed_dispatch.py` lines 158–172, generalised to extract the write payload:
```python
def _extract_rpc_write_payload(request: httpx.Request) -> dict[str, object] | None:
    """Extract the values dict from a JSON-RPC write/create call body."""
    body = json.loads(request.content)
    rpc_args: list[object] = body.get("params", {}).get("args", [])
    # execute_kw args: [db, uid, password, model, method, positional_args, kwargs]
    if len(rpc_args) >= 6:
        pos_args = rpc_args[5]
        if isinstance(pos_args, list) and pos_args:
            last = pos_args[-1]
            if isinstance(last, dict):
                return last  # type: ignore[return-value]
    return None
```

**Test pattern for WRITE-02 (only model_fields_set sent)**:
```python
@respx.mock
@pytest.mark.asyncio
async def test_typed_write_sends_only_set_fields(auth_client: OdooClient) -> None:
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    instance = WritePartner(id=1, name="Updated")  # only id + name set
    await auth_client.write(instance)
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    assert set(payload.keys()) == {"name"}  # 'comment' unset, 'state'/'line_ids' metadata-excluded
```

**Integration test pattern** (mirrors `test_integration.py` module-level `pytestmark`):
```python
# At bottom of file, gated section:
@pytest.mark.integration
@pytest.mark.asyncio
async def test_codegen_read_write_roundtrip() -> None:
    """TEST-01 integration: generate class, read record, write back, assert (closes 999.3)."""
    from godoo.testcontainers import TestHarness
    async with TestHarness(modules=["base"], snapshot=False) as h:
        # Generate, read, write — assertions against live Odoo
        ...
```

---

## Shared Patterns

### Lazy-import dispatch guard
**Source:** `client.py` lines 292–298 (read typed dispatch)
**Apply to:** `create()` and `write()` typed dispatch branches
```python
try:
    from godoo.client._pydantic_transform import _serialize_for_write
except ModuleNotFoundError as exc:
    raise OdooValidationError(
        "Typed writes require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
    ) from exc
```

### OdooValidationError pre-RPC raise
**Source:** `client.py` lines 256–259 (Ref guard), `client.py` line 532 (empty-list guard)
**Apply to:** `write(instance)` when `instance.id is None`; `_serialize_for_write` when x2many field in `model_fields_set`
```python
raise OdooValidationError("...actionable message...")
```

### `# type: ignore[misc]` on multi-overload implementation
**Source:** `client.py` line 236
**Apply to:** `create()` and `write()` implementation `def` lines when they gain overloads

### Section separator style
**Source:** `_pydantic_transform.py` lines 25–27, 103–105, 194–196
**Apply to:** new `_serialize_for_write` section header in `_pydantic_transform.py`
```python
# ------------------------------------------------------------------
# Write serializer (mirror of _odoo_wire_transforms)
# ------------------------------------------------------------------
```

### `from __future__ import annotations` + TYPE_CHECKING guard
**Source:** every file in the codebase
**Apply to:** `test_typed_writes.py` line 1 (mandatory); `OdooBaseModel` annotation in `client.py` overloads must be under `TYPE_CHECKING`

### respx.mock fixture scope
**Source:** `test_rel_resolution.py` lines 33–38; `test_typed_dispatch.py` lines 35–40
**Apply to:** `auth_client` fixture in `test_typed_writes.py` — identical pattern, `with respx.mock:` scopes the auth call, per-test `@respx.mock` decorator scopes each test's own mocks

---

## No Analog Found

All files have close analogs in the codebase.

---

## Metadata

**Analog search scope:** `packages/godoo-client/src/`, `packages/godoo-introspection/src/`, `packages/godoo-client/tests/`, `packages/godoo-introspection/tests/`, `packages/godoo-testcontainers/tests/`
**Files scanned:** 12 (all primary analog files read in full)
**Pattern extraction date:** 2026-06-03
