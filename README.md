# godoo-py

Async Python libraries for Odoo RPC, instance-derived types and disposable test
environments. Python 3.14+; LGPL-3.0-or-later.

| Distribution | Import namespace | Purpose |
| --- | --- | --- |
| `godoo-client` | `godoo.client` | Async CRUD, safety guards and eight domain services |
| `godoo-introspection` | `godoo.introspection` | Live schema discovery and Pydantic model generation |
| `godoo-testcontainers` | `godoo.testcontainers` | Odoo/Postgres containers, harness and snapshots |
| `godoo` | None | Metadata-only distribution reserving the family name |

Install the client distribution for application code:

```sh
uv add godoo-client
# Optional generated-model support:
uv add 'godoo-client[typed]'
```

Set `ODOO_URL`, `ODOO_DB`, `ODOO_USER` and `ODOO_PASSWORD` for an instance you are
authorized to read, then:

```python
import asyncio
from godoo.client import create_client

async def main():
    client = await create_client()
    try:
        partners = await client.search_read(
            "res.partner",
            [["is_company", "=", True]],
            fields=["name", "email"],
            limit=5,
        )
        for partner in partners:
            print(partner["name"], partner.get("email"))
    finally:
        await client.aclose()

asyncio.run(main())
```

Use the [getting-started guide](docs/getting-started.md), [service guides](docs/index.md)
and [API reference](docs/api/client.md) for usage. The [typed-model guide](docs/guides/typed-models.md)
explains code generation and relation/write boundaries. See [testing](docs/testing.md)
for disposable environments and [browser design](docs/browser.md) for the unshipped
Pyodide path.

[Contributing](CONTRIBUTING.md) covers setup and checks;
[development](docs/development.md) explains the package structure. Odoo 18 is the
default required integration target; later-major qualification is explicit and
follows the same candidate passing Odoo 18. Source manifests and CI
configuration alone do not establish publication, runtime or consumer acceptance.

[Python library targets](docs/library-targets.md) retain product intent and explicit
language differences. The [organization overview](https://github.com/godoo-dev/.github/blob/main/profile/README.md)
provides family orientation. Track work in this repository's
[GitHub issues](https://github.com/godoo-dev/godoo-py/issues).
Agent entrypoint: [AGENTS.md](AGENTS.md).
