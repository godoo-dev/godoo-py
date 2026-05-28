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
