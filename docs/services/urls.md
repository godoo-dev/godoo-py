# URL Service

Access via `client.urls`.  Builds Odoo URLs for backend records and portal
pages.

## Methods

### get_base_url

Reads `web.base.url` from `ir.config_parameter`.  The result is cached per
client instance:

```python
base = await client.urls.get_base_url()
# "https://mycompany.odoo.com"
```

Pass `force_refresh=True` to bypass the cache.

### get_record_url

Build a version-agnostic backend URL for any record:

```python
url = await client.urls.get_record_url("sale.order", 42)
# "https://mycompany.odoo.com/mail/view?model=sale.order&res_id=42"
```

!!! info "Why `/mail/view`?"
    The Odoo backend URL format has changed across versions (hash fragment in
    older versions, `/odoo/` prefix in newer ones).  The `/mail/view` controller
    exists on Odoo 14 through 19 and performs a server-side redirect to the
    correct format.  This makes URLs stable across upgrades.

### get_portal_url

Build a customer-facing portal URL with an access token:

```python
result = await client.urls.get_portal_url("sale.order", 42)
print(result.url)           # full portal URL with token
print(result.access_token)  # the token string, if generated
```

Portal URLs let external users (customers, vendors) view specific records
without logging in.

## Types

| Type | Fields |
|---|---|
| `PortalUrlOptions` | `access_token: bool` (default `True`) |
| `PortalUrlResult` | `url: str`, `access_token: str \| None` |
