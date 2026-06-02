# Architecture Research — godoo-py v1.2

**Domain:** Python async Odoo SDK — Typed Relations, Writes & Error Surface
**Researched:** 2026-06-02
**Confidence:** HIGH — all claims verified from direct source reading; no assumptions

---

## Existing Architecture Baseline (verified from source)

### Namespace layout (post v1.1)

```
packages/godoo-client/src/godoo/client/
├── __init__.py             # barrel: OdooClient, all errors, SafetyContext, ...
├── client.py               # OdooClient facade — @overload read/search_read + CRUD helpers
├── config.py               # config_from_env, create_client
├── errors.py               # OdooError hierarchy (7 classes)
├── typed.py                # stdlib-only: OdooModel Protocol, Ref[T] dataclass
├── _pydantic_transform.py  # SOLE pydantic importer: OdooBaseModel, derive_partial_model
├── safety/
│   └── __init__.py         # SafetyContext, OperationInfo, infer_safety_level
└── rpc/
    ├── protocol.py         # Transport Protocol (structural)
    ├── transport.py        # JsonRpcTransport._categorize_error (line 138)
    └── types.py            # OdooSessionInfo

packages/godoo-introspection/src/godoo/introspection/
├── codegen.py              # CodeGenerator — emits OdooBaseModel subclasses (Pydantic)
└── type_mapper.py          # pydantic_field_str() — 20-ttype → (annotation, default, imports)
```

### Hard constraints (load-bearing for v1.2 design)

1. `_pydantic_transform.py` is the only file that imports Pydantic — never at module top-level in any other file (D-04/D-08). Subprocess isolation test verifies this.
2. `OdooClient` is imported under `TYPE_CHECKING` in all service files to prevent circular imports.
3. Runtime typed dispatch uses `hasattr(model, "__odoo_model__")` — never `isinstance(model, BaseModel)`.
4. All mutations route through `self.call()` which calls `_guard()` — safety guard is free for any new typed path.
5. `from __future__ import annotations` in every file — annotation strings are never evaluated at runtime.
6. `mypy --strict` on all `src/` directories.

### Current `Ref[T]` dataclass (typed.py:22–34 — VERIFIED)

```python
@dataclass(frozen=True)
class Ref[T]:
    id: int
    name: str | None
```

`T` is annotation-only — erased by `from __future__ import annotations`. No `_target_cls` field exists today. When `_odoo_wire_transforms` constructs `Ref(id=value[0], name=...)` at `_pydantic_transform.py:138`, it does NOT pass target class information. The `T` in `Ref[ResPartner]` annotation is available via `get_args(field_info.annotation)` at validation time but is never stored in the Ref instance.

### Current `_odoo_wire_transforms` m2o branch (verified, lines 130–138)

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

At this point `annotation` is `field_info.annotation` — the full annotation including type arguments (e.g. `Optional[Ref[ResPartner]]`). `get_args(annotation)` is callable here and would yield `(Ref[ResPartner], type(None))` for an `Optional[Ref[ResPartner]]` field.

### Current `OdooRpcError` (errors.py:20–43 — VERIFIED)

```python
class OdooRpcError(OdooError):
    def __init__(self, message, *, code=None, data=None, cause=None):
        super().__init__(message)
        self.code = code
        self.data = data          # ← named .data today; SEED-003 renames to .raw
        ...
```

All subclasses pass through the same `__init__` (no override of `__init__` in subclasses — verified). All subclasses override only `to_json()` using `result = super().to_json(); result["error"] = "..."; return result`.

### Current `_categorize_error` (transport.py:138–168 — VERIFIED)

Constructs errors as: `OdooValidationError(message, code=code, data=data)`. The `data` kwarg is the full parsed `error_dict["data"]` dict from the Odoo response. No stripping occurs today.

---

## Feature Integration Analysis

---

### TYPED-F1: `client.read(ref)` / `client.read(list[Ref])` — Ref-Driven Resolution

#### The Core Problem: Ref Has No Runtime Target Class

`Ref[T]` instances carry only `id` and `name`. To resolve a `Ref` to its model, `client.read(ref)` needs to know which `OdooBaseModel` subclass to instantiate. The `T` type argument is annotation-only and inaccessible at runtime on the `Ref` instance.

