"""Odoo ttype to Pydantic field annotation and default expression mapper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from godoo.introspection.types import FieldSchema

logger = logging.getLogger("godoo_introspection.codegen")

# ------------------------------------------------------------------
# ttype groups sharing the same output annotation
# ------------------------------------------------------------------

_OPTIONAL_STR_TTYPES = frozenset(
    {"char", "text", "html", "image", "binary", "serialized", "reference"}
)
_OPTIONAL_FLOAT_TTYPES = frozenset({"float", "monetary"})
_LIST_INT_TTYPES = frozenset({"one2many", "many2many"})
_DICT_ANY_TTYPES = frozenset({"json", "properties"})


def pydantic_field_str(
    field: FieldSchema,
    in_set: frozenset[str],
    classname_fn: Callable[[str], str],
) -> tuple[str, str]:
    """Return (annotation_str, default_expr_str) for a Pydantic field line.

    The field line is assembled by the caller as:
        f"    {field_name}: {annotation_str} = {default_expr_str}"

    Examples:
        ("Optional[str]", "None")
        ("bool", "False")
        ("Optional[Ref[ResCountry]]", "None")
        ("Optional[Ref[int]]", "None  # res.company")
        ("list[int]", "[]")
        ("Optional[Literal['draft', 'done']]", "None")
    """
    ttype = field.ttype

    # Optional[str] group
    if ttype in _OPTIONAL_STR_TTYPES:
        return ("Optional[str]", "None")

    # Optional[int]
    if ttype == "integer":
        return ("Optional[int]", "None")

    # Optional[float] group
    if ttype in _OPTIONAL_FLOAT_TTYPES:
        return ("Optional[float]", "None")

    # bool — non-Optional exception (CF-04)
    if ttype == "boolean":
        return ("bool", "False")

    # Optional[date]
    if ttype == "date":
        return ("Optional[date]", "None")

    # Optional[datetime]
    if ttype == "datetime":
        return ("Optional[datetime]", "None")

    # many2one — in-set → Ref[TargetClass], not-in-set → Ref[int] with comment
    if ttype == "many2one":
        relation = field.relation or ""
        if relation and relation in in_set:
            target_class = classname_fn(relation)
            return (f"Optional[Ref[{target_class}]]", "None")
        else:
            comment = f"  # {relation}" if relation else ""
            return ("Optional[Ref[int]]", f"None{comment}")

    # list[int] group (no Optional per CF-05)
    if ttype in _LIST_INT_TTYPES:
        return ("list[int]", "[]")

    # selection — static vs dynamic
    if ttype == "selection":
        if field.selection:
            # static: known values → Optional[Literal['val1', 'val2', ...]]
            vals = ", ".join(repr(v) for v, _ in field.selection)
            return (f"Optional[Literal[{vals}]]", "None")
        else:
            # dynamic: no enumerable values at codegen time
            return ("Optional[str]", "None")

    # json / properties → Optional[dict[str, Any]]
    if ttype in _DICT_ANY_TTYPES:
        return ("Optional[dict[str, Any]]", "None")

    # Unknown ttype fallback — log warning, return Optional[Any]
    logger.warning("Unknown Odoo ttype %r for field %r — falling back to Any", ttype, field.name)
    return ("Optional[Any]", "None")
