[![PyPI](https://img.shields.io/pypi/v/godoo)](https://pypi.org/project/godoo/) [![Downloads](https://img.shields.io/pypi/dm/godoo)](https://pypi.org/project/godoo/) [![CI](https://img.shields.io/github/actions/workflow/status/marcfargas/godoo/test.yml?branch=main)](https://github.com/marcfargas/godoo/actions) [![Coverage](https://img.shields.io/codecov/c/github/marcfargas/godoo)](https://codecov.io/gh/marcfargas/godoo) [![License](https://img.shields.io/github/license/marcfargas/godoo)](LICENSE) ![Odoo 17](https://img.shields.io/badge/Odoo-17-blueviolet) ![Odoo 18](https://img.shields.io/badge/Odoo-18-blueviolet) ![Odoo 19](https://img.shields.io/badge/Odoo-19-blueviolet)

# godoo

Async Python SDK for Odoo JSON-RPC — typed, tested, ready.

An async Python client for Odoo's JSON-RPC API with full type annotations and 8 domain services. Includes testcontainers integration for testing against real Odoo 17, 18, and 19 instances. Built with httpx, dataclasses, and mypy --strict.

## Packages

| Package | PyPI | Description |
|---|---|---|
| **godoo** | `uv add godoo` | Core client + 8 domain services |
| **godoo-testcontainers** | `uv add godoo-testcontainers` | Docker-based Odoo for integration testing |
| **godoo-introspection** | `uv add godoo-introspection` | Schema discovery + codegen (coming soon) |

## Install

```bash
uv add godoo
# or
pip install godoo
```

## Quickstart

Set `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, and `ODOO_PASSWORD`, then:

```python
import asyncio
from godoo import create_client

async def main():
    client = await create_client()  # reads ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD
    partners = await client.search_read(
        "res.partner",
        [["is_company", "=", True]],
        fields=["name", "email"],
        limit=5,
    )
    for p in partners:
        print(p["name"], p.get("email", ""))

asyncio.run(main())
```

## Services

| Service | Access | Description |
|---|---|---|
| [Mail](https://www.marcfargas.com/~godoo/services/mail/) | `client.mail` | Post notes and messages on record chatter |
| [Modules](https://www.marcfargas.com/~godoo/services/modules/) | `client.modules` | Install, uninstall, upgrade Odoo modules |
| [Attendance](https://www.marcfargas.com/~godoo/services/attendance/) | `client.attendance` | Clock in/out and presence tracking |
| [Timesheets](https://www.marcfargas.com/~godoo/services/timesheets/) | `client.timesheets` | Timer-based and manual time logging |
| [Accounting](https://www.marcfargas.com/~godoo/services/accounting/) | `client.accounting` | Cash discovery, reconciliation, balance |
| [URLs](https://www.marcfargas.com/~godoo/services/urls/) | `client.urls` | Version-agnostic record and portal links |
| [Properties](https://www.marcfargas.com/~godoo/services/properties/) | `client.properties` | Safe read-merge-write for property fields |
| [CDC](https://www.marcfargas.com/~godoo/services/cdc/) | `client.cdc` | Change data capture via audit log |

## Safety Guards

Write and delete operations require opt-in confirmation before execution.
Guards are configurable per-client or globally, protecting against accidental mutations.
See the [documentation](https://www.marcfargas.com/~godoo/) for details.

---

[Documentation](https://www.marcfargas.com/~godoo/) · [Contributing](CONTRIBUTING.md) · [License](LICENSE)
