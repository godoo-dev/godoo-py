"""PEP 593 Annotated metadata marker for generated TypedDict fields."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldMeta:
    """Metadata carrier for a generated TypedDict field.

    Carries the full ir.model.fields projection plus codegen-specific flags.
    Consumers extract via:
        typing.get_type_hints(MyTypedDict, include_extras=True)
    and walk metadata tuples looking for FieldMeta instances.

    Frozen and hashable — safe to use as dict keys or set elements.
    """

    ttype: str
    field_description: str = ""
    relation: str | None = None
    relation_field: str | None = None
    required: bool = False
    readonly: bool = False
    store: bool = True
    index: bool = False
    copy: bool = True
    translate: bool = False
    help: str = ""
    compute: str | None = None
    depends: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    on_delete: str | None = None
    size: int | None = None
    digits: tuple[int, int] | None = None
    # Codegen-specific flags
    original_ttype: str | None = None  # set when ttype is unmapped (D-Mapping-3)
    dynamic_selection: bool = False  # set when selection values not enumerable (D-Mapping-2)
