<!-- refreshed: 2026-05-18 -->
# Architecture

**Analysis Date:** 2026-05-18

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                       Caller (user code)                            │
│  config_from_env() / create_client()  ·  OdooClientConfig           │
│  `packages/godoo/src/godoo/config.py`                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         OdooClient                                  │
│  `packages/godoo/src/godoo/client.py`                               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐ │
│  │  Safety Gate  │  │  CRUD helpers    │  │  @cached_property     │ │
│  │  _guard(op)   │  │  search / read   │  │  service accessors    │ │
│  │  safety/      │  │  write / unlink  │  │  mail, cdc, modules…  │ │
│  └──────────────┘  └──────────────────┘  └───────────────────────┘ │
└───────────────┬─────────────────────────────┬───────────────────────┘
                │ call()                      │ lazy-import + cache
                ▼                             ▼
┌───────────────────────────┐  ┌──────────────────────────────────────┐
│     JsonRpcTransport      │  │            Services (8)              │
│  `rpc/transport.py`       │  │  `services/{name}/`                  │
│                           │  │                                      │
│  call_rpc()  → POST /     │  │  functions.py  ← standalone async   │
│  jsonrpc                  │  │  service.py    ← class delegating    │
│  _categorize_error()      │  │  types.py      ← dataclasses        │
└───────────────────────────┘  └──────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Odoo JSON-RPC endpoint                           │
│  POST /jsonrpc  (common.authenticate / object.execute_kw)           │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `OdooClientConfig` | Value object: URL, DB, credentials, optional safety context | `packages/godoo/src/godoo/client.py` |
| `OdooClient` | Auth lifecycle, safety guard enforcement, CRUD helpers, lazy service accessors | `packages/godoo/src/godoo/client.py` |
| `JsonRpcTransport` | HTTP wire protocol — builds JSON-RPC payloads, maps error types, manages session | `packages/godoo/src/godoo/rpc/transport.py` |
| `OdooSessionInfo` | Immutable auth token: uid, session_id, db | `packages/godoo/src/godoo/rpc/types.py` |
| `SafetyContext` | Pluggable async confirm callback that gates mutating operations | `packages/godoo/src/godoo/safety/__init__.py` |
| `config_from_env` | Reads `ODOO_URL/DB/USER/PASSWORD` from env, returns config | `packages/godoo/src/godoo/config.py` |
| `create_client` | Combines `config_from_env` + authenticate; one-liner async factory | `packages/godoo/src/godoo/config.py` |
| Service functions | Domain-level async functions taking `OdooClient` as first arg | `packages/godoo/src/godoo/services/{name}/functions.py` |
| Service classes | Thin wrappers that hold `self._client` and delegate to functions | `packages/godoo/src/godoo/services/{name}/service.py` |
| `OdooTestContainer` | Provisions Docker Postgres + Odoo containers for integration tests | `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` |

## Pattern Overview

**Overall:** Layered SDK with a functional core

**Key Characteristics:**
- Every service exposes two equivalent APIs: standalone functions (take `client` as first arg) and a class wrapper that closes over `self._client`. Callers may use either.
- The `OdooClient` layer is the only integration point. Services never import the transport directly; they call `client.search_read()`, `client.write()`, etc.
- Safety is a cross-cutting middleware injected at the `call()` boundary in `OdooClient`. Services are unaware of it.
- Service classes are instantiated lazily via `@cached_property` to avoid circular imports at module load time.
- Transport errors are categorized at the lowest layer (`JsonRpcTransport._categorize_error`) and surface as typed subclasses of `OdooRpcError`.

## Layers

**RPC Transport:**
- Purpose: HTTP wire protocol — POST to `/jsonrpc`, parse response, raise typed exceptions
- Location: `packages/godoo/src/godoo/rpc/`
- Contains: `JsonRpcTransport`, `OdooSessionInfo`
- Depends on: `httpx`, `godoo.errors`
- Used by: `OdooClient` only

**Client / Safety:**
- Purpose: Auth lifecycle, safety guard, CRUD convenience helpers, service registry
- Location: `packages/godoo/src/godoo/client.py`, `packages/godoo/src/godoo/safety/__init__.py`
- Contains: `OdooClient`, `OdooClientConfig`, `SafetyContext`, `OperationInfo`, `infer_safety_level`
- Depends on: `rpc/transport.py`, `safety/`, `errors.py`
- Used by: all callers; services call back into `OdooClient`

