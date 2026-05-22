from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

SafetyLevel = Literal["READ", "WRITE", "DELETE"]

READ_METHODS: frozenset[str] = frozenset(
    {
        "search",
        "read",
        "search_read",
        "search_count",
        "fields_get",
        "name_get",
        "name_search",
        "default_get",
        "onchange",
        "load_views",
        "check_access_rights",
        "check_access_rule",
        "read_group",
    }
)

DELETE_METHODS: frozenset[str] = frozenset({"unlink"})


@dataclass
class OperationInfo:
    name: str
    level: SafetyLevel
    model: str
    description: str
    target: str | None = None
    details: dict | None = None  # type: ignore[type-arg]


@dataclass
class SafetyContext:
    confirm: Callable[[OperationInfo], Awaitable[bool]]


# ---------------------------------------------------------------------------
# Module-level default context
# ---------------------------------------------------------------------------

_default_safety_context: SafetyContext | None = None


def set_default_safety_context(ctx: SafetyContext | None) -> None:
    global _default_safety_context
    _default_safety_context = ctx


def get_default_safety_context() -> SafetyContext | None:
    return _default_safety_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def infer_safety_level(method: str) -> SafetyLevel:
    if method in READ_METHODS:
        return "READ"
    if method in DELETE_METHODS:
        return "DELETE"
    return "WRITE"


def resolve_safety_context(
    client_context: SafetyContext | None = None,
    *,
    undefined: bool = False,
) -> SafetyContext | None:
    """Resolve the effective safety context.

    - ``undefined=True``: the caller has no opinion — fall back to global default.
    - ``undefined=False`` (default): ``client_context`` is the caller's explicit choice
      (even ``None`` meaning "disable safety").
    """
    if undefined:
        return _default_safety_context
    return client_context
