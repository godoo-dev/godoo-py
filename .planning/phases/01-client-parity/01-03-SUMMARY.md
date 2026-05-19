---
phase: 01-client-parity
plan: 03
subsystem: client
tags: [python, asyncio, contextvars, async-generator, pagination, odoo, jsonrpc]

# Dependency graph
requires:
  - phase: 01-01
    provides: timeout field on OdooClientConfig
  - phase: 01-02
    provides: existing OdooClient CRUD helpers and transport
provides:
  - "__aenter__/__aexit__ on OdooClient — async context manager lifecycle"
  - "with_context() + _OdooContextScope + _ambient_context ContextVar — ambient RPC context"
  - "iter_search_read() — keyset-paginated async generator"
  - "Tests for CLIENT-01, CLIENT-02, CLIENT-03"
affects:
  - "01-04 — builds on same client.py; reads import structure"
  - "future-phases — iter_search_read is primary bulk-read API"

# Tech tracking
tech-stack:
  added:
    - "contextvars (stdlib) — ContextVar for task-safe ambient context"
    - "collections.abc.AsyncIterator (TYPE_CHECKING only) — return type for iter_search_read"
  patterns:
    - "Module-level ContextVar with None default (B039 compliant); callers treat None as empty dict"
    - "Sync context manager (_OdooContextScope) injecting into async call() chokepoint"
    - "Keyset (id-cursor) pagination with internal id injection + strip-on-yield"
    - "kwargs never mutated in-place — always `kwargs = {**kwargs, ...}`"

key-files:
  created: []
  modified:
    - "packages/godoo/src/godoo/client.py"
    - "packages/godoo/tests/test_client.py"

key-decisions:
  - "ContextVar default=None (not {}) to satisfy ruff B039 (mutable ContextVar defaults); code uses `get() or {}` at call sites"
  - "AsyncIterator import deferred to Task 2 (not Task 1) to avoid ruff F401 between commits"
  - "iter_search_read always injects 'id' into fetch fields for cursor advancement, then strips from yielded records when caller did not request it"
  - "_extract_rpc_kwargs helper in tests reads kwargs from params.args[6] (execute_kw wire format), not params.kwargs"

patterns-established:
  - "Pattern: _OdooContextScope.__enter__ uses ContextVar.set() + token; __exit__ uses token.reset() — safe for nested blocks"
  - "Pattern: ambient context merge in call() — ambient or explicit context= always copies kwargs dict, never mutates"
  - "Pattern: iter_search_read stop conditions — empty batch AND len(batch) < fetch_size guarantee termination (T-03-04 mitigated)"

requirements-completed:
  - CLIENT-01
  - CLIENT-02
  - CLIENT-03

# Metrics
duration: 6min
completed: 2026-05-19
---

# Phase 01 Plan 03: CLIENT-01/02/03 Summary

**OdooClient gains async context manager, task-safe with_context ambient RPC injection via ContextVar, and iter_search_read keyset-paginated async generator — all with tests.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-19T10:55:09Z
- **Completed:** 2026-05-19T11:01:37Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- `async with OdooClient(config) as client:` — authenticates on enter, closes transport on exit (CLIENT-01)
- `with client.with_context(lang="fr_FR"):` — all RPC calls in the block carry `{"lang": "fr_FR"}` in kwargs["context"]; nested blocks merge and pop cleanly; concurrent asyncio tasks are isolated via ContextVar (CLIENT-03)
- `async for r in client.iter_search_read("res.partner", batch_size=500):` — keyset pagination via id-cursor, optional limit cap, id field stripped when not requested (CLIENT-02)
- 11 new tests covering all behaviors including concurrent isolation (test_with_context_concurrent_isolation verifies D-06)

## Task Commits

1. **Task 1: __aenter__/__aexit__ and with_context** - `8bab5c5` (feat)
2. **Task 2: iter_search_read keyset pagination** - `ee1c3cc` (feat)
3. **Task 3: Tests for CLIENT-01/02/03** - `21a89bf` (test)

## Files Created/Modified

- `packages/godoo/src/godoo/client.py` — added `contextvars` import, `_ambient_context` ContextVar, `_OdooContextScope` class, `with_context()` method, ambient context injection in `call()`, `iter_search_read()` async generator, `__aenter__`/`__aexit__` lifecycle methods
- `packages/godoo/tests/test_client.py` — added `asyncio`, `json` imports, `_ambient_context` import, `_extract_rpc_kwargs` helper, 11 new test functions

## Decisions Made

- **ContextVar default=None**: ruff B039 prohibits mutable defaults (`{}`). Using `None` with `get() or {}` at call sites is idiomatic and correct.
- **AsyncIterator import in Task 2**: Adding it in Task 1 would cause ruff F401 between commits since `iter_search_read` (the only consumer) is added in Task 2.
- **_extract_rpc_kwargs helper**: The Odoo JSON-RPC transport wraps `execute_kw` call as `params.args = [db, uid, pwd, model, method, args, kwargs]`, not `params.kwargs`. Tests must read `args[6]` to inspect kwargs.
- **id-field internal injection**: Per D-09/Pitfall-4, `id` is always fetched for cursor advancement then stripped from yielded records when not in caller's `fields=` list.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ContextVar mutable default rejected by ruff B039**
- **Found during:** Task 1 verification
- **Issue:** `contextvars.ContextVar("_ambient_context", default={})` violates B039 — mutable default for ContextVar
- **Fix:** Changed default to `None`; all `_ambient_context.get()` call sites use `or {}` to normalize
- **Files modified:** `packages/godoo/src/godoo/client.py`
- **Committed in:** `8bab5c5` (Task 1 commit)

**2. [Rule 1 - Bug] RUF005 list concatenation in iter_search_read**
- **Found during:** Task 2 verification
- **Issue:** `["id"] + list(fields)` and `base_domain + [...]` flagged by ruff RUF005
- **Fix:** Changed to spread syntax: `["id", *list(fields)]` and `[*base_domain, ...]`
- **Files modified:** `packages/godoo/src/godoo/client.py`
- **Committed in:** `ee1c3cc` (Task 2 commit)

**3. [Rule 1 - Bug] Test capture helper used wrong JSON-RPC body path**
- **Found during:** Task 3 test execution
- **Issue:** `body["params"]["kwargs"]` does not exist; the transport puts kwargs at `body["params"]["args"][6]`
- **Fix:** Added `_extract_rpc_kwargs()` helper that reads `params.args[6]`; all body-capture tests use it
- **Files modified:** `packages/godoo/tests/test_client.py`
- **Committed in:** `21a89bf` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs found during linting/test execution)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the three auto-fixed deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CLIENT-01, CLIENT-02, CLIENT-03 complete; `client.py` ready for plan 01-04 (fields_get, ref, execute_kw, read_binary, bulk create, py.typed)
- All existing tests pass with no regressions (172 assertions, 0 failures)
- ruff + mypy --strict green

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. `with_context` passes values verbatim to Odoo (T-03-01 accepted by design); ContextVar isolation verified by concurrent test (T-03-02 mitigated); kwargs immutability enforced (T-03-03 mitigated); iter_search_read termination guaranteed (T-03-04 mitigated).

---
*Phase: 01-client-parity*
*Completed: 2026-05-19*
