---
phase: 10-typed-relation-resolution
verified: 2026-06-02T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 10: Typed Relation Resolution — Verification Report

**Phase Goal:** A caller holding a `Ref[T]` can resolve it to the related typed model instance through `client.read`, without naming the target model, using one batched RPC per distinct target model.
**Verified:** 2026-06-02
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `Ref[T]` produced by wire transform carries Python target class at runtime so `client.read(ref)` needs no additional model arg | VERIFIED | `typed.py` line 33: `_target_cls: type | None = field(default=None, compare=False, hash=False, repr=False)`; `_pydantic_transform.py` line 163: `_target_cls=_ref_target_class(annotation)` passed at construction |
| 2 | `client.read(ref)` returns single instance (one RPC); `client.read(refs)` for mixed typed Refs issues one batched RPC per distinct target model with ids deduplicated | VERIFIED | `client.py` lines 224–251: dispatch branch groups by `_target_cls`, deduplicates with `if r.id not in groups[r._target_cls]`, fires `await self.read(target_cls, target_ids)` per group, stitches ordered; `test_rel_resolution.py` `test_read_homogeneous_list_resolves` asserts `len(respx.calls)==1`; `test_read_heterogeneous_list_preserves_order` asserts `len(respx.calls)==2` |
| 3 | Passing untyped `Ref[int]` to `client.read` raises `OdooValidationError` naming the cause | VERIFIED | `client.py` lines 227–232: `bad = [r for r in refs if r._target_cls is None]`; raises `OdooValidationError(f"Cannot resolve Ref(id={bad[0].id}): no target model known — it came from an untyped many2one field.")`; `test_rel_resolution.py` `test_read_untyped_ref_raises_before_rpc` passes with `match="no target model known"` and asserts `len(respx.calls)==0` |
| 4 | Existing `Ref(id, name)` construction and equality semantics unchanged — `_target_cls` is `compare=False, hash=False, repr=False` | VERIFIED | `typed.py` line 33 uses exactly `field(default=None, compare=False, hash=False, repr=False)`; Plan 01 truths include equality and hash unchanged |
| 5 | Wire transform tests exercise `Ref`/date/datetime fields through full `client.read` dispatch chain (TEST-02) | VERIFIED | `test_typed_dispatch.py` lines 264–275: `test_read_typed_ref_field_populated` calls `auth_client.read(TinyPartner, [1])` with `parent_id: [3, "Acme"]` on the wire and asserts `result[0].parent_id._target_cls is TinyPartner` |
| 6 | Resolution is single-level only — arbitrary-depth nesting explicitly out of scope (REL-05) | VERIFIED | `client.py` dispatch branch calls `await self.read(target_cls, target_ids)` (the typed path, not another Ref-dispatch recursion); no recursive Ref unwrapping; REL-ADV-01 explicitly deferred in REQUIREMENTS.md |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/godoo-client/src/godoo/client/typed.py` | `_target_cls` field on `Ref[T]` frozen dataclass | VERIFIED | Line 33: `_target_cls: type \| None = field(default=None, compare=False, hash=False, repr=False)` |
| `packages/godoo-client/src/godoo/client/_pydantic_transform.py` | `_ref_target_class()` helper + updated m2o branch | VERIFIED | Lines 52–71: `_ref_target_class` implemented; line 163: `_target_cls=_ref_target_class(annotation)` in m2o branch |
| `packages/godoo-client/src/godoo/client/client.py` | Ref / list[Ref] overloads + dispatch branch in `read()` | VERIFIED | Lines 192–196: two new `@overload` signatures; lines 224–251: Ref dispatch branch with fail-fast guard, grouping, dedup, batching, stitch |
| `packages/godoo-client/tests/test_typed_dispatch.py` | TEST-02 wire-fidelity test | VERIFIED | Lines 264–275: `test_read_typed_ref_field_populated` present and passing |
| `packages/godoo-client/tests/test_rel_resolution.py` | Four resolution behavior tests (REL-02..REL-05) | VERIFIED | All four test functions present and passing: `test_read_single_ref_resolves`, `test_read_homogeneous_list_resolves`, `test_read_heterogeneous_list_preserves_order`, `test_read_untyped_ref_raises_before_rpc` |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `_pydantic_transform.py _odoo_wire_transforms` | `Ref` constructor | `_target_cls=_ref_target_class(annotation)` kwarg at line 163 | WIRED |
| `_ref_target_class` | `get_args / get_origin` | `get_origin(annotation)` at lines 59–66 | WIRED |
| `client.py read() Ref dispatch branch` | `self.read(target_cls, target_ids)` | `await self.read(target_cls, target_ids)` at line 244 | WIRED |
| `test_rel_resolution.py heterogeneous test` | `respx.calls` count | `side_effect=lambda req, route: next(responses)` iterator at line 120 | WIRED |

### Behavioral Spot-Checks

All 17 unit tests in `test_rel_resolution.py` (4) and `test_typed_dispatch.py` (13) passed:

```
packages/godoo-client/tests/test_rel_resolution.py ....  [4 passed]
packages/godoo-client/tests/test_typed_dispatch.py ..... [13 passed]
17 passed in 0.80s
```

mypy `packages/godoo-client/src` exits 0 (no errors; note on unused testcontainers section is pre-existing).

### Requirements Coverage

| Requirement | Plan | Description | Status | Evidence |
|-------------|------|-------------|--------|----------|
| REL-01 | 10-01 | `Ref[T]` carries target model class at runtime | SATISFIED | `_target_cls` field + wire transform population |
| REL-02 | 10-02 | `client.read(ref)` returns single typed instance | SATISFIED | `client.py` Ref branch + `test_read_single_ref_resolves` |
| REL-03 | 10-02 | `client.read(refs)` batches per distinct model, deduplicates ids | SATISFIED | Grouping + dedup logic in `client.py` + `test_read_homogeneous_list_resolves` / `test_read_heterogeneous_list_preserves_order` |
| REL-04 | 10-02 | Untyped `Ref[int]` raises clear typed error | SATISFIED | Fail-fast guard in `client.py` + `test_read_untyped_ref_raises_before_rpc` |
| REL-05 | 10-02 | Resolution is single-level only | SATISFIED | No recursive Ref unwrapping in dispatch; REL-ADV-01 deferred |
| TEST-02 | 10-01 | Wire transforms exercised through full `client.read` dispatch chain | SATISFIED | `test_read_typed_ref_field_populated` in `test_typed_dispatch.py` |

### Anti-Patterns Found

None. No TBD/FIXME/XXX markers in modified files. No stubs or hardcoded-empty returns in the Ref dispatch path.

### Observations (out-of-requirement edge cases — not gaps)

A code review flagged two correctness edge cases in `client.py` that are **outside phase 10 requirements**:

1. **Raw `KeyError` at stitch step** (line 248): `fetched[(r._target_cls, r.id)]` will raise `KeyError` if the Odoo `read()` call returns fewer records than requested (e.g. record deleted between the id listing and the read). None of REL-01..REL-05 require graceful handling of this scenario; the untyped-ref guard (REL-04) only covers `_target_cls is None`. This is a production-hardening concern, not a phase requirement failure.

2. **Mixed-list Ref detection** (line 224): `isinstance(model[0], Ref)` only checks the first element of a list. A `list[Any]` with a non-Ref first element and Ref remainder would fall through to the str/typed branch and produce a confusing error. All in-scope test cases use homogeneous Ref lists; the phase requirement (REL-03) does not specify behavior for such malformed inputs. Not a phase gap.

Both items are candidates for Phase 12 tech-debt close-out if the maintainer wishes to address them.

### Human Verification Required

None. All phase-10 behaviors are fully automatable and verified by the unit test suite.

### Gaps Summary

No gaps. All 6 success criteria verified. All 6 requirement IDs (REL-01 through REL-05, TEST-02) satisfied by code evidence and passing tests.

---

_Verified: 2026-06-02T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
