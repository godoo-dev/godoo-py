# Phase 2: Introspection - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `godoo-introspection` from scratch — a Python **library** (NOT a CLI) that
discovers live Odoo schemas and generates typed, **programmatically-consumable**
Python representations. First-class consumers are downstream tooling: the godoo
state-manager, structure-aware domain-filter libraries, future code-aware helpers.
Every artefact the library emits — types, relation targets, dynamic-selection
markers, unmapped-ttype fallbacks — must be machine-readable.

Phase 2 delivers, inside `packages/godoo-introspection/`:

- **INTRO-01** `Introspector` — queries `ir.model.fields` on a live Odoo instance for
  schema retrieval
- **INTRO-02** `IntrospectionCache` — model-keyed, with a live-bypass option
- **INTRO-03** `CodeGenerator` — emits a valid Python module string from a
  `ModelSchema`
- **INTRO-04** type mapper — Odoo ttypes → Python type hints
- **INTRO-06** selection fields emitted as `Literal[...]`
- **INTRO-07** `py.typed` PEP 561 marker

**6 requirements.** Scope is fixed by REQUIREMENTS.md / ROADMAP.md — discussion
clarified HOW to implement, never WHETHER to add capabilities.

**Removed from scope:** **INTRO-05 (`godoo-introspect` CLI) hard-dropped** by owner
decision — see D-CLI-1. The library has never been intended to ship a CLI; the
charter wording in SEED §2 and REQUIREMENTS / ROADMAP needs to be amended (same
protocol that retired CLIENT-09 in Phase 1).

</domain>

<decisions>
## Implementation Decisions

