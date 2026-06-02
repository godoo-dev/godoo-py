# Technology Stack — godoo-py v1.2 Typed Relations, Writes & Error Surface

**Project:** godoo-py
**Researched:** 2026-06-02
**Scope:** NEW capabilities needed for v1.2 only. Established stack (Python 3.14,
uv workspace, hatchling, httpx>=0.28, pydantic>=2.13 behind `godoo[typed]`,
typer>=0.26 in godoo-introspection, ruff, mypy --strict, pytest-asyncio, respx) is
fixed and NOT re-evaluated here.
**Confidence:** HIGH — all API claims verified against Pydantic 2.13.4 (installed),
transport.py and client.py read directly, key behaviors confirmed with live `uv run python`.

---

## Summary Verdict: No New Dependencies Required

All three v1.2 features are buildable entirely from the already-declared stack:

| Feature | New Dep? | Existing Capability Used |
|---------|----------|--------------------------|
| TYPED-F1 — Ref-driven relation resolution | None | `Ref[T]` dataclass + `get_args()` + existing `client.read()` |
| TYPED-F2 — typed write/create | None | `model_dump(exclude_unset=True)` + stdlib `re` + existing `client.write/create` |
| SEED-003 — OdooError restructure | None | stdlib `re`, `str`, `dict` — pure fault-payload parsing |

The roadmap must not invent any dependency work for v1.2.

---

## Feature-by-Feature Capability Analysis

### TYPED-F1 — Ref-Driven Typed Relation Resolution

**What it must do:** `client.read(ref)` / `client.read(list[Ref])` where `ref` is a
typed `Ref` instance resolves into the related Pydantic model, batched (one RPC per
target model class), single level deep.

**Capability needed: Ref carries the target model class at runtime.**

The current `Ref[T]` is a `@dataclass(frozen=True)` with only `id: int` and
`name: str | None`. The type parameter `T` is erased at runtime — `Ref[ResPartner](1,
'ACME')` produces an instance indistinguishable from `Ref[ResUsers](1, 'Admin')` at
runtime. For `client.read(ref)` to dispatch to the right model, the `Ref` instance must
carry the model class.

**Verified design path (no new dep):**

Extend `Ref` with an optional `model_class` field using `compare=False, hash=False` to
preserve backward compatibility:

```python
@dataclass(frozen=True)
class Ref[T]:
    id: int
    name: str | None
    model_class: type | None = field(default=None, compare=False, hash=False)
```

`compare=False` and `hash=False` on `model_class` means `Ref(1, 'ACME', None) ==
Ref(1, 'ACME', ResPartner)` — existing equality-based tests are unaffected. This is
a backward-compatible extension (new kwarg with default).

The wire-transform in `_pydantic_transform.py` already processes field annotations to
build `Ref` instances. It uses `_annotation_mentions_ref(annotation)` to detect
`Ref[X] | None` fields. At that point `get_args(annotation)` is available — verified:

```python
get_args(Ref[SomeModel])          # → (SomeModel,)
get_args(Ref[SomeModel])[0]       # → SomeModel class object
hasattr(SomeModel, '__odoo_model__')  # → True
```

The wire-transform can populate `model_class=get_args(annotation)[0]` when that arg
carries `__odoo_model__` (i.e., when it is a typed generated model class), and
`model_class=None` when the annotation is `Ref[int]` (unresolvable foreign key without
a generated model).

**Batching pattern (pure stdlib):**

```python
from collections import defaultdict

by_model: dict[type, list[Ref]] = defaultdict(list)
for ref in refs:
    if ref.model_class is not None:
        by_model[ref.model_class].append(ref)

# One client.read() call per model class — existing read() typed dispatch path
for model_class, model_refs in by_model.items():
    ids = [r.id for r in model_refs]
    records = await client.read(model_class, ids)
```

`collections.defaultdict` is stdlib. No new library.

**Importability constraint upheld:** `Ref` and `OdooModel` live in
`godoo.client.typed` (stdlib-only module). The `model_class` field holds a `type | None`
— no Pydantic import required to define or instantiate `Ref`. The resolution call
(`client.read(model_class, ids)`) is the only place Pydantic is touched, and that
already goes through the existing lazy-import branch in `client.py`.

---

### TYPED-F2 — Typed Write/Create

**What it must do:** Accept `OdooBaseModel` instances (or subclasses) in `client.write`
/ `client.create`, serialize them into the `dict[str, Any]` that Odoo JSON-RPC expects,
honouring partial-write semantics (only fields explicitly set by the caller should be
sent).

**Capability needed: `model_dump(exclude_unset=True)` plus a write-direction transform.**

**Verified: Pydantic 2.13 `model_dump` API (confirmed live against 2.13.4)**

