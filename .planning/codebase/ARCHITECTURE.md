# Architecture

**Analysis Date:** 2026-04-10

## Pattern Overview

**Overall:** Layered async client with a domain-driven service tier above a JSON-RPC transport layer, protected by a safety guard.

**Key Characteristics:**
- Service-oriented: Each domain (mail, accounting, modules, etc.) is a separate service wrapping business logic
- Dependency injection via constructor: Services receive `OdooClient` as the sole dependency
- Lazy initialization: Services are cached properties on `OdooClient`, instantiated on first access
- Safety-first design: All write/delete operations pass through a confirmation guard before RPC dispatch
- Async-all: Every service function and method is async; all network I/O uses `httpx.AsyncClient`
- Type-safe: Full mypy strict compliance with dataclasses for all input/output types

## Layers

**Application (Entry Point):**
- Purpose: User-facing async client API
- Location: `packages/godoo/src/godoo/client.py`
- Contains: `OdooClient` class with CRUD helpers and service accessors
- Depends on: `JsonRpcTransport`, `SafetyContext`, service implementations
- Used by: User code, service classes

**Service Layer:**
- Purpose: Domain-specific business logic (mail, accounting, timesheets, etc.)
- Location: `packages/godoo/src/godoo/services/{name}/`
- Contains: Service classes (e.g., `MailService`, `AccountingService`) that delegate to functions
- Depends on: `OdooClient`, types, functions
- Used by: Application layer (via cached properties on `OdooClient`)

**Function Layer:**
- Purpose: Standalone async functions implementing service logic
- Location: `packages/godoo/src/godoo/services/{name}/functions.py`
- Contains: Async functions that take `client: OdooClient` as first arg, perform business logic, call `client.call()`
- Depends on: `OdooClient`, types, error classes
- Used by: Service classes

**Safety Guard:**
- Purpose: Confirm operations before dispatch to RPC
- Location: `packages/godoo/src/godoo/safety/__init__.py`
- Contains: `SafetyContext` (async confirmation callback), `OperationInfo` (operation descriptor), safety level inference
- Depends on: Nothing (pure logic)
- Used by: `OdooClient._guard()` before every non-READ operation

**RPC Transport:**
- Purpose: JSON-RPC wire protocol and session management
- Location: `packages/godoo/src/godoo/rpc/transport.py`
- Contains: `JsonRpcTransport` class wrapping `httpx.AsyncClient`, error classification
- Depends on: `httpx`, error classes
- Used by: `OdooClient`

**Error Handling:**
- Purpose: Exception taxonomy and error classification
- Location: `packages/godoo/src/godoo/errors.py`
- Contains: Exception hierarchy (`OdooError`, `OdooRpcError` subclasses for specific errors)
- Depends on: Nothing
- Used by: Transport, service functions, all layers

**Configuration:**
- Purpose: Environment-based setup and client bootstrapping
- Location: `packages/godoo/src/godoo/config.py`
- Contains: `config_from_env()` (reads ODOO_* env vars), `create_client()` (factory with auth)
- Depends on: `OdooClient`, `OdooClientConfig`
- Used by: Setup code, tests

## Data Flow

**Authentication Flow:**

1. User creates `OdooClientConfig` (url, database, username, password)
2. User instantiates `OdooClient(config)`
3. User calls `await client.authenticate()`
4. `OdooClient.authenticate()` → `JsonRpcTransport.authenticate()`
5. Transport calls RPC method `common.authenticate` with credentials
6. Server returns `uid`; transport stores `OdooSessionInfo` (uid, session_id, db)
7. Services become accessible via cached properties (e.g., `client.mail`, `client.accounting`)

**Service Call Flow:**

1. User calls `await client.mail.post_internal_note(model, res_id, body)`
2. `MailService.post_internal_note()` calls function `post_internal_note(client, model, res_id, body, options)`
3. Function builds kwargs dict with Odoo RPC params
4. Function calls `await client.call(model, "message_post", [res_id], kwargs)`
5. `OdooClient.call()` → `OdooClient._guard(OperationInfo)` checks safety context
6. If safety guard blocks, raises `OdooSafetyError`; if allowed or disabled, continues
7. `OdooClient.call()` → `JsonRpcTransport.call()`
8. Transport encodes as JSON-RPC 2.0, POSTs to `/jsonrpc` endpoint
9. Response parsed; if RPC error, classified to specific error subclass (e.g., `OdooValidationError`, `OdooAccessError`)
10. If success, result normalized (e.g., mail service extracts message ID from various response formats)
11. Result returned to user

**State Management:**

- **Session State:** Stored in `JsonRpcTransport._session` (read-only after auth, cleared on logout)
- **Auth State:** Checked via `OdooClient.is_authenticated()`; prevents calls before auth
- **Safety State:** Stored in `OdooClient._safety_context` (can be overridden per-client via `set_safety_context()`)
- **Connection State:** Held by `httpx.AsyncClient`; closed via `OdooClient.aclose()`

