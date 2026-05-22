# godoo-introspection

Schema discovery and codegen for Odoo models

> **Pre-Alpha:** This package is in early development. The API may change without notice and not all advertised features are implemented yet.

## Install

```bash
pip install godoo-introspection
```

## Quick start

```python
import asyncio
from godoo.client import create_client
from godoo.introspection import Introspector

async def main():
    client = await create_client()
    introspector = Introspector(client)
    schema = await introspector.get_schema("res.partner")
```

## Links

- [Documentation](https://www.marcfargas.com/~odoopy/)
- [GitHub repository](https://github.com/godoo-dev/godoo-py)
- License: LGPL-3.0-or-later
