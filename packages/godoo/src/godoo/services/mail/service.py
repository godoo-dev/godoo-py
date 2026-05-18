"""MailService — class wrapper around mail functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from godoo.services.mail.functions import post_internal_note, post_open_message

if TYPE_CHECKING:
    from godoo.client import OdooClient
    from godoo.services.mail.types import PostMessageOptions


class MailService:
    """High-level mail / messaging service for Odoo."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def post_internal_note(
        self,
        model: str,
        res_id: int,
        body: str,
        options: PostMessageOptions | None = None,
    ) -> int:
        return await post_internal_note(self._client, model, res_id, body, options)

    async def post_open_message(
        self,
        model: str,
        res_id: int,
        body: str,
        options: PostMessageOptions | None = None,
    ) -> int:
        return await post_open_message(self._client, model, res_id, body, options)
