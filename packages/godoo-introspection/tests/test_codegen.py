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


def test_generate_id_optional_with_none_default() -> None:
    """id field emits as int | None = None — optional so instances can be built for create()."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", id=FieldSchema(name="id", ttype="integer"))
    result = gen.generate(schema)
    assert "    id: int | None = None" in result
    # Must NOT be a required int with no default
    lines = result.splitlines()
    id_lines = [ln for ln in lines if ln.strip().startswith("id:")]
    assert len(id_lines) == 1
    assert "None" in id_lines[0]


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
    """Schema with no fields emits id: int | None = None and pass."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = ModelSchema(name="res.empty", fields={})
    result = gen.generate(schema)
    assert "    id: int | None = None" in result
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
    """pydantic_field_str returns a 4-tuple (annotation, default, imports_set, extra_dict)."""
    from godoo.introspection.type_mapper import pydantic_field_str

    # date field
    _ann, _default, imports, _ = pydantic_field_str(_date_field(), frozenset(), _model_to_classname)
    assert "date" in imports, f"date field should have 'date' in imports, got {imports}"

    # datetime field
    _ann, _default, imports, _ = pydantic_field_str(_datetime_field(), frozenset(), _model_to_classname)
    assert "datetime" in imports, f"datetime field should have 'datetime' in imports, got {imports}"

    # selection field with static values
    _ann, _default, imports, _ = pydantic_field_str(_selection_field(), frozenset(), _model_to_classname)
    assert "Literal" in imports, f"selection field should have 'Literal' in imports, got {imports}"

    # json field
    _ann, _default, imports, _ = pydantic_field_str(_json_field(), frozenset(), _model_to_classname)
    assert "Any" in imports, f"json field should have 'Any' in imports, got {imports}"

    # many2one field
    _ann, _default, imports, _ = pydantic_field_str(
        _m2o_field("partner_id", "res.partner"), frozenset(), _model_to_classname
    )
    assert "Ref" in imports, f"m2o field should have 'Ref' in imports, got {imports}"

    # char field — no special imports
    _ann, _default, imports, _ = pydantic_field_str(_char_field(), frozenset(), _model_to_classname)
    assert len(imports) == 0, f"char field should have empty imports, got {imports}"


def test_generate_date_import_via_structural(tmp_path: Path) -> None:
    """Schema with a date field generates 'from datetime import date' in source (structural import)."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", create_date=_date_field("create_date"))
    result = gen.generate(schema)
    assert "from datetime import date" in result, f"Expected 'from datetime import date' in:\n{result}"


# ---------------------------------------------------------------------------
# GEN-01 codegen emission — Task 2
# ---------------------------------------------------------------------------


def _readonly_field(fname: str = "state") -> FieldSchema:
    return FieldSchema(name=fname, ttype="char", readonly=True)


def _x2many_field(fname: str = "line_ids") -> FieldSchema:
    return FieldSchema(name=fname, ttype="one2many")


def test_readonly_field_emits_field_with_json_schema_extra() -> None:
    """Readonly field generates Field(default=None, json_schema_extra={'odoo_readonly': True})."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", state=_readonly_field("state"))
    result = gen.generate(schema)
    assert "json_schema_extra=" in result, f"Expected json_schema_extra in:\n{result}"
    assert "'odoo_readonly': True" in result, f"Expected odoo_readonly metadata in:\n{result}"


def test_x2many_field_emits_default_factory() -> None:
    """x2many field generates Field(default_factory=list, ...) not Field(default=[], ...)."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", line_ids=_x2many_field("line_ids"))
    result = gen.generate(schema)
    assert "Field(default_factory=list" in result, f"Expected default_factory=list in:\n{result}"
    # Must NOT use mutable default — PydanticUserError at import time
    assert "= []" not in result, f"Must not use mutable default '= []' in:\n{result}"


def test_field_import_added_when_metadata_present() -> None:
    """'from pydantic import Field' appears when any field carries metadata."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", state=_readonly_field("state"))
    result = gen.generate(schema)
    assert "from pydantic import Field" in result, f"Expected pydantic Field import in:\n{result}"


