# Feature Landscape

**Domain:** Async Python SDK for Odoo — four-layer stack
**Researched:** 2026-04-10
**Source basis:** PROJECT.md vision, ARCHITECTURE.md (8 existing services), TS odoo-state-manager README (inlined), competitive landscape table (perplexity, 2025/2026)

---

## Layer 1: godoo core (hardening)

The existing client has: authenticate, search, read, search_read, search_count, create, write, unlink, call, safety guard, 8 domain services (accounting, attendance, cdc, mail, modules, properties, timesheets, urls). The hardening milestone locks this API before downstream layers depend on it.

### Table Stakes (must have for v1)

1. **Full CRUD surface** — search, read, search_read, search_count, create, write, unlink already present; must verify all accept `context` kwarg passthrough for Odoo's context dict (lang, allowed_company_ids, etc.).
2. **execute_kw passthrough** — expose a raw `execute_kw(model, method, args, kwargs)` for callers that need non-CRUD methods not covered by helpers. Currently accessible via `client.call()` but not explicitly documented in the public surface.
3. **Context propagation** — `with_context(**ctx)` or equivalent that returns a scoped client where every subsequent call includes the merged context. Critical for multi-language and multi-company scenarios.
4. **Batch / multi-create** — `create` already accepts a single dict; Odoo 16+ allows list-of-dicts for bulk creation. The helper must accept `list[dict]` and return `list[int]`.
5. **Pagination helpers** — `search_read` has `limit`/`offset`; needs an `iter_search_read()` async generator that pages automatically until exhaustion.
6. **Binary field handling** — Odoo returns binary fields as base64 strings. A helper `read_binary(model, id, field) -> bytes` that decodes transparently is expected by callers dealing with attachments.
7. **fields_get access** — `fields_get(model, attributes?)` for callers that need raw field metadata without importing introspection.
8. **Integration test coverage for all 8 services** — each service must have at least one integration test against a real Odoo (via testcontainers) before v1. Currently unit-tested with respx mocks only.
9. **Consistent error taxonomy** — OdooAccessError, OdooValidationError, OdooMissingError, OdooAuthError, OdooNetworkError, OdooTimeoutError, OdooSafetyError all exist; must verify each is raised from the correct site and catches nothing it should not.
10. **aclose / context manager** — `async with OdooClient(...) as client:` pattern for safe connection teardown. `aclose()` exists; `__aenter__`/`__aexit__` may not.
11. **Logout / session teardown** — explicit `logout()` to destroy the Odoo session server-side (calls `/web/session/destroy` or equivalent), not just discards the local token.
12. **Config from env** — `config_from_env()` and `create_client()` already present; confirm prefix support works and is tested.

### Differentiating

- **Safety guard as first-class citizen** — no other Python Odoo client (OdooRPC, aio-odoorpc, odoo-rpc-client) ships a pluggable async confirmation callback before writes. This is the unique differentiator in the core layer.
  - *aio-odoorpc gap*: zero safety layer; every write fires immediately.
  - *OdooRPC gap*: sync only, no safety layer.
- **Typed service tier** — domain services (mail, timesheets, accounting, etc.) with typed dataclass inputs/outputs exist nowhere else in the competitive landscape; all competitors expose raw dict returns with no type contracts.
- **Session-scoped async context** — httpx.AsyncClient pooling with a single session per OdooClient is idiomatic async Python; aio-odoorpc creates a new HTTP session per call in its thin wrapper design.

---

## Layer 2: godoo-introspection

Currently a placeholder package. The core value proposition of godoo depends on shipping this.

### Table Stakes (must have for v1)

