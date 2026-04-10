# Requirements: godoo

**Defined:** 2026-04-10
**Core Value:** Typing is generated per-instance via introspection, never assumed. The four-layer stack (client + introspection + state-manager + moduleX) composes around that premise.

---

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases. Odoo version support: **v17 + v18 only**.

### Core Client Hardening (CORE)

- [ ] **CORE-01**: Every public client method accepts a `context` kwarg that is merged with the session context and forwarded to Odoo (`lang`, `allowed_company_ids`, `tz`, etc.)
- [ ] **CORE-02**: `client.with_context(**ctx)` returns a scoped `OdooClient` where every subsequent call merges the provided context into requests
- [ ] **CORE-03**: `client.create()` accepts `dict | list[dict]` and returns `int | list[int]` respectively (bulk create via Odoo 16+ list syntax)
- [ ] **CORE-04**: `client.iter_search_read(model, domain, fields, batch_size=200)` is an async generator that auto-paginates until exhaustion
- [ ] **CORE-05**: `client.read_binary(model, record_id, field) -> bytes` decodes Odoo's base64 binary fields transparently
- [ ] **CORE-06**: `client.fields_get(model, attributes=None)` exposes raw field metadata without requiring the introspection package
- [ ] **CORE-07**: `client.execute_kw(model, method, args, kwargs)` is documented as the escape hatch for non-CRUD Odoo methods
- [ ] **CORE-08**: `client.ref(xml_id)` resolves an `ir.model.data` xml_id to `(model, record_id)` via a single RPC call
- [ ] **CORE-09**: `OdooClient` implements `__aenter__` / `__aexit__` so `async with OdooClient(...) as client:` is idiomatic
- [ ] **CORE-10**: `client.logout()` calls Odoo's session-destroy endpoint server-side (not just discarding the local token)
- [ ] **CORE-11**: All 8 existing domain services (accounting, attendance, cdc, mail, modules, properties, timesheets, urls) have at least one integration test against a real Odoo instance via godoo-testcontainers
- [ ] **CORE-12**: Error taxonomy audit — verify `OdooAccessError`, `OdooValidationError`, `OdooMissingError`, `OdooAuthError`, `OdooNetworkError`, `OdooTimeoutError`, `OdooSafetyError` are each raised from the correct RPC failure site with actionable messages
- [ ] **CORE-13**: Safety guard callback can be async; `async def confirm(op: WriteOp) -> bool` contract is documented
- [ ] **CORE-14**: pytest-asyncio pinned to `>=1.0` in every package, full test suite passes on the upgrade
- [ ] **CORE-15**: Client public API is frozen and documented before any downstream package depends on it; any change after the freeze requires an explicit version bump

### Introspection & Type Generation (INTRO)

- [ ] **INTRO-01**: `godoo-introspect` CLI command accepts `--url --db --user --password --output PATH [--format typeddict|dataclass]` with env var fallback (`ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`)
- [ ] **INTRO-02**: CLI emits a standalone Python package at `PATH/` that is importable and pip/uv installable (has its own `pyproject.toml`)
- [ ] **INTRO-03**: Generator enumerates all non-transient `ir.model` records and cross-references `ir.model.fields` to catch `x_` custom fields missed by `fields_get`
- [ ] **INTRO-04**: `--format typeddict` emits one `TypedDict` per model matching `search_read` return shape
- [ ] **INTRO-05**: `--format dataclass` emits one `@dataclass` per model with optional fields reflecting Odoo's `required` flag
- [ ] **INTRO-06**: Selection fields emit `Literal[...]` types listing every valid selection value from the instance
- [ ] **INTRO-07**: `compute` and `related` fields are tagged as read-only (via comment or wrapper type) in generated output
- [ ] **INTRO-08**: Many2one / many2many / one2many fields emit typed references to the target model when that model is in the generated package; fall back to `int` / `list[int]` otherwise
- [ ] **INTRO-09**: Odoo v17+ Properties fields (`ir.model._properties_definition`) are represented as typed property dicts, not `Any`
- [ ] **INTRO-10**: Re-running the generator against the same instance produces deterministic, git-diffable output
- [ ] **INTRO-11**: Unknown `ttype` values fall back to `Any` with a warning on stderr, not a crash
- [ ] **INTRO-12**: Generated package includes a top-level `__version__` + instance fingerprint (Odoo version, DB name, timestamp) to detect drift between generated types and runtime schema

### State Manager (STATE)

DSL primitives — Pythonic port of `@marcfargas/odoo-state-manager`. Every TS primitive has a Python equivalent.

