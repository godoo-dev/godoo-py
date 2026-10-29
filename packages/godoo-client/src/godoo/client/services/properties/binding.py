"""Optional application aliases over runtime-discovered properties."""

from __future__ import annotations

import keyword
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, overload

from .codec import decode_values, encode_values, value_for
from .mutations import dispatch, require_acknowledged
from .scope import load_definitions, parent_id_for, read_rows, record_ids
from .types import (
    PropertyDefinition,
    PropertyDefinitions,
    PropertyDriftError,
    PropertyLookupError,
    PropertyOptions,
    PropertyReceipt,
    PropertyRecord,
    PropertyValueError,
    PropertyValues,
)


@dataclass(frozen=True)
class _Alias:
    definition: PropertyDefinition
    options: dict[str, str] | None


def _select(collection: PropertyDefinitions | PropertyOptions, selector: Any) -> Any:
    if not isinstance(selector, Mapping) or set(selector) not in ({"id"}, {"label"}):
        raise PropertyValueError("A selector must contain exactly one of id or label.")
    key, value = next(iter(selector.items()))
    if not isinstance(value, str) or not value:
        raise PropertyValueError("Selectors must be nonempty strings.")
    if key == "label":
        return collection.by_label(value)
    try:
        return collection[value]
    except KeyError:
        raise PropertyLookupError(f"Unknown property/option ID {value!r}.") from None


def _alias_name(alias: str, technical_ids: Mapping[str, Any], used: set[str]) -> None:
    if (
        not isinstance(alias, str)
        or not alias.isidentifier()
        or alias.startswith("_")
        or keyword.iskeyword(alias)
        or alias in dir(PropertyValues)
        or alias in technical_ids
        or alias in used
    ):
        raise PropertyValueError(f"Invalid or colliding alias {alias!r}.")


