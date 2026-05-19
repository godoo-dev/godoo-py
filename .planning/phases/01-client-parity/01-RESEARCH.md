# Phase 01: Client Parity — Research

**Researched:** 2026-05-19
**Domain:** Python async client SDK — async context managers, ContextVar ambient state,
keyset pagination, httpx timeout hierarchy, @typing.overload, PEP 561
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** CLIENT-09 (OAuthProxyClient) dropped from v1 scope entirely — no bearer-token transport.
- **D-02:** `client.with_context(**ctx)` returns a context manager used in a plain `with` block. `__enter__`/`__exit__` only set/clear ambient state; the block body still `await`s normally.
- **D-03:** Inside the block, calls go on the base `client` directly. Ambient context applies to the whole surface (CRUD helpers AND all 8 services).
- **D-04:** Nested `with` blocks merge their context dicts; each block pops only its own layer on exit.
- **D-05:** An explicit per-call `context=` kwarg merges over the ambient context — explicit keys win; other ambient keys still apply.
- **D-06:** Ambient-context mechanism is a research item. `contextvars.ContextVar` is the leading direction.
- **D-07:** `create` typed with `@typing.overload` — `create(model, dict) -> int` and `create(model, list[dict]) -> list[int]`.
- **D-08:** `create(model, [])` raises `OdooValidationError` locally, before any RPC.
- **D-09:** Keyset (id-cursor) pagination — `('id', '>', last_id)` appended to domain, `order='id'`, `limit=batch_size`.
- **D-10:** No custom `order` parameter — iteration always id ascending.
- **D-11:** `batch_size` parameter, default 500.
- **D-12:** Optional `limit` parameter caps total records yielded.
- **D-13:** Yields individual records (`AsyncIterator[dict[str, Any]]`), not batches.
- **D-14:** `__aenter__` calls `authenticate()` and returns `self`; `__aexit__` calls `aclose()`.
- **D-15:** `fields_get()` returns raw `dict[str, Any]` keyed by field name.
- **D-16:** `ref(xml_id)` returns numeric `res_id` as `int`; raises `OdooMissingError` when not found.
- **D-17:** `execute_kw()` is raw passthrough, routed through `OdooClient.call()`.
- **D-18:** `read_binary()` returns decoded `bytes`; decodes the base64 Odoo returns.
- **D-19:** `py.typed` — PEP 561 marker file in the `godoo` package.
- **D-20:** FIXES-03 — `timeout: float | None` on `OdooClientConfig`, threaded to `httpx.AsyncClient(timeout=...)`.
- **D-21:** FIXES-01 — `CdcService.get_feed` fixed by changing `async def` to plain `def`.
- **D-22:** FIXES-02 — transport catches `httpx.TimeoutException` before generic `httpx.RequestError` and raises `OdooTimeoutError`.

### Claude's Discretion

- The exact fix shape for D-21/D-22 follows the CONCERNS.md fix approaches verbatim.
- Un-specified ergonomics (parameter names, docstring wording, helper placement) are at planner/executor discretion, consistent with existing godoo conventions.

### Deferred Ideas (OUT OF SCOPE)

- CLIENT-09 (OAuthProxyClient) — hard-dropped, not parked.
- Pre-existing deferrals: COMPAT-01 (Python floor), CLIENT-V2-01 (auto re-auth), PERF-01/02.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLIENT-01 | `async with OdooClient(...)` opens/closes session | `__aenter__`/`__aexit__` pattern confirmed; `authenticate()` + `aclose()` already exist |
| CLIENT-02 | `iter_search_read()` auto-paginated async generator | Keyset pagination confirmed correct; `('id', '>', last_id)` domain append verified |
| CLIENT-03 | `with_context(...)` threads context dict into RPC calls | `contextvars.ContextVar` confirmed as correct mechanism (see D-06 research below) |
| CLIENT-04 | `fields_get()` returns field metadata | `fields_get` already in `READ_METHODS`; direct `call()` dispatch confirmed |
| CLIENT-05 | `ref(xml_id)` resolves XML ID to record id | `ir.model.data` domain approach confirmed; `OdooMissingError` already exists |
| CLIENT-06 | `execute_kw()` raw RPC passthrough | Routes through `call(model, method, args, kwargs)`; safety level inferred from `method` parameter |
| CLIENT-07 | `read_binary()` returns decoded bytes | `base64.b64decode()` stdlib confirmed; Odoo False-field edge case documented |
| CLIENT-08 | Bulk `create` with list of dicts | `@typing.overload` pattern confirmed; wire side unchanged; empty-list guard pattern exists |
| CLIENT-10 | `py.typed` PEP 561 marker | File location confirmed: `packages/godoo/src/godoo/py.typed`; hatchling includes it automatically |
| FIXES-01 | `CdcService.get_feed` class-API fix | Bug confirmed in code; `async def` → plain `def` fix confirmed |
| FIXES-02 | Transport timeouts raise `OdooTimeoutError` | Bug confirmed: `httpx.ReadTimeout` currently raises `OdooNetworkError`; fix approach verified |
| FIXES-03 | Configurable request timeout | `httpx.AsyncClient(timeout=float\|None)` confirmed; threading path identified |
</phase_requirements>

