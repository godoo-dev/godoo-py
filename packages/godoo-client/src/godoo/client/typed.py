"""Stdlib-only typed-model primitives. Importable without pydantic [typed] extra."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Protocol


class OdooModel(Protocol):
    """Marker protocol for typed Odoo model classes.

    Concrete classes (emitted by Phase 7 codegen) declare:
        __odoo_model__: ClassVar[str] = "res.partner"

    Runtime dispatch in OdooClient.read/search_read keys on
    hasattr(model, "__odoo_model__") — never on isinstance(BaseModel) (D-04).
    """

    __odoo_model__: ClassVar[str]


@dataclass(frozen=True)
class Ref[T]:
    """Typed many2one reference: numeric id + display name.

    ``name`` is ``str | None`` to handle restricted display names — Odoo
    returns ``[id, False]`` when the current user cannot read the related
    record's display name. The wire transform sets ``name=None`` in that case.
    """

    id: int
    name: str | None
    _target_cls: type | None = field(default=None, compare=False, hash=False, repr=False)
    """Runtime target class; excluded from equality, hash, and repr."""


__all__ = ["OdooModel", "Ref"]
