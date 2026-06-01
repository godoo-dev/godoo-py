"""Tests for CodeGenerator (Pydantic emitter)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from godoo.introspection.codegen import CodeGenerator, _model_to_classname, _model_to_filename
from godoo.introspection.types import FieldSchema, ModelSchema


def _schema(model_name: str = "res.partner", **fields: FieldSchema) -> ModelSchema:
    """Build a minimal ModelSchema for testing."""
    return ModelSchema(name=model_name, fields=dict(fields))


def _char_field(fname: str = "name") -> FieldSchema:
    return FieldSchema(name=fname, ttype="char")


def _bool_field(fname: str = "active") -> FieldSchema:
    return FieldSchema(name=fname, ttype="boolean")


def _selection_field(fname: str = "state") -> FieldSchema:
    return FieldSchema(
        name=fname,
        ttype="selection",
        selection=[("draft", "Draft"), ("done", "Done")],
    )


def _m2o_field(fname: str, relation: str) -> FieldSchema:
    return FieldSchema(name=fname, ttype="many2one", relation=relation)


# ---------------------------------------------------------------------------
# Preserved helpers (classname and filename)
# ---------------------------------------------------------------------------


def test_model_to_classname() -> None:
    assert _model_to_classname("res.partner") == "ResPartner"
    assert _model_to_classname("account.move.line") == "AccountMoveLine"
    assert _model_to_classname("ir.model.fields") == "IrModelFields"


def test_model_to_filename() -> None:
    assert _model_to_filename("res.partner") == "res_partner.py"
    assert _model_to_filename("account.move.line") == "account_move_line.py"


# ---------------------------------------------------------------------------
# Pydantic-specific generate() tests
# ---------------------------------------------------------------------------


def test_generate_pydantic_class_name() -> None:
    """Generated source has correct Pydantic class declaration."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner")
    result = gen.generate(schema)
    assert "class ResPartner(OdooBaseModel):" in result


def test_generate_odoo_model_classvar() -> None:
    """Generated source has __odoo_model__ ClassVar with double quotes."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner")
    result = gen.generate(schema)
    assert '__odoo_model__: ClassVar[str] = "res.partner"' in result


def test_generate_id_plain_int() -> None:
    """id field emits as plain int — no Optional, no default."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", id=FieldSchema(name="id", ttype="integer"))
    result = gen.generate(schema)
    assert "    id: int" in result
    # Must NOT have Optional[int] or default for id
    lines = result.splitlines()
    id_lines = [l for l in lines if l.strip().startswith("id:")]
    assert len(id_lines) == 1
    assert "Optional" not in id_lines[0]
    assert "=" not in id_lines[0]


def test_generate_optional_char() -> None:
    """char field emits as Optional[str] = None."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"))
    result = gen.generate(schema)
    assert "    name: Optional[str] = None" in result


def test_generate_bool_non_optional() -> None:
    """boolean field emits as bool = False (not Optional)."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", active=_bool_field("active"))
    result = gen.generate(schema)
    assert "    active: bool = False" in result


def test_generate_selection_literal() -> None:
    """static selection field emits Optional[Literal[...]] = None."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", state=_selection_field("state"))
    result = gen.generate(schema)
    assert "Optional[Literal[" in result
    assert "= None" in result


def test_generate_no_field_meta() -> None:
    """Generated source contains no TypedDict, FieldMeta, markers, NotRequired, Required."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"))
    result = gen.generate(schema)
    assert "FieldMeta" not in result
    assert "TypedDict" not in result
    assert "markers" not in result
    assert "NotRequired" not in result
    assert "Required" not in result


def test_generate_valid_python_compiles() -> None:
    """Generated source compiles without SyntaxError."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema(
        "res.partner",
        name=_char_field("name"),
        active=_bool_field("active"),
        state=_selection_field("state"),
    )
    result = gen.generate(schema)
    compile(result, "<string>", "exec")


def test_generate_many2one_in_set_cross_import() -> None:
    """many2one in in_set emits cross-import and Optional[Ref[TargetClass]]."""
    gen = CodeGenerator(None, in_set=frozenset({"res.country"}))  # type: ignore[arg-type]
    schema = _schema("res.partner", country_id=_m2o_field("country_id", "res.country"))
    result = gen.generate(schema)
    assert "from .res_country import ResCountry" in result
    assert "Optional[Ref[ResCountry]]" in result


def test_generate_many2one_not_in_set_degraded() -> None:
    """many2one not in in_set emits Optional[Ref[int]] with trailing # model comment."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", company_id=_m2o_field("company_id", "res.company"))
    result = gen.generate(schema)
    assert "Optional[Ref[int]]" in result
    assert "# res.company" in result


def test_generate_importlib_roundtrip(tmp_path: Path) -> None:
    """Full importlib roundtrip: loaded module has correct __odoo_model__ attribute."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"))
    result = gen.generate(schema)
    mod_file = tmp_path / "res_partner.py"
    mod_file.write_text(result, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("res_partner_test", mod_file)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    assert hasattr(mod.ResPartner, "__odoo_model__")
    assert mod.ResPartner.__odoo_model__ == "res.partner"


def test_generate_empty_schema_has_id_and_pass() -> None:
    """Schema with no fields emits id: int and pass."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = ModelSchema(name="res.empty", fields={})
    result = gen.generate(schema)
    assert "    id: int" in result
    assert "pass" in result


def test_generate_header() -> None:
    """Generated source includes AUTOGENERATED header and from __future__ import annotations."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema()
    result = gen.generate(schema)
    assert "AUTOGENERATED" in result
    assert "from __future__ import annotations" in result


# ---------------------------------------------------------------------------
# Preserved write() tests
# ---------------------------------------------------------------------------


def test_write_creates_files(tmp_path: Path) -> None:
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"))
    gen.write([schema], tmp_path)
    assert (tmp_path / "res_partner.py").exists()
    content = (tmp_path / "res_partner.py").read_text()
    assert "ResPartner" in content


def test_write_creates_init(tmp_path: Path) -> None:
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"))
    gen.write([schema], tmp_path)
    init_file = tmp_path / "__init__.py"
    assert init_file.exists()
    content = init_file.read_text()
    assert "ResPartner" in content


def test_write_invalid_dir_raises(tmp_path: Path) -> None:
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema()
    with pytest.raises(ValueError, match="not a directory"):
        gen.write([schema], Path("/nonexistent/path"))
