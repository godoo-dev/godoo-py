"""PropertiesService — async client-bound entrypoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

from . import functions

if TYPE_CHECKING:
    from collections.abc import Mapping

    from godoo.client.client import OdooClient

    from .types import PropertyDefinitions, PropertyRecord


class PropertiesService:
    """Runtime discovery, values, sparse patches and optional application aliases."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def definitions(
        self,
        model: str,
        *,
        field: str,
        parent_id: int,
        context: dict[str, Any] | None = None,
        parent_field: str | None = None,
        definition_field: str | None = None,
    ) -> PropertyDefinitions:
        return await functions.definitions(
            self._client,
            model,
            field=field,
            parent_id=parent_id,
            context=context,
            parent_field=parent_field,
            definition_field=definition_field,
        )

    @overload
    async def read(
        self,
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
        self,
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
        self,
        model: str,
        ids: int | list[int],
        *,
        field: str,
        fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
        parent_field: str | None = None,
        definition_field: str | None = None,
    ) -> PropertyRecord | list[PropertyRecord]:
        return await functions.read(
            self._client,
            model,
            ids,
            field=field,
            fields=fields,
            context=context,
            parent_field=parent_field,
            definition_field=definition_field,
        )

    async def patch(
        self,
        model: str,
        record_id: int,
        *,
        field: str,
        changes: Mapping[str, Any],
        context: dict[str, Any] | None = None,
        parent_field: str | None = None,
        definition_field: str | None = None,
    ) -> None:
        return await functions.patch(
            self._client,
            model,
            record_id,
            field=field,
            changes=changes,
            context=context,
            parent_field=parent_field,
            definition_field=definition_field,
        )

    @staticmethod
    def properties_to_write_format(props_list: list[dict[str, Any]]) -> dict[str, Any]:
        return functions.properties_to_write_format(props_list)

    async def update_safely(
        self,
        model: str,
        record_id: int,
        field: str,
        updates: dict[str, Any],
    ) -> None:
        return await functions.update_safely(self._client, model, record_id, field, updates)

    async def update_safely_batch(
        self,
        model: str,
        record_ids: list[int],
        field: str,
        updates: dict[str, Any],
    ) -> None:
        return await functions.update_safely_batch(self._client, model, record_ids, field, updates)
