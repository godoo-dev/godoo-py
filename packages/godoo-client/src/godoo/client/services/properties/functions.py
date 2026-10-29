"""Properties service — standalone async functions."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, overload

from godoo.client.errors import OdooAuthError

from .binding import PropertyBinding
from .codec import decode_values, encode_values, legacy_values
from .mutations import dispatch, require_acknowledged
from .scope import PropertyScope, discover, load_definitions, parent_id_for, read_rows, record_ids
from .types import PropertyBatchError, PropertyDefinitions, PropertyRecord, PropertyValues

if TYPE_CHECKING:
    from collections.abc import Mapping

    from godoo.client.client import OdooClient


async def definitions(
    client: OdooClient,
    model: str,
    *,
    field: str,
    parent_id: int,
    context: dict[str, Any] | None = None,
    parent_field: str | None = None,
    definition_field: str | None = None,
) -> PropertyDefinitions:
    record_ids(parent_id)
    scope = await discover(
        client,
        model,
        field,
        context=context,
        parent_field=parent_field,
        definition_field=definition_field,
    )
    return await load_definitions(scope.for_parent(parent_id))


@overload
async def read(
    client: OdooClient,
    model: str,
    ids: int,
    *,
    field: str,
    fields: list[str] | None = None,
    context: dict[str, Any] | None = None,
    parent_field: str | None = None,
    definition_field: str | None = None,
) -> PropertyRecord: ...


@overload
async def read(
    client: OdooClient,
    model: str,
    ids: list[int],
    *,
    field: str,
    fields: list[str] | None = None,
    context: dict[str, Any] | None = None,
    parent_field: str | None = None,
    definition_field: str | None = None,
) -> list[PropertyRecord]: ...


async def read(
    client: OdooClient,
    model: str,
    ids: int | list[int],
    *,
    field: str,
    fields: list[str] | None = None,
    context: dict[str, Any] | None = None,
    parent_field: str | None = None,
    definition_field: str | None = None,
) -> PropertyRecord | list[PropertyRecord]:
    target_ids = record_ids(ids)
    if not target_ids:
        return []
    scope = await discover(
        client,
        model,
        field,
        context=context,
        parent_field=parent_field,
        definition_field=definition_field,
    )
    requested = None if fields is None else list(dict.fromkeys([*fields, field, scope.parent_field]))
    rows = await read_rows(scope, model, target_ids, requested)
    snapshots = {}
    result = []
    for row in rows:
        parent_id = parent_id_for(scope, row)
        if parent_id not in snapshots:
            snapshots[parent_id] = await load_definitions(scope.for_parent(parent_id))
        snapshot = snapshots[parent_id]
        values = decode_values(row.get(field), snapshot)
        result.append(PropertyRecord(row["id"], row, PropertyValues(values), snapshot))
    return result[0] if type(ids) is int else result


async def patch(
    client: OdooClient,
    model: str,
    record_id: int,
    *,
    field: str,
    changes: Mapping[str, Any],
    context: dict[str, Any] | None = None,
    parent_field: str | None = None,
    definition_field: str | None = None,
) -> None:
    record_ids(record_id)
    changes = deepcopy(dict(changes))
    if not changes:
        return
    record = await read(
        client,
        model,
        record_id,
        field=field,
        fields=[],
        context=context,
        parent_field=parent_field,
        definition_field=definition_field,
    )
    snapshot = record.property_definitions
    values = dict(record.properties)
    values.update(PropertyBinding(snapshot, {})._changes(changes, snapshot))
    payload = encode_values(values, snapshot)
    receipts = await dispatch(snapshot._scope, {record_id: payload}, 1)
    require_acknowledged(receipts[0])


def properties_to_write_format(props_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert inline property reads to value-only writes, stripping relational display names."""
    return legacy_values(props_list)


def _legacy_scope(client: OdooClient, model: str, field: str) -> PropertyScope:
    session = client.get_session()
    if session is None:
        raise OdooAuthError("Authenticate before updating properties.")
    return PropertyScope(
        client,
        model,
        field,
        "",
        "",
        "",
        0,
        client._capture_context(),
        session,
        (session.uid, session.db, session.session_id),
    )


def _legacy_merge(current: Any, updates: dict[str, Any]) -> dict[str, Any]:
    # Only explicit unset sentinels may stand in for an empty property list.
    if current is None or current is False:
        current = []
    # Validate the untouched values before merging, including duplicate IDs.
    properties_to_write_format(current)
    entries = {entry["name"]: deepcopy(entry) for entry in current}
    for name, value in updates.items():
        entries[name] = {**entries.get(name, {}), "name": name, "value": value}
    return properties_to_write_format(list(entries.values()))


async def update_safely(
    client: OdooClient,
    model: str,
    record_id: int,
    field: str,
    updates: dict[str, Any],
) -> None:
    """Merge visible values; non-atomic and limited to inline metadata, without discovery."""
    scope = _legacy_scope(client, model, field)
    rows = await read_rows(scope, model, record_ids(record_id), [field])
    payload = _legacy_merge(rows[0][field], deepcopy(updates))
    receipts = await dispatch(scope, {record_id: payload}, 1)
    require_acknowledged(receipts[0])


async def update_safely_batch(
    client: OdooClient,
    model: str,
    record_ids: list[int],
    field: str,
    updates: dict[str, Any],
) -> None:
    """Preflight the complete legacy batch, then write with at most four active workers."""
    # Keep the historical record_ids argument name.
    from .scope import record_ids as validate_ids

    ids = validate_ids(record_ids)
    if not ids:
        return
    scope = _legacy_scope(client, model, field)
    updates = deepcopy(updates)
    rows = await read_rows(scope, model, ids, [field])
    payloads = {row["id"]: _legacy_merge(row[field], updates) for row in rows}
    receipts = await dispatch(scope, payloads, 4)
    if any(receipt.status != "acknowledged" for receipt in receipts):
        raise PropertyBatchError(receipts)
