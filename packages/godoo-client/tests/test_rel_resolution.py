"""Resolution behavior tests for client.read(Ref[T]) and client.read(list[Ref[T]]) dispatch (REL-02..REL-05)."""

from __future__ import annotations

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
# Model fixtures
# ------------------------------------------------------------------


class TinyPartner(OdooBaseModel):
    """Minimal partner model for Ref resolution tests."""

    __odoo_model__: ClassVar[str] = "res.partner"
    id: int
    name: str | None = None


class TinyMove(OdooBaseModel):
    """Minimal account.move model for heterogeneous Ref resolution tests."""

    __odoo_model__: ClassVar[str] = "account.move"
    id: int
    name: str | None = None


# ------------------------------------------------------------------
# REL-02: Single-ref resolution
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_read_single_ref_resolves(auth_client: OdooClient) -> None:
    """read(Ref[T]) resolves to a single model instance via one RPC (REL-02)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 42, "name": "Acme"}]))
    )
    ref: Ref[TinyPartner] = Ref(id=42, name="Acme", _target_cls=TinyPartner)
    result = await auth_client.read(ref)
    assert isinstance(result, TinyPartner)
    assert result.id == 42


# ------------------------------------------------------------------
# REL-03: Homogeneous list — one batched RPC
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_read_homogeneous_list_resolves(auth_client: OdooClient) -> None:
    """read(list[Ref[T]]) batches ids into one RPC for same-model refs (REL-03)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]))
    )
    refs = [
        Ref(id=1, name="A", _target_cls=TinyPartner),
        Ref(id=2, name="B", _target_cls=TinyPartner),
    ]
    result = await auth_client.read(refs)
    assert len(result) == 2
    assert result[0].id == 1
    assert result[1].id == 2
    # Exactly one RPC call (the auth mock ran in its own respx.mock scope)
    assert len(respx.calls) == 1


# ------------------------------------------------------------------
# REL-02 + REL-03 + D-02: Heterogeneous list — two RPCs, order preserved
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_read_heterogeneous_list_preserves_order(auth_client: OdooClient) -> None:
    """read(list[Ref]) with mixed models issues one RPC per distinct target model,
    results stitched back in input order (REL-02, REL-03, D-02)."""
    responses = iter(
        [
            httpx.Response(200, json=_jsonrpc_result([{"id": 1, "name": "Partner"}])),
            httpx.Response(200, json=_jsonrpc_result([{"id": 7, "name": "Move"}])),
        ]
    )
    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=lambda req, route: next(responses))
    refs = [
        Ref(id=1, name="Partner", _target_cls=TinyPartner),
        Ref(id=7, name="Move", _target_cls=TinyMove),
    ]
    result = await auth_client.read(refs)
    assert len(result) == 2
    assert isinstance(result[0], TinyPartner)
    assert isinstance(result[1], TinyMove)
    assert result[0].id == 1
    assert result[1].id == 7
    # Two RPCs — one per distinct target model
    assert len(respx.calls) == 2


# ------------------------------------------------------------------
# REL-04: Untyped-ref guard — raises before any RPC
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_read_untyped_ref_raises_before_rpc(auth_client: OdooClient) -> None:
    """read(Ref) with _target_cls=None raises OdooValidationError BEFORE any RPC (REL-04)."""
    untyped: Ref[int] = Ref(id=42, name="X")  # _target_cls defaults to None
    with pytest.raises(OdooValidationError, match="no target model known"):
        await auth_client.read(untyped)
    # No RPC was fired — auth ran in a separate respx.mock scope
    assert len(respx.calls) == 0
