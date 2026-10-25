from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortalUrlOptions:
    """Options for building a portal URL."""

    access_token: bool = True


@dataclass
class PortalUrlResult:
    """Result of portal URL lookup."""

    url: str
    access_token: str | None = None
