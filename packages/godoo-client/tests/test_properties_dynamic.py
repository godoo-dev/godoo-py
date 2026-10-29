"""Public dynamic-properties regressions through an authenticated transport seam."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import TYPE_CHECKING, Any

import pytest
from godoo.client import OdooClient, OdooClientConfig
from godoo.client.errors import (
    OdooAccessError,
    OdooAuthError,
    OdooMissingError,
    OdooNetworkError,
    OdooRpcError,
    OdooSafetyError,
)
from godoo.client.rpc.types import OdooSessionInfo
from godoo.client.safety import SafetyContext
from godoo.client.services.properties import (
    PropertyBatchCancelledError,
    PropertyDriftError,
    PropertyLookupError,
    PropertyScopeError,
    PropertyValueError,
    PropertyWriteUnknownError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

MODEL = "project.task"
PARENT = "project.project"
FIELD = "task_properties"
DEFINITION_FIELD = "task_properties_definition"
DEFINITIONS = [
    {"name": "x_priority", "string": "Priority", "type": "selection", "selection": [["p_hi", "High"], ["p_lo", "Low"]]},
    {"name": "x_estimate", "string": "Estimated effort", "type": "integer"},
    {"name": "x_text", "string": "Notes", "type": "char"},
    {"name": "x_flag", "string": "Approved", "type": "boolean"},
    {"name": "x_cost", "string": "Cost", "type": "float"},
    {"name": "x_date", "string": "Due", "type": "date"},
    {"name": "x_when", "string": "Scheduled", "type": "datetime"},
    {"name": "x_owner", "string": "Owner", "type": "many2one", "comodel": "res.partner"},
    {"name": "x_watchers", "string": "Watchers", "type": "many2many", "comodel": "res.partner"},
    {"name": "x_tags", "string": "Labels", "type": "tags", "tags": [["t_red", "Red", 1], ["t_blue", "Blue", 2]]},
    {"name": "x_section", "string": "Details", "type": "separator"},
]
VALUES = {
    "x_priority": "p_hi",
    "x_estimate": 8,
    "x_text": "Keep me",
    "x_flag": True,
    "x_cost": 2.5,
    "x_date": "2026-10-30",
    "x_when": "2026-10-30 09:30:00",
    "x_owner": [7, "Alice"],
    "x_watchers": [[7, "Alice"], [9, "Bob"]],
    "x_tags": ["t_red", "t_blue"],
}
WIRE = {**VALUES, "x_owner": 7, "x_watchers": [7, 9]}
ALIASES = {
    "priority": {"label": "Priority", "options": {"high": {"label": "High"}, "low": {"id": "p_lo"}}},
    "estimate": {"label": "Estimated effort"},
    "labels": {"id": "x_tags", "options": {"red": {"id": "t_red"}, "blue": {"label": "Blue"}}},
}


class Transport:
    """Small Odoo-shaped server: reads carry metadata; writes accept value dictionaries."""

    def __init__(self):
        self.session = None
        self.auth_count = 0
        self.calls: list[tuple[str, str, list[Any], dict[str, Any]]] = []
        self.metadata = {
            FIELD: {
                "type": "properties",
                "definition_record": "project_id",
                "definition_record_field": DEFINITION_FIELD,
            },
            "project_id": {"type": "many2one", "relation": PARENT},
        }
        self.definitions = deepcopy(DEFINITIONS)
        self.parents = {rid: 42 for rid in range(1, 9)}
        self.values: dict[int, dict[str, Any]] = {}
        self.raw: dict[int, Any] = {}
        self.omitted: set[int] = set()
        self.read_error: Exception | None = None
        self.responses: dict[int, Any] = {}
        self.write_hook: Callable[[int], Awaitable[Any]] | None = None

    async def authenticate(self, username, password):
        assert (username, password) == ("fixture", "fixture")
        self.auth_count += 1
        self.session = OdooSessionInfo(uid=7, session_id=f"fixture-{self.auth_count}", db="fixture")
        return self.session

    async def call(self, model, method, args, kwargs):
        assert self.session is not None
        self.calls.append(deepcopy((model, method, args, kwargs)))
        if method == "fields_get":
            assert args == []
            if model == MODEL:
                return deepcopy(self.metadata)
            assert model == PARENT
            return {DEFINITION_FIELD: {"type": "properties_definition"}}
        if method == "read" and model == PARENT:
            return [{"id": rid, DEFINITION_FIELD: deepcopy(self.definitions)} for rid in args[0]]
        if method == "read" and model == MODEL:
            if self.read_error is not None:
                raise self.read_error
            rows = []
            # Deliberately do not preserve request order: public code must restore it.
            for rid in sorted(args[0]):
                if rid in self.omitted:
                    continue
                values = {**deepcopy(VALUES), **deepcopy(self.values.get(rid, {}))}
                raw = [{**deepcopy(d), "value": values.get(d["name"])} for d in self.definitions]
                row = {
                    "id": rid,
                    "name": f"Task {rid}",
                    "project_id": [self.parents[rid], "Project"] if self.parents[rid] else False,
                    FIELD: deepcopy(self.raw.get(rid, raw)),
                }
                fields = kwargs.get("fields")
                rows.append(row if fields is None else {k: v for k, v in row.items() if k == "id" or k in fields})
            return rows
        assert (model, method) == (MODEL, "write"), (model, method)
        ids, values = args
        assert len(ids) == 1 and set(values) == {FIELD}
        assert isinstance(values[FIELD], dict), "Properties writes must be value-only dictionaries"
        if self.write_hook is not None:
            return await self.write_hook(ids[0])
        response = self.responses.get(ids[0], True)
        if isinstance(response, Exception):
            raise response
        return response

    def logout(self):
        self.session = None

    async def aclose(self):
        pass

    def matching(self, model, method):
        return [call for call in self.calls if call[:2] == (model, method)]

    @property
    def writes(self):
        return self.matching(MODEL, "write")


@pytest.fixture
async def api():
    transport = Transport()
    client = OdooClient(
        OdooClientConfig(
            url="http://unused.invalid",
            database="fixture",
            username="fixture",
            password="fixture",
            transport_factory=lambda config: transport,
        )
    )
    await client.authenticate()
    try:
        yield client, transport
    finally:
        await client.aclose()


async def definitions(client, **kwargs):
    return await client.properties.definitions(MODEL, field=FIELD, parent_id=42, **kwargs)


async def binding(client, spec=None):
    return (await definitions(client)).bind(ALIASES if spec is None else spec)


def assert_payload(transport, rid, changes):
    matching = [call for call in transport.writes if call[2][0] == [rid]]
    assert len(matching) == 1
    expected = {**deepcopy(WIRE), **changes}
    assert matching[0][2] == [[rid], {FIELD: expected}]
    actual = matching[0][2][1][FIELD]
    # Dict equality alone would accept False in place of an explicit integer zero.
    for name, value in expected.items():
        assert type(actual[name]) is type(value), name
        if isinstance(value, list):
            assert [type(item) for item in actual[name]] == [type(item) for item in value], name


@pytest.mark.parametrize("overrides", [False, True])
async def test_definitions_before_children_discover_metadata_and_explicit_routes(api, overrides):
    client, transport = api
    transport.parents.clear()
    kwargs = {}
    if overrides:
        transport.metadata[FIELD] = {"type": "properties"}
        kwargs = {"parent_field": "project_id", "definition_field": DEFINITION_FIELD}
    snapshot = await definitions(client, context={"lang": "en_US"}, **kwargs)
    assert (snapshot.parent_id, snapshot.parent_field, snapshot.definition_field) == (
        42,
        "project_id",
        DEFINITION_FIELD,
    )
    assert snapshot["x_owner"].comodel == "res.partner"
    assert snapshot["x_tags"].options["t_red"].color == 1
    assert snapshot.by_label("Priority").options.by_label("High").id == "p_hi"
    assert [(c[0], c[1]) for c in transport.calls] == [(MODEL, "fields_get"), (PARENT, "fields_get"), (PARENT, "read")]
    assert transport.calls[-1][2:] == ([[42]], {"fields": [DEFINITION_FIELD], "context": {"lang": "en_US"}})


@pytest.mark.parametrize("fault", ["missing_field", "wrong_type", "missing_route", "wrong_parent"])
async def test_bad_discovery_metadata_fails_before_child_or_write(api, fault):
    client, transport = api
    if fault == "missing_field":
        del transport.metadata[FIELD]
    elif fault == "wrong_type":
        transport.metadata[FIELD]["type"] = "json"
    elif fault == "missing_route":
        del transport.metadata[FIELD]["definition_record"]
    else:
        transport.metadata["project_id"]["type"] = "char"
    with pytest.raises(PropertyValueError):
        await definitions(client)
    assert len(transport.calls) == 1


@pytest.mark.parametrize("collection", ["properties", "options"])
async def test_label_lookup_is_exact_and_requires_unique_match(api, collection):
    client, transport = api
    if collection == "properties":
        transport.definitions.append({"name": "x_other", "string": "Priority", "type": "char"})
        entries = await definitions(client)
        duplicate, exact, technical = "Priority", "Notes", "x_text"
    else:
        transport.definitions[0]["selection"].append(["p_other", "High"])
        entries = (await definitions(client))["x_priority"].options
        duplicate, exact, technical = "High", "Low", "p_lo"
    assert entries.by_label(exact).id == technical
    assert entries[technical].label == exact
    for label in (duplicate, exact.lower(), "missing"):
        with pytest.raises(PropertyLookupError):
            entries.by_label(label)


@pytest.mark.parametrize("ids", [2, [3, 1, 2], []])
async def test_dynamic_read_scalar_list_order_fields_and_rpc_cost(api, ids):
    client, transport = api
    result = await client.properties.read(MODEL, ids, field=FIELD, fields=["name"])
    if ids == []:
        assert result == [] and transport.calls == []
        return
    records = [result] if isinstance(ids, int) else result
    assert [record.id for record in records] == ([ids] if isinstance(ids, int) else ids)
    for record in records:
        assert record.record["name"] == f"Task {record.id}"
        assert dict(record.properties) == WIRE
        assert record.property_definitions.by_label("Priority").id == "x_priority"
        with pytest.raises(AttributeError):
            _ = record.properties.priority
    assert len(transport.calls) == 4
    assert len(transport.matching(PARENT, "read")) == 1
    assert set(transport.matching(MODEL, "read")[0][3]["fields"]) == {"name", FIELD, "project_id"}


async def test_dynamic_read_discovers_each_parent_once(api):
    client, transport = api
    transport.parents[2] = 43
    result = await client.properties.read(MODEL, [3, 2, 1], field=FIELD)
    assert [record.property_definitions.parent_id for record in result] == [42, 43, 42]
    assert [call[2] for call in transport.matching(PARENT, "read")] == [[[42]], [[43]]]
    assert len(transport.calls) == 5


@pytest.mark.parametrize("fault", ["missing", "access", "no_parent"])
async def test_read_missing_inaccessible_and_parentless_records_are_explicit(api, fault):
    client, transport = api
    if fault == "missing":
        transport.omitted.add(2)
        error = OdooMissingError
    elif fault == "access":
        transport.read_error = OdooAccessError("read denied")
        error = OdooAccessError
    else:
        transport.parents[2] = 0
        error = PropertyScopeError
    with pytest.raises(error):
        await client.properties.read(MODEL, [1, 2], field=FIELD)
    assert transport.writes == []


async def test_alias_projection_keeps_technical_mapping_and_translates_patch(api):
    client, transport = api
    bound = await binding(client)
    task = await bound.read(1, fields=["name"])
    assert task.properties.priority == "high"
    assert task.properties.labels == ["red", "blue"]
    assert task.properties.estimate == 8
    assert task.properties["x_priority"] == "p_hi"
    assert task.properties["x_owner"] == 7
    assert "priority" not in task.properties and set(task.properties) == set(WIRE)
    with pytest.raises(KeyError):
        _ = task.properties["estimate"]
    transport.calls.clear()
    await bound.patch(1, {"priority": "low", "estimate": 0, "labels": ["blue"], "x_text": ""})
    assert_payload(transport, 1, {"x_priority": "p_lo", "x_estimate": 0, "x_tags": ["t_blue"], "x_text": ""})
    assert [(c[0], c[1]) for c in transport.calls] == [(PARENT, "read"), (MODEL, "read"), (MODEL, "write")]
    assert bound.inspect()["priority"]["options"] == {"high": "p_hi", "low": "p_lo"}
    inspection = bound.inspect()
    inspection["priority"]["options"].clear()
    assert bound.inspect()["priority"]["options"] == {"high": "p_hi", "low": "p_lo"}


@pytest.mark.parametrize("name,raw,alias", [("x_priority", "p_lo", "priority"), ("x_tags", ["t_blue"], "labels")])
async def test_subset_option_aliases_refuse_unmapped_reads_with_raw_ids(api, name, raw, alias):
    client, transport = api
    selected = "p_hi" if name == "x_priority" else "t_red"
    bound = await binding(client, {alias: {"id": name, "options": {"mapped": {"id": selected}}}})
    transport.values[1] = {name: raw}
    dynamic = await client.properties.read(MODEL, 1, field=FIELD)
    assert dynamic.properties[name] == raw
    with pytest.raises(PropertyValueError, match=r"p_lo|t_blue"):
        await bound.read(1)
    # Raw technical patches remain available even outside the selected option aliases.
    await bound.patch(1, {name: raw})
    assert_payload(transport, 1, {name: raw})


@pytest.mark.parametrize(
    "name,value,wire",
    [
        ("x_estimate", 0, 0),
        ("x_flag", False, False),
        ("x_text", "", ""),
        ("x_cost", 0.0, 0.0),
        ("x_watchers", [], []),
        ("x_tags", [], []),
        ("x_owner", 11, 11),
        ("x_watchers", [11, 12], [11, 12]),
        ("x_priority", None, False),
        ("x_estimate", None, False),
        ("x_flag", None, False),
        ("x_text", None, False),
        ("x_cost", None, False),
        ("x_date", None, False),
        ("x_when", None, False),
        ("x_owner", None, False),
        ("x_watchers", None, []),
        ("x_tags", None, []),
    ],
)
async def test_public_patch_clear_falsy_relations_and_untouched_values(api, name, value, wire):
    client, transport = api
    await client.properties.patch(MODEL, 1, field=FIELD, changes={name: value})
    assert_payload(transport, 1, {name: wire})
    assert len(transport.calls) == 5


@pytest.mark.parametrize(
    "values,expected",
    [
        (
            {name: False for name in VALUES},
            {name: [] if name in ("x_tags", "x_watchers") else False if name == "x_flag" else None for name in VALUES},
        ),
        (
            {"x_estimate": 0, "x_cost": 0.0, "x_text": "", "x_flag": False, "x_watchers": [], "x_tags": []},
            {**WIRE, "x_estimate": 0, "x_cost": 0.0, "x_text": "", "x_flag": False, "x_watchers": [], "x_tags": []},
        ),
    ],
)
async def test_read_normalizes_unset_and_preserves_explicit_falsy_values(api, values, expected):
    client, transport = api
    transport.values[1] = values
    task = await client.properties.read(MODEL, 1, field=FIELD)
    assert dict(task.properties) == expected
    assert {name: type(value) for name, value in task.properties.items()} == {
        name: type(value) for name, value in expected.items()
    }


@pytest.mark.parametrize("fault", ["duplicate", "missing", "unknown", "metadata", "relation", "untyped", "not_list"])
async def test_malformed_unbound_visible_values_refuse_merged_write(api, fault):
    client, transport = api
    bound = await binding(client, {"estimate": {"id": "x_estimate"}})
    raw = [{**deepcopy(d), "value": deepcopy(VALUES.get(d["name"]))} for d in DEFINITIONS]
    if fault == "duplicate":
        raw.append(deepcopy(raw[0]))
    elif fault == "missing":
        raw = [entry for entry in raw if entry["name"] != "x_owner"]
    elif fault == "unknown":
        raw.append({"name": "x_hidden", "type": "char", "value": "hidden"})
    elif fault == "metadata":
        raw[7]["comodel"] = "res.users"
    elif fault == "relation":
        raw[7]["value"] = ["not-an-id", "Alice"]
    elif fault == "untyped":
        del raw[7]["type"]
    else:
        raw = {"x_owner": 7}
    transport.raw[2] = raw
    with pytest.raises(PropertyValueError):
        await bound.patch_many([1, 2], {"estimate": 0})
    assert transport.writes == []
    assert len(transport.matching(MODEL, "read")) == 1


@pytest.mark.parametrize("kind", ["json", "html"])
async def test_unsupported_unbound_kind_is_inspectable_but_blocks_read_and_merge(api, kind):
    client, transport = api
    transport.definitions.append({"name": "x_unknown", "string": "Future", "type": kind})
    snapshot = await definitions(client)
    assert snapshot["x_unknown"].type == kind
    bound = snapshot.bind({"estimate": {"id": "x_estimate"}})
    with pytest.raises(PropertyValueError, match="Unsupported"):
        await bound.read(1)
    with pytest.raises(PropertyValueError, match="Unsupported"):
        await bound.patch(1, {"estimate": 0})
    assert transport.writes == []


@pytest.mark.parametrize(
    "spec,error",
    [
        ({"items": {"id": "x_estimate"}}, PropertyValueError),
        ({"x_estimate": {"id": "x_estimate"}}, PropertyValueError),
        ({"_private": {"id": "x_estimate"}}, PropertyValueError),
        ({"a": {"label": "Priority", "id": "x_priority"}}, PropertyValueError),
        ({"a": {"id": "missing"}}, PropertyLookupError),
        ({"a": {"id": "x_estimate"}, "b": {"id": "x_estimate"}}, PropertyValueError),
        ({"a": {"id": "x_estimate", "options": {}}}, PropertyValueError),
        ({"a": {"id": "x_priority", "options": {"one": {"id": "p_hi"}, "two": {"label": "High"}}}}, PropertyValueError),
        ({"a": {"id": "x_priority", "options": {"one": {"id": "missing"}}}}, PropertyLookupError),
    ],
)
async def test_bind_rejects_collisions_ambiguous_selectors_and_invalid_option_maps(api, spec, error):
    client, transport = api
    snapshot = await definitions(client)
    with pytest.raises(error):
        snapshot.bind(spec)
    assert len(transport.calls) == 3


async def test_renamed_property_and_option_labels_retain_technical_ids(api):
    client, transport = api
    bound = await binding(client)
    transport.definitions[0]["string"] = "Urgency"
    transport.definitions[0]["selection"][0][1] = "Critical"
    await bound.refresh()
    assert bound.property_definitions.by_label("Urgency").options.by_label("Critical").id == "p_hi"
    with pytest.raises(PropertyLookupError):
        bound.property_definitions.by_label("Priority")
    assert (await bound.read(1)).properties.priority == "high"
    await bound.patch(1, {"priority": "high"})
    assert_payload(transport, 1, {"x_priority": "p_hi"})


@pytest.mark.parametrize("fault", ["recreated", "kind", "comodel", "removed_option"])
async def test_drift_refresh_rolls_back_entire_snapshot_and_blocks_mutation(api, fault):
    client, transport = api
    bound = await binding(client, {**ALIASES, "owner": {"id": "x_owner"}})
    before = bound.property_definitions
    transport.definitions[1]["string"] = "New effort label"
    if fault == "recreated":
        transport.definitions[0]["name"] = "x_new_priority"
    elif fault == "kind":
        transport.definitions[1]["type"] = "float"
    elif fault == "comodel":
        transport.definitions[7]["comodel"] = "res.users"
    else:
        transport.definitions[0]["selection"].pop()
    with pytest.raises(PropertyDriftError):
        await bound.refresh()
    assert bound.property_definitions is before
    assert bound.property_definitions["x_estimate"].label == "Estimated effort"
    with pytest.raises(PropertyDriftError):
        await bound.patch(1, {"estimate": 0})
    assert transport.writes == []
    assert transport.matching(MODEL, "read") == []


@pytest.mark.parametrize("fault", ["moved", "missing", "invalid_last_patch"])
async def test_whole_batch_preflight_prevents_any_write(api, fault):
    client, transport = api
    bound = await binding(client)
    changes = {1: {"estimate": 0}, 2: {"priority": "low"}, 3: {"estimate": 4}}
    if fault == "moved":
        transport.parents[3] = 43
        error = PropertyScopeError
    elif fault == "missing":
        transport.omitted.add(3)
        error = OdooMissingError
    else:
        changes[3] = {"estimate": "invalid"}
        error = PropertyValueError
    with pytest.raises(error):
        await bound.patch_each(changes)
    assert transport.writes == []
    assert len(transport.matching(MODEL, "read")) == (0 if fault == "invalid_last_patch" else 1)


async def test_patch_many_and_each_execute_real_batches_with_sparse_changes(api):
    client, transport = api
    bound = await binding(client)
    transport.calls.clear()
    receipts = await bound.patch_many([3, 1, 2], {"estimate": 0}, concurrency=2)
    assert [(r.record_id, r.status, r.error) for r in receipts] == [
        (3, "acknowledged", None),
        (1, "acknowledged", None),
        (2, "acknowledged", None),
    ]
    assert len(transport.calls) == 5
    assert len(transport.matching(MODEL, "read")) == 1
    for rid in (3, 1, 2):
        assert_payload(transport, rid, {"x_estimate": 0})
    transport.calls.clear()
    receipts = await bound.patch_each({2: {"priority": None}, 1: {"labels": []}, 3: {}}, concurrency=2)
    assert [(r.record_id, r.status) for r in receipts] == [(2, "acknowledged"), (1, "acknowledged")]
    assert_payload(transport, 2, {"x_priority": False})
    assert_payload(transport, 1, {"x_tags": []})
    assert len(transport.calls) == 4


async def test_empty_changes_and_empty_batches_make_no_rpc_calls(api):
    client, transport = api
    bound = await binding(client)
    transport.calls.clear()
    await client.properties.patch(MODEL, 1, field=FIELD, changes={})
    await bound.patch(1, {})
    assert await bound.patch_many([1, 2], {}) == []
    assert await bound.patch_many([], {"estimate": 0}) == []
    assert await bound.patch_each({1: {}, 2: {}}) == []
    assert await bound.patch_each({}) == []
    assert transport.calls == []


async def test_batch_worker_pool_bounds_tasks_and_inflight_writes(api):
    client, transport = api
    bound = await binding(client)
    entered = asyncio.Event()
    release = asyncio.Event()
    active = peak = 0

    async def write(rid):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 2:
            entered.set()
        try:
            await release.wait()
            return True
        finally:
            active -= 1

    transport.write_hook = write
    previous_tasks = asyncio.all_tasks()
    job = asyncio.create_task(bound.patch_many(list(range(1, 9)), {"estimate": 0}, concurrency=2))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        # One batch task and two workers, rather than a task per record behind a semaphore.
        assert len(asyncio.all_tasks() - previous_tasks) == 3
        assert len(transport.writes) == 2
    finally:
        release.set()
        receipts = await asyncio.wait_for(job, 2)
    assert peak == 2 and active == 0
    assert len(receipts) == len(transport.writes) == 8
    assert all(receipt.status == "acknowledged" for receipt in receipts)


async def test_mixed_batch_acknowledged_failed_and_unknown_receipts_do_not_retry(api):
    client, transport = api
    bound = await binding(client)
    rejected = OdooRpcError("server rejected")
    dropped = OdooNetworkError("response lost")
    transport.responses = {1: True, 2: False, 3: rejected, 4: dropped, 5: {"unexpected": True}, 6: 1}
    receipts = await bound.patch_many([6, 1, 5, 2, 4, 3], {"estimate": 0}, concurrency=2)
    assert [(r.record_id, r.status) for r in receipts] == [
        (6, "unknown"),
        (1, "acknowledged"),
        (5, "unknown"),
        (2, "failed"),
        (4, "unknown"),
        (3, "failed"),
    ]
    indexed = {r.record_id: r for r in receipts}
    assert indexed[3].error is rejected
    assert indexed[1].error is None
    assert isinstance(indexed[2].error, OdooRpcError)
    for rid in (4, 5, 6):
        assert isinstance(indexed[rid].error, PropertyWriteUnknownError)
        assert indexed[rid].error.record_id == rid
    assert indexed[4].error.__cause__ is dropped
    assert len(transport.writes) == 6
    for rid in range(1, 7):
        assert_payload(transport, rid, {"x_estimate": 0})


@pytest.mark.parametrize("bound_api", [False, True])
@pytest.mark.parametrize(
    "response", [OdooNetworkError("timeout after dispatch"), RuntimeError("lost response"), None, 1]
)
async def test_single_write_unknown_is_distinct_and_never_retried(api, bound_api, response):
    client, transport = api
    transport.responses[1] = response
    if bound_api:
        bound = await binding(client)
        operation = bound.patch(1, {"estimate": 0})
    else:
        operation = client.properties.patch(MODEL, 1, field=FIELD, changes={"x_estimate": 0})
    with pytest.raises(PropertyWriteUnknownError) as caught:
        await operation
    assert caught.value.record_id == 1
    assert "retry" in str(caught.value)
    assert_payload(transport, 1, {"x_estimate": 0})


async def test_cancellation_retains_acknowledged_unknown_and_undispatched_ids(api):
    client, transport = api
    bound = await binding(client)
    second_started = asyncio.Event()
    release = asyncio.Event()

    async def write(rid):
        if rid == 1:
            return True
        second_started.set()
        await release.wait()
        return True

    transport.write_hook = write
    job = asyncio.create_task(bound.patch_many([1, 2, 3, 4], {"estimate": 0}, concurrency=1))
    try:
        await asyncio.wait_for(second_started.wait(), 2)
    finally:
        job.cancel()
    with pytest.raises(PropertyBatchCancelledError) as caught:
        await job
    assert [(r.record_id, r.status) for r in caught.value.receipts] == [(1, "acknowledged"), (2, "unknown")]
    assert isinstance(caught.value.receipts[1].error, PropertyWriteUnknownError)
    assert caught.value.undispatched_ids == [3, 4]
    assert [call[2][0] for call in transport.writes] == [[1], [2]]


async def test_binding_context_is_deep_snapshot_and_excludes_new_ambient_keys(api):
    client, transport = api
    nested = {"allowed": [1, 2]}
    explicit = {"lang": "en_US", "custom": {"nested": [3]}}
    with client.with_context(lang="es_ES", tenant=nested), client.with_context(tz="Europe/Madrid"):
        snapshot = await definitions(client, context=explicit)
    bound = snapshot.bind(ALIASES)
    expected = {"lang": "en_US", "tenant": {"allowed": [1, 2]}, "custom": {"nested": [3]}, "tz": "Europe/Madrid"}
    nested["allowed"].append(99)
    explicit["custom"]["nested"].append(99)
    exposed = snapshot.context
    exposed["tenant"]["allowed"].clear()
    transport.calls.clear()
    with client.with_context(lang="fr_FR", new_key="must not leak", tenant={"allowed": [88]}):
        await bound.read(1)
        await bound.patch(1, {"estimate": 0})
        await bound.refresh()
    assert len(transport.calls) == 5
    assert all(call[3]["context"] == expected for call in transport.calls)
    assert snapshot.context == expected
    # The fixed service scope must unwind after each call.
    with client.with_context(new_key="ordinary call"):
        await client.read(MODEL, 1, fields=["name"])
    assert transport.calls[-1][3]["context"] == {"new_key": "ordinary call"}


@pytest.mark.parametrize("change", ["reauth", "same_identity_new_object", "uid", "database", "session_id", "logout"])
async def test_binding_rejects_authentication_identity_changes_before_rpc(api, change):
    client, transport = api
    bound = await binding(client)
    if change == "reauth":
        await client.authenticate()
    elif change == "same_identity_new_object":
        transport.session = deepcopy(transport.session)
    elif change == "logout":
        client.logout()
    elif change == "uid":
        transport.session.uid += 1
    elif change == "database":
        transport.session.db = "another"
    else:
        transport.session.session_id = "another"
    transport.calls.clear()
    with pytest.raises(PropertyScopeError):
        await bound.read(1)
    with pytest.raises(PropertyScopeError):
        await bound.patch(1, {"estimate": 0})
    assert transport.calls == []


async def test_authentication_changed_during_safety_await_blocks_wire_dispatch(api):
    client, transport = api
    bound = await binding(client)
    confirming = asyncio.Event()
    release = asyncio.Event()

    async def confirm(op):
        assert (op.model, op.name, op.level) == (MODEL, "write", "WRITE")
        confirming.set()
        await release.wait()
        return True

    client.set_safety_context(SafetyContext(confirm=confirm))
    job = asyncio.create_task(bound.patch(1, {"estimate": 0}))
    try:
        await asyncio.wait_for(confirming.wait(), 2)
        await client.authenticate()
    finally:
        release.set()
    with pytest.raises((OdooAuthError, PropertyScopeError)):
        await asyncio.wait_for(job, 2)
    assert transport.writes == []


async def test_fixed_context_preserves_live_safety_guards(api):
    client, transport = api
    bound = await binding(client)
    operations = []

    async def deny(op):
        operations.append(op)
        return False

    client.set_safety_context(SafetyContext(confirm=deny))
    await bound.read(1)
    with pytest.raises(OdooSafetyError):
        await bound.patch(1, {"estimate": 0})
    assert [(op.model, op.name, op.level) for op in operations] == [(MODEL, "write", "WRITE")]
    assert transport.writes == []
    client.set_safety_context(None)
    await bound.patch(1, {"estimate": 0})
    assert_payload(transport, 1, {"x_estimate": 0})


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"estimate": 0, "x_estimate": 1}, PropertyValueError),
        ({"missing": 0}, PropertyLookupError),
        ({"priority": "p_hi"}, PropertyValueError),
        ({"labels": "red"}, PropertyValueError),
        ({"x_priority": "unknown-option"}, PropertyValueError),
        ({"x_estimate": True}, PropertyValueError),
        ({"x_owner": 0}, PropertyValueError),
        ({"x_owner": [7, "Alice"]}, PropertyValueError),
        ({"x_watchers": [[7, "Alice"]]}, PropertyValueError),
        ({"x_flag": 1}, PropertyValueError),
        ({"x_cost": float("nan")}, PropertyValueError),
        ({"x_date": "2026-02-30"}, PropertyValueError),
    ],
)
async def test_invalid_patch_values_and_alias_technical_duplicates_refuse_writes(api, changes, error):
    client, transport = api
    bound = await binding(client)
    transport.calls.clear()
    with pytest.raises(error):
        await bound.patch_each({1: {"estimate": 0}, 2: changes})
    assert [(call[0], call[1]) for call in transport.calls] == [(PARENT, "read")]


@pytest.mark.parametrize(
    "ids,concurrency",
    [([1, 1], 2), ([0], 2), ([True], 2), ([1], 0), ([1], -1), ([1], True), ([1], 1.5)],
)
async def test_invalid_batch_ids_and_concurrency_refuse_rpc_calls(api, ids, concurrency):
    client, transport = api
    bound = await binding(client)
    transport.calls.clear()
    with pytest.raises(PropertyValueError):
        await bound.patch_many(ids, {"estimate": 0}, concurrency=concurrency)
    assert transport.calls == []


@pytest.mark.parametrize("batch", [False, True])
async def test_legacy_public_helpers_strip_relational_displays_and_send_merged_dicts(api, batch):
    client, transport = api
    if batch:
        await client.properties.update_safely_batch(MODEL, [2, 1], FIELD, {"x_estimate": 0})
        assert len(transport.calls) == 3
        assert [call[2][0] for call in transport.writes] == [[2], [1]]
    else:
        await client.properties.update_safely(MODEL, 1, FIELD, {"x_estimate": 0})
        assert len(transport.calls) == 2
    for rid in [2, 1] if batch else [1]:
        assert_payload(transport, rid, {"x_estimate": 0})
    assert transport.matching(MODEL, "fields_get") == []
    assert transport.matching(PARENT, "read") == []


async def test_public_converter_requires_relational_metadata_and_normalizes_displays(api):
    client, _ = api
    raw = [{**deepcopy(d), "value": deepcopy(VALUES.get(d["name"]))} for d in DEFINITIONS]
    assert client.properties.properties_to_write_format(raw) == WIRE
    with pytest.raises(PropertyValueError):
        client.properties.properties_to_write_format([{"name": "x_owner", "value": [7, "Alice"]}])


@pytest.mark.parametrize("legacy", [False, True])
async def test_missing_value_entry_rejects_entire_batch(api, legacy):
    client, transport = api
    bound = await binding(client)
    raw = [{**deepcopy(d), "value": deepcopy(VALUES.get(d["name"]))} for d in DEFINITIONS]
    del next(entry for entry in raw if entry["name"] == "x_text")["value"]
    transport.raw[2] = raw
    with pytest.raises(PropertyValueError, match="Missing value"):
        if legacy:
            await client.properties.update_safely_batch(MODEL, [1, 2], FIELD, {"x_estimate": 0})
        else:
            await bound.patch_many([1, 2], {"estimate": 0})
    assert transport.writes == []


@pytest.mark.parametrize("raw", [{}, "", 0])
@pytest.mark.parametrize("batch", [False, True])
async def test_legacy_malformed_falsy_response_rejects_before_writes(api, raw, batch):
    client, transport = api
    transport.raw[2] = raw
    with pytest.raises(PropertyValueError):
        if batch:
            await client.properties.update_safely_batch(MODEL, [1, 2], FIELD, {"x_estimate": 0})
        else:
            await client.properties.update_safely(MODEL, 2, FIELD, {"x_estimate": 0})
    assert transport.writes == []


async def test_interleaved_writers_can_overwrite_an_untouched_value(api):
    """Characterize the documented non-atomic read/merge/write boundary."""
    client, transport = api
    bound = await binding(client)
    first_ready = asyncio.Event()
    second_written = asyncio.Event()
    stored = None

    async def write(rid):
        nonlocal stored
        payload = deepcopy(transport.writes[-1][2][1][FIELD])
        if payload["x_estimate"] == 0:
            first_ready.set()
            await second_written.wait()
        stored = payload
        if payload["x_text"] == "Concurrent edit":
            second_written.set()
        return True

    transport.write_hook = write
    first = asyncio.create_task(bound.patch(1, {"estimate": 0}))
    try:
        await asyncio.wait_for(first_ready.wait(), 2)
        await bound.patch(1, {"x_text": "Concurrent edit"})
        await asyncio.wait_for(first, 2)
    finally:
        if not first.done():
            first.cancel()
            await asyncio.gather(first, return_exceptions=True)
    assert stored == {**WIRE, "x_estimate": 0}
    assert len(transport.writes) == 2
