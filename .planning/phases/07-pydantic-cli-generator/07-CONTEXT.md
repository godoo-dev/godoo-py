# Phase 7: Pydantic CLI Generator - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend `godoo-introspection` with a Pydantic model emitter and a `godoo-introspect`
CLI entrypoint. The existing `CodeGenerator` (TypedDict emitter) is hard-replaced by a
Pydantic-model emitter; the TypedDict codegen path and its tests are removed;
`type_mapper.py` is migrated to Pydantic type forms. A single CLI command
`godoo-introspect generate` connects to a live Odoo instance, fetches model schemas
via the existing `Introspector`, and writes one Pydantic file per model plus a barrel
`__init__.py` to a user-specified output directory.

**In scope:** CLI entrypoint (`godoo-introspect generate`, `typer`-based), model
selection (`--models <glob,...>` fnmatch-style / `--all`), credential handling
(`config_from_env()` default, flag overrides), relation-target degradation
(`Ref[TargetClass]` vs `Ref[int]`), Pydantic emitter replacing TypedDict emitter,
`type_mapper.py` migration to Pydantic type forms, removal of TypedDict codegen +
its tests, `pydantic>=2.13` + `typer>=0.26` as runtime deps of `godoo-introspection`,
`[project.scripts]` entry `godoo-introspect` in `packages/godoo-introspection/pyproject.toml`.

**Out of scope:** Nested relational fetch (phase deferred as TYPED-F1); typed
write/create paths (TYPED-F2); Pyodide browser execution (Phase 8); any changes to
`packages/godoo-client`; keeping any TypedDict codegen path alive.

</domain>

<decisions>
## Implementation Decisions

### Emitter Architecture

- **D-01 (Pydantic replaces TypedDict — breaking change):** The existing `CodeGenerator`
  in `codegen.py` currently emits TypedDict modules (INTRO-03, shipped in v0.2.0).
  In Phase 7 this class is hard-replaced: it becomes a Pydantic-model emitter.
  The TypedDict emitter and all tests that exercise the TypedDict output are deleted.
  `type_mapper.py` is migrated to emit Pydantic-compatible type forms (e.g. `Optional[str]`
  instead of `str | Literal[False]`; `Ref[TargetClass]` or `Ref[int]` for many2one;
  `list[int]` for x2many). This is a **breaking change** to the published v0.2.0 public
  API surface (INTRO-03) and must be changelog-noted at release.
  NOTE: This is planning context only — do NOT implement the emitter during Phase 7
  planning; implementation happens in the execution plans.

- **D-02 (Rationale for Pydantic — from SEED-002):** Pydantic is the deliberate exception
  to the project's "dataclasses, not Pydantic" rule because it handles Odoo's bidirectional
  wire transform DECLARATIVELY (False→None, [id,name]→Ref, str→date/datetime,
  str→Literal) with zero per-model glue. A dataclass cannot do this without hand-written
  `__post_init__` per model. This is not a port of godoo-ts; it is a Pythonic design that
  takes advantage of Pydantic's validation model.

### Carried Forward from Phase 6 (locked — do not re-derive)

- **CF-01:** Generated models subclass `OdooBaseModel` from
  `godoo.client._pydantic_transform`. `OdooBaseModel(BaseModel)` owns the `@model_validator`
  wire transforms (False→None for non-bool, m2o→Ref, date-string→datetime).
- **CF-02:** Each generated model carries `__odoo_model__: ClassVar[str]` set to the Odoo
  technical name (e.g. `"res.partner"`), enabling `client.read(ResPartner, ids)` dispatch
  via `hasattr(model, "__odoo_model__")` — never `isinstance(BaseModel)`.
- **CF-03:** Selection fields emit as `Literal[...]` with instance-actual registered values.
  Static known values → `Literal['val1', 'val2', ...]`. Dynamic (no values at introspection
  time) → `str`.
