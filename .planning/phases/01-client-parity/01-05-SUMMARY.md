---
phase: 01-client-parity
plan: "05"
subsystem: godoo-client
tags: [gap-closure, correctness, typing, exception-safety, docstrings]
dependency_graph:
  requires: [01-04]
  provides: [hardened-read-binary, typed-safety-sentinel, exception-safe-aexit, accurate-with-context-docs]
  affects: [packages/godoo/src/godoo/client.py, packages/godoo/tests/test_client.py]
tech_stack:
  added: []
  patterns: [typed-sentinel, exception-preservation, tdd-red-green]
key_files:
  created: []
  modified:
    - packages/godoo/src/godoo/client.py
    - packages/godoo/tests/test_client.py
decisions:
  - "Used assert + isinstance for _UndefinedType narrowing because mypy does not narrow on identity checks with a singleton instance (is _UNDEFINED); assert is zero-cost in production and expresses intent clearly"
  - "WR-04 test uses unittest.mock patch.object to mock authenticate and aclose; direct __aenter__ instance patching does not work in Python (dunder lookup bypasses instance __dict__)"
metrics:
  duration: "6m"
  completed: "2026-05-19T12:35:00Z"
  tasks_completed: 4
  files_changed: 2
---

# Phase 01 Plan 05: Gap-Closure CR-02 / WR-03 / WR-04 / WR-05 Summary

**One-liner:** Hardened `read_binary` with typed `OdooValidationError` on malformed base64, typed `_UndefinedType` sentinel eliminating `Any` on `_safety_context`, exception-safe `__aexit__` preserving body errors, and accurate `with_context` / `_OdooContextScope` docstrings.

## What Was Built

Four targeted correctness/typing fixes closing code-review findings on the Phase 1 client surface:

1. **CR-02** — `read_binary` now wraps `base64.b64decode` in `try/except (ValueError, TypeError)` and raises `OdooValidationError` with model/record/field context. Callers can uniformly catch `OdooError`.
2. **WR-03** — `_safety_context` attribute changed from `Any` to `SafetyContext | _UndefinedType | None`. New `_UndefinedType` class + `Final` typed singleton replace the bare `object()` sentinel. `mypy --strict` now fully checks the attribute.
3. **WR-04** — `__aexit__` wraps `aclose()` in `try/except`; if the block body raised, the close failure is logged as a warning (not re-raised), preserving the original body exception. On a clean exit, close failures propagate normally.
4. **WR-05** — `_OdooContextScope` class docstring and `with_context` method docstring now accurately document that `asyncio.create_task()` inside the block inherits a copy of the ambient context that persists independently after the block exits (standard `ContextVar` semantics).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Guard read_binary base64 decode (CR-02) | 26eeea6 | client.py, test_client.py |
| 2 | Replace _safety_context Any with typed sentinel (WR-03) | 00fbf55 | client.py |
| 3 | Make __aexit__ preserve the body exception (WR-04) | e098a72 | client.py, test_client.py |
| 4 | Correct with_context / _OdooContextScope docstrings (WR-05) | 4bc0750 | client.py |
| - | Apply ruff format | 4db73fb | client.py, test_client.py |

## Verification Results

- `uv run pytest packages/ -m "not integration"` — **185 passed** (183 pre-existing + 2 new regression tests)
- `uv run mypy packages/godoo/src packages/godoo-testcontainers/src` — **Success: no issues found in 45 source files**
- `uv run ruff check .` — **All checks passed**
- `uv run ruff format --check .` — **67 files already formatted**
- `grep "except (ValueError, TypeError)" packages/godoo/src/godoo/client.py` — found
- `grep "_UndefinedType" packages/godoo/src/godoo/client.py` — found

## New Regression Tests

| Test | Covers |
|------|--------|
| `test_read_binary_malformed_base64` | CR-02: malformed base64 → OdooValidationError (not binascii.Error) |
| `test_aexit_preserves_body_exception_when_aclose_fails` | WR-04: body ValueError propagates when aclose() also raises RuntimeError |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed with one deviation in test design:

**1. [Rule 1 - Bug] WR-04 test required patch.object rather than direct __aenter__ patching**
- **Found during:** Task 3
- **Issue:** Python dunder method lookup bypasses instance `__dict__`; assigning `c.__aenter__ = fake_fn` has no effect when `async with c:` calls `type(c).__aenter__(c)`.
- **Fix:** Used `unittest.mock.patch.object(c, "authenticate", ...)` and `patch.object(c, "aclose", ...)` to mock the two relevant methods, then used actual `async with c:` with a body that raises ValueError.
- **Files modified:** `packages/godoo/tests/test_client.py`
- **Commit:** e098a72 (included in Task 3 commit)

**2. [Rule 2 - Narrowing] mypy needs assert for _UndefinedType narrowing**
- **Found during:** Task 2
- **Issue:** mypy does not narrow a union type using `is sentinel_instance` identity checks (only narrows on `isinstance` or `is None`/`is not None`). After the `if is _UNDEFINED: return` branch, `_safety_context` remained typed as `SafetyContext | _UndefinedType | None` in the else path.
- **Fix:** Added `assert not isinstance(self._safety_context, _UndefinedType)` to narrow the type for mypy. Zero runtime cost in production; documents invariant clearly.
- **Files modified:** `packages/godoo/src/godoo/client.py`
- **Commit:** 00fbf55

## Known Stubs

None.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All changes are internal client hardening.

## Self-Check: PASSED

- `packages/godoo/src/godoo/client.py` — found (modified)
- `packages/godoo/tests/test_client.py` — found (modified)
- Commit 26eeea6 — found (Task 1)
- Commit 00fbf55 — found (Task 2)
- Commit e098a72 — found (Task 3)
- Commit 4bc0750 — found (Task 4)
- 185 tests pass, mypy clean, ruff clean