1. **fields_get full traversal** — call `fields_get(model)` for every model discovered via `ir.model`; collect all field metadata (type, string, required, readonly, store, related, compute, selection, relation, relation_field, domain, groups).
2. **ir.model enumeration** — iterate all `ir.model` records to discover the model list; filter by `transient=False` for permanent models; expose `model`, `name`, `info` attributes.
3. **ir.model.fields cross-reference** — use `ir.model.fields` as a secondary source to fill gaps not returned by `fields_get` (notably `x_` custom fields, `ttype`, `field_description`, `required`, `readonly`).
4. **Computed/related field tagging** — fields with `compute` or `related` set must be tagged in generated types as read-only; callers must not be tempted to write to them.
5. **Selection field value enumeration** — for `selection` fields, capture all `(key, label)` pairs and emit them as a `Literal[...]` or `Enum` type. Without this, selection fields degrade to `str`.
6. **Many2one / many2many / one2many relation resolution** — emit typed foreign-key references when the related model is also in the generated package; fall back to `int` or `list[int]` when the relation points outside the package scope.
7. **v17+ Properties field support** — `ir.model` in Odoo 17+ includes `_properties_definition` column; generated types must represent `properties` fields as a typed dict keyed by property name, not as `Any`.
8. **Per-instance output package** — the generator emits a standalone Python package (e.g., `odoo_types_myinstance/`) installable via pip/uv, importable as `from odoo_types_myinstance.models.sale_order import SaleOrder`. Package name is configurable.
9. **Re-run / incremental semantics** — re-running the generator against the same instance regenerates from scratch (no partial state); output is deterministic and diffable in git.
10. **TypedDict vs dataclass output option** — `TypedDict` is preferable for dict-shaped Odoo records (returned from `search_read`); `dataclass` for construction helpers. At minimum one mode must be supported; the choice must be documented.
11. **CLI entry point** — `godoo-introspect --url URL --db DB --user USER --password PASS --output ./types` as a one-shot command; reads env vars as fallback.
12. **Handling of missing/unknown field types** — if a field `ttype` is unrecognized (e.g., future Odoo versions add a type), fall back to `Any` and emit a warning rather than crashing.

### Differentiating

- **No other Python Odoo tool generates typed stubs** — OdooRPC, aio-odoorpc, and all competitors work with raw `dict[str, Any]` returns. Per-instance type generation is unique to this stack.
  - *OdooRPC gap*: no introspection, no typing, returns plain dicts.
  - *aio-odoorpc gap*: by design "thin layer", no schema awareness at all.
- **Custom field (`x_`) coverage** — standard Odoo stubs (if they existed) would only cover base modules; introspection captures every custom field, every Studio-added property, every partner-specific extension on that specific database.
- **Properties field typing (v17+)** — the `ir.model` Properties feature (Odoo 17) is completely undocumented in any third-party Python tooling. Being first to generate typed Properties dicts is a concrete differentiator.

---

## Layer 3: godoo-state-manager

Pythonic port of `@marcfargas/odoo-state-manager`. Every primitive in the TS README must have an equivalent. The mapping table below covers all features; each is then separated into table stakes vs differentiating.

### TS Primitive → Python Equivalent Mapping

| TS Primitive | Python Equivalent | Notes |
|---|---|---|
| `resource(model, definition)` | `resource(model: str, **fields) -> ResourceDefinition` dataclass | kwargs instead of object literal |
| `_ref=lookup(...)` | `ref=lookup(...)` kwarg on `resource()` | `ref` avoids underscore dunder collision |
| `removeUnmanaged` per-field flag | `remove_unmanaged: bool` kwarg on relational field value | snake_case |
| Nested `resource()` inside relational field | Same — `resource()` returns a dataclass, nestable | |
| Collections as plain arrays | Collections as plain `list[ResourceDefinition]` | |
| `lookup(model, domain)` | `lookup(model: str, domain: ...) -> LookupRef` dataclass | |
| Object shorthand `{ key: value }` | Dict shorthand `{"key": value}` → expands to `[["key", "=", value]]` | |
| Raw domain array | `list[list]` domain passed directly | |
| `lookup` must resolve to exactly 1 | Same; multi-match raises `StatePlanError` | |
| `lookup` as `_ref`: not found → create | Same: `ref=lookup(...)` not found → create mode | |
| `lookup` as field value: not found → error | Same; raises `StatePlanError` at resolve phase | |
| `lookup` inside many2many arrays | `list[LookupRef]`; each resolved independently | |
| `model(model, policy)` | `model_policy(model: str, policy: ModelPolicy) -> ModelPolicyDefinition` | `model` is a Python builtin; rename to `model_policy` |
| `removeOrphans` policy | `ModelPolicy.REMOVE_ORPHANS` enum value | |
| `archiveOrphans` policy | `ModelPolicy.ARCHIVE_ORPHANS` enum value | requires `active` field |
| `md(source)` | `md(source: str) -> ContentMarker` | renders Markdown to HTML at transform phase |
| `mdFile(path, opts?)` | `md_file(path: str | Path, *, css: str | Path | None = None, inline_css: bool = True, strip_frontmatter: bool = True) -> ContentMarker` | snake_case, Path-typed |
| `translated(default, translations?)` | `translated(default: str, **lang_overrides: str) -> TranslatedValue` | `translated("Hello", fr_FR="Bonjour")` |
| `withCss(html, cssFile, opts?)` | `with_css(html: str, css: str | Path) -> ContentMarker` | |
| `html(value, opts?)` | `html(value: str, *, verify: bool = True) -> ContentMarker` | optional wrapper |

