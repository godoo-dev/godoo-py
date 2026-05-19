---
phase: 01-client-parity
plan: "04"
subsystem: api
tags: [python, odoo, jsonrpc, typing, overload, base64]

# Dependency graph
requires:
  - phase: 01-03
    provides: iter_search_read, with_context, async context manager on OdooClient
provides:
  - fields_get method on OdooClient (CLIENT-04)
  - ref xml_id resolver on OdooClient (CLIENT-05)
  - execute_kw raw RPC passthrough on OdooClient (CLIENT-06)
  - read_binary binary field decoder on OdooClient (CLIENT-07)
  - overloaded bulk create on OdooClient (CLIENT-08)
  - Full Phase 1 client parity complete
affects: [02-introspection, 03-testcontainers, 04-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@overload pattern for single vs list return type discrimination at call sites"
    - "Local OdooValidationError raise before any RPC call for precondition failures"
    - "ir.model.data search_read pattern for xml_id resolution"

key-files:
  created: []
  modified:
    - packages/godoo/src/godoo/client.py
    - packages/godoo/tests/test_client.py

key-decisions:
  - "D-15: fields_get returns raw dict[str, Any] — no typed wrapper, Odoo native shape"
  - "D-16: ref() queries ir.model.data via search_read, raises OdooMissingError when not found"
  - "D-17: execute_kw routes through call() so safety guard still classifies and gates methods"
  - "D-18: read_binary uses base64.b64decode on Odoo response; returns b'' for False/None fields"
  - "D-07: create uses @overload so mypy infers exact int vs list[int] return type per call site"
  - "D-08: create(model, []) raises OdooValidationError locally before any RPC call"

patterns-established:
  - "@overload with isinstance guard: add two @overload signatures before the implementation def; use isinstance(values, list) to branch"
  - "Local precondition validation pattern: check inputs, raise OdooValidationError, then proceed to RPC"

requirements-completed:
  - CLIENT-04
  - CLIENT-05
  - CLIENT-06
  - CLIENT-07
  - CLIENT-08

# Metrics
duration: 12min
completed: 2026-05-19
---

# Phase 01 Plan 04: Client Parity — Remaining Methods Summary

**Five new OdooClient methods complete TypeScript parity: fields_get, ref (xml_id resolver), execute_kw (raw RPC passthrough), read_binary (base64 decoder), and @overload bulk create — Phase 1 fully complete.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-19T10:55:00Z
- **Completed:** 2026-05-19T11:07:00Z
- **Tasks:** 3 (TDD RED + GREEN combined across tasks 1/2/3)
- **Files modified:** 2

## Accomplishments

- Added `fields_get`, `ref`, `execute_kw`, `read_binary`, and overloaded `create` to OdooClient
- All five methods route through `call()` — safety guard classification is automatic for `execute_kw`
- `@overload` on `create` ensures mypy infers exact return type (int vs list[int]) at each call site
- 11 new unit tests covering all behaviors including edge cases (malformed xml_id, False field, empty list)
- Full quality gate passes: 183 unit tests, mypy --strict, ruff check/format all exit 0

## Task Commits

1. **TDD RED: Failing tests for CLIENT-04/05/06/07/08** - `612e6d5` (test)
2. **GREEN: Implement all five methods + overloaded create** - `406e20c` (feat)

_Note: TDD RED committed first to establish failing baseline; GREEN implemented all methods in one commit covering tasks 1, 2, and 3._

## Files Created/Modified

- `packages/godoo/src/godoo/client.py` — Added `import base64`, `overload` to typing imports, `OdooMissingError`/`OdooValidationError` to errors import; added `fields_get`, `ref`, `execute_kw`, `read_binary`; replaced `create` with overloaded version
- `packages/godoo/tests/test_client.py` — Added `import base64`, `OdooMissingError`/`OdooValidationError` imports; added 11 new test functions covering CLIENT-04 through CLIENT-08

## Decisions Made

- `fields_get` returns the raw dict keyed by field name (Odoo native shape) — no typed wrapper needed; the shape varies by model
- `ref()` validates xml_id format locally before any RPC call (raises `OdooValidationError` if no dot), then queries `ir.model.data` via `search_read` (raises `OdooMissingError` if empty result)
- `execute_kw` is a minimal one-liner delegating to `call()` — this is intentional; safety guard in `call()` handles classification
- `read_binary` returns `b""` for Odoo's `False` sentinel (unset binary field) — consistent with expected caller behavior
- `@overload` decorators on `create` placed before the implementation def per Python typing conventions (D-07)

## Deviations from Plan

None — plan executed exactly as written. All implementations match the PATTERNS.md reference exactly. Ruff formatting was applied to test_client.py (auto-format, not a behavioral deviation).

## Issues Encountered

None. All tests passed on first run after implementation.

## Known Stubs

None.

## Threat Flags

None. All threat model items from the plan were addressed in implementation:
- T-04-01 (execute_kw elevation): execute_kw routes through call() which calls infer_safety_level(method) and _guard(op)
- T-04-02 (read_binary base64): base64.b64decode is stdlib; False/None sentinel handled with b"" return
- T-04-03 (ref injection): xml_id split on "." and used as exact-match domain values; malformed format raises before RPC
- T-04-04 (bulk create DoS): no size limit — documented as caller responsibility; accepted

## Self-Check

Verified:
- [x] `packages/godoo/src/godoo/client.py` exists and contains @overload (2 matches), base64, ir.model.data, OdooMissingError, OdooValidationError
- [x] `packages/godoo/tests/test_client.py` exists with all 11 new tests
- [x] Commit `612e6d5` exists (TDD RED)
- [x] Commit `406e20c` exists (GREEN implementation)
- [x] 183 unit tests pass, mypy --strict exits 0, ruff exits 0

## Self-Check: PASSED

## Next Phase Readiness

Phase 1 (Client Parity) is complete. All requirements CLIENT-01 through CLIENT-08 and FIXES-01/02/03 are implemented and tested.

Phase 2 (godoo-introspection) and Phase 3 (godoo-testcontainers parity) can now begin — they depend on Phase 1 client being complete. Per the planning decision, Phases 2 and 3 may run in parallel since the packages are independent.

---
*Phase: 01-client-parity*
*Completed: 2026-05-19*
