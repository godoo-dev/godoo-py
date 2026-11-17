"""Pydantic model emitter: transforms ModelSchema into a valid Python OdooBaseModel module string."""

from __future__ import annotations

import keyword
import logging
from typing import TYPE_CHECKING

from godoo.introspection.type_mapper import pydantic_field_str

if TYPE_CHECKING:
    from pathlib import Path

    from godoo.introspection.introspector import Introspector
    from godoo.introspection.types import FieldSchema, ModelSchema

logger = logging.getLogger("godoo_introspection.codegen")

# ------------------------------------------------------------------
# Module-level constants
# ------------------------------------------------------------------

# Pydantic reserved names that must not be used as field names in OdooBaseModel subclasses.
# Using any of these as a field name shadows Pydantic's own class-level API and causes
# silent or fatal misbehaviour (Finding #4).
_PYDANTIC_RESERVED_NAMES: frozenset[str] = frozenset(
    {
        "model_config",
        "model_fields",
        "model_validate",
        "model_dump",
        "model_rebuild",
        "model_post_init",
        "model_json_schema",
        "schema",
        "copy",
        "dict",
        "json",
    }
)


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _model_to_classname(model: str) -> str:
    """Convert 'res.partner' → 'ResPartner', 'account.move.line' → 'AccountMoveLine'.

    Raises:
        ValueError: if the resulting name is not a valid Python identifier
                    (e.g. '3d.model' → '3DModel' starts with a digit).
    """
    result = "".join(part.capitalize() for part in model.replace(".", "_").split("_"))
    if not result.isidentifier():
        raise ValueError(f"Model name {model!r} produces invalid Python identifier {result!r}")
    return result


def _model_to_filename(model: str) -> str:
    """Convert 'res.partner' → 'res_partner.py'."""
    return model.replace(".", "_") + ".py"


# ------------------------------------------------------------------
# CodeGenerator
# ------------------------------------------------------------------


def _skip_field_name(field_name: str) -> bool:
    # Security: validate field_name is a valid Python identifier (T-07-01)
    if not field_name.isidentifier():
        logger.warning("Field name %r is not a valid Python identifier — skipping", field_name)
        return True
    # Finding #5: skip Python keywords (e.g. 'class', 'return', 'import')
    if keyword.iskeyword(field_name):
        logger.warning("Field name %r is a Python keyword — skipping", field_name)
        return True
    # Finding #4: skip Pydantic reserved names (e.g. 'model_config', 'schema')
    if field_name in _PYDANTIC_RESERVED_NAMES:
        logger.warning("Field name %r is a Pydantic reserved name — skipping", field_name)
        return True
    return False


def _import_lines(needed: set[str], cross_imports: list[tuple[str, str]]) -> list[str]:
    lines: list[str] = []
    # Stdlib imports (date/datetime)
    stdlib = [name for name in ("date", "datetime") if name in needed]
    if stdlib:
        lines += [f"from datetime import {', '.join(stdlib)}", ""]
    # typing imports — always ClassVar, Optional; conditionally Literal, Any
    typing_names = ["ClassVar", "Optional", *(name for name in ("Literal", "Any") if name in needed)]
    lines += [f"from typing import {', '.join(typing_names)}", ""]
    # godoo imports
    lines.append("from godoo.client._pydantic_transform import OdooBaseModel")
    if "Ref" in needed:
        lines.append("from godoo.client.typed import Ref")
    if "Field" in needed:
        lines.append("from pydantic import Field")
    # Cross-imports for in-set many2one targets
    if cross_imports:
        lines.append("")
        lines += [f"from .{stem} import {target_class}" for stem, target_class in cross_imports]
    return lines