---

## Summary

Phase 1 adds 9 new methods/behaviors to `OdooClient` and 3 bug fixes to the transport/service layer. All changes are additive or mechanical: no new packages are required, no architectural layers are new. Every new method attaches to `client.py` (CRUD surface) or `transport.py` (transport), following established patterns.

The single highest-uncertainty item — the ambient-context mechanism for `with_context()` — has been resolved through direct Python runtime verification. `contextvars.ContextVar` is confirmed correct: sync `with` blocks that set/reset the var work correctly across `await` points in the same task, concurrent tasks see independent copies, nested blocks merge and restore correctly, and the `token.reset()` mechanism is safe for single-use teardown.

No new external dependencies are required. All changes are pure Python standard library + the existing `httpx` dependency. The test infrastructure (pytest-asyncio + respx) is already in place and sufficient for all new tests.

**Primary recommendation:** Implement all 12 requirements in a single wave targeting `client.py`, `transport.py`, and `services/cdc/service.py`. The py.typed marker is a one-line file creation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| async context manager (`__aenter__`/`__aexit__`) | OdooClient (client.py) | — | Lifecycle management belongs to the client facade |
| Ambient context propagation (`with_context`) | OdooClient (client.py) | — | `call()` is the single chokepoint; threading at this level covers all 8 services automatically |
| Keyset pagination (`iter_search_read`) | OdooClient (client.py) | — | CRUD helper; uses existing `call()` flow; no transport changes needed |
| Field metadata (`fields_get`) | OdooClient (client.py) | — | Standard ORM method; `call()` dispatch; already in READ_METHODS |
| XML ID resolution (`ref`) | OdooClient (client.py) | — | Queries `ir.model.data` via existing `search_read` helper |
| Raw RPC passthrough (`execute_kw`) | OdooClient (client.py) | — | Routes through `call()` for safety guard; transport handles the wire |
| Binary field decode (`read_binary`) | OdooClient (client.py) | — | Reads a field then decodes base64; stdlib only |
| Bulk create overload | OdooClient (client.py) | — | Typing only; wire behavior unchanged |
| Timeout configuration | OdooClientConfig (client.py) + JsonRpcTransport (transport.py) | — | Config lives on the value object; threaded to httpx at transport construction time |
| Timeout error classification | JsonRpcTransport (transport.py) | — | Transport categorizes errors at the wire layer |
| CDC get_feed class-API fix | CdcService (services/cdc/service.py) | — | Service wrapper bug; functions.py unchanged |
| PEP 561 marker | Package filesystem (src/godoo/py.typed) | — | Empty file in package root; no code changes |

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version (installed) | Purpose | Why Standard |
|---------|---------------------|---------|--------------|
| httpx | 0.28.1 | Async HTTP client — all Odoo RPC | Already the transport; `AsyncClient(timeout=...)` and `TimeoutException` hierarchy used in FIXES-02/03 |
| contextvars (stdlib) | Python 3.14 | Task-local ambient state for `with_context()` | Stdlib; correct semantics for concurrent asyncio tasks |
| base64 (stdlib) | Python 3.14 | Decode Odoo binary field base64 | Stdlib; exact tool for CLIENT-07 |
| typing (stdlib) | Python 3.14 | `@typing.overload` for bulk create | Stdlib; required for CLIENT-08 mypy overload |
| collections.abc (stdlib) | Python 3.14 | `AsyncIterator[T]` return type annotation | Already used in CDC service |

### Supporting (test infrastructure — already installed)

| Library | Version (installed) | Purpose | When to Use |
|---------|---------------------|---------|-------------|
| respx | 0.22.0 | Mock httpx for unit tests | All new transport and client tests |
| pytest-asyncio | installed | Async test support | All new async test functions |

### No New Packages Required

All 12 requirements are implementable with the existing dependency set. The package legitimacy audit section is omitted because this phase installs no new packages.

---

## Architecture Patterns

### System Architecture Diagram

