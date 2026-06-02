---
phase: 10-typed-relation-resolution
plan: "02"
subsystem: godoo-client/client
tags:
  - typed-models
  - ref
  - dispatch
  - batching
  - tdd
  - rel-02
  - rel-03
  - rel-04
  - rel-05
dependency_graph:
  requires:
    - Phase 10 Plan 01 (Ref._target_cls field + _ref_target_class() helper)
    - Phase 9 (OdooValidationError with structured fields)
  provides:
    - OdooClient.read(ref: Ref[T]) -> T overload + dispatch
    - OdooClient.read(refs: list[Ref[T]]) -> list[T] overload + dispatch
    - Fail-fast guard: untyped Ref raises OdooValidationError before any RPC (REL-04)
    - Batched resolution: one recursive read() per distinct target model, ids deduplicated (REL-03)
    - Order-preserved stitch of heterogeneous-model results (D-02)
    - test_rel_resolution.py with four behavior tests (REL-02..REL-05)
  affects:
    - Phase 10 (completes the typed Ref resolution story — REL-01..REL-05 all closed)
    - Phase 11 (typed write paths consume the same dispatch infrastructure)
tech_stack:
  added: []
  patterns:
    - collections.defaultdict for group-by-target-class in-body (lazy import, not module-level)
    - Overload + Any implementation signature pattern for heterogeneous dispatch
    - type: ignore[misc] on overloaded read() to suppress mypy overload-mismatch warning
    - respx side_effect iterator pattern for sequential mock responses in heterogeneous tests
key_files:
  created:
    - packages/godoo-client/tests/test_rel_resolution.py
  modified:
    - packages/godoo-client/src/godoo/client/client.py
decisions:
  - OdooClient.read() implementation signature uses model: Any + ids: int | list[int] | None = None to accommodate Ref / list[Ref] / type[T] / str overloads; type: ignore[misc] suppresses mypy overload-mismatch warning
  - cast("list[T]", ...) removed from read() typed branch since implementation return is Any — avoids unbound T error
  - noqa: TC002 not needed in test_rel_resolution.py (Ref used directly, no Pydantic model field annotation in that file)
metrics:
  duration: "~5 minutes"
  completed_date: "2026-06-02"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
  tests_added: 4
  tests_total_after: 227
---

# Phase 10 Plan 02: Ref Dispatch in OdooClient.read() Summary

**One-liner:** Added `@overload read(Ref[T]) -> T` and `@overload read(list[Ref[T]]) -> list[T]` to `OdooClient` with a dispatch branch that fail-fasts on untyped refs, groups typed refs by target class, deduplicates ids, fires one batched `self.read(target_cls, ids)` per distinct model, and stitches results back in input order (REL-02..REL-05).

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Ref overloads + dispatch branch in OdooClient.read() | d0d95a4 | client.py |
| 2 | test_rel_resolution.py — four behavior tests | a1d7cc4 | test_rel_resolution.py |

## What Was Built

### `client.py` — Ref overloads and dispatch branch

Two new `@overload` signatures added BEFORE the existing `type[T]` and `str` overloads:
```python
@overload
async def read(self, ref: Ref[T]) -> T: ...

@overload
async def read(self, refs: list[Ref[T]]) -> list[T]: ...
```

The `read()` implementation signature changed from `model: str | type[T]` to `model: Any, ids: ... | None = None` to accommodate all four overload shapes. The body gained a new dispatch branch at the top (before the existing `hasattr(__odoo_model__)` branch):

```python
if isinstance(model, Ref) or (isinstance(model, list) and model and isinstance(model[0], Ref)):
    refs = [model] if isinstance(model, Ref) else list(model)
    # fail-fast guard (REL-04)
    bad = [r for r in refs if r._target_cls is None]
    if bad:
        raise OdooValidationError(
            f"Cannot resolve Ref(id={bad[0].id}): no target model known ..."
        )
    # group by target class, dedupe ids (REL-03)
    from collections import defaultdict
    groups: dict[type[Any], list[int]] = defaultdict(list)
    for r in refs:
        if r.id not in groups[r._target_cls]:
            groups[r._target_cls].append(r.id)
    # one batched read() per distinct target model
    fetched: dict[tuple[type[Any], int], Any] = {}
    for target_cls, target_ids in groups.items():
        results = await self.read(target_cls, target_ids)
        for record in results:
            fetched[(target_cls, record.id)] = record
    # stitch in input order (D-02)
    ordered = [fetched[(r._target_cls, r.id)] for r in refs]
    return ordered[0] if isinstance(model, Ref) else ordered
```

