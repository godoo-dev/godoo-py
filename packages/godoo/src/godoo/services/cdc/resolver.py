"""Value resolver for CDC tracking values."""

from __future__ import annotations

from typing import Any

from godoo.services.cdc.types import TypedValue


def resolve_values(
    row: dict[str, Any],
    field_type: str,
) -> tuple[TypedValue, TypedValue]:
    """Resolve old/new values from a mail.tracking.value row.

    Odoo stores old/new in type-specific columns:
    - integer: old_value_integer / new_value_integer
    - float/monetary: old_value_float / new_value_float
    - char/text: old_value_char / new_value_char
    - datetime: old_value_datetime / new_value_datetime
    - many2one: old_value_integer (id) + old_value_char (name)
    """
    if field_type in ("integer",):
        old_raw = row.get("old_value_integer", 0)
        new_raw = row.get("new_value_integer", 0)
        return (
            TypedValue(raw=old_raw, display=str(old_raw)),
            TypedValue(raw=new_raw, display=str(new_raw)),
        )

    if field_type in ("float", "monetary"):
        old_raw = row.get("old_value_float", 0.0)
        new_raw = row.get("new_value_float", 0.0)
        return (
            TypedValue(raw=old_raw, display=str(old_raw)),
            TypedValue(raw=new_raw, display=str(new_raw)),
        )

    if field_type in ("char", "text", "html", "selection"):
        old_raw = row.get("old_value_char", "")
        new_raw = row.get("new_value_char", "")
        return (
            TypedValue(raw=old_raw, display=str(old_raw or "")),
            TypedValue(raw=new_raw, display=str(new_raw or "")),
        )

    if field_type in ("datetime", "date"):
        old_raw = row.get("old_value_datetime", "")
        new_raw = row.get("new_value_datetime", "")
        return (
            TypedValue(raw=old_raw, display=str(old_raw or "")),
            TypedValue(raw=new_raw, display=str(new_raw or "")),
        )

    if field_type == "many2one":
        old_id = row.get("old_value_integer", 0)
        old_name = row.get("old_value_char", "")
        new_id = row.get("new_value_integer", 0)
        new_name = row.get("new_value_char", "")
        return (
            TypedValue(raw=old_id, display=str(old_name or "")),
            TypedValue(raw=new_id, display=str(new_name or "")),
        )

    if field_type == "boolean":
        old_raw = bool(row.get("old_value_integer", 0))
        new_raw = bool(row.get("new_value_integer", 0))
        return (
            TypedValue(raw=old_raw, display=str(old_raw)),
            TypedValue(raw=new_raw, display=str(new_raw)),
        )

    # Fallback: treat as char
    old_raw = row.get("old_value_char", "")
    new_raw = row.get("new_value_char", "")
    return (
        TypedValue(raw=old_raw, display=str(old_raw or "")),
        TypedValue(raw=new_raw, display=str(new_raw or "")),
    )
