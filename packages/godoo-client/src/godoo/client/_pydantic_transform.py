"""Pydantic wire transforms — sole module that imports pydantic.

NEVER import this module at top of any other godoo.client submodule.
Always reach it via lazy `from godoo.client._pydantic_transform import ...`
inside a dispatch-branch function body (D-04, D-08).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, get_args, get_origin

from godoo.client.typed import Ref
from pydantic import BaseModel, create_model, model_validator

# Module-private cache keyed by (id(model_class), frozenset(fields)).
# Unbounded — cardinality bounded by models x distinct_field_subsets used at runtime.
# Escape hatch: clear_partial_model_cache(). Document in docstring.
_partial_model_cache: dict[tuple[int, frozenset[str]], type[BaseModel]] = {}


# ------------------------------------------------------------------
# Helper predicates (module-private)
# ------------------------------------------------------------------


def _annotation_is(annotation: Any, target: type) -> bool:
    """Return True if annotation IS target or target appears in get_args(annotation).

    Handles bare `bool` and `bool | None` / `Optional[bool]` uniformly (D-02 / A2 fix).
    """
    if annotation is target:
        return True
    # Handle Union / Optional types: `bool | None` etc.
    return any(arg is target for arg in get_args(annotation))


def _annotation_mentions_ref(annotation: Any) -> bool:
    """Return True if Ref appears in the annotation (handles `Ref[X] | None`)."""
    origin = get_origin(annotation)
    if origin is Ref:
        return True
    for arg in get_args(annotation):
        if get_origin(arg) is Ref or arg is Ref:
            return True
        # Recurse one level for nested generics
        if get_args(arg) and _annotation_mentions_ref(arg):
            return True
    return False


def _looks_iso_date(value: str) -> bool:
    """Return True if value is a valid ISO date string (date-only, not datetime)."""
    if len(value) != 10:
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _looks_iso_datetime(value: str) -> bool:
    """Return True if value looks like an ISO datetime string (contains T or space separator)."""
    if "T" not in value and " " not in value:
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


# ------------------------------------------------------------------
# OdooBaseModel
# ------------------------------------------------------------------


class OdooBaseModel(BaseModel):
    """Base for all generated Odoo typed models. Applies wire transforms.

    Wire-transform contract:
    - Fields annotated `bool` or `bool | None` preserve `False` on the wire (D-02).
      Boolean fields MUST be emitted as bare `bool` or `bool | None` to opt out of
      the False→None coercion that applies to all other field types.
    - Non-bool fields: `False` on the wire → `None`.
    - Many2one `[id, "Name"]` tuples → `Ref(id=id, name="Name")`.
    - ISO date strings → `date`; ISO datetime strings → `datetime`.

    Subclasses (emitted by Phase 7 codegen) declare:
        __odoo_model__: ClassVar[str] = "res.partner"
    plus their fields.
    """

    __odoo_model__: ClassVar[str]

    @model_validator(mode="before")
    @classmethod
    def _odoo_wire_transforms(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out: dict[str, Any] = {}
        for name, value in data.items():
            field_info = cls.model_fields.get(name)
            if field_info is None:
                out[name] = value
                continue
            annotation = field_info.annotation

            # Finding #1: list-origin check — False for any list-annotated field
            # (bare list[T] or list[T] | None) maps to [] BEFORE the generic False->None rule.
            # This also handles x2many Odoo fields that return False for empty sets.
            _origin = get_origin(annotation)
            if _origin is not list:
                # Handle Optional[list[T]] / Union types — scan args for a list origin
                for _arg in get_args(annotation):
                    if get_origin(_arg) is list:
                        _origin = list
                        break
            if value is False and _origin is list:
                out[name] = []
                continue

            # D-02: preserve False for bool-annotated fields (bare bool AND bool | None)
            if value is False and not _annotation_is(annotation, bool):
                out[name] = None
                continue

            # m2o tuple [id, "Name"] or [id, False] → Ref(id, name)
            # Finding #3: accept False as value[1] for restricted display names
            if (
                isinstance(value, list)
                and len(value) == 2
                and isinstance(value[0], int)
                and (isinstance(value[1], str) or value[1] is False)
                and _annotation_mentions_ref(annotation)
            ):
                out[name] = Ref(id=value[0], name=None if value[1] is False else value[1])
                continue

            # ISO datetime BEFORE date (datetime is a subclass of date — order matters)
            if isinstance(value, str) and _annotation_is(annotation, datetime) and _looks_iso_datetime(value):
                out[name] = datetime.fromisoformat(value)
                continue

            if (
                isinstance(value, str)
                and _annotation_is(annotation, date)
                and not _annotation_is(annotation, datetime)
                and _looks_iso_date(value)
            ):
                out[name] = date.fromisoformat(value)
                continue

            out[name] = value
        return out


# ------------------------------------------------------------------
# derive_partial_model
# ------------------------------------------------------------------


def derive_partial_model(model: type[BaseModel], fields: list[str]) -> type[BaseModel]:
    """Derive a subset Pydantic model carrying only the requested fields.

    Returns a subclass of `model` (inheriting OdooBaseModel's @model_validator
    so wire transforms still apply on partial reads — D-01). All requested fields
    become `(annotation | None, None)` — All-Optional partial semantics.

    Results are cached by `(id(model), frozenset(fields))`. The cache is
    unbounded (see Pitfall 4 in RESEARCH.md). Call `clear_partial_model_cache()`
    as an escape hatch if needed.

    Raises:
        ValueError: if any name in `fields` is not declared on `model`.
    """
    key = (id(model), frozenset(fields))
    cached = _partial_model_cache.get(key)
    if cached is not None:
        return cached

    field_defs: dict[str, Any] = {}
    for name in fields:
        if name not in model.model_fields:
            raise ValueError(f"Field {name!r} not declared on {model.__name__}")
        fi = model.model_fields[name]
        # All-Optional partial semantics: each field becomes (annotation | None, None)
        ann = fi.annotation if fi.annotation is not None else Any
        field_defs[name] = (ann | None, None)

    derived = create_model(
        f"{model.__name__}__partial__{abs(hash(key))}",
        __base__=model,
        **field_defs,
    )
    _partial_model_cache[key] = derived
    return derived


def clear_partial_model_cache() -> None:
    """Clear the derive_partial_model cache.

    Escape hatch for long-lived processes that accumulate cache entries.
    See Pitfall 4 in RESEARCH.md for context.
    """
    _partial_model_cache.clear()