## Key Abstractions

**OdooClient:**
- Purpose: High-level user-facing API combining CRUD, services, auth, and safety
- Examples: `packages/godoo/src/godoo/client.py`
- Pattern: Facade over transport and services; dependency injector for services

**Service Class (e.g., MailService):**
- Purpose: Grouped business logic for a domain; delegates to functions
- Examples: `packages/godoo/src/godoo/services/mail/service.py`, `packages/godoo/src/godoo/services/accounting/service.py`
- Pattern: Methods mirror function signatures; functions hold actual logic (testable, reusable)

**Functions (e.g., post_internal_note):**
- Purpose: Testable, standalone business logic operations
- Examples: `packages/godoo/src/godoo/services/mail/functions.py`, `packages/godoo/src/godoo/services/accounting/functions.py`
- Pattern: Async functions with `client: OdooClient` as first arg; other args are domain-specific; return typed results

**Types (e.g., PostMessageOptions):**
- Purpose: Input/output contracts for functions and services
- Examples: `packages/godoo/src/godoo/services/mail/types.py` (dataclass fields for message options)
- Pattern: Dataclasses (no Pydantic) with defaults; inherit optional fields as `field(default_factory=...)`

**JsonRpcTransport:**
- Purpose: Stateful wire protocol handler; single httpx.AsyncClient per instance
- Examples: `packages/godoo/src/godoo/rpc/transport.py`
- Pattern: Owns session state and password; all calls go through `call_rpc()` which handles JSON-RPC 2.0 protocol and error mapping

**SafetyContext:**
- Purpose: Pluggable operation confirmation callback
- Examples: `packages/godoo/src/godoo/safety/__init__.py`
- Pattern: Dataclass wrapping an async callable `confirm(OperationInfo) -> bool`; can be global default or per-client

## Entry Points

**For Application Code:**
- Location: `packages/godoo/src/godoo/__init__.py`
- Exports: `OdooClient`, `OdooClientConfig`, all error types, service classes, safety types
- Triggers: Import `from godoo import OdooClient`
- Responsibilities: Publish public API; other modules are internal

**For Config Setup:**
- Location: `packages/godoo/src/godoo/config.py`
- Entry: `config_from_env()` or `create_client()`
- Triggers: User calls to bootstrap from environment
- Responsibilities: Load env vars, validate, return configured client or config

**For Tests:**
- Location: `packages/godoo/tests/` and `packages/godoo-testcontainers/`
- Entry: `pytest` with integration marker for real Odoo (needs Docker)
- Triggers: `uv run pytest` or `uv run pytest -m integration`
- Responsibilities: Mock HTTP (respx) for unit tests; testcontainers for integration tests

## Error Handling

**Strategy:** Classify all RPC errors to domain-specific exception subclasses; safety guard raises local errors.

**Patterns:**

- **RPC Error Classification:** `JsonRpcTransport._categorize_error()` maps RPC error codes/messages to `OdooRpcError` subclasses:
  - `OdooAccessError` for ACL violations (code 1, message "Access denied")
  - `OdooValidationError` for business logic errors (message contains "ValidationError" or "UserError")
  - `OdooMissingError` for record not found (message contains "MissingError")
  - `OdooAuthError` for auth failures (message contains "Auth", "login" failures)
  - Generic `OdooRpcError` for unknown errors

- **Safety Guard Errors:** If `SafetyContext.confirm()` returns False, `OdooClient._guard()` raises `OdooSafetyError` with full `OperationInfo` attached (for logging, debugging).

- **Network Errors:** Connection failures and HTTP errors raised as `OdooNetworkError`; timeouts as `OdooTimeoutError`.

- **All errors implement `to_json()`** for serialization (useful for APIs, logging).

## Cross-Cutting Concerns

**Logging:** 
- Loggers: `godoo.client`, `godoo.client.rpc`, `godoo.client.modules` (per layer)
- Pattern: Named loggers with hierarchical scope; `logger.debug()` for RPC calls, `logger.warning()` for retries
- Used for: Observability in production

**Validation:**
- Pattern: Functions validate inputs before RPC calls (e.g., `ensure_html_body()` in mail service)
- Pattern: Service functions check preconditions and raise `OdooValidationError` for bad input
- Used for: Fail-fast, clear error messages

**Authentication:**
- Pattern: Session stored in transport after `authenticate()`; checked via `OdooClient.is_authenticated()`
- Pattern: `OdooClient.call()` raises `OdooAuthError` if called before auth
- Used for: Prevent silent failures, enforces auth-before-call discipline

**Type Safety:**
- Pattern: All service functions and methods fully typed with return types
- Pattern: `TYPE_CHECKING` imports to avoid circular deps (e.g., `OdooClient` imported in `if TYPE_CHECKING` block in services)
- Pattern: Dataclasses for input/output; `cast()` only in CRUD helpers where Odoo returns `Any`
- Used for: Mypy --strict compliance; IDE support

---

*Architecture analysis: 2026-04-10*
