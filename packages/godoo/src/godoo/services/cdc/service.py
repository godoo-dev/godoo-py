"""CdcService — class wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from godoo.services.cdc.functions import check, get_feed, get_history

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from godoo.client import OdooClient
    from godoo.services.cdc.types import (
        CdcCheckResult,
        GetFeedOptions,
        GetHistoryOptions,
        TrackingEvent,
    )


class CdcService:
    """High-level Change Data Capture service for Odoo."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def check(self, model: str) -> CdcCheckResult:
        return await check(self._client, model)

    async def get_history(
        self,
        model: str,
        res_id: int,
        options: GetHistoryOptions | None = None,
    ) -> list[TrackingEvent]:
        return await get_history(self._client, model, res_id, options)

    async def get_feed(self, options: GetFeedOptions) -> AsyncIterator[TrackingEvent]:
        return get_feed(self._client, options)