**Required change:** `Ref[T]` must carry `_target_cls: type | None` — populated by the wire transform at validation time, when `field_info.annotation` is available.

#### Step 1: Extend `Ref[T]` — `client/typed.py` MODIFIED

Add a non-frozen, defaulted field so existing `Ref(id=..., name=...)` construction sites still work:

```python
@dataclass(frozen=True)
class Ref[T]:
    id: int
    name: str | None
    _target_cls: type | None = field(default=None, compare=False, repr=False, hash=False)
```

`compare=False, hash=False` — the target class is metadata, not identity. `repr=False` keeps repr clean. `frozen=True` is preserved — `field(default=None)` is compatible with frozen dataclasses.

**mypy --strict note:** `field(default=None, ...)` on a frozen dataclass with a TypeVar parameter requires care. The annotation `_target_cls: type | None` (not `type[T] | None`) avoids generic complexity at the call site while remaining honest about the value. Callers who need the typed class cast it themselves.

#### Step 2: Populate `_target_cls` in Wire Transform — `_pydantic_transform.py` MODIFIED

In `_odoo_wire_transforms`, the m2o branch already has `annotation` for the field. Extract the target class from the annotation's type arguments:

```python
# m2o branch — after confirming _annotation_mentions_ref(annotation):
target_cls = _extract_ref_target_cls(annotation)
out[name] = Ref(id=value[0], name=None if value[1] is False else value[1], _target_cls=target_cls)
```

New private helper `_extract_ref_target_cls(annotation) -> type | None`:
- Unwrap `Optional[Ref[X]]` → `Ref[X]`
- Extract `get_args(Ref[X])` → `(X,)`
- Return `X` if `hasattr(X, "__odoo_model__")` else `None`
- For `Ref[int]`: `int` has no `__odoo_model__` → returns `None`

This helper is NEW in `_pydantic_transform.py`. It does not change the existing `_annotation_mentions_ref` predicate — add a sibling rather than modifying the predicate to return two values.

#### Step 3: New `@overload` on `client.read` — `client/client.py` MODIFIED

Current implementation signature: `read(self, model: str | type[T], ids: int | list[int], ...)`.

The Ref overloads use a different first-parameter type. Add two new `@overload` signatures:

```python
@overload
async def read(self, model: Ref[T]) -> T: ...

@overload
async def read(self, model: list[Ref[T]]) -> list[T]: ...
```

The implementation signature becomes:
```python
async def read(
    self,
    model: str | type[T] | Ref[T] | list[Ref[T]],
    ids: int | list[int] | None = None,
    fields: list[str] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]] | list[T] | T:
```

Making `ids` optional (default `None`) allows `read(ref)` without `ids`. The existing overloads require `ids` — their signatures are unchanged. mypy will dispatch correctly because `Ref` and `list[Ref]` are structurally distinct from `str` and `type[T]`.

**Ref import in client.py:** `Ref` lives in `typed.py` (stdlib-only). `OdooModel` is already imported from `typed.py` at module level (`from godoo.client.typed import OdooModel`, line 21 of client.py). Add `Ref` to that same import. No pydantic boundary crossed.

#### Step 4: Batch-by-Target-Model Logic — `client/client.py` MODIFIED

Inside the new Ref branch:

```python
# Single Ref
if isinstance(model, Ref):
    if model._target_cls is None:
        raise OdooValidationError("Cannot resolve untyped Ref[int] — target model class unavailable")
    results = await self.read(model._target_cls, [model.id], fields=fields, **kwargs)
    return cast("T", results[0])

# list[Ref]
if isinstance(model, list) and model and isinstance(model[0], Ref):
    return await self._resolve_ref_list(model, fields=fields, **kwargs)
```

`_resolve_ref_list` is a private async method on `OdooClient` (NEW):

