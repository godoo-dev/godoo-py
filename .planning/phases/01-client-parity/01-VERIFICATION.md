---
phase: 01-client-parity
verified: 2026-05-19T13:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed:
    - "read_binary raises a typed OdooValidationError — never a raw binascii.Error — on malformed base64 (CR-02)"
    - "_safety_context has a precise static type (SafetyContext | _UndefinedType | None, no Any) so mypy --strict fully checks the sentinel/None/SafetyContext states (WR-03)"
    - "__aexit__ preserves the exception raised by the async with body when aclose() also fails — the close failure is logged, not propagated (WR-04)"
    - "with_context / _OdooContextScope docstrings accurately describe ContextVar propagation to tasks spawned inside the block (WR-05)"
    - "CR-01 (iter_search_read short-page break) dismissed as non-defect — correct standard keyset pagination; Odoo applies record rules inside SQL LIMIT before returning the page"
  gaps_remaining: []
  regressions: []
---

# Phase 1: Client Parity Verification Report (Re-Verification)

**Phase Goal:** The godoo client package reaches full parity with @godoo/client and all adjacent transport/service bugs are fixed
**Verified:** 2026-05-19T13:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (plan 01-05 closed CR-02, WR-03, WR-04, WR-05; CR-01 dismissed)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `async with OdooClient(...)` opens/closes session automatically | VERIFIED | `__aenter__` (line 438) calls `authenticate()` and returns self; `__aexit__` (lines 443-459) calls `aclose()` with exception-safe try/except. Test `test_async_context_manager_authenticates_and_closes` passes. |
| 2 | `async for record in client.iter_search_read(...)` streams large result sets without loading all into memory | VERIFIED | `iter_search_read` (line 229) is an async generator using keyset (id-cursor) pagination with configurable `batch_size=500`. CR-01 dismissed: the `if len(batch) < fetch_size: break` is correct standard keyset pagination — Odoo applies record rules inside SQL WHERE before LIMIT, so a short page genuinely means end-of-data. Existing two-page, limit, and id-strip tests cover the termination invariant. |
| 3 | `client.with_context(lang="fr_FR").search_read(...)` threads context to RPC calls within the block | VERIFIED | `_OdooContextScope` (line 54) backed by `_ambient_context` ContextVar; injected in `call()` at line 170. Docstrings updated (WR-05) to document ContextVar task-propagation semantics accurately. Five tests pass including nested merge, explicit-kwarg-wins, and concurrent isolation. |
| 4 | `fields_get()`, `ref()`, `execute_kw()`, `read_binary()`, bulk `create` all return correct typed results | VERIFIED | All five methods present and substantive: `fields_get` (line 280), `ref` (line 287), `execute_kw` (line 306), `read_binary` (line 319) — now guarded with `try/except (ValueError, TypeError)` raising `OdooValidationError` (CR-02 fix), `create` with `@overload` (lines 337-352). All CLIENT-04 through CLIENT-08 tests pass plus new `test_read_binary_malformed_base64` regression test. |
| 5 | `CdcService.get_feed` works from class API; transport timeouts raise `OdooTimeoutError`; configurable request timeout respected | VERIFIED | `get_feed` is `def` (not `async def`) in service.py line 38. `except httpx.TimeoutException` at transport.py line 87 before the generic `except httpx.RequestError` handler. `OdooClientConfig.timeout` wired to `JsonRpcTransport(timeout=config.timeout)`. Three timeout tests pass. |

**Score:** 5/5 truths verified

### Re-Verification: Gap Closure Confirmation

All four items raised by the initial `human_needed` verdict have been resolved:

**CR-02 — read_binary base64 guard (CLOSED)**

`read_binary` in `client.py` now wraps `base64.b64decode(raw)` in `try/except (ValueError, TypeError)` and raises `OdooValidationError(f"Binary field {field!r} on {model}:{record_id} is not valid base64") from exc`. A `binascii.Error` (which is a `ValueError` subclass) can no longer escape as a non-`OdooError` exception. The regression test `test_read_binary_malformed_base64` asserts that the payload `"@@@notbase64@@@"` raises `OdooValidationError`, that the raised exception is an `OdooError` subclass, and that the field name appears in the message.

**WR-03 — _safety_context Any annotation (CLOSED)**

The bare `object()` sentinel was replaced with a `_UndefinedType` class and a `Final`-typed singleton `_UNDEFINED: Final = _UndefinedType()`. The attribute annotation at line 97 is now `self._safety_context: SafetyContext | _UndefinedType | None = _UNDEFINED`. The `Any` annotation is gone. `_effective_safety()` uses `assert not isinstance(self._safety_context, _UndefinedType)` to narrow the type for mypy after the `is _UNDEFINED` branch returns. `mypy --strict` passes cleanly.

