---
phase: 10-typed-relation-resolution
plan: "01"
subsystem: godoo-client/typed
tags:
  - typed-models
  - ref
  - wire-transform
  - tdd
  - rel-01
  - test-02
dependency_graph:
  requires:
    - Phase 6 (OdooBaseModel wire transforms, _pydantic_transform.py)
    - Phase 9 (OdooValidationError with .human_message — used by Wave 2)
  provides:
    - Ref._target_cls field with compare=False, hash=False, repr=False semantics
    - _ref_target_class() helper extracting T from Ref[T] annotations
    - Wire transform populates _target_cls on every Ref instance produced from m2o tuples
    - TEST-02 wire-fidelity test through full client.read() dispatch chain
  affects:
    - Phase 10 Plan 02 (Ref dispatch: read(ref), batching, untyped guard — consumes _target_cls)
tech_stack:
  added: []
  patterns:
    - dataclass field(compare=False, hash=False, repr=False) for excluded metadata
    - get_origin / get_args for annotation reflection (mirrors _annotation_mentions_ref pattern)
    - TDD RED/GREEN cycle per task
key_files:
  created: []
  modified:
    - packages/godoo-client/src/godoo/client/typed.py
    - packages/godoo-client/src/godoo/client/_pydantic_transform.py
    - packages/godoo-client/tests/test_typed.py
    - packages/godoo-client/tests/test_pydantic_transform.py
    - packages/godoo-client/tests/test_typed_dispatch.py
decisions:
  - ODD-1 resolved: _target_cls: type | None = field(default=None, compare=False, hash=False, repr=False) on Ref[T] (Option A)
  - Sibling helper _ref_target_class() preferred over mutating _annotation_mentions_ref() return type — keeps existing callers stable
  - TC002 noqa on Ref import in test_typed_dispatch.py — Ref is needed at runtime for Pydantic field annotation resolution, cannot be TYPE_CHECKING-gated
metrics:
  duration: "~20 minutes"
  completed_date: "2026-06-02"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
  tests_added: 17
  tests_total_after: 223
---

# Phase 10 Plan 01: Ref._target_cls Field + _ref_target_class() Helper Summary

**One-liner:** Added `_target_cls: type | None` to `Ref[T]` frozen dataclass with compare/hash/repr=False semantics, implemented `_ref_target_class()` annotation-reflection helper, and wired both into the m2o wire transform so every `Ref` produced from `[id, "Name"]` tuples carries its target class at runtime (REL-01).

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 (RED) | Failing tests for Ref._target_cls + _ref_target_class() | a5f8af6 | test_typed.py, test_pydantic_transform.py |
| 1 (GREEN) | Add _target_cls to Ref[T]; implement _ref_target_class() | 8015285 | typed.py, _pydantic_transform.py, test_pydantic_transform.py |
| 2 (RED) | TEST-02 wire-fidelity test (TinyPartner missing parent_id) | bbb4cfd | test_typed_dispatch.py |
| 2 (GREEN) | Add parent_id to TinyPartner; test passes | 5cb22f1 | test_typed_dispatch.py |

## What Was Built

### `typed.py` — `_target_cls` field on `Ref[T]`

`Ref[T]` gained a third field:
```python
_target_cls: type | None = field(default=None, compare=False, hash=False, repr=False)
```

Key properties:
- `compare=False` — `Ref(id=1, name="X") == Ref(id=1, name="X", _target_cls=SomeClass)` is `True`
- `hash=False` — hash is unchanged regardless of `_target_cls`
- `repr=False` — `repr(Ref(id=1, name="X", _target_cls=X))` stays `Ref(id=1, name='X')`
- `default=None` — backward-compatible construction: `Ref(id=1, name="X")` still works

### `_pydantic_transform.py` — `_ref_target_class()` helper + m2o update

New module-private helper:
```python
def _ref_target_class(annotation: Any) -> type | None
```

Mirrors `_annotation_mentions_ref()` structure but extracts the type argument:
- `Ref[SomeModel]` → returns `SomeModel`
- `Ref[SomeModel] | None` → returns `SomeModel` (union unwrapping)
- Bare `Ref` → returns `None`
- Non-Ref annotation → returns `None`