```python
async def _resolve_ref_list(self, refs: list[Ref[Any]], ...) -> list[Any]:
    # Group by target class
    grouped: dict[type, list[tuple[int, Ref[Any]]]] = {}
    for i, ref in enumerate(refs):
        if ref._target_cls is None:
            raise OdooValidationError(f"Ref at index {i} is untyped (Ref[int]) — cannot resolve")
        grouped.setdefault(ref._target_cls, []).append((i, ref))

    # Fetch each group; results keyed by id
    id_to_record: dict[int, Any] = {}
    for target_cls, indexed_refs in grouped.items():
        ids = [ref.id for _, ref in indexed_refs]
        records = await self.read(target_cls, ids, ...)
        for record in records:
            id_to_record[record.id] = record  # OdooBaseModel instances have .id

    # Reassemble in input order
    return [id_to_record[ref.id] for ref in refs]
```

This method lives in `client.py`, not a separate module. The lazy Pydantic import is inherited from the delegated `self.read(target_cls, ...)` call — no direct Pydantic import needed in `_resolve_ref_list`.

#### TYPED-F1 Integration Point Summary

| Symbol | File | Change | Notes |
|--------|------|--------|-------|
| `Ref[T]` | `client/typed.py` | MODIFIED | Add `_target_cls: type \| None` field |
| `_extract_ref_target_cls` | `client/_pydantic_transform.py` | NEW helper | Extracts target class from `Optional[Ref[X]]` annotation |
| `_odoo_wire_transforms` (m2o branch) | `client/_pydantic_transform.py` | MODIFIED | Pass `_target_cls` to Ref constructor |
| `OdooClient.read` | `client/client.py` | MODIFIED | New `@overload` for `Ref[T]` and `list[Ref[T]]`; Ref dispatch branch |
| `OdooClient._resolve_ref_list` | `client/client.py` | NEW private method | Batch-group-and-fetch logic |
| `Ref` import in `client.py` | `client/client.py` | MODIFIED | Add `Ref` to `from godoo.client.typed import OdooModel, Ref` |

**Pydantic-optional boundary:** `Ref._target_cls` is a plain `type | None` stored in stdlib dataclass — no Pydantic. The target class extraction runs inside `_pydantic_transform.py` (already Pydantic-only module). The `client.read(ref)` dispatch branch lazy-imports nothing new — it delegates to `self.read(target_cls, ids)` which already uses the existing lazy import.

**`Ref[int]` behaviour:** `_target_cls = None` → `OdooValidationError` raised at read time. Expected, documented.

---

### TYPED-F2: Typed Write/Create — Accept `OdooBaseModel` Instances

#### Serialization Function — `_pydantic_transform.py` NEW

`OdooBaseModel.model_dump(exclude_none=True)` produces a dict that needs reverse transforms before sending to Odoo:

- `Ref(id=14, name="France") → 14` (m2o field: send id only)
- `date(2024, 1, 15) → "2024-01-15"` (date field)
- `datetime(2024, 1, 15, 12, 0, 0) → "2024-01-15 12:00:00"` (datetime field — Odoo format, not ISO T)
- `list[int]` — unchanged
- `bool` — unchanged
- `str`, `int`, `float`, `None` — unchanged

New function `odoo_dump(instance: OdooBaseModel, *, exclude_id: bool = True) -> dict[str, Any]`:

```python
def odoo_dump(instance: OdooBaseModel, *, exclude_id: bool = True) -> dict[str, Any]:
    from datetime import date, datetime
    raw = instance.model_dump(exclude_none=True)
    if exclude_id:
        raw.pop("id", None)
    for name, value in list(raw.items()):
        if isinstance(value, Ref):
            raw[name] = value.id
        elif isinstance(value, datetime):  # datetime before date — subclass
            raw[name] = value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, date):
            raw[name] = value.isoformat()
    return raw
```

`date`/`datetime` imports are stdlib — permitted in `_pydantic_transform.py` (they are already imported there at lines 11–12). `Ref` is already imported from `typed.py` at line 13 of `_pydantic_transform.py`.

#### New `@overload` on `write` and `create` — `client/client.py` MODIFIED

**`write` overloads (existing lines 440–473):**

```python
@overload
async def write(self, model: type[T], ids: int | list[int], values: T, **kwargs) -> bool: ...
@overload
async def write(self, model: str, ids: int | list[int], values: dict[str, Any], **kwargs) -> bool: ...
```

Implementation: detect `hasattr(model, "__odoo_model__")` → lazy import `odoo_dump` → serialize `values` → call existing `self.call(model.__odoo_model__, "write", ...)`.

**`create` overloads (existing lines 440–462):**

