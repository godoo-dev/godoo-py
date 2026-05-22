"""ModelSchema and FieldSchema dataclasses — typed schema representations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldSchema:
    """Raw ir.model.fields projection — all columns from search_read.

    Frozen and immutable. The `selection` field is a list but accepted by
    frozen=True (though it makes instances non-hashable).
    """

    name: str
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
    selection: list[tuple[str, str]] = field(default_factory=list)
    # ^ list of (value, label) tuples from ir.model.fields.selection records


@dataclass  # NOT frozen=True — ModelSchema has a dict field (unhashable; see Pitfall 6)
class ModelSchema:
    """Typed schema for one Odoo model, returned by Introspector.get_schema()."""

    name: str  # technical model name, e.g. 'res.partner'
    display_name: str = ""  # human label from ir.model.name
    transient: bool = False
    fields: dict[str, FieldSchema] = field(default_factory=dict)
