"""Dispatch unit tests: str path (TYPED-04) + type[T] path (TYPED-03) + friendly error when [typed] missing."""

from __future__ import annotations

import json
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
from godoo.client.typed import Ref

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
# Finding #2: search_read typed path injects 'id' into fields sent to Odoo
# ------------------------------------------------------------------


def _extract_rpc_fields(request: httpx.Request) -> list[str] | None:
    """Extract the 'fields' value from a JSON-RPC execute_kw request body.

    The body structure is: params.args[6] = the kwargs dict passed to execute_kw.
    Returns None if no 'fields' key is present.
    """
    body = json.loads(request.content)
    rpc_args: list[object] = body.get("params", {}).get("args", [])
    # execute_kw args: [db, uid, password, model, method, positional_args, kwargs]
    if len(rpc_args) >= 7 and isinstance(rpc_args[6], dict):
        rpc_kwargs: dict[str, object] = rpc_args[6]  # type: ignore[assignment]
        fields = rpc_kwargs.get("fields")
        if isinstance(fields, list):
            return fields  # type: ignore[return-value]
    return None


@respx.mock
@pytest.mark.asyncio
async def test_search_read_typed_id_injected_into_fields(auth_client: OdooClient) -> None:
    """search_read typed path with fields=['name'] injects 'id' into the RPC payload."""
    captured_fields: list[list[str]] = []

    def _capture(request: httpx.Request, route: respx.Route) -> httpx.Response:
        fields = _extract_rpc_fields(request)
        if fields is not None:
            captured_fields.append(fields)
        return httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))

    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=_capture)
    result = await auth_client.search_read(TinyPartner, [], fields=["name"])
    assert len(result) == 1
    assert result[0].name == "Foo"
    assert len(captured_fields) == 1, "Expected exactly one RPC call with fields"
    assert "id" in captured_fields[0], f"'id' should be injected, got: {captured_fields[0]}"
    assert "name" in captured_fields[0]


@respx.mock
@pytest.mark.asyncio
async def test_search_read_typed_id_already_present_not_duplicated(auth_client: OdooClient) -> None:
    """search_read typed path does not duplicate 'id' when already in fields."""
    captured_fields: list[list[str]] = []

    def _capture(request: httpx.Request, route: respx.Route) -> httpx.Response:
        fields = _extract_rpc_fields(request)
        if fields is not None:
            captured_fields.append(fields)
        return httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))

    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=_capture)
    await auth_client.search_read(TinyPartner, [], fields=["id", "name"])
    assert len(captured_fields) == 1
    assert captured_fields[0].count("id") == 1, f"'id' should appear exactly once, got: {captured_fields[0]}"


@respx.mock
@pytest.mark.asyncio
async def test_read_typed_id_not_injected(auth_client: OdooClient) -> None:
    """read() typed path does NOT inject 'id' — Odoo read() always returns id."""
    captured_fields: list[list[str]] = []

    def _capture(request: httpx.Request, route: respx.Route) -> httpx.Response:
        fields = _extract_rpc_fields(request)
        if fields is not None:
            captured_fields.append(fields)
        return httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Foo"}]))

    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=_capture)
    await auth_client.read(TinyPartner, [1], fields=["name"])
    # read() passes fields as-is (no injection); Odoo read() always returns id
    assert len(captured_fields) == 1
    # No double-injection: fields list should be exactly ["name"]
    assert captured_fields[0] == ["name"]


# ------------------------------------------------------------------
# Finding #7: ValueError from derive_partial_model -> OdooValidationError
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_dispatch_unknown_field_raises_odoo_validation_search_read(
    auth_client: OdooClient,
) -> None:
    """search_read typed path wraps ValueError from derive_partial_model as OdooValidationError."""
    with pytest.raises(OdooValidationError, match="nonexistent_field"):
        await auth_client.search_read(TinyPartner, [], fields=["nonexistent_field"])


@respx.mock
@pytest.mark.asyncio
async def test_typed_dispatch_unknown_field_raises_odoo_validation_read(
    auth_client: OdooClient,
) -> None:
    """read() typed path wraps ValueError from derive_partial_model as OdooValidationError."""
    with pytest.raises(OdooValidationError, match="nonexistent_field"):
        await auth_client.read(TinyPartner, [1], fields=["nonexistent_field"])


# ------------------------------------------------------------------
# TEST-02: Ref-typed field wire-fidelity through full dispatch chain
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_read_typed_ref_field_populated(auth_client: OdooClient) -> None:
    """Ref-typed field is populated with _target_cls via wire transform (TEST-02)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "parent_id": [3, "Acme"]}]))
    )
    result = await auth_client.read(TinyPartner, [1])
    assert result[0].parent_id is not None
    assert result[0].parent_id.id == 3
    assert result[0].parent_id.name == "Acme"
    assert result[0].parent_id._target_cls is TinyPartner


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
