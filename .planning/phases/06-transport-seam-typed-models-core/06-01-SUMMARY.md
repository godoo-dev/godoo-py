---
plan: 06-01
phase: 06-transport-seam-typed-models-core
status: complete
completed: 2026-05-28
requirements_addressed:
  - BROWSER-01
---

# Plan 06-01: Transport Protocol Seam — Summary

## What Was Built

Added the transport-injection seam (BROWSER-01): a stdlib `Transport` Protocol in
`godoo/client/rpc/protocol.py`, barrel-exported from `rpc/__init__.py`, with a
`transport_factory` field on `OdooClientConfig` and a single injection branch in
`OdooClient.__init__`. `JsonRpcTransport` satisfies the Protocol structurally without
modification.

## Tasks Completed

1. **Task 1** — Created `rpc/protocol.py` with 5-member `Transport(Protocol)` class
   (`session`, `authenticate`, `call`, `logout`, `aclose`). Updated `rpc/__init__.py`
   to barrel-export `Transport` with alphabetical `__all__` ordering.

2. **Task 2** — Extended `OdooClientConfig` with
   `transport_factory: Callable[[OdooClientConfig], Transport] | None = field(default=None)`.
   Added injection branch in `OdooClient.__init__`: calls `config.transport_factory(config)`
   when not None, falls back to `JsonRpcTransport(...)` exactly as v1.0.
   `Callable` and `Transport` both moved under `TYPE_CHECKING` per ruff TC002/TC003.

3. **Task 3** — Created `tests/test_transport_protocol.py` with
   `test_jsonrpc_transport_satisfies_protocol` — the mypy-assignment line
   `t: Transport = JsonRpcTransport("http://example", "db")` is the structural-conformance
   assertion; 5 `hasattr` assertions are belt-and-braces runtime checks.

## Key Files Created / Modified

- `packages/godoo-client/src/godoo/client/rpc/protocol.py` — NEW
- `packages/godoo-client/src/godoo/client/rpc/__init__.py` — MODIFIED (Transport barrel export)
- `packages/godoo-client/src/godoo/client/client.py` — MODIFIED (transport_factory field + injection branch)
- `packages/godoo-client/tests/test_transport_protocol.py` — NEW

## Deviations

- `OdooSessionInfo` in `protocol.py` moved under `TYPE_CHECKING` (ruff TC002 — only used in annotations).
- `Callable` in `client.py` moved under `TYPE_CHECKING` (ruff TC003 — PEP 563 makes all annotations strings).
- `Transport` import in test file moved under `TYPE_CHECKING` (ruff TC002 — same reason).

## Verification

- `uv run python -c "from godoo.client.rpc import Transport, ..."` → member set `{'session', 'authenticate', 'call', 'logout', 'aclose'}` exactly.
- Default-path and injected-path Python smoke tests both pass.
- `uv run pytest packages/ -m "not integration"` → 300 passed, 0 failed.
- `uv run mypy packages/godoo-client/src/...` → no issues.
- `uv run ruff check packages/godoo-client/...` → all checks passed.

## Self-Check: PASSED
