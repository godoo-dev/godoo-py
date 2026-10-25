"""Stdlib-only typed primitives: Ref dataclass + OdooModel marker contract."""

from __future__ import annotations

import dataclasses
from typing import ClassVar

import pytest
from godoo.client.typed import OdooModel, Ref


def test_ref_construction_and_equality() -> None:
    """Ref constructs from keyword and positional args; equality uses dataclass semantics."""
    r1: Ref[str] = Ref(id=1, name="X")
    r2: Ref[str] = Ref(1, "X")
    assert r1 == r2
    assert r1.id == 1
    assert r1.name == "X"


def test_ref_is_frozen() -> None:
    """Ref is frozen — mutation raises dataclasses.FrozenInstanceError."""
    r: Ref[str] = Ref(id=1, name="X")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.id = 2  # type: ignore[misc]


def test_odoo_model_marker_satisfied() -> None:
    """A class with __odoo_model__ satisfies the D-04 dispatch guard hasattr check."""

    class _Marker:
        __odoo_model__: ClassVar[str] = "res.partner"

    assert hasattr(_Marker, "__odoo_model__")


def test_odoo_model_marker_absent() -> None:
    """A class without __odoo_model__ returns False from hasattr — not a typed model."""

    class _NotMarker:
        pass

    assert not hasattr(_NotMarker, "__odoo_model__")


def test_ref_generic_subscriptable() -> None:
    """Ref[T] is subscriptable at type-check time — mypy assertion via annotation."""
    # These are purely type-level; at runtime they just produce GenericAlias objects.
    _ref_int = Ref[int]
    _ref_str = Ref[str]
    assert _ref_int is not None
    assert _ref_str is not None


def test_odoo_model_is_protocol() -> None:
    """OdooModel is a Protocol (not a runtime_checkable ABC) — confirmed by behaviour."""
    # OdooModel is NOT runtime_checkable (Open Q1 decision) so isinstance fails.
    # The dispatch guard uses hasattr(model, "__odoo_model__") — pin that contract here.
    import typing

    assert isinstance(OdooModel, type(typing.Protocol))


# ------------------------------------------------------------------
# _target_cls field on Ref[T] — REL-01
# ------------------------------------------------------------------


def test_ref_target_cls_defaults_to_none() -> None:
    """Ref(id, name) has _target_cls=None by default (backward-compatible construction)."""
    r: Ref[str] = Ref(id=1, name="X")
    assert r._target_cls is None


def test_ref_target_cls_can_be_set() -> None:
    """Ref(id, name, _target_cls=SomeClass) stores the class."""

    class _Dummy:
        pass

    r: Ref[object] = Ref(id=1, name="X", _target_cls=_Dummy)
    assert r._target_cls is _Dummy


def test_ref_equality_ignores_target_cls() -> None:
    """Refs with different _target_cls compare equal (compare=False semantics)."""

    class _A:
        pass

    class _B:
        pass

    r1 = Ref(id=1, name="X", _target_cls=_A)
    r2 = Ref(id=1, name="X", _target_cls=_B)
    r3 = Ref(id=1, name="X")
    assert r1 == r2
    assert r1 == r3


def test_ref_hash_ignores_target_cls() -> None:
    """hash(Ref) is identical regardless of _target_cls value (hash=False semantics)."""

    class _C:
        pass

    r1 = Ref(id=1, name="X")
    r2 = Ref(id=1, name="X", _target_cls=_C)
    assert hash(r1) == hash(r2)


def test_ref_repr_excludes_target_cls() -> None:
    """repr(Ref) does NOT include _target_cls (repr=False keeps repr clean)."""

    class _D:
        pass

    r = Ref(id=1, name="X", _target_cls=_D)
    assert "_target_cls" not in repr(r)
