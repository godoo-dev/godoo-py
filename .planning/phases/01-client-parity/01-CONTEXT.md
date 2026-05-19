# Phase 1: Client Parity - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the `godoo` async Odoo client's parity gaps against `@godoo/client` and fix
three adjacent transport/service bugs. Phase 1 delivers, on the existing `OdooClient`
surface:

- **CLIENT-01** async context manager (`async with OdooClient(...)`)
- **CLIENT-02** `iter_search_read()` auto-paginated async generator
- **CLIENT-03** `with_context(...)` call modifier
- **CLIENT-04** `fields_get()` field-metadata introspection
- **CLIENT-05** `ref(xml_id)` XML-ID lookup
- **CLIENT-06** `execute_kw()` raw RPC passthrough
- **CLIENT-07** `read_binary()` binary-field fetch
- **CLIENT-08** bulk `create` (list of value dicts)
- **CLIENT-10** `py.typed` PEP 561 marker
- **FIXES-01** `CdcService.get_feed` class-API signature bug
- **FIXES-02** transport timeouts raise `OdooTimeoutError`
- **FIXES-03** configurable request timeout

**12 requirements.** Scope is fixed by REQUIREMENTS.md / ROADMAP.md — discussion
clarified HOW to implement, never WHETHER to add capabilities.

**Removed from scope:** CLIENT-09 (`OAuthProxyClient`) was hard-dropped during this
discussion — see D-01.

</domain>

<decisions>
## Implementation Decisions

### Scope change — CLIENT-09 dropped
- **D-01:** CLIENT-09 (`OAuthProxyClient`, bearer-token transport) was removed from v1
  scope entirely by owner decision — never implemented, not a real parity gap. Struck
  from `SEED.md` §2/§4 (charter amended), `REQUIREMENTS.md` (requirement + traceability
  + coverage 31→30), `ROADMAP.md` (Phase 1 requirements line), and `PROJECT.md` (active
  bullet + Key Decisions row). `CLIENT-10` was intentionally **not** renumbered — the
  ID gap is self-documenting. No source code existed, so nothing in `packages/` changed.