**Services:**
- Purpose: Domain-specific operations against Odoo models
- Location: `packages/godoo/src/godoo/services/{name}/`
- Contains: `functions.py` (business logic), `service.py` (class wrapper), `types.py` (dataclasses)
- Depends on: `OdooClient` (via TYPE_CHECKING import to avoid circular), peer service functions when composing (e.g. `timesheets.functions` imports `attendance.functions.resolve_employee_id`)
- Used by: user code via `client.{service_name}`

**Configuration:**
- Purpose: Environment-variable bootstrapping
- Location: `packages/godoo/src/godoo/config.py`
- Contains: `config_from_env`, `create_client`
- Depends on: `OdooClient`, `OdooClientConfig`
- Used by: top-level user entry points

**Test Infrastructure:**
- Purpose: Docker-based live Odoo instance for integration tests
- Location: `packages/godoo-testcontainers/src/godoo_testcontainers/`
- Contains: `OdooTestContainer`, `StartedOdooContainer`, `SeedInfo`, seed resolver
- Depends on: `godoo` (core package), `testcontainers`, `httpx`
- Used by: `tests/conftest.py` session fixture

## Data Flow

### Primary Request Path

1. Caller builds config and authenticates (`config.py:create_client` or `OdooClient.authenticate()`)
2. `OdooClient.authenticate()` delegates to `JsonRpcTransport.authenticate()` → POST `/jsonrpc` with `common.authenticate`; stores `OdooSessionInfo`
3. Caller invokes a CRUD helper or service method, e.g. `client.search_read(model, domain)`
4. `OdooClient.call()` (`client.py:102`) infers `SafetyLevel` via `infer_safety_level(method)` and calls `_guard(op)` — raises `OdooSafetyError` if denied
5. `OdooClient.call()` delegates to `JsonRpcTransport.call()` which POSTs `object.execute_kw` to `/jsonrpc`
6. `JsonRpcTransport.call_rpc()` inspects the response; on `"error"` key calls `_categorize_error()` and raises the appropriate `OdooRpcError` subclass
7. Typed Python data is returned up the call chain

### Service Delegation Flow

1. Caller accesses `client.accounting` (first access instantiates `AccountingService(client)` via `@cached_property`)
2. `client.accounting.discover_cash_accounts()` delegates to `discover_cash_accounts(self._client)` in `functions.py`
3. Function calls `client.search_read(...)` (back through the OdooClient layer)

### CDC Feed Flow (async generator pattern)

1. `client.cdc.get_feed(options)` returns `get_feed(client, options)` — an `AsyncIterator`
2. Caller iterates with `async for event in feed:`
3. Each batch fetches from `mail.tracking.value`, resolves field metadata via `field_cache.py` (module-level dict cache), resolves typed values via `resolver.py`
4. Generator yields `TrackingEvent` dataclasses and advances the id-cursor; stops when batch < `batch_size`

**State Management:**
- `OdooClient` holds mutable `_safety_context` (sentinel `_UNDEFINED` / `None` / `SafetyContext`)
- `JsonRpcTransport` holds `_session: OdooSessionInfo | None` and `_password: str | None`
- CDC `field_cache.py` holds a module-level `_cache: dict[str, FieldMeta]` dict — process-global, not client-scoped
- URL service `functions.py` holds a module-level `_base_url_cache: dict[int, str]` keyed by `id(client)`
- No other global mutable state; services are stateless

## Key Abstractions

**OdooClient:**
- Purpose: Single entry point for all Odoo interactions; abstracts transport + safety + service registry
- Examples: `packages/godoo/src/godoo/client.py`
- Pattern: Facade + service locator via `@cached_property`

**Service Trio (functions / service / types):**
- Purpose: Separates business logic (functions) from object API (service class) from data shapes (types)
- Examples: `packages/godoo/src/godoo/services/accounting/`, `packages/godoo/src/godoo/services/cdc/`
- Pattern: Functions-first with class wrapper; functions are independently callable for testing

**SafetyContext:**
- Purpose: Pluggable async gate for write/delete operations; callers inject a `confirm` callback
- Examples: `packages/godoo/src/godoo/safety/__init__.py`
- Pattern: Dataclass wrapping an async callable; module-level default + per-client override

