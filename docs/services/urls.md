# URL Service

Access via `client.urls`.  Builds Odoo URLs for backend records and portal
pages.

## Methods

### get_base_url

<!-- atlas: base/url-base-url -->

Reads `web.base.url` from `ir.config_parameter`.  The result is cached per
client instance:

```python
base = await client.urls.get_base_url()
# "https://mycompany.odoo.com"
```

Pass `force_refresh=True` to bypass the cache.

### get_record_url

Build a mail-controller redirect URL by interpolating the model and record ID:

```python
url = await client.urls.get_record_url("sale.order", 42)
# "https://mycompany.odoo.com/mail/view?model=sale.order&res_id=42"
```

<!-- atlas: base/url-record-basic -->

Resolution requires the deployed mail controller and suitable record access.
The redirect destination depends on the version, installed modules and model routes.

### get_portal_url

Build a customer-facing portal URL with an access token:

```python
result = await client.urls.get_portal_url("sale.order", 42)
print(result.url)           # full portal URL with token
print(result.access_token)  # an existing token string, or None
```

<!-- atlas: base/url-portal-mixin -->

The helper reads an existing token and never requests token creation. Pass
`PortalUrlOptions(access_token=False)` to omit token reads and URL parameters.
Token links grant access only where the model's portal policy permits it.

<!-- atlas: base/url-record-basic -->

Missing records or an empty `access_url` use the mail redirect instead. A missing
or disabled token yields `None`; RPC access failures propagate.

## Types

| Type | Fields |
|---|---|
| `PortalUrlOptions` | `access_token: bool` (default `True`) |
| `PortalUrlResult` | `url: str`, `access_token: str \| None` |
