"""Pydantic model emitter: transforms ModelSchema into a valid Python OdooBaseModel module string."""

from __future__ import annotations

import keyword
import logging
from typing import TYPE_CHECKING

from godoo.introspection.type_mapper import pydantic_field_str

if TYPE_CHECKING:
    from pathlib import Path

    from godoo.introspection.introspector import Introspector
    from godoo.introspection.types import ModelSchema

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

        # -- Track which imports are needed as we process fields --
        need_date = False
        need_datetime = False
        need_literal = False
        need_any = False
        need_ref = False
        need_field_import = False  # set to True when any field carries extra metadata (GEN-01)
        cross_imports: list[tuple[str, str]] = []  # (stem, classname) for in-set m2o targets

        # Collect non-id field lines
        field_lines: list[str] = []
        non_id_fields = [(fn, fs) for fn, fs in schema.fields.items() if fn != "id"]

        for field_name, fs in non_id_fields:
            # Security: validate field_name is a valid Python identifier (T-07-01)
            if not field_name.isidentifier():
                logger.warning("Field name %r is not a valid Python identifier — skipping", field_name)
                continue

            # Finding #5: skip Python keywords (e.g. 'class', 'return', 'import')
            if keyword.iskeyword(field_name):
                logger.warning("Field name %r is a Python keyword — skipping", field_name)
                continue

            # Finding #4: skip Pydantic reserved names (e.g. 'model_config', 'schema')
            if field_name in _PYDANTIC_RESERVED_NAMES:
                logger.warning("Field name %r is a Pydantic reserved name — skipping", field_name)
                continue

            # Finding #10: structural import detection — unpack 4-tuple from type_mapper (GEN-01)
            annotation, default, imports, extra = pydantic_field_str(fs, self._in_set, _model_to_classname)

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
                need_field_import = True
            else:
                default_expr = default
            field_lines.append(f"    {field_name}: {annotation} = {default_expr}")

            # Track imports needed — set-membership checks on the imports frozenset
            need_date |= "date" in imports
            need_datetime |= "datetime" in imports
            need_literal |= "Literal" in imports
            need_any |= "Any" in imports
            need_ref |= "Ref" in imports

            # Track cross-imports for in-set m2o targets (structural, reads fs.ttype directly)
            if fs.ttype == "many2one" and fs.relation and fs.relation in self._in_set:
                stem = _model_to_filename(fs.relation)[:-3]
                target_class = _model_to_classname(fs.relation)
                entry = (stem, target_class)
                if entry not in cross_imports:
                    cross_imports.append(entry)

        # -- Assemble the file --
        lines: list[str] = []

        # Header comments
        lines.append("# AUTOGENERATED by godoo-introspection - do not edit manually.")
        lines.append(f"# Model: {schema.name}")
        lines.append("")

        # Future imports
        lines.append("from __future__ import annotations")
        lines.append("")

        # Stdlib imports (date/datetime)
        if need_date and need_datetime:
            lines.append("from datetime import date, datetime")
            lines.append("")
        elif need_datetime:
            lines.append("from datetime import datetime")
            lines.append("")
        elif need_date:
            lines.append("from datetime import date")
            lines.append("")

        # typing imports — always ClassVar, Optional; conditionally Literal, Any
        typing_names = ["ClassVar", "Optional"]
        if need_literal:
            typing_names.append("Literal")
        if need_any:
            typing_names.append("Any")
        lines.append(f"from typing import {', '.join(typing_names)}")
        lines.append("")

        # godoo imports
        lines.append("from godoo.client._pydantic_transform import OdooBaseModel")
        if need_ref:
            lines.append("from godoo.client.typed import Ref")
        if need_field_import:
            lines.append("from pydantic import Field")

        # Cross-imports for in-set many2one targets
        if cross_imports:
            lines.append("")
            for stem, target_class in cross_imports:
                lines.append(f"from .{stem} import {target_class}")

        # Two blank lines before class
        lines.append("")
        lines.append("")

        # Class definition
        lines.append(f"class {class_name}(OdooBaseModel):")
        lines.append(f'    __odoo_model__: ClassVar[str] = "{schema.name}"')
        lines.append("")

        # id field — optional so instances can be constructed for create();
        # _serialize_for_write drops id from write/create payloads regardless.
        lines.append("    id: int | None = None")

        # Non-id fields
        for fl in field_lines:
            lines.append(fl)

        # If no non-id fields, emit pass
        if not field_lines:
            lines.append("    pass")

        lines.append("")
        return "\n".join(lines)

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
