"""Odoo ttype to Python type hint string mapper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from godoo.introspection.types import FieldSchema

logger = logging.getLogger("godoo_introspection.codegen")

# ------------------------------------------------------------------
# ttype groups sharing the same output type string
# ------------------------------------------------------------------

_STR_FALSE_TTYPES = frozenset(
    {"char", "text", "html", "image", "date", "datetime", "binary", "serialized", "reference"}
)
_FLOAT_FALSE_TTYPES = frozenset({"float", "monetary"})
_LIST_INT_TTYPES = frozenset({"one2many", "many2many"})


def python_type_str(field: FieldSchema) -> str:
    """Return the Python type hint string for a FieldSchema.

    The returned string is a bare type expression suitable for embedding
    directly in generated source code (e.g. ``"str | Literal[False]"``).
    Annotated wrapping and FieldMeta instantiation are handled by codegen.py.
    """
    ttype = field.ttype

    # str | Literal[False] group
    if ttype in _STR_FALSE_TTYPES:
        return "str | Literal[False]"

    # int | Literal[False]
    if ttype == "integer":
        return "int | Literal[False]"

    # float | Literal[False] group
    if ttype in _FLOAT_FALSE_TTYPES:
        return "float | Literal[False]"

    # bool — NO | Literal[False] (False is a valid boolean value)
    if ttype == "boolean":
        return "bool"

    # tuple[int, str] | Literal[False]
    if ttype == "many2one":
        return "tuple[int, str] | Literal[False]"

    # list[int] (no Literal[False] — these are always lists)
    if ttype in _LIST_INT_TTYPES:
        return "list[int]"

    # selection — static vs dynamic
    if ttype == "selection":
        if field.selection:
            # static: known values → Literal['val1', 'val2', ...] | Literal[False]
            vals = ", ".join(repr(v) for v, _ in field.selection)
            return f"Literal[{vals}] | Literal[False]"
        else:
            # dynamic: no enumerable values at codegen time
            return "str | Literal[False]"

    # json / properties → dict[str, Any] | Literal[False]
    if ttype in {"json", "properties"}:
        return "dict[str, Any] | Literal[False]"

    # Unknown ttype fallback — log warning, return Any
    logger.warning("Unknown Odoo ttype %r for field %r — falling back to Any", ttype, field.name)
    return "Any"