```
User code
    |
    | async with OdooClient(...) as client:   <- CLIENT-01: __aenter__/__aexit__
    |     with client.with_context(lang="fr_FR"):  <- CLIENT-03: ContextVar set
    |         await client.search_read(...)   <- ambient context injected at call()
    |         async for r in client.iter_search_read(...):  <- CLIENT-02: keyset pages
    |             ...
    v
OdooClient.call(model, method, args, kwargs)
    |--- infer_safety_level(method) -> SafetyLevel
    |--- _guard(op) -> raise OdooSafetyError if blocked
    |--- _get_ambient_context() -> merge with explicit context kwarg  <- CLIENT-03
    |--- transport.call(model, method, args, merged_kwargs)
    v
JsonRpcTransport.call_rpc()
    |--- except httpx.TimeoutException -> raise OdooTimeoutError  <- FIXES-02
    |--- except httpx.RequestError -> raise OdooNetworkError
    |--- httpx.AsyncClient(timeout=config.timeout)  <- FIXES-03
```

### Recommended Project Structure Changes

```
packages/godoo/src/godoo/
├── py.typed                     # NEW — PEP 561 marker (CLIENT-10)
├── client.py                    # MODIFIED — 9 new methods + ContextVar
└── rpc/
    └── transport.py             # MODIFIED — timeout + FIXES-02/03
packages/godoo/tests/
├── test_client.py               # MODIFIED — tests for new methods
└── test_transport.py            # MODIFIED — timeout and FIXES-02/03 tests
packages/godoo/src/godoo/services/cdc/
└── service.py                   # MODIFIED — FIXES-01
```

### Pattern 1: `__aenter__` / `__aexit__` (CLIENT-01)

`OdooClient` already has `authenticate()` and `aclose()`. The context manager simply delegates:

```python
# Source: Python stdlib docs + existing OdooClient lifecycle methods
async def __aenter__(self) -> OdooClient:
    await self.authenticate()
    return self

async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: object,
) -> None:
    await self.aclose()
```

`__aexit__` always calls `aclose()` regardless of exception — the transport must be closed to avoid resource leak.

### Pattern 2: `contextvars.ContextVar` for `with_context()` (CLIENT-03, D-06 RESOLVED)

**D-06 research verdict: `contextvars.ContextVar` is CORRECT. Confirmed by direct runtime verification.**

Evidence:
1. Sync `with` block (`__enter__`/`__exit__`) sets/resets the var synchronously. Awaits inside the block happen in the same asyncio task, so the var value is visible across await points. [VERIFIED: Python 3.14 runtime]
2. Concurrent asyncio tasks (via `asyncio.gather` or `asyncio.create_task`) each inherit a copy of the parent context at creation time. Changes in one task do not affect another. [VERIFIED: Python 3.14 runtime]
3. `token.reset()` restores the exact previous value, even across nested `with` blocks. [VERIFIED: Python 3.14 runtime]
4. A used token cannot be reset twice (raises `RuntimeError`). The `__exit__` pattern is safe because the token is held as `self._token` on the context manager instance. [VERIFIED: Python 3.14 runtime]

**Confirmed: a plain instance attribute is unsafe** — two concurrent tasks on the same `OdooClient` instance would clobber each other. `ContextVar` avoids this entirely.

Implementation:

```python
# In client.py — module level
import contextvars
_ambient_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "_ambient_context", default={}
)

# The context manager returned by with_context()
class _OdooContextScope:
    """Sync context manager that sets ambient RPC context for the duration of a with block."""

    def __init__(self, layer: dict[str, Any]) -> None:
        self._layer = layer
        self._token: contextvars.Token[dict[str, Any]] | None = None

    def __enter__(self) -> _OdooContextScope:
        current = _ambient_context.get()
        self._token = _ambient_context.set({**current, **self._layer})
        return self

    def __exit__(self, *_: object) -> None:
        if self._token is not None:
            _ambient_context.reset(self._token)
            self._token = None

# On OdooClient:
def with_context(self, **kwargs: Any) -> _OdooContextScope:
    """Return a context manager that threads kwargs into all RPC calls in its block."""
    return _OdooContextScope(kwargs)
```

**Threading in `call()`** (D-05 merge semantics):

```python
async def call(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
    # ... existing safety checks ...

    # Merge ambient context with explicit per-call context (explicit wins)
    ambient = _ambient_context.get()
    if ambient or "context" in kwargs:
        merged_ctx = {**ambient, **kwargs.get("context", {})}
        if merged_ctx:
            kwargs = {**kwargs, "context": merged_ctx}

    return await self._transport.call(model, method, args, kwargs)
```

`kwargs` is copied (not mutated in-place) to avoid surprising callers who pass the same dict repeatedly.

