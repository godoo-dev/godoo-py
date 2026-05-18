"""UrlService — class wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from godoo.services.urls.functions import (
    get_base_url,
    get_portal_url,
    get_record_url,
)

if TYPE_CHECKING:
    from godoo.client import OdooClient
    from godoo.services.urls.types import PortalUrlOptions, PortalUrlResult


class UrlService:
    """High-level URL builder service for Odoo."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def get_base_url(self, *, force_refresh: bool = False) -> str:
        return await get_base_url(self._client, force_refresh=force_refresh)

    async def get_record_url(self, model: str, res_id: int) -> str:
        return await get_record_url(self._client, model, res_id)

    async def get_portal_url(
        self,
        model: str,
        res_id: int,
        options: PortalUrlOptions | None = None,
    ) -> PortalUrlResult:
        return await get_portal_url(self._client, model, res_id, options)
