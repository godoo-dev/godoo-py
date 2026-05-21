"""Tests for the type mapper (pure unit)."""

from __future__ import annotations

import logging

import pytest

from godoo_introspection.type_mapper import python_type_str
from godoo_introspection.types import FieldSchema


def _field(ttype: str, **kwargs: object) -> FieldSchema:
    """Build a minimal FieldSchema for testing."""
    return FieldSchema(name="f", ttype=ttype, **kwargs)  # type: ignore[arg-type]


def test_char() -> None:
    assert python_type_str(_field("char")) == "str | Literal[False]"


def test_text() -> None:
    assert python_type_str(_field("text")) == "str | Literal[False]"


def test_html() -> None:
    assert python_type_str(_field("html")) == "str | Literal[False]"


def test_image() -> None:
    assert python_type_str(_field("image")) == "str | Literal[False]"


def test_integer() -> None:
    assert python_type_str(_field("integer")) == "int | Literal[False]"


def test_float() -> None:
    assert python_type_str(_field("float")) == "float | Literal[False]"


def test_monetary() -> None:
    assert python_type_str(_field("monetary")) == "float | Literal[False]"


def test_boolean_no_false_literal() -> None:
    result = python_type_str(_field("boolean"))
    assert result == "bool"
    assert "Literal[False]" not in result


def test_date() -> None:
    assert python_type_str(_field("date")) == "str | Literal[False]"


def test_datetime() -> None:
    assert python_type_str(_field("datetime")) == "str | Literal[False]"


def test_binary() -> None:
    assert python_type_str(_field("binary")) == "str | Literal[False]"


def test_serialized() -> None:
    assert python_type_str(_field("serialized")) == "str | Literal[False]"


def test_many2one() -> None:
    assert python_type_str(_field("many2one")) == "tuple[int, str] | Literal[False]"


def test_one2many() -> None:
    assert python_type_str(_field("one2many")) == "list[int]"


def test_many2many() -> None:
    assert python_type_str(_field("many2many")) == "list[int]"


def test_reference() -> None:
    assert python_type_str(_field("reference")) == "str | Literal[False]"


def test_selection_static() -> None:
    field = FieldSchema(name="f", ttype="selection", selection=[("draft", "Draft"), ("done", "Done")])
    result = python_type_str(field)
    assert "Literal['draft', 'done']" in result
    assert "Literal[False]" in result


def test_selection_dynamic_empty() -> None:
    field = FieldSchema(name="f", ttype="selection", selection=[])
    assert python_type_str(field) == "str | Literal[False]"


def test_json() -> None:
    assert python_type_str(_field("json")) == "dict[str, Any] | Literal[False]"


def test_properties() -> None:
    assert python_type_str(_field("properties")) == "dict[str, Any] | Literal[False]"


def test_unknown_ttype_returns_any() -> None:
    result = python_type_str(_field("__custom_ttype__"))
    assert result == "Any"


def test_unknown_ttype_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="godoo_introspection.codegen"):
        python_type_str(_field("__another_unknown__"))
    assert any("__another_unknown__" in record.message for record in caplog.records)
    assert any(record.levelno == logging.WARNING for record in caplog.records)
