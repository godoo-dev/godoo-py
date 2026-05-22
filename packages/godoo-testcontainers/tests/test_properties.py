from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from godoo.errors import OdooValidationError
from godoo_testcontainers.properties import ConfigParameterHelper


class TestConfigParameterHelper:
    def _make_client(self) -> MagicMock:
        client = MagicMock()
        client.execute_kw = AsyncMock(return_value=True)
        return client

    async def test_set_calls_execute_kw(self) -> None:
        client = self._make_client()
        helper = ConfigParameterHelper(client)
        await helper.set("mail.catchall.domain", "example.com")
        client.execute_kw.assert_called_once_with(
            "ir.config_parameter", "set_param", ["mail.catchall.domain", "example.com"]
        )

    async def test_set_empty_key_raises(self) -> None:
        helper = ConfigParameterHelper(self._make_client())
        with pytest.raises(OdooValidationError):
            await helper.set("", "value")

    async def test_set_empty_key_no_rpc_call(self) -> None:
        client = self._make_client()
        helper = ConfigParameterHelper(client)
        with pytest.raises(OdooValidationError):
            await helper.set("", "value")
        client.execute_kw.assert_not_called()

    async def test_set_many_calls_set_per_key(self) -> None:
        client = self._make_client()
        helper = ConfigParameterHelper(client)
        await helper.set_many({"a": "1", "b": "2"})
        assert client.execute_kw.call_count == 2

    async def test_set_many_empty_dict_is_noop(self) -> None:
        client = self._make_client()
        helper = ConfigParameterHelper(client)
        await helper.set_many({})
        client.execute_kw.assert_not_called()

    async def test_set_many_preserves_key_value_pairs(self) -> None:
        client = self._make_client()
        helper = ConfigParameterHelper(client)
        await helper.set_many({"x.key": "myvalue"})
        client.execute_kw.assert_called_once_with("ir.config_parameter", "set_param", ["x.key", "myvalue"])

    async def test_set_accepts_empty_value(self) -> None:
        client = self._make_client()
        helper = ConfigParameterHelper(client)
        await helper.set("some.key", "")
        client.execute_kw.assert_called_once_with("ir.config_parameter", "set_param", ["some.key", ""])