class CodeGenerator:
    """Transforms ModelSchema objects into valid Python OdooBaseModel module strings.

    Usage::

        gen = CodeGenerator(introspector, in_set=frozenset(model_names))
        source = gen.generate(schema)           # string
        gen.write([schema1, schema2], out_dir)  # write files

    The ``in_set`` argument is a frozenset of Odoo model names that will be
    generated. many2one fields whose target is in ``in_set`` emit
    ``Optional[Ref[TargetClass]]`` with a cross-import; those whose target is
    not in ``in_set`` degrade to ``Optional[Ref[int]]`` with a trailing comment.

    Note on circular imports: all in-set many2one relations are emitted as
    regular imports (not ``TYPE_CHECKING`` guards). This is safe because
    ``from __future__ import annotations`` defers all annotation evaluation,
    so circular regular imports are safe at class-definition time for the
    annotation use case. A full circular-detection second pass is out of scope
    for Phase 7.
    """

    def __init__(self, introspector: Introspector, in_set: frozenset[str] = frozenset()) -> None:
        self._introspector = introspector
        self._in_set = in_set

    def generate(self, schema: ModelSchema) -> str:
        """Return a valid Python module string for one model.

        The output subclasses ``OdooBaseModel`` and carries:
        - ``__odoo_model__: ClassVar[str]`` set to the Odoo technical name
        - ``id: int | None = None`` — optional so instances can be built for ``create()``;
          ``_serialize_for_write`` drops ``id`` from the payload regardless, and Odoo always
          returns ``id`` on reads so the field is always populated after a round-trip.
        - Per non-id field: ``Optional[T] = None`` or appropriate Pydantic form

        Raises:
            ValueError: if the model name produces an invalid Python class name.
        """
        class_name = _model_to_classname(schema.name)

        # Collect non-id field lines, the import names they need (GEN-01) and
        # cross-imports for in-set m2o targets as (stem, classname).
        field_lines: list[str] = []
        needed: set[str] = set()
        cross_imports: list[tuple[str, str]] = []
        for field_name, fs in schema.fields.items():
            if field_name == "id" or _skip_field_name(field_name):
                continue
            line, imports = self._field_line(field_name, fs)
            field_lines.append(line)
            needed |= imports
            entry = self._cross_import(fs)
            if entry is not None and entry not in cross_imports:
                cross_imports.append(entry)

        # -- Assemble the file --
        lines = [
            "# AUTOGENERATED by godoo-introspection - do not edit manually.",
            f"# Model: {schema.name}",
            "",
            "from __future__ import annotations",
            "",
            *_import_lines(needed, cross_imports),
            # Two blank lines before class
            "",
            "",
            f"class {class_name}(OdooBaseModel):",
            f'    __odoo_model__: ClassVar[str] = "{schema.name}"',
            "",
            # id field — optional so instances can be constructed for create();
            # _serialize_for_write drops id from write/create payloads regardless.
            "    id: int | None = None",
            *field_lines,
        ]
        # If no non-id fields, emit pass
        if not field_lines:
            lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    def _field_line(self, field_name: str, fs: FieldSchema) -> tuple[str, set[str]]:
        # Finding #10: structural import detection — unpack 4-tuple from type_mapper (GEN-01)
        annotation, default, imports, extra = pydantic_field_str(fs, self._in_set, _model_to_classname)
        needed = set(imports)
        # GEN-01: emit Field() with json_schema_extra when metadata is present
        if extra:
            if default == "[]":
                # x2many: use default_factory=list to avoid PydanticUserError (mutable default)
                default_expr = f"Field(default_factory=list, json_schema_extra={extra!r})"
            else:
                # Strip any trailing inline comment (e.g. "None  # res.users") before
                # embedding the default inside Field(...).  The comment is harmless on a
                # bare assignment line but breaks Python syntax inside a function call.
                bare_default = default.split("#")[0].rstrip()
                default_expr = f"Field(default={bare_default}, json_schema_extra={extra!r})"
            needed.add("Field")
        else:
            default_expr = default
        return f"    {field_name}: {annotation} = {default_expr}", needed

    def _cross_import(self, fs: FieldSchema) -> tuple[str, str] | None:
        # Structural: reads fs.ttype directly
        if fs.ttype == "many2one" and fs.relation and fs.relation in self._in_set:
            return _model_to_filename(fs.relation)[:-3], _model_to_classname(fs.relation)
        return None

    def write(self, schemas: list[ModelSchema], output_dir: Path) -> None:
        """Write one .py file per schema plus an __init__.py barrel in output_dir.

        Raises ValueError if output_dir is not an existing directory.
        """
        # Security: validate output_dir before any write (T-07-01)
        if not output_dir.is_dir():
            raise ValueError(f"output_dir {output_dir!r} is not a directory")

        class_names: list[tuple[str, str]] = []  # (stem, class_name)

        for schema in schemas:
            source = self.generate(schema)
            filename = _model_to_filename(schema.name)
            stem = filename[:-3]  # remove .py
            class_name = _model_to_classname(schema.name)
            # Finding #9: always write LF line endings (newline="\n") on all platforms
            (output_dir / filename).write_text(source, encoding="utf-8", newline="\n")
            class_names.append((stem, class_name))
            logger.debug("Wrote %s → %s", schema.name, filename)

        # Generate barrel __init__.py
        barrel_lines = [
            "# AUTOGENERATED by godoo-introspection — do not edit manually.",
            "",
        ]
        for stem, class_name in class_names:
            barrel_lines.append(f"from .{stem} import {class_name}")
        barrel_lines.append("")
        barrel_lines.append("__all__ = [")
        for _, class_name in class_names:
            barrel_lines.append(f'    "{class_name}",')
        barrel_lines.append("]")
        barrel_lines.append("")

        # Finding #9: always write LF line endings (newline="\n") on all platforms
        (output_dir / "__init__.py").write_text("\n".join(barrel_lines), encoding="utf-8", newline="\n")
        logger.debug("Wrote __init__.py barrel with %d exports", len(class_names))
