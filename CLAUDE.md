# CLAUDE.md

@../godoo-hq/UMBRELLA_CLAUDE.md

## Project

godoo — Async Python SDK for Odoo JSON-RPC. LGPL-3.0-or-later.

## Structure

uv workspace with 3 packages:
- `packages/godoo` → `godoo` (core client + 8 services)
- `packages/godoo-testcontainers` → `godoo_testcontainers` (Docker test infra)
- `packages/godoo-introspection` → `godoo_introspection` (schema discovery, placeholder)

## Conventions

- Python 3.14, hatchling build backend
- `from __future__ import annotations` in every file
- `TYPE_CHECKING` for `OdooClient` imports in services (prevents circular imports)
- Dataclasses for types, not Pydantic
- All service functions are async

## Linting & Types

- ruff: line-length 120, select `[E, F, W, I, UP, B, SIM, TCH, RUF]`
- mypy --strict on all `src/` directories
- Run: `uv run ruff check . && uv run ruff format . && uv run mypy packages/godoo/src packages/godoo-testcontainers/src`

## Testing

- pytest-asyncio with `asyncio_mode = "auto"`, session-scoped event loop
- Unit tests: `uv run pytest packages/ -m "not integration"`
- Integration tests: `uv run pytest -m integration` (requires Docker)
- Mock HTTP with `respx`

## Service Pattern

Each service lives in `services/{name}/` with:
1. `types.py` — dataclasses for inputs/outputs
2. `functions.py` — standalone async functions (client as first arg)
3. `service.py` — class delegating to functions
4. `__init__.py` — barrel re-exports

Wire into `client.py` with `@cached_property` using lazy imports.

## Testcontainers

testcontainers-python has a SYNC API. All calls (`.start()`, `wait_for_logs()`) must be wrapped in `asyncio.to_thread()`.

## Git

- Conventional commits: feat, fix, chore, ci, docs (with scope in parens)
- Never commit `docs/superpowers/`
- develop branch for work, main for clean merges

<!-- GSD:project-start source:PROJECT.md -->
## Project

**godoo-py**

godoo-py is the Python monorepo for the godoo library family — the Python member of
the godoo / Odoo Atlas initiative. It ships three packages: `godoo` (an async Odoo
JSON-RPC client), `godoo-introspection` (live-schema discovery and typed code
generation), and `godoo-testcontainers` (Docker-based Odoo test infrastructure). It is
a public LGPL-3.0 library for Python developers automating or testing Odoo instances.

**Core Value:** The Python family member reaches feature parity with the TypeScript core-3 libraries —
a Python developer gets the same client, introspection, and testcontainers capabilities
that godoo-ts already ships.

### Constraints

