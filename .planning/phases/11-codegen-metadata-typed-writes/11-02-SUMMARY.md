---
phase: 11-codegen-metadata-typed-writes
plan: "02"
subsystem: godoo-client
tags: [pydantic, typed-writes, serializer, odoo-wire, overloads]
dependency_graph:
  requires:
    - phase: 11-01
      provides: "GEN-01 — odoo_readonly/odoo_x2many in json_schema_extra on generated model fields"
  provides:
    - "_serialize_for_write() — write-path serializer consuming GEN-01 metadata"
    - "client.create(instance: OdooBaseModel) typed overload — returns int"
    - "client.write(instance: OdooBaseModel) typed overload — id=None guard + returns bool"
  affects:
    - "11-03 (TEST-01 wave — typed create/write roundtrip tests)"
tech_stack:
  added: []
  patterns:
    - "Write serializer iterates model_fields_set exclusively (never model_dump)"
    - "odoo_readonly guard: unconditionally skips Field(json_schema_extra={'odoo_readonly': True})"
    - "x2many guard: raises OdooValidationError before RPC for odoo_x2many=True fields (D-01)"
    - "OdooValidationError lazy-imported inside _serialize_for_write body (D-04 invariant)"
    - "OdooBaseModel under TYPE_CHECKING only in client.py — pydantic stays off module-level import path"
    - "hasattr(__odoo_model__) duck-typed dispatch guard (same pattern as read/search_read)"
    - "# type: ignore[misc] on multi-overload create/write implementation def lines"
key_files:
  created:
    - packages/godoo-client/tests/test_serialize_for_write.py
  modified:
    - packages/godoo-client/src/godoo/client/_pydantic_transform.py
    - packages/godoo-client/src/godoo/client/client.py
key_decisions:
  - "TDD RED/GREEN for _serialize_for_write (write tests first, then implement)"
  - "dict[str, Any] annotation for extra_dict (not dict[str, object]) — avoids mypy strict assignment error with pydantic's JsonValue type"
  - "ruff format applied to pre-existing client.py long raise (OdooValidationError single-line collapse) — included in Task 2 commit"
patterns-established:
  - "Write-path dispatch follows same hasattr+lazy-import pattern as read-path"
  - "_serialize_for_write is the sole write serializer; consumed by both create() and write() typed branches"
requirements-completed:
  - WRITE-01
  - WRITE-02
  - WRITE-03
  - WRITE-04
  - WRITE-05
duration: ~30min
completed: "2026-06-03"
---

# Phase 11 Plan 02: Typed Write Path (WRITE-01..05) Summary

**`_serialize_for_write()` + typed `create(instance)`/`write(instance)` overloads: readonly exclusion, x2many guard, and reverse wire transforms wired into client.py via duck-typed dispatch**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-06-03T09:15:00Z
- **Completed:** 2026-06-03T09:21:00Z
- **Tasks:** 2 (Task 1 TDD: RED + GREEN; Task 2: overloads)
- **Files modified:** 3

## Accomplishments

- `_serialize_for_write(instance: OdooBaseModel) -> dict[str, Any]` implemented in `_pydantic_transform.py`; iterates `model_fields_set` exclusively, applies WRITE-04 readonly skip and WRITE-05 x2many raise before transforms
- `client.create(instance)` gains typed `@overload` stub + dispatch branch; returns `int`
- `client.write(instance)` gains typed `@overload` stub + `id is None` guard + dispatch branch; returns `bool`
- 16 new unit tests (TDD RED/GREEN) covering all WRITE-01..05 behaviors; all 280 non-integration tests pass

## Task Commits

1. **Task 1 RED: Failing tests for _serialize_for_write** - `1be11c8` (test)
2. **Task 1 GREEN: Implement _serialize_for_write()** - `043a1ca` (feat)
3. **Task 2: Typed create/write overloads in client.py** - `254ed20` (feat)

## Files Created/Modified

- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — `_serialize_for_write()` added after `clear_partial_model_cache()` with section separator
- `packages/godoo-client/src/godoo/client/client.py` — `OdooBaseModel` added to `TYPE_CHECKING`; `create()` and `write()` replaced with 3-overload and 2-overload blocks respectively
- `packages/godoo-client/tests/test_serialize_for_write.py` — 16 unit tests for WRITE-01..05 behaviors

## Decisions Made

- `dict[str, Any]` (not `dict[str, object]`) for `extra_dict` in `_serialize_for_write` to satisfy mypy strict with pydantic's `JsonValue` union type narrowing
- ruff-required format change to pre-existing `_validate_typed` raise was included in the Task 2 commit — it was a clean format fix, not a behavior change

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] mypy strict incompatible-types on extra_dict annotation**
- **Found during:** Task 1 GREEN (running quality gate after implementation)
- **Issue:** `extra_dict: dict[str, object] = extra if isinstance(extra, dict) else {}` triggered `Incompatible types in assignment` — mypy narrowed `fi.json_schema_extra` after `isinstance(extra, dict)` to `dict[str, JsonValue]` which is incompatible with `dict[str, object]` in strict mode
- **Fix:** Changed annotation to `dict[str, Any]` — mypy accepted the narrowing and `type: ignore[assignment]` was then unused
- **Files modified:** `_pydantic_transform.py`
- **Committed in:** 043a1ca (Task 1 GREEN)

**2. [Rule 3 - Blocking] Pre-existing ruff format violation in client.py**
- **Found during:** Task 2 quality gate
- **Issue:** `ruff format --check` reported `client.py` needed reformatting (pre-existing long raise in `_validate_typed` exceeded line limit after earlier changes)
- **Fix:** `uv run ruff format packages/godoo-client/src/godoo/client/client.py` — collapsed 3-line raise to single line
- **Files modified:** `client.py`
- **Committed in:** 254ed20 (Task 2 commit) — co-located with Task 2 changes, not a separate commit, because the format fix was required to unblock the quality gate for Task 2

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking pre-existing format)
**Impact on plan:** Both fixes required for quality gate pass; no scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## Known Stubs

None. All write-path logic is fully wired: `_serialize_for_write` reads real `json_schema_extra` metadata, `create()`/`write()` dispatch to it via `hasattr(__odoo_model__)`. No placeholder or TODO values.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes beyond what was planned. The `_serialize_for_write` function enforces both WRITE-04 (readonly exclusion) and WRITE-05 (x2many guard) as specified in the threat register.

## Next Phase Readiness

- Wave 3 (Plan 11-03) can now add integration tests (TEST-01): `generate class → read record → write back → assert`
- `_serialize_for_write` is importable from `godoo.client._pydantic_transform`
- Typed create/write callable as `await client.create(instance)` and `await client.write(instance)`

---
*Phase: 11-codegen-metadata-typed-writes*
*Completed: 2026-06-03*

## Self-Check: PASSED

- [x] `packages/godoo-client/src/godoo/client/_pydantic_transform.py` exists with `_serialize_for_write`
- [x] `packages/godoo-client/src/godoo/client/client.py` has `OdooBaseModel` under `TYPE_CHECKING` and typed overloads
- [x] `packages/godoo-client/tests/test_serialize_for_write.py` has 16 unit tests (all pass)
- [x] Commits 1be11c8, 043a1ca, 254ed20 verified in git log
- [x] All 280 non-integration tests pass
- [x] mypy --strict exits 0 on packages/godoo-client/src
- [x] ruff check + format --check exit 0
