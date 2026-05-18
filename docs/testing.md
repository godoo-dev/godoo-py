# Testing with godoo-testcontainers

`godoo-testcontainers` lets you spin up real Odoo + PostgreSQL containers for
integration tests.  No mocks, no stubs -- your tests run against a live Odoo
instance.

## Installation

```bash
uv add --dev godoo-testcontainers
```

Requires Docker to be running on your machine or CI environment.

## Pytest fixture

```python
import pytest
from godoo_testcontainers import OdooTestContainer

@pytest.fixture(scope="session")
async def odoo():
    """Start an Odoo container with the sale module installed."""
    container = OdooTestContainer(modules=["sale"])
    started = await container.start()
    yield started
    await started.cleanup()

@pytest.fixture
def client(odoo):
    """Pre-authenticated OdooClient."""
    return odoo.client
```

Use the fixture in your tests:

```python
async def test_create_partner(client):
    partner_id = await client.create("res.partner", {
        "name": "Test Partner",
        "email": "test@example.com",
    })
    assert partner_id > 0

    records = await client.read("res.partner", partner_id, fields=["name"])
    assert records[0]["name"] == "Test Partner"
```

## OdooTestContainer options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `modules` | `list[str]` | `[]` | Odoo modules to install after startup |
| `database` | `str` | `"test_odoo"` | Database name |
| `admin_password` | `str` | `"admin"` | Admin password |
| `startup_timeout` | `int` | `300` | Max seconds to wait for Odoo to be ready |
| `env` | `dict[str, str]` | `{}` | Extra environment variables for the Odoo container |

## Seed-aware startup

If you have a pre-seeded PostgreSQL image (with modules already installed), the
container will detect it via the `ODOO_SEED_IMAGE` environment variable and
skip the slow `--init base` step.  Only modules not already present in the seed
are installed at startup.

This dramatically reduces test startup time -- from minutes to seconds.

```bash
# Use a pre-seeded image
export ODOO_SEED_IMAGE=registry.example.com/odoo-seed:18
```

## What you get back

`container.start()` returns a `StartedOdooContainer` with:

| Attribute | Type | Description |
|---|---|---|
| `client` | `OdooClient` | Pre-authenticated client |
| `module_manager` | `ModuleManager` | Module manager for runtime installs |
| `url` | `str` | Odoo base URL (localhost + mapped port) |
| `database` | `str` | Database name |

## CI matrix for multiple Odoo versions

Test against Odoo 17, 18, and 19 in parallel by setting `ODOO_VERSION`:

```yaml
# .github/workflows/test.yml
jobs:
  test:
    strategy:
      matrix:
        odoo-version: ["17.0", "18.0", "19.0"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run pytest -m integration
        env:
          ODOO_VERSION: ${{ matrix.odoo-version }}
```

## Environment variables

| Variable | Description |
|---|---|
| `ODOO_VERSION` | Odoo Docker image tag (e.g. `18.0`, `17.0`). Defaults to latest. |
| `ODOO_SEED_IMAGE` | Pre-seeded PostgreSQL image for faster startup |

## Tips

- Use `scope="session"` on the fixture to avoid restarting containers per test
- The `module_manager` on the started container can install additional modules
  at runtime if a specific test needs them
- Container startup waits for a successful `/web/session/authenticate` call,
  not just log output, so your client is guaranteed ready
