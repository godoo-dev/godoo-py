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
    id_lines = [ln for ln in lines if ln.strip().startswith("id:")]
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


# ---------------------------------------------------------------------------
# Finding #4 — Reserved Pydantic names guard
# ---------------------------------------------------------------------------


def test_generate_reserved_name_skipped() -> None:
    """Fields named after Pydantic reserved names (e.g. 'model_config') are skipped."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", model_config=_char_field("model_config"))
    result = gen.generate(schema)
    # The field should NOT appear as a field declaration
    lines = result.splitlines()
    field_lines = [ln for ln in lines if ln.strip().startswith("model_config:")]
    assert len(field_lines) == 0, f"'model_config' field should be skipped, got lines: {field_lines}"


# ---------------------------------------------------------------------------
# Finding #5 — Python keyword guard
# ---------------------------------------------------------------------------


def test_generate_keyword_field_skipped() -> None:
    """Fields named after Python keywords (e.g. 'class') are skipped."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", **{"class": _char_field("class")})
    result = gen.generate(schema)
    # The field 'class' must not appear as a field declaration
    assert "class:" not in result, f"'class:' field should be skipped in:\n{result}"


# ---------------------------------------------------------------------------
# Finding #8 — Class name validation
# ---------------------------------------------------------------------------


def test_invalid_classname_raises() -> None:
    """_model_to_classname raises ValueError for model names producing invalid identifiers."""
    with pytest.raises(ValueError, match="invalid Python identifier"):
        _model_to_classname("3d.model")


def test_generate_invalid_classname_propagates() -> None:
    """CodeGenerator.generate propagates ValueError for a model with an invalid class name."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("3d.model")
    with pytest.raises(ValueError, match="invalid Python identifier"):
        gen.generate(schema)


# ---------------------------------------------------------------------------
# Finding #9 — LF newlines on all platforms
# ---------------------------------------------------------------------------


def test_write_newline_lf(tmp_path: Path) -> None:
    """Written .py files use LF line endings on all platforms (no CRLF bytes)."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"))
    gen.write([schema], tmp_path)
    content = (tmp_path / "res_partner.py").read_bytes()
    assert b"\r\n" not in content, "File must not contain CRLF line endings"
    init_content = (tmp_path / "__init__.py").read_bytes()
    assert b"\r\n" not in init_content, "__init__.py must not contain CRLF line endings"


# ---------------------------------------------------------------------------
# Finding #10 — Structural imports from type_mapper
# ---------------------------------------------------------------------------


def _date_field(fname: str = "create_date") -> FieldSchema:
    return FieldSchema(name=fname, ttype="date")


def _datetime_field(fname: str = "write_date") -> FieldSchema:
    return FieldSchema(name=fname, ttype="datetime")


def _json_field(fname: str = "metadata") -> FieldSchema:
    return FieldSchema(name=fname, ttype="json")


def test_type_mapper_returns_imports_set() -> None:
    """pydantic_field_str returns a 3-tuple (annotation, default, imports_set)."""
    from godoo.introspection.type_mapper import pydantic_field_str

    # date field
    _ann, _default, imports = pydantic_field_str(_date_field(), frozenset(), _model_to_classname)
    assert "date" in imports, f"date field should have 'date' in imports, got {imports}"

    # datetime field
    _ann, _default, imports = pydantic_field_str(_datetime_field(), frozenset(), _model_to_classname)
    assert "datetime" in imports, f"datetime field should have 'datetime' in imports, got {imports}"

    # selection field with static values
    _ann, _default, imports = pydantic_field_str(_selection_field(), frozenset(), _model_to_classname)
    assert "Literal" in imports, f"selection field should have 'Literal' in imports, got {imports}"

    # json field
    _ann, _default, imports = pydantic_field_str(_json_field(), frozenset(), _model_to_classname)
    assert "Any" in imports, f"json field should have 'Any' in imports, got {imports}"

    # many2one field
    _ann, _default, imports = pydantic_field_str(
        _m2o_field("partner_id", "res.partner"), frozenset(), _model_to_classname
    )
    assert "Ref" in imports, f"m2o field should have 'Ref' in imports, got {imports}"

    # char field — no special imports
    _ann, _default, imports = pydantic_field_str(_char_field(), frozenset(), _model_to_classname)
    assert len(imports) == 0, f"char field should have empty imports, got {imports}"


def test_generate_date_import_via_structural(tmp_path: Path) -> None:
    """Schema with a date field generates 'from datetime import date' in source (structural import)."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", create_date=_date_field("create_date"))
    result = gen.generate(schema)
    assert "from datetime import date" in result, f"Expected 'from datetime import date' in:\n{result}"
