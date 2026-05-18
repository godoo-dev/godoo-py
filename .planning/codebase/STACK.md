# Technology Stack

**Analysis Date:** 2026-05-18

## Languages

**Primary:**
- Python 3.14 - All source code across all three packages

## Runtime

**Environment:**
- CPython 3.14 (pinned via `.python-version`)

**Package Manager:**
- uv (workspace mode, `astral-sh/setup-uv@v6` in CI)
- Lockfile: `uv.lock` present and committed

## Frameworks

**Core:**
- `httpx>=0.27` - Async HTTP client for all Odoo JSON-RPC transport (`packages/godoo/src/godoo/rpc/transport.py`)
- asyncio (stdlib) - Concurrency model; all public APIs are `async def`

**Testing:**
- `pytest>=8` - Test runner
- `pytest-asyncio>=0.24` - Async test support (mode: `auto`, session-scoped event loop)
- `pytest-cov>=6` - Coverage reporting
- `respx>=0.22` - Mock HTTP client for httpx (used in unit tests)
- `testcontainers[postgres]>=4` - Docker container orchestration for integration tests (`packages/godoo-testcontainers/`)

**Build/Dev:**
- `hatchling` - Build backend for all three packages
- `ruff>=0.8` - Linter and formatter (line-length 120, selects E, F, W, I, UP, B, SIM, TCH, RUF)
- `mypy>=1.13` - Static type checker (strict mode)
- `python-semantic-release>=9` - Automated versioning and changelog generation
- `mkdocs-material>=9` - Documentation site
- `mkdocstrings[python]>=0.27` - Auto-generated API reference from docstrings

## Key Dependencies

**Critical:**
- `httpx>=0.27` - The sole runtime HTTP dependency; drives all Odoo communication. Any breaking httpx API change breaks the core transport.
- `testcontainers[postgres]>=4` - Has a sync-only API; all calls must be wrapped in `asyncio.to_thread()` (enforced pattern in `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`)

**Infrastructure:**
- `godoo>=0.1.0` - Both `godoo-testcontainers` and `godoo-introspection` depend on the core `godoo` package (workspace dependency)

## Configuration

**Environment:**
- Runtime config via `config_from_env()` in `packages/godoo/src/godoo/config.py`
- Required env vars (configurable prefix, default `ODOO`):
  - `ODOO_URL` — Odoo instance base URL
  - `ODOO_DB` (or `ODOO_DATABASE`) — database name
  - `ODOO_USER` (or `ODOO_USERNAME`) — login username
  - `ODOO_PASSWORD` — login password
- Integration test env var: `ODOO_VERSION` (e.g., `"17.0"`, `"18.0"`, `"19.0"`)
- Optional seed image env var: `ODOO_SEED_IMAGE` (Docker image with pre-seeded Odoo DB)

**Build:**
- Root `pyproject.toml` — workspace config, shared tool settings (ruff, mypy, pytest, coverage, semantic-release)
- `packages/godoo/pyproject.toml` — package metadata, `hatchling` build target
- `packages/godoo-testcontainers/pyproject.toml` — package metadata, `hatchling` build target
- `packages/godoo-introspection/pyproject.toml` — package metadata, `hatchling` build target

## Platform Requirements

**Development:**
- Python 3.14
- uv installed
- Docker (for integration tests only)

**Production:**
- Python >=3.14 (all packages enforce `requires-python = ">=3.14"`)
- Deployed as PyPI library packages, not a server process

---

*Stack analysis: 2026-05-18*
