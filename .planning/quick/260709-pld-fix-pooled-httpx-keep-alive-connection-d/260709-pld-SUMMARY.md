---
phase: quick-260709-pld
plan: 01
status: complete
subsystem: godoo-client transport
tags: [httpx, keep-alive, transport, bugfix]
dependency-graph:
  requires: []
  provides: [ISSUE-1]
  affects: [packages/godoo-client/src/godoo/client/rpc/transport.py]
tech-stack:
  added: []
  patterns: [httpx.Limits(max_keepalive_connections=0) per-instance client construction]
key-files:
  created: []
  modified:
    - packages/godoo-client/src/godoo/client/rpc/transport.py
    - packages/godoo-client/tests/test_transport.py
decisions:
  - "Disabled keep-alive pooling entirely (max_keepalive_connections=0) rather than adding retry-on-RemoteProtocolError, matching plan's TDD spec and issue #1 root-cause analysis"
metrics:
  duration: "~10 minutes"
  completed: 2026-07-09
---

# Phase quick-260709-pld Plan 01: Disable httpx keep-alive pooling Summary

Disabled httpx keep-alive connection pooling in `JsonRpcTransport` by passing `httpx.Limits(max_keepalive_connections=0)` to the underlying `httpx.AsyncClient`, fixing single-worker Odoo dev servers dropping the pooled connection on the 2nd+ RPC call (issue #1).

## What Was Built

`JsonRpcTransport.__init__` (`packages/godoo-client/src/godoo/client/rpc/transport.py`) now constructs
`self._limits = httpx.Limits(max_keepalive_connections=0)` and passes `limits=self._limits` alongside the
existing `timeout=timeout` keyword to `httpx.AsyncClient(...)`. This forces every RPC call to open a fresh
TCP connection instead of reusing a pooled keep-alive connection, matching the TS twin's automatic recovery
behavior via undici. A brief inline comment documents the rationale (single-worker Odoo drops pooled
connections between requests; httpx's `retries=` option does not cover mid-request `RemoteProtocolError` on
an already-pooled connection).

A new regression test `test_transport_disables_keepalive_pooling` in `packages/godoo-client/tests/test_transport.py`
asserts `t._limits.max_keepalive_connections == 0`, following the existing `test_transport_timeout_param_accepted`
style (construct transport, assert on stored httpx client config).

## TDD Cycle

- **RED** (`a93f0bc`): Added `test_transport_disables_keepalive_pooling` asserting `t._limits.max_keepalive_connections == 0`. Ran and confirmed failure: `AttributeError: 'JsonRpcTransport' object has no attribute '_limits'`.
- **GREEN** (`6a335f6`): Implemented the `httpx.Limits(max_keepalive_connections=0)` construction and wired it into `httpx.AsyncClient(...)`. Re-ran the test suite; all pass.
- **REFACTOR**: Not needed — the change is minimal (3 lines + comment) and no cleanup was required.

## Verification

- `uv run pytest packages/godoo-client/tests/test_transport.py -q` — 20 passed (19 existing + 1 new), including `test_call_after_auth` (two sequential RPC calls succeed) and `test_transport_timeout_param_accepted` (timeout wiring unaffected).
- `uv run pytest packages/ -m "not integration" -q` — full unit suite (509 tests) passes with no regressions.
- `uv run ruff check packages/godoo-client/src/godoo/client/rpc/transport.py packages/godoo-client/tests/test_transport.py` — clean.
- `uv run ruff format --check packages/godoo-client/src/godoo/client/rpc/transport.py packages/godoo-client/tests/test_transport.py` — both already formatted.
- `uv run mypy packages/godoo-client/src` — Success: no issues found in 45 source files.
- Full-repo `uv run ruff check .` reports one pre-existing, unrelated failure in `spikes/08-pyodide/transport_pyfetch.py` (import-sort ordering) — out of scope for this task per scope-boundary rule; not touched by this plan, logged below as deferred (not fixed).

## Deviations from Plan

None — plan executed exactly as written. Task-file-path correction noted in the execution prompt
(`packages/godoo-client/src/godoo/client/rpc/transport.py`, not `rpc/transport.py`) matched the actual
repo layout with no further adjustment needed.

## Deferred / Out-of-Scope Findings

| Item | File | Status |
|------|------|--------|
| Pre-existing ruff I001 (unsorted import block) | `spikes/08-pyodide/transport_pyfetch.py` | Out of scope — pre-existing, unrelated to this task's files; not fixed |

## Commits

- `a93f0bc` — `test(client): add failing regression test for keep-alive pooling`
- `6a335f6` — `fix(client): disable httpx keep-alive pooling in JsonRpcTransport`

## Self-Check: PASSED

- FOUND: packages/godoo-client/src/godoo/client/rpc/transport.py contains `max_keepalive_connections=0`
- FOUND: packages/godoo-client/tests/test_transport.py contains `test_transport_disables_keepalive_pooling`
- FOUND commit a93f0bc in git log
- FOUND commit 6a335f6 in git log
