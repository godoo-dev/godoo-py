"""Tests for Introspector and IntrospectionCache."""

from __future__ import annotations

import httpx
import pytest
import respx
from godoo.client.client import OdooClient, OdooClientConfig
from godoo.client.errors import OdooMissingError, OdooValidationError
from godoo.introspection.introspector import IntrospectionCache, Introspector
from godoo.introspection.markers import FieldMeta
from godoo.introspection.types import FieldSchema, ModelSchema

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
# FieldMeta behavior tests
# ---------------------------------------------------------------------------


def test_field_meta_hashable():
    """FieldMeta(ttype="char") is hashable (frozen=True, all scalar fields)."""
    meta = FieldMeta(ttype="char")
    assert hash(meta) is not None


def test_field_meta_default_attrs():
    """FieldMeta has all expected attributes with correct defaults."""
    meta = FieldMeta(ttype="many2one")
    assert meta.ttype == "many2one"
    assert meta.field_description == ""
    assert meta.relation is None
    assert meta.relation_field is None
    assert meta.required is False
    assert meta.readonly is False
    assert meta.store is True
    assert meta.index is False
    assert meta.copy is True
    assert meta.translate is False
    assert meta.help == ""
    assert meta.compute is None
    assert meta.depends == ()
    assert meta.modules == ()
    assert meta.on_delete is None
    assert meta.size is None
    assert meta.digits is None
    assert meta.original_ttype is None
    assert meta.dynamic_selection is False


def test_model_schema_not_hashable():
    """ModelSchema is NOT hashable (has dict field)."""
    schema = ModelSchema(name="res.partner")
    with pytest.raises(TypeError):
        hash(schema)


# ---------------------------------------------------------------------------
# Introspector behavior tests
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_get_schemas_empty_raises(auth_client):
    """get_schemas([]) raises OdooValidationError without any RPC call."""
    introspector = Introspector(auth_client)
    with pytest.raises(OdooValidationError):
        await introspector.get_schemas([])


@respx.mock
@pytest.mark.asyncio
async def test_get_schema_missing_model_raises(auth_client):
    """Mock ir.model returning empty list — raises OdooMissingError."""
    # RPC 1: ir.model — empty result
    # RPC 2: ir.model.fields — empty result
    responses = iter(
        [
            _rpc_response([]),  # ir.model
            _rpc_response([]),  # ir.model.fields
        ]
    )
    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=responses)
    introspector = Introspector(auth_client)
    with pytest.raises(OdooMissingError):
        await introspector.get_schema("nonexistent")


@respx.mock
@pytest.mark.asyncio
async def test_get_schema_returns_model_schema(auth_client):
    """get_schema returns a ModelSchema with correct name and at least one FieldSchema."""
    # RPC 1: ir.model
    model_records = [{"id": 1, "name": "Partner", "model": "res.partner", "transient": False}]
    # RPC 2: ir.model.fields
    field_records = [
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
        }
    ]
    responses = iter(
        [
            _rpc_response(model_records),  # ir.model
            _rpc_response(field_records),  # ir.model.fields
        ]
    )
    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=responses)
    introspector = Introspector(auth_client)
    schema = await introspector.get_schema("res.partner")
    assert isinstance(schema, ModelSchema)
    assert schema.name == "res.partner"
    assert "name" in schema.fields
    assert isinstance(schema.fields["name"], FieldSchema)


