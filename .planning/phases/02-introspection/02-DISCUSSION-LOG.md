# Phase 2: Introspection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 2-Introspection
**Areas discussed:** Schema source, Generated type shape, Type-mapping for tricky fields, CLI model selection + cross-model refs (reframed mid-discussion to: CLI status + machine-readable metadata)

---

## Schema source

### Q1 — What's the schema-retrieval primitive for `Introspector.get_schema(model)`?

| Option | Description | Selected |
|--------|-------------|----------|
| `ir.model.fields` `search_read` | Matches SEED §2 wording, batchable across models in one RPC, exposes module/group attribution. Aligns with how @godoo/introspection works in spirit. | ✓ |
| `client.fields_get(model)` | One RPC per model returning the canonical ORM dict. Cheap, simple, already on the client. ORM-truth (includes computed fields). | |
| Hybrid: fields_get primary, `ir.model.fields` supplemental | Use fields_get for per-model field shape; query `ir.model.fields` when caller wants module/group attribution. Two code paths, richer output. | |

**User's choice:** `ir.model.fields` `search_read`
**Notes:** Aligns with SEED, batchable, gives module/group/store/compute/depends/on_delete attribution.

### Q2 — What does `Introspector.get_schema("res.partner")` return?

| Option | Description | Selected |
|--------|-------------|----------|
| `ModelSchema` dataclass with fields dict | `ModelSchema(name, info, transient, fields: dict[str, FieldSchema])` where `FieldSchema` is a typed dataclass. Fully typed, mypy-strict friendly. | ✓ |
| `dict[str, FieldSchema]` only | Just the field map, no wrapping. Lighter, but loses model-level metadata. | |
| Raw `list[dict[str, Any]]` from RPC | Thin pass-through. Pushes typing burden on caller — violates "never raw dict from service functions" convention. | |

**User's choice:** `ModelSchema` dataclass with fields dict
**Notes:** Project convention is dataclasses for types; raw dicts don't cross public APIs.

### Q3 — Should `Introspector` expose a batch API alongside the single-model one?

| Option | Description | Selected |
|--------|-------------|----------|
| Both: `get_schema(name)` + `get_schemas(names)` | Batch does one RPC for many models, then splits results. Cache populated for every model in the batch. | ✓ |
| Single-model only, internal batching opaque | Public API is `get_schema(name)`; cache prevents N RPCs after warm-up. Simpler surface, chattier first run. | |
| Batch-only, no single accessor | Always pass a list. Pure-functional shape. Less ergonomic for one-off lookups. | |

**User's choice:** Both
**Notes:** Batch warms cache for every model in the response.

---

## Generated type shape

### Q1 — What Python construct does `CodeGenerator` emit for each model?

| Option | Description | Selected |
|--------|-------------|----------|
| `TypedDict` | `class ResPartner(TypedDict, total=False): id: int; …` — matches search_read wire shape, zero runtime. | ✓ |
| `@dataclass` | Instantiable but mismatched with wire — requires `ResPartner(**row)` boilerplate. | |
| `.pyi` stub modules | Pure type-only, IDEs see them, runtime doesn't. Can't import names at runtime. | |
| `TypedDict` + `Protocol` pair | Two constructs to maintain. Overkill for parity. | |

**User's choice:** `TypedDict`
**Notes:** Matches `search_read`'s dict-of-dicts wire shape; runtime-importable.

### Q2 — How does the emitted `TypedDict` express required vs optional fields?

| Option | Description | Selected |
|--------|-------------|----------|
| `total=False`; `id` explicitly `Required` | Wire reality — any field may be omitted from a partial `search_read`; `id` is the one guaranteed key. Python 3.14 has `Required`/`NotRequired` natively. | ✓ |
| `total=True`, optional only when Odoo `required=False` | Matches the model's storage-time required flag. Lies about wire because partial reads. | |
| `total=False`, plain (no `Required`/`NotRequired`) | Simplest; loses the "id is always present" assertion. | |

