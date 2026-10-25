# Contributing to godoo

## Dev Setup

```bash
git clone https://github.com/godoo-dev/godoo-py.git
cd godoo-py
uv sync --frozen --all-packages --all-extras
uv run pytest packages/ tests/ --import-mode=importlib -m "not integration"  # verify setup
```

## Candidate verification

The CI harmonization uses one candidate built from the selected source revision:

```bash
uv sync --frozen --all-packages --all-extras
./scripts/check.py offline --evidence /absolute/evidence/offline
./scripts/check.py package --artifacts /absolute/candidate --evidence /absolute/evidence/package
./scripts/check.py odoo18 --artifacts /absolute/candidate --evidence /absolute/evidence/odoo18
```

Package proof builds all four wheels, then imports and drives their public APIs
in a noneditable consumer outside the checkout. Odoo proof installs the same
hashed wheels, selects root and package integration suites, observes server major 18 and
checks cleanup. Docker is required; missing Docker, skips and empty selection fail.
The intentionally empty `godoo` distribution stays metadata-only.

Version preparation produces reviewable manifest/changelog changes before final
checks. Manual promotion accepts only a clean immutable SHA on `main`, runs the
full required proof and publishes the exact tested wheels only when `publish`
is explicitly selected. Ordinary validation and docs builds publish nothing.
Hosted branch rules and protected publishing environments require separate setup.

## Running Tests

### Unit Tests (no Docker needed)

```bash
uv run pytest packages/ tests/ --import-mode=importlib -v -m "not integration"
```

### Integration Tests (requires Docker)

```bash
./scripts/check.py odoo18 --artifacts /absolute/candidate --evidence /absolute/proof/odoo18
```

Integration tests spin up real Odoo instances via testcontainers. First run pulls Docker images (~1-2 min), subsequent runs are faster with seed images.

The required command targets Odoo 18. Optional qualification of Odoo 19 requires
successful Odoo 18 proof for the same candidate:

```bash
./scripts/check.py odoo19 --artifacts /absolute/candidate --baseline18 /absolute/proof/odoo18 --evidence /absolute/proof/odoo19
```

## Linting & Type Checking

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy packages/godoo-client/src packages/godoo-testcontainers/src packages/godoo-introspection/src
```

Use checks relevant to the change. Documentation edits need link/import checks and
`git diff --check`; they do not require a Docker test campaign.

## Commit Conventions

We use conventional commits:

- `feat(client): add new service method`
- `fix(testcontainers): handle server restart`
- `docs: update getting started guide`
- `chore: bump dependencies`
- `ci: qualify Odoo 19 after Odoo 18`

## How Integration Tests Work

Tests use `OdooTestContainer` which:

1. Creates a Docker network
2. Starts PostgreSQL (with seed image if available, fresh otherwise)
3. Starts Odoo, waits for ORM readiness (probes `/web/session/authenticate`)
4. Installs requested modules (handles server restarts during install)
5. Returns an authenticated `OdooClient`

The container is session-scoped — one Odoo instance shared across all integration tests.

## Adding a New Service

1. Create `packages/godoo-client/src/godoo/client/services/{name}/`
2. Add four files following the pattern:
   - `types.py` — dataclasses for service types
   - `functions.py` — standalone async functions (take `client` as first arg)
   - `service.py` — service class delegating to functions
   - `__init__.py` — re-export public symbols
3. Add `@cached_property` accessor in `client.py` (lazy import inside the property)
4. Add re-export in `packages/godoo-client/src/godoo/client/__init__.py`
5. Add tests in `packages/godoo-client/tests/test_{name}.py`
6. Add docs page in `docs/services/{name}.md`

See [development](docs/development.md) for the namespace and transport boundaries.
