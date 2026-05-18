"""CDC (Change Data Capture) service — standalone async functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from godoo.services.cdc.field_cache import ensure_fields_cached
from godoo.services.cdc.resolver import resolve_values
from godoo.services.cdc.types import (
    CdcCheckResult,
    GetFeedOptions,
    GetHistoryOptions,
    TrackingEvent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from godoo.client import OdooClient

_TRACKING_FIELDS = [
    "id",
    "field",
    "field_desc",
    "old_value_integer",
    "new_value_integer",
    "old_value_float",
    "new_value_float",
    "old_value_char",
    "new_value_char",
    "old_value_datetime",
    "new_value_datetime",
    "old_value_text",
    "new_value_text",
    "mail_message_id",
    "create_date",
]


async def check(
    client: OdooClient,
    model: str,
) -> CdcCheckResult:
    """Check whether a model has tracked fields."""
    fields = await client.search_read(
        "ir.model.fields",
        [("model", "=", model), ("tracking", "!=", False)],
        fields=["name"],
    )
    tracked = [f["name"] for f in fields]
    return CdcCheckResult(
        model=model,
        has_tracking=bool(tracked),
        tracked_fields=tracked,
    )


async def get_history(
    client: OdooClient,
    model: str,
    res_id: int,
    options: GetHistoryOptions | None = None,
) -> list[TrackingEvent]:
    """Fetch tracking history for a specific record."""
    opts = options or GetHistoryOptions()
    # First get message IDs for this record
    msg_domain: list[Any] = [
        ("model", "=", model),
        ("res_id", "=", res_id),
    ]
    if opts.since:
        msg_domain.append(("date", ">=", opts.since))
    messages = await client.search_read(
        "mail.message",
        msg_domain,
        fields=["id", "date", "author_id"],
        order="date desc",
        **({"limit": opts.limit} if opts.limit else {}),
    )
    if not messages:
        return []
    msg_ids = [m["id"] for m in messages]
    msg_map = {m["id"]: m for m in messages}

    # Fetch tracking values
    tv_domain: list[Any] = [("mail_message_id", "in", msg_ids)]
    if opts.field_names:
        tv_domain.append(("field", "in", opts.field_names))
    tracking_rows = await client.search_read(
        "mail.tracking.value",
        tv_domain,
        fields=_TRACKING_FIELDS,
        order="id desc",
    )
    if not tracking_rows:
        return []

    # Resolve field types
    field_names = list({r["field"] for r in tracking_rows if r.get("field")})
    field_meta = await ensure_fields_cached(client, model, field_names) if field_names else {}

    events: list[TrackingEvent] = []
    for row in tracking_rows:
        fname = row.get("field", "")
        meta = field_meta.get(fname)
        ftype = meta.field_type if meta else "char"
        old_val, new_val = resolve_values(row, ftype)
        msg_id_raw = row.get("mail_message_id")
        msg_id = msg_id_raw[0] if isinstance(msg_id_raw, list) else msg_id_raw
        msg = msg_map.get(msg_id, {})
        author = msg.get("author_id")
        author_name = author[1] if isinstance(author, list) and len(author) >= 2 else ""
        events.append(
            TrackingEvent(
                id=row["id"],
                field_name=fname,
                field_description=row.get("field_desc", ""),
                old_value=old_val,
                new_value=new_val,
                date=msg.get("date", ""),
                author=author_name,
                message_id=msg_id if isinstance(msg_id, int) else None,
            )
        )
    return events


async def get_feed(
    client: OdooClient,
    options: GetFeedOptions,
) -> AsyncIterator[TrackingEvent]:
    """Async generator yielding tracking events using id-based cursor pagination."""
    cursor = options.since_id

    while True:
        # Build domain for mail.tracking.value
        domain: list[Any] = [("id", ">", cursor)]

        # If we have specific res_ids, find messages first
        if options.res_ids is not None:
            msg_domain: list[Any] = [
                ("model", "=", options.model),
                ("res_id", "in", options.res_ids),
            ]
            messages = await client.search_read(
                "mail.message",
                msg_domain,
                fields=["id", "date", "author_id"],
            )
            if not messages:
                return
            msg_ids = [m["id"] for m in messages]
            domain.append(("mail_message_id", "in", msg_ids))
            msg_map = {m["id"]: m for m in messages}
        else:
            # Broader: get all tracking values above cursor
            msg_map = {}

        if options.field_names:
            domain.append(("field", "in", options.field_names))

        tracking_rows = await client.search_read(
            "mail.tracking.value",
            domain,
            fields=_TRACKING_FIELDS,
            order="id asc",
            limit=options.batch_size,
        )
        if not tracking_rows:
            return

        # If we don't have a msg_map yet, build one
        if not msg_map:
            all_msg_ids = list(
                {
                    r["mail_message_id"][0] if isinstance(r.get("mail_message_id"), list) else r.get("mail_message_id")
                    for r in tracking_rows
                    if r.get("mail_message_id")
                }
            )
            if all_msg_ids:
                msgs = await client.read(
                    "mail.message",
                    [mid for mid in all_msg_ids if isinstance(mid, int)],
                    fields=["id", "date", "author_id", "model"],
                )
                msg_map = {m["id"]: m for m in msgs}

        # Filter by model if needed (when no res_ids constraint)
        field_names = list({r["field"] for r in tracking_rows if r.get("field")})
        field_meta = await ensure_fields_cached(client, options.model, field_names) if field_names else {}

        for row in tracking_rows:
            fname = row.get("field", "")
            meta = field_meta.get(fname)
            ftype = meta.field_type if meta else "char"
            old_val, new_val = resolve_values(row, ftype)
            msg_id_raw = row.get("mail_message_id")
            msg_id = msg_id_raw[0] if isinstance(msg_id_raw, list) else msg_id_raw
            msg = msg_map.get(msg_id, {}) if isinstance(msg_id, int) else {}

            # Filter: only yield events for the requested model
            if options.res_ids is None and msg.get("model") and msg["model"] != options.model:
                cursor = row["id"]
                continue

            author = msg.get("author_id")
            author_name = author[1] if isinstance(author, list) and len(author) >= 2 else ""
            yield TrackingEvent(
                id=row["id"],
                field_name=fname,
                field_description=row.get("field_desc", ""),
                old_value=old_val,
                new_value=new_val,
                date=msg.get("date", ""),
                author=author_name,
                message_id=msg_id if isinstance(msg_id, int) else None,
            )
            cursor = row["id"]

        if len(tracking_rows) < options.batch_size:
            return