### Pipeline Phase → Python Equivalent Mapping

| TS Phase | Python Phase | Notes |
|---|---|---|
| Evaluate — load `.ts` files, collect `resource()` / `model()` exports | **Evaluate** — load `.py` definition files, collect exported `resource()` / `model_policy()` calls | Python module import; no compilation step |
| Resolve — batch `lookup()` via `searchRead` | **Resolve** — batch `lookup()` via `client.search_read()`; grouped by model for minimal RPC calls |
| Introspect — dependency graph, module requirements, field metadata | **Introspect** — build dependency graph from nested resources; validate required fields; fetch field metadata via `fields_get()` | |
| Transform — Markdown to HTML, CSS inline, extract translations, sanitization | **Transform** — `markdown` library for Md→HTML; `premailer` or `cssutils` for CSS inlining; collect `translated()` pairs; HTML sanitization via `bleach` or `nh3` |
| Diff — desired vs actual per-field including per-language translation diffs | **Diff** — fetch current records via `search_read()`; compare field-by-field; handle `ir.translation` or Odoo 16+ inline translation format | most complex phase |
| Plan — ordered operations with sanitization warnings | **Plan** — return `Plan` dataclass with `operations: list[Operation]`, `warnings: list[Warning]`; operations ordered by dependency level |
| Apply — execute level by level, write translations per-language | **Apply** — execute operations level by level using `client.create/write/unlink`; write translations via `client.call("res.lang", "set_translation", ...)` or `ir.translation.create()` depending on Odoo version |
| Verify — re-run plan after apply, report drift | **Verify** — re-run diff phase after apply; if plan is not empty, report as `VerifyError` |

### Table Stakes (must have for v1)

