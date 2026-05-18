# External Integrations

**Analysis Date:** 2026-05-18

## APIs & External Services

**Odoo JSON-RPC:**
- Odoo (any instance, versions 17.0 / 18.0 / 19.0 tested in CI) — the sole external service this SDK wraps
  - SDK/Client: `httpx.AsyncClient` (owned by `JsonRpcTransport` in `packages/godoo/src/godoo/rpc/transport.py`)
  - Auth: Username + password passed to Odoo's `/jsonrpc` common.authenticate endpoint; session UID held in-memory as `OdooSessionInfo`
  - Endpoints consumed:
    - `POST /jsonrpc` — all RPC calls (service `common`, `object`)
    - `POST /web/session/authenticate` — readiness probe in testcontainers (`packages/godoo-testcontainers/src/godoo_testcontainers/container.py`)

## Data Storage

**Databases:**
- PostgreSQL — managed by Odoo internally; not accessed directly by this SDK
  - For integration tests: `postgres:15-alpine` Docker image via `testcontainers[postgres]`
  - Seed DB variant: custom Docker image specified by `ODOO_SEED_IMAGE` env var containing a pre-initialized Postgres dump

**File Storage:**
- Local filesystem only — `docker/seed-config.json` read from working directory for seed image configuration (`packages/godoo-testcontainers/src/godoo_testcontainers/seed_resolver.py`)

**Caching:**
- None (no Redis, Memcached, or in-process cache beyond `functools.cached_property` on service accessors in `packages/godoo/src/godoo/client.py`)

## Authentication & Identity

**Auth Provider:**
- Odoo native authentication — username/password sent via JSON-RPC common.authenticate
  - Implementation: `JsonRpcTransport.authenticate()` in `packages/godoo/src/godoo/rpc/transport.py`
  - Session: UID + password stored in-memory on the transport; re-sent on every `execute_kw` call (Odoo stateless RPC pattern)
  - No OAuth, no API key, no token refresh — raw credential pair per connection

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, or similar)

**Logs:**
- Python stdlib `logging` module
  - Logger `godoo.client` in `packages/godoo/src/godoo/client.py`
  - Logger `godoo.client.rpc` in `packages/godoo/src/godoo/rpc/transport.py`
  - Logger `godoo.testcontainers` in `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`
  - Log level `ERROR` used for integration test CI runs (set via `--log-cli-level=ERROR` in `.github/workflows/test.yml`)

## CI/CD & Deployment

**Hosting:**
- PyPI — packages published via `uv publish --trusted-publishing always` (OIDC, no stored token)
- Documentation — GitHub Pages, published by `peaceiris/actions-gh-pages@v4` to the `gh-pages` branch; served at `https://www.marcfargas.com/~godoo/`

**CI Pipeline:**
- GitHub Actions (`.github/workflows/`)
  - `test.yml` — lint + unit tests on push to `main`/`develop`; integration tests (matrix: Odoo 17.0, 18.0, 19.0) after lint/unit pass
  - `release.yml` — triggers after `Test` workflow succeeds on `main`; runs `python-semantic-release` then publishes to PyPI
  - `docs.yml` — triggers on `main` when `docs/`, `mkdocs.yml`, or source files change; builds and deploys MkDocs site
- Coverage uploaded to Codecov via `codecov/codecov-action@v5` (non-blocking — `fail_ci_if_error: false`)

## Environment Configuration

**Required env vars (runtime):**
- `ODOO_URL` — base URL of Odoo instance (e.g., `https://myodoo.example.com`)
- `ODOO_DB` / `ODOO_DATABASE` — Odoo database name
- `ODOO_USER` / `ODOO_USERNAME` — Odoo login
- `ODOO_PASSWORD` — Odoo password

**Required env vars (integration tests / CI):**
- `ODOO_VERSION` — Odoo Docker image version tag (`17.0`, `18.0`, `19.0`)
- `ODOO_SEED_IMAGE` — (optional) Pre-seeded Postgres Docker image; skips cold Odoo DB init when set

**Required env vars (release CI):**
- `GH_TOKEN` / `GITHUB_TOKEN` — GitHub token for `python-semantic-release` to create tags and releases

**Secrets location:**
- GitHub Actions environment `pypi` — trusted OIDC publishing (no stored PyPI token)
- `GH_TOKEN` — GitHub Actions built-in `GITHUB_TOKEN`

## Webhooks & Callbacks

**Incoming:**
- None — this is a client SDK, not a server

**Outgoing:**
- None beyond direct JSON-RPC calls to Odoo

---

*Integration audit: 2026-05-18*
