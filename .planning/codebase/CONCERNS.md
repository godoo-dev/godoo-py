# Codebase Concerns

**Analysis Date:** 2026-05-18

## Tech Debt

**Misleading multi-exception `except` syntax in `seed_resolver.py`:**
- Issue: Line 35 reads `except FileNotFoundError, json.JSONDecodeError:` — this looks like Python 2's `except E, varname:` syntax but Python 3.14 parses the attribute expression `json.JSONDecodeError` as a tuple, making it functionally equivalent to `except (FileNotFoundError, json.JSONDecodeError):`. The code is accidentally correct but will confuse any reader or linter and may break under future parser changes.
- Files: `packages/godoo-testcontainers/src/godoo_testcontainers/seed_resolver.py:35`
- Impact: Misleading — maintainers will read it as broken, static analysis tools may flag it, and any refactor risk accidentally silencing only one exception.
- Fix approach: Replace with `except (FileNotFoundError, json.JSONDecodeError):`.

**`OdooTimeoutError` is defined but never raised:**
- Issue: `OdooTimeoutError` is a public error class exported at the top level (`godoo/__init__.py`), but `transport.py` only catches `httpx.RequestError` (which includes timeouts) and re-raises everything as `OdooNetworkError`. `httpx.TimeoutException` is never caught and converted to `OdooTimeoutError`.
- Files: `packages/godoo/src/godoo/errors.py:73`, `packages/godoo/src/godoo/rpc/transport.py:81-87`
- Impact: Users who import and catch `OdooTimeoutError` will never receive it; timeout conditions silently land as `OdooNetworkError`.
- Fix approach: In `transport.py`, add `except httpx.TimeoutException` before the generic `RequestError` handler and raise `OdooTimeoutError`.

**`startup_timeout` parameter is stored but never used:**
- Issue: `OdooTestContainer.__init__` accepts `startup_timeout: int = 300` and stores it as `self._startup_timeout`, but `_wait_for_odoo_ready` hardcodes `max_attempts=120` (240 seconds at 2s sleep). The stored value is never consulted.
- Files: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:51,57,168`
- Impact: Users who pass `startup_timeout=600` for slow environments get no effect. The parameter is a silent no-op.
- Fix approach: Derive `max_attempts` from `self._startup_timeout // 2` in the call to `_wait_for_odoo_ready`.

**`FieldMeta.selection` field is defined but never populated:**
- Issue: `FieldMeta` dataclass has a `selection: list[tuple[str, str]] | None = None` field. `fetch_field_meta` requests `selection_ids` from `ir.model.fields` but never maps the result into `FieldMeta.selection`. `ensure_fields_cached` does not request `selection_ids` at all. The field sits unused.
- Files: `packages/godoo/src/godoo/services/cdc/types.py:14`, `packages/godoo/src/godoo/services/cdc/field_cache.py:44,78`
- Impact: Selection field display values (`old_value_char`/`new_value_char`) are used as-is rather than resolved to human-readable labels. CDC events for `selection` type fields show raw stored keys (e.g. `"draft"`) which may differ from display labels in some Odoo configurations.
- Fix approach: Either remove `selection` from `FieldMeta` and the `selection_ids` fetch if resolution is not planned, or implement the mapping.

**`assert` used for runtime control flow in `config.py`:**
- Issue: After `missing` list validation, four `assert ... is not None` statements are used to inform the type checker. These work correctly at runtime but are removed under `-O` (optimize flag) and are not idiomatic — a plain `cast()` or `# type: ignore` would be more appropriate.
- Files: `packages/godoo/src/godoo/config.py:44-47`
- Impact: Low — only matters if the package is deployed with Python `-O`, but is a minor anti-pattern.
- Fix approach: Replace `assert` statements with `cast(str, url)` etc., or use explicit narrowing.

**`_UNDEFINED` sentinel typed as `Any` in `client.py`:**
- Issue: `self._safety_context: Any = _UNDEFINED` uses `Any` to allow a sentinel/None/SafetyContext union. The `_effective_safety` method has a redundant double-check: `if self._safety_context is not _UNDEFINED else None` is unreachable because the outer `if` already tests for `_UNDEFINED`.
- Files: `packages/godoo/src/godoo/client.py:54,76-82`
- Impact: The redundant branch is dead code; the `Any` annotation defeats strict mypy checking for that attribute.
- Fix approach: Use a typed sentinel pattern (`_Sentinel = object()`) with a `Union` annotation, or simplify `_effective_safety` to remove the dead branch.

**Static JSON-RPC request `id` is always `1`:**
- Issue: Every JSON-RPC call in `transport.py` uses `"id": 1` (line 71) regardless of concurrent calls. Odoo's JSON-RPC implementation is stateless and ignores the `id` in practice, but the spec requires unique IDs per request. This could cause confusion if response matching is ever added.
- Files: `packages/godoo/src/godoo/rpc/transport.py:71`
- Impact: Low for current usage (synchronous request-response cycle, no multiplexing), but non-compliant with the JSON-RPC spec.
- Fix approach: Use `uuid.uuid4()` or an incrementing counter per-transport instance.