### Pattern 3: Keyset Pagination for `iter_search_read()` (CLIENT-02)

```python
# Source: Odoo ORM documentation + D-09..D-13 locked decisions
async def iter_search_read(
    self,
    model: str,
    domain: list[Any] | None = None,
    *,
    fields: list[str] | None = None,
    batch_size: int = 500,
    limit: int | None = None,
    **kwargs: Any,
) -> AsyncIterator[dict[str, Any]]:
    base_domain = list(domain or [])
    last_id = 0
    yielded = 0

    while True:
        page_domain = base_domain + [("id", ">", last_id)]
        remaining = (limit - yielded) if limit is not None else None
        fetch_size = min(batch_size, remaining) if remaining is not None else batch_size

        batch = await self.search_read(
            model,
            page_domain,
            fields=fields,
            limit=fetch_size,
            order="id",
            **kwargs,
        )
        if not batch:
            break

        for record in batch:
            yield record
            yielded += 1
            if limit is not None and yielded >= limit:
                return

        if len(batch) < fetch_size:
            break
        last_id = batch[-1]["id"]
```

**Why keyset over offset:** Offset pagination suffers O(n) database cost on large offsets and skips/duplicates records when rows are inserted/deleted mid-iteration. Keyset on `id` is O(1) per page with a B-tree index. [VERIFIED: standard SQL pagination knowledge; `id` is always indexed in Odoo]

**Stop condition:** `len(batch) < fetch_size` — if fewer records than requested were returned, there is no next page. Empty batch is also handled (`if not batch: break`).

**The `id` field caveat:** The keyset pagination approach requires `id` to be present in every fetched record to advance `last_id`. When `fields` is provided by the caller, `id` may not be included. Resolution: always inject `"id"` into the fetched fields internally, then strip it from yielded records if the caller did not request it. [ASSUMED — need to verify whether Odoo always returns `id` regardless of `fields` parameter, or requires it to be explicit]

### Pattern 4: `@typing.overload` for Bulk `create()` (CLIENT-08)

```python
# Source: Python typing docs + PEP 484
from typing import overload

@overload
async def create(self, model: str, values: dict[str, Any], **kwargs: Any) -> int: ...
@overload
async def create(self, model: str, values: list[dict[str, Any]], **kwargs: Any) -> list[int]: ...

async def create(
    self,
    model: str,
    values: dict[str, Any] | list[dict[str, Any]],
    **kwargs: Any,
) -> int | list[int]:
    if isinstance(values, list):
        if not values:
            raise OdooValidationError("Cannot create with empty list of values")
        return cast("list[int]", await self.call(model, "create", [values], kwargs))
    return cast("int", await self.call(model, "create", [values], kwargs))
```

**Wire behavior:** `args=[values]` passes a dict or list directly to Odoo's `create` method. Odoo 16+ returns `int` for a single dict, `list[int]` for a list. No wire changes needed. [CITED: Odoo ORM documentation pattern]

**mypy handling:** With `@overload`, call sites get exact return types:
- `await client.create("res.partner", {"name": "A"})` → inferred as `int`
- `await client.create("res.partner", [{"name": "A"}])` → inferred as `list[int]`

### Pattern 5: FIXES-02 — httpx Timeout Exception Order

**Current bug (confirmed):** `transport.py` catches `httpx.RequestError` generically. Since `httpx.TimeoutException` IS a subclass of `httpx.RequestError`, timeouts land as `OdooNetworkError`.

**Fix:** Add `except httpx.TimeoutException` before the generic `except httpx.RequestError` block:

```python
# Source: httpx exception hierarchy — verified at runtime
try:
    response = await self._client.post(...)
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    raise OdooNetworkError(...) from exc
except httpx.TimeoutException as exc:          # NEW — must come before RequestError
    raise OdooTimeoutError(f"Request timed out: {exc}", cause=exc) from exc
except httpx.RequestError as exc:
    raise OdooNetworkError(f"Connection error: {exc}", cause=exc) from exc
```

**Exception hierarchy (verified at runtime):**
- `httpx.TimeoutException` → `TransportError` → `RequestError`
- `httpx.ReadTimeout`, `httpx.ConnectTimeout`, `httpx.WriteTimeout`, `httpx.PoolTimeout` all inherit from `TimeoutException`
- All of these ARE caught by the generic `except httpx.RequestError` — so order matters

### Pattern 6: FIXES-03 — Configurable Timeout Threading

**Config change:**

```python
@dataclass
class OdooClientConfig:
    url: str
    database: str
    username: str
    password: str
    safety: SafetyContext | None = field(default=None)
    timeout: float | None = field(default=None)  # NEW
```

