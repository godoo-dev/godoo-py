"""RPC data types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OdooSessionInfo:
    uid: int
    session_id: str
    db: str
