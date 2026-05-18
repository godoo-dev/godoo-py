# Research Summary — godoo v1

**Synthesized:** 2026-04-10
**Source files:** STACK.md (238), FEATURES.md (256), ARCHITECTURE.md (554), PITFALLS.md (781)

---

## Elevator Pitch

godoo v1 is a four-layer async Python SDK for Odoo — RPC client hardening, per-instance type generation via introspection, Pythonic declarative state management, and a live Studio-style x-module builder — where *every* layer is differentiated against the existing Python ecosystem. No current Python Odoo tool ships typed returns, per-instance stubs, declarative plan/apply state, or live x-module creation.

## Stack Decisions

**Locked (validated for 2026):** Python 3.14 · asyncio · httpx · uv workspace · hatchling · ruff · mypy --strict · dataclasses · pytest-asyncio · respx · testcontainers-python.

**Action item on locked stack:** Upgrade `pytest-asyncio >= 1.0` (1.3.0, Nov 2025) as first commit of Phase 1. Existing `asyncio_default_fixture_loop_scope = "session"` is forward-compatible.

**New runtime deps (per layer):**
- **godoo-introspection**: `jinja2` (template-driven codegen; libcst ruled out — wrong tool), `typer` (CLI)
- **godoo-state-manager**: `nh3 0.3.4+` (Rust HTML sanitizer, bleach deprecated), `markdown-it-py 4.0.0+` (CommonMark compliance > mistune speed), `css-inline 0.20.2+` (Rust CSS inliner, premailer ruled out), `typer` (CLI)
- **godoo-moduleX**: **no new runtime deps** — pure RPC over existing transport

## Table-Stakes Features by Layer

### Core (hardening)
- Full CRUD with `context` kwarg passthrough on every method
- `execute_kw` raw passthrough for non-CRUD methods
- `with_context(**ctx)` scoped-client helper (multi-language/multi-company)
- Batch `create(list[dict]) -> list[int]` (Odoo 16+ bulk)
- `iter_search_read()` async generator with auto-pagination
- `read_binary(model, id, field) -> bytes` base64-decoding helper
- `fields_get()` accessor (without importing introspection)
- Integration tests for all 8 services against real Odoo via testcontainers
- Full error taxonomy audit (Access/Validation/Missing/Auth/Network/Timeout/Safety)
- `async with OdooClient(...)` — `__aenter__` / `__aexit__` if missing
- Explicit `logout()` — destroys Odoo session server-side

### Introspection
- `fields_get` traversal over every `ir.model` (filter `transient=False`)
- Cross-reference `ir.model.fields` for `x_` customs and gaps
- Tag `compute`/`related` fields as read-only in generated types
- Selection fields → `Literal[...]` / `Enum` (not `str`)
- Many2one/many2many/one2many emit typed refs when target in package
- **v17+ Properties field support** (open question: schema location)
- Per-instance output package (e.g., `odoo_types_myinstance/`), pip-installable
- Deterministic re-run (regenerate from scratch, diffable)
- `godoo-introspect --url ... --output ./types` CLI
- Graceful unknown-ttype fallback (warn, emit `Any`)

### State-manager (every TS primitive ported)
| TS | Python | Notes |
|---|---|---|
| `resource(model, def)` | `resource(model: str, **fields)` | kwargs instead of object literal |
| `_ref=lookup(...)` | `ref=lookup(...)` | avoids dunder collision |
| `removeUnmanaged` | `remove_unmanaged` | snake_case |
| `lookup(model, domain)` | `lookup(model: str, domain)` | dataclass |
| `model(m, policy)` | **`model_policy(m, policy)`** | `model` is Python builtin; rename required |
| `removeOrphans` / `archiveOrphans` | `remove_orphans` / `archive_orphans` | |
| `md(source)` | `md(source)` | markdown-it-py |
| `mdFile(path, opts)` | `md_file(path, *, css, inline_css, strip_frontmatter)` | |
| `translated(default, map)` | `translated(default, **languages)` | |
| `withCss(html, cssFile)` | `with_css(html, css_file, *, inline)` | |
| `html(value, opts)` | `html(value, *, verify)` | |
| Pipeline: evaluate→resolve→introspect→transform→diff→plan→apply→verify | Same 8 phases, one module per phase | |
| Library API: `plan/apply/diff/formatPlan` | `plan/apply/diff/format_plan` | |
| CLI: `plan/apply/diff/init` | Same via typer | |

### moduleX
- Declare `x_` models with `state='manual'` via `ir.model` + `ir.model.fields`
- Declare `x_` fields on existing models (same mechanism)
- Views (forms/lists/kanbans) via `ir.ui.view` with `arch_db`, inheritance via `inherit_id` + `mode`
- Menus via `ir.ui.menu` + actions via `ir.actions.act_window`
- ACLs via `ir.model.access` (`group_id` + perm bits)
- Record rules via `ir.rule` (Python domain strings)
- Seed data records in the x-models
- **`ir.model.data` xml_id bookkeeping MUST be in from first commit** — source of truth for idempotency and correct removal
- x-module listing, update, and removal (reverse deletion order: menus → actions → views → rules → ACLs → fields → models)

## Differentiating Features