```python
@overload
async def create(self, model: type[T], values: T, **kwargs) -> int: ...
@overload
async def create(self, model: type[T], values: list[T], **kwargs) -> list[int]: ...
@overload
async def create(self, model: str, values: dict[str, Any], **kwargs) -> int: ...
@overload
async def create(self, model: str, values: list[dict[str, Any]], **kwargs) -> list[int]: ...
```

Implementation: `hasattr(model, "__odoo_model__")` → serialize single instance or list → call existing `self.call(model.__odoo_model__, "create", ...)`.

#### Safety Guard — No Changes

All typed write/create paths route through `self.call()` which calls `_guard()`. Safety is free — no new guard logic needed.

#### Public Export

`OdooBaseModel` is in `_pydantic_transform.py` (private module). If users need to type-annotate against it, it should be exposed. However, it is already accessible via `from godoo.client._pydantic_transform import OdooBaseModel` for generated model files. Adding it to `client/__init__.py` `__all__` is optional — depends on whether it is a public API (it was not in v1.1). Decision deferred to requirements author; the implementation does not require it.

#### TYPED-F2 Integration Point Summary

| Symbol | File | Change | Notes |
|--------|------|--------|-------|
| `odoo_dump` | `client/_pydantic_transform.py` | NEW function | Serializes `OdooBaseModel` → Odoo write/create payload dict |
| `OdooClient.write` | `client/client.py` | MODIFIED | New `@overload` for `type[T]` + `T` instance |
| `OdooClient.create` | `client/client.py` | MODIFIED | New `@overload` for `type[T]` + `T \| list[T]` |
| `client/__init__.py` | `client/__init__.py` | POSSIBLY MODIFIED | Add `OdooBaseModel` to exports if public API |

**Pydantic-optional boundary:** `odoo_dump` is in `_pydantic_transform.py` — already Pydantic-only. The new overloads in `client.py` lazy-import it the same way `read()` does. No Pydantic at module load time.

---

### SEED-003: Restructure `OdooError` Hierarchy

#### Current Structure (verified from errors.py)

```
OdooError
├── OdooRpcError(code, data, cause)     ← self.data = raw server dict
│   ├── OdooAuthError
│   ├── OdooNetworkError
│   │   └── OdooTimeoutError
│   ├── OdooValidationError
│   ├── OdooAccessError
│   └── OdooMissingError
└── OdooSafetyError(operation)           ← local-only; unaffected by SEED-003
```

No subclass overrides `__init__` (verified — only `OdooAuthError` has an `__init__` override, and it delegates to `super().__init__` with the same signature). All subclasses override only `to_json()`.

#### What SEED-003 Changes

**`OdooRpcError.__init__` — MODIFIED:**

```python
class OdooRpcError(OdooError):
    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        data: dict[str, Any] | None = None,   # kwarg name stays "data" at call sites
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.raw: dict[str, Any] | None = data     # RENAMED: was self.data
        # NEW structured fields — extracted from data dict:
        self.odoo_model: str | None = _extract_model(data)
        self.odoo_field: str | None = _extract_field(data)
        self.constraint: str | None = _extract_constraint(data)
        self.human_message: str | None = _extract_human_message(data)
        if cause is not None:
            self.__cause__ = cause
```

**Breaking change:** `self.data` → `self.raw`. The kwarg name in `__init__` stays `data=` (no call-site changes in `_categorize_error`). Only external callers accessing `exc.data` must migrate to `exc.raw`.

**`OdooAuthError.__init__` — MINIMALLY MODIFIED:**

```python
class OdooAuthError(OdooRpcError):
    def __init__(self, message="Authentication failed", *, code=None, data=None, cause=None):
        super().__init__(message, code=code, data=data, cause=cause)
```

Signature unchanged — `data=` kwarg name stays. Only the inherited `self.raw` rename affects it. No functional change.

**`OdooRpcError.to_json` — MODIFIED:**

```python
def to_json(self) -> dict[str, Any]:
    return {
        "error": "RPC_ERROR",
        "message": str(self),
        "model": self.odoo_model,
        "field": self.odoo_field,
        "constraint": self.constraint,
        "human_message": self.human_message,
        "raw": self.raw,
    }
```

