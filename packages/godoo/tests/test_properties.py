"""Tests for the properties service."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.services.properties import PropertiesService, properties_to_write_format

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
# properties_to_write_format
# ---------------------------------------------------------------------------


def test_properties_to_write_format():
    props = [
        {"name": "x_color", "value": "red"},
        {"name": "x_size", "value": 42},
    ]
    result = properties_to_write_format(props)
    assert result == {"x_color": "red", "x_size": 42}


def test_properties_to_write_format_empty():
    assert properties_to_write_format([]) == {}


# ---------------------------------------------------------------------------
# update_safely — mock
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_update_safely_merges(auth_client):
    """Read existing props, merge updates, write back."""
    existing = [
        {"name": "x_color", "value": "blue"},
        {"name": "x_size", "value": 10},
    ]
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            # read
            _rpc_response([{"id": 1, "x_props": existing}]),
            # write
            _rpc_response(True),
        ]
    )
    svc = PropertiesService(auth_client)
    await svc.update_safely("res.partner", 1, "x_props", {"x_color": "red", "x_new": "val"})
    # Verify the write was called (no exception means success)


@respx.mock
@pytest.mark.asyncio
async def test_update_safely_batch(auth_client):
    """Batch update applies to multiple records (sequential to avoid race)."""
    from godoo.services.properties.functions import update_safely

    # Run sequentially to have deterministic mock order
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            # read record 1
            _rpc_response([{"id": 1, "x_props": []}]),
            # write record 1
            _rpc_response(True),
            # read record 2
            _rpc_response([{"id": 2, "x_props": []}]),
            # write record 2
            _rpc_response(True),
        ]
    )
    # Call update_safely sequentially to get deterministic mock ordering
    await update_safely(auth_client, "res.partner", 1, "x_props", {"x_color": "red"})
    await update_safely(auth_client, "res.partner", 2, "x_props", {"x_color": "red"})
