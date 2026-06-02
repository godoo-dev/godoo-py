---
phase: 10-typed-relation-resolution
reviewed: 2026-06-02T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - packages/godoo-client/src/godoo/client/_pydantic_transform.py
  - packages/godoo-client/src/godoo/client/client.py
  - packages/godoo-client/src/godoo/client/typed.py
  - packages/godoo-client/tests/test_pydantic_transform.py
  - packages/godoo-client/tests/test_rel_resolution.py
  - packages/godoo-client/tests/test_typed.py
  - packages/godoo-client/tests/test_typed_dispatch.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-06-02T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 10 adds typed relation resolution: a `_target_cls` carried on `Ref[T]`, wire-transform
population of that field, and `OdooClient.read()` overloads that dispatch on `Ref` / `list[Ref]`
to batch-resolve relations. The dispatch logic, batching, dedup, and order-stitching are mostly
sound and well tested for the happy paths. However, the resolution path has two un-handled
failure modes that crash with raw, untyped exceptions instead of the project's typed error
contract, and the `Ref[T]` resolution recursion does not re-validate that the target class is a
typed model — a `Ref` whose `_target_cls` is a plain (non-`__odoo_model__`) class silently
routes the class *object* into the str RPC path as a model name. The test suite covers
happy paths thoroughly but has zero coverage for the partial-success and missing-record cases
that the BLOCKER findings describe.

## Critical Issues

### CR-01: `read(Ref)` / `read(list[Ref])` raises bare `KeyError` when Odoo omits a record

**File:** `packages/godoo-client/src/godoo/client/client.py:242-248`
**Issue:** The resolution path builds `fetched` from whatever records Odoo's `read` returns,
then stitches results back with `fetched[(r._target_cls, r.id)]`. Odoo's `read` silently drops
ids the current user cannot access (ACL filtering) or that no longer exist (deleted between the
m2o snapshot and the resolve call). When that happens, the requested id is absent from `fetched`
and line 248 raises a bare `KeyError(( <cls>, <id> ))`.

This is a real, reachable production scenario: a `Ref` captured from an earlier read is resolved
later, and the target record was deleted or ACL-restricted in the interim. The whole point of the
typed error tree (`OdooMissingError`, `OdooValidationError`) is that callers can catch domain
errors; a raw `KeyError` leaks an internal tuple and bypasses that contract. The dedup at line 239
guarantees each id is requested once, so a short result list is the *only* signal of a missing
record, and it is not checked.

**Fix:**
```python
ordered: list[Any] = []
for r in refs:
    record = fetched.get((r._target_cls, r.id))
    if record is None:
        raise OdooMissingError(
            f"Ref(id={r.id}) on {r._target_cls.__name__} could not be resolved "
            "— the record was not returned by Odoo (deleted or access-restricted)."
        )
    ordered.append(record)
```
(Import `OdooMissingError`; it is already exported from `godoo.client.errors`.)

### CR-02: `Ref` resolution routes a class object into the str RPC path when `_target_cls` is not a typed model

**File:** `packages/godoo-client/src/godoo/client/client.py:243-244`
**Issue:** The resolve loop calls `await self.read(target_cls, target_ids)`. The recursive `read`
only takes the typed branch when `hasattr(target_cls, "__odoo_model__")` (line 256). `_target_cls`
is populated by `_ref_target_class()`, which returns *any* `type` it finds in the annotation —
including `object` for a `Ref[object]` field (proven by `test_m2o_bare_ref_target_cls_none`, which
asserts `_target_cls is object`). For such a `Ref`, `_target_cls is not None`, so the up-front
guard at line 227-232 passes, but `hasattr(object, "__odoo_model__")` is `False`. The recursion
then falls through to the str path (line 280) and calls `self.call(object, "read", [id_list], {})`
with a **class object as the `model` argument**. That is sent over JSON-RPC as the model name,
producing a confusing server-side failure (or a `TypeError`/serialization error) rather than the
intended typed resolution or a clean local validation error.

