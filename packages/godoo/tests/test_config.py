"""Tests for config_from_env and create_client."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.errors import OdooError


def _jsonrpc_result(result):
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def test_config_from_env_default_prefix(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://odoo.test")
    monkeypatch.setenv("ODOO_DB", "mydb")
    monkeypatch.setenv("ODOO_USER", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "secret")

    from godoo.config import config_from_env

    config = config_from_env()
    assert config.url == "http://odoo.test"
    assert config.database == "mydb"
    assert config.username == "admin"
    assert config.password == "secret"


def test_config_from_env_custom_prefix(monkeypatch):
    monkeypatch.setenv("ODOO_PROD_URL", "http://prod.odoo.test")
    monkeypatch.setenv("ODOO_PROD_DB", "proddb")
    monkeypatch.setenv("ODOO_PROD_USER", "produser")
    monkeypatch.setenv("ODOO_PROD_PASSWORD", "prodpass")

    from godoo.config import config_from_env

    config = config_from_env(prefix="ODOO_PROD")
    assert config.url == "http://prod.odoo.test"
    assert config.database == "proddb"
    assert config.username == "produser"
    assert config.password == "prodpass"


def test_config_from_env_database_alias(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://odoo.test")
    monkeypatch.setenv("ODOO_DATABASE", "aliasdb")
    monkeypatch.setenv("ODOO_USER", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "secret")
    # Ensure the primary key is absent
    monkeypatch.delenv("ODOO_DB", raising=False)

    from importlib import reload

    import godoo.config as cfg_mod

    reload(cfg_mod)
    from godoo.config import config_from_env

    config = config_from_env()
    assert config.database == "aliasdb"


def test_config_from_env_username_alias(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://odoo.test")
    monkeypatch.setenv("ODOO_DB", "mydb")
    monkeypatch.setenv("ODOO_USERNAME", "aliasuser")
    monkeypatch.setenv("ODOO_PASSWORD", "secret")
    monkeypatch.delenv("ODOO_USER", raising=False)

    from godoo.config import config_from_env

    config = config_from_env()
    assert config.username == "aliasuser"


def test_config_from_env_missing_vars_raises(monkeypatch):
    # Clear all relevant env vars
    for var in ["ODOO_URL", "ODOO_DB", "ODOO_DATABASE", "ODOO_USER", "ODOO_USERNAME", "ODOO_PASSWORD"]:
        monkeypatch.delenv(var, raising=False)

    from godoo.config import config_from_env

    with pytest.raises(OdooError) as exc_info:
        config_from_env()
    # Should mention missing vars
    assert "ODOO_URL" in str(exc_info.value)


def test_config_from_env_partial_missing_raises(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://odoo.test")
    for var in ["ODOO_DB", "ODOO_DATABASE", "ODOO_USER", "ODOO_USERNAME", "ODOO_PASSWORD"]:
        monkeypatch.delenv(var, raising=False)

    from godoo.config import config_from_env

    with pytest.raises(OdooError):
        config_from_env()


@respx.mock
@pytest.mark.asyncio
async def test_create_client_authenticates(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://odoo.test")
    monkeypatch.setenv("ODOO_DB", "mydb")
    monkeypatch.setenv("ODOO_USER", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "secret")

    respx.post("http://odoo.test/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))

    from godoo.config import create_client

    client = await create_client()
    assert client.is_authenticated()
    assert client.get_session().uid == 2
