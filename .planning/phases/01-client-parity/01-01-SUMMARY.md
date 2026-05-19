---
phase: 01-client-parity
plan: "01"
subsystem: transport
tags: [fix, timeout, httpx, transport, reliability]
requirements: [FIXES-02, FIXES-03]

dependency_graph:
  requires: []
  provides:
    - configurable request timeout via OdooClientConfig.timeout
    - OdooTimeoutError raised on httpx.TimeoutException (ReadTimeout, ConnectTimeout)
  affects:
    - packages/godoo/src/godoo/rpc/transport.py
    - packages/godoo/src/godoo/client.py
    - packages/godoo/tests/test_transport.py

tech_stack:
  added: []
  patterns:
    - except httpx.TimeoutException before except httpx.RequestError (exception handler ordering)
    - timeout: float | None threaded from config to httpx.AsyncClient constructor

key_files:
  modified:
    - packages/godoo/src/godoo/rpc/transport.py
    - packages/godoo/src/godoo/client.py
    - packages/godoo/tests/test_transport.py

decisions:
  - "D-20: timeout is a single float | None field on OdooClientConfig, not an httpx.Timeout object — simpler API for callers"
  - "D-22: TimeoutException handler placed before RequestError handler so it is not silently swallowed by the generic network error handler"

metrics:
  duration_seconds: 323
  completed: "2026-05-19T10:47:58Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 01 Plan 01: Transport Timeout Fixes Summary

Configurable request timeout (FIXES-03) and correct TimeoutException-to-OdooTimeoutError mapping (FIXES-02) — surgical two-file patch plus three new unit tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix transport timeout source changes — FIXES-02 and FIXES-03 | 53868e7 | transport.py, client.py |
| 2 | Add timeout tests to test_transport.py | 5fc4c66 | test_transport.py |

## What Was Built

**FIXES-03 — configurable timeout:**
- Added `timeout: float | None = None` parameter to `JsonRpcTransport.__init__`; passed directly to `httpx.AsyncClient(timeout=timeout)`
- Added `timeout: float | None = field(default=None)` to `OdooClientConfig` dataclass
- Wired `config.timeout` to `JsonRpcTransport` constructor in `OdooClient.__init__`

**FIXES-02 — correct exception hierarchy:**
- Added `except httpx.TimeoutException as exc:` handler in `call_rpc` between the existing `httpx.HTTPStatusError` and `httpx.RequestError` handlers
- Handler raises `OdooTimeoutError(f"Request timed out: {exc}", cause=exc) from exc`
- Imported `OdooTimeoutError` in `transport.py` error imports block

**Tests (3 new, 18 total):**
- `test_read_timeout_raises_odoo_timeout_error` — ReadTimeout surfaces as OdooTimeoutError
- `test_connect_timeout_raises_odoo_timeout_error` — ConnectTimeout surfaces as OdooTimeoutError
- `test_transport_timeout_param_accepted` — timeout=30.0 threads to `_client.timeout.read`

## Verification Results

- `uv run pytest packages/godoo/tests/test_transport.py` — 18 passed
- `uv run pytest packages/ -m "not integration"` — 160 passed (no regressions)
- `uv run mypy packages/godoo/src packages/godoo-testcontainers/src` — no issues in 45 files
- `uv run ruff check . && uv run ruff format --check .` — all checks passed

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Changes are entirely within the existing transport layer boundary (godoo client → Odoo JSON-RPC endpoint).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| packages/godoo/src/godoo/rpc/transport.py | FOUND |
| packages/godoo/src/godoo/client.py | FOUND |
| packages/godoo/tests/test_transport.py | FOUND |
| .planning/phases/01-client-parity/01-01-SUMMARY.md | FOUND |
| Commit 53868e7 (Task 1) | FOUND |
| Commit 5fc4c66 (Task 2) | FOUND |
