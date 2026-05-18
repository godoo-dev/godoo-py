"""Tests for the URLs service."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.services.urls import UrlService
from godoo.services.urls.functions import _base_url_cache

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
