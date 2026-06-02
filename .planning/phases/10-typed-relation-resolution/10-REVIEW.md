---
phase: 10-typed-relation-resolution
reviewed: 2026-06-02T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - packages/godoo-client/src/godoo/client/typed.py
  - packages/godoo-client/src/godoo/client/_pydantic_transform.py
  - packages/godoo-client/src/godoo/client/client.py
  - packages/godoo-client/tests/test_typed_dispatch.py
  - packages/godoo-client/tests/test_rel_resolution.py
findings:
  critical: 2
  warning: 3
  info: 2
  total: 7
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-06-02T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

This phase adds `Ref[T]._target_cls` capture (Plan 01) and the `OdooClient.read(Ref[T])` dispatch branch (Plan 02). The core data-flow design is sound and the TDD approach is solid. However, two Critical bugs were found: a `KeyError` crash that silently drops records returned out-of-id-order from Odoo, and a behaviorally incorrect detection condition for a list of `Ref` objects that silently misfires on any non-empty `list[non-Ref]`. Three Warnings cover a partially broken `_ref_target_class` recursion path, a missing overload for the duplicate-refs de-duplication semantic, and the assert-as-guard pattern in production code.

---

## Critical Issues

### CR-01: `fetched` dict KeyError crash when Odoo returns records out of id-order or omits missing ids

**File:** `packages/godoo-client/src/godoo/client/client.py:248`

**Issue:** The stitch loop at line 248 builds `ordered` by doing `fetched[(r._target_cls, r.id)]` for every `r` in the original `refs` list. The `fetched` dict is populated by iterating over the typed RPC result (line 245-246). If Odoo returns records in a different order than the requested ids — or omits a record entirely (deleted record, ACL restriction, etc.) — the key `(target_cls, r.id)` will be absent and the line raises an unhandled `KeyError`, crashing the call site with no `OdooMissingError` or other typed exception.

This is a correctness bug, not just a robustness concern. The plan says "one batched `self.read(target_cls, ids)`" but `read()` on a non-existent or ACL-restricted record simply omits it from the result — it does not raise. The existing typed path at line 275 (`[target.model_validate(r) for r in raw]`) also returns a short list in that case; the downstream caller would get a `KeyError` rather than the missing-id behaviour the project already handles via `OdooMissingError` in other methods.

**Fix:**
```python
# Replace the stitch at line 248 with a .get() and explicit missing-id handling:
ordered = []
for r in refs:
    record = fetched.get((r._target_cls, r.id))
    if record is None:
        from godoo.client.errors import OdooMissingError
        raise OdooMissingError(
            f"Ref(id={r.id}, model={getattr(r._target_cls, '__odoo_model__', r._target_cls)!r})"
            " was not returned by Odoo — record may be deleted or access-restricted."
        )
    ordered.append(record)
```

---

### CR-02: Ref-list detection fires on any non-empty `list` whose first element happens to be a `Ref`

**File:** `packages/godoo-client/src/godoo/client/client.py:224`

**Issue:** The detection guard is:
```python
isinstance(model, list) and model and isinstance(model[0], Ref)
```
This only inspects `model[0]`. A `list` whose first element is a `Ref` but whose remaining elements are non-`Ref` objects (e.g., mixed content, a user mistake, or a future overload expansion) bypasses the guard silently and reaches the `list(model)` cast at line 226. When a later element is a non-`Ref`, line 227 (`r._target_cls`) raises `AttributeError` with no helpful message. Worse, if a future caller passes a `list[int]` where the first element happens to be wrapped as a `Ref` by accident, the branch fires incorrectly.

The plan acknowledged heterogeneous lists are valid only when all elements are `Ref`. The detection should validate all elements — or at minimum raise a clear `OdooValidationError` when non-`Ref` elements are found, before reaching the batching logic.

