"""Tests for the Pydantic type mapper (pure unit)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from godoo.introspection.codegen import _model_to_classname
from godoo.introspection.type_mapper import pydantic_field_str
from godoo.introspection.types import FieldSchema

if TYPE_CHECKING:
    import pytest


def _field(ttype: str, **kwargs: object) -> FieldSchema:
    """Build a minimal FieldSchema for testing."""
    return FieldSchema(name="f", ttype=ttype, **kwargs)  # type: ignore[arg-type]


# classname_fn for tests
_fn = _model_to_classname


def test_char() -> None:
    assert pydantic_field_str(_field("char"), frozenset(), _fn) == ("Optional[str]", "None")


def test_text() -> None:
    assert pydantic_field_str(_field("text"), frozenset(), _fn) == ("Optional[str]", "None")


def test_html() -> None:
    assert pydantic_field_str(_field("html"), frozenset(), _fn) == ("Optional[str]", "None")


def test_image() -> None:
    assert pydantic_field_str(_field("image"), frozenset(), _fn) == ("Optional[str]", "None")


def test_binary() -> None:
    assert pydantic_field_str(_field("binary"), frozenset(), _fn) == ("Optional[str]", "None")


def test_serialized() -> None:
    assert pydantic_field_str(_field("serialized"), frozenset(), _fn) == ("Optional[str]", "None")


def test_reference() -> None:
    assert pydantic_field_str(_field("reference"), frozenset(), _fn) == ("Optional[str]", "None")


def test_integer() -> None:
    assert pydantic_field_str(_field("integer"), frozenset(), _fn) == ("Optional[int]", "None")


def test_float() -> None:
    assert pydantic_field_str(_field("float"), frozenset(), _fn) == ("Optional[float]", "None")


def test_monetary() -> None:
    assert pydantic_field_str(_field("monetary"), frozenset(), _fn) == ("Optional[float]", "None")


def test_boolean() -> None:
    annotation, default = pydantic_field_str(_field("boolean"), frozenset(), _fn)
    assert annotation == "bool"
    assert default == "False"
    assert "Optional" not in annotation


def test_date() -> None:
    assert pydantic_field_str(_field("date"), frozenset(), _fn) == ("Optional[date]", "None")


def test_datetime() -> None:
    assert pydantic_field_str(_field("datetime"), frozenset(), _fn) == ("Optional[datetime]", "None")


def test_many2one_in_set() -> None:
    field = FieldSchema(name="f", ttype="many2one", relation="res.partner")
    annotation, default = pydantic_field_str(field, frozenset({"res.partner"}), _fn)
    assert annotation == "Optional[Ref[ResPartner]]"
    assert default == "None"


def test_many2one_not_in_set() -> None:
    field = FieldSchema(name="f", ttype="many2one", relation="res.company")
    annotation, default = pydantic_field_str(field, frozenset(), _fn)
    assert annotation == "Optional[Ref[int]]"
    assert default.startswith("None  # res.company")


def test_one2many() -> None:
    assert pydantic_field_str(_field("one2many"), frozenset(), _fn) == ("list[int]", "[]")


def test_many2many() -> None:
    assert pydantic_field_str(_field("many2many"), frozenset(), _fn) == ("list[int]", "[]")


def test_selection_static() -> None:
    field = FieldSchema(name="f", ttype="selection", selection=[("draft", "Draft"), ("done", "Done")])
    annotation, default = pydantic_field_str(field, frozenset(), _fn)
    assert annotation == "Optional[Literal['draft', 'done']]"
    assert default == "None"


def test_selection_dynamic_empty() -> None:
    field = FieldSchema(name="f", ttype="selection", selection=[])
    assert pydantic_field_str(field, frozenset(), _fn) == ("Optional[str]", "None")


def test_json() -> None:
    assert pydantic_field_str(_field("json"), frozenset(), _fn) == ("Optional[dict[str, Any]]", "None")


def test_properties() -> None:
    assert pydantic_field_str(_field("properties"), frozenset(), _fn) == ("Optional[dict[str, Any]]", "None")


def test_unknown_ttype_returns_optional_any() -> None:
    annotation, default = pydantic_field_str(_field("__custom__"), frozenset(), _fn)
    assert annotation.startswith("Optional[Any]")
    assert default == "None"


def test_unknown_ttype_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="godoo_introspection.codegen"):
        pydantic_field_str(_field("__another_unknown__"), frozenset(), _fn)
    assert any("__another_unknown__" in record.message for record in caplog.records)
    assert any(record.levelno == logging.WARNING for record in caplog.records)