- **Tech stack**: Python 3.14, uv workspace, hatchling, httpx — established; not changing
- **Conventions**: `from __future__ import annotations` everywhere, `TYPE_CHECKING` imports for `OdooClient` in services, dataclasses (not Pydantic), all service functions async — established patterns
- **Service pattern**: each service is a `types.py`/`functions.py`/`service.py`/`__init__.py` quad, wired into `client.py` via lazy `@cached_property`
- **Licensing**: LGPL-3.0-or-later (public library)
- **Quality gate**: ruff (line-length 120) + `mypy --strict` on all `src/`; pytest-asyncio `asyncio_mode = auto`
- **Umbrella-aware**: `CLAUDE.md` `@`-imports `../godoo-hq/UMBRELLA_CLAUDE.md`
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.14 - All source code across all three packages
## Runtime
- CPython 3.14 (pinned via `.python-version`)
- uv (workspace mode, `astral-sh/setup-uv@v6` in CI)
- Lockfile: `uv.lock` present and committed
## Frameworks
- `httpx>=0.27` - Async HTTP client for all Odoo JSON-RPC transport (`packages/godoo/src/godoo/rpc/transport.py`)
- asyncio (stdlib) - Concurrency model; all public APIs are `async def`
- `pytest>=8` - Test runner
- `pytest-asyncio>=0.24` - Async test support (mode: `auto`, session-scoped event loop)
- `pytest-cov>=6` - Coverage reporting
- `respx>=0.22` - Mock HTTP client for httpx (used in unit tests)
- `testcontainers[postgres]>=4` - Docker container orchestration for integration tests (`packages/godoo-testcontainers/`)
- `hatchling` - Build backend for all three packages
- `ruff>=0.8` - Linter and formatter (line-length 120, selects E, F, W, I, UP, B, SIM, TCH, RUF)
- `mypy>=1.13` - Static type checker (strict mode)
- `python-semantic-release>=9` - Automated versioning and changelog generation
- `mkdocs-material>=9` - Documentation site
- `mkdocstrings[python]>=0.27` - Auto-generated API reference from docstrings
## Key Dependencies
- `httpx>=0.27` - The sole runtime HTTP dependency; drives all Odoo communication. Any breaking httpx API change breaks the core transport.
- `testcontainers[postgres]>=4` - Has a sync-only API; all calls must be wrapped in `asyncio.to_thread()` (enforced pattern in `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`)
- `godoo>=0.1.0` - Both `godoo-testcontainers` and `godoo-introspection` depend on the core `godoo` package (workspace dependency)
## Configuration
- Runtime config via `config_from_env()` in `packages/godoo/src/godoo/config.py`
- Required env vars (configurable prefix, default `ODOO`):
- Integration test env var: `ODOO_VERSION` (e.g., `"17.0"`, `"18.0"`, `"19.0"`)
- Optional seed image env var: `ODOO_SEED_IMAGE` (Docker image with pre-seeded Odoo DB)
- Root `pyproject.toml` — workspace config, shared tool settings (ruff, mypy, pytest, coverage, semantic-release)
- `packages/godoo/pyproject.toml` — package metadata, `hatchling` build target
- `packages/godoo-testcontainers/pyproject.toml` — package metadata, `hatchling` build target
- `packages/godoo-introspection/pyproject.toml` — package metadata, `hatchling` build target
## Platform Requirements
- Python 3.14
- uv installed
- Docker (for integration tests only)
- Python >=3.14 (all packages enforce `requires-python = ">=3.14"`)
- Deployed as PyPI library packages, not a server process
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Snake_case module names: `transport.py`, `field_cache.py`, `seed_resolver.py`
- Service directories match the service concept: `accounting/`, `timesheets/`, `cdc/`
- Test files prefixed with `test_`: `test_client.py`, `test_accounting.py`
- Internal helpers prefixed with underscore: `_m2o_id`, `_m2o_name`, `_base_url_cache`
- PascalCase: `OdooClient`, `JsonRpcTransport`, `AccountingService`, `SafetyContext`
- Error classes follow `Odoo<Concept>Error` pattern: `OdooRpcError`, `OdooAuthError`, `OdooSafetyError`
- Dataclass names are noun phrases describing the concept: `OdooClientConfig`, `StartedOdooContainer`, `TrackingEvent`
- Snake_case: `discover_cash_accounts`, `trace_reconciliation`, `resolve_partner_from_move`
- Async functions follow verb-noun pattern: `get_history`, `get_feed`, `calculate_days_to_pay`
- Boolean predicates are plain: `is_authenticated`, `is_module_installed`, `is_closing_entry`
- Private helpers prefixed with underscore: `_categorize_error`, `_effective_safety`, `_guard`, `_m2o_id`
- Snake_case throughout
- Module-level constants in SCREAMING_SNAKE: `READ_METHODS`, `DELETE_METHODS`, `_TRACKING_FIELDS`
- Sentinels named `_UNDEFINED` (prefixed underscore for module-private)
- `Literal` types named descriptively: `SafetyLevel = Literal["READ", "WRITE", "DELETE"]`
- Type aliases at module level in `types.py` files
- `frozenset` for immutable method sets
## Code Style
- Tool: `ruff format`
- Line length: 120 characters (configured in root `pyproject.toml`)
- Target version: Python 3.14
- Tool: `ruff check` with rules `["E", "F", "W", "I", "UP", "B", "SIM", "TCH", "RUF"]`
- `mypy --strict` on all `src/` directories
- `warn_return_any = true`, `disallow_untyped_defs = true`
## Import Organization
- Used in every service file and `client.py` to prevent circular imports
- `OdooClient` is always imported under `TYPE_CHECKING` in service files
- Service classes are imported under `TYPE_CHECKING` in `client.py`
## Error Handling
- `OdooSafetyError` inherits directly from `OdooError` (NOT `OdooRpcError`, it is local-only).
- `OdooNetworkError` → `OdooTimeoutError` (network sub-hierarchy).
- Raise typed exceptions from the lowest layer (`transport.py` categorises RPC errors)
- Use `cause=exc` kwarg + `self.__cause__ = cause` chain to preserve original exception
- Every error class implements `to_json() -> dict[str, Any]` for serialisation
- Local validation raises `OdooValidationError` before any RPC call (e.g., `log_time` validates hours > 0)
## Logging
- Logger per module with `logging.getLogger("godoo.client")` or `logging.getLogger("godoo.client.rpc")`
- `logger.debug(...)` for low-level RPC calls: `logger.debug("JSON-RPC call: method=%s", method)`
- `logger.info(...)` for lifecycle events in testcontainers: `logger.info("Odoo ready (attempt %d)", i + 1)`
- `logger.error(...)` for failure details: `logger.error("Odoo container logs:\n%s", logs[-3000:])`
- Use `%s`-style format strings (not f-strings) in log calls
## Comments
- Module docstrings describing purpose: `"""JSON-RPC transport over httpx."""`
- Function docstrings for public API functions (one-liners or brief paragraphs)
- Inline comments for non-obvious behaviour: sentinel semantics, heuristics
- Section separators using dashes: `# ------------------------------------------------------------------`
## Function Design
- `client: OdooClient` is always the first positional argument in standalone functions
- Optional config objects use dedicated dataclasses (`GetHistoryOptions`, `LogTimeOptions`) rather than many keyword args
- Keyword-only arguments enforced with `*` for clarity: `search_read(..., *, fields=None, limit=None, ...)`
- `None` defaults for optional collections — never mutable defaults
- Typed with `cast()` at the `client.call()` level for JSON-RPC returns
- Return typed dataclasses or primitives — never raw `dict` from service functions
- Async generators use `AsyncIterator[T]` return type
## Module Design
- Every `__init__.py` defines `__all__` explicitly: `packages/godoo/src/godoo/__init__.py`
- Service `__init__.py` barrel-exports both the service class, all functions, and all types
- `client.py` imports service classes inside `@cached_property` bodies (lazy imports)
- Services import `OdooClient` only under `TYPE_CHECKING`
- Preferred over Pydantic for all types
- `field(default_factory=list)` for mutable defaults
- `field(default=None, repr=False)` for sensitive/large fields
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
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
- Every service exposes two equivalent APIs: standalone functions (take `client` as first arg) and a class wrapper that closes over `self._client`. Callers may use either.
- The `OdooClient` layer is the only integration point. Services never import the transport directly; they call `client.search_read()`, `client.write()`, etc.
- Safety is a cross-cutting middleware injected at the `call()` boundary in `OdooClient`. Services are unaware of it.
- Service classes are instantiated lazily via `@cached_property` to avoid circular imports at module load time.
- Transport errors are categorized at the lowest layer (`JsonRpcTransport._categorize_error`) and surface as typed subclasses of `OdooRpcError`.
## Layers
- Purpose: HTTP wire protocol — POST to `/jsonrpc`, parse response, raise typed exceptions
- Location: `packages/godoo/src/godoo/rpc/`
- Contains: `JsonRpcTransport`, `OdooSessionInfo`
- Depends on: `httpx`, `godoo.errors`
- Used by: `OdooClient` only
- Purpose: Auth lifecycle, safety guard, CRUD convenience helpers, service registry
- Location: `packages/godoo/src/godoo/client.py`, `packages/godoo/src/godoo/safety/__init__.py`
- Contains: `OdooClient`, `OdooClientConfig`, `SafetyContext`, `OperationInfo`, `infer_safety_level`
- Depends on: `rpc/transport.py`, `safety/`, `errors.py`
- Used by: all callers; services call back into `OdooClient`
- Purpose: Domain-specific operations against Odoo models
- Location: `packages/godoo/src/godoo/services/{name}/`
- Contains: `functions.py` (business logic), `service.py` (class wrapper), `types.py` (dataclasses)
- Depends on: `OdooClient` (via TYPE_CHECKING import to avoid circular), peer service functions when composing (e.g. `timesheets.functions` imports `attendance.functions.resolve_employee_id`)
- Used by: user code via `client.{service_name}`
- Purpose: Environment-variable bootstrapping
- Location: `packages/godoo/src/godoo/config.py`
- Contains: `config_from_env`, `create_client`
- Depends on: `OdooClient`, `OdooClientConfig`
- Used by: top-level user entry points
- Purpose: Docker-based live Odoo instance for integration tests
- Location: `packages/godoo-testcontainers/src/godoo_testcontainers/`
- Contains: `OdooTestContainer`, `StartedOdooContainer`, `SeedInfo`, seed resolver
- Depends on: `godoo` (core package), `testcontainers`, `httpx`
- Used by: `tests/conftest.py` session fixture
## Data Flow
### Primary Request Path
### Service Delegation Flow
### CDC Feed Flow (async generator pattern)
- `OdooClient` holds mutable `_safety_context` (sentinel `_UNDEFINED` / `None` / `SafetyContext`)
- `JsonRpcTransport` holds `_session: OdooSessionInfo | None` and `_password: str | None`
- CDC `field_cache.py` holds a module-level `_cache: dict[str, FieldMeta]` dict — process-global, not client-scoped
- URL service `functions.py` holds a module-level `_base_url_cache: dict[int, str]` keyed by `id(client)`
- No other global mutable state; services are stateless
## Key Abstractions
- Purpose: Single entry point for all Odoo interactions; abstracts transport + safety + service registry
- Examples: `packages/godoo/src/godoo/client.py`
- Pattern: Facade + service locator via `@cached_property`
- Purpose: Separates business logic (functions) from object API (service class) from data shapes (types)
- Examples: `packages/godoo/src/godoo/services/accounting/`, `packages/godoo/src/godoo/services/cdc/`
- Pattern: Functions-first with class wrapper; functions are independently callable for testing
- Purpose: Pluggable async gate for write/delete operations; callers inject a `confirm` callback
- Examples: `packages/godoo/src/godoo/safety/__init__.py`
- Pattern: Dataclass wrapping an async callable; module-level default + per-client override
- Purpose: Typed exception tree from HTTP errors down to ACL/validation/missing errors
- Examples: `packages/godoo/src/godoo/errors.py`
- Pattern: `OdooError` → `OdooRpcError` → {Auth, Network, Timeout, Validation, Access, Missing}; plus `OdooSafetyError` (local, not from RPC)
## Entry Points
- Location: `packages/godoo/src/godoo/config.py`
- Triggers: User code startup; reads env vars
- Responsibilities: Build config, construct client, authenticate, return ready client
- Location: `packages/godoo/src/godoo/client.py`
- Triggers: Direct instantiation when caller has explicit config
- Responsibilities: Construct transport, hold config; `authenticate()` performs JSON-RPC auth
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
### Importing OdooClient at module level in services
### Using sync testcontainers calls in async tests
## Error Handling
- `JsonRpcTransport._categorize_error()` maps Odoo's `exception_type` / `data.name` strings to typed `OdooRpcError` subclasses (`packages/godoo/src/godoo/rpc/transport.py:136`)
- `OdooClient._guard()` raises `OdooSafetyError` (a local, non-RPC error) when a safety callback returns `False`
- Services raise `OdooValidationError` for domain-level precondition failures (e.g. employee not found in `attendance/functions.py`)
- All error classes expose `.to_json()` for structured serialization
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
