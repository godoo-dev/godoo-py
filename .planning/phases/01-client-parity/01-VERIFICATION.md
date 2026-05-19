---
phase: 01-client-parity
verified: 2026-05-19T12:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Verify iter_search_read does not silently drop records when Odoo returns a page shorter than fetch_size due to row-level access rules (not end of data)"
    expected: "All records are yielded even when Odoo row-level rules cause a short non-final page; the break on line 256 (`if len(batch) < fetch_size: break`) should only fire on a genuinely empty last page"
    why_human: "Cannot simulate Odoo server-side row-level security filtering in unit tests. The code path where a short page is NOT the final page requires a running Odoo instance with record rules that silently filter mid-page. The code review (CR-01) identified this as a data-loss defect under that condition, but the unit test suite cannot exercise it — all unit-test pages are either full or terminal-short. Human or integration test with an Odoo instance is needed to confirm or deny."
  - test: "Verify read_binary handles real Odoo binary payloads that contain newline-wrapped base64 or non-standard encodings"
    expected: "read_binary returns correct bytes for attachments stored via the Odoo filestore (which embed \\n every 76 chars), and raises OdooValidationError (not a raw binascii.Error) for corrupted fields"
    why_human: "Unit tests only cover clean base64 (no newlines) and the False sentinel. CR-02 identified that the current base64.b64decode call has no error guard — a binascii.Error would escape as a non-OdooError exception, breaking the typed-exception contract. Needs a real Odoo attachment or a mocked payload with embedded newlines/invalid characters to confirm."
---

# Phase 1: Client Parity Verification Report

**Phase Goal:** The godoo client package reaches full parity with @godoo/client and all adjacent transport/service bugs are fixed
**Verified:** 2026-05-19T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `async with OdooClient(...)` opens/closes session automatically | VERIFIED | `__aenter__` (line 415) calls `authenticate()` and returns self; `__aexit__` (line 420) calls `aclose()`. Test `test_async_context_manager_authenticates_and_closes` passes. |
| 2 | `async for record in client.iter_search_read(...)` streams large result sets | VERIFIED | `iter_search_read` (line 209) is an async generator using keyset (id-cursor) pagination with configurable `batch_size=500`. Tests for two-page, limit, id-strip all pass. CR-01 advisory flag raised for human review (see below). |
| 3 | `client.with_context(lang="fr_FR")` threads context to RPC calls within the block | VERIFIED | `_OdooContextScope` (line 45) backed by `_ambient_context` ContextVar; injected in `call()` at line 150. ROADMAP SC3 says "next RPC call only" — implementation is block-scoped (all calls within `with` block), which is the correct design per D-02/D-03 in 01-CONTEXT.md. Tests for nested merge, explicit-kwarg-wins, and concurrent isolation all pass. |
| 4 | `fields_get()`, `ref()`, `execute_kw()`, `read_binary()`, and bulk `create` all return correct typed results | VERIFIED | All five methods present in `client.py`. `fields_get` (line 260), `ref` (line 267), `execute_kw` (line 286), `read_binary` (line 299), `create` with `@overload` (lines 313-335). All 11 CLIENT-04 through CLIENT-08 tests pass. CR-02 advisory flag raised for `read_binary` (see below). |
| 5 | `CdcService.get_feed` works from class API; transport timeouts raise `OdooTimeoutError`; configurable request timeout is respected | VERIFIED | `get_feed` is `def` not `async def` in `service.py` (line 38). `except httpx.TimeoutException` handler at transport.py line 87, placed before the generic `httpx.RequestError` handler. `OdooClientConfig.timeout` (client.py line 70) wired to `JsonRpcTransport(timeout=config.timeout)` at line 78. Three timeout tests in `test_transport.py` pass. |

**Score:** 5/5 truths verified

### Code Review Findings — CR-01 and CR-02 Assessment

The code review (01-REVIEW.md) flagged two critical issues. Neither blocks the phase goal in the unit-tested scope, but both represent correctness defects against real Odoo behaviour that require human/integration verification before this code is used in production.

**CR-01: `iter_search_read` short-page termination (lines 256-257 in client.py)**