**WR-04 — __aexit__ exception masking (CLOSED)**

`__aexit__` now wraps `await self.aclose()` in `try/except Exception`. When the block body raised (`exc_val is not None`) and `aclose()` also raises, the close failure is logged with `logger.warning(...)` and the method returns normally, allowing the original body exception to propagate. When the exit is clean and `aclose()` raises, the exception is re-raised normally. The regression test `test_aexit_preserves_body_exception_when_aclose_fails` confirms that raising `ValueError("body error")` in the body propagates out even when `aclose()` raises `RuntimeError`.

**CR-01 — iter_search_read short-page break (DISMISSED)**

Not a defect. `if len(batch) < fetch_size: break` is correct standard keyset pagination: Odoo evaluates record rules inside `search_read`'s SQL `WHERE` clause before applying `LIMIT`, so a page shorter than the requested limit always means no more records match for this cursor. This is the same pattern used by every keyset paginator against Odoo's API. The existing unit tests (two-page traversal, limit cutoff, id-strip) cover the termination invariant. No code change required.

**WR-05 — with_context docstrings (CLOSED)**

`_OdooContextScope` class docstring and `with_context` method docstring both now state that tasks spawned via `asyncio.create_task()` inside the block inherit a copy of the ambient context at creation time and retain it independently — the copy is not reset when the block exits. Docstring-only change; no behavior modified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/godoo/src/godoo/client.py` | Full client parity + gap-closure hardening | VERIFIED | 462 lines; all methods present and substantive; CR-02 guard, WR-03 typed sentinel, WR-04 exception-safe aexit, WR-05 docstrings all present |
| `packages/godoo/tests/test_client.py` | All CLIENT-01 through CLIENT-08 tests + 2 regression tests | VERIFIED | `test_read_binary_malformed_base64` and `test_aexit_preserves_body_exception_when_aclose_fails` both present and passing |
| `packages/godoo/src/godoo/rpc/transport.py` | Timeout-aware transport with OdooTimeoutError | VERIFIED | `except httpx.TimeoutException` at line 87 before `except httpx.RequestError` |
| `packages/godoo/src/godoo/services/cdc/service.py` | `CdcService.get_feed` as plain def | VERIFIED | Line 38: `def get_feed` (no async keyword) |
| `packages/godoo/src/godoo/py.typed` | Empty PEP 561 marker | VERIFIED | File exists (0 bytes) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `read_binary base64.b64decode` | `OdooValidationError` | `try/except (ValueError, TypeError)` | WIRED | Lines 331-334 in client.py; `raise OdooValidationError(...) from exc` |
| `_safety_context attribute` | `_UndefinedType sentinel` | `SafetyContext \| _UndefinedType \| None` annotation | WIRED | Line 97 in client.py; `_UNDEFINED: Final = _UndefinedType()` at line 45 |
| `__aexit__ aclose()` | `logger.warning` on close failure | `try/except Exception` with `exc_val is None` branch | WIRED | Lines 455-459 in client.py |
| `_OdooContextScope docstring` | ContextVar task-propagation statement | Updated class + method docstrings | WIRED | Lines 55-59 (`_OdooContextScope`) and lines 219-226 (`with_context`) |
| `OdooClientConfig.timeout` | `JsonRpcTransport.__init__(timeout=)` | `OdooClient.__init__` wiring | WIRED | Line 78: `JsonRpcTransport(config.url, config.database, timeout=config.timeout)` |
| `httpx.TimeoutException` | `OdooTimeoutError` | handler order in transport.py | WIRED | Line 87: TimeoutException before RequestError at line 89 |
| `CdcService.get_feed (plain def)` | `get_feed in functions.py (async generator)` | `return get_feed(self._client, options)` | WIRED | Line 39 in service.py; no `await` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `except (ValueError, TypeError)` guard in read_binary | grep in client.py | Lines 331-334 — guard present, raises OdooValidationError | PASS |
| `_safety_context: SafetyContext \| _UndefinedType \| None` (no Any) | grep in client.py | Line 97 — exact annotation, no Any | PASS |
| `_UNDEFINED: Final = _UndefinedType()` | grep in client.py | Line 45 — typed Final singleton | PASS |
| `__aexit__` try/except preserving body exception | grep in client.py | Lines 455-459 — try/except with exc_val branch and logger.warning | PASS |
| ContextVar task-propagation in `_OdooContextScope` docstring | grep in client.py | Lines 57-59 — asyncio.create_task propagation documented | PASS |
| Unit test suite | `uv run pytest packages/ -m "not integration" -q` | **185 passed** in 2.77s | PASS |
| Regression tests (read_binary + aexit) | `uv run pytest ... -k "read_binary or aexit"` | 5 passed (3 pre-existing + 2 new) | PASS |
| mypy --strict | `uv run mypy packages/godoo/src packages/godoo-testcontainers/src` | **Success: no issues found in 45 source files** | PASS |
| ruff lint | `uv run ruff check .` | **All checks passed** | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CLIENT-01 | 01-03-PLAN.md | `async with OdooClient(...)` context manager | SATISFIED | `__aenter__`/`__aexit__` in client.py; WR-04 exception-safe aexit now added; test passes |
| CLIENT-02 | 01-03-PLAN.md | `iter_search_read()` keyset-paginated async generator | SATISFIED | `iter_search_read` in client.py; CR-01 dismissed; existing tests cover termination |
| CLIENT-03 | 01-03-PLAN.md | `with_context()` ambient RPC context | SATISFIED | `_OdooContextScope` + `_ambient_context` ContextVar; WR-05 docstrings updated; 5 tests pass |
| CLIENT-04 | 01-04-PLAN.md | `fields_get()` field metadata | SATISFIED | `fields_get` in client.py; tests pass |
| CLIENT-05 | 01-04-PLAN.md | `ref(xml_id)` XML-ID lookup | SATISFIED | `ref` in client.py; 3 tests pass |
| CLIENT-06 | 01-04-PLAN.md | `execute_kw()` raw RPC passthrough | SATISFIED | `execute_kw` in client.py; test passes |
| CLIENT-07 | 01-04-PLAN.md | `read_binary()` binary field decoder | SATISFIED | `read_binary` in client.py; CR-02 guard added; 4 tests pass (3 pre-existing + 1 new regression) |
| CLIENT-08 | 01-04-PLAN.md | Bulk `create` with list of dicts | SATISFIED | `@overload create` in client.py; bulk and empty-list tests pass |
| CLIENT-10 | 01-02-PLAN.md | `py.typed` PEP 561 marker | SATISFIED | `packages/godoo/src/godoo/py.typed` exists (0 bytes) |
| FIXES-01 | 01-02-PLAN.md | `CdcService.get_feed` returns usable async iterator | SATISFIED | `def get_feed` (not async def) in service.py; `test_get_feed_is_not_coroutine_function` passes |
| FIXES-02 | 01-01-PLAN.md | Transport timeouts raise `OdooTimeoutError` | SATISFIED | `except httpx.TimeoutException` at transport.py; 2 timeout tests pass |
| FIXES-03 | 01-01-PLAN.md | Configurable request timeout on `OdooClientConfig` | SATISFIED | `timeout: float \| None = None` on `OdooClientConfig`; wired to `JsonRpcTransport`; test passes |

All 12 phase requirements (CLIENT-01/02/03/04/05/06/07/08/10, FIXES-01/02/03) are satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `packages/godoo/src/godoo/client.py` | 108-111 | Dead/redundant branch in `_effective_safety` (WR-02) | Info | Cosmetic unreachable `else None` arm; no behavioral impact; mypy passes; tracked in 01-REVIEW.md |

No TBD/FIXME/XXX/debt markers in phase-modified files. No stubs. No unresolved warnings from prior verification remain.

### Human Verification Required

None. All items previously routed to human verification have been resolved:

- CR-02: Closed by guarded `try/except (ValueError, TypeError)` + regression test
- CR-01: Dismissed as non-defect (correct standard keyset pagination)

---

## Summary

Phase 1 goal — "The godoo client package reaches full parity with @godoo/client and all adjacent transport/service bugs are fixed" — is fully achieved.

All 12 requirements (CLIENT-01 through CLIENT-08, CLIENT-10, FIXES-01/02/03) are implemented with substantive, non-stub code wired into the client surface. The gap-closure plan (01-05) resolved every item that prevented the initial `passed` verdict:

- `read_binary` now raises `OdooValidationError` (never a raw `binascii.Error`) on malformed base64
- `_safety_context` carries a precise `SafetyContext | _UndefinedType | None` static type (no `Any`)
- `__aexit__` preserves the body exception when `aclose()` also fails
- `with_context` / `_OdooContextScope` docstrings accurately describe ContextVar task-propagation semantics
- CR-01 was reviewed and dismissed: the short-page break is correct standard keyset pagination

Quality gate passes cleanly: **185 unit tests pass** (185/185 incl. 2 new regression tests), **mypy --strict** reports no issues in 45 source files, **ruff** reports all checks passed.

---

_Verified: 2026-05-19T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