- [ ] **STATE-01**: `resource(model: str, *, ref=None, remove_unmanaged=False, **fields)` declares a managed record; returns a `ResourceDefinition` dataclass
- [ ] **STATE-02**: `lookup(model: str, domain=None, **shorthand)` declares a read-only reference; accepts shorthand kwargs (`email='x'`) or raw domain list; returns a `LookupRef`
- [ ] **STATE-03**: `model_policy(model: str, *, remove_orphans=False, archive_orphans=False)` declares model-level cleanup (renamed from TS `model()` to avoid Python builtin collision)
- [ ] **STATE-04**: `remove_unmanaged=True` on a field deletes unlisted children for one2many and unlinks associations for many2many — different destructiveness documented explicitly
- [ ] **STATE-05**: `md(source: str)` renders inline Markdown to HTML via markdown-it-py at plan time
- [ ] **STATE-06**: `md_file(path, *, css=None, inline_css=True, strip_frontmatter=True)` loads a Markdown file, optionally inlines CSS via css-inline, strips frontmatter by default
- [ ] **STATE-07**: `translated(default, **languages)` declares per-language values; first positional arg is always the instance default language
- [ ] **STATE-08**: `with_css(html: str, css_file: str, *, inline=True)` injects CSS into raw HTML
- [ ] **STATE-09**: `html(value: str, *, verify=True)` wraps raw HTML, `verify=False` suppresses sanitization warnings
- [ ] **STATE-10**: Nested `resource()` calls inside relational fields work (no wrapping needed)
- [ ] **STATE-11**: `lookup()` works inside many2many arrays; each element resolves independently

Pipeline — 8 phases, one module per phase.

- [ ] **STATE-12**: **Evaluate** phase loads user state `.py` files via `importlib`; side-effect registration into a module-level registry
- [ ] **STATE-13**: **Resolve** phase batch-resolves all `lookup()` markers via `search_read`; fails fast on multi-match
- [ ] **STATE-14**: **Introspect** phase fetches field metadata; degrades gracefully if `godoo-introspection` is not installed (skips validation, warns)
- [ ] **STATE-15**: **Transform** phase renders Markdown, inlines CSS, extracts translations, runs nh3 sanitization checks
- [ ] **STATE-16**: **Diff** phase compares desired vs actual including per-language translation diffs on inline-JSON HTML fields (v17+ inline format only)
- [ ] **STATE-17**: **Plan** phase emits ordered operations with level assignments from the dependency graph; surfaces sanitization warnings without blocking
- [ ] **STATE-18**: **Apply** phase executes operations level by level; writes translations per-language via `context={'lang': ...}`
- [ ] **STATE-19**: **Verify** phase re-runs plan after apply; any remaining drift is reported as an error

Public API.

- [ ] **STATE-20**: `plan(dir, client)`, `apply(dir, client)`, `diff(dir, client)`, `format_plan(plan)` are the public entry points
- [ ] **STATE-21**: `evaluate()`, `resolve_lookups()`, `domain_to_tuples()` are exposed as lower-level helpers
- [ ] **STATE-22**: Every resource is tracked via an `ir.model.data` xml_id from creation — idempotent re-runs, safe removal
- [ ] **STATE-23**: `godoo-state plan / apply / diff / init [DIR]` CLI via typer; auth from env vars; exit 0 clean / 2 changes-or-drift
- [ ] **STATE-24**: `ir.rule` domain strings are AST-validated before being sent (security boundary for Python eval)

### moduleX (MODX)

Record types supported in v1: `ir.model`, `ir.model.fields`, `ir.ui.view`, `ir.ui.menu`, `ir.actions.act_window`, `ir.model.access`, `ir.rule`.