The guard at 227-232 checks only `_target_cls is None`; it must also confirm the target is an
actual Odoo-typed model. `Ref[object]` is the documented fallback annotation (`typed.py` docstring,
and `_TestPartner.parent_id: Ref[object]`), so this is not a contrived input.

**Fix:** Tighten the guard to require a typed model, not merely a non-`None` type:
```python
bad = [r for r in refs if not hasattr(r._target_cls, "__odoo_model__")]
if bad:
    raise OdooValidationError(
        f"Cannot resolve Ref(id={bad[0].id}): target {bad[0]._target_cls!r} "
        "is not a typed Odoo model (came from an untyped or Ref[object] field)."
    )
```

## Warnings

### WR-01: Empty `list[Ref]` silently falls through to the str RPC path with `model=[]`

**File:** `packages/godoo-client/src/godoo/client/client.py:224`
**Issue:** The dispatch guard is `isinstance(model, list) and model and isinstance(model[0], Ref)`.
For an empty list (`await client.read([])`), `model` is falsy, so the Ref branch is skipped.
Execution falls to line 253 (`id_list = ... ids or []` → `[]`) and then to the str path at line
280, calling `self.call([], "read", [[]], {})` — the empty list is passed as the Odoo model name.
A caller resolving a dynamically-built, possibly-empty list of refs gets an opaque RPC failure
instead of an empty result. The natural, correct behavior is to return `[]`.

**Fix:** Special-case the empty list before the str path, e.g. at the top of `read`:
```python
if isinstance(model, list) and not model:
    return []
```
(Place it so it does not collide with the existing `model: type[T]` overloads — an empty list is
unambiguously the `list[Ref]` case.)

### WR-02: `read()` typed path with `fields` can crash validation when a required base field is excluded

**File:** `packages/godoo-client/src/godoo/client/client.py:265-275`
**Issue:** In the `read` typed branch, when `fields` is provided, `derive_partial_model` makes only
the *requested* fields `Optional`. Non-requested fields that are **required** on the base model
(no default) stay required. `read()` deliberately does not inject `id`, relying on Odoo always
returning it — true for `id`, but any *other* required field (e.g. a codegen model with
`name: str` and no default) that the caller omits from `fields` will be absent from the raw dict,
and `target.model_validate(r)` raises a pydantic `ValidationError` (not an `OdooValidationError`).
The `search_read` path has the same shape but is partly masked because it injects `id`. This is a
latent crash for any non-trivial generated model the moment a caller does a projected read that
drops a required field. The test models (`TinyPartner`, `_TestPartner`) all give every non-`id`
field a default, so the suite never exercises this.

**Fix:** Either (a) document and enforce that generated models must default every field to `None`
(All-Optional at the source), or (b) in `derive_partial_model`, when building the partial, relax
*all* non-requested base fields to optional as well (so a projected read never fails on an
unrequested required field), or (c) catch pydantic `ValidationError` around `model_validate` and
re-raise as `OdooValidationError`. Add a test with a model that has a second required field and a
projected read excluding it.

### WR-03: Cache key `(id(model), frozenset(fields))` can collide after GC reuses an id

