# CLAUDE.md

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