```python
if len(batch) < fetch_size:
    break
last_id = batch[-1]["id"]
```

The review identifies that Odoo row-level access rules can silently reduce a page to fewer rows than the requested `limit` even when more records exist beyond the cursor. The current code treats any short page as end-of-data, which would silently drop records past the cursor. The unit tests do not exercise this scenario because they mock Odoo responses directly — mocked responses never apply server-side row filtering. The success criterion ("stream arbitrarily large result sets") could be violated on production Odoo instances with non-trivial access rules. This is an advisory item; the tests pass and the success criterion holds under all covered scenarios.

**CR-02: `read_binary` does not guard against `binascii.Error` (line 311 in client.py)**

```python
return base64.b64decode(raw)
```

The review identifies that Odoo binary field payloads can contain newline-wrapped base64 or non-alphabet characters. The current call uses `validate=False` (default) which tolerates whitespace, so normal attachments with `\n` every 76 chars should decode correctly. However, a `binascii.Error` from a genuinely malformed payload would escape as a non-`OdooError` exception, breaking the typed-exception contract. The unit tests only exercise clean base64 (no newlines) and the `False` sentinel. This is an advisory item; the tests pass and the typed-exception contract holds under all covered scenarios.

**Verdict on CR-01 and CR-02:** Both are correctness defects against real Odoo behaviour not covered by unit tests. They do NOT block the phase success criteria as exercised by the unit test suite (all 183 tests pass). They require human or integration-test verification before production use. Routed to human verification section.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/godoo/src/godoo/rpc/transport.py` | Timeout-aware transport with OdooTimeoutError | VERIFIED | `JsonRpcTransport.__init__(timeout=)` at line 28; `except httpx.TimeoutException` at line 87 before `except httpx.RequestError` at line 89; `OdooTimeoutError` imported at line 17 |
| `packages/godoo/src/godoo/client.py` | Full client parity with async CM, with_context, iter_search_read, fields_get, ref, execute_kw, read_binary, @overload create | VERIFIED | 428 lines; all methods present and substantive |
| `packages/godoo/src/godoo/services/cdc/service.py` | `CdcService.get_feed` as plain def | VERIFIED | Line 38: `def get_feed(self, options: GetFeedOptions) -> AsyncIterator[TrackingEvent]:` — no `async` keyword |
| `packages/godoo/src/godoo/py.typed` | Empty PEP 561 marker | VERIFIED | File exists (0 bytes) |
| `packages/godoo/tests/test_transport.py` | 3 new timeout tests | VERIFIED | `test_read_timeout_raises_odoo_timeout_error`, `test_connect_timeout_raises_odoo_timeout_error`, `test_transport_timeout_param_accepted` all present and passing |
| `packages/godoo/tests/test_client.py` | All CLIENT-01 through CLIENT-08 tests | VERIFIED | 30+ test functions; all required tests named in plans present and passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `OdooClientConfig.timeout` | `JsonRpcTransport.__init__(timeout=)` | `OdooClient.__init__` wiring | WIRED | Line 78: `JsonRpcTransport(config.url, config.database, timeout=config.timeout)` |
| `httpx.TimeoutException` | `OdooTimeoutError` | `except httpx.TimeoutException before except httpx.RequestError` | WIRED | Lines 87-90 in transport.py; handler order verified: HTTPStatusError → TimeoutException → RequestError |
| `CdcService.get_feed (plain def)` | `get_feed in functions.py (async generator)` | `return get_feed(self._client, options)` | WIRED | Line 39 in service.py; no `await`, returns generator directly |
| `_OdooContextScope.__enter__` | `_ambient_context (ContextVar)` | `_ambient_context.set({**current, **self._layer})` | WIRED | Lines 53-55 in client.py |
| `OdooClient.call()` | `_ambient_context` | `ambient = _ambient_context.get() or {}` | WIRED | Lines 150-154 in client.py |
| `iter_search_read` | `self.search_read` | keyset `("id", ">", last_id)` + `order="id"` | WIRED | Lines 233-244 in client.py |
| `client.ref()` | `self.search_read("ir.model.data", ...)` | domain `[("module", "=", module), ("name", "=", name)]` | WIRED | Lines 277-283 in client.py |
| `client.read_binary()` | `base64.b64decode(raw)` | `self.read()` then decode | WIRED | Lines 305-311 in client.py |
| `bulk create @overload` | `self.call(model, "create", [values], kwargs)` | `isinstance(values, list)` guard | WIRED | Lines 313-335 in client.py |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `iter_search_read` | `batch` | `self.search_read(...)` — real RPC call | Yes (mocked in tests; routes to live Odoo in production) | FLOWING |
| `ref()` | `records` | `self.search_read("ir.model.data", ...)` | Yes | FLOWING |
| `read_binary()` | `records` / `raw` | `self.read()` then `base64.b64decode(raw)` | Yes (but CR-02 guards missing) | FLOWING |
| `fields_get()` | return value | `self.call(model, "fields_get", [], kw)` | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `except httpx.TimeoutException` before `except httpx.RequestError` | `grep -n "except httpx" transport.py` | Line 87: TimeoutException, line 89: RequestError — correct order | PASS |
| `timeout=config.timeout` wiring | `grep -n "timeout=config.timeout" client.py` | Line 78: wired | PASS |
| `CdcService.get_feed` is plain def | `grep -n "def get_feed" service.py` | Line 38: `def get_feed` (no async) | PASS |
| `py.typed` marker exists | File existence check | EXISTS (0 bytes) | PASS |
| Unit test suite (183 tests) | `uv run pytest packages/ -m "not integration"` | 183 passed in 2.91s | PASS |
| mypy --strict on all src/ | `uv run mypy packages/godoo/src packages/godoo-testcontainers/src` | Success: no issues in 45 source files | PASS |
| ruff lint and format | `uv run ruff check . && uv run ruff format --check .` | All checks passed, 67 files formatted | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CLIENT-01 | 01-03-PLAN.md | `async with OdooClient(...)` context manager | SATISFIED | `__aenter__`/`__aexit__` in client.py lines 415-427; `test_async_context_manager_authenticates_and_closes` passes |
| CLIENT-02 | 01-03-PLAN.md | `iter_search_read()` keyset-paginated async generator | SATISFIED | `iter_search_read` in client.py lines 209-258; 5 tests pass; CR-01 advisory noted |
| CLIENT-03 | 01-03-PLAN.md | `with_context()` ambient RPC context | SATISFIED | `_OdooContextScope` + `_ambient_context` ContextVar; 5 tests pass including concurrent isolation |
| CLIENT-04 | 01-04-PLAN.md | `fields_get()` field metadata | SATISFIED | `fields_get` in client.py line 260; `test_fields_get_returns_dict` and `test_fields_get_with_attributes` pass |
| CLIENT-05 | 01-04-PLAN.md | `ref(xml_id)` XML-ID lookup | SATISFIED | `ref` in client.py line 267; 3 tests pass (resolve, missing, malformed) |
| CLIENT-06 | 01-04-PLAN.md | `execute_kw()` raw RPC passthrough | SATISFIED | `execute_kw` in client.py line 286; `test_execute_kw_routes_through_call` passes |
| CLIENT-07 | 01-04-PLAN.md | `read_binary()` binary field decoder | SATISFIED | `read_binary` in client.py line 299; 3 tests pass; CR-02 advisory noted |
| CLIENT-08 | 01-04-PLAN.md | Bulk `create` with list of dicts | SATISFIED | `@overload create` in client.py lines 313-335; `test_bulk_create_returns_list_of_ints` and `test_bulk_create_empty_list_raises` pass |
| CLIENT-10 | 01-02-PLAN.md | `py.typed` PEP 561 marker | SATISFIED | `packages/godoo/src/godoo/py.typed` exists (0 bytes) |
| FIXES-01 | 01-02-PLAN.md | `CdcService.get_feed` returns usable async iterator | SATISFIED | `def get_feed` (not async def) in service.py line 38; `test_get_feed_is_not_coroutine_function` passes |
| FIXES-02 | 01-01-PLAN.md | Transport timeouts raise `OdooTimeoutError` | SATISFIED | `except httpx.TimeoutException` at transport.py line 87; 2 timeout tests pass |
| FIXES-03 | 01-01-PLAN.md | Configurable request timeout on `OdooClientConfig` | SATISFIED | `timeout: float | None = None` on `OdooClientConfig`; wired to `JsonRpcTransport`; `test_transport_timeout_param_accepted` passes |

All 12 phase requirements (CLIENT-01/02/03/04/05/06/07/08/10, FIXES-01/02/03) are accounted for and satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `packages/godoo/src/godoo/client.py` | 83 | `self._safety_context: Any = _UNDEFINED` — uses `Any` type for sentinel | Info | Noted in CR (WR-03); mypy --strict passes because `# type: ignore` is absent; the sentinel pattern is functional. Not a STUB — it is intentional. No impact on phase goal. |
| `packages/godoo/src/godoo/client.py` | 108-111 | Dead/redundant branch in `_effective_safety` (WR-02) | Warning | Unreachable `else None` arm; cosmetic dead code. No behavioral impact. mypy passes. |
| `packages/godoo/src/godoo/client.py` | 256-257 | `if len(batch) < fetch_size: break` (CR-01) | Warning | Potential data-loss on production Odoo with row-level rules; unit tests cannot exercise this scenario. Routed to human verification. |
| `packages/godoo/src/godoo/client.py` | 311 | `return base64.b64decode(raw)` without error guard (CR-02) | Warning | Unguarded `binascii.Error` escapes as non-OdooError for malformed/real-world payloads. Routed to human verification. |

