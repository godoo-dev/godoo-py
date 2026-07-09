---
phase: quick-260709-pld
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - packages/godoo-client/src/godoo/client/rpc/transport.py
  - packages/godoo-client/tests/test_transport.py
autonomous: true
requirements: [ISSUE-1]
must_haves:
  truths:
    - "JsonRpcTransport opens a fresh TCP connection per RPC (no keep-alive reuse)"
    - "A single JsonRpcTransport instance can make 2+ sequential RPC calls without a pooled-connection drop"
  artifacts:
    - path: packages/godoo-client/src/godoo/client/rpc/transport.py
      provides: "httpx.AsyncClient constructed with keep-alive pooling disabled"
      contains: "max_keepalive_connections=0"
    - path: packages/godoo-client/tests/test_transport.py
      provides: "regression test asserting keep-alive pooling is disabled"
      contains: "max_keepalive_connections"
  key_links:
    - from: packages/godoo-client/src/godoo/client/rpc/transport.py
      to: httpx.AsyncClient
      via: "limits=httpx.Limits(max_keepalive_connections=0)"
      pattern: "httpx\\.Limits\\(max_keepalive_connections=0\\)"
---

<objective>
Fix the pooled httpx keep-alive connection drop reported in godoo-dev/godoo-py#1:
`JsonRpcTransport` reuses one `httpx.AsyncClient` (and its pooled HTTP/1.1 keep-alive
connection) across every RPC. A single-worker Odoo dev server (the default started by
`OdooTestContainer`) does not reliably keep that connection reusable, so the first RPC
succeeds and the 2nd+ fails with `RemoteProtocolError` / `OdooNetworkError`. Disable
keep-alive connection pooling so every request opens a fresh TCP connection.

Purpose: Restore reliable multi-call behavior against single-worker Odoo instances,
matching the TS twin (`@godoo-dev/client`) which recovers automatically via undici.
Output: Updated transport that disables keep-alive pooling + a respx regression test.
</objective>

<execution_context>
@/home/marc/.claude/perficio/plugins/perficio/gsd-core/workflows/execute-plan.md
@/home/marc/.claude/perficio/plugins/perficio/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@packages/godoo-client/src/godoo/client/rpc/transport.py
@packages/godoo-client/tests/test_transport.py

Issue: https://github.com/godoo-dev/godoo-py/issues/1

Verified facts (from the codebase, do not re-derive):
- `httpx.Limits(max_keepalive_connections=0)` exposes a public attribute
  `.max_keepalive_connections == 0` — use this as the stable test assertion target.
- The existing test `test_transport_timeout_param_accepted` (bottom of the test file)
  reads `t._client.timeout.read`; follow that same "construct transport, assert on the
  httpx client config" style for the new regression test.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Disable httpx keep-alive pooling in JsonRpcTransport + add regression test</name>
  <files>packages/godoo-client/src/godoo/client/rpc/transport.py, packages/godoo-client/tests/test_transport.py</files>
  <read_first>
    packages/godoo-client/src/godoo/client/rpc/transport.py (the __init__ that constructs httpx.AsyncClient — line 30)
    packages/godoo-client/tests/test_transport.py (existing respx test patterns; especially test_transport_timeout_param_accepted at the bottom and test_call_after_auth)
  </read_first>
  <behavior>
    - Constructing a JsonRpcTransport creates an httpx.AsyncClient whose connection pool has max_keepalive_connections == 0 (assert via the stored httpx.Limits object's public .max_keepalive_connections attribute).
    - The existing timeout param still works: JsonRpcTransport(BASE_URL, DB, timeout=30.0) still yields _client.timeout.read == 30.0 (limits change must not regress timeout wiring).
    - Two sequential RPC calls on one authenticated transport both succeed (existing test_call_after_auth continues to pass).
  </behavior>
  <action>
    In `JsonRpcTransport.__init__` (packages/godoo-client/src/godoo/client/rpc/transport.py),
    change the `httpx.AsyncClient(timeout=timeout)` construction to also pass a limits
    object that disables keep-alive pooling. Build the limits with
    `httpx.Limits(max_keepalive_connections=0)` and assign it to an instance attribute
    (name it `self._limits`) so it is inspectable by the regression test; then pass
    `limits=self._limits` alongside the existing `timeout=timeout` keyword to
    `httpx.AsyncClient`. Keep the existing `from __future__ import annotations`, the
    `httpx` import, and all other constructor state (`_base_url`, `_db`, `_session`,
    `_password`) unchanged. Do NOT alter call_rpc, error handling, or any other method.
    Rationale to preserve in a brief inline comment: single-worker Odoo drops pooled
    keep-alive connections between requests, so each RPC must open a fresh connection
    (see issue #1); httpx's `retries=` option does not cover mid-request
    RemoteProtocolError on an already-pooled connection.

    In packages/godoo-client/tests/test_transport.py, add a new synchronous test
    `test_transport_disables_keepalive_pooling` (mirror the style of the existing
    `test_transport_timeout_param_accepted`): construct `JsonRpcTransport(BASE_URL, DB)`
    and assert `t._limits.max_keepalive_connections == 0`. Do not remove or weaken any
    existing test.
  </action>
  <acceptance_criteria>
    - transport.py contains the exact substring `max_keepalive_connections=0`.
    - transport.py passes `limits=` to `httpx.AsyncClient(...)` in `__init__`.
    - test_transport.py contains a test named `test_transport_disables_keepalive_pooling` that asserts `max_keepalive_connections == 0`.
    - `uv run pytest packages/godoo-client/tests/test_transport.py -q` passes (all existing tests + the new one).
    - `uv run ruff check packages/godoo-client && uv run mypy packages/godoo-client/src` report no errors.
  </acceptance_criteria>
  <verify>
    <automated>uv run pytest packages/godoo-client/tests/test_transport.py -q && uv run ruff check packages/godoo-client/src/godoo/client/rpc/transport.py packages/godoo-client/tests/test_transport.py && uv run mypy packages/godoo-client/src</automated>
  </verify>
  <done>
    JsonRpcTransport constructs its httpx.AsyncClient with keep-alive pooling disabled
    (max_keepalive_connections=0), the new regression test asserts this, all existing
    transport tests still pass, and ruff + mypy --strict are clean.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| godoo.client → Odoo JSON-RPC | Untrusted network transport; RPC responses cross here |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-pld-01 | Denial of Service | transport.py connection handling | low | accept | Disabling keep-alive opens a fresh TCP connection per RPC — marginally higher connection overhead against multi-worker production Odoo, but correctness against single-worker Odoo takes precedence (issue #1). No new external input introduced. |
| T-pld-SC | Tampering | dependency installs | low | accept | No new packages added; httpx already a pinned runtime dependency. No install task, so no Package Legitimacy Gate required. |
</threat_model>

<verification>
- `uv run pytest packages/godoo-client/tests/test_transport.py -q` — all transport tests pass including the new regression test.
- Full quality gate: `uv run ruff check . && uv run mypy packages/godoo-client/src`.
</verification>

<success_criteria>
- `JsonRpcTransport` no longer reuses pooled keep-alive connections; every RPC opens a fresh connection.
- Regression test locks in `max_keepalive_connections == 0`.
- No existing test regressed; ruff + mypy --strict clean.
</success_criteria>

<output>
Create `.planning/quick/260709-pld-fix-pooled-httpx-keep-alive-connection-d/260709-pld-SUMMARY.md` when done.
</output>
