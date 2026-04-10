# Codebase Structure

**Analysis Date:** 2026-04-10

## Directory Layout

```
godoo/
├── packages/
│   ├── godoo/                          # Core async Odoo client + 8 services
│   │   ├── src/godoo/
│   │   │   ├── __init__.py             # Public API exports
│   │   │   ├── client.py               # OdooClient main class
│   │   │   ├── config.py               # Environment setup helpers
│   │   │   ├── errors.py               # Exception hierarchy
│   │   │   ├── rpc/
│   │   │   │   ├── __init__.py         # RPC package exports
│   │   │   │   ├── transport.py        # JsonRpcTransport (httpx wrapper)
│   │   │   │   └── types.py            # OdooSessionInfo dataclass
│   │   │   ├── safety/
│   │   │   │   └── __init__.py         # Safety guard (OperationInfo, SafetyContext, levels)
│   │   │   └── services/
│   │   │       ├── __init__.py         # Empty (services are lazily loaded)
│   │   │       ├── accounting/         # Accounting operations (reconcile, cash accounts, etc.)
│   │   │       ├── attendance/         # Attendance tracking (check-in/out)
│   │   │       ├── cdc/                # Change Data Capture (audit trail, feed)
│   │   │       ├── mail/               # Message posting (internal notes, open messages)
│   │   │       ├── modules/            # Module upgrade/downgrade management
│   │   │       ├── properties/         # Property/settings management
│   │   │       ├── timesheets/         # Timesheet operations (hours, validation)
│   │   │       └── urls/               # URL generation (signed document links)
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── conftest.py             # Pytest fixtures and markers
│   │   │   ├── test_*.py               # Unit tests (mocked with respx)
│   │   │   └── integration/
│   │   │       ├── __init__.py
│   │   │       └── test_*.py           # Integration tests (Docker-based, marked with @pytest.mark.integration)
│   │   └── pyproject.toml              # godoo package metadata (version, deps)
│   ├── godoo-testcontainers/           # Docker test infrastructure (Odoo container helpers)
│   │   ├── src/godoo_testcontainers/
│   │   │   ├── __init__.py
│   │   │   ├── container.py            # Testcontainers for Odoo (start/stop/wait)
│   │   │   └── seed_resolver.py        # Test data loading
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── godoo-introspection/            # Schema discovery (placeholder, TBD)
│       ├── src/godoo_introspection/
│       │   └── __init__.py             # Empty
│       └── pyproject.toml
├── tests/                              # Workspace-level integration tests
│   ├── __init__.py
│   ├── conftest.py                     # Shared fixtures
│   └── integration/
│       ├── __init__.py
│       ├── test_crud.py                # CRUD operations (search, read, write, unlink)
│       └── test_modules.py             # Module operations
├── docker/                             # Docker support files (compose, build scripts)
├── docs/                               # mkdocs documentation
├── .planning/                          # GSD planning artifacts (auto-generated)
├── .github/                            # GitHub Actions CI/CD
├── pyproject.toml                      # Workspace root (uv config, shared dev dependencies)
├── uv.lock                             # Workspace lockfile
├── README.md
├── CHANGELOG.md
├── CLAUDE.md                           # Project conventions and patterns
└── LICENSE                             # LGPL-3.0-or-later
```

## Directory Purposes

**`packages/godoo/src/godoo/`:**
- Purpose: Core async Odoo JSON-RPC client with domain services
- Contains: Application entry point, transport layer, service tier, error handling, safety guard
- Key files: `client.py` (main API), `rpc/transport.py` (wire protocol)

**`packages/godoo/src/godoo/services/`:**
- Purpose: Domain-specific business logic, organized by feature area
- Contains: 8 service modules (accounting, attendance, cdc, mail, modules, properties, timesheets, urls)
- Pattern: Each service has `types.py`, `functions.py`, `service.py`, `__init__.py`

**`packages/godoo/src/godoo/rpc/`:**
- Purpose: JSON-RPC protocol and session management
- Contains: httpx-backed async transport, session state, error classification
- Key files: `transport.py` (main implementation), `types.py` (OdooSessionInfo)

**`packages/godoo/src/godoo/safety/`:**
- Purpose: Operation confirmation guard for write/delete operations
- Contains: SafetyContext (async callback), OperationInfo (descriptor), safety level inference
- Key files: `__init__.py` (all logic in one module)

**`packages/godoo/tests/`:**
- Purpose: Unit and integration tests for core client
- Contains: Test files mirroring service names, conftest for fixtures, integration/ subdir for Docker-based tests
- Pattern: Unit tests use respx to mock HTTP; integration tests use testcontainers

**`packages/godoo-testcontainers/src/`:**
- Purpose: Docker container management for integration testing
- Contains: Testcontainers wrapper for Odoo image, seed data resolution
- Key files: `container.py` (start/stop/wait), `seed_resolver.py` (fixtures)

**`tests/` (workspace-level):**
- Purpose: Integration tests requiring full stack (Odoo + godoo client)
- Contains: CRUD, module operation tests
- Pattern: Marked with `@pytest.mark.integration`; requires Docker running

**`docs/`:**
- Purpose: mkdocs-material documentation site
- Contains: API reference (auto-generated from docstrings), guides, examples
- Built via: `mkdocs build`

## Key File Locations

**Entry Points:**

- `packages/godoo/src/godoo/__init__.py`: Public API (imports OdooClient, services, errors)
- `packages/godoo/src/godoo/client.py`: Main OdooClient class; user imports and interact with this
- `packages/godoo/src/godoo/config.py`: Bootstrap functions (`config_from_env()`, `create_client()`)

**Configuration:**

