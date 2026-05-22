from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from godoo.client import OdooClient


class ConfigParameterHelper:
    """Test-only helper for setting ir.config_parameter key/value pairs via JSON-RPC."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def set(self, key: str, value: str) -> None:
        """Set a single ir.config_parameter. Upsert — safe to call multiple times with same key."""
        if not key:
            from godoo.client.errors import OdooValidationError

            raise OdooValidationError("ir.config_parameter key must not be empty")
        await self._client.execute_kw("ir.config_parameter", "set_param", [key, value])

    async def set_many(self, values: Mapping[str, str]) -> None:
        """Set multiple ir.config_parameter pairs. Sequential — set_param is not designed for concurrent batch RPC."""
        for k, v in values.items():
            await self.set(k, v)