**Fix:** Replace the detection + normalise block with an all-elements check:
```python
if isinstance(model, Ref) or (
    isinstance(model, list) and model and isinstance(model[0], Ref)
):
    refs = [model] if isinstance(model, Ref) else list(model)
    # Validate all elements are Ref — guard against mixed lists
    non_ref = [r for r in refs if not isinstance(r, Ref)]
    if non_ref:
        raise OdooValidationError(
            f"read() received a list whose first element is a Ref but element"
            f" {refs.index(non_ref[0])} is not a Ref: {non_ref[0]!r}"
        )
    ...
```

---

## Warnings

### WR-01: `_ref_target_class` recursion path silently returns `None` for nested-generic `Ref[T] | None` when the bare-`Ref` check fires first

**File:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py:63-70`

**Issue:** The recursive fallback at lines 67-70 calls `_ref_target_class(arg)` again for nested generics. However, the loop at line 63 already checks `if get_origin(arg) is Ref` (line 64) before falling into the recursive path. That is correct. But the recursive call at line 68 will re-enter the same top-level logic for `arg`. For `Ref[T] | None` (a common annotation), the union origin is `types.UnionType` (Python 3.10+ `X | Y`) or `typing.Union` — neither is `Ref`. The loop then iterates the args of the union: `Ref[T]` (origin=Ref, handled correctly) and `NoneType`. So for the standard use-case this works.

The subtle bug is in the `get_args(arg)` guard at line 67: for a plain `arg` like `int` or `str`, `get_args(int)` returns `()` — so the guard is `False` and recursion does not fire. For `list[int]`, `get_args(list[int])` returns `(int,)` — truthy — so `_ref_target_class(list[int])` is called recursively. Inside that recursive call, `get_origin(list[int]) is Ref` is `False`, the loop processes `int`, `get_origin(int)` is `None` ≠ `Ref`, `get_args(int)` is `()` — so it returns `None`. This is correct but wasteful. No actual bug for current usage.

However: `_annotation_mentions_ref` has a parallel loop (line 47) that calls itself recursively via `_annotation_mentions_ref(arg)`. The twin function `_ref_target_class` applies the `get_args(arg)` guard before recursing (line 67) whereas `_annotation_mentions_ref` recurses unconditionally if `get_args(arg)` is truthy (line 47 also guards). The structures are symmetric. But `_ref_target_class` at line 63-66 handles only the direct `get_origin(arg) is Ref` case for args of the outer annotation. It does NOT call `_ref_target_class` recursively when `arg` is itself a bare `Ref` (not a generic `Ref[T]`). `_annotation_mentions_ref` handles bare `Ref` at line 44 (`arg is Ref`). `_ref_target_class` has no equivalent check — for a bare `Ref` in args of a union, `get_origin(Ref)` is `None` (not `Ref`), so line 64 misses it. But a bare `Ref` has no type argument, so returning `None` is the correct documented behaviour. No outright bug, but the asymmetry between the two sibling functions is a latent maintenance hazard — adding new code paths may produce silent `None` returns that look correct.

**Fix:** Add a comment cross-referencing the `arg is Ref` case handled by `_annotation_mentions_ref` to prevent future contributors from inadvertently creating a divergence:
```python
# Note: bare Ref (no type arg) in a union is intentionally not handled here —
# get_origin(Ref) is None, so it falls through to return None, which is correct
# (bare Ref carries no target class). See _annotation_mentions_ref for the parallel
# `arg is Ref` check that only needs bool semantics.
```

---

### WR-02: `assert` used as a runtime guard in production dispatch code

**File:** `packages/godoo-client/src/godoo/client/client.py:238`

**Issue:** Line 238 is `assert r._target_cls is not None`. This assertion is reachable in production — it fires after the `bad` list check at line 227, but `assert` statements are silently removed when Python runs with `-O` (optimised mode, `PYTHONOPTIMIZE=1`). Running godoo-client in an optimised interpreter (Docker images, some CI setups) means this guard disappears entirely, and the `groups[r._target_cls]` call at line 239 would use `None` as a dict key, producing silent wrong behaviour (all untyped refs grouped under the same `None` key and then looked up successfully — but then the stitch at line 248 would produce `KeyError` against `(None, r.id)` or worse, return the wrong record).

The `bad`-list check at line 227 already covers this precondition completely — the assert is redundant in non-optimised mode and silently broken in optimised mode.

**Fix:** Remove the assert. The `bad`-list check above is the definitive guard:
```python
# Remove line 238:
# assert r._target_cls is not None  <-- delete this line
```

---

### WR-03: `test_read_homogeneous_list_resolves` and `test_read_heterogeneous_list_preserves_order` RPC-call-count assertions are fragile and test the wrong thing

**File:** `packages/godoo-client/tests/test_rel_resolution.py:101,132`

**Issue:** Both tests assert `len(respx.calls) == 1` and `len(respx.calls) == 2` respectively, using the module-global `respx.calls` collector inside a `@respx.mock` block. The plan's own comment in the test action section notes: "Note: auth_client fixture runs in a different `with respx.mock` scope so its auth call is not visible here."

This is actually true because the `auth_client` fixture uses a nested `with respx.mock:` block, so `respx.calls` is reset when the test's outer `@respx.mock` decorator opens its own scope. The assertion technically works as intended today. However, `respx.calls` is a module-level singleton that is reset per-scope — if test isolation between scopes ever breaks (e.g., a future change to the fixture that moves auth inside the test's own mock scope), these assertions would silently count the auth call too and produce false failures or false passes.

More importantly, neither test asserts anything about *which* RPC was made (i.e., that the ids were correctly batched). A test that calls `read()` twice for the same model separately and then checks `len(respx.calls) == 1` would fail in the intended scenario but still pass the existing assertion if the count happens to be right for the wrong reason.

**Fix:** Add at minimum a payload inspection assertion alongside the call-count check, similar to the pattern already used in `test_typed_dispatch.py` (`_extract_rpc_fields`). For the homogeneous test, verify that the single RPC carried both ids `[1, 2]` in the request body. For the heterogeneous test, verify that the two RPCs each carried the expected single id.

---

## Info

### IN-01: Duplicate helper code across test files

**File:** `packages/godoo-client/tests/test_rel_resolution.py:22-38`
**Also:** `packages/godoo-client/tests/test_typed_dispatch.py:24-40`

**Issue:** `_jsonrpc_result`, `_make_config`, and the `auth_client` fixture are copy-pasted verbatim between `test_rel_resolution.py` and `test_typed_dispatch.py`. The plan explicitly instructed "copy verbatim from test_typed_dispatch.py" — this is the intentional approach for Plan 02. However, if the auth shape or config defaults change, two files need updating.

**Fix:** Extract to a shared `conftest.py` in the `tests/` directory. This is low-priority but worth tracking.

---

### IN-02: `Ref[T]` docstring does not mention `_target_cls` semantics

**File:** `packages/godoo-client/src/godoo/client/typed.py:23-34`

**Issue:** The class docstring explains `name` semantics but says nothing about `_target_cls`. The field docstring (`"""Runtime target class; excluded from equality, hash, and repr."""`) is concise but does not say how the value is populated (wire transform), what `None` means at the caller site (unresolved / bare annotation), or that it is populated only by `_pydantic_transform.py`. Library users who construct a `Ref` manually for testing may not realise they need to pass `_target_cls` for the resolution dispatch to work.

**Fix:** Extend the class or field docstring:
```python
_target_cls: type | None = field(default=None, compare=False, hash=False, repr=False)
"""Runtime target class; excluded from equality, hash, and repr.

Populated automatically by the wire transform when the field annotation is
``Ref[SomeModel]``. ``None`` when constructed manually or from a bare ``Ref``
annotation. ``OdooClient.read(ref)`` requires a non-None value — pass
``_target_cls=MyModel`` when constructing Refs manually for dispatch.
"""
```

---

_Reviewed: 2026-06-02T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