**File:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py:204, 19`
**Issue:** `_partial_model_cache` is keyed on `id(model)`. The cache holds a strong reference to
the *derived* class but **not** to the source `model`. If the source model class is garbage
collected (e.g. a model defined inside a function, as several tests do), CPython can reuse its
`id()` for a different, unrelated class. A subsequent `derive_partial_model(other_model, fields)`
with the same field set would then hit the stale cache entry and return a partial of the *wrong*
base model — a silent correctness bug. The codegen-emitted models are module-level and long-lived,
so this is unlikely in the primary use case, but it is a genuine soundness hole in a public helper,
and `abs(hash(key))` in the generated class name (line 219) does not disambiguate because the key
itself collides.

**Fix:** Key on the class object directly via a `WeakKeyDictionary` keyed by `model`, with an
inner dict keyed by `frozenset(fields)` — this both prevents id-reuse collisions and lets entries
be reclaimed when the model dies:
```python
from weakref import WeakKeyDictionary
_partial_model_cache: WeakKeyDictionary[type[BaseModel], dict[frozenset[str], type[BaseModel]]] = WeakKeyDictionary()
```

### WR-04: `_ref_target_class` returns the first type arg without verifying it relates to `Ref`

**File:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py:52-71`
**Issue:** The function's contract (docstring) is "Return the T in `Ref[T]` if annotation mentions
Ref, else None." But the recursion at line 67-70 descends into *any* arg that itself has args,
regardless of whether that arg is a `Ref`. For an annotation like `list[SomeClass] | None` (no
`Ref` anywhere) the function would still descend and could return a type that has nothing to do
with `Ref`. In the wire transform this helper is only reached after `_annotation_mentions_ref`
gates the branch (line 158), so the live blast radius is contained — but the function is also
called directly (it is imported and unit-tested in `test_pydantic_transform.py`) and its return
value is silently stamped onto `Ref._target_cls`, which CR-02 shows is load-bearing for dispatch.
A target class extracted from a non-`Ref` annotation is a latent source of mis-dispatch.

**Fix:** Make the recursion `Ref`-aware: only return a type when it is the argument of a `Ref`
origin. Mirror `_annotation_mentions_ref` exactly — descend only when the sub-arg's chain actually
contains a `Ref` origin, and never return a type pulled from a non-`Ref` generic. Add a test:
`_ref_target_class(list[_Model] | None)` must return `None`.

## Info

### IN-01: `from collections import defaultdict` imported inside the function body

**File:** `packages/godoo-client/src/godoo/client/client.py:234`
**Issue:** `defaultdict` is a stdlib import with no circular-import or optional-dependency concern
(unlike the deliberate lazy `_pydantic_transform` import). Importing it inside the hot dispatch
path on every `Ref` resolve is unidiomatic and slightly wasteful. The lazy-import convention in
this codebase exists specifically to avoid circular imports and optional `[typed]` deps — neither
applies here.
**Fix:** Move `from collections import defaultdict` to the module top-level import block.

### IN-02: `# type: ignore[index]` at line 248 masks the missing-record bug

**File:** `packages/godoo-client/src/godoo/client/client.py:248`
**Issue:** The `# type: ignore[index]` suppresses mypy on the dict subscript that CR-01 shows can
raise `KeyError`. The ignore is there to silence the `r._target_cls` being `type | None`, but it
also signals that the indexing was known to be type-unsafe and was waved through rather than
guarded. Once CR-01 is fixed with `.get()` + explicit check, this ignore can be removed entirely.
**Fix:** Remove after applying the CR-01 fix (the `.get()` form needs no ignore once `_target_cls`
is narrowed by the CR-02 guard).

### IN-03: Test coverage gap — no test for partial-resolution / missing-record paths

**File:** `packages/godoo-client/tests/test_rel_resolution.py` (whole file)
**Issue:** `test_rel_resolution.py` covers single-ref, homogeneous, heterogeneous, and untyped-ref
paths, but every mock returns a complete result set. There is no test where Odoo returns *fewer*
records than requested (CR-01), no test for an empty `list[Ref]` (WR-01), and no test for a
`Ref[object]` / non-typed `_target_cls` reaching `read()` resolution (CR-02). These are exactly
the failure modes that crash. The phase's own VERIFICATION should not be considered complete
without them.
**Fix:** Add: (1) a mock returning `[]` for a single typed `Ref` → expect `OdooMissingError`;
(2) `read([])` → expect `[]`; (3) `read(Ref(id=1, name="X", _target_cls=object))` → expect
`OdooValidationError` before any RPC (assert `len(respx.calls) == 0`).

---

_Reviewed: 2026-06-02T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
