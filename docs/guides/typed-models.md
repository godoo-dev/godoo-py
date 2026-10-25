# Instance-derived typed models

The raw client path accepts an Odoo model name and returns dictionaries. The typed
path accepts a generated model class and returns Pydantic instances with Odoo wire
values transformed for Python. Install `godoo-client[typed]` for typed consumers and
`godoo-introspection` where you generate the models. Core raw calls remain httpx-only.

## Generate models

Generation reads the selected Odoo instance. Configure the normal `ODOO_*`
connection variables and create an output directory first:

```sh
mkdir -p generated
uv run godoo-introspect generate --output generated --models 'res.partner,project.*'
```

`--models` uses comma-separated fnmatch patterns; `--all` selects all installed
models and is mutually exclusive with `--models`. Choose the output location and
regeneration cadence in the consuming project. Schema changes require regeneration;
a generated package is an instance/version-specific snapshot.

The generator emits `__odoo_model__` identity, selection types and relation/write
metadata. Static files give editors a type they can inspect offline. Runtime-only
model synthesis cannot provide that same static return type.

## Read and relation boundaries

`client.read(ModelClass, ids)` and `client.search_read(ModelClass, domain)` dispatch
to typed models. A string model name keeps the raw dictionary path. Partial typed
reads derive a partial shape. Wire `False`, date/datetime strings and many2one pairs
are transformed by the typed layer.

`Ref[T]` represents a relation; reading a ref resolves one target, and reading a
list batches targets by model. This is single-level resolution. Arbitrary recursive
nesting, cycle handling and nested-child writes are outside the present interface.
A target must carry resolvable generated model metadata; unresolved/heterogeneous
references need caller care and must not be treated as a portable graph loader.

## Write boundaries

`client.create(instance)` returns a new ID; `client.write(instance)` serializes
explicitly set writable fields. Relation refs become remote IDs, `None` becomes
Odoo `False`, and dates/datetimes become wire strings. Readonly/computed fields are
excluded. Explicit x2many typed writes are designed to raise; fields inherited
from a read are omitted. Use the raw client API and Odoo command tuples when you
need explicit x2many operations. Do not assume a copied Pydantic object is a
complete desired-state resource or that defaults are preserved on create.

These are source-level interfaces, not a blanket robustness or runtime acceptance
claim. Standalone resource ownership, dependency ordering and desired-state
reconciliation belong to Stateman.
