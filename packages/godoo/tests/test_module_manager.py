"""Tests for ModuleManager using respx mock."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig
from godoo.services.modules import ModuleManager

BASE_URL = "http://odoo.test"
DB = "testdb"

MODULE_FIELDS = [
    "id",
    "name",
    "state",
    "shortdesc",
    "summary",
    "description",
    "author",
    "website",
    "installed_version",
    "latest_version",
    "license",
    "application",
    "category_id",
]


def _rpc_response(result, id=1) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})


def _auth_response() -> httpx.Response:
    return _rpc_response(2)


def _make_client() -> OdooClient:
    config = OdooClientConfig(url=BASE_URL, database=DB, username="admin", password="admin")
    return OdooClient(config)


@pytest.fixture
async def auth_client():
    client = _make_client()
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_auth_response())
        await client.authenticate()
    yield client
    await client.aclose()


# ---------------------------------------------------------------------------
# is_module_installed
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_is_module_installed_true(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([42]))
    mgr = ModuleManager(auth_client)
    result = await mgr.is_module_installed("sale")
    assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_is_module_installed_false(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([]))
    mgr = ModuleManager(auth_client)
    result = await mgr.is_module_installed("nonexistent_module")
    assert result is False


# ---------------------------------------------------------------------------
# install_module — already installed
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_install_module_already_installed(auth_client):
    """When module state is already 'installed', return early without calling install."""
    module_info = {"id": 10, "name": "sale", "state": "installed", "shortdesc": "Sales"}
    # search_read returns the module already installed
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([module_info]))
    mgr = ModuleManager(auth_client)
    result = await mgr.install_module("sale")
    assert result["state"] == "installed"
    assert result["name"] == "sale"


# ---------------------------------------------------------------------------
# install_module — normal flow
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_install_module_normal_flow(auth_client):
    """search → state=uninstalled → button_immediate_install → fetch updated info."""
    module_before = {"id": 10, "name": "sale", "state": "uninstalled", "shortdesc": "Sales"}
    module_after = {"id": 10, "name": "sale", "state": "installed", "shortdesc": "Sales"}

    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            _rpc_response([module_before]),  # search_read to find module
            _rpc_response(True),  # button_immediate_install
            _rpc_response([module_after]),  # search_read to fetch updated info
        ]
    )
    mgr = ModuleManager(auth_client)
    result = await mgr.install_module("sale")
    assert result["state"] == "installed"


# ---------------------------------------------------------------------------
# install_module — not found
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_install_module_not_found(auth_client):
    """Raise RuntimeError when module does not exist."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response([]))
    mgr = ModuleManager(auth_client)
    with pytest.raises(RuntimeError, match="not found"):
        await mgr.install_module("nonexistent_module")


# ---------------------------------------------------------------------------
# uninstall_module — normal flow
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_uninstall_module_normal_flow(auth_client):
    """search → state=installed → button_immediate_uninstall → fetch updated info."""
    module_before = {"id": 10, "name": "sale", "state": "installed", "shortdesc": "Sales"}
    module_after = {"id": 10, "name": "sale", "state": "uninstalled", "shortdesc": "Sales"}

    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            _rpc_response([module_before]),  # search_read to find module
            _rpc_response(True),  # button_immediate_uninstall
            _rpc_response([module_after]),  # search_read to fetch updated info
        ]
    )
    mgr = ModuleManager(auth_client)
    result = await mgr.uninstall_module("sale")
    assert result["state"] == "uninstalled"


# ---------------------------------------------------------------------------
# list_modules — with state filter
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_list_modules_with_state_filter(auth_client):
    modules = [
        {"id": 1, "name": "sale", "state": "installed"},
        {"id": 2, "name": "purchase", "state": "installed"},
    ]
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=_rpc_response(modules))
    mgr = ModuleManager(auth_client)
    result = await mgr.list_modules(state="installed")
    assert len(result) == 2
    assert all(m["state"] == "installed" for m in result)


# ---------------------------------------------------------------------------
# install_module — ir_cron retry
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_install_module_retries_on_ir_cron_lock(auth_client):
    """First attempt fails with ir_cron error, second succeeds."""
    module_before = {"id": 10, "name": "sale", "state": "uninstalled", "shortdesc": "Sales"}
    module_after = {"id": 10, "name": "sale", "state": "installed", "shortdesc": "Sales"}

    ir_cron_error_response = httpx.Response(
        200,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": 200,
                "message": "Odoo Server Error",
                "data": {
                    "name": "odoo.exceptions.UserError",
                    "exception_type": "user_error",
                    "message": "Unable to acquire lock on ir_cron table",
                },
            },
        },
    )

    respx.post(f"{BASE_URL}/jsonrpc").mock(
        side_effect=[
            _rpc_response([module_before]),  # search_read to find module
            ir_cron_error_response,  # button_immediate_install fails (ir_cron)
            _rpc_response(True),  # button_immediate_install succeeds on retry
            _rpc_response([module_after]),  # search_read to fetch updated info
        ]
    )
    mgr = ModuleManager(auth_client, retry_delay=0.01)
    result = await mgr.install_module("sale")
    assert result["state"] == "installed"
