# External Integrations

**Analysis Date:** 2026-04-10

## APIs & External Services

**Odoo JSON-RPC API:**
- Service: Odoo ERP instances (Odoo 17, 18, 19)
- What it's used for: Core client interaction with Odoo via JSON-RPC protocol
  - SDK: httpx AsyncClient
  - Endpoint: `/jsonrpc` on Odoo base URL
  - Methods: JSON-RPC 2.0 protocol with `call` method
  - Transport: `packages/godoo/src/godoo/rpc/transport.py` (JsonRpcTransport class)
  - Authentication: `common.authenticate` RPC method with uid-based session
  - Session handling: OdooSessionInfo with session_id, uid, database tracking

**Odoo Models via JSON-RPC:**
- Methods used:
  - `common.authenticate` - Credentials validation
  - `object.execute` - Model CRUD operations (search, read, write, create, unlink, etc.)
  - Domain filters: Odoo standard domain syntax `[["field", "operator", "value"]]`
  - Field access: Model field reads/writes with type preservation

## Data Storage

**Databases:**
- PostgreSQL (via testcontainers for integration testing)
  - Connection: Managed by `testcontainers[postgres]` package
  - Client: DockerContainer wrapping PostgreSQL 
  - Usage: `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` starts PostgreSQL containers
  - Network: Docker network created per test container for Odoo ↔ PostgreSQL communication
  - Credentials: Configurable (default: user=admin, password=admin)

**Odoo Database:**
- Type: PostgreSQL database hosted on Odoo instance
- Connection string: Built from environment variables (ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
- Schema: Managed by Odoo, discovery via `godoo_introspection` package (placeholder)
- Access: Read-write via JSON-RPC authenticated sessions

**File Storage:**
- Local filesystem only
- Configuration files: `docker/seed-config.json` (optional, for testcontainers seed images)

**Caching:**
- None configured - direct HTTP requests to Odoo per call

## Authentication & Identity

**Auth Provider:**
- Custom implementation (Odoo username/password)
  - Implementation: `packages/godoo/src/godoo/rpc/transport.py` (`authenticate()` method)
  - Credentials: Username + password sent to `common.authenticate` RPC
  - Session token: UUID-based session_id generated after successful auth (stored in OdooSessionInfo)
  - Token lifetime: Session-based (user manages logout)
  - Env config: `packages/godoo/src/godoo/config.py` reads ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD

**Safety Guards:**
- Custom safety context for mutation protection
  - Location: `packages/godoo/src/godoo/safety/` module
  - READ operations: Always allowed
  - WRITE/DELETE operations: Optional confirmation check via SafetyContext
  - Implementation: Async callback interface for user confirmation
  - Error: OdooSafetyError raised if operation denied

## Monitoring & Observability

**Error Tracking:**
- None configured
- Error types: OdooError, OdooRpcError, OdooAuthError, OdooNetworkError, OdooValidationError, OdooAccessError, OdooMissingError, OdooTimeoutError, OdooSafetyError
- JSON serialization: All errors have `.to_json()` method for structured logging

**Logs:**
- Approach: Python standard logging module
  - Logger: `logging.getLogger("godoo.client")`
  - Logger: `logging.getLogger("godoo.client.rpc")`
  - Logger: `logging.getLogger("godoo.testcontainers")`
  - Debug level: JSON-RPC call logging in transport
  - Integration tests: `--log-cli-level=ERROR` in CI

## CI/CD & Deployment

**Hosting:**
- PyPI (Python Package Index)
- Distribution: wheels + source distributions via `uv build`

**CI Pipeline:**
- GitHub Actions
  - Workflows: `.github/workflows/test.yml` (lint, unit, integration), `.github/workflows/release.yml` (semantic-release + publish)
  - Lint job: ruff check, ruff format, mypy on all src directories
  - Unit tests: pytest with coverage upload to Codecov
  - Integration tests: pytest with testcontainers, matrix on ODOO_VERSION [17.0, 18.0, 19.0]
  - Release trigger: Runs on main branch when Test workflow succeeds
  - Publishing: PyPI via `uv publish --trusted-publishing always` (OIDC tokens)

**Test Docker Images:**
- ODOO_VERSION environment variable controls Odoo version
- ODOO_SEED_IMAGE environment variable (optional) for pre-seeded images
- Testcontainers manages Docker lifecycle (start/stop containers)
- PostgreSQL image via testcontainers.postgres.PostgresContainer

## Environment Configuration

**Required env vars:**
- `ODOO_URL` - Odoo instance URL (e.g., http://localhost:8069)
- `ODOO_DB` - Database name
- `ODOO_USER` - Username for auth
- `ODOO_PASSWORD` - Password for auth

**Optional env vars:**
- `ODOO_VERSION` - Odoo version for integration tests (defaults to 17.0)
- `ODOO_SEED_IMAGE` - Pre-seeded Odoo Docker image URI
- `GH_TOKEN` - GitHub token for semantic-release (CI only)

**Configuration approach:**
- Environment-based: `packages/godoo/src/godoo/config.py` exposes `config_from_env(prefix="ODOO")`
- Direct instantiation: OdooClientConfig dataclass for programmatic setup
- Lazy loading: Credentials read at client initialization, not import time

**Secrets location:**
- Environment variables (no .env file handling in SDK)
- GitHub Actions secrets: GH_TOKEN for release workflow
- .env file handling: Application responsibility (not SDK concern)

## Webhooks & Callbacks

**Incoming:**
- None - Client-initiated requests only

**Outgoing:**
- Safety confirmation callbacks: Optional async callback function in SafetyContext
  - Location: `packages/godoo/src/godoo/safety/__init__.py`
  - Signature: `async def confirm(operation: OperationInfo) -> bool`
  - When triggered: Before WRITE/DELETE operations if safety context set
  - Not an HTTP webhook - in-process async callback

## Service Structure

**8 Domain Services via JSON-RPC (lazy-loaded on OdooClient):**
1. Mail - `client.mail` - Post notes/messages on records
2. Modules - `client.modules` - Install/upgrade/uninstall modules
3. Attendance - `client.attendance` - Clock in/out, presence tracking
4. Timesheets - `client.timesheets` - Timer-based and manual time logging
5. Accounting - `client.accounting` - Cash discovery, reconciliation, balance
6. URLs - `client.urls` - Record and portal links (version-agnostic)
7. Properties - `client.properties` - Safe read-merge-write for property fields
8. CDC - `client.cdc` - Change data capture via audit log

Each service: `packages/godoo/src/godoo/services/{name}/`
- `types.py` - Input/output dataclasses
- `functions.py` - Standalone async functions (client as first arg)
- `service.py` - Class delegating to functions
- `__init__.py` - Barrel re-exports

---

*Integration audit: 2026-04-10*
