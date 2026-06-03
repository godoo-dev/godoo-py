"""Typed create/write dispatch tests (WRITE-01..05 + TEST-01 unit + integration)."""

from __future__ import annotations

import json
from datetime import date, datetime
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
from pydantic import Field

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


class WritePartner(OdooBaseModel):
    """Minimal model with metadata-bearing fields for write tests."""

    __odoo_model__: ClassVar[str] = "res.partner"
    id: int
    name: str | None = None
    comment: str | None = None
    state: str | None = Field(default=None, json_schema_extra={"odoo_readonly": True})
    line_ids: list[int] = Field(default_factory=list, json_schema_extra={"odoo_x2many": True})


class WriteDates(OdooBaseModel):
    """Minimal model with date/datetime/Ref fields for transform tests."""

    __odoo_model__: ClassVar[str] = "x.event"
    id: int
    close_date: date | None = None
    event_at: datetime | None = None
    partner_id: Ref[WritePartner] | None = None


class NullableIdPartner(OdooBaseModel):
    """Model with nullable id — for testing the id=None guard."""

    __odoo_model__: ClassVar[str] = "res.partner"
    id: int | None = None
    name: str | None = None


# ------------------------------------------------------------------
# Payload inspection helper
# ------------------------------------------------------------------


def _extract_rpc_write_payload(request: httpx.Request) -> dict[str, object] | None:
    """Extract the values dict from a JSON-RPC write/create call body.

    execute_kw args structure: [db, uid, password, model, method, positional_args, kwargs]
    For write:  positional_args = [[record_ids], payload_dict]  → return payload_dict
    For create: positional_args = [payload_dict]                → return payload_dict
    In both cases the payload dict is the last element of positional_args.
    """
    body = json.loads(request.content)
    rpc_args: list[object] = body.get("params", {}).get("args", [])
    # execute_kw args: [db, uid, password, model, method, positional_args, kwargs]
    if len(rpc_args) >= 6:
        pos_args = rpc_args[5]
        if isinstance(pos_args, list) and pos_args:
            last = pos_args[-1]
            if isinstance(last, dict):
                return last  # type: ignore[return-value]
    return None


# ------------------------------------------------------------------
# WRITE-02: only model_fields_set fields appear in the payload
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_write_sends_only_set_fields(auth_client: OdooClient) -> None:
    """WRITE-02: only model_fields_set fields are sent; unset fields are absent."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    instance = WritePartner(id=1, name="Updated")  # only id + name in model_fields_set
    await auth_client.write(instance)
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    # 'comment' was not set; 'state'/'line_ids' carry metadata — excluded by guards
    assert set(payload.keys()) == {"name"}


# ------------------------------------------------------------------
# WRITE-04: readonly fields excluded even when explicitly set
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_write_excludes_readonly_field_even_when_set(auth_client: OdooClient) -> None:
    """WRITE-04: odoo_readonly=True field is excluded from the payload even when explicitly set."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    instance = WritePartner(id=1, name="X", state="draft")  # 'state' is odoo_readonly
    await auth_client.write(instance)
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    assert "state" not in payload
    assert payload == {"name": "X"}


# ------------------------------------------------------------------
# WRITE-03: None → False (Odoo wire convention for cleared fields)
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_write_none_becomes_false(auth_client: OdooClient) -> None:
    """WRITE-03: explicitly set None field serialises to False on the wire."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    instance = WritePartner(id=1, name=None)
    await auth_client.write(instance)
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    assert payload == {"name": False}


# ------------------------------------------------------------------
# WRITE-01: Ref → int (bare id)
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_write_ref_becomes_int(auth_client: OdooClient) -> None:
    """WRITE-01: Ref[T] field serialises to the bare integer id."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    instance = WriteDates(id=1, partner_id=Ref(id=42, name="Foo"))
    await auth_client.write(instance)
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    assert payload == {"partner_id": 42}


