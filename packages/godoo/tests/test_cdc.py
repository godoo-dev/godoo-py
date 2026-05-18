"""Tests for the CDC service."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.services.cdc import CdcService, clear_cache, get_cached, set_cached
from godoo.services.cdc.resolver import resolve_values
from godoo.services.cdc.types import FieldMeta

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
    clear_cache()
    yield client
    await client.aclose()
    clear_cache()


# ---------------------------------------------------------------------------
# resolver — different field types
# ---------------------------------------------------------------------------


def test_resolve_integer():
    row = {"old_value_integer": 5, "new_value_integer": 10}
    old, new = resolve_values(row, "integer")
    assert old.raw == 5
    assert new.raw == 10
    assert old.display == "5"


def test_resolve_float():
    row = {"old_value_float": 1.5, "new_value_float": 3.0}
    old, new = resolve_values(row, "float")
    assert old.raw == 1.5
    assert new.raw == 3.0


def test_resolve_char():
    row = {"old_value_char": "draft", "new_value_char": "posted"}
    old, new = resolve_values(row, "char")
    assert old.raw == "draft"
    assert new.raw == "posted"


def test_resolve_many2one():
    row = {
        "old_value_integer": 1,
        "old_value_char": "Partner A",
        "new_value_integer": 2,
        "new_value_char": "Partner B",
    }
    old, new = resolve_values(row, "many2one")
    assert old.raw == 1
    assert old.display == "Partner A"
    assert new.raw == 2
    assert new.display == "Partner B"


def test_resolve_boolean():
    row = {"old_value_integer": 0, "new_value_integer": 1}
    old, new = resolve_values(row, "boolean")
    assert old.raw is False
    assert new.raw is True


def test_resolve_datetime():
    row = {"old_value_datetime": "2026-01-01 00:00:00", "new_value_datetime": "2026-01-02 00:00:00"}
    old, _new = resolve_values(row, "datetime")
    assert old.raw == "2026-01-01 00:00:00"


# ---------------------------------------------------------------------------
# field_cache
# ---------------------------------------------------------------------------


def test_cache_set_and_get():
    clear_cache()
    meta = FieldMeta(name="state", field_type="selection")
    set_cached("sale.order", "state", meta)
    result = get_cached("sale.order", "state")
    assert result is not None
    assert result.field_type == "selection"


def test_cache_miss():
    clear_cache()
    assert get_cached("sale.order", "nonexistent") is None


# ---------------------------------------------------------------------------
# check — mock
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_check_model_has_tracking(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=_rpc_response(
            [
                {"id": 1, "name": "state"},
                {"id": 2, "name": "partner_id"},
            ]
        )
    )
    svc = CdcService(auth_client)
    result = await svc.check("sale.order")
    assert result.has_tracking is True
    assert "state" in result.tracked_fields
    assert "partner_id" in result.tracked_fields


@respx.mock
@pytest.mark.asyncio
async def test_check_model_no_tracking(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([]))
    svc = CdcService(auth_client)
    result = await svc.check("res.config.settings")
    assert result.has_tracking is False
    assert result.tracked_fields == []