REL-05 (single-level only) is enforced implicitly: the dispatch branch calls `self.read(target_cls, ids)` which routes to the `hasattr(__odoo_model__)` branch on the recursive call — that branch does not further recurse into Ref dispatch.

### `test_rel_resolution.py` — four behavior tests

| Test | Behavior Covered | Requirements |
|------|-----------------|--------------|
| `test_read_single_ref_resolves` | `read(Ref[T])` returns typed instance, one RPC | REL-02 |
| `test_read_homogeneous_list_resolves` | `read(list[Ref[T]])` batches to one RPC, two ids | REL-03 |
| `test_read_heterogeneous_list_preserves_order` | Mixed-model list fires two RPCs, input order preserved | REL-02, REL-03, D-02 |
| `test_read_untyped_ref_raises_before_rpc` | `_target_cls=None` → `OdooValidationError` before any RPC | REL-04 |

## Verification

```
ruff check packages/  → All checks passed
ruff format --check packages/ → 88 files already formatted
mypy packages/godoo-client/src ... → Success: no issues found in 57 source files
pytest packages/godoo-client/tests/ -m "not integration" → 227 passed
```

Note: `spikes/08-pyodide/transport_pyfetch.py` has a pre-existing I001 ruff error (not introduced by this plan, out of scope per scope-discipline rule).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] mypy errors on read() implementation signature**
- **Found during:** Task 1 after implementation — mypy reported `[misc]` (overload mismatch), `[unused-ignore]`, and `[valid-type]` (unbound T)
- **Issue:** Original plan said to use `model: Any` and `# type: ignore[return-value]` on return statements, but with `Any` return type those ignores were unnecessary. The `cast("list[T]", ...)` in the typed branch also used an unbound `T`.
- **Fix:** Changed `# type: ignore[override]` to `# type: ignore[misc]`; removed unused `type: ignore[return-value]` on return statements; removed `cast("list[T]", ...)` (return type is `Any` so no cast needed).
- **Files modified:** `packages/godoo-client/src/godoo/client/client.py`
- **Commit:** d0d95a4

**2. [Rule 1 - Bug] RUF100 unused noqa directive in test_rel_resolution.py**
- **Found during:** Task 2 ruff check — `# noqa: TC002` on the `Ref` import was copied from `test_typed_dispatch.py` but is unnecessary here (no Pydantic model field annotation uses `Ref[T]` in this file)
- **Fix:** Removed the `# noqa: TC002` comment; applied `ruff format` to fix trailing whitespace
- **Files modified:** `packages/godoo-client/tests/test_rel_resolution.py`
- **Commit:** a1d7cc4

## TDD Gate Compliance

Both tasks committed with implementation commits (GREEN phase). The plan listed tasks in implementation-first order, so RED/GREEN cycles are:

1. Task 1: `feat(10-02)` commit d0d95a4 (GREEN — existing 223 tests passed before and after)
2. Task 2: `feat(10-02)` commit a1d7cc4 (GREEN — 4 new tests all pass on first run)

The tests in Task 2 passed immediately because Task 1's implementation was complete. This is the expected outcome for this plan's split-task TDD structure.

## Known Stubs

None — all dispatch logic is fully wired. `_target_cls` population from Plan 01 feeds directly into the dispatch branch.

## Threat Flags

None — no new network endpoints, auth paths, or external surfaces introduced. The dispatch branch is an in-process routing layer over the existing `self.read(type[T], ids)` path (T-10-03 accepted, T-10-04 mitigated as specified in threat model).

## Self-Check: PASSED

Files exist:
- [x] `packages/godoo-client/src/godoo/client/client.py` — contains `isinstance(model, Ref)` and `no target model known`
- [x] `packages/godoo-client/tests/test_rel_resolution.py` — contains all four test functions

Commits exist:
- [x] d0d95a4 — feat(10-02): add Ref overloads and dispatch branch to OdooClient.read()
- [x] a1d7cc4 — feat(10-02): add test_rel_resolution.py — Ref dispatch behavior tests (REL-02..REL-05)
