"""Pydantic wire transforms — sole module that imports pydantic.

NEVER import this module at top of any other godoo.client submodule.
Always reach it via lazy `from godoo.client._pydantic_transform import ...`
inside a dispatch-branch function body (D-04, D-08).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, get_args, get_origin
from weakref import WeakKeyDictionary

from godoo.client.typed import Ref
from pydantic import BaseModel, create_model, model_validator

# _READ_CONTEXT_KEY is set in the pydantic validation context by the read path
# (_validate_typed in client.py) when constructing a model from an Odoo response.
# model_post_init keys off it to decide whether construction-time fields count as
# user writes: user construction (constructor kwargs / plain model_validate) seeds
# _user_set_fields from model_fields_set, while a read-built instance starts empty
# so that read-inherited x2many values are never treated as user-written (CR-01).
_READ_CONTEXT_KEY = "godoo_read"

# Helper for the read path to build the validation context that marks an instance
# as read-built. Exposed so client.py can use it without hardcoding the key.
READ_VALIDATION_CONTEXT: dict[str, bool] = {_READ_CONTEXT_KEY: True}

# Module-private cache keyed by the source model class itself (a WeakKeyDictionary, so entries
# are reclaimed when the model class is garbage-collected) with an inner dict keyed by
# frozenset(fields). Keying on the class object — not id(model) — avoids a soundness hole where
# CPython reuses a dead class's id() for an unrelated class and returns the wrong partial (WR-03).
# Escape hatch: clear_partial_model_cache(). Documented in derive_partial_model's docstring.
_partial_model_cache: WeakKeyDictionary[type[BaseModel], dict[frozenset[str], type[BaseModel]]] = WeakKeyDictionary()


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


def _ref_target_class(annotation: Any) -> type | None:
    """Return the T in Ref[T] if annotation mentions Ref, else None.

    Mirrors _annotation_mentions_ref logic but extracts the type argument.
    Returns None for bare Ref or when Ref is not present in the annotation.
    For union annotations like ``Ref[T] | None``, unwraps the union and returns T.
    """
    origin = get_origin(annotation)
    if origin is Ref:
        args = get_args(annotation)
        return args[0] if args and isinstance(args[0], type) else None
    for arg in get_args(annotation):
        if get_origin(arg) is Ref:
            inner = get_args(arg)
            return inner[0] if inner and isinstance(inner[0], type) else None
        # Only descend into a nested generic when its chain actually mentions Ref (WR-04).
        # Without this guard the recursion would pull the first type out of an unrelated
        # generic (e.g. list[_Model] | None) and stamp it onto Ref._target_cls.
        if get_args(arg) and _annotation_mentions_ref(arg):
            result = _ref_target_class(arg)
            if result is not None:
                return result
    return None


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

    Dirty-tracking for x2many write guard (CR-01):
    ``_user_set_fields`` is a per-instance ``set[str]`` of field names the **user**
    wrote — whether via constructor kwargs, plain ``model_validate``, or
    post-construction attribute assignment. It is seeded by ``model_post_init`` and
    extended by ``__setattr__``.

    The discriminator between a *read-built* instance and a *user-built* one is the
    pydantic validation context: the read path (``_validate_typed`` in client.py)
    passes ``context=READ_VALIDATION_CONTEXT`` to ``model_validate``, which arrives at
    ``model_post_init`` as ``{_READ_CONTEXT_KEY: True}``. Construction-time kwargs and
    plain (context-less) ``model_validate`` cannot be told apart by pydantic alone —
    both bypass ``__setattr__`` and both set ``model_fields_set`` — so the context flag
    is the only reliable signal.

    Seeding rules in ``model_post_init``:
    - read-built (context flag present): ``_user_set_fields`` starts EMPTY. Fields
      populated by the read (including x2many returned by Odoo) are NOT user writes.
    - user-built (no context flag): ``_user_set_fields`` is seeded from
      ``model_fields_set`` — every field the caller supplied at construction IS a
      user write, including an x2many passed as a constructor kwarg.

    ``__setattr__`` adds any post-construction field assignment to ``_user_set_fields``.

    For x2many fields the write serializer raises ``OdooValidationError`` whenever the
    field is in ``_user_set_fields`` (no silent drops), while still permitting the
    canonical read→modify-scalar→write roundtrip (read-inherited x2many is omitted,
    never raised). Covered contracts:
    - (a) ``Model(name='X')`` scalar-only → x2many absent from set → no raise.
    - (b) read → change a scalar → write → read-inherited x2many omitted, no raise.
    - (c1) ``Model(name='X', child_ids=[...])`` x2many ctor kwarg → raise.
    - (c2) ``m.child_ids = [...]`` post-construction → raise.
    """

    __odoo_model__: ClassVar[str]

    def model_post_init(self, __context: Any) -> None:
        """Seed per-instance dirty-tracking set after pydantic construction (CR-01).

        Read-built instances (validation context carries the read flag) start with an
        empty user-set so read-inherited fields are never treated as user writes.
        User-built instances seed the set from ``model_fields_set`` so constructor
        kwargs — including an x2many relation — count as explicit user writes.
        """
        is_read = isinstance(__context, dict) and __context.get(_READ_CONTEXT_KEY) is True
        user_set: set[str] = set() if is_read else set(self.model_fields_set)
        # Use object.__setattr__ to bypass our own __setattr__ guard and avoid
        # accidentally recording '_user_set_fields' itself as a mutated field.
        object.__setattr__(self, "_user_set_fields", user_set)

    def __setattr__(self, name: str, value: Any) -> None:
        """Track post-construction field mutations for x2many write guard (CR-01)."""
        try:
            user_set: set[str] = object.__getattribute__(self, "_user_set_fields")
            # Only track declared model fields (not private attrs like _user_set_fields).
            # Use type(self).model_fields to access the class-level descriptor without
            # triggering the pydantic per-instance deprecation warning (pydantic >=2.11).
            if name in type(self).model_fields:
                user_set.add(name)
        except AttributeError:
            # _user_set_fields not yet created (during pydantic's own __init__ before
            # model_post_init runs) — silently skip so construction is unaffected.
            pass
        super().__setattr__(name, value)

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
                out[name] = Ref(
                    id=value[0],
                    name=None if value[1] is False else value[1],
                    _target_cls=_ref_target_class(annotation),
                )
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

    Results are cached in a `WeakKeyDictionary` keyed by the `model` class, with an
    inner dict keyed by `frozenset(fields)`. Keying on the class object (not `id(model)`)
    avoids a soundness hole where a GC'd model's id is reused for an unrelated class
    (WR-03); cache entries are reclaimed when the source model is collected. Call
    `clear_partial_model_cache()` as an escape hatch if needed.

    Raises:
        ValueError: if any name in `fields` is not declared on `model`.
    """
    field_key = frozenset(fields)
    by_fields = _partial_model_cache.get(model)
    if by_fields is not None:
        cached = by_fields.get(field_key)
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
        f"{model.__name__}__partial__{abs(hash(field_key))}",
        __base__=model,
        **field_defs,
    )
    if by_fields is None:
        by_fields = {}
        _partial_model_cache[model] = by_fields
    by_fields[field_key] = derived
    return derived


def clear_partial_model_cache() -> None:
    """Clear the derive_partial_model cache.

    Escape hatch for long-lived processes that accumulate cache entries.
    See Pitfall 4 in RESEARCH.md for context.
    """
    _partial_model_cache.clear()


# ------------------------------------------------------------------
# Write serializer (mirror of _odoo_wire_transforms)
# ------------------------------------------------------------------


def _serialize_for_write(instance: OdooBaseModel) -> dict[str, Any]:
    """Serialize an OdooBaseModel instance to an Odoo write payload.

    Only fields in model_fields_set are included. Readonly fields
    (json_schema_extra odoo_readonly=True) are excluded. x2many fields
    (odoo_x2many=True) that the **user** wrote (present in ``_user_set_fields``) raise
    OdooValidationError — never a silent drop. x2many fields that were merely
    populated by a read (and never written by the caller) are omitted from the
    payload. Transformations:
      Ref  -> int (bare id)
      None -> False (Odoo wire convention for cleared fields)
      datetime -> ISO-format string  (datetime BEFORE date — datetime subclasses date)
      date -> ISO-format string

    x2many guard semantics (CR-01) — keyed off ``_user_set_fields`` (see OdooBaseModel):
    - User-written x2many (constructor kwarg OR post-construction assignment) → RAISE.
    - Read-inherited x2many (populated via the read path's read-flagged model_validate,
      never written by the caller) → omitted from the payload, no raise. This enables
      the read→modify-scalar→write roundtrip without dropping any user-intended write.
    """
    from godoo.client.errors import OdooValidationError  # lazy: avoids circular at module load

    # Retrieve the dirty set once; fall back to empty set if somehow missing.
    try:
        user_set: set[str] = object.__getattribute__(instance, "_user_set_fields")
    except AttributeError:
        user_set = set()

    payload: dict[str, Any] = {}
    for field_name in instance.model_fields_set:
        # 'id' is the record identifier, passed separately in the RPC call — never in the payload
        if field_name == "id":
            continue
        fi = instance.__class__.model_fields.get(field_name)
        if fi is None:
            continue
        extra = fi.json_schema_extra
        extra_dict: dict[str, Any] = extra if isinstance(extra, dict) else {}

        # WRITE-04: skip readonly/computed fields unconditionally
        if extra_dict.get("odoo_readonly"):
            continue

        # WRITE-05: raise whenever the USER wrote an x2many field — whether via a
        # constructor kwarg or a post-construction assignment (both land in
        # _user_set_fields per OdooBaseModel.model_post_init / __setattr__). No silent
        # drops of user-intended writes. x2many values merely inherited from a read are
        # NOT in _user_set_fields, so they are omitted (not raised) — this is what makes
        # the read→modify-scalar→write roundtrip work (CR-01).
        if extra_dict.get("odoo_x2many"):
            if field_name in user_set:
                raise OdooValidationError(
                    f"Field {field_name!r} is an x2many relation and cannot be written via the "
                    f"typed path. Use client.write({instance.__odoo_model__!r}, [<ids>], "
                    f"{{{field_name!r}: [(6, 0, [<ids>])]}}) with command tuples instead."
                )
            # Read-inherited (never written by the caller) — omit from payload.
            continue

        value = getattr(instance, field_name)

        # Ref -> bare int id
        if isinstance(value, Ref):
            payload[field_name] = value.id
            continue

        # None (explicitly set) -> Odoo False
        if value is None:
            payload[field_name] = False
            continue

        # datetime BEFORE date (datetime subclasses date — order matters, mirrors read-side)
        if isinstance(value, datetime):
            payload[field_name] = value.isoformat()
            continue
        if isinstance(value, date):
            payload[field_name] = value.isoformat()
            continue

        payload[field_name] = value

    return payload