# ------------------------------------------------------------------
# WRITE-01: date → ISO string
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_write_date_becomes_iso_string(auth_client: OdooClient) -> None:
    """WRITE-01: date field serialises to ISO date string."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    instance = WriteDates(id=1, close_date=date(2024, 3, 15))
    await auth_client.write(instance)
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    assert payload == {"close_date": "2024-03-15"}


# ------------------------------------------------------------------
# WRITE-01: datetime → ISO string
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_write_datetime_becomes_iso_string(auth_client: OdooClient) -> None:
    """WRITE-01: datetime field serialises to ISO datetime string."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    instance = WriteDates(id=1, event_at=datetime(2024, 3, 15, 10, 30))
    await auth_client.write(instance)
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    assert payload == {"event_at": "2024-03-15T10:30:00"}


# ------------------------------------------------------------------
# WRITE-05: explicit post-init x2many mutation raises OdooValidationError before RPC (CR-01)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_typed_write_x2many_raises(auth_client: OdooClient) -> None:
    """WRITE-05 / CR-01 contract (c): explicit post-init x2many assignment raises before any RPC."""
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
        instance = WritePartner(id=1)
        instance.line_ids = [1, 2]  # explicit post-init mutation — contract (c)
        with pytest.raises(OdooValidationError, match="x2many"):
            await auth_client.write(instance)
        # No RPC beyond the auth call — the serializer raises before network
        assert len(respx.calls) == 0


# ------------------------------------------------------------------
# write() guard: id=None raises OdooValidationError before RPC
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_typed_write_id_none_raises(auth_client: OdooClient) -> None:
    """write(instance) with instance.id=None raises OdooValidationError before any RPC."""
    with respx.mock:
        respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
        instance = NullableIdPartner(name="No ID Yet")  # id defaults to None
        with pytest.raises(OdooValidationError, match="id is None"):
            await auth_client.write(instance)
        assert len(respx.calls) == 0


# ------------------------------------------------------------------
# create(instance) — typed path
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_typed_create_returns_new_id(auth_client: OdooClient) -> None:
    """create(instance) sends correct payload and returns the new record id."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(42)))
    # NullableIdPartner has id: int | None = None so id is not in model_fields_set when omitted
    instance = NullableIdPartner(name="New Partner")
    result = await auth_client.create(instance)
    assert result == 42
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    assert payload == {"name": "New Partner"}
    # id was not in model_fields_set, so it must not appear in the payload
    assert "id" not in payload


class WritePartnerWithReadonly(OdooBaseModel):
    """WritePartner variant where id is optional — for create-path readonly test."""

    __odoo_model__: ClassVar[str] = "res.partner"
    id: int | None = None
    name: str | None = None
    state: str | None = Field(default=None, json_schema_extra={"odoo_readonly": True})


@respx.mock
@pytest.mark.asyncio
async def test_typed_create_excludes_readonly(auth_client: OdooClient) -> None:
    """create(instance) excludes odoo_readonly fields from the payload."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(99)))
    instance = WritePartnerWithReadonly(name="New", state="draft")  # state is odoo_readonly
    await auth_client.create(instance)
    payload = _extract_rpc_write_payload(respx.calls[0].request)
    assert payload is not None
    assert "state" not in payload
    assert payload == {"name": "New"}


