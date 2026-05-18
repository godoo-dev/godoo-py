"""PropertiesService — class wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from godoo.services.properties.functions import (
    properties_to_write_format,
    update_safely,
    update_safely_batch,
)

if TYPE_CHECKING:
    from godoo.client import OdooClient


class PropertiesService:
    """High-level service for Odoo properties fields."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    @staticmethod
    def properties_to_write_format(props_list: list[dict[str, Any]]) -> dict[str, Any]:
        return properties_to_write_format(props_list)

    async def update_safely(
        self,
        model: str,
        record_id: int,
        field: str,
        updates: dict[str, Any],
    ) -> None:
        return await update_safely(self._client, model, record_id, field, updates)

    async def update_safely_batch(
        self,
        model: str,
        record_ids: list[int],
        field: str,
        updates: dict[str, Any],
    ) -> None:
        return await update_safely_batch(self._client, model, record_ids, field, updates)