### with_context() — CLIENT-03
- **D-02:** `client.with_context(**ctx)` returns a **context manager** used in a plain
  (sync) `with` block. `__enter__`/`__exit__` only set/clear ambient state; the block
  body still `await`s normally. (Overrode the initially-selected "reusable scoped
  client" option — owner explicitly wanted the Pythonic `with` form.)
- **D-03:** Inside the block, calls go on the **base `client` directly** —
  `client.search_read(...)`, `client.accounting.get_cash_balance(...)`. The ambient
  context applies to the **whole surface** (CRUD helpers AND all 8 services) because
  it is the same client object.
- **D-04:** Nested `with` blocks **merge** their context dicts; each block pops only
  its own layer on exit. The client outside any block is never polluted.
- **D-05:** An explicit per-call `context=` kwarg **merges over** the ambient context —
  explicit keys win for that call; other ambient keys still apply.
- **D-06:** The ambient-context mechanism is a **research item**. `contextvars.ContextVar`
  is the leading direction (task-local — concurrent `asyncio` tasks sharing one client
  do not clobber each other; `with` nesting still works). Researcher should confirm or
  surface a better option. A plain instance attribute is **rejected** — unsafe under
  concurrency.

### Bulk create — CLIENT-08
- **D-07:** Single `create` method typed with `@typing.overload` —
  `create(model, dict) -> int` and `create(model, list[dict]) -> list[int]`. mypy infers
  the exact return per call site; no runtime `int | list[int]` union leaks to callers.
  Wire side needs no change: `args=[values]` already passes a dict or a list straight to
  Odoo's `create` (which returns an int for a dict, a list for a list).
- **D-08:** `create(model, [])` (empty list) raises `OdooValidationError` **locally**,
  before any RPC — consistent with the existing local-precondition-validation
  convention (e.g. `log_time` validates hours > 0).

### iter_search_read — CLIENT-02
- **D-09:** **Id-cursor (keyset) pagination** — each batch adds `('id', '>', last_id)`
  to the domain, orders by `id`, `limit=batch_size`. Robust against concurrent
  inserts/deletes mid-iteration; avoids deep-offset DB cost. (Offset paging rejected.)
- **D-10:** **No custom `order` parameter** — iteration is always `id` ascending
  (keyset requires a deterministic key).
- **D-11:** `batch_size` parameter, **default 500**, caller-overridable.
- **D-12:** Optional total **`limit`** parameter — caps the number of records yielded,
  separate from `batch_size`.
- **D-13:** Yields **individual records** (`AsyncIterator[dict[str, Any]]`), not
  batches — fixed by ROADMAP success criterion 2 (`async for record in ...`).

### Remaining requirements — recorded defaults (accepted, not separately discussed)
- **D-14:** CLIENT-01 `async with OdooClient(...)` — `__aenter__` calls `authenticate()`
  and returns `self`; `__aexit__` calls `aclose()`.
- **D-15:** CLIENT-04 `fields_get()` — returns the raw `dict[str, Any]` keyed by field
  name (Odoo's native `fields_get` shape). Typed field-metadata representations are
  Phase 2 (introspection) territory; not duplicated on the client.
- **D-16:** CLIENT-05 `ref(xml_id)` — returns the numeric `res_id` as `int`; raises
  `OdooMissingError` when the xml_id does not resolve.
- **D-17:** CLIENT-06 `execute_kw()` — raw passthrough for non-standard methods, routed
  through `OdooClient.call()` so the safety guard still classifies and gates it.
- **D-18:** CLIENT-07 `read_binary()` — returns decoded **`bytes`** (decodes the base64
  Odoo returns for binary fields), not the raw base64 `str`.
- **D-19:** CLIENT-10 `py.typed` — mechanical PEP 561 marker file in the `godoo` package.
- **D-20:** FIXES-03 — request timeout as a single `timeout: float | None` field on
  `OdooClientConfig`, threaded to `httpx.AsyncClient(timeout=...)`. httpx's granular
  `Timeout` object is **not** exposed in v1.
- **D-21:** FIXES-01 — `CdcService.get_feed` fixed per `CONCERNS.md`: the class-API
  method must return a directly-usable async iterator (not an un-awaited generator or a
  coroutine). Mechanical.
- **D-22:** FIXES-02 — transport catches `httpx.TimeoutException` **before** the generic
  `httpx.RequestError` handler and raises `OdooTimeoutError`. Mechanical, per `CONCERNS.md`.

### Claude's Discretion
- The exact fix shape for D-21/D-22 follows the `CONCERNS.md` fix approaches verbatim.
- Un-specified ergonomics (parameter names, docstring wording, helper placement) are at
  planner/executor discretion, consistent with existing `godoo` conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Charter & requirements
- `SEED.md` §2 — defines the client parity gaps. `../godoo-ts/` ships **no package
  source**, so this bullet list (not a reference implementation) IS the parity spec.
  Amended 2026-05-19: `OAuthProxyClient` struck from §2 and §4.
- `.planning/REQUIREMENTS.md` — CLIENT-01–08, CLIENT-10, FIXES-01/02/03 requirement
  text + traceability table.
- `.planning/ROADMAP.md` — Phase 1 goal and 5 success criteria.

### Codebase (the fix recipes live here)
- `.planning/codebase/CONCERNS.md` — **exact fix approaches** for FIXES-01 (§Known
  Bugs — `get_feed` signature mismatch), FIXES-02 (§Tech Debt — `OdooTimeoutError`
  never raised), FIXES-03 (§Missing Critical Features — no request timeout); also the
  async-context-manager gap. MUST read for the fix recipes.
- `.planning/codebase/ARCHITECTURE.md` — layer model, `call()` chokepoint, service
  pattern, anti-patterns.
- `.planning/codebase/CONVENTIONS.md` — naming, typing, module conventions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`OdooClient`** (`packages/godoo/src/godoo/client.py`) — CRUD helpers (`search`,
  `read`, `search_read`, `create`, `write`, `unlink`, …), the `call()` chokepoint,
  `_guard()` safety, lazy `@cached_property` service registry. All new client methods
  (`fields_get`, `ref`, `execute_kw`, `read_binary`, bulk `create`, `iter_search_read`,
  `with_context`, `__aenter__`/`__aexit__`) attach **here** — they are core client
  surface, not a new domain-service quad.
- **`JsonRpcTransport`** (`packages/godoo/src/godoo/rpc/transport.py`) — `httpx`
  wire layer; `call()`/`call_rpc()`; `_categorize_error()`. FIXES-02 and FIXES-03 land
  here. `httpx.AsyncClient()` is currently constructed with **no `timeout=` arg**.
- **Error hierarchy** (`packages/godoo/src/godoo/errors.py`) — `OdooTimeoutError`,
  `OdooMissingError`, `OdooValidationError` already exist; reuse them, do not add new
  types.
- **`CdcService`** (`packages/godoo/src/godoo/services/cdc/service.py:38-39`) —
  FIXES-01 target.

### Established Patterns
- `call()` is the single chokepoint: `infer_safety_level` → `_guard` →
  `transport.call`. `execute_kw`, bulk `create`, and `iter_search_read` all route
  through it so safety + auth checks stay uniform.
- CRUD helpers `cast()` the JSON-RPC `Any` return to a typed result; `@typing.overload`
  for bulk `create` extends this typing discipline.
- `args=[values]` in `create` already passes a dict OR a list straight to Odoo — bulk
  `create` needs only signature/return typing, no wire changes.
- Local precondition validation raises `OdooValidationError` before the RPC — the
  empty-list bulk-create guard (D-08) follows this.

### Integration Points
- `OdooClientConfig` dataclass gains a `timeout` field (D-20).
- `with_context` ambient state must be visible to `OdooClient.call()` AND every
  service. Because services call back through `client.call()` / `client.search_read()`,
  threading the context at the `call()` layer covers all 8 services automatically.

</code_context>

<specifics>
## Specific Ideas

- Owner's exact framing for `with_context`, typed verbatim during discussion:
  *"I think `with_context` should be a Python context: `with client.with_context(lang='fr'):
  client.search(...)` — much more Pythonic."* This overrode the initially-selected
  "reusable scoped client" option; the `with`-block form (D-02) is the locked design.
- `@typing.overload` was explicitly chosen for bulk `create` to keep strict-mypy call
  sites clean — no `int | list[int]` union leaking to callers.

</specifics>

<deferred>
## Deferred Ideas

- **None new** from this discussion — it stayed within phase scope.
- CLIENT-09 (`OAuthProxyClient`) is **not deferred** — it was hard-dropped (removed
  from all planning docs), not parked for a later milestone.
- Pre-existing deferrals remain on record in `REQUIREMENTS.md` (v2 section) and
  `STATE.md` Deferred Items: COMPAT-01 (Python floor), CLIENT-V2-01 (auto re-auth),
  PERF-01/02.

</deferred>

---

*Phase: 1-Client Parity*
*Context gathered: 2026-05-19*
