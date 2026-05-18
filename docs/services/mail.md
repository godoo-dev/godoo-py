# Mail Service

Access via `client.mail`.  Provides methods for posting messages on Odoo records
that inherit `mail.thread`.

## Requirements

The target model **must** inherit `mail.thread`.  Most standard Odoo business
models (sale.order, account.move, helpdesk.ticket, etc.) already do.

## Methods

### post_internal_note

Post a staff-only internal note.  Uses subtype `mail.mt_note`, so followers are
**not** notified by email.

```python
msg_id = await client.mail.post_internal_note(
    "sale.order",
    42,
    "Customer confirmed delivery address by phone.",
)
```

### post_open_message

Post a public message that triggers follower notifications:

```python
from godoo.services.mail.types import PostMessageOptions

msg_id = await client.mail.post_open_message(
    "sale.order",
    42,
    "Your order has been shipped!",
    options=PostMessageOptions(partner_ids=[15]),
)
```

## HTML body handling

- **Plain text** is automatically wrapped in `<p>` tags before sending.
- **HTML strings** (already containing tags) are sent as-is.
- An **empty body** raises `OdooValidationError`.

## PostMessageOptions

| Field | Type | Description |
|---|---|---|
| `partner_ids` | `list[int]` | Additional partners to notify (beyond followers) |
| `attachment_ids` | `list[int]` | IDs of `ir.attachment` records to attach |

## Odoo 19 compatibility

Odoo 19 changed `message_post` to return `list[int]` instead of `int`.
godoo handles this automatically -- both `post_internal_note` and
`post_open_message` always return a single `int` message ID regardless of
Odoo version.
