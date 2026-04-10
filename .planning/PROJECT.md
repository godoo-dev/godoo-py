# godoo

## What This Is

godoo is an async Python SDK for Odoo, built as a three-layer stack: an RPC client, a declarative state manager, and a live "x-module" builder. It's the Odoo toolkit for Python developers and Odoo consultants who treat Odoo's infinite per-instance customization as a first-class constraint instead of pretending it away.

## Core Value

**Typing is generated per-instance via introspection, never assumed.** Point godoo-introspection at an Odoo instance and you get a typed Python package that reflects *that* instance — models, fields, custom fields, properties, and all. Everything else (the ergonomic async client, declarative state, live x-modules) rests on that premise.

## Requirements

### Validated

<!-- Inferred from existing v0.1.1 codebase — shipped and relied upon. -->

- ✓ uv workspace with 3 packages (`packages/godoo`, `packages/godoo-testcontainers`, `packages/godoo-introspection`) — existing
- ✓ Async JSON-RPC transport for Odoo (`packages/godoo/src/godoo/client.py`) — existing
- ✓ 8 service modules wired via `@cached_property` on `OdooClient` with lazy imports — existing
- ✓ `godoo-testcontainers` Docker test harness wrapping the sync testcontainers-python API in `asyncio.to_thread()` — existing
- ✓ Unit test infrastructure: pytest-asyncio (auto mode, session-scoped loop), `respx` HTTP mocking — existing
- ✓ Release pipeline: semantic-release + PyPI publishing (restored in recent commits) — existing

### Active

<!-- v1 hypotheses. All four layers ship together. -->

- [ ] **Harden godoo core** — audit the 8 existing services for consistency; add integration tests against real Odoo via testcontainers; lock the client API before downstream packages depend on it
- [ ] **godoo-introspection** — replace the placeholder with a real type generator: point at an Odoo instance, emit a typed Python package (dataclasses/TypedDicts) covering every model, field, and property in that instance, including customizations
- [ ] **godoo-state-manager** — Pythonic port of [@marcfargas/odoo-state-manager](https://github.com/marcfargas/odoo-toolbox/blob/master/packages/odoo-state-manager/README.md): `resource()` / `lookup()` / `model()` DSL returning dataclasses, plan/apply/diff/drift semantics, translations, HTML/Markdown markers, `removeUnmanaged` / `removeOrphans` cleanup policies
- [ ] **godoo-moduleX** — live Studio-style x-module builder over RPC. Declare models + x-fields, views + menus, ACLs + record rules, and seed data as a named logical "x-module"; push via RPC directly into `ir.model` / `ir.ui.view` / `ir.model.access` / `ir.rule` etc. No deployment pipeline, no .zip output — the module exists only in the target DB
- [ ] **Documentation & examples for the whole stack** — README per package, a top-level "getting started" walkthrough that shows the four layers composing

### Out of Scope

- **Sync client API** — godoo is async-only. Users needing sync can wrap with `asyncio.run()`. Rationale: dual API doubles maintenance surface; asyncio is the modern Python I/O story
- **Data migration tooling** — state-manager is for declarative config, not bulk data imports or v14→v17 upgrades. Rationale: scope creep into a different product
- **Odoo.sh-specific integrations** — no staging/deployment API wrappers. Rationale: generic RPC works against any Odoo, tying to Odoo.sh fragments the audience
- **Workflows / wizards / server actions in moduleX** — only CRUD-shaped primitives (models, fields, views, menus, ACLs, rules, data). Rationale: workflows and server actions need Python code that can't be expressed via RPC; out of moduleX's charter
- **Static / generic Odoo type stubs** — godoo will not ship `.pyi` files pretending to know the Odoo schema. Rationale: every Odoo instance is customized; generic stubs lie. Types come from introspection of the real target instance or not at all
- **1:1 TS API parity** — the Python state-manager reinterprets the TS DSL Pythonically (dataclasses, kwargs, Python idioms). Rationale: forcing TS ergonomics into Python makes both languages worse

## Context

- **Brownfield init** — godoo is at v0.1.1 with real code: uv workspace, 8 services, testcontainers test infra, working release pipeline. Recent commits were fixing semantic-release and PyPI publishing config. A full codebase map lives in `.planning/codebase/` (STACK, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, INTEGRATIONS, CONCERNS).
- **Sibling project** — godoo is the Python counterpart to [marcfargas/odoo-toolbox](https://github.com/marcfargas/odoo-toolbox), a TypeScript stack containing `@marcfargas/odoo-client`, `@marcfargas/odoo-introspection`, `@marcfargas/odoo-state-manager`, and `@marcfargas/odoo-testcontainers`. The TS toolbox is the reference semantics; godoo reinterprets those semantics in async Python.
- **Solo maintainer** — Marc Fargas is the sole author. Dogfooding via real Odoo work is both a driver and a validation channel.
- **godoo-introspection is load-bearing** — currently a placeholder, but the core value proposition (per-instance typing) depends on it. Its design and shipping are on the critical path for v1, not an afterthought.

## Constraints

- **Tech stack**: Python 3.14, async-only, hatchling build backend, uv workspace — already decided and in-repo
- **Linting & types**: ruff (line-length 120, select `[E, F, W, I, UP, B, SIM, TCH, RUF]`), mypy `--strict` on every `src/` — already enforced
- **Imports**: `from __future__ import annotations` everywhere; `TYPE_CHECKING` for `OdooClient` imports in services (prevents circular imports) — established convention
- **Data types**: dataclasses, not Pydantic — established convention
- **License**: LGPL-3.0-or-later — matches the author's default for open-source work
- **Async discipline**: all service functions async; sync third-party APIs (testcontainers-python) must be wrapped in `asyncio.to_thread()` — established convention
- **Testing**: pytest-asyncio auto mode; unit tests mock HTTP with `respx`, integration tests hit real Odoo via testcontainers and are gated by a marker — established convention

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Typing is optional and per-instance via introspection | Every Odoo instance is customized; generic stubs lie. Pointing at the real target produces the only types that are actually correct. | — Pending |
| Pythonic DSL for state-manager, not 1:1 TS parity | Forcing TS idioms into Python makes both languages worse. Same semantics, Python-native surface. | — Pending |
| `resource()` / `lookup()` return dataclasses | Close enough to the TS API to be recognizable, ergonomic in Python, integrates with mypy and IDE autocomplete when paired with generated types | — Pending |
| moduleX is live-via-RPC, not .zip generation | The use case is "deploy simple model+view modules without touching deployment code." A file-emitting pipeline would contradict that goal. | — Pending |
| Full three-layer stack + moduleX ships together in v1 | The layers reinforce each other: introspection enables typing, state-manager needs the client, moduleX needs state-manager. Shipping one without the others underdelivers the pitch. | — Pending |
| Async-only, no sync shim | Dual API doubles maintenance surface for a solo maintainer. `asyncio.run()` is an acceptable escape hatch. | — Pending |
| Dataclasses, not Pydantic | Lighter, no runtime schema validation needed at the SDK layer, matches existing convention | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-10 after initialization*
