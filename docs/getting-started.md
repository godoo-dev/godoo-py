# Getting Started

## Installation

=== "uv"

    ```bash
    uv add godoo
    ```

=== "pip"

    ```bash
    pip install godoo
    ```

## Configuration

godoo reads connection details from environment variables.  Set these before running your code:

| Variable | Alias | Description |
|---|---|---|
| `ODOO_URL` | | Base URL of the Odoo instance (e.g. `https://mycompany.odoo.com`) |
| `ODOO_DB` | `ODOO_DATABASE` | Database name |
| `ODOO_USER` | `ODOO_USERNAME` | Login username |
| `ODOO_PASSWORD` | | Login password |

```bash
export ODOO_URL=https://mycompany.odoo.com
export ODOO_DB=mycompany
export ODOO_USER=admin
export ODOO_PASSWORD=secret
```

## Creating a client

The fastest way to get started is `create_client`, which reads the environment and authenticates in one call:

```python
from godoo import create_client

client = await create_client()
```

For more control, build the config yourself:

```python
from godoo import OdooClient, OdooClientConfig

config = OdooClientConfig(
    url="https://mycompany.odoo.com",
    database="mycompany",
    username="admin",
    password="secret",
)
client = OdooClient(config)
await client.authenticate()
```

## CRUD operations

### search_read

Fetch records matching a domain with specific fields:

```python
partners = await client.search_read(
    "res.partner",
    [("is_company", "=", True)],
    fields=["name", "email", "phone"],
    limit=10,
    order="name asc",
)
```

### search

Return only IDs:

```python
ids = await client.search("res.partner", [("country_id.code", "=", "ES")])
```

### read

Read specific records by ID:

```python
records = await client.read("res.partner", [1, 2, 3], fields=["name", "email"])
```

### search_count

Count matching records without fetching them:

```python
total = await client.search_count("sale.order", [("state", "=", "sale")])
```

### create

Create a new record and get its ID back:

```python
partner_id = await client.create("res.partner", {
    "name": "Acme Corp",
    "email": "info@acme.com",
    "is_company": True,
})
```

### write

Update one or more records:

```python
await client.write("res.partner", partner_id, {"phone": "+34 600 000 000"})
```

### unlink

Delete records:

```python
await client.unlink("res.partner", [partner_id])
```

## Using services

High-level services are available as cached properties on the client:

```python
# Post an internal note
await client.mail.post_internal_note("sale.order", 42, "Reviewed and approved")

# Check if a module is installed
installed = await client.modules.is_module_installed("sale")

# Get a shareable URL for a record
url = await client.urls.get_record_url("sale.order", 42)
```

See the [Services](services/mail.md) section for full documentation of each service.

## Cleanup

Always close the client when you are done:

```python
await client.aclose()
```
