# Multi-Environment Configuration

godoo supports connecting to multiple Odoo instances from the same application
using environment variable prefixes.

## How it works

`config_from_env` and `create_client` accept a `prefix` argument (default:
`"ODOO"`).  The prefix is prepended to `_URL`, `_DB`, `_USER`, and `_PASSWORD`.

## Setup

Set environment variables for each environment:

```bash
# Production
export ODOO_PROD_URL=https://prod.mycompany.com
export ODOO_PROD_DB=production
export ODOO_PROD_USER=api_user
export ODOO_PROD_PASSWORD=prod_secret

# Staging
export ODOO_STG_URL=https://staging.mycompany.com
export ODOO_STG_DB=staging
export ODOO_STG_USER=api_user
export ODOO_STG_PASSWORD=stg_secret
```

## Usage

```python
from godoo import create_client

async def main():
    prod = await create_client("ODOO_PROD")
    staging = await create_client("ODOO_STG")

    # Compare record counts across environments
    prod_count = await prod.search_count("sale.order", [("state", "=", "sale")])
    stg_count = await staging.search_count("sale.order", [("state", "=", "sale")])
    print(f"Production: {prod_count} confirmed orders")
    print(f"Staging:    {stg_count} confirmed orders")

    await prod.aclose()
    await staging.aclose()
```

## Manual config

For environments where variables do not follow the prefix convention, build
configs directly:

```python
from godoo import OdooClient, OdooClientConfig

prod_config = OdooClientConfig(
    url="https://prod.mycompany.com",
    database="production",
    username="api_user",
    password="prod_secret",
)
prod = OdooClient(prod_config)
await prod.authenticate()
```

## Tips

- Use **read-only credentials** for production when possible
- Pair multi-environment setups with [safety guards](safety-guards.md) to
  prevent accidental writes to production
- Each client maintains its own HTTP session and authentication state
