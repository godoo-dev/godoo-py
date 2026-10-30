from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
import pytest_asyncio
from godoo.client import OdooMissingError
from godoo.client.services.properties import (
    PropertyDriftError,
    PropertyLookupError,
    PropertyScopeError,
    PropertyValueError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from godoo.client import OdooClient


MODEL = "project.task"
FIELD = "task_properties"
PARENT_MODEL = "project.project"
DEFINITION_FIELD = "task_properties_definition"
pytestmark = pytest.mark.integration


@dataclass
class PropertySandbox:
    client: OdooClient
    ids: dict[str, str]
    definitions: list[dict[str, Any]]
    projects: list[int] = field(default_factory=list)
    partners: list[int] = field(default_factory=list)
    tasks: list[int] = field(default_factory=list)

    @property
    def project_id(self) -> int:
        return self.projects[0]

    def initial_values(self) -> dict[str, Any]:
        return {
            self.ids["priority"]: self.ids["high"],
            self.ids["tags"]: [self.ids["red"], self.ids["blue"]],
            self.ids["estimate"]: 12,
            self.ids["ratio"]: 1.25,
            self.ids["active"]: True,
            self.ids["note"]: "Keep this note",
            self.ids["day"]: "2026-10-30",
            self.ids["moment"]: "2026-10-30T14:15:16",
            self.ids["owner"]: self.partners[0],
            self.ids["reviewers"]: list(self.partners),
        }

    async def create_task(self, *, project_id: int | None = None) -> int:
        task_id = await self.client.create(
            MODEL,
            {
                "name": f"Property contract {uuid4().hex}",
                "project_id": self.project_id if project_id is None else project_id,
                FIELD: self.initial_values(),
            },
        )
        self.tasks.append(task_id)
        return task_id

    async def raw(self, task_id: int) -> list[dict[str, Any]]:
        return (await self.client.read(MODEL, task_id, [FIELD]))[0][FIELD]

    async def parent_definitions(self, project_id: int | None = None) -> list[dict[str, Any]]:
        records = await self.client.read(
            PARENT_MODEL,
            self.project_id if project_id is None else project_id,
            [DEFINITION_FIELD],
        )
        return records[0][DEFINITION_FIELD]

    async def set_definitions(self, definitions: list[dict[str, Any]]) -> None:
        await self.client.write(PARENT_MODEL, self.project_id, {DEFINITION_FIELD: definitions})

    async def discover(self) -> Any:
        return await self.client.properties.definitions(
            MODEL, field=FIELD, parent_id=self.project_id, context={"lang": "en_US"}
        )

    async def binding(self) -> Any:
        definitions = await self.discover()
        return definitions.bind(
            {
                "priority": {
                    "label": "Priority",
                    "options": {"high": {"label": "High"}, "low": {"id": self.ids["low"]}},
                },
                "estimate": {"label": "Estimated effort"},
                "tags": {
                    "id": self.ids["tags"],
                    "options": {"red": {"label": "Red"}, "blue": {"id": self.ids["blue"]}},
                },
            }
        )


@pytest_asyncio.fixture
async def property_sandbox(client: OdooClient) -> AsyncIterator[PropertySandbox]:
    """Only create records in the existing owned disposable Odoo fixture."""
    ids = {
        name: uuid4().hex[:16]
        for name in (
            "priority",
            "tags",
            "estimate",
            "ratio",
            "active",
            "note",
            "day",
            "moment",
            "owner",
            "reviewers",
            "high",
            "low",
            "red",
            "blue",
        )
    }
    definitions: list[dict[str, Any]] = [
        {
            "name": ids["priority"],
            "string": "Priority",
            "type": "selection",
            "selection": [[ids["high"], "High"], [ids["low"], "Low"]],
        },
        {
            "name": ids["tags"],
            "string": "Labels",
            "type": "tags",
            "tags": [[ids["red"], "Red", 1], [ids["blue"], "Blue", 2]],
        },
        {"name": ids["estimate"], "string": "Estimated effort", "type": "integer"},
        {"name": ids["ratio"], "string": "Ratio", "type": "float"},
        {"name": ids["active"], "string": "Reviewed", "type": "boolean"},
        {"name": ids["note"], "string": "Note", "type": "char"},
        {"name": ids["day"], "string": "Due date", "type": "date"},
        {"name": ids["moment"], "string": "Appointment", "type": "datetime"},
        {"name": ids["owner"], "string": "Owner", "type": "many2one", "comodel": "res.partner"},
        {"name": ids["reviewers"], "string": "Reviewers", "type": "many2many", "comodel": "res.partner"},
    ]
    sandbox = PropertySandbox(client, ids, definitions)
    try:
        for name in ("Owner", "Reviewer"):
            sandbox.partners.append(await client.create("res.partner", {"name": f"{name} {uuid4().hex}"}))
        for name in ("Original", "Other"):
            sandbox.projects.append(
                await client.create(
                    PARENT_MODEL,
                    {"name": f"{name} property contract {uuid4().hex}", DEFINITION_FIELD: deepcopy(definitions)},
                )
            )
        yield sandbox
    finally:
        # Try every dependency level even if an earlier cleanup fails.
        try:
            if sandbox.tasks:
                await client.unlink(MODEL, sandbox.tasks)
        finally:
            try:
                if sandbox.projects:
                    await client.unlink(PARENT_MODEL, sandbox.projects)
            finally:
                if sandbox.partners:
                    await client.unlink("res.partner", sandbox.partners)


async def test_definitions_before_children_and_dynamic_reads(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    client, ids = sandbox.client, sandbox.ids
    assert await client.search(MODEL, [["project_id", "=", sandbox.project_id]]) == []
    definitions = await sandbox.discover()
    assert set(definitions) == {definition["name"] for definition in sandbox.definitions}
    priority = definitions.by_label("Priority")
    assert (priority.id, priority.label, priority.type) == (ids["priority"], "Priority", "selection")
    assert priority.options.by_label("High").id == ids["high"]
    assert definitions[ids["owner"]].comodel == "res.partner"
    assert definitions[ids["reviewers"]].type == "many2many"
    assert definitions[ids["tags"]].options.by_label("Red").id == ids["red"]
    explicit = await client.properties.definitions(
        MODEL,
        field=FIELD,
        parent_id=sandbox.project_id,
        parent_field="project_id",
        definition_field=DEFINITION_FIELD,
        context={"lang": "en_US"},
    )
    assert dict(explicit) == dict(definitions)

    task_id = await sandbox.create_task()
    task = await client.properties.read(MODEL, task_id, field=FIELD, fields=["name"])
    assert task.id == task_id
    assert task.record["name"].startswith("Property contract ")
    assert task.property_definitions.by_label("Priority").id == ids["priority"]
    assert dict(task.properties) == sandbox.initial_values()
    assert [record.id for record in await client.properties.read(MODEL, [task_id], field=FIELD)] == [task_id]

    binding = await sandbox.binding()
    bound = await binding.read(task_id)
    assert bound.properties.priority == "high"
    assert bound.properties.estimate == 12
    assert bound.properties.tags == ["red", "blue"]
    assert bound.properties[ids["priority"]] == ids["high"]
    assert bound.properties[ids["owner"]] == sandbox.partners[0]
    assert [record.id for record in await binding.read([task_id])] == [task_id]


async def test_sparse_single_patch_preserves_unbound_relations_and_definitions(
    property_sandbox: PropertySandbox,
) -> None:
    sandbox = property_sandbox
    client, ids = sandbox.client, sandbox.ids
    task_id = await sandbox.create_task()
    original_definitions = await sandbox.parent_definitions()
    raw = {prop["name"]: prop["value"] for prop in await sandbox.raw(task_id)}
    assert raw[ids["owner"]][0] == sandbox.partners[0]
    assert all(isinstance(pair[1], str) for pair in raw[ids["reviewers"]])
    await client.properties.patch(MODEL, task_id, field=FIELD, changes={ids["priority"]: ids["low"]})
    binding = await sandbox.binding()
    await binding.patch(task_id, {"estimate": 0, "tags": ["blue"]})
    task = await binding.read(task_id)
    expected = sandbox.initial_values() | {
        ids["priority"]: ids["low"],
        ids["estimate"]: 0,
        ids["tags"]: [ids["blue"]],
    }
    assert dict(task.properties) == expected
    assert task.properties.priority == "low"
    assert task.properties.tags == ["blue"]
    await client.properties.patch(
        MODEL,
        task_id,
        field=FIELD,
        changes={ids["owner"]: sandbox.partners[1], ids["reviewers"]: [sandbox.partners[1]]},
    )
    changed = await client.properties.read(MODEL, task_id, field=FIELD)
    expected.update({ids["owner"]: sandbox.partners[1], ids["reviewers"]: [sandbox.partners[1]]})
    assert dict(changed.properties) == expected
    assert await sandbox.parent_definitions() == original_definitions


async def test_scalar_zero_false_empty_and_type_aware_clear(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    client, ids = sandbox.client, sandbox.ids
    task_id = await sandbox.create_task()
    original_definitions = await sandbox.parent_definitions()
    explicit = {ids["estimate"]: 0, ids["ratio"]: 0.0, ids["active"]: False, ids["note"]: ""}
    await client.properties.patch(MODEL, task_id, field=FIELD, changes=explicit)
    task = await client.properties.read(MODEL, task_id, field=FIELD)
    assert task.properties[ids["estimate"]] == 0
    assert task.properties[ids["estimate"]] is not False
    assert task.properties[ids["ratio"]] == 0.0
    assert task.properties[ids["ratio"]] is not False
    assert task.properties[ids["active"]] is False
    # Observe server normalization separately from the public codec. The client
    # sends "" (covered by exact payload tests), but project.task readback is unset.
    raw_note = next(entry["value"] for entry in task.record[FIELD] if entry["name"] == ids["note"])
    assert raw_note is False
    assert task.properties[ids["note"]] is None
    # Compare a direct RPC dictionary write with the service path before treating
    # this collapse as Odoo behavior rather than a client serialization defect.
    direct_task_id = await sandbox.create_task()
    before = next(entry["value"] for entry in await sandbox.raw(direct_task_id) if entry["name"] == ids["note"])
    assert before == "Keep this note"
    direct = sandbox.initial_values() | explicit
    assert await client.write(MODEL, direct_task_id, {FIELD: direct}) is True
    raw_note = next(entry["value"] for entry in await sandbox.raw(direct_task_id) if entry["name"] == ids["note"])
    assert raw_note is False
    direct_task = await client.properties.read(MODEL, direct_task_id, field=FIELD)
    assert direct_task.properties[ids["note"]] is None
    for name in ("priority", "tags", "day", "moment", "owner", "reviewers"):
        assert task.properties[ids[name]] == sandbox.initial_values()[ids[name]]

    await client.properties.patch(
        MODEL,
        task_id,
        field=FIELD,
        changes={ids["reviewers"]: [], ids["tags"]: []},
    )
    task = await client.properties.read(MODEL, task_id, field=FIELD)
    assert task.properties[ids["reviewers"]] == []
    assert task.properties[ids["tags"]] == []
    assert task.properties[ids["owner"]] == sandbox.partners[0]

    await client.properties.patch(
        MODEL, task_id, field=FIELD, changes={technical_id: None for technical_id in sandbox.initial_values()}
    )
    task = await client.properties.read(MODEL, task_id, field=FIELD)
    # The public codec represents unset scalars as None; booleans and list kinds
    # have their own empty values, regardless of Odoo's stored False sentinel.
    assert dict(task.properties) == {
        ids["priority"]: None,
        ids["tags"]: [],
        ids["estimate"]: None,
        ids["ratio"]: None,
        ids["active"]: False,
        ids["note"]: None,
        ids["day"]: None,
        ids["moment"]: None,
        ids["owner"]: None,
        ids["reviewers"]: [],
    }
    assert await sandbox.parent_definitions() == original_definitions


async def test_actual_batches_and_all_record_preflight(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    ids = sandbox.ids
    task_a, task_b = await sandbox.create_task(), await sandbox.create_task()
    binding = await sandbox.binding()
    original_definitions = await sandbox.parent_definitions()
    receipts = await binding.patch_many([task_a, task_b], {"priority": "low"}, concurrency=2)
    assert {receipt.record_id for receipt in receipts} == {task_a, task_b}
    assert len(receipts) == 2
    assert all(receipt.status == "acknowledged" and receipt.error is None for receipt in receipts)
    records = {record.id: record for record in await binding.read([task_a, task_b])}
    assert all(record.properties.priority == "low" for record in records.values())

    receipts = await binding.patch_each(
        {task_a: {"estimate": 0, "tags": ["blue"]}, task_b: {"priority": None, "tags": []}},
        concurrency=2,
    )
    assert {receipt.record_id for receipt in receipts} == {task_a, task_b}
    assert len(receipts) == 2
    assert all(receipt.status == "acknowledged" and receipt.error is None for receipt in receipts)
    records = {record.id: record for record in await binding.read([task_a, task_b])}
    assert records[task_a].properties.estimate == 0
    assert records[task_a].properties.priority == "low"
    assert records[task_a].properties.tags == ["blue"]
    assert records[task_b].properties.estimate == 12
    assert records[task_b].properties.priority is None
    assert records[task_b].properties.tags == []
    for record in records.values():
        assert record.properties[ids["owner"]] == sandbox.partners[0]
        assert record.properties[ids["reviewers"]] == sandbox.partners
        assert record.properties[ids["note"]] == "Keep this note"

    receipts = await binding.patch_each(
        {
            task_a: {ids["owner"]: sandbox.partners[1], ids["reviewers"]: [sandbox.partners[1]]},
            task_b: {ids["owner"]: None, ids["reviewers"]: []},
        },
        concurrency=2,
    )
    assert len(receipts) == 2
    assert {receipt.record_id for receipt in receipts} == {task_a, task_b}
    assert all(receipt.status == "acknowledged" and receipt.error is None for receipt in receipts)
    records = {record.id: record for record in await binding.read([task_a, task_b])}
    assert records[task_a].properties[ids["owner"]] == sandbox.partners[1]
    assert records[task_a].properties[ids["reviewers"]] == [sandbox.partners[1]]
    assert records[task_b].properties[ids["owner"]] is None
    assert records[task_b].properties[ids["reviewers"]] == []
    assert records[task_a].properties.estimate == 0
    assert records[task_b].properties.estimate == 12

    before = [await sandbox.raw(task_id) for task_id in (task_a, task_b)]
    with pytest.raises(PropertyValueError):
        await binding.patch_each({task_a: {"estimate": 99}, task_b: {"estimate": "invalid integer"}})
    assert [await sandbox.raw(task_id) for task_id in (task_a, task_b)] == before
    assert await sandbox.parent_definitions() == original_definitions


async def test_legacy_converter_and_helpers_round_trip_real_relations(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    client, ids = sandbox.client, sandbox.ids
    task_a, task_b = await sandbox.create_task(), await sandbox.create_task()
    original_definitions = await sandbox.parent_definitions()
    raw = await sandbox.raw(task_a)
    snapshot = deepcopy(raw)
    payload = client.properties.properties_to_write_format(raw)
    assert raw == snapshot
    assert payload[ids["owner"]] == sandbox.partners[0]
    assert payload[ids["reviewers"]] == sandbox.partners
    assert all(not isinstance(value, dict) for value in payload.values())
    # Exercise the converter's dictionary-write consumer path, which does not
    # benefit from Odoo18's display-name removal for list-shaped writes.
    await client.write(MODEL, task_a, {FIELD: payload})
    assert dict((await client.properties.read(MODEL, task_a, field=FIELD)).properties) == sandbox.initial_values()
    await client.properties.update_safely(MODEL, task_a, FIELD, {ids["estimate"]: 0})
    await client.properties.update_safely_batch(MODEL, [task_a, task_b], FIELD, {ids["priority"]: ids["low"]})
    records = await client.properties.read(MODEL, [task_a, task_b], field=FIELD)
    assert {record.id for record in records} == {task_a, task_b}
    for record in records:
        expected = sandbox.initial_values() | {ids["priority"]: ids["low"]}
        if record.id == task_a:
            expected[ids["estimate"]] = 0
        assert dict(record.properties) == expected
    assert await sandbox.parent_definitions() == original_definitions


async def test_exact_labels_collisions_and_explicit_technical_selectors(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    ids = sandbox.ids
    duplicates = [uuid4().hex[:16], uuid4().hex[:16]]
    definitions = deepcopy(sandbox.definitions)
    definitions.extend({"name": name, "string": "Duplicate", "type": "char"} for name in duplicates)
    definitions[0]["selection"].extend([[uuid4().hex[:16], "Repeated"], [uuid4().hex[:16], "Repeated"]])
    await sandbox.set_definitions(definitions)
    discovered = await sandbox.discover()
    for label in ("priority", "Priority ", "Missing", "Duplicate"):
        with pytest.raises(PropertyLookupError):
            discovered.by_label(label)
    for label in ("high", "High ", "Missing", "Repeated"):
        with pytest.raises(PropertyLookupError):
            discovered[ids["priority"]].options.by_label(label)
    with pytest.raises(PropertyLookupError):
        discovered.bind({"duplicate": {"label": "Duplicate"}})
    for alias in ("items", ids["priority"]):
        with pytest.raises(PropertyValueError):
            discovered.bind({alias: {"id": ids["priority"]}})
    with pytest.raises(PropertyLookupError):
        discovered.bind({"priority": {"id": ids["priority"], "options": {"choice": {"label": "Repeated"}}}})
    binding = discovered.bind({"duplicate": {"id": duplicates[0]}})
    task_id = await sandbox.create_task()
    original_definitions = await sandbox.parent_definitions()
    await binding.patch(task_id, {"duplicate": "Only the selected technical ID"})
    task = await binding.read(task_id)
    assert task.properties.duplicate == "Only the selected technical ID"
    assert task.properties[duplicates[0]] == "Only the selected technical ID"
    assert task.properties[duplicates[1]] is None
    assert await sandbox.parent_definitions() == original_definitions


async def test_property_and_option_renames_keep_bound_technical_ids(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    ids = sandbox.ids
    task_id = await sandbox.create_task()
    binding = await sandbox.binding()
    changed = deepcopy(sandbox.definitions)
    changed[0]["string"] = "Renamed priority"
    changed[0]["selection"][0][1] = "Renamed high"
    await sandbox.set_definitions(changed)
    # Mutations must refresh automatically without resolving the old label again.
    await binding.patch(task_id, {"priority": "high", "estimate": 0})
    await binding.refresh()
    task = await binding.read(task_id)
    assert task.properties.priority == "high"
    assert task.properties[ids["priority"]] == ids["high"]
    priority = task.property_definitions.by_label("Renamed priority")
    assert priority.id == ids["priority"]
    assert priority.options.by_label("Renamed high").id == ids["high"]
    with pytest.raises(PropertyLookupError):
        task.property_definitions.by_label("Priority")
    assert await sandbox.parent_definitions() == changed


@pytest.mark.parametrize("drift", ["replacement", "type", "comodel", "removed_option"])
async def test_incompatible_live_definition_drift_prevents_writes(
    property_sandbox: PropertySandbox, drift: str
) -> None:
    sandbox = property_sandbox
    ids = sandbox.ids
    task_id = await sandbox.create_task()
    discovered = await sandbox.discover()
    binding = discovered.bind(
        {
            "priority": {"id": ids["priority"], "options": {"high": {"id": ids["high"]}}},
            "owner": {"id": ids["owner"]},
            "estimate": {"id": ids["estimate"]},
        }
    )
    changed = deepcopy(sandbox.definitions)
    if drift == "replacement":
        changed[0]["name"] = uuid4().hex[:16]
    elif drift == "type":
        changed[0] = {"name": ids["priority"], "string": "Priority", "type": "char"}
    elif drift == "comodel":
        owner = next(definition for definition in changed if definition["name"] == ids["owner"])
        owner["comodel"] = "res.users"
    else:
        changed[0]["selection"] = [[ids["low"], "Low"]]
    await sandbox.set_definitions(changed)
    before = await sandbox.raw(task_id)
    with pytest.raises(PropertyDriftError):
        await binding.patch(task_id, {"estimate": 99})
    assert await sandbox.raw(task_id) == before
    with pytest.raises(PropertyDriftError):
        await binding.refresh()
    assert await sandbox.parent_definitions() == changed


async def test_moved_and_missing_records_reject_whole_batch(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    client = sandbox.client
    task_a, task_b = await sandbox.create_task(), await sandbox.create_task()
    binding = await sandbox.binding()
    original_definitions = await sandbox.parent_definitions()
    await client.write(MODEL, task_b, {"project_id": sandbox.projects[1]})
    before = [await sandbox.raw(task_id) for task_id in (task_a, task_b)]
    with pytest.raises(PropertyScopeError):
        await binding.patch(task_b, {"estimate": 99})
    with pytest.raises(PropertyScopeError):
        await binding.patch_many([task_a, task_b], {"estimate": 99})
    assert [await sandbox.raw(task_id) for task_id in (task_a, task_b)] == before

    await client.unlink(MODEL, task_b)
    sandbox.tasks.remove(task_b)
    before_a = await sandbox.raw(task_a)
    with pytest.raises(OdooMissingError):
        await binding.patch_each({task_a: {"estimate": 99}, task_b: {"estimate": 99}})
    assert await sandbox.raw(task_a) == before_a
    assert await sandbox.parent_definitions() == original_definitions
    assert await sandbox.parent_definitions(sandbox.projects[1]) == original_definitions


async def test_unmapped_live_option_is_an_explicit_read_error(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    ids = sandbox.ids
    task_id = await sandbox.create_task()
    definitions = await sandbox.discover()
    binding = definitions.bind({"priority": {"id": ids["priority"], "options": {"high": {"id": ids["high"]}}}})
    await sandbox.client.properties.patch(MODEL, task_id, field=FIELD, changes={ids["priority"]: ids["low"]})
    with pytest.raises(PropertyValueError, match=ids["low"]):
        await binding.read(task_id)
    assert (await sandbox.client.properties.read(MODEL, task_id, field=FIELD)).properties[ids["priority"]] == ids["low"]


async def test_bound_create_single_and_batch_read_back_all_kinds(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    ids = sandbox.ids
    bound = await sandbox.binding()
    assert await sandbox.client.search(MODEL, [["project_id", "=", sandbox.project_id]]) == []
    properties = sandbox.initial_values()
    for name in ("priority", "tags", "estimate"):
        del properties[ids[name]]
    properties.update({"priority": "low", "tags": ["blue"], "estimate": 0})
    task_id = await bound.create({"name": "Created with aliases", FIELD: properties})
    sandbox.tasks.append(task_id)
    task = await bound.read(task_id)
    assert task.record["name"] == "Created with aliases"
    assert task.record["project_id"][0] == sandbox.project_id
    assert task.properties.priority == "low"
    assert task.properties.tags == ["blue"]
    assert dict(task.properties) == sandbox.initial_values() | {
        ids["priority"]: ids["low"],
        ids["tags"]: [ids["blue"]],
        ids["estimate"]: 0,
    }

    task_ids = await bound.create(
        [
            {
                "name": "Falsy values",
                FIELD: {
                    "priority": None,
                    "tags": [],
                    "estimate": 0,
                    ids["active"]: False,
                    ids["ratio"]: 0.0,
                    ids["note"]: "",
                    ids["owner"]: None,
                    ids["reviewers"]: [],
                    ids["day"]: None,
                    ids["moment"]: None,
                },
            },
            {"name": "Technical IDs", "project_id": sandbox.project_id, FIELD: sandbox.initial_values()},
        ]
    )
    sandbox.tasks.extend(task_ids)
    tasks = await bound.read(task_ids)
    assert [task.record["name"] for task in tasks] == ["Falsy values", "Technical IDs"]
    assert dict(tasks[0].properties) == {
        ids["priority"]: None,
        ids["tags"]: [],
        ids["estimate"]: 0,
        ids["active"]: False,
        ids["ratio"]: 0.0,
        ids["note"]: None,
        ids["owner"]: None,
        ids["reviewers"]: [],
        ids["day"]: None,
        ids["moment"]: None,
    }
    assert type(tasks[0].properties[ids["estimate"]]) is int
    assert tasks[0].properties[ids["active"]] is False
    assert dict(tasks[1].properties) == sandbox.initial_values()
    assert await sandbox.parent_definitions() == sandbox.definitions


async def test_bound_create_uses_server_defaults_and_captured_parent(property_sandbox: PropertySandbox) -> None:
    sandbox = property_sandbox
    ids = sandbox.ids
    definitions = deepcopy(sandbox.definitions)
    for definition in definitions:
        if definition["name"] == ids["priority"]:
            definition["default"] = ids["high"]
        elif definition["name"] == ids["estimate"]:
            definition["default"] = 7
    await sandbox.set_definitions(definitions)
    with sandbox.client.with_context(default_project_id=sandbox.projects[1]):
        snapshot = await sandbox.discover()
    bound = snapshot.bind({"priority": {"id": ids["priority"]}})
    task_ids = await bound.create(
        [
            {"name": "Omitted properties"},
            {"name": "Empty properties", FIELD: {}},
            {"name": "Sparse properties", FIELD: {"priority": ids["low"]}},
            {"name": "Explicit clears", FIELD: {"priority": None, ids["estimate"]: None}},
        ]
    )
    sandbox.tasks.extend(task_ids)
    tasks = await bound.read(task_ids)
    assert all(task.record["project_id"][0] == sandbox.project_id for task in tasks)
    assert [task.properties[ids["priority"]] for task in tasks] == [ids["high"], ids["high"], ids["low"], None]
    assert [task.properties[ids["estimate"]] for task in tasks] == [7, 7, 7, None]
    assert await sandbox.parent_definitions() == definitions


async def test_bound_create_preflights_batch_and_drift_without_creating_records(
    property_sandbox: PropertySandbox,
) -> None:
    sandbox = property_sandbox
    bound = await sandbox.binding()
    for invalid in ({"project_id": sandbox.projects[1]}, {FIELD: {"priority": "missing"}}):
        with pytest.raises((PropertyScopeError, PropertyValueError)):
            await bound.create([{"name": "Must not exist", FIELD: {"estimate": 0}}, invalid])
        assert await sandbox.client.search(MODEL, [["project_id", "=", sandbox.project_id]]) == []
    changed = deepcopy(sandbox.definitions)
    changed[0]["selection"] = [[sandbox.ids["low"], "Low"]]
    await sandbox.set_definitions(changed)
    with pytest.raises(PropertyDriftError):
        await bound.create({"name": "Must not exist", FIELD: {"estimate": 0}})
    assert await sandbox.client.search(MODEL, [["project_id", "=", sandbox.project_id]]) == []
    assert await sandbox.parent_definitions() == changed