### Scope change — INTRO-05 dropped
- **D-CLI-1:** INTRO-05 (`godoo-introspect` CLI entry point) is removed from v1
  scope entirely. The library is the deliverable; consumers are other Python
  tooling. The amendment lands in:
  - `SEED.md` §2 (strike the CLI bullet from the `godoo-introspection` section)
    and §4/§5 if referenced — *charter amendment, same protocol as CLIENT-09*.
  - `.planning/REQUIREMENTS.md` — strike `INTRO-05`, update traceability table,
    update coverage count (30→29 v1 requirements).
  - `.planning/ROADMAP.md` — Phase 2 requirements line (drop INTRO-05) and
    success criterion 4 (rephrase from "Running `godoo-introspect ...` writes
    one .py file per requested model" to a library-level criterion, e.g.
    "Calling `CodeGenerator.write(models, output_dir)` writes one .py file per
    requested model"; planner decides exact wording).
  - `.planning/PROJECT.md` — drop the CLI bullet from Active, add a Key
    Decisions row.
  - Other INTRO IDs are **not** renumbered — the gap is self-documenting (same
    pattern as CLIENT-09 → CLIENT-10).

### Schema source — INTRO-01
- **D-Schema-1:** `Introspector.get_schema()` uses **`search_read('ir.model.fields',
  ...)`** as the schema primitive (NOT `client.fields_get()`). Matches SEED §2
  wording; batchable across models in one RPC; exposes module / group / on_delete
  / store / compute / depends / modules attribution that `fields_get` does not.
- **D-Schema-2:** `get_schema()` returns a **typed `ModelSchema` dataclass**:
  `ModelSchema(name, info, transient, fields: dict[str, FieldSchema])`. `FieldSchema`
  is a frozen dataclass carrying the full `ir.model.fields` projection. No raw
  `dict[str, Any]` leaks across the public API (per project conventions).
- **D-Schema-3:** Dual public API — `get_schema(name: str) -> ModelSchema` AND
  `get_schemas(names: list[str]) -> dict[str, ModelSchema]`. The batch path does
  one RPC (`[('model', 'in', names)]`) and warms the cache for every model
  returned. Single-model calls stay a thin wrapper over the batch.
- **Planner discretion:** missing-model behaviour follows the existing convention —
  `OdooMissingError` raised when a requested model is not present in `ir.model`
  (mirrors `client.ref()` D-16). FieldSchema attribute list and exact ir.model
  row metadata captured on `ModelSchema` (transient, info, state) are at planner
  discretion grounded in the FieldMeta projection below.

### Generated type shape — INTRO-03, INTRO-04, INTRO-06
- **D-Shape-1:** `CodeGenerator` emits **`TypedDict`** per model (NOT `@dataclass`,
  NOT `.pyi` stubs, NOT Pydantic — Pydantic is rejected globally). TypedDict
  matches the wire shape of `search_read`'s dict-of-dicts return; zero-runtime;
  imports at runtime so consumers can do `isinstance` / `get_type_hints` on them.
- **D-Shape-2:** TypedDict declared with **`total=False`**; the `id` field is
  marked **`Required[int]`**; every other field is `NotRequired[...]`. This
  models the wire reality: any field may be omitted from a partial
  `search_read(fields=[...])`; only `id` is guaranteed. Python 3.14 has
  `Required`/`NotRequired` natively (PEP 655).
- **D-Shape-3:** **Flat output directory**, one `.py` file per model. Filename
  is the snake_case dotted model name (`res.partner` → `res_partner.py`,
  `account.move.line` → `account_move_line.py`). Class name is the PascalCase
  joined form (`ResPartner`, `AccountMoveLine`). Auto-generated `__init__.py`
  re-exports every emitted class (barrel) so consumers can write
  `from generated_types import ResPartner` OR
  `from generated_types.res_partner import ResPartner`.
- **Planner discretion:** file-header convention (`from __future__ import
  annotations`, `# AUTOGENERATED` banner), help-text-as-docstring rendering,
  exact `CodeGenerator.generate(model: str) -> str` vs
  `CodeGenerator.write(models, output_dir)` API split. INTRO-03 success
  criterion ("receive a valid Python module string") implies the `.generate`
  variant is the primary; writing to disk is a thin convenience built on it.

### Type mapping — INTRO-04, INTRO-06
- **D-Mapping-1:** **Wire-faithful mapping.** The TypedDict reports what
  `search_read` literally returns; consumers coerce at their boundary.
  - `many2one` → `tuple[int, str] | Literal[False]`
  - `date` / `datetime` → `str | Literal[False]` (ISO wire form, NOT
    `datetime.date`/`datetime.datetime`)
  - `binary` → `str | Literal[False]` (base64 wire form, NOT `bytes`).
    Note: this is the schema type, distinct from `client.read_binary()` which
    decodes to `bytes` (D-18).
  - `selection` → `Literal["value1", "value2", ...] | Literal[False]` (closed-set
    preserved — INTRO-06)
  - `one2many` / `many2many` → `list[int]`
  - `reference` → `str | Literal[False]` (Odoo's "model,id" form)
  - `char` / `text` / `html` / `image` → `str | Literal[False]`
  - `integer` → `int | Literal[False]`
  - `float` / `monetary` → `float | Literal[False]`
  - `boolean` → `bool`
  - `serialized` → `str | Literal[False]`
  - `json` / `properties` → `dict[str, Any] | Literal[False]`
- **D-Mapping-2:** **Dynamic selection (no enumerable values)** —
  `Annotated[str | Literal[False], FieldMeta(..., dynamic_selection=True)]`.
  The Literal[...] is dropped (no enumerable values); the metadata flag tells
  consumers this is a closed-set-at-runtime field whose values aren't known at
  codegen time. **No inline comment** — metadata must be machine-readable.
- **D-Mapping-3:** **Unknown / unmapped ttype** —
  `Annotated[Any, FieldMeta(ttype='<unknown>', original_ttype='foo')]`.
  Falls back to `Any` so codegen still completes; the original Odoo ttype is
  preserved in `FieldMeta.original_ttype` so consumers can decide what to do.
  Codegen logs a warning at generation time. **No inline comment** —
  machine-readable only.

### Cross-model references — relations
- **D-Refs-1:** `many2one` and `one2many`/`many2many` relation targets are
  carried **as strings in the `FieldMeta` marker**, NOT as Python type
  references and NOT as inline comments. Example: `country_id` on `res.partner`
  is emitted as:

  ```python
  country_id: NotRequired[
      Annotated[
          tuple[int, str] | Literal[False],
          FieldMeta(ttype='many2one', relation='res.country', required=False, ...),
      ]
  ]
  ```

  Files stay independent — codegen for `res.partner` does NOT require codegen
  for `res.country`. No transitive-closure obligation. Consumers traverse
  relations by reading `FieldMeta.relation` and looking up the target
  TypedDict themselves (e.g., the state manager keeps its own type registry).

### Machine-readable metadata — Annotated markers
- **D-Meta-1:** Per-field metadata is attached via **PEP 593
  `Annotated[T, FieldMeta(...)]`**. Consumers extract via
  `typing.get_type_hints(SomeTypedDict, include_extras=True)` and walk the
  metadata tuple looking for `FieldMeta` instances. Standard Python typing
  machinery; no parallel structures to keep in sync.
- **D-Meta-2:** A **single unified `FieldMeta` frozen dataclass** carries every
  per-field attribute. NOT multiple narrow markers (no separate `Relation()`,
  `Required()`, `Help()`, `Compute()` markers). Single source of truth per
  field; one `isinstance(m, FieldMeta)` check on the consumer side.
- **D-Meta-3:** `FieldMeta` is the **full `ir.model.fields` projection** plus
  codegen-specific flags. Attribute set:
  - From `ir.model.fields`: `ttype`, `field_description`, `relation`,
    `relation_field`, `required`, `readonly`, `store`, `index`, `copy`,
    `translate`, `help`, `compute`, `depends` (tuple), `modules` (tuple),
    `on_delete`, `size`, `digits`
  - Codegen-specific: `original_ttype` (preserved when ttype is unmapped),
    `dynamic_selection` (bool, True when selection values aren't enumerable
    at codegen time)
  - `FieldMeta` lives in a small public module (e.g.
    `godoo_introspection.markers`) so consumers import it directly. Frozen
    dataclass, hashable, `repr`-friendly.

### Claude's Discretion
- **Cache scope** (per-`Introspector`-instance vs module-global) — INTRO-02
  says "keyed by model name, with a live-bypass option." Pattern precedent
  exists for both: module-global `_cache` in `services/cdc/field_cache.py`
  vs per-instance state. Planner picks based on test-isolation and
  multi-client safety. Per-instance is the safer default; researcher should
  confirm.
- **Bypass option shape** — `get_schema(name, bypass_cache=True)` keyword on
  the call vs a separate `refresh(name)` method. Planner discretion.
- **`Introspector` ↔ `CodeGenerator` API split** — INTRO-01 and INTRO-03 lock
  the class names; their composition (constructor signatures, whether
  `CodeGenerator` takes an `Introspector` or a `ModelSchema`, whether there's
  a single top-level convenience function) is planner discretion grounded in
  the project's quad pattern.
- **`__init__.py` package barrel** — auto-generated content (whether it's
  literally re-exported `ResPartner`, `AccountMoveLine`, … or whether it also
  re-exports `FieldMeta` from the user-supplied source module) is planner
  discretion.
- **Filename/class-name normalisation edge cases** — model names containing
  unusual characters (`_`, digits, single-letter segments) follow standard
  Python identifier rules; planner picks the canonical case-fold rule.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Charter & requirements
- `SEED.md` §2 (`godoo-introspection` block) — defines the introspection parity
  surface. `../godoo-ts/packages/` contains only `_example` — there is **no TS
  reference implementation** to mirror, so SEED §2 IS the spec, same as the
  client. Amendment due 2026-05-21: strike the CLI bullet (INTRO-05) per D-CLI-1.
- `.planning/REQUIREMENTS.md` — INTRO-01–04, INTRO-06–07 requirement text +
  traceability table. INTRO-05 to be struck per D-CLI-1; v1 coverage 30→29.
- `.planning/ROADMAP.md` — Phase 2 goal + success criteria. Success criterion 4
  to be rephrased from CLI-flavoured to library-flavoured per D-CLI-1.

### Phase 1 decisions (apply here)
- `.planning/phases/01-client-parity/01-CONTEXT.md` — especially D-15
  (`client.fields_get()` returns raw `dict[str, Any]` — explicitly defers typed
  field-metadata representations to Phase 2 / this CONTEXT), D-16 (`ref()` →
  `OdooMissingError` precedent), D-18 (`read_binary()` decodes to `bytes` —
  contrast with binary-as-`str` in TypedDict schemas, D-Mapping-1), and the
  client surface as the integration target.

### Codebase (the patterns and integration points)
- `.planning/codebase/ARCHITECTURE.md` — layer model, `OdooClient` as the sole
  integration point; service pattern (`types.py` / `functions.py` / `service.py`
  / `__init__.py` quad — though introspection is a separate package, the
  module conventions still apply); anti-patterns.
- `.planning/codebase/CONVENTIONS.md` — naming, typing, module conventions
  (snake_case modules, PascalCase classes, dataclasses-not-Pydantic, all-async,
  `from __future__ import annotations`, `TYPE_CHECKING` imports for
  `OdooClient`).
- `.planning/codebase/STRUCTURE.md` §`packages/godoo-introspection/` — current
  placeholder state of the package.
- `packages/godoo/src/godoo/client.py` — `OdooClient` surface;
  `search_read()` is the primary primitive `Introspector` calls (D-Schema-1).
  `fields_get()` at `:280` (D-15) is NOT used by introspection but is the
  obvious adjacent API to be aware of.
- `packages/godoo/src/godoo/errors.py` — `OdooMissingError`,
  `OdooValidationError` — reuse, do not add new types.

### Reference (not authoritative)
- `../godoo-ts/packages/` — contains only `_example`; no
  `@godoo/introspection` source to mirror. Cite SEED §2 instead.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`OdooClient.search_read`** (`packages/godoo/src/godoo/client.py`) — the
  primary RPC primitive `Introspector` calls against `ir.model` and
  `ir.model.fields`. Phase 1 didn't change its shape; the existing typing
  (returns `list[dict[str, Any]]`) is sufficient for the introspection layer
  to cast into `ModelSchema` / `FieldSchema`.
- **`OdooClient`** as constructor argument — `Introspector(client: OdooClient)`
  follows the service convention even though introspection is a separate
  package; use `TYPE_CHECKING` for the `OdooClient` annotation.
- **`OdooMissingError`** (`packages/godoo/src/godoo/errors.py`) — the right
  exception type when a requested model isn't in `ir.model` (consistent with
  Phase 1 D-16).
- **Per-instance cache pattern precedent** — `services/cdc/field_cache.py` has
  a module-global `_cache: dict[str, FieldMeta]` (process-scoped); the
  `urls/functions.py` has `_base_url_cache` keyed by `id(client)`. Both are
  valid prior art; the `IntrospectionCache` design decision (per-instance vs
  module-global) is open per Claude's Discretion above.
- **Dataclass-for-types convention** — `ModelSchema`, `FieldSchema`, and
  `FieldMeta` are frozen dataclasses, matching every other types module in the
  codebase.

### Established Patterns
- `from __future__ import annotations` at the top of every module — applies to
  generated `.py` files too (they live in user code at runtime; the convention
  is universal).
- `TYPE_CHECKING` imports for `OdooClient` to prevent circular imports.
- Local precondition validation raises `OdooValidationError` before the RPC —
  applies to e.g. empty-`models` list inputs.
- One service per package quad (`types.py` / `functions.py` / `service.py` /
  `__init__.py`) — `godoo-introspection` may adopt the same shape inside its
  own `src/godoo_introspection/` even though it's not a service-of-`godoo`
  (planner discretion).
- `cast()` at the `client.call()`/`search_read()` boundary to absorb the
  `dict[str, Any]` return and produce typed `ModelSchema`/`FieldSchema`
  instances.

### Integration Points
- `Introspector` takes an authenticated `OdooClient` and only calls
  `search_read` on it — no new client surface needed. The Phase 1 client API
  already exposes everything required.
- Generated `.py` files import from `typing` (`TypedDict`, `Required`,
  `NotRequired`, `Literal`, `Annotated`, `Any`) and from
  `godoo_introspection.markers` (`FieldMeta`). The user's generated-types
  directory must therefore have `godoo-introspection` importable at runtime
  (it's a real runtime import, not just type-time).
- The `py.typed` marker (INTRO-07) lands as a mechanical empty file inside
  `packages/godoo-introspection/src/godoo_introspection/py.typed`, exactly
  like CLIENT-10 / D-19 for the client.

</code_context>

<specifics>
## Specific Ideas

- **Owner's framing for the package shape:** *"Introspect has NEVER BEEN A CLI,
  it has always been a library to be consumed by tooling. Everything introspect
  does has to be consumable by code, which already kills any shit comment
  usage. First consumer is the state manager library; or a structure-aware
  domain filter library."* This overturned both the residual CLI requirement
  (INTRO-05) and any design that leaned on inline comments as the metadata
  carrier — every emitted artefact must be programmatically extractable.
- The named downstream consumers — godoo state-manager, structure-aware domain
  filter — are the design north star for `FieldMeta`'s attribute set
  (D-Meta-3). Anything those tools want from Odoo's `ir.model.fields` should
  surface; nothing should be hidden behind a comment.
- The choice of **PEP 593 `Annotated`** over a parallel `_FIELDS` dict was made
  to keep one source of truth (the TypedDict) and lean on standard
  `typing.get_type_hints(include_extras=True)` for extraction — no custom
  registry to drift.

</specifics>

<deferred>
## Deferred Ideas

- **None new** from this discussion — it stayed within phase scope.
- **INTRO-05 (CLI) is not deferred** — it was hard-dropped (D-CLI-1), the same
  protocol used to retire CLIENT-09 in Phase 1. It does not park for a later
  milestone unless explicitly re-scoped.
- Pre-existing deferrals on record in REQUIREMENTS.md (v2 section) — COMPAT-01
  (Python floor), CLIENT-V2-01 (auto re-auth), PERF-01/02 — remain untouched.
- A future "consumer convenience" library (e.g. helpers in `godoo-introspection`
  for the state manager to traverse `FieldMeta.relation` chains) is **not** in
  scope here; this phase only emits the data, doesn't shape the consumer's
  API.

</deferred>

---

*Phase: 2-Introspection*
*Context gathered: 2026-05-21*
