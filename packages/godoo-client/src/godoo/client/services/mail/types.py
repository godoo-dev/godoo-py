from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PostMessageOptions:
    """Options for posting a message on an Odoo record."""

    partner_ids: list[int] = field(default_factory=list)
    attachment_ids: list[int] = field(default_factory=list)