Full signature:
```python
def model_dump(
    mode: Literal['json', 'python'] | str = 'python',
    include: IncEx | None = None,
    exclude: IncEx | None = None,
    context: Any | None = None,
    by_alias: bool | None = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
    exclude_computed_fields: bool = False,
    round_trip: bool = False,
    warnings: bool | Literal['none', 'warn', 'error'] = True,
    fallback: Callable[[Any], Any] | None = None,
    serialize_as_any: bool = False,
    polymorphic_serialization: bool | None = None,
) -> dict[str, Any]
```

**`exclude_unset=True` is the partial-write mechanism.** Pydantic tracks which fields
were explicitly provided via `model_fields_set: set[str]`. A field that was never passed
to the constructor is absent from `model_fields_set` and is excluded by
`exclude_unset=True`. This is the correct semantic for Odoo partial writes: only send
what the caller explicitly changed.

**Critical distinction confirmed:**

| Scenario | `exclude_unset=True` result | Odoo write behaviour |
|----------|----------------------------|----------------------|
| Field never provided | Excluded from dump | Field unchanged in Odoo |
| Field set to `None` | Included (as `None`) | Clears the field in Odoo (after transform: `False`) |
| Field set to `False` | Included (as `False`) | Boolean field set to False in Odoo |
| Field set to `0` | Included (as `0`) | Numeric field cleared |

Verified live:
```python
p = Partner(id=1, name='Test')
p.model_fields_set   # → {'id', 'name'}
p.model_dump(exclude_unset=True)  # → {'id': 1, 'name': 'Test'}
# 'active' (default=True) is absent — not sent to Odoo
```

**Write-direction transform (no new dep — stdlib only):**

`model_dump(exclude_unset=True)` produces a `dict` with Python-native types. The
following transforms are needed before passing to `client.call(model, 'write', ...)`:

1. **Strip `id`** — Odoo's `write` method takes ids as a separate arg; `id` must not
   appear in the values dict. Simple `dict.pop('id', None)` or `exclude={'id'}`.

2. **`Ref` → `int`** — `model_dump(mode='python')` (the default) renders `Ref(id=5,
   name='ACME')` as `{'id': 5, 'name': 'ACME'}` (dataclass → dict). This must become
   `5` (the foreign-key integer). One-pass dict walk, `isinstance(v, Ref) → v.id`.

3. **`None` → `False`** — Odoo's JSON-RPC convention uses `False` (not `None`) for
   unset/cleared relational fields. Transform `None → False` for all values. (Bool
   fields are never `None` after the wire-transform inbound, so no ambiguity on the
   write path.)

4. **`date`/`datetime` → ISO string** — `model_dump(mode='python')` returns native
   `date`/`datetime` objects. Stdlib `json.dumps` (used by httpx internally) does NOT
   serialize them. Use `model_dump(mode='json')` instead — verified: converts `date`
   to `'2025-01-15'` string, preserves all other types. This is the right call to make.

   ALTERNATIVELY: a single-pass transform can call `.isoformat()` on any
   `date`/`datetime` values. Either approach works; `mode='json'` is simpler.

5. **`list[int]` (x2many fields)** — x2many values stay as `list[int]` through
   `model_dump`. Odoo expects `[(6, 0, ids)]` for replace-semantics, or `[(4, id)]` for
   append. For v1.2 write support, the design decision is: typed write passes `list[int]`
   directly (replace-semantics via `[(6, 0, ids)]` transform) OR the caller constructs
   the command tuples manually and passes a raw `list[Any]`. This is a design choice,
   not a library limitation. No new dep either way.

**`by_alias`:** NOT needed for this project. Odoo field names ARE the canonical Python
names (snake_case like `partner_id`, `move_id`). Generated models use these as field
names directly. No alias mapping is required.

**`exclude_defaults` vs `exclude_unset`:** For Odoo writes, `exclude_unset` is correct.
`exclude_defaults` would incorrectly omit a field explicitly set to its default value
(e.g., `active=True` when the caller explicitly wants to re-enable a record). Use
`exclude_unset` exclusively.

**`model_fields_set` after `model_validate`:** Confirmed live — `model_validate(dict)`
populates `model_fields_set` with all keys present in the input dict. This means a
round-tripped model (read then write) sends all fields back unless the caller uses
`model_construct` (bypasses validation, `model_fields_set` is what you pass via
`_fields_set` kwarg). For partial-write ergonomics, the pattern is:

```python
# User explicitly creates only what they want to write
patch = ResPartner(id=42, name='Updated Name')  # model_fields_set = {'id', 'name'}
await client.write(patch)                        # sends only name to Odoo
```

Not `model_validate(full_read_result)` then modify — that would send all fields.