Subclasses override only `result["error"] = "..."` — that pattern still works unchanged.

**Extraction helpers — NEW private functions in `errors.py`:**

Odoo's `data` dict shape (from `_categorize_error` inspection) has keys: `exception_type`, `name`, `message`, `debug`, `arguments`, `context`. The structured fields map as:

- `human_message` — `data.get("message")` or `data.get("arguments", [None])[0]`
- `odoo_model` — heuristic from `data.get("name")` (e.g. `"odoo.exceptions.ValidationError"`) or `data.get("context", {}).get("model")`
- `odoo_field` — `data.get("field")` if present, else `None`
- `constraint` — `data.get("context", {}).get("constraint")` if present
- Traceback stripping: `data.get("debug")` contains the Python traceback — NOT included in `to_json()` output; available only via `self.raw["debug"]`

All helpers return `None` if `data is None` or the key is absent — safe defaults.

**`_categorize_error` in `transport.py` — MINIMALLY MODIFIED:**

Current construction: `OdooValidationError(message, code=code, data=data)` where `message` is `data.get("message", "Unknown RPC error")` from the outer error dict (not the nested `data["message"]`).

The `message` passed to the constructor is Odoo's outer error message — which may contain a server traceback in some versions. The stripping happens in `OdooRpcError.__init__` by extracting `human_message` from `data["message"]` (the nested, cleaner message) and using that as the overriding display.

**Alternative approach:** override `str(self)` to return `self.human_message or self.args[0]`. This avoids changing `message` assignment in `_categorize_error` at all — the human-readable message surfaces via `str(exc)` without touching the constructor.

This second approach is cleaner: `_categorize_error` is unchanged except it now benefits from structured fields on the raised exception.

#### Existing Raise Sites — No Change Required

`client.py` raises `OdooValidationError("...")` and `OdooAuthError("...")` with string-only messages (no `data=`). After SEED-003, `self.raw = None` and structured fields are all `None` for these — the existing behaviour is preserved exactly.

#### SEED-003 Integration Point Summary

| Symbol | File | Change | Notes |
|--------|------|--------|-------|
| `OdooRpcError.__init__` | `client/errors.py` | MODIFIED | `self.data` → `self.raw`; add structured fields |
| `OdooRpcError.to_json` | `client/errors.py` | MODIFIED | Surface structured fields; `raw` instead of `details` |
| `OdooAuthError.__init__` | `client/errors.py` | MINIMALLY MODIFIED | `super()` call unchanged; just inherits new fields |
| `_extract_model`, `_extract_field`, `_extract_constraint`, `_extract_human_message` | `client/errors.py` | NEW private helpers | Safe None-returning extractors |
| `_categorize_error` | `client/rpc/transport.py` | NOT MODIFIED | `data=` kwarg unchanged; stripping handled in `OdooRpcError.__init__` |
| `client/__init__.py` `__all__` | `client/__init__.py` | NOT MODIFIED | All errors already exported |

---

## Data Flow Changes

### TYPED-F1: Ref Resolution Data Flow

```
Before (v1.1):
  OdooBaseModel._odoo_wire_transforms
    → Ref(id=14, name="France")          # no target class

After (v1.2):
  OdooBaseModel._odoo_wire_transforms
    → _extract_ref_target_cls(annotation)  # annotation = Optional[Ref[ResCountry]]
    → Ref(id=14, name="France", _target_cls=ResCountry)

New resolution path:
  client.read(ref)                         # ref._target_cls = ResCountry
    → ref._target_cls is None? → OdooValidationError
    → self.read(ResCountry, [ref.id])      # existing typed read path
    → list[ResCountry][0]                  # unwrap single

  client.read([ref1, ref2, ref3])          # list[Ref] — may be mixed types
    → group by ref._target_cls
    → self.read(ResCountry, [id1, id2])
    → self.read(ResCurrency, [id3])
    → reassemble in input order
```

### TYPED-F2: Typed Write/Create Data Flow

