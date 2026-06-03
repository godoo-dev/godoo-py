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
    ann, default, imports = pydantic_field_str(_field("char"), frozenset(), _fn)
    assert (ann, default) == ("Optional[str]", "None")
    assert imports == frozenset()


def test_text() -> None:
    ann, default, imports = pydantic_field_str(_field("text"), frozenset(), _fn)
    assert (ann, default) == ("Optional[str]", "None")
    assert imports == frozenset()


def test_html() -> None:
    ann, default, imports = pydantic_field_str(_field("html"), frozenset(), _fn)
    assert (ann, default) == ("Optional[str]", "None")
    assert imports == frozenset()


def test_image() -> None:
    ann, default, imports = pydantic_field_str(_field("image"), frozenset(), _fn)
    assert (ann, default) == ("Optional[str]", "None")
    assert imports == frozenset()


def test_binary() -> None:
    ann, default, imports = pydantic_field_str(_field("binary"), frozenset(), _fn)
    assert (ann, default) == ("Optional[str]", "None")
    assert imports == frozenset()


def test_serialized() -> None:
    ann, default, imports = pydantic_field_str(_field("serialized"), frozenset(), _fn)
    assert (ann, default) == ("Optional[str]", "None")
    assert imports == frozenset()


def test_reference() -> None:
    ann, default, imports = pydantic_field_str(_field("reference"), frozenset(), _fn)
    assert (ann, default) == ("Optional[str]", "None")
    assert imports == frozenset()


def test_integer() -> None:
    ann, default, imports = pydantic_field_str(_field("integer"), frozenset(), _fn)
    assert (ann, default) == ("Optional[int]", "None")
    assert imports == frozenset()


def test_float() -> None:
    ann, default, imports = pydantic_field_str(_field("float"), frozenset(), _fn)
    assert (ann, default) == ("Optional[float]", "None")
    assert imports == frozenset()


def test_monetary() -> None:
    ann, default, imports = pydantic_field_str(_field("monetary"), frozenset(), _fn)
    assert (ann, default) == ("Optional[float]", "None")
    assert imports == frozenset()


def test_boolean() -> None:
    annotation, default, imports = pydantic_field_str(_field("boolean"), frozenset(), _fn)
    assert annotation == "bool"
    assert default == "False"
    assert "Optional" not in annotation
    assert imports == frozenset()


def test_date() -> None:
    ann, default, imports = pydantic_field_str(_field("date"), frozenset(), _fn)
    assert (ann, default) == ("Optional[date]", "None")
    assert imports == frozenset({"date"})


def test_datetime() -> None:
    ann, default, imports = pydantic_field_str(_field("datetime"), frozenset(), _fn)
    assert (ann, default) == ("Optional[datetime]", "None")
    assert imports == frozenset({"datetime"})


def test_many2one_in_set() -> None:
    field = FieldSchema(name="f", ttype="many2one", relation="res.partner")
    annotation, default, imports = pydantic_field_str(field, frozenset({"res.partner"}), _fn)
    assert annotation == "Optional[Ref[ResPartner]]"
    assert default == "None"
    assert imports == frozenset({"Ref"})


def test_many2one_not_in_set() -> None:
    field = FieldSchema(name="f", ttype="many2one", relation="res.company")
    annotation, default, imports = pydantic_field_str(field, frozenset(), _fn)
    assert annotation == "Optional[Ref[int]]"
    assert default.startswith("None  # res.company")
    assert imports == frozenset({"Ref"})


def test_one2many() -> None:
    ann, default, imports = pydantic_field_str(_field("one2many"), frozenset(), _fn)
    assert (ann, default) == ("list[int]", "[]")
    assert imports == frozenset()


def test_many2many() -> None:
    ann, default, imports = pydantic_field_str(_field("many2many"), frozenset(), _fn)
    assert (ann, default) == ("list[int]", "[]")
    assert imports == frozenset()


def test_selection_static() -> None:
    field = FieldSchema(name="f", ttype="selection", selection=[("draft", "Draft"), ("done", "Done")])
    annotation, default, imports = pydantic_field_str(field, frozenset(), _fn)
    assert annotation == "Optional[Literal['draft', 'done']]"
    assert default == "None"
    assert imports == frozenset({"Literal"})


def test_selection_dynamic_empty() -> None:
    field = FieldSchema(name="f", ttype="selection", selection=[])
    ann, default, imports = pydantic_field_str(field, frozenset(), _fn)
    assert (ann, default) == ("Optional[str]", "None")
    assert imports == frozenset()


def test_json() -> None:
    ann, default, imports = pydantic_field_str(_field("json"), frozenset(), _fn)
    assert (ann, default) == ("Optional[dict[str, Any]]", "None")
    assert imports == frozenset({"Any"})


def test_properties() -> None:
    ann, default, imports = pydantic_field_str(_field("properties"), frozenset(), _fn)
    assert (ann, default) == ("Optional[dict[str, Any]]", "None")
    assert imports == frozenset({"Any"})


def test_unknown_ttype_returns_optional_any() -> None:
    annotation, default, imports = pydantic_field_str(_field("__custom__"), frozenset(), _fn)
    assert annotation.startswith("Optional[Any]")
    assert default == "None"
    assert imports == frozenset({"Any"})


def test_unknown_ttype_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="godoo_introspection.codegen"):
        pydantic_field_str(_field("__another_unknown__"), frozenset(), _fn)
    assert any("__another_unknown__" in record.message for record in caplog.records)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


# ---------------------------------------------------------------------------
# GEN-01 — metadata emission tests
# ---------------------------------------------------------------------------


def _field_ro(ttype: str, **kwargs: object) -> FieldSchema:
    """Build a FieldSchema with readonly=True."""
    return FieldSchema(name="f", ttype=ttype, readonly=True, **kwargs)  # type: ignore[arg-type]


def _field_computed_nonstored(ttype: str) -> FieldSchema:
    """Build a computed non-stored FieldSchema (D-03 rule)."""
    return FieldSchema(name="f", ttype=ttype, store=False, compute="_compute_f")


def test_readonly_field_emits_odoo_readonly_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field_ro("char"), frozenset(), _fn)
    assert extra == {"odoo_readonly": True}


def test_computed_nonstored_emits_odoo_readonly_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field_computed_nonstored("float"), frozenset(), _fn)
    assert extra == {"odoo_readonly": True}


def test_nonstored_without_compute_no_metadata() -> None:
    """Non-stored field without compute is NOT marked readonly (D-04 refinement)."""
    f = FieldSchema(name="f", ttype="char", store=False, compute=None)
    _, _, _, extra = pydantic_field_str(f, frozenset(), _fn)
    assert "odoo_readonly" not in extra


def test_one2many_emits_odoo_x2many_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field("one2many"), frozenset(), _fn)
    assert extra.get("odoo_x2many") is True


def test_many2many_emits_odoo_x2many_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field("many2many"), frozenset(), _fn)
    assert extra.get("odoo_x2many") is True


def test_plain_writable_field_no_metadata() -> None:
    _, _, _, extra = pydantic_field_str(_field("char"), frozenset(), _fn)
    assert extra == {}


def test_readonly_x2many_emits_both_flags() -> None:
    f = FieldSchema(name="f", ttype="one2many", readonly=True)
    _, _, _, extra = pydantic_field_str(f, frozenset(), _fn)
    assert extra.get("odoo_readonly") is True
    assert extra.get("odoo_x2many") is True


def test_boolean_readonly_emits_odoo_readonly() -> None:
    _, _, _, extra = pydantic_field_str(_field_ro("boolean"), frozenset(), _fn)
    assert extra == {"odoo_readonly": True}
