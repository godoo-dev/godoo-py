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

_OPTIONAL_STR_TTYPES = frozenset({"char", "text", "html", "image", "binary", "serialized", "reference"})
_OPTIONAL_FLOAT_TTYPES = frozenset({"float", "monetary"})
_LIST_INT_TTYPES = frozenset({"one2many", "many2many"})
_DICT_ANY_TTYPES = frozenset({"json", "properties"})


def pydantic_field_str(
    field: FieldSchema,
    in_set: frozenset[str],
    classname_fn: Callable[[str], str],
) -> tuple[str, str, frozenset[str], dict[str, bool]]:
    """Return (annotation_str, default_expr_str, imports_set, extra_dict) for a Pydantic field line.

    The field line is assembled by the caller as:
        f"    {field_name}: {annotation_str} = {default_expr_str}"

    The ``imports_set`` is a frozenset of import tokens needed for the annotation.
    Possible tokens: "date", "datetime", "Literal", "Any", "Ref". Empty frozenset
    for types that require no extra imports (str, int, float, bool, list[int]).

    The ``extra_dict`` carries write-metadata flags for ``json_schema_extra``:
      - ``odoo_readonly``: True when ``readonly=True`` OR (``store=False`` AND
        ``compute is not None``). Plain non-stored inverse fields (store=False,
        compute=None) are writable and are NOT marked readonly (D-04).
      - ``odoo_x2many``: True when ttype is "one2many" or "many2many".
    Plain writable scalar fields return an empty dict.

    Examples:
        ("Optional[str]", "None", frozenset(), {})
        ("bool", "False", frozenset(), {})
        ("Optional[Ref[ResCountry]]", "None", frozenset({"Ref"}), {})
        ("Optional[Ref[int]]", "None  # res.company", frozenset({"Ref"}), {})
        ("list[int]", "[]", frozenset(), {"odoo_x2many": True})
        ("Optional[Literal['draft', 'done']]", "None", frozenset({"Literal"}), {})
        ("Optional[date]", "None", frozenset({"date"}), {})
        ("Optional[datetime]", "None", frozenset({"datetime"}), {})
    """
    ttype = field.ttype

    # Compute write-metadata once before the ttype dispatch chain (GEN-01)
    # D-04: readonly=True OR (store=False AND compute is not None)
    # Plain non-stored inverse fields (store=False, compute=None) are writable.
    extra: dict[str, bool] = {}
    if field.readonly or (not field.store and field.compute is not None):
        extra["odoo_readonly"] = True
    if ttype in ("one2many", "many2many"):
        extra["odoo_x2many"] = True

    # Optional[str] group
    if ttype in _OPTIONAL_STR_TTYPES:
        return ("Optional[str]", "None", frozenset(), extra)

    # Optional[int]
    if ttype == "integer":
        return ("Optional[int]", "None", frozenset(), extra)

    # Optional[float] group
    if ttype in _OPTIONAL_FLOAT_TTYPES:
        return ("Optional[float]", "None", frozenset(), extra)

    # bool — non-Optional exception (CF-04)
    if ttype == "boolean":
        return ("bool", "False", frozenset(), extra)

    # Optional[date]
    if ttype == "date":
        return ("Optional[date]", "None", frozenset({"date"}), extra)

    # Optional[datetime]
    if ttype == "datetime":
        return ("Optional[datetime]", "None", frozenset({"datetime"}), extra)

    # many2one — in-set → Ref[TargetClass], not-in-set → Ref[int] with comment
    if ttype == "many2one":
        relation = field.relation or ""
        if relation and relation in in_set:
            target_class = classname_fn(relation)
            return (f"Optional[Ref[{target_class}]]", "None", frozenset({"Ref"}), extra)
        else:
            comment = f"  # {relation}" if relation else ""
            return ("Optional[Ref[int]]", f"None{comment}", frozenset({"Ref"}), extra)

    # list[int] group (no Optional per CF-05)
    if ttype in _LIST_INT_TTYPES:
        return ("list[int]", "[]", frozenset(), extra)

    # selection — static vs dynamic
    if ttype == "selection":
        if field.selection:
            # static: known values → Optional[Literal['val1', 'val2', ...]]
            vals = ", ".join(repr(v) for v, _ in field.selection)
            return (f"Optional[Literal[{vals}]]", "None", frozenset({"Literal"}), extra)
        else:
            # dynamic: no enumerable values at codegen time
            return ("Optional[str]", "None", frozenset(), extra)

    # json / properties → Optional[dict[str, Any]]
    if ttype in _DICT_ANY_TTYPES:
        return ("Optional[dict[str, Any]]", "None", frozenset({"Any"}), extra)

    # Unknown ttype fallback — log warning, return Optional[Any]
    logger.warning("Unknown Odoo ttype %r for field %r — falling back to Any", ttype, field.name)
    return ("Optional[Any]", "None", frozenset({"Any"}), extra)
