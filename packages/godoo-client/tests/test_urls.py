"""Tests for the URLs service."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.client.services.urls import UrlService
from godoo.client.services.urls.functions import _base_url_cache

BASE_URL = "http://odoo.test"
DB = "testdb"


def _rpc_response(result, id=1) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})


def _make_client() -> OdooClient:
    return OdooClient(OdooClientConfig(url=BASE_URL, database=DB, username="admin", password="admin"))


@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(2))
        await client.authenticate()
    _base_url_cache.clear()
    yield client
    await client.aclose()
    _base_url_cache.clear()


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_get_record_url(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([{"id": 1, "value": "https://myodoo.com"}]))
    svc = UrlService(auth_client)
    url = await svc.get_record_url("res.partner", 42)
    assert url == "https://myodoo.com/mail/view?model=res.partner&res_id=42"


@respx.mock
@pytest.mark.asyncio
async def test_get_base_url_strips_trailing_slash(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([{"id": 1, "value": "https://myodoo.com/"}]))
    svc = UrlService(auth_client)
    base = await svc.get_base_url()
    assert base == "https://myodoo.com"


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_get_base_url_caching(auth_client):
    route = respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=_rpc_response([{"id": 1, "value": "https://myodoo.com"}])
    )
    svc = UrlService(auth_client)
    url1 = await svc.get_base_url()
    url2 = await svc.get_base_url()
    assert url1 == url2
    # Should only call the RPC once (cached)
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_base_url_force_refresh(auth_client):
    route = respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=_rpc_response([{"id": 1, "value": "https://myodoo.com"}])
    )
    svc = UrlService(auth_client)
    await svc.get_base_url()
    await svc.get_base_url(force_refresh=True)
    assert route.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("records", "enabled", "path", "token"),
    [
        (
            [{"access_url": "/my/orders/7", "access_token": "existing"}],
            True,
            "/my/orders/7?access_token=existing",
            "existing",
        ),
        ([{"access_url": "/my/orders/7", "access_token": False}], True, "/my/orders/7", None),
        ([{"access_url": "/my/orders/7"}], False, "/my/orders/7", None),
        ([], True, "/mail/view?model=sale.order&res_id=7", None),
        ([{"access_url": False}], True, "/mail/view?model=sale.order&res_id=7", None),
    ],
)
async def test_portal_existing_token_and_fallback(auth_client, records, enabled, path, token):
    from unittest.mock import AsyncMock, patch

    from godoo.client.services.urls import PortalUrlOptions

    _base_url_cache[id(auth_client)] = "https://myodoo.com"
    with (
        patch.object(auth_client, "read", new=AsyncMock(return_value=records)) as read,
        patch.object(auth_client, "call", new=AsyncMock()) as call,
    ):
        result = await auth_client.urls.get_portal_url("sale.order", 7, PortalUrlOptions(access_token=enabled))
    assert result.url == f"https://myodoo.com{path}"
    assert result.access_token == token
    read.assert_awaited_once_with("sale.order", 7, fields=["access_url", "access_token"] if enabled else ["access_url"])
    call.assert_not_awaited()