**`model_copy(update=...)` as partial-update helper:** Pydantic's `model_copy(update=
{'field': value})` creates a copy with updated fields added to `model_fields_set`.
Useful pattern to document but requires no new dep.

---

### SEED-003 — OdooError Hierarchy Restructure

**What it must do:** Add structured fields (model / field / constraint name / human
message), strip server tracebacks and filesystem paths from user-facing exception
`str(e)`, add `.raw` escape hatch preserving the full fault payload dict.

**Capability needed: stdlib only — pure dict access + `re` module.**

**Current state (read directly from `errors.py`):**

The existing hierarchy:
```
OdooError
  OdooRpcError(message, code, data)     # data = raw fault dict from JSON-RPC
    OdooAuthError
    OdooNetworkError
      OdooTimeoutError
    OdooValidationError
    OdooAccessError
    OdooMissingError
  OdooSafetyError(message, operation)   # local — not from RPC
```

`OdooRpcError` already stores the full `data` dict — the raw fault payload is already
present on every exception. The `data` dict from Odoo JSON-RPC contains:

```python
{
    'name': 'odoo.exceptions.ValidationError',   # exception class path
    'debug': 'Traceback (most recent call last):\n  File "/opt/odoo/...',  # server traceback
    'message': 'The field Name is required.',     # human-readable
    'exception_type': 'validation_error',         # already used in _categorize_error
    'arguments': ['The field Name is required.'], # raw args to exception constructor
    'context': {'uid': 1, 'lang': 'en_US', ...}, # Odoo context at fault time
}
```

**Structured fields via stdlib dict access (no new dep):**

```python
# From data dict — all stdlib dict.get() calls
model_name  = data.get('context', {}).get('active_model')          # or parse from message
field_name  = None  # not always present; parse from message heuristics
constraint  = None  # parse from ValidationError message (regex)
human_msg   = (data.get('arguments') or [data.get('message', '')])[0]
```

**Path stripping via `re` module (stdlib):**

```python
import re
_SERVER_PATH_RE = re.compile(r'["\']?/[^\s"\']+\.py["\']?')
clean = _SERVER_PATH_RE.sub('<server-path>', message)
```

Verified live: strips `/opt/odoo/16.0/addons/base/models/res_partner.py` → `<server-path>`.

**Traceback stripping:** The `debug` key contains the full server traceback. Simply do
not include `data['debug']` in the user-facing `str(self)` or `to_json()`. The `.raw`
attribute preserves the full `data` dict for callers who need the traceback.

**`.raw` escape hatch:** Rename or alias the existing `self.data` to `self.raw`. The
current `data` attribute on `OdooRpcError` is not part of any documented public API
surface — renaming it to `raw` is the breaking change already scoped by SEED-003. The
`to_json()` override can then expose a `raw` key instead of `details`.

**No new library needed.** The entire restructure is:
1. New fields on `OdooRpcError.__init__`: `model`, `field`, `constraint`, `human_message`
2. New extraction helper (private, `_extract_structured_fields(data: dict) -> ...`) using
   `dict.get()` and `re.sub()`
3. `data` renamed to `raw` (breaking change, already scoped)
4. `__str__` returns `human_message` (stripped) instead of the raw RPC message
5. `to_json()` updated accordingly

---

## Pydantic 2.13 API Reference (Version-Confirmed)

Installed and verified: **pydantic 2.13.4** (current as of research date).

| API | Signature / Behaviour | Use in v1.2 |
|-----|----------------------|-------------|
| `model_dump(exclude_unset=True)` | Returns only fields in `model_fields_set` | TYPED-F2 partial writes |
| `model_dump(exclude_unset=True, mode='json')` | Same, but converts `date`→ISO str, `datetime`→ISO str | TYPED-F2 date field writes |
| `model_dump(exclude_defaults=True)` | Omits fields equal to their declared default | NOT used — wrong semantic for Odoo writes |
| `model_dump(exclude_none=True)` | Omits `None` values | NOT used — `None` means "clear field", must send `False` |
| `model_fields_set: set[str]` | Fields explicitly provided at construction | Used to understand what the caller set |
| `model_validate(obj)` | Classmethod; populates `model_fields_set` with ALL keys in obj | Round-trip reads: all fields appear set |
| `model_construct(**kwargs, _fields_set=...)` | Bypass validation; only `_fields_set` fields are "set" | Escape hatch for perf-critical paths |
| `model_copy(update={...})` | Shallow copy with updated fields added to `model_fields_set` | Partial-update helper pattern (document, not implement) |
| `get_args(annotation)` | stdlib `typing.get_args` | Extracts `T` from `Ref[T]` at annotation-processing time |
| `get_origin(annotation)` | stdlib `typing.get_origin` | Detects `Ref[T]` origin is `Ref` class |

**`by_alias`:** Not needed. Odoo field names are the canonical Python names; no alias mapping required.

**`field_serializer` decorator:** Not needed for TYPED-F2. The write-direction transform
is done in a single helper function in `_pydantic_transform.py`, not via Pydantic
serializer hooks. This keeps the transform inspectable and testable without Pydantic
internals.

---

## Integration Points

### `godoo.client.typed` (stdlib-only module)

`Ref[T]` gets a new `model_class: type | None` field. This module must remain importable
without Pydantic. `type | None` is a stdlib annotation — safe.

### `godoo.client._pydantic_transform` (Pydantic module — lazy import only)

Two additions:
1. `_extract_model_class_from_annotation(annotation)` — returns the `T` from `Ref[T]`
   if `T` has `__odoo_model__`, else `None`. Used by `_odoo_wire_transforms` when
   constructing `Ref` instances.
2. `to_odoo_write_payload(instance, *, exclude: set[str] | None = None) -> dict[str, Any]`
   — takes an `OdooBaseModel` instance, calls `model_dump(exclude_unset=True, mode='json')`,
   strips `id`, transforms `Ref`→`int`, `None`→`False`. Returns a dict safe to pass to
   `client.call(model, 'write', [ids, payload], {})`.

### `godoo.client.client` (`OdooClient`)

`write` and `create` get `@overload` typed dispatch mirroring the existing `read`
pattern:

```python
@overload
async def write(self, model: type[T], instance: T, **kwargs) -> bool: ...
@overload
async def write(self, model: str, ids: int | list[int], values: dict, **kwargs) -> bool: ...
```

The typed branch calls `to_odoo_write_payload(instance)` from `_pydantic_transform`
(lazy import). The `str` branch is unchanged from v1.0.

### `godoo.client.errors` (SEED-003)

`OdooRpcError` changes:
- `data` renamed to `raw`
- New keyword-only init params: `model_name`, `field_name`, `constraint_name`, `human_message`
- `_categorize_error` in `transport.py` calls a new `_parse_fault(data) -> FaultInfo` helper
  (a dataclass) that extracts structured fields before constructing the error
- `__str__` returns the stripped `human_message`
- `to_json()` surfaces structured fields, includes `raw` key

---

## What NOT to Add

| What | Why Not |
|------|---------|
| `marshmallow` or any serialization library | `model_dump` already does it; one serialize/validate library is the constraint |
| `lxml` or `html.parser` for traceback stripping | Tracebacks are plain text strings; `re.sub` is sufficient |
| `pydantic-extra-types` | No date/currency/phone handling needed beyond stdlib |
| Any new optional extra in pyproject.toml | All new code is behind the existing `godoo[typed]` gate or stdlib-only |
| `model_config = {'populate_by_name': True}` or alias changes | No aliases; Odoo field names ARE the Python names |
| `model_serializer` on `OdooBaseModel` | Write-direction transform belongs in a standalone function, not a Pydantic hook — keeps it testable without model instances |

---

## Version Table (Unchanged from v1.1 — No Bumps Required)

| Library | Installed Version | pyproject.toml Constraint | Location |
|---------|------------------|--------------------------|----------|
| pydantic | 2.13.4 | `>=2.13` | `godoo-client[typed]` optional extra |
| typer | 0.26.5 | `>=0.26` | `godoo-introspection` runtime dep |
| httpx | 0.28.1 | `>=0.27` | `godoo-client` runtime dep (sole) |

No version bumps needed. No new entries.

---

## Sources

- Pydantic 2.13 `model_dump` API: https://pydantic.dev/docs/validation/latest/api/pydantic/base_model/ (verified 2026-06-02)
- Pydantic 2.13 serialization concepts: https://pydantic.dev/docs/validation/latest/concepts/serialization/ (verified 2026-06-02)
- Pydantic 2.13 model construction / `model_fields_set`: https://pydantic.dev/docs/validation/latest/concepts/models/ (verified 2026-06-02)
- `Ref[T]` generic arg retrieval: `get_args(Ref[SomeModel])[0]` returns class — confirmed via `uv run python` (2026-06-02)
- `model_dump(exclude_unset=True)` and `model_fields_set` behaviour: confirmed via `uv run python` against pydantic 2.13.4 (2026-06-02)
- `model_dump(mode='json')` date→ISO string: confirmed via `uv run python` (2026-06-02)
- `json.dumps` rejection of `date` objects: confirmed via `uv run python` (2026-06-02)
- `Ref` equality with `compare=False`: confirmed via `uv run python` (2026-06-02)
- Existing `errors.py` hierarchy: read directly from `packages/godoo-client/src/godoo/client/errors.py`
- Existing `transport.py` fault parsing: read directly from `packages/godoo-client/src/godoo/client/rpc/transport.py`
- Existing `_pydantic_transform.py` wire transforms: read directly from source

---

*Stack research for: godoo-py v1.2 Typed Relations, Writes & Error Surface*
*Researched: 2026-06-02*