**OdooError hierarchy:**
- Purpose: Typed exception tree from HTTP errors down to ACL/validation/missing errors
- Examples: `packages/godoo/src/godoo/errors.py`
- Pattern: `OdooError` → `OdooRpcError` → {Auth, Network, Timeout, Validation, Access, Missing}; plus `OdooSafetyError` (local, not from RPC)

## Entry Points

**`create_client` (async):**
- Location: `packages/godoo/src/godoo/config.py`
- Triggers: User code startup; reads env vars
- Responsibilities: Build config, construct client, authenticate, return ready client

**`OdooClient.__init__` + `authenticate`:**
- Location: `packages/godoo/src/godoo/client.py`
- Triggers: Direct instantiation when caller has explicit config
- Responsibilities: Construct transport, hold config; `authenticate()` performs JSON-RPC auth

**`OdooTestContainer.start` (async):**
- Location: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`
- Triggers: pytest session fixture in `tests/conftest.py`
- Responsibilities: Spin up Docker network, Postgres, Odoo; wait for readiness; authenticate client; install modules

## Architectural Constraints

- **Threading:** Single async event loop. testcontainers-python has a sync API; all `.start()`, `wait_for_logs()` calls are wrapped in `asyncio.to_thread()` (`container.py`)
- **Global state:** Two module-level caches: `_cache` in `services/cdc/field_cache.py` and `_base_url_cache` in `services/urls/functions.py`. Both are process-global and not invalidated between test runs without calling `clear_cache()`.
- **Circular imports:** Services use `TYPE_CHECKING` to import `OdooClient` only for type annotations; runtime imports are deferred to avoid circular dependency between `client.py` and service modules. `@cached_property` bodies use local `from ... import` for the same reason.
- **No async context manager:** `OdooClient` does not implement `__aenter__`/`__aexit__`; callers must call `aclose()` explicitly or manage lifecycle themselves.

## Anti-Patterns

### Accessing transport directly from services

**What happens:** A service bypasses `OdooClient` and calls `client._transport.call()` directly
**Why it's wrong:** Bypasses the safety guard at `OdooClient.call()`, and `_transport` is a private attribute
**Do this instead:** Services call `client.search_read()`, `client.write()`, etc. via the public CRUD helpers on `OdooClient`

### Importing OdooClient at module level in services

**What happens:** A `functions.py` or `service.py` does `from godoo.client import OdooClient` at the top of the file
**Why it's wrong:** Creates a circular import (`client.py` imports service classes; service modules import `OdooClient`)
**Do this instead:** Place `OdooClient` imports inside `if TYPE_CHECKING:` blocks and use string annotations or `from __future__ import annotations` — exactly as done in every existing service (`packages/godoo/src/godoo/services/accounting/functions.py:17`)

### Using sync testcontainers calls in async tests

**What happens:** Calling `container.start()`, `wait_for_logs()` directly in async code
**Why it's wrong:** Blocks the event loop
**Do this instead:** Wrap every sync testcontainers call with `await asyncio.to_thread(...)` as done in `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`

## Error Handling

**Strategy:** Typed exception hierarchy; errors raised at the lowest layer they can be detected; callers catch specific subclasses.

**Patterns:**
- `JsonRpcTransport._categorize_error()` maps Odoo's `exception_type` / `data.name` strings to typed `OdooRpcError` subclasses (`packages/godoo/src/godoo/rpc/transport.py:136`)
- `OdooClient._guard()` raises `OdooSafetyError` (a local, non-RPC error) when a safety callback returns `False`
- Services raise `OdooValidationError` for domain-level precondition failures (e.g. employee not found in `attendance/functions.py`)
- All error classes expose `.to_json()` for structured serialization

## Cross-Cutting Concerns

**Logging:** `logging.getLogger("godoo.client")` in `client.py`; `logging.getLogger("godoo.client.rpc")` in `transport.py`; `logging.getLogger("godoo.client.modules")` in `module_manager.py`; `logging.getLogger("godoo.testcontainers")` in testcontainers. Standard Python `logging` — no framework.

**Validation:** Performed in service functions before issuing RPC calls (e.g. checking employee resolution, checking module state before upgrade). No schema validation layer.

**Authentication:** Explicit call to `client.authenticate()` required before any `call()`. `is_authenticated()` check in `call()` raises `OdooAuthError` if skipped. Session is stored in `JsonRpcTransport._session`.

---

*Architecture analysis: 2026-05-18*
