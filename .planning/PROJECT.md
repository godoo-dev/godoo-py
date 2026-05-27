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

## Current Milestone: v1.1 Typed Models & Browser Reach

**Goal:** Sharpen developer ergonomics with instance-derived typed models, and de-risk
running godoo in the browser — without breaking the existing API.

**Target features:**
- Rename `packages/godoo` → `packages/godoo-client` to close the directory↔dist-name gap
  (import namespace stays `godoo.*` — no user breakage)
- Instance-specific typed models: a `godoo-introspection` CLI that emits a Pydantic model
  package from the live schema, plus a polymorphic typed-read layer in core behind a
  `godoo[typed]` extra (`client.read(ResPartner, …)` → `list[ResPartner]`; raw `str` path
  unchanged; relational fields type as typed `Ref[Model]` / id, no nested fetch)
- Pyodide/browser spike: prove whether httpx works in Pyodide (or needs a custom transport
  adapter), then decide whether to commit to a browser-compatible build

**Version note:** v1.1 is additive (typed reads dispatch on `read()`'s first arg; default
install stays httpx-only). If the Pyodide spike surfaces required breaking changes, revisit
and bump to v2.0.

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

<!-- Validated in Phase 2: Introspection (2026-05-21). -->

- ✓ `Introspector` — live schema via batched `ir.model` / `ir.model.fields` queries — Phase 2
- ✓ `IntrospectionCache` — per-instance model-keyed cache with live-bypass option — Phase 2
- ✓ `CodeGenerator` — emits typed TypedDict Python modules from a live schema — Phase 2
- ✓ Type mapper — all 20 Odoo field ttypes → Python type hints — Phase 2
- ✓ Selection fields emitted as `Literal[...]` — Phase 2
- ✓ `godoo-introspection` `py.typed` PEP 561 marker — Phase 2

<!-- Validated in Phase 3: Testcontainers Parity (2026-05-22). -->

- ✓ Local snapshot cache (`pg_dump`/restore, sha256-keyed) — Phase 3
- ✓ Custom addons bind-mount (`addons_path`) — Phase 3
- ✓ Properties provisioner (`ConfigParameterHelper`, ir.config_parameter) — Phase 3
- ✓ `TestHarness` async-cm composing the provisioners — Phase 3
- ✓ `godoo-testcontainers` `py.typed` PEP 561 marker — Phase 3

<!-- Validated in Phase 4 + 4.1: Release (2026-05-22). -->

- ✓ `godoo-dev/godoo-py` GitHub repo created, `origin` configured, CI passing — Phase 4
- ✓ `godoo`→`godoo-client` rename; PEP 420 `godoo.*` namespace restructure — Phase 4
- ✓ All four distributions published to PyPI (0.2.0) via OIDC trusted publishing — Phase 4
- ✓ Client-facing READMEs wired into each `pyproject.toml`; PyPI pages render (0.2.1) — Phase 4.1

### Active

<!-- v1.1 Typed Models & Browser Reach — scoping in progress. REQ-IDs land in REQUIREMENTS.md. -->

_Milestone v1.1 is being scoped (see Current Milestone above). Requirements with REQ-IDs are
defined in `.planning/REQUIREMENTS.md`._

### Out of Scope

- Python version floor relaxation (3.11/3.12) — SEED is silent; the 3.14 floor holds for v1, revisit post-v1
- Automatic re-authentication on session expiry (was CLIENT-V2-01) — struck: godoo authenticates with API keys / passwords, which do not expire; there is no session to re-establish, so this solves a non-problem
- Performance refactors (`read_group` aggregation, CDC two-round-trip) — not parity gaps; backlog
- Full CONCERNS.md test-coverage backfill — v1 covers only new and changed code, not the pre-existing gaps
- godoo-adoption branch protocol — no separate source repo to shed; does not apply (SEED §3)

## Context

- **v1.0 shipped (2026-05-22).** All three packages reached TS parity and were published
  to PyPI: `godoo-client`, `godoo-introspection`, `godoo-testcontainers` (plus a `godoo`
  placeholder dist) on a PEP 420 shared `godoo.*` namespace, at package version 0.2.1 via
  OIDC trusted publishing. 26/26 v1 requirements complete. GSD milestone tag:
  `milestone-v1.0` (distinct from the semantic-release package tags `v0.1.0`/`v0.2.0`).
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
| `godoo` client package → `godoo-client` on PyPI; introspection/testcontainers keep names | SEED §6(b); PyPI name clarity | ✓ Good — shipped 0.2.0 with PEP 420 `godoo.*` namespace |
| Test framework inherited unchanged (pytest-asyncio, respx, ruff, strict mypy) | SEED §6(c); existing config is sound | ✓ Good |
| v1 scope = SEED §2 gaps + bugs in the same files | Adjacent bugs are cheap to fix in the same blast radius | ✓ Good — all 26 v1 requirements shipped |
| Keep the Python 3.14 floor for v1 | SEED is silent; hold charter scope, revisit post-v1 | ✓ Held — revisit via COMPAT-01 post-v1 |
| Include a release phase (repo create + PyPI publish) | SEED §5 deliverable; the satellite owns publish | ✓ Good — published via OIDC trusted publishing |
| Drop CLIENT-09 (`OAuthProxyClient`) from v1; amend SEED §2/§4 | Owner decision — never implemented, not a real parity gap | ✓ Good |
| Drop TESTC-03/04/05 (partners/projects/users provisioners) from v1 | Declarative seeding belongs to godoo-stateman; testcontainers does bare minimum | D-Drop-1 |
| Drop INTRO-05 (`godoo-introspect` CLI) from v1 | Library is the v1 deliverable; no CLI surface yet | D-CLI-1 |
| Insert Phase 4.1 (package READMEs) after release | PyPI pages rendered empty — only the `godoo` meta package shipped a README | ✓ Good — fixed in 0.2.1 |
| Tag GSD milestone as `milestone-v1.0`, not `v1.0` | Bare `v1.0` collides with semantic-release's `vX.Y.Z` tag namespace and would force a 1.0 package bump | ✓ Good |

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
*Last updated: 2026-05-27 — milestone v1.1 (Typed Models & Browser Reach) started*