def test_no_field_import_when_no_metadata() -> None:
    """'from pydantic import Field' is absent for all-plain-scalar models."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"), active=_bool_field("active"))
    result = gen.generate(schema)
    assert "from pydantic import Field" not in result, f"Field import must be absent in:\n{result}"


# ---------------------------------------------------------------------------
# Regression — readonly many2one OUTSIDE in_set must not break Field() syntax
# ---------------------------------------------------------------------------


def test_readonly_m2o_not_in_set_generates_valid_python() -> None:
    """Regression (11-01): a readonly many2one whose target is OUTSIDE in_set compiles.

    The degraded not-in-set m2o branch returns a default carrying a trailing inline
    comment ('None  # res.users'). When that field ALSO carries metadata (readonly),
    the default is embedded inside Field(default=..., json_schema_extra=...). The inline
    comment, harmless on a bare assignment line, terminates the Field(...) call early and
    produces a SyntaxError. This guards that the comment is stripped before embedding.
    """
    gen = CodeGenerator(None)  # type: ignore[arg-type]  # empty in_set → m2o degrades to Ref[int]
    # create_uid is the canonical real-world case: readonly + many2one to res.users
    create_uid = FieldSchema(name="create_uid", ttype="many2one", relation="res.users", readonly=True)
    schema = _schema("res.partner", create_uid=create_uid)
    source = gen.generate(schema)

    # The degraded m2o still emits Ref[int] and a Field() with readonly metadata
    assert "Optional[Ref[int]]" in source
    assert "'odoo_readonly': True" in source
    # The bare inline comment must NOT survive inside the Field() call
    assert "Field(default=None  #" not in source, f"inline comment leaked into Field():\n{source}"

    # Core assertion: the generated source must be syntactically valid Python.
    compile(source, "<gen>", "exec")

    # And it must actually build into a usable class (exec + model_rebuild).
    ns: dict[str, object] = {}
    exec(source, ns)  # trusted codegen output
    ResPartner = ns["ResPartner"]
    ResPartner.model_rebuild(_types_namespace=ns)  # type: ignore[attr-defined]
    instance = ResPartner(name="Acme")  # type: ignore[call-arg]
    assert instance.create_uid is None  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# CR-02 contract: generated class can be instantiated without id (create path)
# ---------------------------------------------------------------------------


def test_generated_class_instantiable_without_id() -> None:
    """A generated class (exec'd) can be instantiated without id — create() contract (a).

    id defaults to None so ResPartner(name='X') works without a bogus id sentinel.
    This exercises the actual codegen output, not a hand-written fixture.

    model_rebuild(_types_namespace=ns) is called so pydantic can resolve deferred
    annotations from ``from __future__ import annotations`` in the generated source.
    """
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema(
        "res.partner",
        name=_char_field("name"),
        active=_bool_field("active"),
    )
    source = gen.generate(schema)
    ns: dict[str, object] = {}
    exec(source, ns)  # source is our own trusted codegen output
    ResPartner = ns["ResPartner"]
    ResPartner.model_rebuild(_types_namespace=ns)  # type: ignore[attr-defined]

    # Contract (a): instantiation without id must not raise
    instance = ResPartner(name="Acme Corp")  # type: ignore[call-arg]
    assert instance.id is None  # type: ignore[union-attr]
    assert instance.name == "Acme Corp"  # type: ignore[attr-defined]


def test_generated_class_id_is_optional_in_source() -> None:
    """Generated source contains 'id: int | None = None', never 'id: int' with no default."""
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    schema = _schema("res.partner", name=_char_field("name"))
    source = gen.generate(schema)
    lines = source.splitlines()
    id_lines = [ln for ln in lines if "id:" in ln and not ln.strip().startswith("#")]
    # Only the field declaration line — must be optional with default
    assert any("id: int | None = None" in ln for ln in id_lines), (
        f"Expected 'id: int | None = None' in generated source; id lines: {id_lines}"
    )
