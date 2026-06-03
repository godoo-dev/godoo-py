"""Unit tests for _serialize_for_write() — write-path serializer (WRITE-01..05)."""

from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar

import pytest
from godoo.client._pydantic_transform import OdooBaseModel, _serialize_for_write
from godoo.client.errors import OdooValidationError
from godoo.client.typed import Ref
from pydantic import Field

# ------------------------------------------------------------------
# Test model fixtures
# ------------------------------------------------------------------


class _WritePartner(OdooBaseModel):
    """Minimal model for write-serializer unit tests.

    id is Optional (generated shape per CR-02) so instances can be built for create().
    """

    __odoo_model__: ClassVar[str] = "res.partner"

    id: int | None = None
    name: str | None = None
    comment: str | None = None
    website: str | None = None
    is_company: bool = False
    credit_limit: float | None = None
    # Fields with odoo metadata
    state_readonly: str | None = Field(default=None, json_schema_extra={"odoo_readonly": True})
    compute_field: str | None = Field(default=None, json_schema_extra={"odoo_readonly": True})
    line_ids: list[int] = Field(default_factory=list, json_schema_extra={"odoo_x2many": True})
    tag_ids: list[int] = Field(default_factory=list, json_schema_extra={"odoo_x2many": True})
    parent_id: Ref[_WritePartner] | None = None
    create_date: datetime | None = None
    date_deadline: date | None = None


# ------------------------------------------------------------------
# WRITE-01: only model_fields_set fields included
# ------------------------------------------------------------------


def test_only_set_fields_included() -> None:
    """Only explicitly set fields appear in the payload — unset fields are absent (WRITE-01)."""
    instance = _WritePartner(id=1, name="Acme")
    payload = _serialize_for_write(instance)
    assert "name" in payload
    assert "comment" not in payload
    assert "website" not in payload


def test_no_set_fields_returns_empty_dict() -> None:
    """An instance with only id from model_validate yields an empty payload (id is always dropped)."""
    instance = _WritePartner.model_validate({"id": 1})
    payload = _serialize_for_write(instance)
    # id is dropped unconditionally; no other fields were set.
    assert payload == {}


def test_multiple_set_fields_included() -> None:
    """Multiple explicitly set fields all appear in the payload."""
    instance = _WritePartner(id=1, name="Acme", comment="Hello")
    payload = _serialize_for_write(instance)
    assert "name" in payload
    assert "comment" in payload


# ------------------------------------------------------------------
# WRITE-02: None -> False (Odoo wire convention for cleared fields)
# ------------------------------------------------------------------


def test_none_field_becomes_false() -> None:
    """An explicitly set None value maps to False on the wire (Odoo clear convention)."""
    instance = _WritePartner(id=1, name=None)
    payload = _serialize_for_write(instance)
    assert "name" in payload
    assert payload["name"] is False


# ------------------------------------------------------------------
# WRITE-03: value transforms — Ref, date, datetime
# ------------------------------------------------------------------


def test_ref_field_becomes_int() -> None:
    """A Ref field in model_fields_set maps to its bare int id."""
    instance = _WritePartner(id=1, parent_id=Ref(id=42, name="Parent"))
    payload = _serialize_for_write(instance)
    assert "parent_id" in payload
    assert payload["parent_id"] == 42


def test_datetime_field_becomes_iso_string() -> None:
    """A datetime field becomes an ISO-format string (WRITE-03)."""
    dt = datetime(2026, 1, 15, 12, 30, 0)
    instance = _WritePartner(id=1, create_date=dt)
    payload = _serialize_for_write(instance)
    assert payload["create_date"] == "2026-01-15T12:30:00"


def test_date_field_becomes_iso_string() -> None:
    """A date field becomes an ISO-format string (WRITE-03)."""
    d = date(2026, 3, 1)
    instance = _WritePartner(id=1, date_deadline=d)
    payload = _serialize_for_write(instance)
    assert payload["date_deadline"] == "2026-03-01"


def test_datetime_checked_before_date() -> None:
    """datetime is checked before date (datetime subclasses date — order matters)."""
    # A datetime must NOT be converted by the date branch
    dt = datetime(2026, 1, 15, 0, 0, 0)
    instance = _WritePartner(id=1, create_date=dt)
    payload = _serialize_for_write(instance)
    # datetime.isoformat() includes time component; date.isoformat() would not
    assert "T" in payload["create_date"]


def test_bool_false_passthrough() -> None:
    """A bool field set to False is passed through unchanged — NOT coerced to None→False."""
    instance = _WritePartner(id=1, is_company=False)
    payload = _serialize_for_write(instance)
    assert "is_company" in payload
    # False (bool) is NOT None, so the None→False branch does not fire; value stays False
    assert payload["is_company"] is False


