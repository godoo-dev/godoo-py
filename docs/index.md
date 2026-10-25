# godoo

**Async Python SDK for Odoo JSON-RPC**

godoo gives you a fully typed, async-first client for Odoo's JSON-RPC API.
Built on `httpx`; CI requires Odoo18 before explicit later-major qualification. Current runtime
acceptance requires execution evidence for the selected version.

## Highlights

- **Async from the ground up** -- built on `httpx.AsyncClient`, all calls are non-blocking
- **Full CRUD helpers** -- `search`, `read`, `search_read`, `create`, `write`, `unlink`
- **8 high-level services** -- mail, modules, attendance, timesheets, accounting, URLs, properties, CDC
- **Safety guards** -- optional confirmation callback before write/delete operations
- **Structured errors** -- typed exception hierarchy with `to_json()` serialisation
- **Testcontainers integration** -- spin up real Odoo instances in Docker for integration tests
- **Instance-derived models** with optional Pydantic typed reads/writes

## Quick install

```bash
uv add godoo-client
```

Or with pip:

```bash
pip install godoo-client
```

## Hello, Odoo

```python
import asyncio
from godoo.client import create_client

async def main():
    client = await create_client()  # reads ODOO_* env vars
    partners = await client.search_read(
        "res.partner",
        [("is_company", "=", True)],
        fields=["name", "email"],
        limit=5,
    )
    for p in partners:
        print(p["name"], p["email"])
    await client.aclose()

asyncio.run(main())
```

## Next steps

- [Getting Started](getting-started.md) -- install, configure, first CRUD operations
- [Services](services/mail.md) -- high-level APIs for mail, attendance, accounting, and more
- [Guides](guides/multi-environment.md) -- patterns for multi-environment, safety, error handling
- [API Reference](api/client.md) -- full autodoc of public client symbols
- [Typed models](guides/typed-models.md) — generation, relations and write limits
- [Browser design](browser.md) — Pyodide feasibility and shipping prerequisites
- [Development](development.md) — package and transport boundaries