class PropertyBinding:
    """A fixed parent/context and stable technical-ID mapping; no static schema required."""

    def __init__(self, definitions: PropertyDefinitions, aliases: Mapping[str, Mapping[str, Any]]) -> None:
        definitions._scope.check_identity()
        self._definitions = definitions
        self._aliases: dict[str, _Alias] = {}
        property_ids: set[str] = set()
        for alias, spec in deepcopy(dict(aliases)).items():
            _alias_name(alias, definitions, set())
            if not isinstance(spec, Mapping) or set(spec) - {"id", "label", "options"}:
                raise PropertyValueError(f"Malformed alias declaration {alias!r}.")
            definition = _select(definitions, {k: v for k, v in spec.items() if k != "options"})
            if definition.id in property_ids or definition.type == "separator":
                raise PropertyValueError("Aliases must target distinct writable properties.")
            option_map = None
            if "options" in spec:
                if definition.type not in ("selection", "tags") or not isinstance(spec["options"], Mapping):
                    raise PropertyValueError("Option aliases require a selection or tags property.")
                option_map = {}
                option_ids: set[str] = set()
                for option_alias, selector in spec["options"].items():
                    _alias_name(option_alias, definition.options, set())
                    option = _select(definition.options, selector)
                    if option.id in option_ids:
                        raise PropertyValueError("Multiple option aliases target the same technical ID.")
                    option_map[option_alias] = option.id
                    option_ids.add(option.id)
            self._aliases[alias] = _Alias(definition, option_map)
            property_ids.add(definition.id)

    @property
    def property_definitions(self) -> PropertyDefinitions:
        return self._definitions

    def inspect(self) -> dict[str, Any]:
        return {
            alias: {
                "id": entry.definition.id,
                "type": entry.definition.type,
                "comodel": entry.definition.comodel,
                "options": deepcopy(entry.options),
            }
            for alias, entry in self._aliases.items()
        }

    async def refresh(self) -> None:
        candidate = await load_definitions(self._definitions._scope)
        for alias, entry in self._aliases.items():
            before = entry.definition
            if before.id not in candidate:
                raise PropertyDriftError(f"Property {before.id!r} for alias {alias!r} was removed; explicitly rebind.")
            after = candidate[before.id]
            if before.type != after.type or before.comodel != after.comodel:
                raise PropertyDriftError(f"Property {before.id!r} changed kind/comodel.")
            for option_id in (entry.options or {}).values():
                if option_id not in after.options:
                    raise PropertyDriftError(f"Mapped option {option_id!r} was removed from {before.id!r}.")
        self._definitions = candidate

    @overload
    async def read(self, ids: int, *, fields: list[str] | None = None) -> PropertyRecord: ...

    @overload
    async def read(self, ids: list[int], *, fields: list[str] | None = None) -> list[PropertyRecord]: ...

    async def read(
        self, ids: int | list[int], *, fields: list[str] | None = None
    ) -> PropertyRecord | list[PropertyRecord]:
        target_ids = record_ids(ids)
        definitions = self._definitions
        scope = definitions._scope
        requested = None if fields is None else list(dict.fromkeys([*fields, scope.parent_field, scope.field]))
        rows = await read_rows(scope, scope.model, target_ids, requested)
        result = []
        for row in rows:
            parent_id_for(scope, row)
            values = decode_values(row.get(scope.field), definitions)
            aliases = {}
            for alias, entry in self._aliases.items():
                value = values[entry.definition.id]
                if entry.options is not None and value is not None:
                    reverse = {oid: name for name, oid in entry.options.items()}
                    raw_values = value if entry.definition.type == "tags" else [value]
                    missing = [oid for oid in raw_values if oid not in reverse]
                    if missing:
                        raise PropertyValueError(
                            f"Unmapped option IDs {missing!r} for property {entry.definition.id!r}."
                        )
                    value = [reverse[oid] for oid in raw_values] if entry.definition.type == "tags" else reverse[value]
                aliases[alias] = value
            result.append(PropertyRecord(row["id"], row, PropertyValues(values, aliases), definitions))
        return result[0] if type(ids) is int else result

    def _changes(self, changes: Mapping[str, Any], definitions: PropertyDefinitions) -> dict[str, Any]:
        if not isinstance(changes, Mapping):
            raise PropertyValueError("Property changes must be a mapping.")
        result = {}
        for key, value in changes.items():
            if key in self._aliases:
                entry = self._aliases[key]
                name = entry.definition.id
                if entry.options is not None and value is not None:
                    raw_values = value if entry.definition.type == "tags" else [value]
                    if not isinstance(raw_values, list) or any(
                        not isinstance(v, str) or v not in entry.options for v in raw_values
                    ):
                        raise PropertyValueError(f"Unknown option alias for property {key!r}: {value!r}.")
                    value = (
                        [entry.options[v] for v in raw_values]
                        if entry.definition.type == "tags"
                        else entry.options[value]
                    )
            else:
                name = key
            if name not in definitions:
                raise PropertyLookupError(f"Unknown property ID or alias {key!r}.")
            if name in result:
                raise PropertyValueError(f"Property {name!r} selected twice in one patch.")
            if value is False and definitions[name].type != "boolean":
                raise PropertyValueError(f"False is not a {definitions[name].type} patch value; use None to clear.")
            result[name] = None if value is None else value_for(definitions[name], value)
        return result

    async def patch(self, record_id: int, changes: Mapping[str, Any], *, refresh: bool = True) -> None:
        receipts = await self.patch_each({record_id: changes}, concurrency=1, refresh=refresh)
        for receipt in receipts:
            require_acknowledged(receipt)

    async def patch_many(
        self,
        ids: list[int],
        changes: Mapping[str, Any],
        *,
        concurrency: int = 4,
        refresh: bool = True,
    ) -> list[PropertyReceipt]:
        return await self.patch_each(
            {rid: changes for rid in record_ids(ids)}, concurrency=concurrency, refresh=refresh
        )

    async def patch_each(
        self,
        changes: Mapping[int, Mapping[str, Any]],
        *,
        concurrency: int = 4,
        refresh: bool = True,
    ) -> list[PropertyReceipt]:
        if type(concurrency) is not int or concurrency <= 0:
            raise PropertyValueError("concurrency must be a positive integer.")
        ids = record_ids(list(changes))
        # Copy before the first await so caller mutation cannot change the preflight.
        patches = deepcopy(dict(changes))
        if any(not isinstance(patch, Mapping) for patch in patches.values()):
            raise PropertyValueError("Each property patch must be a mapping.")
        if not ids or not any(patches.values()):
            return []
        if refresh:
            await self.refresh()
        definitions = self._definitions
        scope = definitions._scope
        normalized = {rid: self._changes(patch, definitions) for rid, patch in patches.items()}
        rows = await read_rows(scope, scope.model, ids, [scope.parent_field, scope.field])
        payloads = {}
        for row in rows:
            parent_id_for(scope, row)
            current = decode_values(row.get(scope.field), definitions)
            current.update(normalized[row["id"]])
            payload = encode_values(current, definitions)
            if normalized[row["id"]]:
                payloads[row["id"]] = payload
        return await dispatch(scope, payloads, concurrency)