**User's choice:** `total=False`; `id: Required[int]`
**Notes:** PEP 655 markers; faithful to partial-read wire reality.

### Q3 — How are emitted files laid out and named?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat dir + auto-generated `__init__.py` barrel | `res_partner.py`, `account_move_line.py`, … plus `__init__.py` re-exporting `ResPartner`, `AccountMoveLine`, … | ✓ |
| Flat dir, no `__init__.py` | One file per model, callers always import the specific module. | |
| Single combined module | All types in one `models.py`. Conflicts with ROADMAP "one .py file per requested model". | |

**User's choice:** Flat dir + auto-generated `__init__.py` barrel
**Notes:** snake_case dotted-model → filename; PascalCase joined → class name.

---

## Type-mapping for tricky fields

### Q1 — Wire-faithful or Python-idiomatic type mapping?

| Option | Description | Selected |
|--------|-------------|----------|
| Wire-faithful: keep `Literal[False]` and wire scalars | `many2one → tuple[int, str] \| Literal[False]`; dates/datetime/binary → `str \| Literal[False]`. TypedDict tells the truth. | ✓ |
| Python-idiomatic: `None` nulls + parsed scalars | `int \| None` for m2o; `datetime.date \| None`; `bytes \| None`. Cleaner-looking but the type lies. | |
| Hybrid: `Literal[False]` for nulls, parsed scalars | Pushes parsing into codegen runtime — doesn't fit TypedDict (pure typing, no parser hook). | |

**User's choice:** Wire-faithful
**Notes:** Consumers coerce at their boundary; type matches what's literally in the dict.

### Q2 — What does codegen emit when a selection field has no enumerable values (dynamic/computed selection)?

| Option | Description | Selected |
|--------|-------------|----------|
| Fallback to `str \| Literal[False]` with inline comment | `state: NotRequired[str \| Literal[False]]  # dynamic selection — values not enumerable` | ✓ (initial — then revised) |
| Hard error during codegen | Refuse to emit the model. Forces manual override. | |
| Skip the field entirely | Omit dynamic-selection fields. Loses field from type. | |

**User's choice:** Initially fallback with inline comment — **revised mid-discussion** per the CLI/comment correction. Final landing: `Annotated[str | Literal[False], FieldMeta(..., dynamic_selection=True)]` — metadata is machine-readable, NOT a comment. See D-Mapping-2 in CONTEXT.md.

### Q3 — How does the type mapper handle unmapped or unknown Odoo ttypes?

| Option | Description | Selected |
|--------|-------------|----------|
| Known table + `Any` fallback with comment | Standard table for `image`/`html`/`monetary`/`serialized`/`properties`; unknown → `Any # unmapped ttype: foo`. | ✓ (initial — then revised) |
| Known table + hard error on unknown | Block codegen on any module surprise. | |
| Known table + skip unknown fields silently | Hidden gaps risk. | |

**User's choice:** Initially fallback with comment — **revised mid-discussion** to machine-readable. Final landing: `Annotated[Any, FieldMeta(ttype='<unknown>', original_ttype='foo')]`. Warning still logged at codegen time. See D-Mapping-3.

---

## CLI status (reframed mid-area-4 by the owner)

> Mid-discussion correction from the owner: *"Introspect has NEVER BEEN A CLI,
> it has always been a library to be consumed by tooling. Everything introspect
> does has to be consumable by code, which already kills any shit comment usage.
> First consumer is the state manager library; or a structure-aware domain
> filter library."*
>
> The originally-planned "CLI model selection + cross-model refs" question batch
> was rejected on submit and replaced with the two questions below.

### Q1 — What's the status of INTRO-05 (the `godoo-introspect` CLI)?