m2o wire transform branch updated to pass `_target_cls=_ref_target_class(annotation)` as keyword arg to `Ref(...)` constructor. Additive-only change; existing guard stays intact.

### `test_typed_dispatch.py` — TEST-02 wire-fidelity test

`TinyPartner` extended with `parent_id: Ref[TinyPartner] | None = None`.

New test `test_read_typed_ref_field_populated`:
- Mocks Odoo response `[{"id": 1, "parent_id": [3, "Acme"]}]`
- Calls `await auth_client.read(TinyPartner, [1])`
- Asserts `result[0].parent_id._target_cls is TinyPartner`

This exercises the full dispatch chain: `OdooClient.read()` → `_odoo_wire_transforms` → `Ref` constructor with `_target_cls`.

## Verification

```
ruff check packages/  → All checks passed
ruff format --check packages/ → 87 files already formatted
mypy packages/godoo-client/src ... → Success: no issues found in 57 source files
pytest packages/godoo-client/tests/ -m "not integration" → 223 passed
```

Note: `spikes/08-pyodide/transport_pyfetch.py` has a pre-existing I001 ruff error (not introduced by this plan, out of scope per scope-discipline rule).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff TC002 on `Ref` import in `test_typed_dispatch.py`**
- **Found during:** Task 2 GREEN phase
- **Issue:** Ruff TC002 flagged `from godoo.client.typed import Ref` as a "move to TYPE_CHECKING block" candidate, but `Ref` is needed at runtime for Pydantic model field annotation resolution on `TinyPartner.parent_id`.
- **Fix:** Added `# noqa: TC002` comment explaining the runtime requirement.
- **Files modified:** `packages/godoo-client/tests/test_typed_dispatch.py`
- **Commit:** 5cb22f1

**2. [Rule 1 - Bug] Ruff I001/E501/UP037 on `test_pydantic_transform.py` import**
- **Found during:** Task 1 GREEN phase ruff check
- **Issue:** Added `_ref_target_class` to a single-line import that exceeded 120 chars (E501); ruff also flagged I001 (import ordering) and UP037 (quoted type annotation `Ref["_TypedPartner"]`).
- **Fix:** Expanded import to multi-line block form; changed `Ref["_TypedPartner"]` to `Ref[_TypedPartner]` (works with `from __future__ import annotations`).
- **Files modified:** `packages/godoo-client/tests/test_pydantic_transform.py`
- **Commit:** 8015285

## TDD Gate Compliance

Both tasks followed RED/GREEN TDD cycle:

1. Task 1: `test(10-01)` commit a5f8af6 (RED) → `feat(10-01)` commit 8015285 (GREEN)
2. Task 2: `test(10-01)` commit bbb4cfd (RED) → `feat(10-01)` commit 5cb22f1 (GREEN)

No REFACTOR phase needed — code was clean after GREEN.

## Known Stubs

None — all fields are wired correctly. `_target_cls` is populated by the wire transform; no placeholder values.

## Threat Flags

None — the `_ref_target_class()` helper performs annotation reflection on static type objects (not user-supplied data). T-10-01 and T-10-02 from the threat model are accepted as noted in the plan.

## Self-Check: PASSED

Files exist:
- [x] `packages/godoo-client/src/godoo/client/typed.py` — contains `_target_cls`
- [x] `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — contains `_ref_target_class`
- [x] `packages/godoo-client/tests/test_typed_dispatch.py` — contains `test_read_typed_ref_field_populated`
- [x] `packages/godoo-client/tests/test_typed.py` — contains `_target_cls` tests
- [x] `packages/godoo-client/tests/test_pydantic_transform.py` — contains `_ref_target_class` tests

Commits exist:
- [x] a5f8af6 — test(10-01): RED phase Task 1
- [x] 8015285 — feat(10-01): GREEN phase Task 1
- [x] bbb4cfd — test(10-01): RED phase Task 2
- [x] 5cb22f1 — feat(10-01): GREEN phase Task 2
