"""Definition-aware property codecs; RPC values and patch inputs are distinct."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from .types import PropertyDefinition, PropertyOption, PropertyOptions, PropertyValueError

if TYPE_CHECKING:
    from collections.abc import Mapping

KINDS = frozenset(
    {"boolean", "integer", "float", "char", "date", "datetime", "many2one", "many2many", "selection", "tags"}
)


def parse_definitions(raw: Any) -> tuple[PropertyDefinition, ...]:
    if raw is False or raw is None:
        return ()
    if not isinstance(raw, list):
        raise PropertyValueError("Expected a list of property definitions.")
    definitions = []
    seen = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise PropertyValueError("Malformed property definition.")
        name, label, kind = entry.get("name"), entry.get("string"), entry.get("type")
        if not isinstance(name, str) or not name or name in seen:
            raise PropertyValueError(f"Missing or duplicate property ID {name!r}.")
        if not isinstance(label, str) or not isinstance(kind, str):
            raise PropertyValueError(f"Missing label/type for property {name!r}.")
        comodel = entry.get("comodel") or None
        if comodel is not None and not isinstance(comodel, str):
            raise PropertyValueError(f"Malformed comodel for property {name!r}.")
        if kind in ("many2one", "many2many") and not comodel:
            raise PropertyValueError(f"Missing comodel for property {name!r}.")
        options = []
        option_ids = set()
        for option in (
            (entry.get("selection" if kind == "selection" else "tags") or []) if kind in ("selection", "tags") else []
        ):
            size = 2 if kind == "selection" else 3
            if not isinstance(option, (list, tuple)) or len(option) != size:
                raise PropertyValueError(f"Malformed option for property {name!r}.")
            oid, text = option[:2]
            if not isinstance(oid, str) or not oid or oid in option_ids or not isinstance(text, str):
                raise PropertyValueError(f"Missing or duplicate option ID for property {name!r}.")
            color = option[2] if kind == "tags" else None
            if color is not None and type(color) is not int:
                raise PropertyValueError(f"Malformed tag color for property {name!r}.")
            options.append(PropertyOption(oid, text, color))
            option_ids.add(oid)
        definitions.append(PropertyDefinition(name, label, kind, comodel, PropertyOptions(tuple(options))))
        seen.add(name)
    return tuple(definitions)


def value_for(definition: PropertyDefinition, value: Any, *, reading: bool = False) -> Any:
    """Return normalized Python values (reading) or validated value-only wire values."""
    kind = definition.type
    if kind not in KINDS:
        raise PropertyValueError(f"Unsupported property kind {kind!r} for {definition.id!r}.")
    if value is None or (value is False and reading):
        if kind == "boolean":
            return False
        if kind in ("many2many", "tags"):
            return []
        return None if reading else False
    if value is False and kind != "boolean":
        if kind in ("many2many", "tags"):
            return []
        return None if reading else False
    valid = True
    if kind == "boolean":
        valid = type(value) is bool
    elif kind == "integer":
        valid = type(value) is int
    elif kind == "float":
        valid = type(value) in (int, float) and math.isfinite(value)
    elif kind == "char":
        valid = isinstance(value, str)
    elif kind in ("date", "datetime"):
        valid = isinstance(value, str)
        if valid:
            try:
                if kind == "date":
                    date.fromisoformat(value)
                else:
                    datetime.fromisoformat(value)
            except ValueError:
                valid = False
    elif kind == "many2one":
        if reading and _display_pair(value):
            value = value[0]
        valid = type(value) is int and value > 0
    elif kind == "many2many":
        if reading and isinstance(value, list):
            value = [item[0] if _display_pair(item) else item for item in value]
        valid = isinstance(value, list) and all(type(item) is int and item > 0 for item in value)
    elif kind == "selection":
        valid = isinstance(value, str) and value in definition.options
    elif kind == "tags":
        valid = isinstance(value, list) and all(isinstance(item, str) and item in definition.options for item in value)
    if not valid:
        raise PropertyValueError(f"Invalid {kind} value {value!r} for property {definition.id!r}.")
    return value


def _display_pair(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and type(value[0]) is int
        and value[0] > 0
        and (isinstance(value[1], str) or value[1] is None or value[1] is False)
    )


def decode_values(raw: Any, definitions: Mapping[str, PropertyDefinition]) -> dict[str, Any]:
    if raw is None or raw is False:
        raw = []
    if not isinstance(raw, list):
        raise PropertyValueError("Expected a list of properties from Odoo.")
    result = {}
    seen = set()
    for entry in raw:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise PropertyValueError("Malformed property read entry.")
        name = entry["name"]
        if name in seen or name not in definitions:
            raise PropertyValueError(f"Duplicate or unexpected property ID {name!r} in read.")
        seen.add(name)
        definition = definitions[name]
        if definition.type == "separator":
            continue
        if entry.get("type") != definition.type or (entry.get("comodel") or None) != definition.comodel:
            raise PropertyValueError(f"Property metadata changed during read for {name!r}.")
        if "value" not in entry:
            raise PropertyValueError(f"Missing value for property {name!r} in read.")
        result[name] = value_for(definition, entry["value"], reading=True)
    for name, definition in definitions.items():
        if name not in seen and definition.type != "separator":
            raise PropertyValueError(f"Property {name!r} missing from the server read.")
    return result


def encode_values(values: Mapping[str, Any], definitions: Mapping[str, PropertyDefinition]) -> dict[str, Any]:
    return {name: value_for(definitions[name], value) for name, value in values.items()}


def legacy_values(raw: Any) -> dict[str, Any]:
    """Normalize inline read metadata, allowing historical untyped scalar inputs."""
    if not isinstance(raw, list):
        raise PropertyValueError("Expected a list of property dictionaries.")
    result = {}
    for entry in raw:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"]:
            raise PropertyValueError("Malformed property entry.")
        name = entry["name"]
        if name in result:
            raise PropertyValueError(f"Duplicate property ID {name!r}.")
        if entry.get("type") == "separator":
            continue
        if "value" not in entry:
            raise PropertyValueError(f"Missing value for property {name!r} in read.")
        value = entry["value"]
        if "type" in entry:
            definition = parse_definitions([{**entry, "string": entry.get("string", name)}])[0]
            result[name] = value_for(definition, value_for(definition, value, reading=True))
        else:
            if value is not None and type(value) not in (str, int, float, bool):
                raise PropertyValueError(f"Property {name!r} needs type metadata for non-scalar values.")
            if type(value) is float and not math.isfinite(value):
                raise PropertyValueError(f"Nonfinite property value for {name!r}.")
            result[name] = False if value is None else value
    return result