- [ ] **MODX-01**: `XModule(name, author=None)` declares a named logical x-module; records registered to it carry an xml_id prefixed with the module name
- [ ] **MODX-02**: `x_model(name, *, state='manual', fields=[...])` creates a custom model via `ir.model` with the required `x_` prefix and `state='manual'` enforced
- [ ] **MODX-03**: `x_field(model, name, ttype, **opts)` adds an `x_`-prefixed field to an existing or new model via `ir.model.fields`; selection values serialize as Python-tuple-strings (not JSON)
- [ ] **MODX-04**: `view(model, arch, *, inherit_from=None, mode='primary')` creates `ir.ui.view` records; `inherit_from` + `mode='extension'` for XPath view patches
- [ ] **MODX-05**: `menu(name, *, parent=None, action=None, sequence=10)` creates `ir.ui.menu` entries
- [ ] **MODX-06**: `action(name, model, *, view_mode='list,form', domain=None)` creates `ir.actions.act_window` records
- [ ] **MODX-07**: `acl(model, group, *, read=True, write=False, create=False, unlink=False)` creates `ir.model.access` rules; `group=None` is rejected (no global ACLs)
- [ ] **MODX-08**: `record_rule(model, group, *, domain, perm_read=True, ...)` creates `ir.rule` records; domain is AST-validated
- [ ] **MODX-09**: `module.push(client)` creates or updates all records in dependency order: models → fields → views → menus → actions → ACLs → rules
- [ ] **MODX-10**: `module.remove(client)` deletes all records in **strict reverse order**: menus → actions → views → rules → ACLs → fields → models
- [ ] **MODX-11**: `module.diff(client)` reports drift between declared state and live database state
- [ ] **MODX-12**: `XModule.list(client)` enumerates all x-modules currently deployed to the instance
- [ ] **MODX-13**: Registry reload latency under multi-worker Odoo is documented; `push()` waits or warns when workers are out of sync
- [ ] **MODX-14**: Every pushed record has a stable `ir.model.data` xml_id so re-runs are idempotent and removal is reliable
- [ ] **MODX-15**: moduleX is implemented as a DSL layer that emits `list[Resource]` consumed by `godoo-state-manager`'s plan/apply/diff pipeline (no parallel engine)
- [ ] **MODX-16**: Integration tests cover: create x-module with 1 model + 2 fields + 1 view + 1 menu + 1 ACL; update a field; remove the whole module; verify no orphans in `ir.model.data`

### Documentation & Examples (DOCS)

- [ ] **DOCS-01**: Top-level `README.md` explains the four-layer stack, the core value proposition (per-instance typing), and a 5-minute "hello Odoo" example
- [ ] **DOCS-02**: Each package has its own README with install, quick start, API surface, and links upward
- [ ] **DOCS-03**: End-to-end walkthrough: generate types → declare a `res.partner.category` via state-manager → push an x-module that adds a `x_custom_field` to `res.partner` → verify with a typed query
- [ ] **DOCS-04**: `CHANGELOG.md` reflects every v1 requirement as it ships
- [ ] **DOCS-05**: TS `odoo-state-manager` → Python state-manager migration note for TS toolbox users

---

## v2 Requirements

Deferred to future releases. Tracked but not in current roadmap.

### moduleX extensions (v1.1)
- **MODX-20**: Seed data — initial records inside x-models managed as part of the `XModule` declaration
- **MODX-21**: `ir.cron` scheduled jobs as an x-module record type
- **MODX-22**: `ir.sequence` number sequences as an x-module record type
- **MODX-23**: `ir.server.action` server actions (requires Python code — design constraint)

### Extended Odoo support (v2)
- **CORE-20**: Odoo v15 + v16 support, including `ir.translation` legacy translation writes
- **CORE-21**: Odoo v19+ `pyodoo-client` compatibility layer for post-JSON-RPC deprecation

### Advanced introspection (v2)
- **INTRO-20**: Incremental / diffed regeneration (update only changed models)
- **INTRO-21**: mypy plugin for compile-time validation of domain tuples against generated field types

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Sync client API | godoo is async-only; dual API doubles maintenance for a solo maintainer. `asyncio.run()` is the escape hatch |
| Data migration tooling | state-manager is for declarative config, not bulk data imports or version upgrades |
| Odoo.sh-specific integrations | generic RPC works against any Odoo; tying to Odoo.sh fragments the audience |
| Workflows / wizards / server actions in moduleX | Require Python code not expressible via RPC; out of moduleX charter |
| Static generic Odoo type stubs | Every instance is customized; generic stubs lie. Types come from introspection or not at all |
| 1:1 TS API parity | Forcing TS ergonomics into Python makes both worse — same semantics, Pythonic surface |
| Odoo v15 and v16 support | v1 scoped to v17+ to drop `ir.translation` legacy path and use Properties fields directly |
| Seed data in moduleX v1 | Deferred to v1.1 — adds scope without changing the differentiating story |

## Traceability

Empty until roadmap creation populates the phase mapping.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01..15 | TBD (Phase 1) | Pending |
| INTRO-01..12 | TBD (Phase 2) | Pending |
| STATE-01..24 | TBD (Phase 3) | Pending |
| MODX-01..16 | TBD (Phase 4) | Pending |
| DOCS-01..05 | TBD (Phase 5) | Pending |

**Coverage (pre-roadmap):**
- v1 requirements: **72 total** (15 CORE + 12 INTRO + 24 STATE + 16 MODX + 5 DOCS)
- Mapped to phases: 0
- Unmapped: 72 ⚠️ (roadmap will resolve)

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after initial definition*
