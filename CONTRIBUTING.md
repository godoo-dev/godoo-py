# Contributing to godoo

## Dev Setup

```bash
git clone https://github.com/marcfargas/godoo.git
cd odoopy
uv sync
uv run pytest packages/ -m "not integration"  # verify setup
```

## Running Tests

### Unit Tests (no Docker needed)

```bash
uv run pytest packages/ -v -m "not integration"
```

### Integration Tests (requires Docker)

```bash
uv run pytest -m integration -v
```

Integration tests spin up real Odoo instances via testcontainers. First run pulls Docker images (~1-2 min), subsequent runs are faster with seed images.

Set `ODOO_VERSION` to test against a specific version (default: 17.0):

```bash
ODOO_VERSION=18.0 uv run pytest -m integration -v
```

## Linting & Type Checking

```bash
uv run ruff check .
uv run ruff format .
uv run mypy packages/godoo/src packages/godoo-testcontainers/src
```

All three must pass before committing.

## Commit Conventions

We use conventional commits:

- `feat(client): add new service method`
- `fix(testcontainers): handle server restart`
- `docs: update getting started guide`
- `chore: bump dependencies`
- `ci: add Odoo 19 to matrix`

## How Integration Tests Work

Tests use `OdooTestContainer` which:

1. Creates a Docker network
2. Starts PostgreSQL (with seed image if available, fresh otherwise)
3. Starts Odoo, waits for ORM readiness (probes `/web/session/authenticate`)
4. Installs requested modules (handles server restarts during install)
5. Returns an authenticated `OdooClient`

The container is session-scoped — one Odoo instance shared across all integration tests.

## Adding a New Service

1. Create `packages/godoo/src/godoo/services/{name}/`
2. Add four files following the pattern:
   - `types.py` — dataclasses for service types
   - `functions.py` — standalone async functions (take `client` as first arg)
   - `service.py` — service class delegating to functions
   - `__init__.py` — re-export public symbols
3. Add `@cached_property` accessor in `client.py` (lazy import inside the property)
4. Add re-export in `packages/godoo/src/godoo/__init__.py`
5. Add tests in `packages/godoo/tests/test_{name}.py`
6. Add docs page in `docs/services/{name}.md`
