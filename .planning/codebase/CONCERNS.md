# Codebase Concerns

**Analysis Date:** 2026-04-10

## Tech Debt

**Introspection package is placeholder-only:**
- Issue: `godoo-introspection` package has only an empty `__init__.py` file with no implementation
- Files: `packages/godoo-introspection/src/godoo_introspection/__init__.py`
- Classfication: Pre-Alpha (per pyproject.toml)
- Impact: Package ships with zero functionality; imports will succeed but provide nothing. Any dependent code calling introspection APIs will fail at runtime. Documentation or users expecting schema discovery/codegen will be blocked.
- Fix approach: Either remove from workspace if not ready, or implement core schema discovery (model fields, field types, field constraints). At minimum, provide stubs that raise NotImplementedError with helpful error messages.

**Release pipeline instability:**
- Issue: Recent releases show version cycling from 0.1.0 → 1.0.0 → 1.0.1 → 0.1.1; semantic-release was incrementing major version on 0.x initial versions because `allow_zero_version = true` was missing from config
- Files: `pyproject.toml` (root), `.github/workflows/release.yml`
- History: Commits e78d383, 844f265, 1ae8818 — all release fixes
- Impact: PyPI will have multiple versions (1.0.0, 1.0.1 in addition to 0.1.0, 0.1.1); users installing via `pip install godoo` may get an unintended major version. Tags on GitHub are inconsistent. Recovery required: tag management and possible PyPI yanking.
- Fix approach: `allow_zero_version = true` is now set (commit 844f265); validate next release succeeds and stays at 0.2.0. Monitor semantic-release behavior for one release cycle.

**Password stored in transport state:**
- Issue: `JsonRpcTransport._password` holds plaintext password in memory after authentication (line 63 of `rpc/transport.py`)
- Files: `packages/godoo/src/godoo/rpc/transport.py:32,63,114,126`
- Impact: Password persists in memory longer than necessary; can be exposed via memory dumps, debuggers, or exceptions. Currently only cleared by explicit `logout()` call, not on error.
- Fix approach: Either (1) document that callers must call `logout()` to clear credentials, (2) implement `__del__` or context manager to auto-clear on GC, (3) drop password storage entirely if reauthentication is handled server-side via session ID (OdooSessionInfo.session_id already exists).

**httpx.AsyncClient lifecycle not enforced:**
- Issue: `JsonRpcTransport._client` (httpx.AsyncClient) must be closed via `aclose()` (line 130) but no context manager or `__aenter__/__aexit__` implemented
- Files: `packages/godoo/src/godoo/rpc/transport.py:30,128-130`
- Impact: Users who don't explicitly call `client.aclose()` will leak TCP connections. Long-running services may exhaust connection pool.
- Fix approach: Add `async with OdooClient(...) as client:` support via `__aenter__/__aexit__` delegation to transport. Alternatively, warn in docstrings and require explicit cleanup. Consider adding a finalizer warning if aclose is not called before GC.

## Performance Bottlenecks

**Accounting service function is large and complex:**
- Problem: `services/accounting/functions.py` is 297 lines with nested loops and multiple Odoo RPC calls
- Files: `packages/godoo/src/godoo/services/accounting/functions.py`
- Cause: Converts nested account.move, account.move.line structures; multiple search_read calls in sequence without batching
- Improvement path: Profile hot paths; batch RPC calls where possible. Consider caching field definitions across batch operations. Break into smaller helper functions for testability.

**CDC service resolver makes sequential RPC calls:**
- Problem: `services/cdc/functions.py` calls search_read → resolve_values → field resolution, each potentially hitting Odoo separately
- Files: `packages/godoo/src/godoo/services/cdc/functions.py`, `services/cdc/resolver.py`, `services/cdc/field_cache.py`
- Cause: Field caching exists (`field_cache.py`) but may not be shared across multiple `get_history()` calls on the same table
- Improvement path: Pre-fetch all tracked field definitions in `check()` and cache at client level. Implement field metadata TTL cache to avoid redundant calls in bulk operations.

