# Error Handling

godoo provides a structured error hierarchy so you can catch specific failure
types and handle them appropriately.

## Error hierarchy

```
OdooError
├── OdooRpcError (code, data)
│   ├── OdooAuthError
│   ├── OdooNetworkError
│   │   └── OdooTimeoutError
│   ├── OdooValidationError
│   ├── OdooAccessError
│   └── OdooMissingError
└── OdooSafetyError (local, not RPC)
```

## RPC errors

All RPC errors carry optional `code` and `data` fields from the Odoo JSON-RPC
response.

### OdooAuthError

Raised when authentication fails or the session expires:

```python
from godoo import OdooAuthError

try:
    await client.authenticate()
except OdooAuthError:
    print("Bad credentials or session expired")
```

### OdooValidationError

Maps to Odoo's `ValidationError` and `UserError`.  Commonly raised when
business rules are violated:

```python
from godoo import OdooValidationError

try:
    await client.write("sale.order", 42, {"state": "invalid"})
except OdooValidationError as e:
    print(f"Validation failed: {e}")
```

### OdooAccessError

ACL or record rule violation:

```python
from godoo import OdooAccessError

try:
    await client.read("hr.employee", [1], fields=["name"])
except OdooAccessError:
    print("Insufficient permissions")
```

### OdooMissingError

The requested record does not exist:

```python
from godoo import OdooMissingError

try:
    await client.read("res.partner", [999999])
except OdooMissingError:
    print("Record not found")
```

### OdooNetworkError / OdooTimeoutError

Connection failures and timeouts:

```python
from godoo import OdooNetworkError, OdooTimeoutError

try:
    partners = await client.search_read("res.partner", [])
except OdooTimeoutError:
    print("Request timed out")
except OdooNetworkError:
    print("Could not reach Odoo server")
```

## OdooSafetyError

Raised locally when a [safety guard](safety-guards.md) blocks an operation.
No network call is made:

```python
from godoo import OdooSafetyError

try:
    await client.unlink("res.partner", [1])
except OdooSafetyError as e:
    print(f"Blocked: {e.operation.description}")
```

## Structured output with to_json()

Every error supports `to_json()` for logging or API responses:

```python
try:
    await client.authenticate()
except OdooAuthError as e:
    print(e.to_json())
    # {"error": "AUTH_ERROR", "message": "Authentication failed", "details": ...}
```

## RPC error classification

When Odoo returns an error, godoo classifies it in two steps:

1. **Check `exception_type`** in the response -- maps directly to `ValidationError`,
   `AccessError`, `MissingError`, etc.
2. **Fall back to `data.name`** -- older Odoo versions use this field instead

This two-step approach ensures correct classification across Odoo 17-19.

## Common patterns

### Retry on network errors

```python
import asyncio
from godoo import OdooNetworkError

async def resilient_read(client, model, ids, retries=3):
    for attempt in range(retries):
        try:
            return await client.read(model, ids)
        except OdooNetworkError:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

### Catch-all with specifics

```python
from godoo import OdooError, OdooAuthError, OdooValidationError

try:
    await client.create("sale.order", values)
except OdooAuthError:
    await client.authenticate()  # re-auth and retry
except OdooValidationError as e:
    log.warning("Business rule violated: %s", e)
except OdooError as e:
    log.error("Unexpected Odoo error: %s", e.to_json())
```
