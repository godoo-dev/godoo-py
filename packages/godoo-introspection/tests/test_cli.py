"""Tests for godoo-introspect CLI — validation paths and mocked happy-path."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import respx
from godoo.client.errors import OdooAuthError, OdooNetworkError
from godoo.introspection.cli import app
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

runner = CliRunner()

BASE_URL = "http://odoo.test"


def _rpc_response(result: object, id: int = 1) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": id, "result": result})


# ------------------------------------------------------------------
# Validation-only tests (no network)
# ------------------------------------------------------------------


def test_generate_requires_models_or_all(tmp_path: Path) -> None:
    """generate with neither --models nor --all exits 1 and explains the error."""
    result = runner.invoke(app, ["generate", "--output", str(tmp_path)])
    assert result.exit_code == 1
    assert "provide --models" in (result.output or result.stdout)


def test_generate_models_and_all_mutually_exclusive(tmp_path: Path) -> None:
    """generate with both --models and --all exits 1 and notes they are mutually exclusive."""
    result = runner.invoke(app, ["generate", "--output", str(tmp_path), "--models", "res.*", "--all"])
    assert result.exit_code == 1
    assert "mutually exclusive" in (result.output or result.stdout)


def test_generate_bad_output_dir() -> None:
    """generate with a non-existent output directory exits 1 and mentions does not exist."""
    result = runner.invoke(app, ["generate", "--output", "/nonexistent/path/xyz123", "--all"])
    assert result.exit_code == 1
    assert "does not exist" in (result.output or result.stdout)


def test_generate_password_not_in_output(tmp_path: Path) -> None:
    """Password must never appear in CLI output — not even on auth failure paths."""
    secret = "s3cr3t_password_xyz"
    result = runner.invoke(
        app,
        [
            "generate",
            "--output",
            str(tmp_path),
            "--all",
            "--password",
            secret,
            "--url",
            "http://fake",
            "--db",
            "fake",
            "--user",
            "admin",
        ],
    )
    # Password must not appear in any output even if the call fails
    assert secret not in (result.output or "")


# ------------------------------------------------------------------
# Network-mocked happy-path test
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# Finding #6: OdooError (auth/network) caught in CLI generate sync wrapper
# ------------------------------------------------------------------


def test_generate_auth_error_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OdooAuthError raised inside asyncio.run is caught and exits with code 1."""
    exc_instance = OdooAuthError("bad creds")

    from godoo.introspection import cli as cli_module

    async def _raise_async(*_: object) -> None:
        raise exc_instance

    monkeypatch.setattr(cli_module, "_generate_async", _raise_async)
    result = runner.invoke(
        app,
        [
            "generate",
            "--output",
            str(tmp_path),
            "--all",
            "--url",
            "http://fake",
            "--db",
            "fake",
            "--user",
            "admin",
            "--password",
            "admin",
        ],
    )
    assert result.exit_code == 1
    assert "bad creds" in (result.output or "")


def test_generate_network_error_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OdooNetworkError raised inside asyncio.run is caught and exits with code 1."""
    exc_instance = OdooNetworkError("connection refused")

    from godoo.introspection import cli as cli_module

    async def _raise_async(*_: object) -> None:
        raise exc_instance

    monkeypatch.setattr(cli_module, "_generate_async", _raise_async)
    result = runner.invoke(
        app,
        [
            "generate",
            "--output",
            str(tmp_path),
            "--all",
            "--url",
            "http://fake",
            "--db",
            "fake",
            "--user",
            "admin",
            "--password",
            "admin",
        ],
    )
    assert result.exit_code == 1
    assert "connection refused" in (result.output or "")


def test_generate_odoo_error_password_not_in_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Password must not appear in CLI output even when OdooAuthError is raised (T-w2x-02)."""
    secret_password = "super_secret_password_xyz"
    exc_instance = OdooAuthError("invalid login")

    from godoo.introspection import cli as cli_module

    async def _raise_async(*_: object) -> None:
        raise exc_instance

    monkeypatch.setattr(cli_module, "_generate_async", _raise_async)
    result = runner.invoke(
        app,
        [
            "generate",
            "--output",
            str(tmp_path),
            "--all",
            "--url",
            "http://fake",
            "--db",
            "fake",
            "--user",
            "admin",
            "--password",
            secret_password,
        ],
    )
    assert result.exit_code == 1
    assert secret_password not in (result.output or ""), "Password must never appear in CLI output"


# ------------------------------------------------------------------
# Network-mocked happy-path test
# ------------------------------------------------------------------


def test_generate_happy_path_writes_files(tmp_path: Path) -> None:
    """Full path: mock auth + ir.model search_read + get_schemas RPCs → files written."""
    ir_model_records_all = [
        {"id": 1, "name": "Language", "model": "res.lang", "transient": False},
    ]
    ir_model_records_schema = [
        {"id": 1, "name": "Language", "model": "res.lang", "transient": False},
    ]
    ir_model_field_records = [
        {
            "id": 10,
            "name": "name",
            "ttype": "char",
            "field_description": "Name",
            "relation": False,
            "relation_field": False,
            "required": False,
            "readonly": False,
            "store": True,
            "index": False,
            "copied": True,
            "translate": False,
            "help": "",
            "compute": False,
            "depends": "",
            "modules": "",
            "on_delete": False,
            "size": False,
            "selection_ids": [],
            "model": "res.lang",
        },
    ]
    # RPC sequence:
    #  1. authenticate → uid=2
    #  2. ir.model search_read (--all: list all non-transient models)
    #  3. ir.model search_read inside get_schemas (model metadata)
    #  4. ir.model.fields search_read inside get_schemas (field data)
    responses = iter(
        [
            _rpc_response(2),  # authenticate → uid=2
            _rpc_response(ir_model_records_all),  # ir.model search_read for all model names
            _rpc_response(ir_model_records_schema),  # ir.model inside get_schemas
            _rpc_response(ir_model_field_records),  # ir.model.fields inside get_schemas
        ]
    )
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=responses)
        result = runner.invoke(
            app,
            [
                "generate",
                "--output",
                str(tmp_path),
                "--all",
                "--url",
                BASE_URL,
                "--db",
                "testdb",
                "--user",
                "admin",
                "--password",
                "admin",
            ],
        )
    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "Generated" in result.output
    assert (tmp_path / "res_lang.py").exists()
    assert (tmp_path / "__init__.py").exists()
    content = (tmp_path / "res_lang.py").read_text()
    assert "OdooBaseModel" in content
    assert '__odoo_model__: ClassVar[str] = "res.lang"' in content