- **CF-04:** Boolean fields emit as plain `bool` (default `False`) — the one non-Optional
  exception. The `@model_validator` in `OdooBaseModel` inspects `model_fields[name].annotation`;
  if `bool`, leave untouched (Odoo's real `False` is preserved). All other scalar fields →
  `Optional[T] = None`.
- **CF-05:** one2many / many2many fields → `list[int]`. x2many always yields a list, never
  `Ref[T]`.
- **CF-06:** `pydantic>=2.13` and `typer>=0.26` are **runtime deps** of `godoo-introspection`
  (not extras). No optional-extra gating on the CLI package itself.

### Model Selection

- **D-03 (model selection flags):** `godoo-introspect generate` accepts:
  - `--models pat1,pat2,...` — comma-separated list of fnmatch-style glob patterns matched
    against Odoo technical model names (e.g. `project.*`, `res.partner`, `account.*`).
    `*` matches any characters including dots.
  - `--all` — generate every installed model (queries `ir.model` without name filter).
  - Exactly one of `--models` or `--all` must be provided; missing → clear error, non-zero exit.

### Relation Targets (many2one)

- **D-04 (relation degradation for many2one):** Target model IS in the generated set →
  emit `Ref[TargetClass]` with a cross-import at the top of the file (from the same output
  package). Target model NOT in the generated set → degrade to `Ref[int]` with a trailing
  `# <odoo.model>` comment on the same line. Files must always compile without errors.
  NO transitive auto-inclusion — if `res.partner` references `res.country` and `res.country`
  is not in the selection, the field types as `Ref[int]  # res.country`.

### Credentials

- **D-05 (credential handling):** `config_from_env()` (reads `ODOO_URL`, `ODOO_DB`,
  `ODOO_USER`, `ODOO_PASSWORD` with the standard env-var prefix) is the default credential
  source. CLI flags `--url`, `--db`, `--user`, `--password` override individual env values.
  Missing config (env and flags both absent for a required value) → clear error message,
  non-zero exit. Password is never echoed, never logged.

### Command Name

- **D-06 (command name):** The CLI command is `godoo-introspect generate` (plain `generate`,
  not `generate-pydantic`). Single Pydantic output means no disambiguation suffix is needed.
  The `[project.scripts]` entry `godoo-introspect` is greenfield (does not currently exist
  in `packages/godoo-introspection/pyproject.toml`).

### Claude's Discretion

- Exact typer argument / option names and help strings — follow typer conventions.
- Whether `--output` defaults to `./models/` or is required — either is fine; required
  is simpler and avoids accidental overwrites.
- Whether to validate output dir existence before connecting to Odoo (fail fast) — yes,
  preferred (validate early, `write()` already enforces this).
- Error message wording for missing credentials or unknown model patterns.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements

- `.planning/ROADMAP.md` §"Phase 7: Pydantic CLI Generator" — goal, success criteria
  (SC-1 through SC-4), requirement IDs TYPED-01/TYPED-02.
- `.planning/REQUIREMENTS.md` — full text of TYPED-01, TYPED-02 (and the supersession
  note linking back to INTRO-03).
- `.planning/PROJECT.md` — dataclasses-not-Pydantic convention (and its deliberate
  exception for the typed layer), httpx-as-sole-runtime-dep constraint for `godoo-client`
  (not `godoo-introspection`).

### Seed & Rationale

- `.planning/seeds/SEED-002-instance-specific-typed-models.md` — origin of the Pydantic
  decision, rationale for static codegen over LSP/mypy-plugin/runtime-dynamic, open
  questions that Phase 6/7 settled.

### Phase 6 Context (locked decisions carried forward)

- `.planning/phases/06-transport-seam-typed-models-core/06-CONTEXT.md` — D-01 through
  D-11; defines `OdooBaseModel`, `OdooModel` Protocol, `Ref[T]`, wire transforms,
  dispatch guard, isolation invariant. CF-01 through CF-06 above come from here.

### Current Source — Introspection Package

- `packages/godoo-introspection/src/godoo/introspection/codegen.py` — existing
  `CodeGenerator` (TypedDict emitter, to be replaced); `_model_to_classname`,
  `_model_to_filename`, `write()` loop, barrel `__init__.py` generation, identifier
  validation — these helpers are REPURPOSED for the Pydantic emitter.
- `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` — current
  TypedDict-oriented type mapper; to be migrated to Pydantic type forms (Optional[T],
  Ref[TargetClass]/Ref[int], list[int], Literal, bool).
- `packages/godoo-introspection/src/godoo/introspection/types.py` — `FieldSchema`,
  `ModelSchema` dataclasses; consumed unchanged.
- `packages/godoo-introspection/src/godoo/introspection/introspector.py` — `Introspector`
  and `IntrospectionCache`; provides async schema fetch; consumed unchanged.
- `packages/godoo-introspection/pyproject.toml` — current deps (`godoo-client>=0.1.0`
  only); needs `pydantic>=2.13`, `typer>=0.26`, and a `[project.scripts]` entry.

### Current Source — Client Package (consumed, not modified)

- `packages/godoo-client/src/godoo/client/typed.py` — `OdooModel` Protocol,
  `Ref[T]` dataclass (stdlib-only; always importable).
- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — `OdooBaseModel`;
  generated files import `from godoo.client._pydantic_transform import OdooBaseModel`.
- `packages/godoo-client/src/godoo/client/config.py` — `config_from_env()`,
  `OdooClientConfig`, `create_client()`; credential sourcing for the CLI.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_model_to_classname(model: str) -> str`** in `codegen.py:50` — converts
  `"res.partner"` → `"ResPartner"`. Already correct; REPURPOSE for Pydantic emitter.
- **`_model_to_filename(model: str) -> str`** in `codegen.py:55` — converts
  `"res.partner"` → `"res_partner.py"`. Already correct; REPURPOSE.
- **`CodeGenerator.write()` loop** in `codegen.py:185` — iterates schemas, calls
  `self.generate(schema)`, writes files, then writes barrel `__init__.py`. The loop
  structure, identifier-validation guard, and barrel generation logic are REPURPOSED;
  only the `generate()` body (TypedDict rendering) is replaced with Pydantic rendering.
- **`Introspector` / `IntrospectionCache`** in `introspector.py` — async schema fetch
  via two RPCs (ir.model + ir.model.fields) + conditional selection fetch. CONSUMED
  unchanged by the CLI layer.
- **`FieldSchema` / `ModelSchema`** in `types.py` — typed dataclasses that `Introspector`
  returns and `CodeGenerator` consumes. CONSUMED unchanged.
- **`config_from_env()`** in `packages/godoo-client/src/godoo/client/config.py` —
  reads `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`; returns `OdooClientConfig`.
  CONSUMED by the CLI to build the client.
- **`OdooBaseModel`** in `packages/godoo-client/src/godoo/client/_pydantic_transform.py`
  — the base class generated files must subclass. CONSUMED (not modified) by the emitter.
- **`Ref[T]`** in `packages/godoo-client/src/godoo/client/typed.py` — the many2one
  reference type emitted in generated files. CONSUMED (not modified).
- **`OdooModel` Protocol** in `packages/godoo-client/src/godoo/client/typed.py` —
  the dispatch protocol requiring `__odoo_model__: ClassVar[str]`. Generated models
  structurally satisfy it (no explicit inheritance needed). CONSUMED (not modified).

### Established Patterns

- `from __future__ import annotations` in every new file.
- `TYPE_CHECKING` for `OdooClient` imports in services — same pattern applies to the
  CLI module if it type-annotates the client.
- Identifier validation via `field_name.isidentifier()` already in `codegen.py:170` —
  keep this guard in the Pydantic emitter.
- Logger per module with `logging.getLogger("godoo_introspection.codegen")`.
- `write()` raises `ValueError` if `output_dir` is not an existing directory (T-02-05
  security check) — keep this.

### Integration Points

- **`packages/godoo-introspection/pyproject.toml`** — add `pydantic>=2.13`,
  `typer>=0.26` to `[project.dependencies]`; add `[project.scripts]` table with
  `godoo-introspect = "godoo.introspection.cli:app"` (or equivalent module path).
  This is GREENFIELD — no `[project.scripts]` currently exists.
- **No CLI framework currently installed** in `godoo-introspection`; `typer` is
  greenfield for this package.
- **`Ref[int]` cross-import** — generated files with degraded many2one fields need
  `from godoo.client.typed import Ref` at the top. Files with in-set many2one fields
  also need cross-imports within the generated package.

### Existing TypedDict Infrastructure (to be REMOVED)

- `codegen.py` — `_annotated_field_meta_str()` helper and the TypedDict class body
  in `generate()` are the parts to DELETE; the surrounding scaffold is repurposed.
- `type_mapper.py` — entire file content is replaced (TypedDict `str | Literal[False]`
  style → Pydantic `Optional[str]` style).
- All tests under `packages/godoo-introspection/tests/` that assert TypedDict output
  format, TypedDict imports, `NotRequired`, `Required`, `FieldMeta` embedding, etc.
  These are DELETED in Phase 7 (16 tests per decision D-01).

</code_context>

<specifics>
## Specific Ideas

- **Relation degradation comment format:** `Ref[int]  # res.country` — the trailing
  comment carries the Odoo technical model name so a developer reading generated code
  can easily find what the relation points to and re-run with an expanded `--models`
  set to get a typed cross-reference.
- **fnmatch matching:** `fnmatch.fnmatch(model_name, pattern)` against the Odoo
  technical model name (e.g. `"project.task"`). Patterns like `project.*` match
  `project.task`, `project.project`, etc. Multiple patterns are OR-combined.
- **`--all` implementation:** query `ir.model` with no name filter (or `[("transient",
  "=", False)]` to skip transient models) and generate every result.
- **Credential precedence:** env vars first; explicit CLI flags override. Typer's
  `envvar=` parameter on `Option()` handles this natively.

</specifics>

<deferred>
## Deferred Ideas

- **Accepted tradeoff — loss of zero-dep TypedDict typing:** Replacing the TypedDict
  emitter gives up the zero-dependency, zero-runtime-cost typing of raw `search_read`
  dicts (TypedDict annotated dicts in-place with no Pydantic install). Users who relied
  on INTRO-03 TypedDict output for purely static annotation without any runtime dependency
  lose that option. The tradeoff is explicitly accepted: Pydantic's declarative wire
  transform is more valuable than zero-dep static-only typing for this use case.
- **Nested relational fetch (TYPED-F1):** Generating `Ref[ResCountry]` for `country_id`
  is Phase 7 scope. Generating nested instances (resolving `country_id` to a full
  `ResCountry` object via a second RPC) is deferred to future milestone.
- **Typed write/create paths (TYPED-F2):** `client.create(ModelInstance)` is deferred;
  v1.1 covers typed reads only.
- **Re-generation cadence / schema freshness:** No cache invalidation or "diff and warn"
  is in scope for Phase 7. Re-run the CLI whenever the Odoo schema changes.

</deferred>

---

*Phase: 7-Pydantic CLI Generator*
*Context gathered: 2026-06-01*
