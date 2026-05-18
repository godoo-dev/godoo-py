"""Tests for the timesheets service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.errors import OdooValidationError
from godoo.services.timesheets import LogTimeOptions, TimesheetsService, stop_timer

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
# log_time validation
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_log_time_zero_hours_raises(auth_client):
    svc = TimesheetsService(auth_client)
    with pytest.raises(OdooValidationError, match="positive"):
        await svc.log_time(LogTimeOptions(project_id=1, hours=0))


@respx.mock
@pytest.mark.asyncio
async def test_log_time_negative_hours_raises(auth_client):
    svc = TimesheetsService(auth_client)
    with pytest.raises(OdooValidationError, match="positive"):
        await svc.log_time(LogTimeOptions(project_id=1, hours=-1))


# ---------------------------------------------------------------------------
# stop_timer elapsed calculation
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_stop_timer_elapsed_calc(auth_client):
    """stop_timer should compute elapsed hours from create_date."""
    two_hours_ago = (datetime.now(UTC) - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            # read timesheet
            _rpc_response(
                [
                    {
                        "id": 10,
                        "employee_id": 7,
                        "project_id": 1,
                        "task_id": False,
                        "name": "timer",
                        "unit_amount": 0,
                        "date": "2026-01-01",
                        "create_date": two_hours_ago,
                    }
                ]
            ),
            # write
            _rpc_response(True),
        ]
    )
    result = await stop_timer(auth_client, 10)
    # Should be approximately 2 hours
    assert 1.9 <= result["unit_amount"] <= 2.1


@respx.mock
@pytest.mark.asyncio
async def test_stop_timer_minimum_hours(auth_client):
    """stop_timer should return at least 0.01h."""
    just_now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            _rpc_response(
                [
                    {
                        "id": 10,
                        "employee_id": 7,
                        "project_id": 1,
                        "task_id": False,
                        "name": "timer",
                        "unit_amount": 0,
                        "date": "2026-01-01",
                        "create_date": just_now,
                    }
                ]
            ),
            _rpc_response(True),
        ]
    )
    result = await stop_timer(auth_client, 10)
    assert result["unit_amount"] >= 0.01
