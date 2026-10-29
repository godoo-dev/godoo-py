"""Runtime property definitions, value views and mutation outcomes."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from godoo.client.errors import OdooNetworkError, OdooValidationError

if TYPE_CHECKING:
    from .binding import PropertyBinding
    from .scope import PropertyScope


class PropertyLookupError(OdooValidationError):
    """A label or technical selector is missing or ambiguous."""


class PropertyValueError(OdooValidationError):
    """A property declaration or value has an unsupported shape."""


class PropertyScopeError(OdooValidationError):
    """A record or authenticated identity no longer belongs to this scope."""


class PropertyDriftError(OdooValidationError):
    """A retained property or option ID has disappeared or changed incompatibly."""


class PropertyWriteUnknownError(OdooNetworkError):
    """A write may have taken effect; callers must reconcile before retrying."""

    def __init__(self, record_id: int, *, cause: Exception | None = None) -> None:
        self.record_id = record_id
        super().__init__(
            f"Property write outcome is unknown for record {record_id}; do not retry automatically.", cause=cause
        )


@dataclass(frozen=True)
class PropertyOption:
    id: str
    label: str
    color: int | None = None


@dataclass(frozen=True)
class PropertyOptions(Mapping[str, PropertyOption]):
    _entries: tuple[PropertyOption, ...] = ()

    def __getitem__(self, key: str) -> PropertyOption:
        for option in self._entries:
            if option.id == key:
                return option
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (option.id for option in self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def by_label(self, label: str) -> PropertyOption:
        return _by_label(self._entries, label)


@dataclass(frozen=True)
class PropertyDefinition:
    id: str
    label: str
    type: str
    comodel: str | None = None
    options: PropertyOptions = field(default_factory=PropertyOptions)


def _by_label[T: (PropertyOption, PropertyDefinition)](entries: tuple[T, ...], label: str) -> T:
    matches = [entry for entry in entries if entry.label == label]
    if len(matches) != 1:
        raise PropertyLookupError(f"Expected one property/option labelled {label!r}; found {len(matches)}.")
    return matches[0]


@dataclass(frozen=True)
class PropertyDefinitions(Mapping[str, PropertyDefinition]):
    _entries: tuple[PropertyDefinition, ...]
    _scope: PropertyScope = field(repr=False, compare=False)

    def __getitem__(self, key: str) -> PropertyDefinition:
        for definition in self._entries:
            if definition.id == key:
                return definition
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (definition.id for definition in self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def by_label(self, label: str) -> PropertyDefinition:
        return _by_label(self._entries, label)

    @property
    def parent_id(self) -> int:
        return self._scope.parent_id

    @property
    def parent_field(self) -> str:
        return self._scope.parent_field

    @property
    def definition_field(self) -> str:
        return self._scope.definition_field

    @property
    def context(self) -> dict[str, Any]:
        return deepcopy(self._scope.context)

    def bind(self, aliases: Mapping[str, Mapping[str, Any]]) -> PropertyBinding:
        from .binding import PropertyBinding

        return PropertyBinding(self, aliases)


class PropertyValues(Mapping[str, Any]):
    """Technical-ID mapping with an optional, separate attribute alias projection."""

    def __init__(self, values: Mapping[str, Any], aliases: Mapping[str, Any] | None = None) -> None:
        self._values = deepcopy(dict(values))
        self._aliases = deepcopy(dict(aliases or {}))

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __getattr__(self, alias: str) -> Any:
        try:
            return self._aliases[alias]
        except KeyError:
            raise AttributeError(alias) from None


@dataclass(frozen=True)
class PropertyRecord:
    id: int
    record: dict[str, Any]
    properties: PropertyValues
    property_definitions: PropertyDefinitions


@dataclass(frozen=True)
class PropertyReceipt:
    record_id: int
    status: Literal["acknowledged", "failed", "unknown"]
    error: Exception | None = None


class PropertyBatchError(OdooValidationError):
    """Legacy batch failure retaining every observed per-record outcome."""

    def __init__(self, receipts: list[PropertyReceipt]) -> None:
        super().__init__("Legacy property batch has incomplete writes; inspect receipts before retrying.")
        self.receipts = receipts


class PropertyBatchCancelledError(asyncio.CancelledError):
    """Cancellation retaining observed outcomes and IDs never dispatched."""

    def __init__(self, receipts: list[PropertyReceipt], undispatched_ids: list[int]) -> None:
        super().__init__("Property batch cancelled; reconcile unknown writes before retrying.")
        self.receipts = receipts
        self.undispatched_ids = undispatched_ids