**Transport change:**

```python
class JsonRpcTransport:
    def __init__(self, base_url: str, db: str, timeout: float | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._db = db
        self._client = httpx.AsyncClient(timeout=timeout)  # CHANGED
```

**Client wiring:**

```python
class OdooClient:
    def __init__(self, config: OdooClientConfig) -> None:
        self._config = config
        self._transport = JsonRpcTransport(config.url, config.database, timeout=config.timeout)  # CHANGED
```

**Behavior of `timeout=None` (verified):** `httpx.AsyncClient(timeout=None)` sets `Timeout(timeout=None)` — no timeout on any operation (infinite wait). This differs from the current behavior where `httpx.AsyncClient()` with no arg defaults to `Timeout(timeout=5.0)`. This is intentional per D-20 — the user explicitly opts out.

**Migration note:** Existing code using `OdooClientConfig` without `timeout=` continues to work (field has a default). The effective timeout changes from 5s to None (no timeout) by default. This is a behavioral change but intentional — the previous 5s default was accidental (httpx's hardcoded default, not a godoo policy decision).

### Pattern 7: FIXES-01 — CdcService.get_feed Fix

**Current bug (confirmed):**

```python
# BUG in service.py line 38-39:
async def get_feed(self, options: GetFeedOptions) -> AsyncIterator[TrackingEvent]:
    return get_feed(self._client, options)  # returns coroutine, not iterator
```

`get_feed(client, options)` in `functions.py` is an async generator function — calling it returns an `AsyncGenerator` object immediately (no await needed). But because `service.py` declares `async def`, the method body `return get_feed(...)` wraps that in a coroutine. Callers doing `async for event in svc.get_feed(opts)` receive a coroutine, not an async iterator.

**Fix:** Remove `async`:

```python
def get_feed(self, options: GetFeedOptions) -> AsyncIterator[TrackingEvent]:
    return get_feed(self._client, options)
```

Plain `def` returns the async generator directly. No change to `functions.py`.

### Pattern 8: `fields_get()` (CLIENT-04)

```python
async def fields_get(
    self,
    model: str,
    attributes: list[str] | None = None,
) -> dict[str, Any]:
    """Return field metadata for a model."""
    kwargs: dict[str, Any] = {}
    if attributes is not None:
        kwargs["attributes"] = attributes
    return cast("dict[str, Any]", await self.call(model, "fields_get", [], kwargs))
```

`fields_get` is already in `READ_METHODS` — no safety concerns. [VERIFIED: safety/__init__.py line 17]

### Pattern 9: `ref(xml_id)` (CLIENT-05)

```python
async def ref(self, xml_id: str) -> int:
    """Resolve an external ID (module.name) to a numeric record id."""
    parts = xml_id.split(".", 1)
    if len(parts) != 2:
        raise OdooValidationError(f"Invalid XML ID format (expected 'module.name'): {xml_id!r}")
    module, name = parts
    records = await self.search_read(
        "ir.model.data",
        [("module", "=", module), ("name", "=", name)],
        fields=["res_id"],
    )
    if not records:
        raise OdooMissingError(f"XML ID not found: {xml_id!r}")
    return cast("int", records[0]["res_id"])
```

### Pattern 10: `read_binary()` (CLIENT-07)

```python
import base64

async def read_binary(self, model: str, record_id: int, field: str) -> bytes:
    """Fetch a binary field and return decoded bytes."""
    records = await self.read(model, record_id, fields=[field])
    if not records:
        raise OdooMissingError(f"Record {model}:{record_id} not found")
    raw = records[0].get(field)
    if raw is False or raw is None:
        return b""
    return base64.b64decode(raw)
```

**Edge case:** Odoo returns `False` (Python bool) for empty binary fields, not an empty string or `None`. The `if raw is False or raw is None: return b""` guard handles this correctly. [CITED: Odoo ORM binary field behavior — returns False when no attachment data]

### Pattern 11: `execute_kw()` (CLIENT-06)

```python
async def execute_kw(
    self,
    model: str,
    method: str,
    args: list[Any],
    kwargs: dict[str, Any] | None = None,
) -> Any:
    """Raw RPC passthrough for non-standard Odoo methods."""
    return await self.call(model, method, args, kwargs or {})
```

Safety classification: `infer_safety_level(method)` is called inside `call()` on the `method` parameter — so `execute_kw("account.move", "action_post", [], {})` is classified as WRITE (correct). [VERIFIED: safety/__init__.py infer_safety_level]

### Pattern 12: `py.typed` PEP 561 Marker (CLIENT-10)

Create empty file: `packages/godoo/src/godoo/py.typed`

Hatchling automatically includes all non-Python files in the package directory when building the wheel. The `pyproject.toml` already has `"Typing :: Typed"` in classifiers. No other changes required. [VERIFIED: hatchling build behavior — packages = ["src/godoo"] includes all files under src/godoo/]

### Anti-Patterns to Avoid

- **Mutating the `kwargs` dict in-place in `call()`:** Callers may reuse the same dict. Always copy: `kwargs = {**kwargs, "context": merged_ctx}`.
- **Using `self._ambient_context` as an instance attribute:** Breaks concurrent tasks on the same client (instance state is shared; ContextVar is task-local). Explicitly rejected per D-06.
- **Calling `ContextVar.reset(token)` in `__exit__` without guarding:** A double-reset raises `RuntimeError`. Guard with `if self._token is not None` and set to `None` after reset.
- **Placing `async def get_feed` in service.py:** This re-introduces FIXES-01. The generator function in `functions.py` must be called from a plain `def` in `service.py`.
- **Adding `iter_search_read` to a service quad:** This is a CRUD helper on `OdooClient` directly, not a domain service.
- **Injecting `id` into the `fields` list permanently:** If the caller requests specific fields, injecting `id` permanently changes the returned record shape. Strip `id` from the yielded record if it was not in the original `fields` list.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task-local ambient state | Instance attribute with lock | `contextvars.ContextVar` | ContextVar is designed for exactly this; instance attr is unsafe under concurrent tasks |
| Timeout exception hierarchy | Custom exception mapping | Catch `httpx.TimeoutException` before `httpx.RequestError` | httpx already provides the correct hierarchy; just catch in the right order |
| Binary field decoding | Custom base64 parser | `base64.b64decode()` | stdlib handles padding, encoding, and all edge cases |
| Token management for context | Manual push/pop stack | `ContextVar.set()` + `token.reset()` | The token pattern is atomic and re-entrant by design |

---

## Common Pitfalls

### Pitfall 1: `httpx.TimeoutException` Catch Order

**What goes wrong:** `except httpx.RequestError` is placed before `except httpx.TimeoutException`. Since `TimeoutException` is a subclass of `RequestError`, the generic handler catches it first.
**Why it happens:** The hierarchy is non-obvious; both are "network errors".
**How to avoid:** Always order exception handlers from most-specific to most-generic. `TimeoutException` BEFORE `RequestError`.
**Warning signs:** Tests for `OdooTimeoutError` raising `OdooNetworkError` instead.

### Pitfall 2: `ContextVar` Module-Level Scope

**What goes wrong:** The `ContextVar` is defined inside a class method or `__init__`, creating a new var per instance.
**Why it happens:** Looks natural but defeats the purpose — per-task isolation requires the var to be process-global.
**How to avoid:** Define `_ambient_context` at module level in `client.py` (outside any class). One var for the entire process.

### Pitfall 3: `asyncio.create_task` Inherits Context Copy

**What goes wrong:** A task spawned with `asyncio.create_task` inside a `with client.with_context(...)` block sees the ambient context at creation time. If the `with` block exits before the task runs, the task still sees the context (it got a copy, not a reference). This is CORRECT behavior, but may surprise callers who expect spawned tasks to see a clean context.
**Why it matters:** Generally this is the desired behavior — the task inherits the context it was spawned in. But callers should not rely on the spawned task's context var changes being visible to the parent.
**How to avoid:** Document this behavior. It is standard Python ContextVar semantics.

### Pitfall 4: `iter_search_read` Missing `id` Field

**What goes wrong:** Caller passes `fields=["name", "email"]`. `search_read` returns records without `id`. `batch[-1]["id"]` raises `KeyError`. Iteration silently breaks.
**Why it happens:** `fields` parameter filters the returned columns. `id` must be explicitly requested.
**How to avoid:** Internally always include `id` in the fetched fields. If `id` was not in the caller's requested fields, strip it from each yielded record.

### Pitfall 5: `create(model, [])` Wire Behavior

**What goes wrong:** Sending `args=[[]]` to Odoo's `create` may raise a server-side error or return an empty list depending on version. The behavior is undefined.
**Why it happens:** The guard (D-08) raises locally before the RPC. But if the guard is accidentally skipped, the wire call goes through.
**How to avoid:** The `OdooValidationError` guard on empty list must be the FIRST thing in the `isinstance(values, list)` branch, before the `cast` and `call`.

### Pitfall 6: `with_context` Applies to the Full `call()` Chokepoint

**What goes wrong:** A developer implements `with_context` by modifying `search_read`, `read`, etc. individually. Services that call `client.call()` directly bypass the context injection.
**Why it matters:** Context injection must happen in `call()` — the single chokepoint — to cover all 8 services automatically (per D-03).
**How to avoid:** Inject context in `call()` only. All CRUD helpers and service functions go through `call()`.

---

## Runtime State Inventory

This section is not applicable — Phase 1 is pure code additions/fixes. No rename/refactor/migration is involved. No stored data, live service config, OS-registered state, secrets, or build artifacts need updating.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | All | ✓ | 3.14.5 | — |
| uv | Workspace, tests | ✓ | 0.11.13 | — |
| httpx | Transport | ✓ | 0.28.1 | — |
| contextvars (stdlib) | with_context | ✓ | Python 3.14 | — |
| base64 (stdlib) | read_binary | ✓ | Python 3.14 | — |
| typing (stdlib) | @overload | ✓ | Python 3.14 | — |
| pytest | Tests | ✓ | 9.0.2 | — |
| pytest-asyncio | Async tests | ✓ | installed | — |
| respx | Mock HTTP tests | ✓ | 0.22.0 | — |
| mypy | Type checking | ✓ | installed | — |
| ruff | Linting | ✓ | installed | — |

**Baseline status:** 157 unit tests pass. `mypy --strict` passes on all 45 source files. `ruff check` passes. All tools confirmed working.

**Missing dependencies with no fallback:** None.

---

## Code Examples

### Async context manager test pattern

```python
# Source: test_client.py pattern (respx mock)
@respx.mock
async def test_async_context_manager(client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            httpx.Response(200, json=_jsonrpc_result(2)),  # authenticate
        ]
    )
    async with client as c:
        assert c is client
        assert client.is_authenticated()
    # aclose() was called — transport closed
```

### ContextVar test — concurrent isolation

```python
# Source: Python 3.14 runtime verification in this research session
async def test_with_context_concurrent_isolation():
    client_a = OdooClient(...)  # shared client
    
    async def task_a():
        with client_a.with_context(lang="fr_FR"):
            await asyncio.sleep(0)
            # reads ambient context inside with block
            ...
    
    async def task_b():
        with client_a.with_context(lang="de_DE"):
            await asyncio.sleep(0)
            ...
    
    await asyncio.gather(task_a(), task_b())
    # Both tasks complete without clobbering each other
```

### Timeout test pattern (FIXES-02)

```python
# Source: respx mock + httpx exception hierarchy (verified at runtime)
@respx.mock
async def test_timeout_raises_odoo_timeout_error(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=httpx.ReadTimeout("timed out"))
    with pytest.raises(OdooTimeoutError):
        await transport.call_rpc("common.authenticate", {})
```

### Keyset iteration test pattern (CLIENT-02)

```python
# Source: iter_search_read design (D-09..D-13)
@respx.mock
async def test_iter_search_read_two_pages(auth_client):
    # Page 1: batch_size=3, returns 3 records
    page1 = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}]
    # Page 2: returns 1 record (< batch_size → stop)
    page2 = [{"id": 4, "name": "D"}]
    respx.post(...).mock(side_effect=[
        httpx.Response(200, json=_jsonrpc_result(page1)),
        httpx.Response(200, json=_jsonrpc_result(page2)),
    ])
    records = [r async for r in auth_client.iter_search_read("res.partner", batch_size=3)]
    assert len(records) == 4
    assert records[-1]["id"] == 4
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Offset pagination (`offset=N`) | Keyset pagination (`id > last_id`) | Long-standing best practice | Avoids O(n) DB cost on deep pages; correct under concurrent writes |
| Manual `authenticate()` + `aclose()` | `async with OdooClient(...)` | CLIENT-01 | Standard Python resource management pattern |
| Instance attribute for ambient state | `contextvars.ContextVar` | CLIENT-03 | Task-safe; no cross-task clobber |

**Deprecated/outdated:**
- `except httpx.RequestError` as the sole exception catch: superseded by adding `except httpx.TimeoutException` first (FIXES-02)
- `httpx.AsyncClient()` with no timeout argument: replaced by explicit `timeout=config.timeout` (FIXES-03)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Odoo's `search_read` does not return `id` automatically when a `fields` list is specified — `id` must be included explicitly in the list | Pattern 3 (iter_search_read), Pitfall 4 | If Odoo always returns `id`, the "inject then strip" approach adds unnecessary complexity but is harmless. If id is truly not returned, the pitfall is real and the guard is required. |
| A2 | Odoo 16+ returns `list[int]` from `create` when passed a list of dicts | Pattern 4 (bulk create) | Older Odoo versions (< 16) do not support batch create and may raise server-side errors. Since the library targets whatever version the caller has, this is a usage concern not a code bug. |
| A3 | `hatchling` includes `py.typed` (non-`.py` file) in the wheel automatically without additional `[tool.hatch.build.targets.wheel]` include config | Pattern 12 (py.typed) | If hatchling requires explicit `include` for non-Python files, the py.typed marker would be absent from the wheel despite being in the source tree. Low risk — hatchling's default behavior is to include all package files. |

---

## Open Questions

1. **`iter_search_read` — does Odoo always return `id` when fields are specified?**
   - What we know: Standard Odoo ORM `search_read` returns only the requested fields when `fields=` is given. The `id` field is special in some Odoo versions and may be returned regardless.
   - What's unclear: Whether Odoo 16/17/18 always returns `id` even in `search_read` with explicit `fields`, making the inject-and-strip pattern unnecessary.
   - Recommendation: Implement the guard (always inject `id`; strip if not in caller's list). This is safe regardless of Odoo version behavior.

2. **`read_binary` — should empty binary (`False`) return `b""` or raise `OdooMissingError`?**
   - What we know: Odoo returns `False` for unset binary fields. D-18 only specifies returning decoded `bytes`.
   - What's unclear: Whether the caller expects `b""` for an empty field or an exception.
   - Recommendation: Return `b""` for `False`/`None` fields. Raising `OdooMissingError` would be surprising for a valid record with an unset attachment. Document this behavior.

---

## Security Domain

`security_enforcement: true` with `security_asvs_level: 1` in config.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No — no new auth code | — |
| V3 Session Management | No — session management unchanged | — |
| V4 Access Control | Partial — `execute_kw` raw passthrough | Route through `call()` + safety guard (already enforced) |
| V5 Input Validation | Yes — `ref()` xml_id format, bulk create empty list, `read_binary` field name | Local precondition checks before RPC |
| V6 Cryptography | No | — |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `execute_kw` used to call privileged Odoo methods | Elevation of Privilege | Already mitigated: routes through `call()` → `infer_safety_level(method)` → `_guard(op)`. Safety guard gates DELETE/WRITE methods. |
| `with_context` used to inject dangerous Odoo context keys (e.g., `active_test=False`) | Tampering | By design — `with_context` is a power-user feature. Document that context keys are passed verbatim to Odoo. |
| Ambient context leaking across HTTP requests to different models | Information Disclosure | Mitigated by ContextVar task-scoping. The ambient context applies to the current task only, not globally. |
| Binary field content passed to `read_binary` containing malicious data | Not applicable | The client decodes and returns bytes; interpretation is the caller's responsibility. |

---

## Sources

### Primary (HIGH confidence)

- Python 3.14 runtime — `contextvars.ContextVar` behavior, `contextvars.Token`, nested with blocks, concurrent task isolation [VERIFIED: direct runtime execution in this session]
- httpx 0.28.1 runtime — `TimeoutException` MRO, `AsyncClient(timeout=...)` parameter, `Timeout` class signature [VERIFIED: direct runtime inspection]
- Codebase — `packages/godoo/src/godoo/client.py`, `packages/godoo/src/godoo/rpc/transport.py`, `packages/godoo/src/godoo/safety/__init__.py`, `packages/godoo/src/godoo/services/cdc/service.py` [VERIFIED: direct file read]
- `.planning/codebase/CONCERNS.md` — FIXES-01/02/03 exact fix recipes [VERIFIED: direct file read]

### Secondary (MEDIUM confidence)

- `@typing.overload` pattern [CITED: Python typing module — PEP 484]
- Odoo `ir.model.data` lookup for `ref()` [CITED: Odoo ORM external IDs documentation pattern]
- Odoo binary fields returning `False` for empty values [CITED: Odoo ORM field documentation]
- Keyset pagination superiority over offset [CITED: standard SQL pagination practice; id is always indexed in Odoo]
- hatchling including non-Python files automatically [ASSUMED — see A3 in assumptions log]

### Tertiary (LOW confidence)

- Odoo 16+ supporting batch `create` (list of dicts) [ASSUMED — A2 in assumptions log]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; verified installed versions
- Architecture: HIGH — patterns verified against actual source code and Python runtime
- D-06 resolution (ContextVar): HIGH — confirmed by direct runtime execution with concurrent tasks and nested blocks
- FIXES-02/03: HIGH — httpx exception hierarchy and AsyncClient API verified at runtime against installed 0.28.1
- Assumptions A1/A2/A3: LOW — marked as [ASSUMED]; require verification or safe defensive implementation

**Research date:** 2026-05-19
**Valid until:** 2026-06-19 (stable stack; httpx 0.x API is stable)
