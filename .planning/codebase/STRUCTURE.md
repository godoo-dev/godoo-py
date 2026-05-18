# Codebase Structure

**Analysis Date:** 2026-05-18

## Directory Layout

```
godoo-py/
├── packages/                          # uv workspace members
│   ├── godoo/                         # Core SDK package (published as `godoo`)
│   │   ├── pyproject.toml
│   │   ├── tests/                     # Unit tests co-located with package
│   │   │   ├── test_client.py
│   │   │   ├── test_transport.py
│   │   │   ├── test_safety.py
│   │   │   ├── test_errors.py
│   │   │   ├── test_config.py
│   │   │   └── test_{service}.py      # One file per service
│   │   └── src/godoo/                 # Importable source root
│   │       ├── __init__.py            # Public API barrel — all re-exports
│   │       ├── client.py              # OdooClient, OdooClientConfig
│   │       ├── config.py              # config_from_env, create_client
│   │       ├── errors.py              # OdooError hierarchy
│   │       ├── rpc/                   # JSON-RPC transport layer
│   │       │   ├── __init__.py
│   │       │   ├── transport.py       # JsonRpcTransport (httpx)
│   │       │   └── types.py           # OdooSessionInfo
│   │       ├── safety/                # Safety guard
│   │       │   └── __init__.py        # SafetyContext, OperationInfo, helpers
│   │       └── services/              # Domain service modules
│   │           ├── __init__.py        # Empty marker
│   │           ├── accounting/        # Reconciliation, cash, move lines
│   │           ├── attendance/        # Check-in/out, hr.attendance
│   │           ├── cdc/               # Change Data Capture (mail.tracking.value)
│   │           ├── mail/              # Post notes/messages
│   │           ├── modules/           # ir.module.module management
│   │           ├── properties/        # Odoo Properties fields (x_*)
│   │           ├── timesheets/        # account.analytic.line timers
│   │           └── urls/              # Portal/backend URL builders
│   ├── godoo-testcontainers/          # Docker test infra package
│   │   ├── pyproject.toml
│   │   ├── tests/                     # Unit tests for testcontainers helpers
│   │   └── src/godoo_testcontainers/
│   │       ├── __init__.py
│   │       ├── container.py           # OdooTestContainer, StartedOdooContainer
│   │       └── seed_resolver.py       # Seed image selection logic
│   └── godoo-introspection/           # Schema discovery (placeholder)
│       ├── pyproject.toml
│       └── src/godoo_introspection/
│           └── __init__.py            # Empty — not yet implemented
├── tests/                             # Workspace-level integration tests
│   ├── conftest.py                    # Session-scoped OdooTestContainer fixture
│   └── integration/
│       ├── test_crud.py
│       └── test_modules.py
├── docker/                            # Docker helpers (seed-config.json lives here)
├── docs/                              # MkDocs source
│   ├── api/
│   ├── guides/
│   └── services/
├── .github/workflows/                 # CI/CD pipeline definitions
├── .planning/codebase/                # GSD codebase maps (this file)
├── pyproject.toml                     # Workspace root: ruff, mypy, pytest, semantic-release config
├── uv.lock                            # Workspace lockfile
└── mkdocs.yml                         # Docs site config
```

## Directory Purposes

**`packages/godoo/src/godoo/`:**
- Purpose: Core SDK — everything a user of `godoo` imports
- Contains: Client, transport, safety, 8 service modules, public `__init__` barrel
- Key files: `client.py`, `config.py`, `errors.py`

**`packages/godoo/src/godoo/services/{name}/`:**
- Purpose: One subdirectory per Odoo domain area
- Contains: Always `types.py`, `functions.py`, `service.py`, `__init__.py`; CDC also has `field_cache.py` and `resolver.py`
- Key files: `functions.py` (all logic lives here), `types.py` (dataclasses for I/O)

**`packages/godoo/src/godoo/rpc/`:**
- Purpose: Wire protocol isolation — nothing above this layer knows about HTTP
- Contains: `transport.py` (JsonRpcTransport), `types.py` (OdooSessionInfo)

**`packages/godoo/src/godoo/safety/`:**
- Purpose: Safety guard: safety level inference, SafetyContext, module-level default
- Contains: Single `__init__.py` (all safety logic inline)

**`packages/godoo-testcontainers/`:**
- Purpose: Published helper for spinning up a live Odoo instance in tests
- Contains: `OdooTestContainer`, `StartedOdooContainer`, `SeedInfo`, seed resolver

**`packages/godoo-introspection/`:**
- Purpose: Placeholder for future schema discovery tooling
- Contains: Empty `__init__.py` only — not implemented

**`tests/`:**
- Purpose: Workspace-level integration tests that require a live Docker Odoo instance
- Contains: `conftest.py` (session fixture), `integration/` (CRUD + module tests)

**`packages/godoo/tests/`:**
- Purpose: Unit tests for the core SDK — run without Docker
- Contains: One `test_{topic}.py` per logical area; mock HTTP via `respx`