1. **`resource()` primitive** — declare a single managed record with model name and field values; returns a `ResourceDefinition` dataclass.
2. **`lookup()` primitive** — read-only reference to an existing record; dict shorthand `{"key": value}` and raw domain both supported.
3. **`lookup()` as `ref=` on resource** — found → update mode; not found → create mode.
4. **`lookup()` as field value** — not found → `StatePlanError` raised at resolve phase, not at apply time.
5. **`lookup()` inside many2many list** — each element of a `list[LookupRef]` resolved independently.
6. **`model_policy()` primitive** — model-level cleanup policy applied after all resources; accepts `REMOVE_ORPHANS` or `ARCHIVE_ORPHANS`.
7. **`remove_unmanaged` per relational field** — on one2many: unlink unlisted children; on many2many: unlink associations for unlisted records.
8. **Evaluate phase** — load `.py` definition files from a directory; collect all `ResourceDefinition` and `ModelPolicyDefinition` objects exported at module level.
9. **Resolve phase** — batch-resolve all `LookupRef` instances; group by model; single `search_read` per model; cache results.
10. **Introspect phase** — build dependency graph from nested resources; determine execution order; fetch `fields_get()` metadata for validation.
11. **Transform phase** — `md()` renders Markdown to HTML; `md_file()` reads from disk; `with_css()` inlines CSS; `translated()` extracts per-language pairs; `html()` optionally sanitizes.
12. **Diff phase** — compare desired state to actual records fetched via `search_read()`; per-field comparison; detect creates, updates, deletes.
13. **Per-language translation diff** — detect translation changes separately from field value changes; handle Odoo 16+ inline translation format (`{"en_US": "...", "fr_FR": "..."}`) vs `ir.translation` table (Odoo ≤15).
14. **Plan phase** — return ordered `Plan` dataclass; `plan.is_empty` boolean; operations sorted by dependency level so parent resources are created before children.
15. **Apply phase** — execute operations level by level; write translations per-language; collect applied/failed counts; return `ApplyResult`.
16. **Verify phase** — re-run diff after apply; report drift if plan is non-empty; return `VerifyResult`.
17. **`removeOrphans` policy execution** — after applying resources, call `unlink()` on records in the model that are not referenced by any `resource()` declaration.
18. **`archiveOrphans` policy execution** — as above but `write({"active": False})` instead of `unlink()`; guard: verify model has `active` field via `fields_get()` before attempting.
19. **Sanitization warnings** — HTML content markers that contain potentially dangerous tags emit warnings in the plan; apply continues but warnings are surfaced.
20. **CLI: `godoo-state plan [--dir .]`** — show plan; exit 0 if clean, exit 2 if changes pending.
21. **CLI: `godoo-state apply [--dir .]`** — show plan, prompt for confirmation, apply; exit 0 on success.
22. **CLI: `godoo-state diff [--dir .]`** — detect drift; exit 0 if clean, exit 2 if drift.
23. **CLI: `godoo-state init [dir]`** — scaffold a new project with example definition file and `.env` template.
24. **Library API: `plan(dir, client) -> Plan`** — programmatic access to plan phase.
25. **Library API: `apply(dir, client) -> ApplyResult`** — programmatic access to apply.
26. **Library API: `diff(dir, client) -> DriftReport`** — programmatic access to drift detection.
27. **Library API: `format_plan(plan: Plan) -> str`** — formatted human-readable plan string.
28. **Lower-level exports** — `evaluate()`, `resolve_lookups()`, `domain_to_tuples()` accessible for advanced callers.
29. **Auth via env vars** — ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD read by CLI; same as godoo core `config_from_env()`.

### Differentiating

- **Only declarative Python Odoo state management tool** — no other Python package in the competitive landscape offers plan/apply/diff semantics for Odoo configuration records. Every competitor is an RPC client with no state concept.
  - *OdooRPC gap*: CRUD client, no state; sync-only.
  - *aio-odoorpc gap*: async CRUD client, no state.
- **Translation-aware diffing** — detecting and applying per-language field translations as first-class operations is not present in any competing tool.
- **`archiveOrphans` as a safe alternative to deletion** — treating `active=False` as a soft-delete cleanup policy is a domain-specific differentiator for Odoo operators who cannot hard-delete records due to audit/accounting constraints.
- **Markdown and CSS authoring for HTML fields** — no other Odoo tooling provides Markdown-to-HTML rendering or CSS inlining for Odoo HTML fields; this directly addresses the pain of managing Odoo's HTML-heavy portal/website content programmatically.

---

## Layer 4: godoo-moduleX

Live x-module builder over RPC. No .zip, no deployment pipeline. The module exists only as records in the target DB.

### Table Stakes (must have for v1)