- **Only Python tool with a typed client** — OdooRPC/aio-odoorpc/odoo-rpc-client/erppeek all return raw `dict[str, Any]`. godoo ships dataclass/TypedDict returns.
- **Only Python tool with per-instance codegen** — every Odoo instance is customized; generic stubs lie. Introspection produces types that match the specific database.
- **Only Python tool with declarative state management** — no Terraform-for-Odoo equivalent in Python exists.
- **Only Python tool with live x-module creation** — Odoo Studio is the closest comparable thing, and it's a web UI not a library.
- **First-class safety guard** — pluggable async confirmation callback before writes. No other Python client has this.
- **Typed domain services** — 8 services (accounting, attendance, cdc, mail, modules, properties, timesheets, urls) with dataclass I/O. Nothing in the competitive landscape is close.

## Architectural Decisions

**Package DAG (acyclic):**
```
godoo (core leaf)
  ├─ godoo-testcontainers  [test infra, depends on godoo]
  ├─ godoo-introspection   [depends on godoo]
  ├─ godoo-state-manager   [depends on godoo; godoo-introspection = optional-dep]
  └─ godoo-moduleX         [depends on godoo-state-manager]
```

**Load-bearing decisions:**
1. **state-manager's introspection dep is optional** — via `[project.optional-dependencies]`. Users without generated types get a degraded `introspect` phase (skip validation, warn). Lets state-manager ship before introspection is complete.
2. **moduleX re-uses state-manager's pipeline** — does NOT own a parallel engine. moduleX is a DSL layer emitting `list[Resource]` with fixed ordering for its 7 record types. Huge solo-maintainer win.
3. **User state files are plain `.py` modules** — loaded via `importlib`, side-effect registration into a module-level registry. Preserves mypy support + IDE autocomplete. Pattern used by pytest/alembic/celery.
4. **Introspection output is a user-project artifact** — written to a caller-specified path, never bundled in the tool package.
5. **4 small additions needed in godoo core** before state-manager can build cleanly: `search_read_all()` auto-paging, `ref(xml_id)` helper, `context` param on `call()`, translation write coverage. All non-breaking.

## Top Pitfalls (moduleX-heavy, as expected)

1. **xml_id idempotency** — without `ir.model.data` records written alongside every created row, re-runs create duplicates and removals become impossible. Must be architected in from day one.
2. **moduleX deletion order** — FK constraints force strict order: menus → actions → views → rules → ACLs → fields → models. Wrong order = cascade failures.
3. **Registry reload under multi-worker Odoo** — schema changes via RPC don't propagate to other workers until their next request. Readers may see stale schema for seconds.
4. **v16+ translation storage changed from `ir.translation` table to inline JSON dict** in HTML/char fields. State-manager must detect version and write both ways.
5. **`ir.rule` domain is Python eval** — security boundary; state-manager must validate AST before sending.
6. **`state='manual'` + `x_` prefix required** on every model and field created via RPC. Missing either = silent Odoo validation failure.
7. **Selection field format is Python-tuple-string** `"[('a', 'A'), ('b', 'B')]"` not JSON. Serialization matters.
8. **m2m relation table name collisions** — Odoo auto-names tables; manual RPC creation must supply unique `relation` strings.
9. **m2m `removeUnmanaged` vs o2m is destructive** — m2m unlinks associations, o2m *deletes children*. Semantics difference is a footgun.
10. **Pagination silent truncation** — `search_read` defaults to limit 80 on some Odoo versions; callers assuming "all records" get partial data without warning.
11. **Naive UTC datetimes in core client** — Odoo stores UTC but returns naive; tz conversion is caller's job and nobody expects that.
12. **`mail.thread` inheritance cannot be expressed via `inherit_id` over RPC** — Python inheritance, not XML. moduleX needs explicit out-of-scope note or a workaround.

## Open Questions (need live-instance verification)

- Does Odoo 17+ Properties store in `ir.model._properties_definition` or elsewhere? — blocks introspection Properties support
- Exact JSON shape of inline translations in v16/v17 HTML fields — blocks state-manager translation diffing
- Does `ir.model.fields` deletion cascade to dependent views? — determines moduleX deletion order correctness
- Is `markdown-it-py 4.0.0` clean under mypy strict on Python 3.14? — classifiers stop at 3.13
- Does `css_inline` ship `.pyi` stubs? — needs wheel inspection

## Phase Ordering (implications for roadmap)

Suggested 5 phases:

1. **Phase 1 — Core hardening.** No new research needed (code audit + known RPC mechanics). Upgrade pytest-asyncio. Fix silent failure modes. Add the 4 small core additions. Add integration tests for all 8 services. **Locks the API** before downstream depends on it.
2. **Phase 2 — godoo-introspection.** Needs phase research on v17+ Properties schema. Jinja2 template pipeline. CLI. Deterministic output. Per-instance package emission.
3. **Phase 3 — godoo-state-manager.** Needs phase research on pre-v16 translation write path. Full TS primitive port. importlib-based file loader. 8-phase pipeline. xml_id idempotency from day one. Degrades gracefully without introspection.
4. **Phase 4 — godoo-moduleX.** Needs phase research on FK deletion order and `mail.thread` availability. DSL layer on top of state-manager. 7 record types. x-module grouping/registry. Deepest pitfall count.
5. **Phase 5 — Docs and examples.** No research needed. README per package + top-level "getting started" walkthrough showing all four layers composing.

**Parallelism opportunities:** Phase 2 and Phase 3 can partially overlap (state-manager works without introspection). Phase 4 requires stable state-manager pipeline; cannot start until Phase 3's core is done.

**Confidence:** HIGH for Phases 1, 3, 5 · MEDIUM-HIGH for Phase 2 · MEDIUM for Phase 4 (moduleX internals need verification against real Odoo).
