---
phase: 01-client-parity
plan: "02"
subsystem: godoo-core
tags: [bug-fix, packaging, pep561, cdc, typing]
dependency_graph:
  requires: []
  provides: [CdcService.get_feed-plain-def, py.typed-marker]
  affects: [godoo.services.cdc.service, godoo.py.typed]
tech_stack:
  added: []
  patterns: [tdd-red-green, pep561]
key_files:
  created:
    - packages/godoo/src/godoo/py.typed
  modified:
    - packages/godoo/src/godoo/services/cdc/service.py
    - packages/godoo/tests/test_cdc.py
    - uv.lock
decisions:
  - "No changes to pyproject.toml needed: hatchling packages=[src/godoo] auto-includes py.typed"
  - "TDD applied to Task 1: RED commit (022eebc) -> GREEN commit (ed9a9ba)"
metrics:
  duration: "~7 minutes"
  completed: "2026-05-19T10:47:15Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 3
requirements:
  - FIXES-01
  - CLIENT-10
---

# Phase 01 Plan 02: CdcService get_feed Fix and py.typed Marker Summary

Two mechanical fixes: removed the erroneous `async` keyword from `CdcService.get_feed` so callers receive the async generator directly, and added the empty `py.typed` PEP 561 marker so downstream type checkers use godoo's inline annotations.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing test for CdcService.get_feed plain-def requirement | 022eebc | packages/godoo/tests/test_cdc.py |
| 1 (GREEN) | Fix CdcService.get_feed class-API bug (FIXES-01) | ed9a9ba | packages/godoo/src/godoo/services/cdc/service.py |
| 2 | Create py.typed PEP 561 marker (CLIENT-10) | 0b03c66 | packages/godoo/src/godoo/py.typed |

## What Was Built

### Task 1: Fix CdcService.get_feed (FIXES-01)

**Bug:** `CdcService.get_feed` was declared `async def`, which wraps the return value in a coroutine. Since `functions.get_feed` is an async generator (not a coroutine), calling `client.cdc.get_feed(opts)` returned a coroutine object rather than an `AsyncIterator`. Callers attempting `async for event in client.cdc.get_feed(opts)` without `await` would get a `TypeError`.

**Fix:** Removed the `async` keyword from the method signature in `service.py` (line 38). The body `return get_feed(self._client, options)` was already correct — it returns the async generator directly. This single-word change restores the intended behavior.

**TDD applied:** RED commit with failing `test_get_feed_is_not_coroutine_function`, then GREEN commit with the fix.

### Task 2: Create py.typed PEP 561 Marker (CLIENT-10)

Created an empty `packages/godoo/src/godoo/py.typed` file. Per PEP 561, its presence signals that the `godoo` package ships inline type annotations and downstream type checkers (mypy, pyright, pylance) should use them directly. No `pyproject.toml` changes were needed — hatchling's `packages = ["src/godoo"]` configuration already includes all files under `src/godoo/`.

## Verification Results

All verification commands passed after both tasks:

- `inspect.iscoroutinefunction(CdcService.get_feed)` → `False` (PASS)
- `pathlib.Path('packages/godoo/src/godoo/py.typed').exists()` → `True` (PASS)
- `uv run pytest packages/ -m "not integration" -q` → 158 passed, 0 failed
- `uv run mypy packages/godoo/src packages/godoo-testcontainers/src` → Success: no issues found in 45 source files
- `uv run ruff check .` → All checks passed!

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Synced uv.lock with package versions**

- **Found during:** Initial uv environment setup (before Task 1)
- **Issue:** `uv.lock` referenced package versions `0.1.0` but all three `pyproject.toml` files had version `0.1.1`. Running `uv` auto-updated the lockfile.
- **Fix:** Committed the updated `uv.lock` to keep CI (which uses lockfile-strict mode) in sync.
- **Files modified:** `uv.lock`
- **Commit:** f2b7f02

## Known Stubs

None — both tasks make mechanical, complete changes with no placeholder values or stubbed data paths.

## Threat Surface Scan

No new security-relevant surfaces introduced. The `async` removal in `service.py` changes method dispatch but not auth paths, network calls, or trust boundaries. The `py.typed` marker is a zero-byte packaging convention file.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| packages/godoo/src/godoo/services/cdc/service.py | FOUND |
| packages/godoo/src/godoo/py.typed | FOUND |
| .planning/phases/01-client-parity/01-02-SUMMARY.md | FOUND |
| commit 022eebc (test RED) | FOUND |
| commit ed9a9ba (fix GREEN) | FOUND |
| commit 0b03c66 (py.typed) | FOUND |
