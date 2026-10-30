# Properties Service

Access Odoo's runtime-defined properties through `client.properties`. Applications
do not need a Python schema or Pydantic. These additions are implemented in source
for [issue #9](https://github.com/godoo-dev/godoo-py/issues/9); this guide does not
establish registry publication.

## Read properties and definitions

Use an authenticated client and an existing task ID:

```python
task = await client.properties.read(
    "project.task", task_id,
    field="task_properties", fields=["name"],
)
task.id
task.record["name"]
priority = task.property_definitions.by_label("Priority")
high = priority.options.by_label("High")
current_priority = task.properties[priority.id]

await client.properties.patch(
    "project.task", task_id,
    field="task_properties", changes={priority.id: high.id},
)
```

`task.properties` is a mapping keyed by technical property IDs. Definitions expose
`id`, `label`, `type`, `comodel` and an options mapping. `by_label()` requires an
exact, unique match and raises `PropertyLookupError` for missing or ambiguous labels.
A single ID returns one `PropertyRecord`; an ID list returns a list in caller order.
Ordinary fields are in `task.record`; property and parent fields are fetched even
when `fields` restricts ordinary fields. Returned values are detached snapshots;
change server values through a patch.

Definitions can be discovered before a task exists:

```python
property_definitions = await client.properties.definitions(
    "project.task", field="task_properties",
    parent_id=project_id, context={"lang": "en_US"},
)
```

Discovery uses field metadata to find the parent relation and definition field.
Custom models can supply `parent_field=` and `definition_field=` overrides; those
fields undergo the same validation. Parent reads use normal access rights, so
access failures propagate even if Odoo exposes properties on readable children.
An unset or inaccessible parent is an error; an explicitly empty definition list
on a readable parent is valid.

## Optional aliases

Bind names to runtime definitions when an application benefits from stable aliases:

```python
property_binding = property_definitions.bind({
    "priority": {
        "label": "Priority",
        "options": {"high": {"label": "High"}, "low": {"label": "Low"}},
    },
    "estimate": {"label": "Estimated effort"},
})
task = await property_binding.read(task_id)
current_priority = task.properties.priority
await property_binding.patch(task.id, {"priority": "high", "estimate": 0})
await property_binding.patch(task.id, {"priority": None})
```

Selectors contain exactly one of `label` or `id`, for example
`{"id": "technical_id"}`. Labels resolve once. Mapping access always uses technical
IDs and returns technical values; attribute access uses aliases and translates
mapped selection/tag options. Aliases provide dynamic access without inferred
static property types. They must be public Python identifiers and cannot collide
with mapping methods or technical IDs. Multiple aliases for the same target and
patches selecting one property through both an alias and its ID are rejected.

Option mappings may be partial. An aliased read encountering an unmapped selected
option raises `PropertyValueError` containing its technical ID. A patch to another
property still preserves valid unmapped technical values.

Bindings retain technical IDs across label renames. `await property_binding.refresh()`
validates a new snapshot before replacing the old one. Removed bound IDs,
incompatible kind/comodel changes and removed mapped options raise
`PropertyDriftError`; refresh never rebinds by label. Additions, reordering, renames
and changes to unmapped options are permitted. Recreating an identical ID with
compatible metadata cannot be distinguished without a server generation marker.
Existing read results retain their own definition snapshot.

A binding captures the client authentication session, parent and a deep copy of
the effective context. Later ambient context changes do not enter its calls.
Reauthentication requires fresh discovery. Calls retain the client's current
safety guards, including checks immediately before transport dispatch.

## Create records with properties

Discover definitions and bind aliases before creating a child. Pass ordinary record
values and a property mapping under the discovered properties field:

```python
task_id = await property_binding.create({
    "name": "Plan the release",
    "task_properties": {"priority": "high", "estimate": 0},
})
task_ids = await property_binding.create([
    {"name": "First task", "task_properties": {"priority": "low"}},
    {"name": "Second task", "task_properties": {"priority": None}},
])
task = await property_binding.read(task_id)
```

`create()` returns an ID for one mapping and an ID list for a nonempty list of
mappings, following `client.create()`. It supplies the binding's parent relation
when omitted; an explicit parent must be the same positive integer ID. This
overrides any parent default in the captured context. Other ordinary fields pass
through unchanged. Property keys accept aliases or technical IDs using the same
option and value rules as patches, including duplicate-target rejection.

Omitting the properties field leaves its defaults to Odoo. A supplied mapping is
sparse: only supplied keys are encoded, and omitted property defaults remain
server-owned. `None` explicitly clears a supplied property. An empty mapping is
valid; a non-mapping properties value is rejected.

Definitions refresh by default, with the same drift checks as patches;
`refresh=False` uses the retained snapshot. All input mappings are copied before
the first await, and the whole batch is validated before a single `create` RPC.
Creation retains the captured context/authentication and current safety guards.
The server may still reject ordinary fields or change definitions after preflight.

Creation uses the ordinary create response and exception contract, without patch
receipts or automatic retries. An ID response is acknowledgment, not readback
verification. After a transport error or cancellation, reconcile server state
before retrying to avoid duplicate records. Typed instances remain supported by
`client.create()` with their existing serialization; they are not accepted by
`PropertyBinding.create()`. Use `property_definitions.bind({})` for definition-aware
creation using technical IDs only.

## Patch values

An omitted key leaves the property untouched. `None` requests clearing. Explicit
zero, `False`, empty strings and empty lists are preserved for their valid kinds;
`False` is a boolean patch value, while other scalar kinds use `None` to clear.
Odoo18 `project.task` reads an explicitly written empty char as unset (`None`
in this API); preserving the outgoing empty string does not promise a distinct
stored/readback state. Tags and many2many use whole-list replacement; Odoo relation-command arrays are
not accepted.

| Odoo kind | Read value | Patch value | Read after clearing |
| --- | --- | --- | --- |
| boolean | `bool` | `bool` or `None` | `False` |
| integer | `int` or `None` | `int` or `None` | `None` |
| float | finite number or `None` | finite `int`/`float` or `None` | `None` |
| char | `str` or `None` | `str` or `None` | `None` |
| date / datetime | ISO string or `None` | ISO string or `None` | `None` |
| many2one | positive record ID or `None` | positive record ID or `None` | `None` |
| many2many | list of record IDs | ID list or `None` | `[]` |
| selection | option ID or `None` | option ID, mapped alias, or `None` | `None` |
| tags | list of option IDs | option ID/alias list or `None` | `[]` |

Relational display pairs from reads are reduced to IDs before dictionary writes.
Booleans are rejected as integer IDs. Separators remain inspectable definitions
but are not writable values. Unknown kinds and malformed values, including
malformed untouched values in a merged write, fail before dispatch.

## Batches and outcomes

```python
tasks = await property_binding.read([task_a, task_b])
receipts = await property_binding.patch_many(
    [task_a, task_b], {"priority": "high"}, concurrency=4,
)
receipts = await property_binding.patch_each({
    task_a: {"estimate": 0}, task_b: {"priority": None},
}, concurrency=4)
```

Mutations refresh definitions by default; `refresh=False` opts out for bound
patches. Batches validate every patch, requested record, parent membership and
complete merged payload before any write. Missing or inaccessible records raise
`OdooMissingError`; a moved record raises `PropertyScopeError`. Writes then use a
bounded worker pool (default four). Empty patches perform no write and produce no
receipt. Receipts follow input order for records with nonempty patches:

- `acknowledged`: a positive write response was received; this is not readback verification.
- `failed`: a definite rejection was observed; inspect `receipt.error`.
- `unknown`: dispatch may have occurred without a definitive response. Reconcile server state before retrying.

Single patches raise `PropertyWriteUnknownError` for uncertain outcomes. Batch
cancellation raises `PropertyBatchCancelledError`, an `asyncio.CancelledError`
subclass carrying `receipts` and `undispatched_ids`; completed outcomes are kept,
unresolved started operations are unknown, and workers are cancelled and drained.
No uncertain write is retried automatically.

## Why read-merge-write?

Odoo properties writes replace the stored value set. Sparse updates therefore
read current values, normalize them, merge changes and write a complete value-only
dictionary. This preserves supported server-visible unbound properties and avoids
forwarding definition metadata or definition-change flags.

The operation is non-atomic. It cannot preserve hidden stored keys absent from the
current definition, prevent concurrent lost updates, or prevent a task move after
preflight. After discovery, a refreshed bound batch uses one definition read, one
child read and one write per nonempty patch. Discovery adds two metadata calls and
one parent read; a bound read uses one child read. A direct read uses two metadata
calls, one child read and one definition read per distinct parent. A direct patch
adds one write to that path. `property_binding.inspect()` returns the resolved
alias/ID/kind/comodel/option mapping without RPCs.

## Legacy methods

### update_safely

Existing signatures remain available:

```python
await client.properties.update_safely(
    "sale.order", 42, "x_properties",
    {"priority": "high", "reviewed": True},
)
```

This adapter reads inline property metadata, normalizes relational values and
writes a merged value-only dictionary. It does not discover parent definitions.
New keys lacking inline metadata support scalar values only; use the dynamic API
for definition-aware validation. Despite its historical name, it is non-atomic.

### update_safely_batch

```python
await client.properties.update_safely_batch(
    "sale.order", [42, 43, 44], "x_properties", {"priority": "high"},
)
```

All records and merged payloads are preflighted before writes, followed by at most
four active workers. A failed or unknown result raises `PropertyBatchError` with
all `receipts`; do not retry the entire batch blindly.

### properties_to_write_format

```python
from godoo.client.services.properties import PropertiesService

payload = PropertiesService.properties_to_write_format([
    {"name": "owner", "value": [7, "Owner"], "type": "many2one", "comodel": "res.users"},
])
# {"owner": 7}
```

The converter and legacy updates share normalization primitives. This corrects
the former converter's verbatim relational display pairs and changes legacy
updates from metadata-carrying list writes to value-only dictionaries. Full
inline metadata validates relations/options; historical untyped scalars remain
supported. Ambiguous nested values are rejected. Normal client x2many command
serialization is separate from properties encoding.