# ------------------------------------------------------------------
# Regression guard: dict-based paths still work
# ------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_dict_create_still_works(auth_client: OdooClient) -> None:
    """Dict path create('model', {...}) still returns an int id (TYPED-04 regression)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(7)))
    result = await auth_client.create("res.partner", {"name": "X"})
    assert isinstance(result, int)
    assert result == 7


@respx.mock
@pytest.mark.asyncio
async def test_dict_write_still_works(auth_client: OdooClient) -> None:
    """Dict path write('model', id, {...}) still returns True (TYPED-04 regression)."""
    respx.post(f"{BASE_URL}/jsonrpc").mock(return_value=httpx.Response(200, json=_jsonrpc_result(True)))
    result = await auth_client.write("res.partner", 1, {"name": "X"})
    assert result is True


# ------------------------------------------------------------------
# CR-01 / CR-02: contracts exercised against a real codegen-generated class (exec)
# ------------------------------------------------------------------


def _make_codegen_class(extra_fields: dict[str, object] | None = None) -> type:
    """Generate and exec a ResPartner-like class via CodeGenerator.

    Returns the generated class object. Uses a minimal schema so the test does not
    depend on a live Odoo instance. The exec is acceptable because the source is our
    own trusted codegen output.

    model_rebuild(_types_namespace=ns) is called after exec so that pydantic can
    resolve deferred annotations introduced by ``from __future__ import annotations``
    in the generated source. The ``ns`` dict carries all the names the generated
    module imported (Optional, ClassVar, OdooBaseModel, Field, …) so the rebuild
    finds everything it needs.
    """
    from godoo.introspection.codegen import CodeGenerator
    from godoo.introspection.types import FieldSchema, ModelSchema

    fields: dict[str, FieldSchema] = {
        "name": FieldSchema(name="name", ttype="char"),
        "line_ids": FieldSchema(name="line_ids", ttype="one2many"),
    }
    if extra_fields:
        fields.update(extra_fields)  # type: ignore[arg-type]
    schema = ModelSchema(name="res.partner", fields=fields)
    gen = CodeGenerator(None)  # type: ignore[arg-type]
    source = gen.generate(schema)
    ns: dict[str, object] = {}
    exec(source, ns)  # trusted codegen output
    cls: type = ns["ResPartner"]  # type: ignore[assignment]
    cls.model_rebuild(_types_namespace=ns)  # type: ignore[attr-defined]
    return cls


def test_cr02_generated_class_create_without_id() -> None:
    """CR-02 contract (a): generated class can be instantiated without id for create().

    id: int | None = None means ResPartner(name='X') works without a bogus id.
    """
    ResPartner = _make_codegen_class()
    instance = ResPartner(name="Acme Corp")  # type: ignore[call-arg]
    assert instance.id is None  # type: ignore[attr-defined]
    assert instance.name == "Acme Corp"  # type: ignore[attr-defined]


def test_cr02_generated_class_id_not_in_payload() -> None:
    """CR-02: id is excluded from the serialized payload even when set.

    _serialize_for_write always drops id (it's sent as a separate RPC arg).
    """
    from godoo.client._pydantic_transform import _serialize_for_write

    ResPartner = _make_codegen_class()
    instance = ResPartner(name="Acme Corp")  # type: ignore[call-arg]
    payload = _serialize_for_write(instance)
    assert "id" not in payload
    assert payload == {"name": "Acme Corp"}


def test_cr01_generated_class_read_then_modify_scalar_does_not_raise() -> None:
    """CR-01 contract (b): generated class read → modify scalar → serialize MUST NOT raise.

    Simulates client.search_read returning a dict with x2many fields. Modifying one
    scalar field and serializing must succeed even though line_ids is in model_fields_set.
    """
    from godoo.client._pydantic_transform import _serialize_for_write

    ResPartner = _make_codegen_class()
    # Simulate what model_validate receives from the Odoo JSON-RPC response
    instance = ResPartner.model_validate({"id": 42, "name": "Original", "line_ids": [1, 2, 3]})  # type: ignore[call-arg]
    # User modifies only a scalar — the canonical roundtrip case
    instance.name = "Updated"  # type: ignore[attr-defined]

    # Must not raise — contract (b)
    payload = _serialize_for_write(instance)
    assert payload == {"name": "Updated"}
    assert "line_ids" not in payload


def test_cr01_generated_class_explicit_x2many_mutation_raises() -> None:
    """CR-01 contract (c): explicit post-init x2many assignment on generated class raises.

    The user explicitly sets an x2many field and calls write — must raise
    OdooValidationError with a clear message.
    """
    from godoo.client._pydantic_transform import _serialize_for_write

    ResPartner = _make_codegen_class()
    instance = ResPartner(id=42, name="Acme")  # type: ignore[call-arg]
    instance.line_ids = [5, 6, 7]  # type: ignore[attr-defined]  # explicit mutation — contract (c)

    with pytest.raises(OdooValidationError, match="x2many"):
        _serialize_for_write(instance)


# ------------------------------------------------------------------
# TEST-01 integration: codegen → read → write round-trip (closes 999.3)
# ------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_codegen_read_write_roundtrip() -> None:
    """TEST-01 integration: generate class → read record → modify → write → assert (closes 999.3).

    Steps:
    1. Spin up a live Odoo instance via TestHarness (modules=["base"], snapshot=False).
    2. Use Introspector to fetch the schema for "res.lang" (a stable base-module model).
    3. Use CodeGenerator to emit a Python module string.
    4. exec() the source into a temporary namespace to obtain the generated class.
       (exec is used instead of importlib because the generated source is an in-memory
       string and writing to a tempfile would require a cleanup fixture; exec() is safe
       here because the source is produced by our own codegen and trusted.)
    5. call client.search_read(GeneratedClass, [("active", "in", [True, False])], limit=1)
       to fetch one res.lang record.
    6. Modify the 'name' field to a new value on the instance.
    7. call client.write(instance) — assert returns True.
    8. Read the record back and assert the name was updated.
    9. Restore the original name so the container is left in a clean state.
    """
    from godoo.introspection.codegen import CodeGenerator
    from godoo.introspection.introspector import Introspector
    from godoo.testcontainers import TestHarness  # local: integration-only dependency

    async with TestHarness(modules=["base"], snapshot=False) as h:
        client = h.client

        # Step 1: Introspect res.lang schema
        introspector = Introspector(client)
        schema = await introspector.get_schema("res.lang")

        # Step 2: Generate the Python module source string
        gen = CodeGenerator(introspector, in_set=frozenset({"res.lang"}))
        source = gen.generate(schema)

        # Step 3: exec() the source to get the generated class.
        # The source is trusted (our own codegen output), so exec() is acceptable here.
        # model_rebuild is required because generated source uses `from __future__ import
        # annotations` (deferred evaluation); the rebuild resolves annotations using the
        # names that the generated module imported (carried in ns).
        ns: dict[str, object] = {}
        exec(source, ns)
        ResLang: type = ns["ResLang"]  # type: ignore[assignment]
        ResLang.model_rebuild(_types_namespace=ns)  # type: ignore[attr-defined]

        # Step 4: Read one record using the generated typed class
        records = await client.search_read(ResLang, [("active", "in", [True, False])], limit=1)
        assert records, "Expected at least one res.lang record in a base Odoo install"
        instance = records[0]
        assert hasattr(instance, "__odoo_model__"), "Generated class must be an OdooBaseModel subclass"
        assert instance.__odoo_model__ == "res.lang"  # type: ignore[attr-defined]

        original_name: str | None = instance.name  # type: ignore[attr-defined]
        assert original_name is not None, "res.lang record should have a name"

        # Step 5: Modify a writable field and write back
        modified_name = f"{original_name}_test_roundtrip"
        instance.name = modified_name  # type: ignore[attr-defined]

        write_result = await client.write(instance)
        assert write_result is True, "write() should return True on success"

        # Step 6: Read back and confirm the change was persisted
        refreshed = await client.search_read(
            ResLang,
            [("id", "=", instance.id)],  # type: ignore[attr-defined]
            limit=1,
        )
        assert refreshed, "Record should still exist after write"
        assert refreshed[0].name == modified_name  # type: ignore[attr-defined]

        # Step 7: Restore original value to leave container clean
        refreshed[0].name = original_name  # type: ignore[attr-defined]
        await client.write(refreshed[0])
