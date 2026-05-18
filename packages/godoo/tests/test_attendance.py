"""Tests for the attendance service."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.errors import OdooValidationError
from godoo.services.attendance import AttendanceService, resolve_employee_id

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
# resolve_employee_id
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_resolve_employee_id_explicit(auth_client):
    result = await resolve_employee_id(auth_client, 42)
    assert result == 42


@respx.mock
@pytest.mark.asyncio
async def test_resolve_employee_id_from_session(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([7]))
    result = await resolve_employee_id(auth_client)
    assert result == 7


@respx.mock
@pytest.mark.asyncio
async def test_resolve_employee_id_not_found(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([]))
    with pytest.raises(OdooValidationError, match=r"No hr\.employee"):
        await resolve_employee_id(auth_client)


# ---------------------------------------------------------------------------
# clock_in when already clocked in
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_clock_in_already_clocked_in_raises(auth_client):
    """Should raise when employee is already clocked in."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            # resolve_employee_id -> search hr.employee
            _rpc_response([7]),
            # get_status -> search_read hr.attendance (no check_out = clocked in)
            _rpc_response([{"id": 1, "employee_id": 7, "check_in": "2026-01-01 08:00:00"}]),
        ]
    )
    svc = AttendanceService(auth_client)
    with pytest.raises(OdooValidationError, match="already clocked in"):
        await svc.clock_in()


# ---------------------------------------------------------------------------
# clock_in basic flow
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_clock_in_success(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            # resolve_employee_id
            _rpc_response([7]),
            # get_status -> no records (not clocked in)
            _rpc_response([]),
            # create attendance
            _rpc_response(100),
        ]
    )
    svc = AttendanceService(auth_client)
    rec = await svc.clock_in()
    assert rec.id == 100
    assert rec.employee_id == 7
