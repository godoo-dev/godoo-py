# godoo-py

## What This Is

godoo-py is the Python monorepo for the godoo library family — the Python member of
the godoo / Odoo Atlas initiative. It ships three packages: `godoo` (an async Odoo
JSON-RPC client), `godoo-introspection` (live-schema discovery and typed code
generation), and `godoo-testcontainers` (Docker-based Odoo test infrastructure). It is
a public LGPL-3.0 library for Python developers automating or testing Odoo instances.

## Core Value

The Python family member reaches feature parity with the TypeScript core-3 libraries —
a Python developer gets the same client, introspection, and testcontainers capabilities
that godoo-ts already ships.

## Requirements

### Validated

<!-- Existing capabilities incorporated from the C:\dev\godoo-py codebase (mapped 2026-05-18). -->

- ✓ Async `OdooClient` with JSON-RPC auth lifecycle and CRUD helpers — existing
- ✓ Eight domain services (mail, modules, attendance, timesheets, accounting, urls, properties, cdc) — existing
- ✓ `JsonRpcTransport` with a typed `OdooError` exception hierarchy — existing
- ✓ Opt-in `SafetyContext` guard gating mutating operations — existing
- ✓ Env-var config bootstrapping (`config_from_env`, `create_client`) — existing
- ✓ `godoo-testcontainers` — Docker Postgres+Odoo container with a seed resolver — existing
- ✓ uv workspace, hatchling builds, ruff + strict mypy, pytest-asyncio test setup — existing

<!-- Validated in Phase 1: Client Parity (2026-05-19). -->

- ✓ Async context manager (`async with OdooClient(...)`) — Phase 1
- ✓ `iter_search_read()` auto-paginated async generator — Phase 1
- ✓ `with_context(lang=...)` call modifier — Phase 1
- ✓ `fields_get()` field-metadata introspection — Phase 1
- ✓ `ref(xml_id)` XML-ID lookup — Phase 1
- ✓ `execute_kw()` raw RPC passthrough — Phase 1
- ✓ `read_binary()` binary-field fetch — Phase 1
- ✓ Bulk `create` (list of value dicts) — Phase 1
- ✓ `py.typed` PEP 561 marker — Phase 1
- ✓ Fix `CdcService.get_feed` signature bug — Phase 1
- ✓ Raise `OdooTimeoutError` on timeout — Phase 1
- ✓ Request-timeout configuration on the transport — Phase 1

### Active

<!-- v1 milestone: build introspection, fill out testcontainers, release. -->

**godoo-introspection — build from scratch:**
- [ ] `Introspector` — queries `ir.model` / `ir.model.fields` for live schema
- [ ] `IntrospectionCache` — model-keyed cache with bypass option
- [ ] `CodeGenerator` — emits typed Python representations from schema
- [ ] Type mapper — Odoo field types → Python type hints
- [ ] `godoo-introspect` CLI entry point
- [ ] Selection fields emitted as `Literal[...]`

**godoo-testcontainers — parity gaps:**
- [ ] Local snapshot cache (`pg_dump`/restore keyed by content hash)
- [ ] Custom addons mount (`addonsPath`)
- [ ] Four resource provisioners (partners, projects, users, properties)
- [ ] `TestHarness` high-level fixture composing the provisioners
- [ ] `py.typed` markers (introspection + testcontainers)

**Release:**
- [ ] Create `godoo-dev/godoo-py` repo, rename `godoo`→`godoo-client` on PyPI, publish

### Out of Scope

- Python version floor relaxation (3.11/3.12) — SEED is silent; the 3.14 floor holds for v1, revisit post-v1
- Automatic re-authentication on session expiry — flagged by the map but not a SEED parity gap; deferred
- Performance refactors (`read_group` aggregation, CDC two-round-trip) — not parity gaps; backlog
- Full CONCERNS.md test-coverage backfill — v1 covers only new and changed code, not the pre-existing gaps
- godoo-adoption branch protocol — no separate source repo to shed; does not apply (SEED §3)

## Context

- **Brownfield re-run.** The existing `C:\dev\godoo-py` monorepo was incorporated as this
  satellite's base — full git history merged (commit `19d54e8`), prior `.planning/`
  removed so a fresh GSD pass owns planning. The codebase was mapped 2026-05-18
  (`.planning/codebase/`).
- **Umbrella initiative.** godoo-py is one satellite of the godoo / Odoo Atlas
  initiative, coordinated from the private `godoo-hq` spine. The generated `CLAUDE.md`
  must `@`-import `../godoo-hq/UMBRELLA_CLAUDE.md`. On completion, godoo-py reports
  back to the spine's `dev-log.md` against the SEED §4 criteria.
- **Parity target.** The TypeScript core-3 libraries (`@godoo/client`,
  `@godoo/introspection`, `@godoo/testcontainers`) define what "parity" means; godoo-ts
  already ships them.
- **The seed.** `SEED.md` is the charter. §2 lists every parity gap; §6 open questions
  were resolved in the prior pass (see Key Decisions).

## Constraints

- **Tech stack**: Python 3.14, uv workspace, hatchling, httpx — established; not changing
- **Conventions**: `from __future__ import annotations` everywhere, `TYPE_CHECKING` imports for `OdooClient` in services, dataclasses (not Pydantic), all service functions async — established patterns
- **Service pattern**: each service is a `types.py`/`functions.py`/`service.py`/`__init__.py` quad, wired into `client.py` via lazy `@cached_property`
- **Licensing**: LGPL-3.0-or-later (public library)
- **Quality gate**: ruff (line-length 120) + `mypy --strict` on all `src/`; pytest-asyncio `asyncio_mode = auto`
- **Umbrella-aware**: `CLAUDE.md` `@`-imports `../godoo-hq/UMBRELLA_CLAUDE.md`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Incorporate existing repo via full-history merge | SEED §6(a); preserves provenance | ✓ Good |
| `godoo` client package → `godoo-client` on PyPI; introspection/testcontainers keep names | SEED §6(b); PyPI name clarity | — Pending |
| Test framework inherited unchanged (pytest-asyncio, respx, ruff, strict mypy) | SEED §6(c); existing config is sound | ✓ Good |
| v1 scope = SEED §2 gaps + bugs in the same files | Adjacent bugs are cheap to fix in the same blast radius | — Pending |
| Keep the Python 3.14 floor for v1 | SEED is silent; hold charter scope, revisit post-v1 | — Pending |
| Include a release phase (repo create + PyPI publish) | SEED §5 deliverable; the satellite owns publish | — Pending |
| Drop CLIENT-09 (`OAuthProxyClient`) from v1; amend SEED §2/§4 | Owner decision — never implemented, not a real parity gap | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-19 — Phase 1 (Client Parity) complete; 12 requirements validated*