1. **Declare x-models (`ir.model`)** — define a new custom model by name, description, and model technical name (e.g., `x_project_budget`); creates `ir.model` record, sets `state='manual'`.
2. **Declare x-fields on new models (`ir.model.fields`)** — add fields to a declared x-model: field name, ttype (char, integer, float, boolean, date, datetime, text, html, many2one, many2many, one2many, selection, binary), string label, required, readonly, index.
3. **Declare x-fields on existing models** — same as above but targeting `res.partner`, `sale.order`, etc.; creates `ir.model.fields` records on models godoo did not declare.
4. **Selection field values** — for `ttype=selection` fields, declare `(key, label)` pairs via `ir.model.fields.selection` or the `selection` attribute on the field definition.
5. **Many2one relation target** — for `ttype=many2one`, specify `relation` (target model technical name) and `on_delete` policy (set_null, restrict, cascade).
6. **Many2many relation** — for `ttype=many2many`, specify `relation` (m2m table name), `column1`, `column2`, and target model.
7. **One2many relation** — specify `relation` model and `relation_field` (the many2one on the other side).
8. **Form view declaration (`ir.ui.view`)** — declare a form view by: model, arch (XML string or structured definition), priority; creates `ir.ui.view` record with `type='form'`.
9. **Tree/list view declaration** — same as form but `type='tree'` (or `list` in Odoo 17+).
10. **View inheritance** — declare an `ir.ui.view` with `inherit_id` pointing to an existing view's `xml_id`; arch uses XPath or position-based inheritance syntax.
11. **Action declaration (`ir.actions.act_window`)** — declare a window action: name, res_model, view_mode, domain, context, target; creates `ir.actions.act_window` record.
12. **Menu declaration (`ir.ui.menu`)** — declare menu items: name, parent (by xml_id or LookupRef), action (by xml_id or LookupRef), sequence, groups; creates `ir.ui.menu` record.
13. **ACL declaration (`ir.model.access`)** — declare access rules: name, model_id (by model name), group_id (by xml_id), perm_read/write/create/unlink booleans; creates `ir.model.access` record.
14. **Record rules (`ir.rule`)** — declare domain-based record rules: name, model_id, domain_force (string domain), groups (list by xml_id), global flag; creates `ir.rule` record.
15. **Seed data** — declare initial data records (any model) as part of the x-module; applied after structural records; uses `resource()` from state-manager semantics internally.
16. **Idempotent re-run via xml_id** — every declared record is identified by a module-qualified xml_id stored in `ir.model.data`; re-running the push updates existing records instead of creating duplicates.
17. **Module listing** — `list_modules() -> list[XModuleInfo]` enumerates x-modules previously deployed to the target instance by this tool (identified by a naming convention on `ir.model.data`).
18. **Module update** — `push(module)` re-runs the full declaration against the instance; adds new records, updates changed records, leaves unmentioned records untouched by default.
19. **Module removal** — `remove(module_name)` deletes all records created by the x-module in correct dependency order: record rules → ACLs → menus → actions → views → fields → models; uses `unlink()` in reverse-dependency sequence to avoid FK constraint failures.
20. **`ir.model.data` bookkeeping** — every created record is registered in `ir.model.data` with `module=<xmodule_name>`, `name=<record_xml_id>`, `model=<model>`, `res_id=<id>`; this is the source of truth for idempotency and removal.
21. **Dependency validation** — before pushing, verify that all `relation` targets for Many2one/Many2many fields exist in `ir.model`; raise `XModuleValidationError` if a referenced model does not exist on the target instance.
22. **CLI: `godoo-module push <module_dir>`** — push an x-module definition directory to the configured Odoo instance.
23. **CLI: `godoo-module list`** — list deployed x-modules.
24. **CLI: `godoo-module remove <module_name>`** — remove an x-module and all its records.
25. **Library API: `push(module: XModuleDef, client: OdooClient) -> PushResult`** — programmatic push.

### Differentiating

- **No .zip, no deployment pipeline, no server restart** — every other mechanism for adding custom models to Odoo requires a filesystem module (even OCA modules, Studio exports, or hand-written addons) and a module upgrade/install cycle. godoo-moduleX mutates the DB directly over RPC — no deployment step.
  - *Odoo Studio gap*: Studio is UI-only, not programmatically drivable via RPC, and exports to a .zip that requires deployment.
  - *All Python RPC client competitors*: none model the concept of a module at all; they are raw CRUD wrappers.
- **Correct removal order** — deleting a custom module requires unregistering records in reverse dependency order (rules → ACLs → menus → actions → views → fields → models) to avoid FK constraint failures. No existing tool handles this automatically.
- **xml_id-based idempotency** — re-running the same module definition against an already-configured instance is safe and convergent. This is the same guarantee Odoo's own module system provides (via `noupdate`) but achieved purely over RPC without a module manifest.
- **Explicit out-of-scope boundary** — workflows, wizards, server actions requiring Python code are explicitly not in scope (see PROJECT.md); this keeps the surface credible and avoids shipping a partial, broken implementation of a much harder feature.

