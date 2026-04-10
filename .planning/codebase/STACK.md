# Technology Stack

**Analysis Date:** 2026-04-10

## Languages

**Primary:**
- Python 3.14 - All package implementation and tooling

## Runtime

**Environment:**
- Python 3.14+ required
- asyncio framework for async/await support

**Package Manager:**
- uv 0.4.0+ (astral-sh/setup-uv)
- Lockfile: `uv.lock` (workspace lockfile)

## Build System

**Build Backend:**
- hatchling - Build backend specified in all packages
  - Configuration: `[build-system]` in each `pyproject.toml`
  - Wheel packages: `src/` layout for all three packages

**Workspace:**
- uv workspace with 3 packages in `packages/*` directory
  - `packages/godoo` → `godoo` (core client + 8 services)
  - `packages/godoo-testcontainers` → `godoo_testcontainers` (Docker test infra)
  - `packages/godoo-introspection` → `godoo_introspection` (schema discovery)

## Frameworks & Core Dependencies

**HTTP Client:**
- httpx 0.27+ - Async HTTP client for JSON-RPC communication
  - Used in: `packages/godoo/src/godoo/rpc/transport.py`
  - AsyncClient pooling and connection management

**Testing:**
- pytest 8+ - Test runner
  - pytest-asyncio 0.24+ - Async test support with auto mode
  - pytest-cov 6+ - Coverage reporting
  - respx 0.22+ - Mock HTTP with httpx (JSON-RPC mocking)
  - Configuration: `.pytest.ini_options` in workspace `pyproject.toml`
  - asyncio_mode: "auto"
  - asyncio_default_fixture_loop_scope: "session"
  - Test markers: integration tests with `-m "not integration"` filtering

**Linting & Type Checking:**
- ruff 0.8+ - Fast Python linter and formatter
  - Configuration: `[tool.ruff]` in workspace `pyproject.toml`
  - Target: Python 3.14
  - Line length: 120
  - Selected rules: E, F, W, I, UP, B, SIM, TCH, RUF

- mypy 1.13+ - Static type checker (strict mode)
  - Configuration: `[tool.mypy]` in workspace `pyproject.toml`
  - strict = true (enforces all strict checks)
  - warn_return_any = true
  - warn_unused_configs = true
  - disallow_untyped_defs = true
  - Override: testcontainers.* modules (ignore missing imports)

**Documentation:**
- mkdocs-material 9+ - Documentation site theme
- mkdocstrings[python] 0.27+ - Python docstring extraction

**Release & Publishing:**
- python-semantic-release 9+ - Semantic versioning & changelog generation
  - Configured in workspace `pyproject.toml` with multi-package support
  - Branch: main (production releases)
  - Commit parser: conventional commits (feat, fix, perf)
  - PyPI publishing via `uv publish --trusted-publishing always`

## Key Runtime Dependencies

**Core Package (`packages/godoo/src`):**
- httpx 0.27+ - Required only dependency for JSON-RPC transport

**Test Infrastructure (`packages/godoo-testcontainers/src`):**
- godoo - Depends on core godoo package
- testcontainers[postgres] 4+ - Docker container orchestration for integration tests
  - Provides: DockerContainer, PostgresContainer, Network, wait_for_logs utilities
  - Usage: `asyncio.to_thread()` for sync API wrapping (see `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`)

**Introspection Package (`packages/godoo-introspection/src`):**
- godoo - Depends on core godoo package

## Configuration Files

**Python Configuration:**
- Workspace root: `pyproject.toml` - Unified workspace config (uv, ruff, mypy, pytest, semantic-release)
- Per-package: `pyproject.toml` in each `packages/{name}/`
  - name, version, description, license (LGPL-3.0-or-later)
  - requires-python: >=3.14
  - authors, classifiers, URLs

**Build Configuration:**
- `pyproject.toml` [build-system] section - hatchling backend
- Wheel packages configured via `[tool.hatch.build.targets.wheel]`

**Code Quality Configuration:**
- Ruff: `[tool.ruff]` with lint rules and formatting
- mypy: `[tool.mypy]` with strict settings
- pytest: `[tool.pytest.ini_options]` with markers and session-scoped event loop
- coverage: `[tool.coverage.run]` and `[tool.coverage.report]`

**Release Configuration:**
- semantic-release: `[tool.semantic_release]` in workspace `pyproject.toml`
- Multi-package version sync via version_toml paths
- GitHub remote integration (GH_TOKEN environment variable)

## Environment Variables

**Client Configuration:**
- `ODOO_URL` - Odoo instance base URL
- `ODOO_DB` / `ODOO_DATABASE` - Target database (aliases)
- `ODOO_USER` / `ODOO_USERNAME` - Username for authentication (aliases)
- `ODOO_PASSWORD` - Password for authentication
- Custom prefix support: `config_from_env(prefix="CUSTOM")` accepts `CUSTOM_URL`, `CUSTOM_DB`, etc.

**Testing:**
- `ODOO_VERSION` - Odoo version for integration tests (defaults to 17.0)
- `ODOO_SEED_IMAGE` - Docker image for pre-seeded Odoo containers (optional)

**Release:**
- `GH_TOKEN` - GitHub token for semantic-release (read from GitHub Actions secrets)

## Platform Requirements

**Development:**
- Python 3.14+
- uv package manager
- Docker (for integration tests via testcontainers)
- Unix-like shell (CI uses bash)

**Production / Distribution:**
- Python 3.14+
- httpx 0.27+
- PyPI repository (automated via GitHub Actions)
- Trusted publishing (OIDC tokens, no stored PyPI token)

---

*Stack analysis: 2026-04-10*
