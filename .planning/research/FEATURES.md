# Feature Research

**Domain:** Typed relational resolution, typed writes, and structured error surface for an async Odoo JSON-RPC client library
**Researched:** 2026-06-02
**Confidence:** HIGH (Odoo RPC semantics are stable and well-documented; Pydantic patterns are verified against v2 docs; existing v1.1 codebase inspected directly)

---

## Scope Note

This document covers ONLY the three NEW v1.2 features. The shipped v1.1 foundation
(Pydantic model generator, `@overload` dispatch, wire transforms, `OdooBaseModel`,
`Ref[T]`, `godoo[typed]` extra) is treated as **existing infrastructure** — not
re-researched.

Three features are in scope:

- **TYPED-F1** — Ref-driven typed relation resolution: `client.read(ref)` / `client.read(list[Ref])` resolves a typed `Ref[T]` into the related model instance, batched, single-level deep.
- **TYPED-F2** — Typed write/create: pass `OdooBaseModel` instances into `client.write` / `client.create`.
- **SEED-003** — Restructured `OdooError` hierarchy: structured fields, traceback/path stripping, `.raw` escape hatch.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in a mature typed client. Missing these makes the typed
layer feel half-finished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **TYPED-F1-A: `client.read(ref)` resolves a single `Ref[T]` to `T`** | Users hold `Ref[ResPartner]` objects from reads. The obvious next step is "give me the full record". Without this the Ref type is a dead end — callers must manually extract `.id`, choose a model class, and call `read()` themselves. | LOW | `Ref[T]` carries both the id and the target class at runtime (the `T` parameter). Resolution is one `client.read(T, [ref.id])` call. Returns `T | None` (None if Odoo returns empty, e.g. record deleted). |
| **TYPED-F1-B: `client.read(list[Ref[T]])` batches refs of the same type into one RPC call** | N separate `read` calls for N relations is the classic N+1 problem. SQLAlchemy's `selectinload`, Strawberry's DataLoader, and every mature Python ORM/client batch by default. Users who resolve a list of refs expect one RPC per distinct target model, not one per ref. | MEDIUM | Group refs by `T.__odoo_model__`. Per group: deduplicate ids, call `client.read(T, [ids])`, stitch results back by id into a `dict[int, T]`. Mixed-type list (`list[Ref[A] \| Ref[B]]`) batches separately per type. |
| **TYPED-F2-A: `client.create(instance)` accepts an `OdooBaseModel` instance** | Every ORM (SQLAlchemy, Django, Peewee) lets you call `session.add(obj)` or `Model.objects.create(instance)`. In a typed API client (FastAPI, argo, openapi-python-client), you pass a model instance to the create call. Users expect this. | MEDIUM | Extract writable fields from the instance using `model_dump(exclude_unset=True)` to honour partial construction — only explicitly-set fields sent. Serialize `Ref[T]` → int id (m2o write format). Do NOT send computed/readonly fields (see field exclusion below). Return int id. |
| **TYPED-F2-B: `client.write(ids, instance)` accepts an `OdooBaseModel` instance** | Same ergonomic expectation as create. SQLAlchemy marks changed attributes and only writes them; Django requires `update_fields` but any ORM book teaches the pattern. | MEDIUM | `model_dump(exclude_unset=True)` gives the caller-set fields. Serialize relations. Guard against sending `id` (Odoo's write ignores it but it is misleading). |
| **SEED-003-A: `OdooRpcError` exposes structured `model`, `field`, `constraint` attributes** | Well-designed API client errors (httpx, Stripe SDK, Twilio) expose machine-readable fields, not just a message string. Users who catch `OdooValidationError` need to know WHICH field or constraint failed without string-parsing the message. | MEDIUM | Parse Odoo's `data.message` and `data.arguments` to extract the model/field/constraint where the pattern is stable. Store as typed optional attributes: `model: str \| None`, `field: str \| None`, `constraint: str \| None`, `human_message: str`. |
| **SEED-003-B: Server traceback stripped from default error surface** | Today `OdooRpcError.data` contains the raw `data.debug` traceback and internal file paths verbatim. Any caller who logs `err.to_json()` leaks server internals, file paths, and potentially arguments that include record values. Stripe, Twilio, and every production-grade SDK strips internal traces before surfacing to callers. | LOW | `to_json()` and the primary `str(err)` message must not include `data.debug` content. The traceback and raw data dict are preserved in `err.raw` (see SEED-003-C). |
| **SEED-003-C: `.raw` escape hatch preserves original error dict for debugging** | Developers debugging Odoo integration failures need the full picture — exception class name, traceback, arguments. Stripping without preserving is a support nightmare. httpx preserves `.response`, requests preserves `.response`, every mature client preserves the original artifact. | LOW | `OdooRpcError.raw: dict[str, Any]` holds the original unmodified `error_dict` from Odoo. Opt-in: callers who need the full traceback inspect `err.raw["data"]["debug"]`. Not serialized by `to_json()`. |

### Differentiators (Competitive Advantage)

Features that go beyond what comparable clients provide and are specific to godoo's
design.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **TYPED-F1-C: Mixed-type `Ref` list batched per target model** | Most relation resolvers only handle homogeneous lists (DataLoader keys are a single type). godoo's API naturally receives heterogeneous relation lists (a record with multiple m2o fields of different types). Batching all same-type refs together in a single pass is a clean zero-config N+1 solution. | MEDIUM | `read(refs: list[Ref])` where refs are of mixed `T` types. Group by `T.__odoo_model__`, one `client.read(T, [ids])` per group. Return `list[T]` in original ref order. Requires a type union return — likely `list[OdooModel]` at the untyped level, or a sequence of matching types per group. |
| **TYPED-F2-C: x2many write ergonomics via helper type** | Odoo's x2many wire format (`[(6,0,[ids])]` for replace, `[(0,0,{vals})]` for create-and-link, `[(1,id,{vals})]` for update-in-place) is cryptic. No existing Python Odoo client provides a typed wrapper that converts human-readable intent to command tuples. | HIGH | Define `X2ManyCommand` helpers: `replace(ids: list[int])` → `(6,0,ids)`, `add(id: int)` → `(4,id,0)`, `remove(id: int)` → `(3,id,0)`, `create_and_link(values: dict)` → `(0,0,values)`, `update(id: int, values: dict)` → `(1,id,values)`, `clear()` → `(5,0,0)`. The typed write path serializes `list[int]` x2many fields as `(6,0,[ids])` automatically (replace semantics as default). **Mark HIGH complexity because the semantics question requires a clear decision: does `list[int]` on an x2many model instance mean REPLACE or something else?** See anti-features. |
| **SEED-003-D: `human_message` derived from Odoo's cleaned error message** | Odoo `data.message` is usually human-readable but sometimes wrapped in technical context. Exposing a clean `human_message` attribute means callers can surface it directly to users without string surgery. | LOW | `human_message` = `data.message` stripped of stack-trace prefix lines and internal path tokens. Requires light regex; Odoo message format is stable enough across versions. |
| **TYPED-F1-D: Identity-map cache within a single `read()` call** | If the caller passes a list with duplicate ref ids pointing to the same target model, only one record fetch per unique id. This is SQLAlchemy's identity map at the call level — not a session-level cache (which would be an anti-feature). | LOW | Deduplication of ids before the RPC call is trivial (`list(dict.fromkeys([r.id for r in refs]))`). Stitch back using the id map. |

### Anti-Features (Deliberately NOT Building)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Ref auto-fetch on attribute access (lazy loading)** | `partner.parent_id` → automatically fetches the `ResPartner` for `parent_id.id`. Mimics SQLAlchemy lazy load. | Requires async attribute access, which is not idiomatic Python (no `async` properties without workarounds). Creates invisible RPC calls. SQLAlchemy itself is moving AWAY from implicit lazy loading in async contexts. | Explicit `client.read(partner.parent_id)` (TYPED-F1). The caller decides when to fetch. |
| **Session-level identity map / result cache across calls** | Callers who read the same record twice don't want two RPC calls. | Stale data in long-running processes. Makes testing harder (cache invalidation). Adds mutable state to the client. Not needed for scripting/automation use cases which is godoo's target. | Per-call deduplication within `read(list[Ref])` only. No cross-call caching. |
| **Deep/recursive relation resolution** | `client.read(partner, depth=3)` auto-fetches the full object graph. | N^depth RPC calls. Circular model references (partner → company → parent_company → ...). Odoo has no native join fetch; this is purely client-side and very expensive. | Single-level explicit resolution. Callers chain `read()` calls if they need depth. |
| **Automatic x2many → full model resolution** | `sale_order.order_line` (list of ids) auto-fetches all `SaleOrderLine` records. | Same as deep resolution — bandwidth and latency explode silently. | x2many stays as `list[int]` by default. Caller explicitly calls `client.read(SaleOrderLine, order.order_line)` when needed. |
| **`write(instance)` sends ALL fields including `id`, computed, and unset** | Seems like a "full save". | Sending `id` is at best a no-op and at worst triggers Odoo errors on some model constraints. Sending computed/readonly fields raises `"Cannot update a readonly field"`. Sending unset fields (those with `None` default from all-Optional design) overwrites server values with null. | `model_dump(exclude_unset=True)` sends only caller-set fields. Computed/readonly fields excluded by an allowlist or via `fields_get` attribute metadata. |
| **x2many automatic REPLACE semantics for `list[int]` write** | Treating `model.child_ids = [1,2,3]` as "replace all children with these ids" feels natural. | Silently destructive. `(6,0,[ids])` removes all existing relations not in the list. A user who sets partial x2many intending to ADD items deletes all others. The semantics must be explicit. | Explicit `X2ManyCommand` helpers (see differentiators). Default: if `list[int]` is passed, serialize as `(4, id, 0)` per id (ADD semantics, not REPLACE). Explicit replace requires `X2ManyCommand.replace([ids])`. |
| **Error message parsing to extract field names via fragile regex** | Appealing for "smart" error attribution. | Odoo error messages are not guaranteed stable across versions. Custom modules produce unpredictable message formats. Regex-based field extraction will produce silent wrong attributions. | Parse only the `data.arguments` array and `data.name` (which is the Python exception class name, stable). For `model`/`field`/`constraint`: populate only when derivable from structured data, not message text. |

---

## Feature Dependencies

```
TYPED-F1 (Ref resolution)
    └──requires──> v1.1: Ref[T] dataclass with runtime T parameter
    └──requires──> v1.1: OdooBaseModel (@overload dispatch, client.read(type[T]))
    └──requires──> v1.1: godoo[typed] optional extra

TYPED-F2 (Typed write/create)
    └──requires──> v1.1: OdooBaseModel (model_dump, model_fields_set)
    └──requires──> v1.1: Ref[T] (m2o serialization: Ref.id → int)
    └──requires──> existing: client.write() / client.create() (raw dict path, to wrap)
    └──enhances──> TYPED-F1: a round-trip pattern — read typed, modify, write back

SEED-003 (Error surface)
    └──requires──> existing: OdooRpcError hierarchy in errors.py
    └──requires──> existing: _categorize_error() in transport.py
    └──independent──> TYPED-F1 and TYPED-F2 (no direct dependency)
    └──complements──> TYPED-F2: write errors now expose model/field/constraint

X2ManyCommand helpers (TYPED-F2-C differentiator)
    └──requires──> TYPED-F2 (typed write path must exist first to consume commands)
    └──optional: can ship in a follow-up task after basic TYPED-F2
```

### Dependency Notes

- **TYPED-F1 requires `Ref[T]` to carry `T` at runtime.** The current `Ref[T]` is a frozen
  dataclass with `id: int` and `name: str | None`. For resolution to work,
  `client.read(ref)` needs to know the target model class from the ref itself. This
  requires either: (a) `Ref.__class_getitem__` stores the type arg and makes it
  retrievable at runtime, or (b) a separate `TypedRef[T]` subclass carries `model_class:
  type[T]` as a field. Option (b) is simpler and avoids metaclass magic. **This is the
  single largest open design question for TYPED-F1.**

- **TYPED-F2 uses `model_dump(exclude_unset=True)`.** The all-Optional model design from
  v1.1 means every field defaults to `None` — so `exclude_unset=True` is the only
  correct way to distinguish "caller explicitly set this field to None (clear it)" from
  "caller never touched this field (leave server value alone)". This is the same pattern
  used by FastAPI PATCH endpoint implementations.

- **TYPED-F2 must serialize `Ref[T]` → int on write.** m2o fields are written as plain
  `int` id in Odoo (not the `[id, "name"]` tuple form used for reads). The write
  serializer must unwrap `Ref(id=42, name="ACME")` → `42`.

- **TYPED-F2 field exclusion strategy.** Odoo's `fields_get` returns `readonly` and
  `store` attributes per field. Sending a readonly/computed (store=False) field to
  `write()` raises `"Cannot update a readonly field"`. Two strategies:
  (a) **client-side exclusion** — read `fields_get` to build an allowlist, cache per
  model. Requires an extra RPC on first write per model type.
  (b) **caller-driven exclusion** — do not pre-filter; let Odoo reject; surface error
  via SEED-003 structured error. No extra RPC. The caller is responsible for not
  sending computed fields.
  Option (b) is simpler and avoids the `fields_get` cache management complexity.
  The `exclude_unset=True` pattern already protects callers who construct instances
  only from values they read (generated fields that are readonly will simply not be
  in `model_fields_set` unless the caller explicitly set them).

- **SEED-003 is independent but should ship in the same milestone.** The v1.2 write path
  will exercise validation errors. Structured errors make write failures actionable
  immediately. Shipping SEED-003 alongside TYPED-F2 closes the feedback loop.

---

## MVP Definition

### v1.2 Launch Set

All three features are in scope for v1.2. Relative priority:

- **SEED-003** first — it is independent and improves the foundation. Error surface
  improvements benefit existing users immediately and every subsequent feature.
- **TYPED-F2** second — typed writes complete the read-modify-write round-trip.
  The basic create/write with `model_dump(exclude_unset=True)` is the core. x2many
  command helpers (TYPED-F2-C) can follow as a second task within the same phase.
- **TYPED-F1** third — Ref resolution is the most complex due to the runtime `T`
  parameter design question. Builds directly on the existing `Ref[T]` and typed read
  dispatch.

### Add After Validation (v1.x)

- `X2ManyCommand` full helper set (TYPED-F2-C) — if the basic list[int] handling ships
  first, the helper types can follow once callers confirm the ergonomics are right.
- `fields_get` allowlist caching for computed-field auto-exclusion on write — only if
  callers report friction from Odoo "readonly field" errors.

### Future Consideration (v2+)

- Multi-level Ref resolution (`depth=2` or chained explicit resolution helpers) — once
  single-level usage patterns are understood.
- Session-scoped identity map as an opt-in plugin — only if automation scripts
  demonstrate clear benefit.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SEED-003-B: traceback stripping | HIGH (security) | LOW | P1 |
| SEED-003-A: structured error fields | HIGH (DX) | MEDIUM | P1 |
| SEED-003-C: `.raw` escape hatch | MEDIUM | LOW | P1 |
| TYPED-F2-A: `create(instance)` | HIGH | MEDIUM | P1 |
| TYPED-F2-B: `write(ids, instance)` | HIGH | MEDIUM | P1 |
| TYPED-F1-A: `read(ref)` single | HIGH | LOW | P1 |
| TYPED-F1-B: `read(list[Ref])` batched | HIGH | MEDIUM | P1 |
| TYPED-F1-D: per-call id deduplication | MEDIUM | LOW | P1 (free with batching) |
| TYPED-F2-C: X2ManyCommand helpers | MEDIUM | HIGH | P2 |
| TYPED-F1-C: mixed-type ref list | LOW | MEDIUM | P2 |
| SEED-003-D: human_message cleanup | LOW | LOW | P2 |

**Priority key:**
- P1: Must ship in v1.2
- P2: Should ship in v1.2 if time allows; can defer to v1.3
- P3: Nice to have, future consideration

---

## Odoo-Specific Write Semantics (Normative Reference)

These are the exact wire formats TYPED-F2 must serialize to. High confidence — cross-verified
against official Odoo ORM docs and odoo-development.readthedocs.io.

### many2one write format

Write an integer id. NOT a tuple.

```python
# Write: set partner_id to record with id=42
{"partner_id": 42}

# WRONG — this is the READ wire format, not write
{"partner_id": [42, "ACME Corp"]}
```

The typed write layer must serialize `Ref(id=42, name="ACME Corp")` → `42`.

### x2many command tuple format

All x2many fields (one2many, many2many) use a list of 3-element command tuples:

| Code | Meaning | Tuple format | Compatibility |
|------|---------|-------------|---------------|
| 0 | Create new record and link | `(0, 0, {values})` | create + write |
| 1 | Update existing linked record | `(1, id, {values})` | write only |
| 2 | Delete and unlink record | `(2, id, 0)` | write only; one2many only |
| 3 | Unlink (remove relation, keep record) | `(3, id, 0)` | write only; many2many only |
| 4 | Link existing record | `(4, id, 0)` | write only; many2many only |
| 5 | Clear all relations | `(5, 0, 0)` | write only; many2many only |
| 6 | Replace entire set (clear + link) | `(6, 0, [ids])` | write only; many2many only |

The underscore positions accept `0` or `False` as placeholders.

**Default serialization decision for TYPED-F2:** When a `list[int]` is present in the
instance's set fields for an x2many annotation, serialize as `[(4, id, 0) for id in ids]`
(ADD semantics). This is the least destructive default. REPLACE semantics require an
explicit `X2ManyCommand.replace([ids])` call. This decision avoids the silent-delete
anti-feature described above.

### Computed / readonly field behavior

Sending a computed field with no `inverse` function to `write()` raises Odoo's
`"Cannot update a readonly field"` error server-side. Computed fields do NOT silently
ignore writes — they raise. The typed write path should NOT pre-filter on a `fields_get`
allowlist (option b from dependency notes above) — let Odoo raise, surface via SEED-003
structured error. The `exclude_unset=True` pattern naturally avoids this for typical
read-modify-write flows.

---

## Existing v1.1 Foundation — What TYPED-F1/F2 Builds On

| v1.1 Component | How v1.2 Uses It |
|----------------|-----------------|
| `Ref[T]` dataclass (`typed.py`) | TYPED-F1: the input to `client.read(ref)`. Needs runtime T access — design question open. |
| `OdooBaseModel` (`_pydantic_transform.py`) | TYPED-F2: `model_dump(exclude_unset=True)` + `model_fields_set` for partial write. |
| `@overload` dispatch on `client.read` | TYPED-F1: adds new overload for `read(Ref[T]) -> T \| None` and `read(list[Ref]) -> list[...]`. |
| `derive_partial_model()` cache | TYPED-F1: NOT used for resolution (full model fetch, not partial). |
| `client.create()` / `client.write()` raw dict path | TYPED-F2: new overloads wrap these; existing raw paths unchanged. |
| `OdooRpcError` tree + `_categorize_error()` | SEED-003: both files modified. `_categorize_error()` grows structured field population; `OdooRpcError` gains `model`, `field`, `constraint`, `human_message`, `raw` attributes. |
| `to_json()` on all error classes | SEED-003: updated to serialize structured fields, omit `raw`/traceback. Breaking change on `.data` attribute (now becomes `.raw`). |

---

## Sources

- [Odoo 17.0 External API docs](https://www.odoo.com/documentation/17.0/developer/reference/external_api.html) — create/write method behaviour
- [odoo-development.readthedocs.io — x2many command tuples](https://odoo-development.readthedocs.io/en/latest/dev/py/x2many.html) — authoritative command codes 0–6
- [FastAPI body-updates docs](https://fastapi.tiangolo.com/tutorial/body-updates/) — `exclude_unset` PATCH pattern
- [Pydantic serialization — exclude_unset](https://docs.pydantic.dev/dev/concepts/serialization/) — `model_dump(exclude_unset=True)` and `model_fields_set`
- [odoo-rpc-client jsonrpc source](https://odoo-rpc-client.readthedocs.io/en/latest/_modules/odoo_rpc_client/connection/jsonrpc.html) — how existing clients expose debug/traceback (they expose it verbatim — anti-pattern)
- [Strawberry DataLoader docs](https://strawberry.rocks/docs/guides/dataloaders) — batched async relation resolution pattern
- [SQLAlchemy selectinload docs](https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html) — selectinload as the canonical batched-not-joined eager load pattern
- [Odoo JSON-RPC error structure](https://www.braincuber.com/tutorial/odoo-19-api-errors-complete-guide) — `data.name`, `data.debug`, `data.message`, `data.arguments` fields confirmed
- [django-dirtyfields](https://github.com/romgar/django-dirtyfields) — dirty-field tracking as an ORM pattern
- [Roman Imankulov — Handling Unset Values in FastAPI with Pydantic](https://roman.pt/posts/handling-unset-values-in-fastapi-with-pydantic/) — unset vs None ergonomics
- Existing codebase: `errors.py`, `transport.py`, `_pydantic_transform.py`, `typed.py`, `client.py` — inspected directly for current state

---
*Feature research for: godoo-py v1.2 — Typed Relations, Writes & Error Surface*
*Researched: 2026-06-02*
