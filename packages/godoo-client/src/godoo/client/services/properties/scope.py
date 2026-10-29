"""Private discovery and scoped RPCs, retaining normal client safety checks."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from typing import TYPE_CHECKING, Any

from godoo.client.errors import OdooAuthError, OdooMissingError

from .codec import parse_definitions
from .types import PropertyDefinitions, PropertyScopeError, PropertyValueError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from godoo.client.client import OdooClient
    from godoo.client.rpc.types import OdooSessionInfo


def record_ids(ids: int | list[int]) -> list[int]:
    result = [ids] if type(ids) is int else ids
    if not isinstance(result, list) or any(type(rid) is not int or rid <= 0 for rid in result):
        raise PropertyValueError("Record IDs must be positive integers.")
    if len(result) != len(set(result)):
        raise PropertyValueError("Duplicate record IDs are not supported.")
    return list(result)


@dataclass(frozen=True)
class PropertyScope:
    client: OdooClient = dataclass_field(repr=False, compare=False)
    model: str
    field: str
    parent_model: str
    parent_field: str
    definition_field: str
    parent_id: int
    context: dict[str, Any] = dataclass_field(repr=False)
    session: OdooSessionInfo = dataclass_field(repr=False, compare=False)
    identity: tuple[int, str, str] = dataclass_field(repr=False)

    def check_identity(self) -> None:
        current = self.client.get_session()
        if current is not self.session or (current.uid, current.db, current.session_id) != self.identity:
            raise PropertyScopeError("Authentication changed; discover properties again.")

    async def call(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        self.check_identity()
        return await self.client._call_with_context(
            model,
            method,
            args,
            kwargs,
            context=self.context,
            session=self.session,
            identity=self.identity,
        )

    def for_parent(self, parent_id: int) -> PropertyScope:
        record_ids(parent_id)
        return replace(self, parent_id=parent_id)


async def discover(
    client: OdooClient,
    model: str,
    property_field: str,
    *,
    context: dict[str, Any] | None = None,
    parent_field: str | None = None,
    definition_field: str | None = None,
) -> PropertyScope:
    session = client.get_session()
    if session is None:
        raise OdooAuthError("Authenticate before discovering properties.")
    scope = PropertyScope(
        client,
        model,
        property_field,
        "",
        "",
        "",
        0,
        client._capture_context(context),
        session,
        (session.uid, session.db, session.session_id),
    )
    metadata = await scope.call(model, "fields_get", [], {})
    if not isinstance(metadata, dict) or not isinstance(metadata.get(property_field), dict):
        raise PropertyValueError(f"Properties field {property_field!r} is missing or inaccessible on {model!r}.")
    info = metadata[property_field]
    if info.get("type") != "properties":
        raise PropertyValueError(f"Field {property_field!r} is not an Odoo properties field.")
    parent_field = parent_field or info.get("definition_record")
    definition_field = definition_field or info.get("definition_record_field")
    if (
        not isinstance(parent_field, str)
        or not parent_field
        or not isinstance(definition_field, str)
        or not definition_field
    ):
        raise PropertyValueError(
            "Missing properties route metadata; supply parent_field and definition_field overrides."
        )
    relation = metadata.get(parent_field, {})
    parent_model = relation.get("relation")
    if relation.get("type") != "many2one" or not isinstance(parent_model, str) or not parent_model:
        raise PropertyValueError("The property definition parent must be a discoverable many2one relation.")
    parent_metadata = await scope.call(parent_model, "fields_get", [], {"attributes": ["type"]})
    if (
        not isinstance(parent_metadata, dict)
        or parent_metadata.get(definition_field, {}).get("type") != "properties_definition"
    ):
        raise PropertyValueError(f"Parent field {definition_field!r} is not a properties_definition field.")
    return replace(scope, parent_model=parent_model, parent_field=parent_field, definition_field=definition_field)


async def read_rows(scope: PropertyScope, model: str, ids: list[int], fields: list[str] | None) -> list[dict[str, Any]]:
    if not ids:
        return []
    kwargs = {} if fields is None else {"fields": fields}
    result = await scope.call(model, "read", [ids], kwargs)
    if not isinstance(result, list):
        raise PropertyValueError("Malformed record read response.")
    indexed = {}
    for row in result:
        if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] not in ids or row["id"] in indexed:
            raise PropertyValueError("Duplicate, unexpected or malformed record in read response.")
        if fields is not None and any(name not in row for name in fields):
            raise PropertyValueError("A requested field was omitted from the record read.")
        indexed[row["id"]] = deepcopy(row)
    missing = [rid for rid in ids if rid not in indexed]
    if missing:
        raise OdooMissingError(f"Records are missing or inaccessible: {missing!r}.")
    return [indexed[rid] for rid in ids]


def parent_id_for(scope: PropertyScope, row: Mapping[str, Any]) -> int:
    value = row.get(scope.parent_field)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        value = value[0]
    if type(value) is not int or value <= 0:
        raise PropertyScopeError(f"Record {row.get('id')!r} has no accessible definition parent.")
    if scope.parent_id and value != scope.parent_id:
        raise PropertyScopeError(f"Record {row.get('id')!r} moved outside parent {scope.parent_id}.")
    return value


async def load_definitions(scope: PropertyScope) -> PropertyDefinitions:
    scope.check_identity()
    rows = await read_rows(scope, scope.parent_model, [scope.parent_id], [scope.definition_field])
    if scope.definition_field not in rows[0]:
        raise PropertyValueError("The definition field was omitted from the parent read.")
    return PropertyDefinitions(parse_definitions(rows[0][scope.definition_field]), scope)