**`docker/`:**
- Purpose: Docker seed image config
- Key files: `docker/seed-config.json` (maps Odoo version → seed image + pre-installed modules)

## Key File Locations

**Entry Points:**
- `packages/godoo/src/godoo/__init__.py`: Public API barrel — all public names re-exported here
- `packages/godoo/src/godoo/config.py`: `config_from_env()`, `create_client()` — typical user entry points
- `packages/godoo/src/godoo/client.py`: `OdooClient`, `OdooClientConfig` — core types

**Configuration:**
- `pyproject.toml` (root): ruff, mypy, pytest, semantic-release, coverage settings
- `packages/godoo/pyproject.toml`: Package metadata + dependencies for `godoo`
- `packages/godoo-testcontainers/pyproject.toml`: Package metadata for `godoo_testcontainers`
- `uv.lock`: Workspace lockfile — commit any changes to this file

**Core Logic:**
- `packages/godoo/src/godoo/rpc/transport.py`: All HTTP/JSON-RPC handling
- `packages/godoo/src/godoo/safety/__init__.py`: Safety enforcement rules
- `packages/godoo/src/godoo/errors.py`: Complete error type hierarchy

**Testing:**
- `tests/conftest.py`: Session-scoped `odoo` fixture (Docker container)
- `packages/godoo/tests/`: Unit tests (no Docker needed)
- `packages/godoo-testcontainers/tests/`: Unit tests for seed resolver and container logic

## Naming Conventions

**Files:**
- Service implementation files are always named exactly: `functions.py`, `service.py`, `types.py`, `__init__.py`
- Test files: `test_{topic}.py` (lowercase, underscores) matching their subject module
- Auxiliary service files use descriptive snake_case: `field_cache.py`, `resolver.py`, `seed_resolver.py`

**Directories:**
- Service directories use lowercase with no separators: `accounting`, `attendance`, `cdc`, `mail`, `modules`, `properties`, `timesheets`, `urls`
- Package directories use hyphenated names: `godoo-testcontainers`, `godoo-introspection`
- Python import names use underscores: `godoo_testcontainers`, `godoo_introspection`

**Classes:**
- Service classes: `{Domain}Service` (e.g. `AccountingService`, `CdcService`) — exception is `ModuleManager` (named for its role)
- Config/data classes: `Odoo{Concept}` (e.g. `OdooClient`, `OdooClientConfig`, `OdooSessionInfo`)
- Error classes: `Odoo{Category}Error` (e.g. `OdooAuthError`, `OdooValidationError`)
- Types within a service: plain descriptive names (e.g. `TrackingEvent`, `CashAccount`, `GetFeedOptions`)

**Functions:**
- Standalone service functions: verb-first snake_case (e.g. `discover_cash_accounts`, `get_feed`, `resolve_employee_id`)
- Private helpers: leading underscore (e.g. `_m2o_id`, `_guard`, `_categorize_error`)

## Where to Add New Code

**New Service:**
1. Create `packages/godoo/src/godoo/services/{name}/` directory
2. Add `types.py` — dataclasses for inputs and outputs
3. Add `functions.py` — async functions taking `OdooClient` as first arg; use `if TYPE_CHECKING:` for the import
4. Add `service.py` — class with `__init__(self, client: OdooClient)` and methods that delegate to functions
5. Add `__init__.py` — barrel re-exporting the service class, public types, and standalone functions
6. Wire into `client.py`: add `TYPE_CHECKING` import at top, add `@cached_property` accessor with lazy local import
7. Add to `packages/godoo/src/godoo/__init__.py` `__all__`
8. Add `packages/godoo/tests/test_{name}.py` with unit tests (mock via `respx`)

**New Method on an Existing Service:**
1. Add the async function to `services/{name}/functions.py` (client as first arg)
2. Add a delegating method to `services/{name}/service.py`
3. Export from `services/{name}/__init__.py` if it should be part of the public API

**New Type:**
- Add to `services/{name}/types.py` as a `@dataclass`

**Shared Utility:**
- If utility is domain-specific (e.g. many2one field parsing for accounting): add to `services/{name}/functions.py` as a private helper (`_m2o_id` style)
- If utility is cross-service: there is no shared utils module yet; place in the most relevant service and import from there (see `timesheets/functions.py` importing `attendance/functions.resolve_employee_id`)

**Integration Test:**
- Add to `tests/integration/test_{topic}.py`; use the `client` fixture from `tests/conftest.py`

**Unit Test:**
- Add to `packages/godoo/tests/test_{topic}.py`; mock HTTP calls with `respx`

## Special Directories

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents
- Generated: By `/gsd:map-codebase`
- Committed: Yes

**`docker/`:**
- Purpose: Seed image configuration for testcontainers
- Generated: No — manually maintained
- Committed: Yes
- Key file: `docker/seed-config.json` — maps Odoo version strings to seed Docker image + pre-installed module list; read by `seed_resolver.py`

**`docs/`:**
- Purpose: MkDocs source for published documentation
- Generated: No (source), but `site/` output is not committed
- Committed: Yes (source only)

---

*Structure analysis: 2026-05-18*