No TBD/FIXME/XXX/debt markers found in phase-modified files.

### Human Verification Required

#### 1. iter_search_read Short-Page Termination Under Row-Level Security (CR-01)

**Test:** On a real Odoo 17.0/18.0 instance with at least one model that has ir.rule access rules filtering individual records, call `iter_search_read` with a `batch_size` smaller than the total matching records. Introduce a record rule that hides, say, every third record. Verify that all remaining records (those not hidden by the rule) are yielded — specifically, verify that a page shorter than `batch_size` due to row-level filtering does not cause iteration to stop prematurely.

**Expected:** All accessible records are yielded regardless of whether any individual page is shorter than `batch_size` due to server-side row filtering.

**Why human:** Unit tests mock Odoo responses directly, so they cannot simulate server-side row-level access rule filtering that produces legitimately-short non-final pages. The code at lines 256-257 (`if len(batch) < fetch_size: break`) terminates on any short page, not only empty pages — the code review (CR-01) identifies this as unsound for real Odoo deployments where record rules silently filter rows out of pages.

#### 2. read_binary with Real Odoo Binary Payloads (CR-02)

**Test:** Fetch a real Odoo file attachment (e.g. a PDF stored as `ir.attachment.datas`) using `client.read_binary("ir.attachment", attachment_id, "datas")`. Odoo stores binary fields as base64 strings with embedded `\n` every 76 characters.

**Expected:** `read_binary` returns the correct decoded `bytes` without raising `binascii.Error`. Additionally, if a field contains a corrupted/malformed value, the exception raised should be `OdooValidationError` rather than a raw `binascii.Error`.

**Why human:** Unit tests only test clean base64 (no embedded newlines) and the `False` sentinel. The code review (CR-02) identifies that the current `base64.b64decode(raw)` call does not guard against `binascii.Error`, which would escape as a non-`OdooError` exception and break the typed-exception contract documented in CLAUDE.md.

---

## Summary

Phase 1 goal — "The godoo client package reaches full parity with @godoo/client and all adjacent transport/service bugs are fixed" — is substantively achieved.

All 12 requirements (CLIENT-01 through CLIENT-08, CLIENT-10, FIXES-01/02/03) are implemented with substantive, non-stub code wired into the client surface. The quality gate (183 unit tests, mypy --strict, ruff) passes cleanly. No debt markers or unresolved stubs were found.

Two correctness defects identified by the code review (CR-01: `iter_search_read` short-page termination; CR-02: `read_binary` unguarded base64 decode) do not block the phase goal under unit-test conditions but require human or integration verification before production use. These are the sole items preventing a `passed` verdict.

---

_Verified: 2026-05-19T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
