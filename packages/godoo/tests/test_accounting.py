"""Tests for the accounting service."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.services.accounting import (
    AccountingService,
    _m2o_id,
    _m2o_name,
    is_closing_entry_from_lines,
)

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
# m2o helpers
# ---------------------------------------------------------------------------


def test_m2o_id_list():
    assert _m2o_id([42, "Partner"]) == 42


def test_m2o_id_int():
    assert _m2o_id(7) == 7


def test_m2o_id_false():
    assert _m2o_id(False) is None


def test_m2o_id_empty_list():
    assert _m2o_id([]) is None


def test_m2o_name_list():
    assert _m2o_name([42, "Partner"]) == "Partner"


def test_m2o_name_false():
    assert _m2o_name(False) == ""


def test_m2o_name_int():
    assert _m2o_name(7) == ""


# ---------------------------------------------------------------------------
# is_closing_entry_from_lines
# ---------------------------------------------------------------------------


def test_is_closing_entry_empty():
    assert is_closing_entry_from_lines([]) is False


def test_is_closing_entry_nets_nonzero():
    lines = [{"debit": 100, "credit": 0, "name": "closing"}]
    assert is_closing_entry_from_lines(lines) is False


def test_is_closing_entry_closing_name():
    lines = [
        {"debit": 100, "credit": 0, "name": "Year-end closing"},
        {"debit": 0, "credit": 100, "name": "Year-end closing"},
    ]
    assert is_closing_entry_from_lines(lines) is True


def test_is_closing_entry_no_hint():
    lines = [
        {"debit": 100, "credit": 0, "name": "Regular entry"},
        {"debit": 0, "credit": 100, "name": "Regular entry"},
    ]
    assert is_closing_entry_from_lines(lines) is False


# ---------------------------------------------------------------------------
# discover_cash_accounts — mock
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_discover_cash_accounts(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=_rpc_response(
            [
                {"id": 1, "name": "Cash", "code": "CSH", "company_id": [1, "My Company"]},
                {"id": 2, "name": "Bank", "code": "BNK", "company_id": [1, "My Company"]},
            ]
        )
    )
    svc = AccountingService(auth_client)
    accounts = await svc.discover_cash_accounts()
    assert len(accounts) == 2
    assert accounts[0].name == "Cash"
    assert accounts[0].company_id == 1