| Option | Description | Selected |
|--------|-------------|----------|
| Drop it — amend SEED/REQUIREMENTS/ROADMAP | Hard-drop INTRO-05 from v1 like CLIENT-09 was. Strike from SEED §2/§4, REQUIREMENTS.md, ROADMAP, PROJECT.md. Phase 2 becomes pure library. | ✓ |
| Keep as a thin convenience wrapper, library is primary | Library is the deliverable; CLI is a tiny argparse wrapper. | |
| Keep INTRO-05 as written, separate concern | Build the CLI as a real entry point. Doubles the surface. | |

**User's choice:** Drop it — amend planning docs (same protocol as CLIENT-09)
**Notes:** Charter wording was historical; the library has always been the intended deliverable.

### Q2 — How is machine-readable per-field metadata attached to the emitted `TypedDict`s?

| Option | Description | Selected |
|--------|-------------|----------|
| PEP 593 `Annotated` + marker classes | Standard Python typing machinery; consumers read via `typing.get_type_hints(cls, include_extras=True)`. | ✓ |
| Parallel `_FIELDS: dict[str, FieldMeta]` alongside the TypedDict | Simpler to consume, but two structures to keep in sync. | |
| Both: `Annotated` AND `_FIELDS` dict | Belt + suspenders, redundant truth. | |

**User's choice:** PEP 593 `Annotated`
**Notes:** Single source of truth; standard typing introspection works out of the box.

### Q3 — How are the per-field markers structured?

| Option | Description | Selected |
|--------|-------------|----------|
| One unified `FieldMeta` marker carrying all Odoo attributes | Frozen dataclass, one source of truth, exhaustive. Consumers do one `isinstance` check. | ✓ |
| Multiple narrow markers per concern | `Relation`, `Required`, `Help`, `Compute`, `Modules`, … composable. Walk markers and isinstance-check each. | |
| Hybrid: `FieldMeta` base + narrow special-case markers | Mixed pattern; two things to learn. | |

**User's choice:** One unified `FieldMeta`
**Notes:** Frozen dataclass, hashable, lives in `godoo_introspection.markers`.

### Q4 — What is `FieldMeta`'s attribute set?

| Option | Description | Selected |
|--------|-------------|----------|
| Full `ir.model.fields` projection | All standard columns + codegen-specific flags. Forward-compatible. | ✓ |
| Minimum viable for known consumers | Only `ttype`, `relation`, `required`, `readonly`, `store`, `help`, `original_ttype`, `dynamic_selection`. | |
| Mirror only stable Odoo columns | Drop `compute`/`depends`/`modules`. | |

**User's choice:** Full `ir.model.fields` projection
**Notes:** Consumers (state manager, domain filter) want everything machine-readable from `ir.model.fields`; nothing hidden behind comments.

---

## Claude's Discretion

- Missing-model behaviour: planner uses `OdooMissingError` per Phase 1 D-16 precedent.
- `FieldSchema` attribute list and `ModelSchema` row metadata (transient, info, state): planner discretion within the `FieldMeta` projection above.
- Cache scope (per-`Introspector`-instance vs module-global): per-instance is the safer default; researcher confirms.
- Bypass-cache shape: `get_schema(name, bypass_cache=True)` keyword vs separate `refresh(name)`: planner discretion.
- `Introspector` ↔ `CodeGenerator` composition (constructor signatures, whether `CodeGenerator` takes an `Introspector` or a `ModelSchema`): planner discretion.
- Generated file conventions (`from __future__ import annotations` header, `# AUTOGENERATED` banner, help-text-as-docstring rendering): planner discretion grounded in CONVENTIONS.md.
- Filename/class-name normalisation edge cases: planner picks the canonical case-fold rule.

## Deferred Ideas

- None new from this discussion — it stayed within phase scope.
- **INTRO-05 (CLI) is not deferred** — it was hard-dropped per D-CLI-1, not parked.
- Pre-existing v2 deferrals (`COMPAT-01`, `CLIENT-V2-01`, `PERF-01/02`) remain untouched.
- "Consumer convenience" helpers (e.g. `godoo-introspection` helpers for the state manager to traverse `FieldMeta.relation` chains): out of scope for Phase 2; downstream consumers shape their own APIs.
