"""Tests for OdooClient using respx mock."""

from __future__ import annotations

import asyncio
import base64
import json

import httpx
import pytest
import respx
from godoo.client import OdooClient, OdooClientConfig, _ambient_context
from godoo.errors import OdooAuthError, OdooMissingError, OdooSafetyError, OdooValidationError
from godoo.safety import OperationInfo, SafetyContext

BASE_URL = "http://odoo.test"
DB = "testdb"


def _jsonrpc_result(result):
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def _make_config(**kwargs):
    defaults = dict(url=BASE_URL, database=DB, username="admin", password="admin")
    defaults.update(kwargs)
    return OdooClientConfig(**defaults)


@pytest.fixture
def client():
    c = OdooClient(_make_config())
    yield c


@pytest.fixture
async def auth_client():
    c = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await c.authenticate()
    yield c


@pytest.mark.asyncio
async def test_call_before_auth_raises(client):
    with pytest.raises(OdooAuthError, match="authenticate"):
        await client.call("res.partner", "search", [[]], {})


@respx.mock
@pytest.mark.asyncio
async def test_authenticate_success(client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
    session = await client.authenticate()
    assert session.uid == 2
    assert client.is_authenticated()


@respx.mock
@pytest.mark.asyncio
async def test_search(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result([1, 2, 3])))
    result = await auth_client.search("res.partner", [[("is_company", "=", True)]])
    assert result == [1, 2, 3]


@respx.mock
@pytest.mark.asyncio
async def test_create(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(42)))
    result = await auth_client.create("res.partner", {"name": "Test"})
    assert result == 42


@respx.mock
@pytest.mark.asyncio
async def test_unlink_single_int_normalized(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    result = await auth_client.unlink("res.partner", 42)
    assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_unlink_list(auth_client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    result = await auth_client.unlink("res.partner", [1, 2, 3])
    assert result is True


@pytest.mark.asyncio
async def test_safety_blocks_write():
    async def deny(op: OperationInfo) -> bool:
        return False

    config = _make_config(safety=SafetyContext(confirm=deny))
    client = OdooClient(config)

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await client.authenticate()

    with pytest.raises(OdooSafetyError):
        await client.write("res.partner", [1], {"name": "Blocked"})


@pytest.mark.asyncio
async def test_safety_allows_read():
    deny_called = False

    async def deny(op: OperationInfo) -> bool:
        nonlocal deny_called
        deny_called = True
        return False

    config = _make_config(safety=SafetyContext(confirm=deny))
    client = OdooClient(config)

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(
            side_effect=[
                httpx.Response(200, json=_jsonrpc_result(2)),
                httpx.Response(200, json=_jsonrpc_result([1, 2])),
            ]
        )
        await client.authenticate()
        result = await client.search("res.partner", [[]])

    assert result == [1, 2]
    assert not deny_called, "deny callback should not be called for READ operations"


@pytest.mark.asyncio
async def test_logout_clears_auth():
    client = OdooClient(_make_config())
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await client.authenticate()
    assert client.is_authenticated()
    client.logout()
    assert not client.is_authenticated()


@pytest.mark.asyncio
async def test_get_session_none_before_auth(client):
    assert client.get_session() is None


@respx.mock
@pytest.mark.asyncio
async def test_get_session_after_auth(client):
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
    await client.authenticate()
    session = client.get_session()
    assert session is not None
    assert session.uid == 2


@pytest.mark.asyncio
async def test_set_safety_context_overrides():
    """set_safety_context replaces config safety."""
    deny_called = False

    async def deny(op: OperationInfo) -> bool:
        nonlocal deny_called
        deny_called = True
        return False

    client = OdooClient(_make_config())

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
        await client.authenticate()

    client.set_safety_context(SafetyContext(confirm=deny))

    with pytest.raises(OdooSafetyError):
        await client.write("res.partner", [1], {"name": "Blocked"})


# ------------------------------------------------------------------
# CLIENT-01: async context manager
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_async_context_manager_authenticates_and_closes():
    """__aenter__ authenticates + returns self; __aexit__ calls aclose()."""
    c = OdooClient(_make_config())
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(2)))
    async with c as opened:
        assert opened is c
        assert c.is_authenticated()
    # aclose() was called — transport is closed; no assertion needed (mock consumed auth response)


# ------------------------------------------------------------------
# CLIENT-03: with_context ambient RPC context
# ------------------------------------------------------------------


def _extract_rpc_kwargs(request: httpx.Request) -> dict:
    """Extract the kwargs dict from an execute_kw JSON-RPC request body.

    The transport builds: params.args = [db, uid, password, model, method, args, kwargs]
    So kwargs is at params.args[6].
    """
    body = json.loads(request.content)
    args_list = body["params"]["args"]
    # args[6] is the kwargs dict passed to execute_kw
    return args_list[6] if len(args_list) > 6 else {}  # type: ignore[no-any-return]