---

## Feature Dependencies Across Layers

```
godoo core (hardened)
  └── godoo-introspection (needs fields_get, search_read on ir.model/ir.model.fields)
  └── godoo-state-manager (needs create/write/unlink, context propagation, search_read)
        └── godoo-moduleX (uses state-manager resource() for seed data; uses client directly for structural records)
```

Key ordering constraints:
- godoo core must lock its API before state-manager and moduleX are built against it.
- godoo-introspection can be developed in parallel with state-manager (both only need stable search_read/fields_get).
- godoo-moduleX depends on state-manager for seed data semantics; it must come after state-manager's `resource()` and pipeline are stable.

---

## Competitive Gap Summary

| Feature | godoo | aio-odoorpc | OdooRPC | odoo-rpc-client |
|---|---|---|---|---|
| Async | YES | YES | NO | NO |
| Typed returns | YES (dataclasses) | NO (raw dict) | NO | NO |
| Safety guard | YES | NO | NO | NO |
| Per-instance typed stubs | YES (introspection) | NO | NO | NO |
| Declarative state (plan/apply/diff) | YES (state-manager) | NO | NO | NO |
| Translation-aware diffing | YES | NO | NO | NO |
| Live x-module builder | YES (moduleX) | NO | NO | NO |
| Active maintenance (2025/2026) | YES | LOW | YES (OCA) | LOW (Odoo 14) |

---

## Anti-Features (Explicitly Out of Scope)

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| Sync client API | Doubles maintenance surface for solo maintainer | Callers use `asyncio.run()` |
| Generic static Odoo type stubs (.pyi) | Every instance is customized; stubs lie | Use godoo-introspection against real target |
| Data migration / bulk import tooling | Different product category entirely | Out of scope; use Odoo's import UI or a dedicated ETL tool |
| Odoo.sh-specific API wrappers | Fragments the audience; generic RPC works everywhere | Stick to standard JSON-RPC |
| Server actions / Python wizard logic in moduleX | Requires Python code that cannot be expressed via RPC | Out of scope; these need a real addon with code deployment |
| 1:1 TS API surface parity | Forces TS idioms into Python; makes both worse | Same semantics, Python-native surface (snake_case, dataclasses, kwargs) |
| Pydantic models | Adds runtime validation overhead not needed at SDK layer | Dataclasses; callers add their own validation if needed |

---

## MVP Recommendation Per Layer

**godoo core:** Items 1-12 above; integration tests are the gate. Do not ship introspection or state-manager until core has full integration test coverage.

**godoo-introspection:** Items 1-11 are v1; Properties support (item 7) may slip to v1.1 if Odoo 17 schema is complex — but must be flagged as a known gap, not silently omitted.

**godoo-state-manager:** All 29 items are table stakes — the TS README defines the complete contract and a partial port would be confusing. Items most likely to be harder in Python: per-language translation diff (item 14) because Odoo 16 changed the translation storage format; prioritize Odoo 17 format and add ≤15 support as a flag.

**godoo-moduleX:** Items 1-25 are all required for the "live x-module" value proposition to hold. The minimum viable slice is: declare model + fields + form view + ACL + idempotent push/remove. Menus, actions, record rules, and seed data can follow in iteration 2 if necessary, but the xml_id bookkeeping (item 16) must be in from the start — retrofitting it later breaks all existing deployments.

---

*Feature analysis confidence:*
- *godoo core:* HIGH — code is in-repo; gaps identified by reading actual client.py and service files.
- *godoo-introspection:* MEDIUM-HIGH — Odoo fields_get and ir.model API are stable and well-documented; Properties field format for v17+ is partially from training data, flag for verification against live Odoo 17 during implementation.
- *godoo-state-manager:* HIGH — TS README is the authoritative spec; every primitive mapped.
- *godoo-moduleX:* MEDIUM — ir.model/ir.model.fields/ir.model.data mutation patterns are known; correct deletion order for constraint safety needs verification against a real instance; FK behavior varies by Odoo version.