```
Before (v1.1):
  client.write("res.partner", [42], {"name": "ACME"})
    → self.call("res.partner", "write", [[42], {"name": "ACME"}], {})
    → safety guard (WRITE) → transport.call() → Odoo

After (v1.2, new typed path):
  client.write(ResPartner, [42], partner_instance)
    → hasattr(ResPartner, "__odoo_model__") → True
    → lazy import: odoo_dump from _pydantic_transform
    → payload = odoo_dump(partner_instance)
        → model_dump(exclude_none=True)
        → reverse transforms: Ref→id, datetime→str, date→str
        → {"name": "ACME", "country_id": 14, ...}
    → self.call("res.partner", "write", [[42], payload], {})
    → safety guard (WRITE) → transport.call() → Odoo
```

### SEED-003: Error Path Data Flow

```
Before (v1.1):
  transport._categorize_error({"message": "...", "data": {...traceback...}})
    → OdooValidationError(message, code=code, data=data)
        → exc.data = {"message": "...", "debug": "Traceback..."}
        → exc.to_json() = {"details": {"message": "...", "debug": "Traceback..."}}

After (v1.2):
  transport._categorize_error({"message": "...", "data": {...traceback...}})
    → OdooValidationError(message, code=code, data=data)   # unchanged call
        → exc.raw = {"message": "...", "debug": "Traceback..."}   # full dict preserved
        → exc.human_message = "Field 'name' is required"          # extracted, clean
        → exc.odoo_model = "res.partner"                          # extracted
        → exc.to_json() = {
              "error": "VALIDATION_ERROR",
              "message": "...",            # stripped (no traceback)
              "human_message": "Field 'name' is required",
              "model": "res.partner",
              "field": None,
              "constraint": None,
              "raw": {"message": "...", "debug": "Traceback..."}  # full escape hatch
          }
```

---

## Recommended Build Order

### Dependency Graph

```
SEED-003
  (no dependencies on TYPED features)

TYPED-F1-prereq: Ref._target_cls + wire transform
  └── depends on: nothing (Ref is stdlib, transform is in existing _pydantic_transform.py)

TYPED-F1-dispatch: client.read(Ref) overloads + _resolve_ref_list
  └── depends on: TYPED-F1-prereq (Ref must carry _target_cls before dispatch is useful)

TYPED-F2: odoo_dump + write/create overloads
  └── depends on: nothing new (odoo_dump uses existing OdooBaseModel + Ref.id)
      Note: odoo_dump.Ref reverse-transform uses ref.id only — no _target_cls dependency
```

### Proposed Phase Order

**Step 1 — SEED-003 (`errors.py` restructure)**

Rationale: Independent of both typed features. Ships first so the cleaner error surface is active for all subsequent testing. Tests: unit tests for `_extract_*` helpers; round-trip test verifying `exc.raw` is preserved and `exc.human_message` is extracted; regression test that `exc.data` raises `AttributeError` (breaking change verification).

**Step 2 — TYPED-F1 prerequisite: `Ref._target_cls` + wire transform**

Modify `typed.py`: add `_target_cls` field. Modify `_pydantic_transform.py`: add `_extract_ref_target_cls` helper + populate `_target_cls` in the m2o branch. Tests: unit test `_odoo_wire_transforms` with `Optional[Ref[SomeModel]]` annotation verifies `_target_cls` is set; with `Ref[int]` annotation verifies `_target_cls = None`.

**Step 3 — TYPED-F1: `client.read(ref)` dispatch + batch logic**

Add `@overload` and `_resolve_ref_list` in `client.py`. Tests: integration test verifying codegen → typed read → Ref resolution round-trip (999.3 requirement).

**Step 4 — TYPED-F2: `odoo_dump` + typed write/create overloads**

Add `odoo_dump` to `_pydantic_transform.py`. Add overloads to `client.py`. Tests: unit test `odoo_dump` round-trip (wire-in → `model_validate` → `odoo_dump` → assert payload dict); integration test for typed write/create.

**Why TYPED-F2 after Step 3, not in parallel:**

Both Step 3 and Step 4 modify `client.py`. Sequential is safer than concurrent for a single-maintainer repo. TYPED-F1 (higher complexity) goes first so its overload changes are stable before TYPED-F2 adds more overloads to the same methods.

---

## Component Summary Table

