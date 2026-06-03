---
phase: 12-tech-debt-close-out
plan: "02"
subsystem: godoo-introspection
tags: [debt, testing, coroutine, cli]
dependency_graph:
  requires: []
  provides: [DEBT-03]
  affects: [packages/godoo-introspection/src/godoo/introspection/cli.py, packages/godoo-introspection/tests/test_cli.py]
tech_stack:
  added: []
  patterns: [finally-coro-close, patch-async-function-not-asyncio-run]
key_files:
  created: []
  modified:
    - packages/godoo-introspection/src/godoo/introspection/cli.py
    - packages/godoo-introspection/tests/test_cli.py
decisions:
  - "Use finally: _coro.close() form (not inspect.iscoroutine guard) — simpler, no new import, always safe per RESEARCH Pitfall-2"
  - "Patch cli_module._generate_async with async def (not asyncio.run) so asyncio.run receives an awaitable that raises — zero unawaited coroutines"
  - "Remove top-level asyncio import from test_cli.py (ruff F401 — no longer used after removing monkeypatch.setattr(asyncio, 'run', ...))"
metrics:
  duration: "5m"
  completed: "2026-06-03"
  tasks: 2
  files: 2
---

# Phase 12 Plan 02: DEBT-03 RuntimeWarning Fix Summary

**One-liner:** Eliminated unawaited-coroutine RuntimeWarning from three test_cli.py error-path tests by patching `_generate_async` directly (test side) and adding `finally: _coro.close()` (production side).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Harden cli.py — extract coroutine, add finally: _coro.close() | 3e9503f | cli.py |
| 2 | Fix three test_cli.py error-path tests — patch _generate_async | 71f6558 | test_cli.py |

## What Was Built

**Task 1 — Production side (cli.py):**

Extracted the coroutine into `_coro` before the try block and added `finally: _coro.close()`. This ensures the coroutine is always closed regardless of whether `asyncio.run` succeeds, raises a handled exception, or raises an unexpected BaseException (e.g., KeyboardInterrupt during test monkeypatching). The `close()` call is a no-op if `asyncio.run` completed normally (Pitfall-2 safe per RESEARCH.md).

**Task 2 — Test side (test_cli.py):**

Replaced `monkeypatch.setattr(asyncio, "run", _raise)` with `monkeypatch.setattr(cli_module, "_generate_async", _raise_async)` in all three error-path tests:
- `test_generate_auth_error_exits_1`
- `test_generate_network_error_exits_1`
- `test_generate_odoo_error_password_not_in_output`

Each replacement uses an `async def _raise_async` that raises the exception when awaited. With this approach, `asyncio.run` receives a real coroutine and runs it — the coroutine raises immediately, the exception propagates through the `except (ValueError, OdooError)` block in `cli.py`, exit_code == 1 and the error message appear in output as before. No unawaited coroutine object is created.

Removed the now-unused top-level `import asyncio` (ruff F401).

## Verification

```
uv run pytest packages/godoo-introspection/tests/test_cli.py -v -W error::RuntimeWarning
→ 8 passed (zero RuntimeWarning promotions)

uv run pytest packages/ -m "not integration"
→ 438 passed, full unit suite green

uv run ruff check packages/ && uv run ruff format --check packages/
→ All checks passed

uv run mypy packages/godoo-client/src packages/godoo-testcontainers/src packages/godoo-introspection/src
→ Success: no issues found in 57 source files
```

## Acceptance Criteria Check

- [x] `uv run pytest packages/godoo-introspection/tests/test_cli.py -v -W error::RuntimeWarning` exits 0
- [x] cli.py contains `_coro = _generate_async(...)` before the try block and `finally: _coro.close()` after
- [x] test_cli.py contains no `monkeypatch.setattr(asyncio, "run", ...)` calls
- [x] test_cli.py contains `monkeypatch.setattr(cli_module, "_generate_async", ...)` in each of the three tests
- [x] mypy --strict passes on godoo-introspection/src with no new errors

## Deviations from Plan

### Out-of-scope findings

**Pre-existing ruff I001 in spikes/08-pyodide/transport_pyfetch.py** (commit `08d4ba3`, Phase 8) — unsorted import block in a spike artifact outside `packages/`. Not caused by this plan's changes. Per scope discipline, deferred rather than fixed inline.

## Known Stubs

None.

## Threat Flags

None — coroutine lifecycle fix; no new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- [x] `packages/godoo-introspection/src/godoo/introspection/cli.py` exists and contains `_coro.close()`
- [x] `packages/godoo-introspection/tests/test_cli.py` exists and contains `_generate_async`
- [x] Commit `3e9503f` exists (Task 1)
- [x] Commit `71f6558` exists (Task 2)
