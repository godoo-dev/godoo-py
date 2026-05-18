"""Tests for JsonRpcTransport using respx mock."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.errors import (
    OdooAccessError,
    OdooAuthError,
    OdooMissingError,
    OdooNetworkError,
    OdooRpcError,
    OdooValidationError,
)
from godoo.rpc import JsonRpcTransport, OdooSessionInfo

BASE_URL = "http://odoo.test"
DB = "testdb"


def _jsonrpc_result(result):
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def _jsonrpc_error(exception_type=None, name=None, message="Error", code=-32000):
    data = {}
    if exception_type:
        data["exception_type"] = exception_type
    if name:
        data["name"] = name
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": code,
            "message": message,
            "data": data,
        },
    }


@pytest.fixture
def transport():
    t = JsonRpcTransport(BASE_URL, DB)
    yield t


@respx.mock
@pytest.mark.asyncio
async def test_authenticate_success(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
    session = await transport.authenticate("admin", "admin")
    assert isinstance(session, OdooSessionInfo)
    assert session.uid == 2
    assert session.db == DB
    assert transport.is_authenticated() if hasattr(transport, "is_authenticated") else transport.session is not None


@respx.mock
@pytest.mark.asyncio
async def test_authenticate_false_uid_raises(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(False)))
    with pytest.raises(OdooAuthError):
        await transport.authenticate("admin", "wrong")


@respx.mock
@pytest.mark.asyncio
async def test_authenticate_zero_uid_raises(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(0)))
    with pytest.raises(OdooAuthError):
        await transport.authenticate("admin", "wrong")


@respx.mock
@pytest.mark.asyncio
async def test_call_after_auth(transport):
    # First authenticate
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            httpx.Response(200, json=_jsonrpc_result(2)),
            httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Test"}])),
        ]
    )
    await transport.authenticate("admin", "admin")
    result = await transport.call("res.partner", "search_read", [[]], {})
    assert result == [{"id": 1, "name": "Test"}]


@respx.mock
@pytest.mark.asyncio
async def test_error_categorization_validation_by_exception_type(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_error(exception_type="validation_error"))
    )
    with pytest.raises(OdooValidationError):
        await transport.call_rpc("common.authenticate", {})


@respx.mock
@pytest.mark.asyncio
async def test_error_categorization_user_error_by_exception_type(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_error(exception_type="user_error"))
    )
    with pytest.raises(OdooValidationError):
        await transport.call_rpc("common.authenticate", {})


@respx.mock
@pytest.mark.asyncio
async def test_error_categorization_access_error_by_name(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_error(name="odoo.exceptions.AccessError"))
    )
    with pytest.raises(OdooAccessError):
        await transport.call_rpc("common.authenticate", {})


@respx.mock
@pytest.mark.asyncio
async def test_error_categorization_missing_error(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_error(exception_type="missing_error"))
    )
    with pytest.raises(OdooMissingError):
        await transport.call_rpc("common.authenticate", {})


@respx.mock
@pytest.mark.asyncio
async def test_error_categorization_access_denied_by_exception_type(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_error(exception_type="access_denied"))
    )
    with pytest.raises(OdooAuthError):
        await transport.call_rpc("common.authenticate", {})


@respx.mock
@pytest.mark.asyncio
async def test_error_categorization_AccessDenied_by_name(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_error(name="odoo.exceptions.AccessDenied"))
    )
    with pytest.raises(OdooAuthError):
        await transport.call_rpc("common.authenticate", {})


@respx.mock
@pytest.mark.asyncio
async def test_http_500_raises_network_error(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(500, text="Internal Server Error"))
    with pytest.raises(OdooNetworkError):
        await transport.call_rpc("common.authenticate", {})


@pytest.mark.asyncio
async def test_connection_error_raises_network_error(transport):
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=httpx.ConnectError("Connection refused"))
        with pytest.raises(OdooNetworkError):
            await transport.call_rpc("common.authenticate", {})


@respx.mock
@pytest.mark.asyncio
async def test_error_categorization_generic_rpc_error(transport):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_error(name="some.other.Error"))
    )
    with pytest.raises(OdooRpcError):
        await transport.call_rpc("common.authenticate", {})


@pytest.mark.asyncio
async def test_session_is_none_initially(transport):
    assert transport.session is None


@pytest.mark.asyncio
async def test_logout_clears_session(transport):
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await transport.authenticate("admin", "admin")
        assert transport.session is not None
        transport.logout()
        assert transport.session is None
