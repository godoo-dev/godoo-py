"""Dispatch unit tests: str path (TYPED-04) + type[T] path (TYPED-03) + friendly error when [typed] missing."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import httpx
import pytest
import respx
from godoo.client._pydantic_transform import OdooBaseModel
from godoo.client.client import OdooClient, OdooClientConfig
from godoo.client.errors import OdooValidationError

BASE_URL = "http://odoo.test"
DB = "testdb"


def _jsonrpc_result(result: object) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def _make_config(**kwargs: object) -> OdooClientConfig:
    defaults: dict[str, object] = dict(url=BASE_URL, database=DB, username="admin", password="admin")
    defaults.update(kwargs)
    return OdooClientConfig(**defaults)  # type: ignore[arg-type]


@pytest.fixture
async def auth_client() -> AsyncGenerator[OdooClient]:
    c = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await c.authenticate()
    yield c


# ------------------------------------------------------------------
# Model fixture
# ------------------------------------------------------------------


class TinyPartner(OdooBaseModel):
    """Minimal model for dispatch tests."""

    __odoo_model__: ClassVar[str] = "res.partner"
    id: int
    name: str | None = None


# ------------------------------------------------------------------
# str path — TYPED-04 regression
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_read_str_path_returns_dicts(auth_client: OdooClient) -> None:
    """str path returns list[dict] unchanged from v1.0 (TYPED-04 invariant)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))
    )
    result = await auth_client.read("res.partner", [1])
    assert isinstance(result, list)
    assert isinstance(result[0], dict)
    assert result[0]["name"] == "Foo"


@respx.mock
@pytest.mark.asyncio
async def test_search_read_str_path_returns_dicts(auth_client: OdooClient) -> None:
    """search_read str path returns list[dict] unchanged (TYPED-04)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))
    )
    result = await auth_client.search_read("res.partner", [])
    assert isinstance(result, list)
    assert isinstance(result[0], dict)
    assert result[0]["name"] == "Foo"


# ------------------------------------------------------------------
# type[T] path — TYPED-03
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_read_typed_path_returns_models(auth_client: OdooClient) -> None:
    """type[T] path returns list[T] with validated instances (TYPED-03)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))
    )
    result = await auth_client.read(TinyPartner, [1])
    assert isinstance(result, list)
    assert all(isinstance(r, TinyPartner) for r in result)
    assert result[0].name == "Foo"


@respx.mock
@pytest.mark.asyncio
async def test_read_typed_applies_wire_transforms(auth_client: OdooClient) -> None:
    """type[T] path applies OdooBaseModel wire transforms (False -> None)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": False}]))
    )
    result = await auth_client.read(TinyPartner, [1])
    assert result[0].name is None


@respx.mock
@pytest.mark.asyncio
async def test_search_read_typed_path_returns_models(auth_client: OdooClient) -> None:
    """search_read type[T] path returns list[T] with validated instances (TYPED-03)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))
    )
    result = await auth_client.search_read(TinyPartner, [])
    assert isinstance(result, list)
    assert all(isinstance(r, TinyPartner) for r in result)
    assert result[0].name == "Foo"


# ------------------------------------------------------------------
# hasattr dispatch guard — D-04
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_dispatch_via_hasattr_takes_typed_branch(auth_client: OdooClient) -> None:
    """hasattr(__odoo_model__) dispatch routes to typed branch even for non-BaseModel classes.

    The typed branch fires (D-04), then `model_validate` on a non-BaseModel class
    raises AttributeError — confirming dispatch went to the typed path (not the str
    path, which would have returned a list[dict] without error).
    """

    class Marker:
        __odoo_model__: ClassVar[str] = "x.y"

    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1}])))
    with pytest.raises((AttributeError, TypeError)):
        await auth_client.read(Marker, [1])


# ------------------------------------------------------------------
# Missing pydantic friendly error — Open Q3
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_dispatch_without_pydantic_raises_friendly_error(
    auth_client: OdooClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulating missing pydantic yields OdooValidationError with install hint.

    We block the _pydantic_transform module by setting it to None in sys.modules,
    which causes the lazy import inside read() to raise ModuleNotFoundError.
    The friendly-error wrap in Task 1 converts this to OdooValidationError with
    the canonical install-hint message.
    """
    monkeypatch.setitem(sys.modules, "godoo.client._pydantic_transform", None)
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))
    )
    with pytest.raises(OdooValidationError) as exc_info:
        await auth_client.read(TinyPartner, [1])
    assert "Install with: pip install 'godoo-client[typed]'" in str(exc_info.value)