| Component | New / Modified | File | Feature |
|-----------|---------------|------|---------|
| `Ref[T]._target_cls` field | MODIFIED | `client/typed.py` | TYPED-F1 |
| `Ref` import in `client.py` | MODIFIED | `client/client.py` | TYPED-F1 |
| `_extract_ref_target_cls` | NEW private helper | `client/_pydantic_transform.py` | TYPED-F1 |
| `_odoo_wire_transforms` m2o branch | MODIFIED | `client/_pydantic_transform.py` | TYPED-F1 |
| `OdooClient.read` `@overload` (Ref/list[Ref]) | MODIFIED | `client/client.py` | TYPED-F1 |
| `OdooClient._resolve_ref_list` | NEW private method | `client/client.py` | TYPED-F1 |
| `odoo_dump` | NEW function | `client/_pydantic_transform.py` | TYPED-F2 |
| `OdooClient.write` `@overload` (typed) | MODIFIED | `client/client.py` | TYPED-F2 |
| `OdooClient.create` `@overload` (typed) | MODIFIED | `client/client.py` | TYPED-F2 |
| `OdooRpcError.__init__` | MODIFIED | `client/errors.py` | SEED-003 |
| `OdooRpcError.to_json` | MODIFIED | `client/errors.py` | SEED-003 |
| `OdooAuthError.__init__` | MINIMALLY MODIFIED | `client/errors.py` | SEED-003 |
| `_extract_model/field/constraint/human_message` | NEW private helpers | `client/errors.py` | SEED-003 |
| `_categorize_error` | NOT MODIFIED | `client/rpc/transport.py` | SEED-003 |

**Unchanged by v1.2:** `JsonRpcTransport` (beyond inheriting SEED-003 benefits), all 8 services, `SafetyContext`, `config.py`, `codegen.py`, `type_mapper.py`, `IntrospectionCache`, `godoo-testcontainers`.

---

## Anti-Patterns to Avoid

### Setting `_target_cls = int` for out-of-set m2o fields

`int` has no `__odoo_model__`. If `_target_cls = int`, the dispatch branch must check `hasattr(int, "__odoo_model__")` → False and raise a confusing error. Use `None` as the sentinel for unresolvable Refs — it is unambiguous and the `OdooValidationError` message at call time is clear.

### Importing `_pydantic_transform` at module top-level (reiteration)

Any new file that needs `odoo_dump` or `OdooBaseModel` must lazy-import inside a function body. The subprocess isolation test will catch violations.

### Stripping traceback in `_categorize_error` instead of `OdooRpcError.__init__`

Stripping in `__init__` covers all raise paths (including direct `OdooValidationError(...)` calls in `client.py`). Stripping in `_categorize_error` only covers the RPC fault path. Centralizing in `__init__` is the correct architectural choice even though direct raises have no `data=` dict and thus no traceback to strip.

### Modifying `_annotation_mentions_ref` to return a tuple

`_annotation_mentions_ref` is used elsewhere as a boolean predicate. Changing its return type breaks existing callers. Add `_extract_ref_target_cls` as a sibling — same annotation traversal logic, different return shape.

### Routing typed write/create directly to `self._transport.call()`

Bypasses the safety guard. All paths must go through `self.call()`.

---

## Sources

All claims verified from direct source reading. No training data assumptions made.

- `packages/godoo-client/src/godoo/client/client.py` — `OdooClient`, lines 1–565
- `packages/godoo-client/src/godoo/client/typed.py` — `Ref[T]`, `OdooModel`, lines 1–36
- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — `OdooBaseModel._odoo_wire_transforms`, `derive_partial_model`, lines 1–208
- `packages/godoo-client/src/godoo/client/errors.py` — full error hierarchy, lines 1–130
- `packages/godoo-client/src/godoo/client/rpc/transport.py` — `JsonRpcTransport._categorize_error`, lines 138–168
- `packages/godoo-client/src/godoo/client/rpc/protocol.py` — `Transport` Protocol
- `packages/godoo-client/src/godoo/client/safety/__init__.py` — `SafetyContext`, `infer_safety_level`
- `packages/godoo-introspection/src/godoo/introspection/codegen.py` — `CodeGenerator.generate`, Ref emission pattern
- `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` — `pydantic_field_str`, m2o annotation forms

---
*Architecture research for: godoo-py v1.2 — Typed Relations, Writes & Error Surface*
*Researched: 2026-06-02*
