# godoo-client

Async Python client for Odoo JSON-RPC

## Install

```bash
pip install godoo-client
```

## Quick start

```python
import asyncio
from godoo.client import create_client

async def main():
    client = await create_client()  # reads ODOO_URL / ODOO_DB / ODOO_USER / ODOO_PASSWORD
    partners = await client.search_read("res.partner", [], fields=["name"])
    await client.aclose()
```

## Links

- [Documentation](https://www.marcfargas.com/~odoopy/)
- [GitHub repository](https://github.com/godoo-dev/godoo-py)
- License: LGPL-3.0-or-later
