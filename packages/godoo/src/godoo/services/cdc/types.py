from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldMeta:
    """Metadata about an Odoo model field."""

    name: str
    field_type: str
    relation: str | None = None
    selection: list[tuple[str, str]] | None = None


@dataclass
class TypedValue:
    """A resolved value with its display representation."""

    raw: Any = None
    display: str = ""


@dataclass
class TrackingEvent:
    """A single tracking/change event from mail.tracking.value."""

    id: int
    field_name: str
    field_description: str
    old_value: TypedValue = field(default_factory=TypedValue)
    new_value: TypedValue = field(default_factory=TypedValue)
    date: str = ""
    author: str = ""
    message_id: int | None = None


@dataclass
class CdcCheckResult:
    """Result of checking whether a model supports change tracking."""

    model: str
    has_tracking: bool
    tracked_fields: list[str] = field(default_factory=list)


@dataclass
class GetHistoryOptions:
    """Options for fetching tracking history."""

    field_names: list[str] | None = None
    limit: int | None = None
    since: str | None = None  # ISO date string


@dataclass
class GetFeedOptions:
    """Options for the CDC feed (async generator)."""

    model: str
    res_ids: list[int] | None = None
    field_names: list[str] | None = None
    batch_size: int = 100
    since_id: int = 0