**Testcontainers wrapping every call in asyncio.to_thread:**
- Problem: All testcontainers-python API calls wrapped via `asyncio.to_thread()` (9 instances in `container.py`)
- Files: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:38,41,65,77,78,91,112,123,165`
- Cause: testcontainers-python API is synchronous; necessary but adds thread pool overhead per call
- Improvement path: Batch-wrap container operations where possible (e.g., start pg + odoo in parallel). Consider using thread pool executor with pre-warmed threads if startup is called frequently.

## Fragile Areas

**Circular import prevention via TYPE_CHECKING is pervasive:**
- Files affected: `packages/godoo/src/godoo/client.py`, `config.py`, `services/*/service.py` (all)
- Why fragile: All service classes guard imports with `if TYPE_CHECKING:` to avoid cycles (lines 19-27 in client.py, similar in config.py). Lazy imports in cached_property methods compensate (lines 195-239 in client.py). Risk: If a service accidentally imports OdooClient at module level, will silently break at runtime despite type checking passing.
- Safe modification: When adding new services, use identical pattern: (1) TYPE_CHECKING import for type hints, (2) lazy import inside cached_property. Verify with `python -c "from godoo import OdooClient"` before committing.
- Test coverage: Test import patterns exist (`test_client.py`) but don't explicitly test circular import scenarios.

**Error categorization is order-dependent:**
- Files: `packages/godoo/src/godoo/rpc/transport.py:136-164`
- Why fragile: `_categorize_error()` checks `exception_type` first, then falls back to `data.name`; Odoo's RPC error responses vary by version/module. If Odoo adds a new exception type but the categorizer doesn't recognize it, falls through to generic OdooRpcError. Subsequent code may assume specific error subclass and fail.
- Safe modification: Before adding new exception types, verify against actual Odoo error responses. Add tests for each categorization path.

**Transport doesn't validate session state across calls:**
- Files: `packages/godoo/src/godoo/rpc/transport.py:104-105`
- Why fragile: `call()` checks `if self._session is None` but doesn't check if session has expired server-side. Server could reject the call with AccessDenied, which gets categorized to OdooAuthError, but transport doesn't clear `_session`. Caller may retry assuming auth failed, when in fact session expired.
- Safe modification: Catch OdooAuthError on the session-validity path and auto-clear session. Document this in docstrings.

## Known Bugs

**Release system forced package versioning to 1.0.0:**
- Symptoms: Multiple versions of godoo appear on PyPI (0.1.0, 0.1.1, 1.0.0, 1.0.1)
- Files: `pyproject.toml` root, `.github/workflows/release.yml`
- Trigger: `semantic-release` v9+ defaults `allow_zero_version = false`, so any pre-1.0 release gets bumped to 1.0.0. Initial release at commit d52890d likely triggered this.
- Workaround: Reinstall from pyproject.toml version spec; or pin to `godoo>=0.1.0,<1.0.0` if 1.0.x versions are unstable
- Status: Fixed in commit 844f265 by adding `allow_zero_version = true`; subsequent releases should stay in 0.x

**Module manager retry logic may infinite-loop on ir_cron errors:**
- Symptoms: `install_module()` retries indefinitely if Odoo returns ir_cron/scheduled action error; no max attempt limit enforced
- Files: `packages/godoo/src/godoo/services/modules/module_manager.py:72,83,96` (calls `_call_with_ir_cron_retry`)
- Trigger: Module installation conflicts with scheduled actions (e.g., ir.cron jobs acquiring locks)
- Workaround: Callers can wrap in their own timeout; testcontainers already uses max_attempts=60 (line 150 in container.py)
- Status: Acceptable for testcontainers but should be documented in ModuleManager docstring; consider adding configurable max_retries to constructor (already exists at line 31 but _MAX_RETRIES is hardcoded)

## Security Considerations

**Plaintext password in memory and logs:**
- Risk: Passwords passed to `authenticate()` are stored in `_password` field; they also appear in debug logs if logger level set to DEBUG
- Files: `packages/godoo/src/godoo/rpc/transport.py:49,63,74` (logging at 74 logs method name but not params; safe)
- Current mitigation: Logger statement is safe (line 74 doesn't log params). Password is not serialized in error messages.
- Recommendations: (1) Add to docstring that callers should never log OdooClientConfig; (2) implement `__repr__` on OdooClientConfig to mask password; (3) clear password immediately after successful auth if server-side session suffices for re-auth

**No HTTPS enforcement:**
- Risk: OdooClient accepts any `url` (http or https); nothing prevents connecting to plain HTTP Odoo instances that would send credentials in plaintext
- Files: `packages/godoo/src/godoo/client.py:36-40` (OdooClientConfig just stores url string)
- Current mitigation: None at library level; responsibility on caller
- Recommendations: (1) Document requirement to always use HTTPS in production; (2) optionally add validation mode that rejects http:// URLs except localhost; (3) add warning log if http://hostname (not localhost) is detected

**Session ID is UUID, not server-issued:**
- Risk: `OdooSessionInfo.session_id` is generated client-side as `str(uuid.uuid4())` (line 62 in transport.py); server doesn't validate this token, only checks uid + db
- Files: `packages/godoo/src/godoo/rpc/transport.py:62`
- Current mitigation: Odoo's JSON-RPC doesn't use session tokens; authentication is implicit per uid+database. Client-side session_id is cosmetic.
- Recommendations: Document that session_id is not a security token. Consider using server-issued session identifiers if Odoo supports them in future (would require checking Odoo RPC API).

## Scaling Limits

**CBC field cache has no TTL or eviction:**
- Current capacity: Entire `ir.model.fields` table for a model cached in memory per OdooClient instance
- Limit: If Odoo database has thousands of field definitions, memory grows unbounded; no cache invalidation on field schema changes
- Files: `packages/godoo/src/godoo/services/cdc/field_cache.py`
- Scaling path: Add optional TTL parameter to cache; implement LRU eviction if memory threshold exceeded; provide manual `clear_cache()` method

**Transport maintains single httpx.AsyncClient per instance:**
- Current capacity: httpx default connection pool is 10 concurrent connections
- Limit: High-concurrency scenarios (100+ concurrent operations) may exceed pool size and timeout
- Files: `packages/godoo/src/godoo/rpc/transport.py:30`
- Scaling path: Make pool_limits configurable via OdooClientConfig (httpx.AsyncClient(limits=...)); or allow passing custom AsyncClient at init time

**Module manager retry loop doesn't respect server load:**
- Current: Fixed 5-second delay between retries; no backoff
- Limit: High-concurrency module installs across multiple clients may hammer Odoo with rapid retry bursts
- Files: `packages/godoo/src/godoo/services/modules/module_manager.py:52,54`
- Scaling path: Add exponential backoff option; respect Retry-After headers if Odoo implements them

## Dependencies at Risk

**Semantic-release v9 configuration fragility:**
- Risk: Configuration is complex; `allow_zero_version`, `major_on_zero`, `commit_parser_options` must all align. One misconfiguration breaks version numbering (as happened).
- Files: `pyproject.toml` root (lines 55-81)
- Impact: Prevents reliable 0.x releases; difficult to debug when CI pipeline fails
- Migration plan: Lock semantic-release to v9.x; document required config for 0.x projects. Consider post-release validation (e.g., check that version bumped as expected)

**httpx dependency (single version specifier):**
- Risk: `httpx>=0.27` in pyproject.toml; no upper bound. Major updates could introduce breaking changes.
- Files: `packages/godoo/pyproject.toml:7`
- Impact: Transitive dependency updates in CI could break builds without explicit user action
- Migration plan: Pin to `httpx>=0.27,<1.0` or `httpx~=0.27`; review compatibility when httpx 1.0 ships

**testcontainers-python SYNC API in ASYNC codebase:**
- Risk: testcontainers-python has no async API; all calls must wrap in `asyncio.to_thread()`. Library updates could change API signature.
- Files: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` (9 usages)
- Impact: testcontainers updates may require code changes even for minor version updates
- Migration plan: Monitor testcontainers-python for async support; or implement thin async wrapper if library is actively maintained. Document that testcontainers is test-infrastructure-only and not pinned in root pyproject.toml.

## Test Coverage Gaps

**Introspection package has no tests:**
- What's not tested: Entire godoo-introspection package (schema discovery, codegen)
- Files: `packages/godoo-introspection/` — no tests/ directory
- Risk: Package ships with empty implementation; no test would catch it
- Priority: High — before first real feature is added, add test structure

**Release pipeline not tested end-to-end:**
- What's not tested: Actual PyPI publish step; version bumping; tag creation
- Files: `.github/workflows/release.yml` — no validation of output artifacts
- Risk: Another version cycling bug could slip through
- Priority: Medium — add post-release smoke test (e.g., `pip install --upgrade godoo` and verify version matches tag)

**Error categorization missing edge cases:**
- What's not tested: Odoo errors with unusual name formats, missing exception_type, mixed exception types
- Files: `packages/godoo/src/godoo/rpc/transport.py:136-164`, `tests/test_transport.py`
- Risk: Unrecognized errors fall through to OdooRpcError; calling code may mishandle
- Priority: Low-Medium — add parametrized tests for each categorization path + a few edge cases

**Auth failure scenarios:**
- What's not tested: Connection errors during auth; server returns uid=0 vs False vs null; refresh/re-auth flows
- Files: `tests/test_transport.py` covers some; integration tests cover others but require Docker
- Risk: Edge cases in production (transient network errors, session expiration) may not be handled gracefully
- Priority: Medium — add parametrized tests for each auth failure case

**Safety guard doesn't have comprehensive negative tests:**
- What's not tested: Malformed OperationInfo; safety context returns None; concurrent safety updates
- Files: `tests/test_safety.py`, `tests/test_client.py`
- Risk: Safety logic could silently fail open (allow all) or closed (deny all) on edge cases
- Priority: Medium — add tests for concurrent set_safety_context + call; test with None context

---

*Concerns audit: 2026-04-10*
