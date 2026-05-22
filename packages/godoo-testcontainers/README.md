# godoo-testcontainers

Docker-based Odoo instances for integration testing

## Install

```bash
pip install godoo-testcontainers
```

## Quick start

```python
import asyncio
from godoo.testcontainers import OdooTestContainer

async def main():
    container = OdooTestContainer(modules=["sale"])
    started = await container.start()
    # started.client is an authenticated OdooClient
    await started.cleanup()
```

## Links

- [Documentation](https://www.marcfargas.com/~odoopy/)
- [GitHub repository](https://github.com/godoo-dev/godoo-py)
- License: LGPL-3.0-or-later