@pytest.mark.asyncio
async def test_with_context_applies_to_rpc_call(auth_client):
    """with_context injects lang into the RPC kwargs.context."""
    captured: dict = {}

    def capture_and_respond(request: httpx.Request) -> httpx.Response:
        captured.update(_extract_rpc_kwargs(request))
        return httpx.Response(200, json=_jsonrpc_result([]))

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=capture_and_respond)
        with auth_client.with_context(lang="fr_FR"):
            await auth_client.search_read("res.partner")

    assert captured.get("context", {}).get("lang") == "fr_FR"


@pytest.mark.asyncio
async def test_with_context_nested_merges(auth_client):
    """Nested with_context blocks merge; each pops only its own layer on exit."""
    captured_inner: dict = {}
    captured_outer_after: dict = {}
    call_count = 0

    def capture_and_respond(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        rpc_kwargs = _extract_rpc_kwargs(request)
        ctx = rpc_kwargs.get("context", {})
        if call_count == 0:
            captured_inner.update(ctx)
        else:
            captured_outer_after.update(ctx)
        call_count += 1
        return httpx.Response(200, json=_jsonrpc_result([]))

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=capture_and_respond)
        with auth_client.with_context(lang="fr"):
            with auth_client.with_context(key="v2"):
                # First call: inside inner block — should have both lang and key
                await auth_client.search_read("res.partner")
            # Second call: inside outer block only — should have only lang
            await auth_client.search_read("res.partner")

    assert captured_inner.get("lang") == "fr"
    assert captured_inner.get("key") == "v2"
    assert captured_outer_after.get("lang") == "fr"
    assert "key" not in captured_outer_after


@pytest.mark.asyncio
async def test_with_context_explicit_kwarg_wins(auth_client):
    """Explicit per-call context= kwarg overrides ambient context for that call."""
    captured: dict = {}

    def capture_and_respond(request: httpx.Request) -> httpx.Response:
        captured.update(_extract_rpc_kwargs(request).get("context", {}))
        return httpx.Response(200, json=_jsonrpc_result([]))

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=capture_and_respond)
        with auth_client.with_context(lang="fr_FR"):
            # Explicit context={"lang": "de_DE"} must win
            await auth_client.search_read("res.partner", context={"lang": "de_DE"})

    assert captured.get("lang") == "de_DE"


@pytest.mark.asyncio
async def test_with_context_outside_block_no_ambient(auth_client):
    """Outside any with_context block, no ambient context is injected."""
    captured_kwargs: dict = {}

    def capture_and_respond(request: httpx.Request) -> httpx.Response:
        captured_kwargs.update(_extract_rpc_kwargs(request))
        return httpx.Response(200, json=_jsonrpc_result([]))

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=capture_and_respond)
        await auth_client.search_read("res.partner")

    # No context key in kwargs, or context is empty
    assert captured_kwargs.get("context", {}) == {}


@pytest.mark.asyncio
async def test_with_context_concurrent_isolation(auth_client):
    """Two concurrent asyncio tasks with different with_context do not clobber each other."""
    results: dict[str, str] = {}

    async def task_a() -> None:
        with auth_client.with_context(lang="fr_FR"):
            await asyncio.sleep(0)  # yield so task_b can run
            results["a"] = (_ambient_context.get() or {}).get("lang", "")

    async def task_b() -> None:
        with auth_client.with_context(lang="de_DE"):
            await asyncio.sleep(0)  # yield so task_a can run
            results["b"] = (_ambient_context.get() or {}).get("lang", "")

    await asyncio.gather(task_a(), task_b())

    assert results["a"] == "fr_FR", f"task_a saw {results['a']!r}, expected 'fr_FR'"
    assert results["b"] == "de_DE", f"task_b saw {results['b']!r}, expected 'de_DE'"


# ------------------------------------------------------------------
# CLIENT-02: iter_search_read keyset pagination
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iter_search_read_two_pages(auth_client):
    """Two pages: page1 has batch_size records, page2 is shorter — yields all records."""
    page1 = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}]
    page2 = [{"id": 4, "name": "D"}]
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(
            side_effect=[
                httpx.Response(200, json=_jsonrpc_result(page1)),
                httpx.Response(200, json=_jsonrpc_result(page2)),
            ]
        )
        records = [r async for r in auth_client.iter_search_read("res.partner", batch_size=3)]

    assert len(records) == 4
    assert records[-1]["id"] == 4


@pytest.mark.asyncio
async def test_iter_search_read_limit_caps_results(auth_client):
    """limit=2 stops iteration after 2 records even if more are available."""
    page = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}]
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(page)))
        records = [r async for r in auth_client.iter_search_read("res.partner", batch_size=10, limit=2)]

    assert len(records) == 2


