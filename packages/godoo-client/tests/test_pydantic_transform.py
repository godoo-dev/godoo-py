"""Wire-transform unit tests: False->None, m2o->Ref, ISO strings->date/datetime, partial models, cache."""

from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar

import pytest
from godoo.client._pydantic_transform import OdooBaseModel, clear_partial_model_cache, derive_partial_model
from godoo.client.typed import Ref
from pydantic import Field

# ------------------------------------------------------------------
# Test model fixture (module-level to allow cache clearing)
# ------------------------------------------------------------------


class _TestPartner(OdooBaseModel):
    """Minimal Odoo partner model for wire-transform unit tests."""

    __odoo_model__: ClassVar[str] = "res.partner"

    id: int
    name: str | None = None
    is_company: bool = False
    is_archived: bool | None = None
    parent_id: Ref[object] | None = None
    create_date: datetime | None = None
    date_active: date | None = None
    tag_ids: list[int] = Field(default_factory=list)


def setup_function(_fn: object) -> None:
    """Clear partial-model cache before each test to prevent state leakage."""
    clear_partial_model_cache()


# ------------------------------------------------------------------
# False -> None (non-bool fields)
# ------------------------------------------------------------------


def test_false_to_none_for_non_bool() -> None:
    """False on the wire becomes None for str | None annotated fields."""
    p = _TestPartner.model_validate({"id": 1, "name": False})
    assert p.name is None


# ------------------------------------------------------------------
# D-02: boolean preservation
# ------------------------------------------------------------------


def test_bool_false_preserved_bare() -> None:
    """False is preserved for bare bool fields — D-02 contract (bare bool)."""
    p = _TestPartner.model_validate({"id": 1, "is_company": False})
    assert p.is_company is False


def test_bool_false_preserved_optional() -> None:
    """False is preserved for Optional[bool] / bool | None fields — D-02 / A2 guard."""
    p = _TestPartner.model_validate({"id": 1, "is_archived": False})
    assert p.is_archived is False


# ------------------------------------------------------------------
# m2o tuple -> Ref
# ------------------------------------------------------------------


def test_m2o_tuple_becomes_ref() -> None:
    """[id, 'Name'] tuple becomes Ref(id, name) for Ref-annotated fields."""
    p = _TestPartner.model_validate({"id": 1, "parent_id": [3, "Acme"]})
    assert p.parent_id == Ref(3, "Acme")


def test_m2o_false_becomes_none() -> None:
    """False on a Ref-annotated field becomes None (non-bool False→None rule applies)."""
    p = _TestPartner.model_validate({"id": 1, "parent_id": False})
    assert p.parent_id is None


# ------------------------------------------------------------------
# ISO string -> date / datetime
# ------------------------------------------------------------------


def test_iso_date_string_becomes_date() -> None:
    """ISO date string '2026-01-15' becomes date(2026,1,15)."""
    p = _TestPartner.model_validate({"id": 1, "date_active": "2026-01-15"})
    assert p.date_active == date(2026, 1, 15)


def test_iso_datetime_string_becomes_datetime() -> None:
    """ISO datetime string '2026-01-15T12:00:00' becomes datetime(2026,1,15,12,0,0)."""
    p = _TestPartner.model_validate({"id": 1, "create_date": "2026-01-15T12:00:00"})
    assert p.create_date == datetime(2026, 1, 15, 12, 0, 0)


# ------------------------------------------------------------------
# derive_partial_model
# ------------------------------------------------------------------


def test_derive_partial_model_returns_subclass() -> None:
    """derive_partial_model returns a subclass of the model with only requested fields."""
    Partial = derive_partial_model(_TestPartner, ["name"])
    assert issubclass(Partial, _TestPartner)
    assert "name" in Partial.model_fields


def test_derive_partial_model_unknown_field_raises() -> None:
    """derive_partial_model raises ValueError for unknown field names."""
    with pytest.raises(ValueError, match="bogus"):
        derive_partial_model(_TestPartner, ["bogus"])


def test_derive_partial_model_is_cached() -> None:
    """derive_partial_model returns the same object on repeated calls (cache hit)."""
    P1 = derive_partial_model(_TestPartner, ["name"])
    P2 = derive_partial_model(_TestPartner, ["name"])
    assert P1 is P2


def test_derive_partial_model_cache_clear() -> None:
    """clear_partial_model_cache causes derive_partial_model to return a new object."""
    P1 = derive_partial_model(_TestPartner, ["name"])
    clear_partial_model_cache()
    P2 = derive_partial_model(_TestPartner, ["name"])
    assert P1 is not P2


# ------------------------------------------------------------------
# Finding #1: x2many False -> [] (list-origin takes precedence over False->None)
# ------------------------------------------------------------------


def test_x2many_false_becomes_empty_list() -> None:
    """False on a list[int] field coerces to [] — list-origin check fires before False→None."""
    p = _TestPartner.model_validate({"id": 1, "tag_ids": False})
    assert p.tag_ids == []


def test_x2many_optional_false_becomes_empty_list() -> None:
    """False on a list[int] | None field coerces to [] — list-origin takes precedence over Optional None."""

    class _ModelWithOptionalList(OdooBaseModel):
        __odoo_model__: ClassVar[str] = "test.optional.list"
        id: int
        tag_ids: list[int] | None = None

    p = _ModelWithOptionalList.model_validate({"id": 1, "tag_ids": False})
    assert p.tag_ids == []


# ------------------------------------------------------------------
# Finding #3: m2o [id, False] -> Ref(id, name=None)
# ------------------------------------------------------------------


def test_m2o_restricted_display_name() -> None:
    """[id, False] on a Ref-annotated field produces Ref(id=id, name=None) (restricted display name)."""
    p = _TestPartner.model_validate({"id": 1, "parent_id": [3, False]})
    assert p.parent_id is not None
    assert p.parent_id.id == 3
    assert p.parent_id.name is None


def test_derive_partial_model_inherits_validator() -> None:
    """The derived partial model inherits OdooBaseModel's @model_validator (wire transforms apply)."""
    Partial = derive_partial_model(_TestPartner, ["name"])
    # Include id (required base field) + name (partial field with wire transform)
    raw = Partial.model_validate({"id": 1, "name": False})
    # Cast to dict to inspect — avoid BaseModel attribute access mypy issues
    assert raw.model_dump().get("name") is None
