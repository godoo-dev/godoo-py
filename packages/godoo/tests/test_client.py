"""Tests for OdooClient using respx mock."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.errors import OdooAuthError, OdooSafetyError
from godoo.safety import OperationInfo, SafetyContext

BASE_URL = "http://odoo.test"
DB = "testdb"


def _jsonrpc_result(result):
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def _make_config(**kwargs):
    defaults = dict(url=BASE_URL, database=DB, username="admin", password="admin")
    defaults.update(kwargs)
    return OdooClientConfig(**defaults)


@pytest.fixture
def client():
    c = OdooClient(_make_config())
    yield c


@pytest.fixture
async def auth_client():
    c = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await c.authenticate()
    yield c


@pytest.mark.asyncio
async def test_call_before_auth_raises(client):
    with pytest.raises(OdooAuthError, match="authenticate"):
        await client.call("res.partner", "search", [[]], {})


@respx.mock
@pytest.mark.asyncio
async def test_authenticate_success(client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
    session = await client.authenticate()
    assert session.uid == 2
    assert client.is_authenticated()


@respx.mock
@pytest.mark.asyncio
async def test_search(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result([1, 2, 3])))
    result = await auth_client.search("res.partner", [[("is_company", "=", True)]])
    assert result == [1, 2, 3]


@respx.mock
@pytest.mark.asyncio
async def test_create(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(42)))
    result = await auth_client.create("res.partner", {"name": "Test"})
    assert result == 42


@respx.mock
@pytest.mark.asyncio
async def test_unlink_single_int_normalized(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    result = await auth_client.unlink("res.partner", 42)
    assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_unlink_list(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    result = await auth_client.unlink("res.partner", [1, 2, 3])
    assert result is True


@pytest.mark.asyncio
async def test_safety_blocks_write():
    async def deny(op: OperationInfo) -> bool:
        return False

    config = _make_config(safety=SafetyContext(confirm=deny))
    client = OdooClient(config)

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await client.authenticate()

    with pytest.raises(OdooSafetyError):
        await client.write("res.partner", [1], {"name": "Blocked"})


@pytest.mark.asyncio
async def test_safety_allows_read():
    deny_called = False

    async def deny(op: OperationInfo) -> bool:
        nonlocal deny_called
        deny_called = True
        return False

    config = _make_config(safety=SafetyContext(confirm=deny))
    client = OdooClient(config)

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(
            side_effect=[
                httpx.Response(200, json=_jsonrpc_result(2)),
                httpx.Response(200, json=_jsonrpc_result([1, 2])),
            ]
        )
        await client.authenticate()
        result = await client.search("res.partner", [[]])

    assert result == [1, 2]
    assert not deny_called, "deny callback should not be called for READ operations"


@pytest.mark.asyncio
async def test_logout_clears_auth():
    client = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await client.authenticate()
    assert client.is_authenticated()
    client.logout()
    assert not client.is_authenticated()


@pytest.mark.asyncio
async def test_get_session_none_before_auth(client):
    assert client.get_session() is None


@respx.mock
@pytest.mark.asyncio
async def test_get_session_after_auth(client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
    await client.authenticate()
    session = client.get_session()
    assert session is not None
    assert session.uid == 2


@pytest.mark.asyncio
async def test_set_safety_context_overrides():
    """set_safety_context replaces config safety."""
    deny_called = False

    async def deny(op: OperationInfo) -> bool:
        nonlocal deny_called
        deny_called = True
        return False

    client = OdooClient(_make_config())

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await client.authenticate()

    client.set_safety_context(SafetyContext(confirm=deny))

    with pytest.raises(OdooSafetyError):
        await client.write("res.partner", [1], {"name": "Blocked"})