---

## Known Bugs

**`CdcService.get_feed` signature mismatch:**
- Symptoms: `CdcService.get_feed` is declared `async def get_feed(self, ...) -> AsyncIterator[...]` but the body is `return get_feed(self._client, options)` — a non-awaited call to the generator function. Callers doing `async for event in await svc.get_feed(opts)` will receive the async generator directly without awaiting. Callers doing `async for event in svc.get_feed(opts)` will get a coroutine, not an iterator.
- Files: `packages/godoo/src/godoo/services/cdc/service.py:38-39`
- Trigger: Any use of `CdcService.get_feed` from the service class (rather than the standalone function).
- Workaround: Use `godoo.services.cdc.get_feed(client, options)` directly.

---

## Security Considerations

**Credentials stored as instance attribute in plaintext:**
- Risk: `JsonRpcTransport` stores the password as `self._password` after authentication. It remains live in memory for the lifetime of the transport instance and is passed in plaintext JSON on every `execute_kw` call (per the Odoo JSON-RPC protocol design). There is no session-cookie alternative implemented.
- Files: `packages/godoo/src/godoo/rpc/transport.py:31,63,119`
- Current mitigation: Standard Odoo JSON-RPC — this is protocol-mandated; password is not logged.
- Recommendations: Document this clearly in the public API. Consider a `__repr__`/`__str__` override on `OdooClientConfig` that masks the password field.

**No TLS certificate verification configuration:**
- Risk: `httpx.AsyncClient()` is created with default settings (TLS verification on). There is no provision to configure SSL verification or custom CA bundles via `OdooClientConfig`. Users with self-signed certs may monkey-patch or bypass SSL entirely.
- Files: `packages/godoo/src/godoo/rpc/transport.py:30`
- Current mitigation: httpx defaults to verifying TLS; not a current hole.
- Recommendations: Add optional `verify: bool | str = True` to `OdooClientConfig` and pass it to `httpx.AsyncClient(verify=...)`.

---

## Performance Bottlenecks

**`update_safely_batch` uses `asyncio.gather` — concurrent read-merge-write races:**
- Problem: `update_safely_batch` fires N concurrent `update_safely` calls via `asyncio.gather`. Each `update_safely` does read → merge → write. For concurrent records this is safe, but if the same `record_id` appears twice (possible via caller error), or if other writers act between read and write, the last writer wins silently.
- Files: `packages/godoo/src/godoo/services/properties/functions.py:45-53`
- Cause: No locking or optimistic concurrency check exists.
- Improvement path: Document the race condition. For single-record repeated calls, sequential execution is safer. Consider accepting `asyncio.gather` only for distinct IDs.

**CDC `get_feed` without `res_ids` builds a secondary message lookup per batch:**
- Problem: When `GetFeedOptions.res_ids is None`, `get_feed` fetches all tracking rows above `cursor`, then builds a `msg_map` by reading `mail.message` for all encountered message IDs in a second round-trip. For high-throughput feeds, this doubles the RPC calls per batch.
- Files: `packages/godoo/src/godoo/services/cdc/functions.py:157-188`
- Cause: `mail.tracking.value` does not carry message metadata; a join requires a second query.
- Improvement path: The design is correct for Odoo's data model. Document the two-round-trip behaviour in the docstring and let callers set a smaller `batch_size` when latency matters.

**`get_cash_balance` fetches all posted journal lines without pagination:**
- Problem: `get_cash_balance` calls `search_read("account.move.line", ...)` with no `limit`, then sums in Python. For a journal with years of history this returns thousands of records.
- Files: `packages/godoo/src/godoo/services/accounting/functions.py:263-276`
- Cause: Balance calculation is done client-side instead of using `read_group` with SUM aggregation.
- Improvement path: Replace with a `read_group` call: `client.call("account.move.line", "read_group", domain, fields=["debit:sum","credit:sum"], groupby=[])`.

---

## Fragile Areas

**`godoo-introspection` is an empty placeholder:**
- Files: `packages/godoo-introspection/src/godoo_introspection/__init__.py`
- Why fragile: The package has a `pyproject.toml` with `Development Status :: 2 - Pre-Alpha` and is released via semantic-release alongside the other packages (see `pyproject.toml` root `build_command`). Any release will publish an empty package with the same version.
- Safe modification: Implement or remove from the release pipeline until ready.
- Test coverage: Zero — nothing to test.

