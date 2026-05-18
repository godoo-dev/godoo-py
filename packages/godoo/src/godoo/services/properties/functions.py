"""Properties service — standalone async functions."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from godoo.client import OdooClient


def properties_to_write_format(props_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert a list of property dicts to Odoo's write format.

    Input:  [{"name": "x_color", "value": "red"}, {"name": "x_size", "value": 42}]
    Output: {"x_color": "red", "x_size": 42}
    """
    return {p["name"]: p["value"] for p in props_list}


async def update_safely(
    client: OdooClient,
    model: str,
    record_id: int,
    field: str,
    updates: dict[str, Any],
) -> None:
    """Read-merge-write a properties field safely.

    Reads the current value of *field*, merges *updates* on top, and writes back.
    """
    records = await client.read(model, record_id, fields=[field])
    current: list[dict[str, Any]] = (records[0].get(field) or []) if records else []
    # Build a lookup from current props
    merged: dict[str, dict[str, Any]] = {p["name"]: p for p in current if isinstance(p, dict)}
    # Apply updates (overwrite value for existing, add new)
    for name, value in updates.items():
        if name in merged:
            merged[name]["value"] = value
        else:
            merged[name] = {"name": name, "value": value}
    await client.write(model, record_id, {field: list(merged.values())})


async def update_safely_batch(
    client: OdooClient,
    model: str,
    record_ids: list[int],
    field: str,
    updates: dict[str, Any],
) -> None:
    """Batch version of update_safely using asyncio.gather."""
    await asyncio.gather(*(update_safely(client, model, rid, field, updates) for rid in record_ids))