@respx.mock
@pytest.mark.asyncio
async def test_get_schema_caches_result(auth_client):
    """Second get_schema call for same model does NOT issue another search_read."""
    model_records = [{"id": 1, "name": "Partner", "model": "res.partner", "transient": False}]
    field_records = [
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
        }
    ]
    responses = iter(
        [
            _rpc_response(model_records),
            _rpc_response(field_records),
        ]
    )
    route = respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=responses)
    introspector = Introspector(auth_client)
    schema1 = await introspector.get_schema("res.partner")
    schema2 = await introspector.get_schema("res.partner")
    # Both calls return same schema, but only 2 RPCs total (not 4)
    assert schema1 is schema2
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_schema_bypass_cache(auth_client):
    """get_schema with bypass_cache=True forces a fresh fetch."""
    model_records = [{"id": 1, "name": "Partner", "model": "res.partner", "transient": False}]
    field_records = [
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
        }
    ]
    # First call: 2 RPCs; second call (bypass): 2 more RPCs = 4 total
    responses = iter(
        [
            _rpc_response(model_records),
            _rpc_response(field_records),
            _rpc_response(model_records),
            _rpc_response(field_records),
        ]
    )
    route = respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=responses)
    introspector = Introspector(auth_client)
    await introspector.get_schema("res.partner")
    await introspector.get_schema("res.partner", bypass_cache=True)
    assert route.call_count == 4


@respx.mock
@pytest.mark.asyncio
async def test_get_schemas_batch_one_rpc(auth_client):
    """get_schemas for two models issues one batch RPC (not one per model)."""
    model_records = [
        {"id": 1, "name": "Partner", "model": "res.partner", "transient": False},
        {"id": 2, "name": "Users", "model": "res.users", "transient": False},
    ]
    field_records = [
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
            "model": "res.partner",
        },
        {
            "id": 20,
            "name": "login",
            "ttype": "char",
            "field_description": "Login",
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
            "model": "res.users",
        },
    ]
    responses = iter(
        [
            _rpc_response(model_records),
            _rpc_response(field_records),
        ]
    )
    route = respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=responses)
    introspector = Introspector(auth_client)
    result = await introspector.get_schemas(["res.partner", "res.users"])
    assert "res.partner" in result
    assert "res.users" in result
    # 2 RPCs total (ir.model + ir.model.fields), not 4 (2 per model)
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_selection_fields_populated(auth_client):
    """Selection field with selection_ids gets FieldSchema.selection populated."""
    model_records = [{"id": 1, "name": "Move", "model": "account.move", "transient": False}]
    field_records = [
        {
            "id": 11,
            "name": "state",
            "ttype": "selection",
            "field_description": "Status",
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
            "selection_ids": [100, 101],
            "model": "account.move",
        }
    ]
    sel_records = [
        {"field_id": [11, "state"], "value": "draft", "name": "Draft", "sequence": 1},
        {"field_id": [11, "state"], "value": "posted", "name": "Posted", "sequence": 2},
    ]
    responses = iter(
        [
            _rpc_response(model_records),
            _rpc_response(field_records),
            _rpc_response(sel_records),  # ir.model.fields.selection
        ]
    )
    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=responses)
    introspector = Introspector(auth_client)
    schema = await introspector.get_schema("account.move")
    assert schema.fields["state"].selection == [("draft", "Draft"), ("posted", "Posted")]


@respx.mock
@pytest.mark.asyncio
async def test_dynamic_selection_empty_list(auth_client):
    """Selection field whose selection_ids fetch returns no records → empty selection list."""
    model_records = [{"id": 1, "name": "Move", "model": "account.move", "transient": False}]
    field_records = [
        {
            "id": 11,
            "name": "state",
            "ttype": "selection",
            "field_description": "Status",
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
            "selection_ids": [100],
            "model": "account.move",
        }
    ]
    responses = iter(
        [
            _rpc_response(model_records),
            _rpc_response(field_records),
            _rpc_response([]),  # ir.model.fields.selection — empty (dynamic selection)
        ]
    )
    respx.post(f"{BASE_URL}/jsonrpc").mock(side_effect=responses)
    introspector = Introspector(auth_client)
    schema = await introspector.get_schema("account.move")
    assert schema.fields["state"].selection == []


# ---------------------------------------------------------------------------
# IntrospectionCache behavior tests
# ---------------------------------------------------------------------------


def test_introspection_cache_invalidate():
    """Set a schema in cache, call invalidate, verify get returns None."""
    cache = IntrospectionCache()
    schema = ModelSchema(name="res.partner")
    cache.set("res.partner", schema)
    assert cache.get("res.partner") is schema
    cache.invalidate("res.partner")
    assert cache.get("res.partner") is None
