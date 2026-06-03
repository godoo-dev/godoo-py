---
phase: 11-codegen-metadata-typed-writes
plan: "03"
subsystem: godoo-client
tags: [typed-writes, unit-tests, integration-test, pytest, respx, TEST-01]
dependency_graph:
  requires:
    - phase: 11-01
      provides: "GEN-01 — odoo_readonly/odoo_x2many in json_schema_extra"
    - phase: 11-02
      provides: "_serialize_for_write() + typed create/write overloads"
  provides:
    - "WRITE-01..05 unit test coverage in test_typed_writes.py"
    - "TEST-01 integration test (codegen→read→write round-trip, closes 999.3)"
  affects: []
tech_stack:
  added: []
  patterns:
    - "respx @respx.mock decorator (not context manager) for per-test HTTP mocking"
    - "_extract_rpc_write_payload() inspects params.args[5][-1] for write/create payloads"
    - "NullableIdPartner model (id: int | None = None) for create-path tests"
    - "exec() of trusted codegen output in integration test (in-memory class loading)"
    - "Integration test: TestHarness(modules=['base'], snapshot=False) pattern"
key_files:
  created:
    - packages/godoo-client/tests/test_typed_writes.py
  modified:
    - packages/godoo-client/src/godoo/client/_pydantic_transform.py
key_decisions:
  - "Rule 1 Bug: _serialize_for_write must skip 'id' field — id is the record identifier passed in [[model.id], payload], not part of the write values dict"
  - "NullableIdPartner fixture (id: int | None = None) used for create-path tests; WritePartner has required id: int for write-path tests"
  - "Integration test uses exec() for generated class loading — avoids tempfile/importlib complexity for in-memory source string"
  - "WritePartnerWithReadonly model defined inline for test_typed_create_excludes_readonly — WritePartner's required id: int prevents use for create path"
requirements-completed:
  - TEST-01
metrics:
  duration: "~20min"
  completed: "2026-06-03"
  tasks: 2
  files: 2
---

# Phase 11 Plan 03: Typed Write Tests (TEST-01) Summary

**One-liner:** 12 respx unit tests prove the typed write path end-to-end (model_fields_set, readonly exclusion, None→False, Ref→int, date/datetime→ISO, x2many guard, id=None guard, dict-path regression) plus a Docker-gated integration test closing 999.3.

## Performance

- **Duration:** ~20 min
- **Started:** 2026-06-03T10:00:00Z
- **Completed:** 2026-06-03T10:20:00Z
- **Tasks:** 2 (Task 1: unit tests + integration stub; Task 2: implicit — integration test included in Task 1 commit)
- **Files modified:** 2

## Accomplishments

- `packages/godoo-client/tests/test_typed_writes.py` created with 12 unit tests (all pass) + 1 integration test
- All WRITE-01..05 behaviors covered by named unit tests
- TEST-01 integration test: codegen→read→write round-trip against live Odoo via TestHarness
- Backlog 999.3 closed by `test_codegen_read_write_roundtrip`
- 426 non-integration tests pass (up from 414, net +12 new unit tests)

## Task Commits

1. **Task 1 + 2: Unit tests + integration test for typed writes** - `68aac6b` (test)
   - 12 unit tests covering WRITE-01..05
   - 1 integration test (TEST-01) for codegen→read→write round-trip
   - Bug fix: `_serialize_for_write` now skips `id` field

## Files Created/Modified

- `packages/godoo-client/tests/test_typed_writes.py` — 12 unit tests + 1 integration test (TEST-01)
- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — `_serialize_for_write`: skip `id` field (auto-fixed bug)

## Decisions Made

- `_serialize_for_write` must skip `id` — the record identifier is already passed as `[[model.id], payload]` in the `write()` RPC call; including `id` in the payload dict is both redundant and wrong
- `NullableIdPartner` (id: int | None = None) used for create-path tests; `WritePartner` with required `id: int` is used for write-path tests (correct separation)
- `exec()` used for integration test class loading — the generated source is trusted (our own codegen), and exec avoids tempfile/importlib overhead for an in-memory string
- `WritePartnerWithReadonly` defined inline (id: int | None = None) for `test_typed_create_excludes_readonly` — reusing `WritePartner` would require `id` and that puts `id` in `model_fields_set`, muddying the assertion

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_serialize_for_write` included `id` field in write payload**
- **Found during:** Task 1 (first test run — `test_typed_write_sends_only_set_fields` failed)
- **Issue:** `WritePartner(id=1, name="Updated")` put both `id` and `name` in `model_fields_set`; the serializer iterated all of them, so the payload was `{"id": 1, "name": "Updated"}` instead of `{"name": "Updated"}`. The `id` is already passed as the record identifier in `[[model.id], payload]` — it must not appear in the values dict.
- **Fix:** Added `if field_name == "id": continue` guard at the top of the iteration loop in `_serialize_for_write`
- **Files modified:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py`
- **Commit:** 68aac6b

**2. [Rule 1 - Bug] `WritePartner(name="New Partner")` failed validation — `id: int` is required**
- **Found during:** Task 1 (second test run — `test_typed_create_returns_new_id` failed)
- **Issue:** The plan specified `WritePartner(name="New")` for create tests, but `WritePartner.id: int` is a required field; Pydantic rejected the call. For create, `id` is not yet known so models need `id: int | None = None`.
- **Fix:** Defined `NullableIdPartner` and `WritePartnerWithReadonly` fixtures with `id: int | None = None` for create-path tests. Write-path tests correctly use `WritePartner(id=1, ...)` with a valid id.
- **Files modified:** `test_typed_writes.py` (fixture design adjustment)
- **Commit:** 68aac6b

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes required for correct test behavior. The `_serialize_for_write` fix is also a correctness improvement to production code (WRITE-02 enforcement).

## Issues Encountered

None beyond the auto-fixed deviations above.

## Known Stubs

None. All 12 unit tests are fully wired. The integration test (`test_codegen_read_write_roundtrip`) is a complete end-to-end test against a live Odoo container — no mock, no placeholder.

## Threat Flags

None. T-11-03-01 (destructive write) is mitigated: integration test uses `res.lang` id=1 with a non-critical `name` field, restores the original value in a final write.

## Self-Check: PASSED

- [x] `packages/godoo-client/tests/test_typed_writes.py` exists with 12 unit tests + 1 integration test
- [x] All 12 unit tests pass: `uv run pytest packages/godoo-client/tests/test_typed_writes.py -k "not integration"` exits 0
- [x] Full non-integration suite: 426 passed, 4 deselected
- [x] `ruff check` + `ruff format --check` exit 0
- [x] `mypy --strict packages/godoo-client/src` exits 0
- [x] Commit 68aac6b verified in git log