**`OdooTestContainer` module install retry is unconditional:**
- Files: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:147-152`
- Why fragile: After a failed `install_module`, the code unconditionally waits for Odoo to come back and retries exactly once. If the failure is not due to a server restart (e.g., wrong module name, missing dependency), the retry also fails and raises a generic exception with no indication of why the original install failed.
- Safe modification: Check the exception type before deciding to retry; only retry on connection errors, not on `RuntimeError` (module not found) or `OdooValidationError`.
- Test coverage: The single retry path has no unit test.

**CDC `get_feed` model-filtering logic is comment-dependent:**
- Files: `packages/godoo/src/godoo/services/cdc/functions.py:202-204`
- Why fragile: The filter `if options.res_ids is None and msg.get("model") and msg["model"] != options.model` silently skips cross-model tracking events and only advances `cursor` without yielding. If `msg_map` is empty (message not found), `msg` is `{}`, so `msg.get("model")` is falsy, and the event is yielded regardless of model. This is a latent correctness issue: cross-model events may leak through when messages cannot be resolved.
- Safe modification: Add an explicit test for this boundary in `test_cdc.py`.
- Test coverage: `get_feed` has zero unit tests.

---

## Scaling Limits

**Python 3.14 minimum version reduces adoption surface:**
- Current capacity: Requires Python 3.14+ (declared in all `pyproject.toml` files and `ruff target-version = "py314"`).
- Limit: Python 3.14 was released in late 2025; as of mid-2026 many production environments still run 3.11 or 3.12. This is the single biggest adoption barrier for the library.
- Scaling path: Audit which 3.14-specific features are actually used. If the codebase uses only features from 3.11+, relaxing to `>=3.11` would significantly widen compatibility.

---

## Dependencies at Risk

**`testcontainers-python` has a synchronous API:**
- Risk: The `testcontainers` library exposes only sync methods (`.start()`, `wait_for_logs()`). All calls must be wrapped in `asyncio.to_thread()`. This creates an architectural coupling where any future `testcontainers` API change (or a switch to a different container library) requires updating all call sites.
- Impact: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` — all container lifecycle calls.
- Migration plan: If an async-native container library becomes available, or if `testcontainers` adds async support, a thin adapter layer in `container.py` would contain the migration.

---

## Missing Critical Features

**No retry/reconnect logic for authentication expiry:**
- Problem: `OdooClient` authenticates once and holds the session. Odoo sessions expire (default 7 days but configurable) and the server can be restarted. There is no automatic re-authentication on `OdooAuthError` mid-operation.
- Blocks: Long-running applications (daemons, batch processors) that hold a client for hours cannot recover from session expiry without restarting.

**No async context manager (`async with`) support on `OdooClient`:**
- Problem: `OdooClient` requires manual calls to `await client.authenticate()` and `await client.aclose()`. There is no `__aenter__`/`__aexit__` implementation, so it cannot be used in `async with` blocks.
- Blocks: Clean resource management patterns; the transport's httpx client leaks if `aclose()` is not called.

**No built-in request timeout configuration:**
- Problem: `httpx.AsyncClient()` is created without a `timeout` parameter, so it uses httpx's default (5 seconds for connect, no read timeout). Long-running Odoo operations (module install, heavy reports) will hang or fail unpredictably.
- Files: `packages/godoo/src/godoo/rpc/transport.py:30`
- Blocks: Reliable use against slow or loaded Odoo instances.

---

## Test Coverage Gaps

**`CdcService.get_feed` — zero unit tests:**
- What's not tested: The entire async-generator pagination logic, model filtering, msg_map construction, and cursor advancement in `get_feed`.
- Files: `packages/godoo/src/godoo/services/cdc/functions.py:128-222`
- Risk: The known correctness issue (cross-model event leakage when msg not found) goes undetected; cursor advancement bugs are invisible.
- Priority: High

**`CdcService.get_history` — zero unit tests:**
- What's not tested: The two-step message + tracking-value fetch, `ensure_fields_cached` integration, author resolution, and `msg_id` normalisation.
- Files: `packages/godoo/src/godoo/services/cdc/functions.py:58-125`
- Risk: Field-type resolution bugs or author extraction regressions go unnoticed.
- Priority: High

**Accounting: `trace_reconciliation`, `calculate_days_to_pay`, `get_cash_balance`, `get_posted_move_lines`, `is_closing_entry` — zero unit tests:**
- What's not tested: All async accounting functions except `discover_cash_accounts`.
- Files: `packages/godoo/src/godoo/services/accounting/functions.py:78-297`
- Risk: Financial logic bugs (e.g. balance sum, days calculation) go undetected.
- Priority: High

**Attendance: `clock_out`, `list_attendances` — no unit tests:**
- What's not tested: Clock-out write path, `check_out` detection on `AttendanceRecord`.
- Files: `packages/godoo/src/godoo/services/attendance/functions.py:76-126`
- Risk: Regression in clock-out logic undetected without integration tests.
- Priority: Medium

**Timesheets: `start_timer`, `get_running_timers`, `list_timesheets` — no unit tests:**
- What's not tested: Timer creation round-trip, zero-amount filtering for running timers.
- Files: `packages/godoo/src/godoo/services/timesheets/functions.py:33-134`
- Risk: Timer lifecycle bugs only caught by integration tests (slow, Docker-dependent).
- Priority: Medium

**`OdooTestContainer.start` container lifecycle — no unit tests:**
- What's not tested: The `start` method logic (seed vs cold start path, module install loop, cleanup on failure).
- Files: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:60-166`
- Risk: Silent regressions in test infrastructure break all integration tests without clear cause.
- Priority: Medium

---

*Concerns audit: 2026-05-18*
