---
phase: 12-tech-debt-close-out
plan: "03"
subsystem: godoo-testcontainers
tags: [breaking-change, api-ergonomics, snapshot, testcontainers, debt]
dependency_graph:
  requires: []
  provides: [OdooTestContainer-required-properties]
  affects: [packages/godoo-testcontainers]
tech_stack:
  added: []
  patterns: [required-keyword-arg-no-default, parity-unit-test]
key_files:
  created:
    - packages/godoo-testcontainers/tests/test_snapshot_key_parity.py
  modified:
    - packages/godoo-testcontainers/src/godoo/testcontainers/container.py
    - packages/godoo-testcontainers/tests/test_container.py
    - tests/conftest.py
    - docs/testing.md
    - packages/godoo-testcontainers/README.md
decisions:
  - "DEBT-04: make properties required (no default) — TypeError at construction time is explicit and actionable vs silent empty-properties key mismatch"
  - "harness.py unchanged — already passes properties=self._properties"
  - "parity test is pure unit test (no Docker, no instantiation) — proves compute_snapshot_key determinism structurally"
metrics:
  duration: "5m"
  completed: "2026-06-03"
  tasks: 2
  files: 6
---

# Phase 12 Plan 03: Snapshot key footgun fix (OdooTestContainer required properties) Summary

**One-liner:** Made `properties` a required keyword arg on `OdooTestContainer.__init__`, eliminating the silent empty-properties snapshot key mismatch (DEBT-04/SC-4 breaking change at 0.2.x).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Make `properties` a required keyword arg (BREAKING CHANGE) | 4b41283 | container.py |
| 2 | Update all callers, add parity tests, update docs | 3c55608 | test_container.py, test_snapshot_key_parity.py, conftest.py, docs/testing.md, README.md |

## What Was Built

### Task 1: Breaking API change to OdooTestContainer

`packages/godoo-testcontainers/src/godoo/testcontainers/container.py`:
- Changed `properties: dict[str, str] | None = None` → `properties: dict[str, str]` (required, no default)
- Removed `properties if properties is not None else {}` None guard — simplified to `self._properties_for_key = properties`
- Updated docstring to document the required-kwarg constraint and DEBT-04 rationale

`harness.py` was already compliant (passes `properties=self._properties`) — no change needed.
`snapshot.py` `compute_snapshot_key` already accepted `properties: dict[str, str]` without None — no change needed.

### Task 2: Callers, parity tests, docs

**test_container.py**: All 13 `OdooTestContainer()` calls updated with `properties={}` across `TestOdooTestContainerDefaults` and `TestOdooTestContainerNewParams`.

**tests/conftest.py**: Session fixture updated — `OdooTestContainer(modules=[...], properties={})`.

**test_snapshot_key_parity.py** (new, 2 tests):
- `test_direct_container_key_matches_testharness_key`: calls `compute_snapshot_key` twice with identical kwargs (non-empty properties dict) and asserts both keys equal — proves determinism.
- `test_empty_properties_key_differs_from_non_empty`: asserts `compute_snapshot_key(properties={})` != `compute_snapshot_key(properties={"web.base.url": ...})` — proves D-08 correctness guarantee.

**docs/testing.md**: Updated code example + added `properties` row to options table (required, description of ir.config_parameter usage).

**packages/godoo-testcontainers/README.md**: Updated Quick Start example with `properties={}`.

## Verification Results

```
uv run pytest packages/godoo-testcontainers/tests/ -v -m "not integration"
→ 90 passed, 3 deselected

uv run pytest packages/ -m "not integration"
→ 440 passed, 4 deselected

uv run mypy packages/godoo-testcontainers/src
→ Success: no issues found in 6 source files

uv run ruff check packages/ && uv run ruff format --check packages/
→ All checks passed! / 91 files already formatted

python -c "OdooTestContainer()"
→ TypeError: missing 1 required keyword-only argument: 'properties'  ✓

python -c "OdooTestContainer(properties={})"; print('ok')
→ ok  ✓
```

Note: pre-existing `ruff I001` in `spikes/08-pyodide/transport_pyfetch.py` (Phase 8 artifact) — out of scope, not fixed per plan instructions.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — this plan introduces no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries.

## Self-Check: PASSED

- [x] `packages/godoo-testcontainers/src/godoo/testcontainers/container.py` exists and has `properties: dict[str, str],` (required)
- [x] `packages/godoo-testcontainers/tests/test_snapshot_key_parity.py` exists with 2 passing tests
- [x] Commits 4b41283 and 3c55608 exist
- [x] 440 unit tests pass
