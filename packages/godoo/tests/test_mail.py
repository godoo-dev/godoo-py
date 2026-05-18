"""Tests for the mail service."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.errors import OdooValidationError
from godoo.services.mail import MailService, PostMessageOptions, ensure_html_body

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
    yield client
    await client.aclose()


# ---------------------------------------------------------------------------
# ensure_html_body
# ---------------------------------------------------------------------------


def test_ensure_html_body_empty_raises():
    with pytest.raises(OdooValidationError):
        ensure_html_body("")


def test_ensure_html_body_whitespace_raises():
    with pytest.raises(OdooValidationError):
        ensure_html_body("   ")


def test_ensure_html_body_plain_text():
    assert ensure_html_body("Hello world") == "<p>Hello world</p>"


def test_ensure_html_body_html_passthrough():
    html = "<div>Hello</div>"
    assert ensure_html_body(html) == html


# ---------------------------------------------------------------------------
# post_internal_note — mock
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_post_internal_note_returns_int(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(42))
    svc = MailService(auth_client)
    result = await svc.post_internal_note("res.partner", 1, "Test note")
    assert result == 42


@respx.mock
@pytest.mark.asyncio
async def test_post_internal_note_returns_list(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([99]))
    svc = MailService(auth_client)
    result = await svc.post_internal_note("res.partner", 1, "Test note")
    assert result == 99


@respx.mock
@pytest.mark.asyncio
async def test_post_internal_note_returns_dict(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response({"id": 77}))
    svc = MailService(auth_client)
    result = await svc.post_internal_note("res.partner", 1, "Test note")
    assert result == 77


@respx.mock
@pytest.mark.asyncio
async def test_post_open_message(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(55))
    svc = MailService(auth_client)
    opts = PostMessageOptions(partner_ids=[1, 2])
    result = await svc.post_open_message("sale.order", 10, "Hello", opts)
    assert result == 55