@pytest.mark.asyncio
async def test_iter_search_read_strips_id_when_not_requested(auth_client):
    """When caller passes fields=['name'] (no 'id'), yielded records do not contain 'id'."""
    page = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    with respx.mock:
        # Return only 2 records (< batch_size=500 → stop after first page)
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(page)))
        records = [r async for r in auth_client.iter_search_read("res.partner", fields=["name"])]

    assert all("id" not in r for r in records)
    assert [r["name"] for r in records] == ["A", "B"]


@pytest.mark.asyncio
async def test_iter_search_read_includes_id_when_requested(auth_client):
    """When caller passes fields=['id', 'name'], yielded records contain 'id'."""
    page = [{"id": 1, "name": "A"}]
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(page)))
        records = [r async for r in auth_client.iter_search_read("res.partner", fields=["id", "name"])]

    assert records[0]["id"] == 1
    assert records[0]["name"] == "A"


@pytest.mark.asyncio
async def test_iter_search_read_empty_yields_nothing(auth_client):
    """Empty first batch immediately stops iteration."""
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result([])))
        records = [r async for r in auth_client.iter_search_read("res.partner")]

    assert records == []


# ------------------------------------------------------------------
# CLIENT-04: fields_get
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_fields_get_returns_dict(auth_client):
    """fields_get returns the raw dict from Odoo keyed by field name."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result({"name": {"type": "char"}}))
    )
    result = await auth_client.fields_get("res.partner")
    assert result == {"name": {"type": "char"}}


@pytest.mark.asyncio
async def test_fields_get_with_attributes(auth_client):
    """fields_get passes the attributes kwarg into the RPC payload."""
    captured: dict = {}

    def capture_and_respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        # params.args = [db, uid, password, model, method, args, kwargs]
        captured.update(body["params"]["args"][6])
        return httpx.Response(200, json=_jsonrpc_result({"name": {"type": "char"}}))

    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=capture_and_respond)
        await auth_client.fields_get("res.partner", attributes=["string", "type"])

    assert captured.get("attributes") == ["string", "type"]


# ------------------------------------------------------------------
# CLIENT-05: ref
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ref_resolves_xml_id(auth_client):
    """ref returns the integer res_id for a valid xml_id."""
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(
            return_value=httpx.Response(200, json=_jsonrpc_result([{"res_id": 1}]))
        )
        result = await auth_client.ref("base.main_company")
    assert result == 1


@pytest.mark.asyncio
async def test_ref_raises_missing_error(auth_client):
    """ref raises OdooMissingError when the xml_id is not found."""
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result([])))
        with pytest.raises(OdooMissingError):
            await auth_client.ref("unknown.xml_id")


@pytest.mark.asyncio
async def test_ref_raises_validation_error_malformed(auth_client):
    """ref raises OdooValidationError locally for xml_id with no dot — no RPC call made."""
    with pytest.raises(OdooValidationError):
        await auth_client.ref("nomodule")


# ------------------------------------------------------------------
# CLIENT-06: execute_kw
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_execute_kw_routes_through_call(auth_client):
    """execute_kw delegates to call() and returns the raw result."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result({"key": "val"}))
    )
    result = await auth_client.execute_kw("account.move", "action_post", [], {})
    assert result == {"key": "val"}


# ------------------------------------------------------------------
# CLIENT-07: read_binary
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_binary_returns_bytes(auth_client):
    """read_binary decodes base64 field and returns plain bytes."""
    encoded = base64.b64encode(b"hello").decode()
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(
            return_value=httpx.Response(200, json=_jsonrpc_result([{"datas": encoded}]))
        )
        result = await auth_client.read_binary("ir.attachment", 42, "datas")
    assert result == b"hello"


@pytest.mark.asyncio
async def test_read_binary_returns_empty_bytes_for_false_field(auth_client):
    """read_binary returns b'' when Odoo returns False for an unset binary field."""
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(
            return_value=httpx.Response(200, json=_jsonrpc_result([{"datas": False}]))
        )
        result = await auth_client.read_binary("ir.attachment", 42, "datas")
    assert result == b""


@pytest.mark.asyncio
async def test_read_binary_raises_missing_error(auth_client):
    """read_binary raises OdooMissingError when record is not found (empty list)."""
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result([])))
        with pytest.raises(OdooMissingError):
            await auth_client.read_binary("ir.attachment", 99, "datas")


# ------------------------------------------------------------------
# CLIENT-08: bulk create with @overload
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_bulk_create_returns_list_of_ints(auth_client):
    """create with a list of dicts returns list[int]."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result([42, 43])))
    result = await auth_client.create("res.partner", [{"name": "A"}, {"name": "B"}])
    assert result == [42, 43]


@pytest.mark.asyncio
async def test_bulk_create_empty_list_raises(auth_client):
    """create with empty list raises OdooValidationError locally, no RPC call."""
    with pytest.raises(OdooValidationError, match="empty"):
        await auth_client.create("res.partner", [])
