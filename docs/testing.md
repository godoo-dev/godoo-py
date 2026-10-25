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
from godoo.testcontainers import OdooTestContainer

@pytest.fixture(scope="session")
async def odoo():
    """Start an Odoo container with the sale module installed."""
    container = OdooTestContainer(modules=["sale"], properties={})
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
| `properties` | `dict[str, str]` | (required) | `ir.config_parameter` key-value pairs used in the snapshot cache key. Pass `{}` if your setup has no custom parameters. |

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

## Required candidate proof

Odoo18 is the default and required runtime. The maintained candidate commands in
[contributing](https://github.com/godoo-dev/godoo-py/blob/develop/CONTRIBUTING.md) build four wheels and run both integration
suites through installed libraries outside the source tree:

```sh
./scripts/check.py package --artifacts /absolute/candidate --evidence /absolute/proof/package
./scripts/check.py odoo18 --artifacts /absolute/candidate --evidence /absolute/proof/odoo18
```

Docker must be available. The required invocation fails for missing Docker, wrong
observed major, skipped/empty suites or failed cleanup. Test data, snapshots,
addons and networks are disposable; evidence and manifests survive teardown.

Later-major qualification is explicit, after successful18 for the same wheels:

```sh
./scripts/check.py odoo19 --artifacts /absolute/candidate --baseline18 /absolute/proof/odoo18 --evidence /absolute/proof/odoo19
```

These commands grant no permission to test a shared or production instance.

## Environment variables

| Variable | Description |
|---|---|
| `ODOO_VERSION` | Odoo Docker image tag, default `18.0`. Required verification rejects another value. |
| `ODOO_SEED_IMAGE` | Pre-seeded PostgreSQL image for faster startup |

## Tips

- Use `scope="session"` on the fixture to avoid restarting containers per test
- The `module_manager` on the started container can install additional modules
  at runtime if a specific test needs them
- Container startup waits for a successful `/web/session/authenticate` call,
  not just log output, so your client is guaranteed ready
