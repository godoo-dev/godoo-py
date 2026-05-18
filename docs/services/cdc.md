# CDC Service (Change Data Capture)

Access via `client.cdc`.  Reads Odoo's native field-change audit log stored in
`mail.tracking.value`.

## Requirements

- The model must inherit `mail.thread`
- Fields you want to track must have `tracking=True` in their definition

## Methods

### check

Diagnostic method -- verify whether a model supports change tracking:

```python
result = await client.cdc.check("sale.order")
print(result.has_tracking)     # True
print(result.tracked_fields)   # ["state", "partner_id", "amount_total", ...]
```

Returns a `CdcCheckResult` with `model`, `has_tracking`, and `tracked_fields`.

### get_history

Fetch all tracked changes for a single record:

```python
from godoo.services.cdc.types import GetHistoryOptions

events = await client.cdc.get_history(
    "sale.order",
    42,
    GetHistoryOptions(field_names=["state"], limit=10),
)
for event in events:
    print(f"{event.date}: {event.field_description} "
          f"changed from {event.old_value.display!r} "
          f"to {event.new_value.display!r}")
```

### get_feed

Async iterator over **all** changes for a model, paginated automatically:

```python
from godoo.services.cdc.types import GetFeedOptions

feed = await client.cdc.get_feed(
    GetFeedOptions(model="sale.order", batch_size=200)
)
async for event in feed:
    print(event.id, event.field_name, event.new_value.display)
```

## Cursor-based pagination

The feed uses **id-based cursors** (not timestamps).  This avoids sub-second
precision issues with `create_date` that could cause events to be skipped or
duplicated.

Set `since_id` to resume from a previous position:

```python
feed = await client.cdc.get_feed(
    GetFeedOptions(model="sale.order", since_id=last_seen_id)
)
```

## Field cache

Field metadata (`ir.model.fields`) is cached across pages within a single feed
iteration to minimise RPC calls.

## Types

### TrackingEvent

| Field | Type | Description |
|---|---|---|
| `id` | `int` | mail.tracking.value ID |
| `field_name` | `str` | Technical field name |
| `field_description` | `str` | Human-readable field label |
| `old_value` | `TypedValue` | Previous value |
| `new_value` | `TypedValue` | New value |
| `date` | `str` | ISO datetime of the change |
| `author` | `str` | User who made the change |
| `message_id` | `int \| None` | Related mail.message ID |

### TypedValue

| Field | Type | Description |
|---|---|---|
| `raw` | `Any` | Raw value from Odoo |
| `display` | `str` | Human-readable display string |

### GetFeedOptions

| Field | Type | Default | Description |
|---|---|---|---|
| `model` | `str` | required | Model technical name |
| `res_ids` | `list[int] \| None` | `None` | Filter to specific record IDs |
| `field_names` | `list[str] \| None` | `None` | Filter to specific fields |
| `batch_size` | `int` | `100` | Records per RPC page |
| `since_id` | `int` | `0` | Resume cursor |