def test_scalar_passthrough() -> None:
    """Plain string and float fields pass through unchanged."""
    instance = _WritePartner(id=1, name="Acme Corp", credit_limit=5000.0)
    payload = _serialize_for_write(instance)
    assert payload["name"] == "Acme Corp"
    assert payload["credit_limit"] == 5000.0


# ------------------------------------------------------------------
# WRITE-04: readonly fields excluded unconditionally
# ------------------------------------------------------------------


def test_readonly_field_excluded_when_set() -> None:
    """A field with odoo_readonly=True in json_schema_extra is skipped even when in model_fields_set (WRITE-04)."""
    instance = _WritePartner(id=1, name="Acme", state_readonly="done")
    payload = _serialize_for_write(instance)
    assert "state_readonly" not in payload
    assert "name" in payload


def test_computed_field_excluded_when_set() -> None:
    """A computed field (also odoo_readonly=True) is excluded from the write payload (WRITE-04)."""
    instance = _WritePartner(id=1, compute_field="computed_value")
    payload = _serialize_for_write(instance)
    assert "compute_field" not in payload


# ------------------------------------------------------------------
# WRITE-05: x2many raises OdooValidationError only on explicit post-init mutation (CR-01)
# ------------------------------------------------------------------


def test_x2many_explicit_mutation_raises_validation_error() -> None:
    """Contract (c): explicitly assigning an x2many field post-construction raises OdooValidationError.

    The guard fires on post-init attribute assignment (m.line_ids = [...]), not on
    constructor kwargs — the caller is unambiguously attempting to write the relation.
    """
    instance = _WritePartner(id=1)
    instance.line_ids = [1, 2, 3]  # explicit post-init mutation — contract (c)
    with pytest.raises(OdooValidationError, match="line_ids"):
        _serialize_for_write(instance)


def test_x2many_error_message_mentions_command_tuples() -> None:
    """The x2many error message directs the caller to use command tuples."""
    instance = _WritePartner(id=1)
    instance.tag_ids = [5]  # explicit post-init mutation
    with pytest.raises(OdooValidationError, match="command tuples"):
        _serialize_for_write(instance)


def test_x2many_raises_before_any_rpc() -> None:
    """The x2many guard fires locally — no async call needed; function is synchronous and raises immediately."""
    # _serialize_for_write is a plain sync function — no await, no coroutine
    import inspect

    assert not inspect.iscoroutinefunction(_serialize_for_write)
    instance = _WritePartner(id=1)
    instance.tag_ids = [1]  # explicit post-init mutation
    with pytest.raises(OdooValidationError):
        _serialize_for_write(instance)


def test_x2many_from_read_does_not_raise() -> None:
    """Contract (b): x2many populated via model_validate (read path) does NOT raise on write.

    This is the canonical read→modify-scalar→write roundtrip. The caller never
    explicitly touched the x2many field — it was stamped in by pydantic's model_validate.
    """
    # Simulate what client.search_read / client.read returns
    instance = _WritePartner.model_validate(
        {
            "id": 42,
            "name": "Acme",
            "line_ids": [1, 2, 3],  # x2many from Odoo response
            "tag_ids": [10, 20],
        }
    )
    # Modify a scalar field only — the roundtrip case
    instance.name = "Acme Updated"

    # Must not raise even though line_ids and tag_ids are in model_fields_set
    payload = _serialize_for_write(instance)
    # Only the explicitly mutated scalar appears in the payload
    assert "name" in payload
    assert "line_ids" not in payload
    assert "tag_ids" not in payload


def test_x2many_from_constructor_does_not_raise() -> None:
    """Contract (a): x2many field at its default (constructor, no explicit x2many kwarg) does not raise.

    Instantiating with only scalar fields (the create() pattern) must succeed.
    line_ids defaults to [] via default_factory — never in _user_set_fields.
    """
    instance = _WritePartner(name="New Partner")  # id defaults to None, line_ids defaults to []
    payload = _serialize_for_write(instance)
    assert "name" in payload
    assert "line_ids" not in payload


# ------------------------------------------------------------------
# Instance is never mutated
# ------------------------------------------------------------------


def test_instance_not_mutated() -> None:
    """_serialize_for_write does not mutate the instance."""
    instance = _WritePartner(id=1, name="Acme", parent_id=Ref(id=5, name="Parent"))
    original_name = instance.name
    original_parent = instance.parent_id
    _serialize_for_write(instance)
    assert instance.name == original_name
    assert instance.parent_id == original_parent