- `pyproject.toml` (root): Workspace config, tool settings (ruff, mypy, pytest, semantic-release)
- `pyproject.toml` (each package): Package version, metadata, dependencies
- `packages/godoo/src/godoo/config.py`: Env var reading (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)

**Core Logic:**

- `packages/godoo/src/godoo/client.py`: OdooClient with CRUD helpers, service accessors, safety guard
- `packages/godoo/src/godoo/rpc/transport.py`: JSON-RPC POST, session management, error classification
- `packages/godoo/src/godoo/services/{name}/functions.py`: Standalone async business logic (e.g., `post_internal_note`, `trace_reconciliation`)
- `packages/godoo/src/godoo/services/{name}/service.py`: Service class delegating to functions
- `packages/godoo/src/godoo/services/{name}/types.py`: Input/output dataclasses

**Testing:**

- `packages/godoo/tests/conftest.py`: Pytest fixtures (e.g., `auth_client`, `_make_client()`)
- `packages/godoo/tests/test_*.py`: Unit tests with respx mocks (one file per service, e.g., `test_mail.py`)
- `packages/godoo/tests/integration/test_*.py`: Integration tests requiring Docker
- `tests/integration/test_crud.py`: Workspace-level CRUD integration tests
- `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`: Testcontainers Odoo instance

**Error Handling:**

- `packages/godoo/src/godoo/errors.py`: Exception hierarchy and classification

**Safety:**

- `packages/godoo/src/godoo/safety/__init__.py`: SafetyContext, OperationInfo, safety level inference

## Naming Conventions

**Files:**

- `client.py`: Main class definition (one class per file, file name is snake_case)
- `types.py`: Dataclass definitions (input/output contracts)
- `functions.py`: Standalone async functions (business logic, testable)
- `service.py`: Service class (delegates to functions)
- `__init__.py`: Barrel re-exports (all public symbols)
- `conftest.py`: Pytest fixtures and configuration
- `test_*.py`: Test modules (one module per tested component)

**Directories:**

- `services/{name}/`: Service module (lowercase, matches Odoo domain name: `mail`, `accounting`, `modules`)
- `rpc/`: Low-level RPC transport
- `safety/`: Operation guard
- `tests/`: Co-located with src/ in same package
- `integration/`: Subdirectory of tests/ for Docker-based tests

**Functions:**

- `async def {action}_{entity}(...)`: Pattern for service functions
  - Examples: `post_internal_note()`, `trace_reconciliation()`, `discover_cash_accounts()`
  - First arg always `client: OdooClient`
  - Returns typed result (not `Any`)

**Classes:**

- `{Domain}Service`: Service class (e.g., `MailService`, `AccountingService`, `CdcService`)
- `{Entity}{Descriptor}`: Types (e.g., `PostMessageOptions`, `CashAccount`, `TrackingEvent`)
- `OdooClient`: Main client class
- `JsonRpcTransport`: Transport implementation

**Variables and Parameters:**

- `client: OdooClient`: Always passed to functions
- `model: str`: Odoo model name (e.g., "res.partner", "sale.order")
- `res_id: int` or `ids: list[int]`: Record ID(s)
- `domain: list[Any]`: Odoo search domain

## Where to Add New Code

**New Service (e.g., HRM):**

1. Create directory: `packages/godoo/src/godoo/services/hrm/`
2. Create files:
   - `types.py`: Input/output dataclasses
   - `functions.py`: Async functions with `client` as first arg
   - `service.py`: Class with methods delegating to functions
   - `__init__.py`: Barrel re-exports
3. Import service class in `packages/godoo/src/godoo/client.py` under `if TYPE_CHECKING`
4. Add cached property to `OdooClient`:
   ```python
   @cached_property
   def hrm(self) -> HrmService:
       from godoo.services.hrm.service import HrmService
       return HrmService(self)
   ```
5. Add to public exports in `packages/godoo/src/godoo/__init__.py`
6. Create `packages/godoo/tests/test_hrm.py` with unit tests (respx mocks)
7. Add integration tests in `packages/godoo/tests/integration/` if needed

**New Function in Existing Service:**

1. Add function signature and implementation to `packages/godoo/src/godoo/services/{name}/functions.py`
2. Add types to `packages/godoo/src/godoo/services/{name}/types.py` if needed
3. Add method to service class in `packages/godoo/src/godoo/services/{name}/service.py`
4. Add to `__all__` in `packages/godoo/src/godoo/services/{name}/__init__.py`
5. Add tests to `packages/godoo/tests/test_{name}.py`

**New CRUD Helper on OdooClient:**

1. Add async method to `OdooClient` class in `packages/godoo/src/godoo/client.py`
2. Implement using existing `client.call()` + `cast()` for type hints
3. Add tests to `packages/godoo/tests/test_client.py`

**Utility or Shared Function:**

- If used by multiple services: Add to appropriate service's `functions.py` and re-export in `__init__.py`
- If shared across services: Consider creating `packages/godoo/src/godoo/utils/` directory with modules like `validation.py`, `formatting.py`

## Special Directories

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents (auto-generated)
- Generated: Yes
- Committed: Yes
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**`dist/`:**
- Purpose: Built distribution packages (wheels, sdists)
- Generated: Yes (`uv build`)
- Committed: No (in .gitignore)

**`.venv/`:**
- Purpose: Virtual environment (if using venv instead of uv workspace)
- Generated: Yes
- Committed: No

**`.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`:**
- Purpose: Tool caches
- Generated: Yes
- Committed: No

**`docker/`:**
- Purpose: Docker configurations (docker-compose, Odoo image config)
- Generated: No
- Committed: Yes
- Used for: Local development and CI integration tests

---

*Structure analysis: 2026-04-10*
