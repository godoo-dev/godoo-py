# Milestone v1.1 — Project Summary
**Generated:** 2026-06-02
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**godoo-py** is the Python monorepo for the godoo library family — the Python member of the godoo / Odoo Atlas initiative. It ships three packages:

- `godoo-client` — async Odoo JSON-RPC client (import namespace `godoo.client.*`)
- `godoo-introspection` — live-schema discovery and typed Pydantic code generation
- `godoo-testcontainers` — Docker-based Odoo + Postgres test infrastructure

**Core value:** A Python developer gets the same client, introspection, and testcontainers capabilities that `godoo-ts` already ships, plus instance-derived typed models for ergonomic type-safe Odoo reads.

**Target users:** Python developers automating or testing Odoo instances. Licensed LGPL-3.0-or-later; published to PyPI.

**Milestone v1.1 — Typed Models & Browser Reach** built on the v1.0 foundation (all three packages at TS parity, PyPI-published) and added:
- A directory rename to align `packages/godoo-client/` with the PyPI dist name
- A transport-injection seam (`OdooClientConfig.transport_factory`) for alternative transport implementations
- A typed read layer: `client.read(ResPartner, ids)` → `list[ResPartner]` via `OdooBaseModel` subclasses (opt-in via `godoo[typed]` extra)
- A Pydantic CLI generator: `godoo-introspect generate` emits a full Pydantic model package from a live Odoo instance
- Phase 8 (Pyodide spike) — planned but not started as of 2026-06-02

**Phase status at report date:**
- Phases 5, 6, 7: Complete
- Phase 8 (Pyodide spike): Not started — next work item

---

## 2. Architecture & Technical Decisions

### Tech Stack

- **Python 3.14**, uv workspace, hatchling build backend
- **httpx** — sole runtime HTTP dependency; drives all Odoo JSON-RPC communication
- **pytest-asyncio** (`asyncio_mode = auto`, session-scoped loop) + **respx** for mock HTTP unit tests
- **testcontainers-python** (sync API; all calls wrapped in `asyncio.to_thread()`)
- **Pydantic >=2.13** — used in the typed layer only; the default install stays Pydantic-free
- **Typer >=0.26** — CLI framework for `godoo-introspect`
- ruff (line-length 120, E/F/W/I/UP/B/SIM/TCH/RUF) + mypy --strict on all `src/` trees
- python-semantic-release for automated versioning

### Key Architectural Decisions

| Decision | Why | Phase |
|----------|-----|-------|
| PEP 420 implicit namespace `godoo.*` — directory name decoupled from import path | Allows `packages/godoo-client/` to match the PyPI dist name without breaking existing `import godoo.client` callers; one `godoo.*` namespace spans three packages | v1.0 Phase 4 |
| Service quad pattern: `types.py` / `functions.py` / `service.py` / `__init__.py` | Separates data shapes, business logic, and object API; functions are independently callable; prevents circular imports via `TYPE_CHECKING` guard on `OdooClient` import | v1.0 Phase 1 |
| testcontainers sync API always wrapped in `asyncio.to_thread()` | testcontainers-python has no async API; wrapping prevents blocking the event loop | v1.0 Phase 3 |
| GSD milestone tags use `milestone-vX.Y`, never bare `vX.Y` | Semantic-release owns the `vX.Y.Z` tag namespace; colliding tags would trigger unintended package version bumps | v1.0 Phase 4 |
| `godoo[typed]` optional extra; pydantic import is lazy (only triggered in typed dispatch branch) | Default install stays httpx-only; a subprocess isolation test (`test_typed_isolation.py`) enforces this in CI | Phase 6 |
| Transport `Protocol` + `transport_factory` on `OdooClientConfig` | Additive seam allowing alternative transport injection (e.g. a Pyodide fetch-backed transport) without modifying `JsonRpcTransport` | Phase 6 (BROWSER-01) |
| Dispatch guard is `hasattr(model, "__odoo_model__")`, never `isinstance(BaseModel)` | Dispatch runs before `_pydantic_transform` is imported; keeps typed dispatch Pydantic-free at the call site | Phase 6 |
| Pydantic replaces TypedDict in codegen — breaking change (INTRO-03 superseded) | Pydantic's `@model_validator` handles Odoo's bidirectional wire transforms declaratively (False→None, [id,name]→Ref, str→date/datetime) with no per-model glue; a dataclass cannot do this without hand-written `__post_init__` per model | Phase 7 |
| `pydantic_field_str` returns a 3-tuple `(field_line, import_fragment, classname)` | Encapsulates per-field import assembly alongside the field declaration; callers accumulate and deduplicate imports | Phase 7 |
| `pretty_exceptions_show_locals=False` on Typer | Prevents credential values from appearing in exception tracebacks | Phase 7 |
| `derive_partial_model` uses `(id(model), frozenset(fields))` keyed LRU cache | Avoids re-creating the same Pydantic dynamic model on every partial-field read; cache key uses `id()` of the model class to avoid hashing class objects | Phase 6 |

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 1 (v1.0) | Client Parity | Complete (2026-05-19) | Async-CM, `iter_search_read`, `with_context`, full CRUD helpers, typed error hierarchy, configurable timeout |
| 2 (v1.0) | Introspection | Complete (2026-05-21) | `Introspector` (3-RPC batch schema fetch + cache), `CodeGenerator` emitting TypedDict modules (later replaced in Phase 7) |
| 3 (v1.0) | Testcontainers Parity | Complete (2026-05-22) | sha256-keyed pg_dump/restore snapshot cache, addons bind-mount, `ConfigParameterHelper`, `TestHarness` async-CM |
| 4 (v1.0) | Release | Complete (2026-05-22) | `godoo-dev/godoo-py` GitHub repo, PEP 420 namespace restructure, all four dists published to PyPI (0.2.0) via OIDC trusted publishing |
| 4.1 (v1.0) | Package READMEs | Complete (2026-05-22) | Per-distribution `readme` keys wired; PyPI pages now render; 0.2.1 published |
| 5 (v1.1) | Directory Rename | Complete (2026-05-28) | `packages/godoo` → `packages/godoo-client` via `git mv`; all 7 config references updated; PEP 420 guard test added |
| 6 (v1.1) | Transport Seam & Typed Models Core | Complete (2026-05-28) | `Transport` Protocol + `transport_factory`; `godoo.client.typed` stdlib module; `OdooBaseModel` wire transforms; `@overload` dispatch on `read`/`search_read`; `godoo[typed]` extra |
| 7 (v1.1) | Pydantic CLI Generator | Complete (2026-06-01) | TypedDict emitter replaced; `type_mapper.py` migrated to Pydantic forms; `godoo-introspect generate` CLI end-to-end; `pydantic>=2.13` + `typer>=0.26` as runtime deps of `godoo-introspection` |
| 8 (v1.1) | Pyodide Spike | Not started | Empirical spike: real HTTPS Odoo call from Pyodide runtime; written verdict on transport strategy + Python floor + go/no-go for browser build |

---

## 4. Requirements Coverage

### v1.1 Requirements (13 total, 11 complete, 2 pending Phase 8)

| Req | Description | Status |
|-----|-------------|--------|
| PKG-01 | `packages/godoo` renamed to `packages/godoo-client` via `git mv`; import namespace `godoo.*` intact | ✅ Complete |
| PKG-02 | All path references updated; CI stays green (mypy, build_command, mkdocs, CONTRIBUTING) | ✅ Complete |
| PKG-03 | CI guard test asserts `godoo.__file__ is None` (PEP 420 invariant) | ✅ Complete |
| TYPED-01 | Developer can generate Pydantic model package via `godoo-introspect generate` CLI | ✅ Complete |
| TYPED-02 | Generated models: `id: int` required, scalars `Optional[T] = None`, `Literal[…]` selections, `Ref[Model]`/`Ref[int]` m2o, `list[int]` x2many | ✅ Complete |
| TYPED-03 | `client.read(ModelClass, ids)` and `search_read(ModelClass, …)` return validated `list[ModelClass]` | ✅ Complete |
| TYPED-04 | Raw `client.read("res.partner", ids)` returns `list[dict[str, Any]]` unchanged | ✅ Complete |
| TYPED-05 | `godoo[typed]` opt-in extra; default install imports no pydantic; subprocess isolation test in CI | ✅ Complete |
| TYPED-06 | Wire transforms: `False`→`None` (non-bool), m2o `[id,"Name"]`→`Ref`, date/datetime strings typed, `bool` fields preserved | ✅ Complete |
| TYPED-07 | `Ref[T]` and `OdooModel` Protocol in stdlib-only `godoo.client.typed`; dispatch uses `hasattr`, never `isinstance(BaseModel)` | ✅ Complete |
| BROWSER-01 | `Transport` Protocol + `transport_factory` hook on `OdooClientConfig`; `JsonRpcTransport` satisfies Protocol structurally | ✅ Complete |
| BROWSER-02 | Pyodide spike: real HTTPS call against TLS-terminated Odoo; written verdict on transport strategy | ⚠️ Pending (Phase 8) |
| BROWSER-03 | Python-floor recommendation (≥3.12 for browser build or defer); explicit go/no-go decision | ⚠️ Pending (Phase 8) |

**Coverage: 11/13 complete (85%). Remaining 2 are gated on Phase 8 (Pyodide spike), which has not started.**

### v1.0 Requirements (26/26 complete — shipped 2026-05-22)

All v1.0 requirements are complete: CLIENT-01 through CLIENT-08/10, FIXES-01 through FIXES-03, INTRO-01 through INTRO-04/06/07, TESTC-01/02/06/07/08, RELEASE-01 through RELEASE-03. Full archive: `.planning/milestones/v1.0-REQUIREMENTS.md`.

---

## 5. Key Decisions Log

| ID | Description | Phase | Rationale |
|----|-------------|-------|-----------|
| D-01 (Phase 5) | Full repo grep sweep for `packages/godoo/` references — enumerated list is minimum, not ceiling | Phase 5 | Guard against stragglers the enumerated list missed |
| D-02 (Phase 5) | Remove stale trailing `uv build --package godoo` from `build_command` after confirming it is a leftover | Phase 5 | Keep semantic-release build clean post-rename |
| D-03 (Phase 5) | PEP 420 guard test lives in `packages/godoo-client/tests/`, not a separate top-level location | Phase 5 | Lives with the package it protects; runs on every pytest invocation |
| D-01 (Phase 6) | Partial-read strategy: derive a subset model of the target class containing only requested fields | Phase 6 | Marc override of research recommendation — partial reads are a real Odoo idiom that should stay typed |
| D-02 (Phase 6) | Boolean `False`-coercion: emit boolean fields as `bool` (non-Optional); `@model_validator` skips coercion for `bool`-annotated fields | Phase 6 | Decidable at validation time without a runtime `FieldMeta` lookup |
| D-03 (Phase 6) | `@overload` dispatch on both `read` AND `search_read` in Phase 6 | Phase 6 | Phase 7 codegen consumes both; shipping only one would require a follow-up |
| D-04 (Phase 6) | Dispatch guard is `hasattr(model, "__odoo_model__")`, never `isinstance(BaseModel)` | Phase 6 | Lets dispatch run before `_pydantic_transform` is imported |
| D-06 (Phase 6) | `Transport` Protocol surface: exactly 5 members (`session`, `authenticate`, `call`, `logout`, `aclose`) | Phase 6 | Minimal interface — only what `OdooClient` actually calls |
| D-01 (Phase 7) | Pydantic replaces TypedDict — breaking change to v0.2.0 public API; INTRO-03 superseded | Phase 7 | Pydantic handles Odoo wire transforms declaratively; TypedDict cannot without per-model glue |
| D-03 (Phase 7) | Model selection: exactly one of `--models <glob,...>` or `--all`; missing → clear error, non-zero exit | Phase 7 | Prevents silent no-op when user forgets to specify scope |
| D-04 (Phase 7) | Many2one relation degradation: in-set → `Ref[TargetClass]` + cross-import; not-in-set → `Ref[int]` + `# <odoo.model>` comment | Phase 7 | No transitive auto-inclusion (balloons codegen); always compiles without errors |
| GSD milestone tag namespace | Use `milestone-vX.Y` (not bare `vX.Y`) to stay out of semantic-release tag namespace | v1.0 Phase 4 | Bare `v1.0` would drive semantic-release into an unintended major bump |
| Drop CLIENT-09 (`OAuthProxyClient`) | Never implemented; not a real parity gap | v1.0 Phase 1 | Scope discipline |
| Drop TESTC-03/04/05 (provisioners) | Declarative seeding belongs to godoo-stateman | v1.0 Phase 3 | testcontainers does bare minimum |
| Drop INTRO-05 (CLI in v1.0) | Library is the v1.0 deliverable; CLI deferred to v1.1 (Phase 7) | v1.0 Phase 2 | Scope discipline |

---

## 6. Tech Debt & Deferred Items

### Open Deferred Items

| Category | ID | Item | Status | Deferred At |
|----------|----|------|--------|-------------|
| Compatibility | COMPAT-01 | Relax Python floor to 3.11/3.12 | Deferred to post-v1 | Init |
| Performance | PERF-01 | `read_group` SUM for cash balance | Backlog | Init |
| Performance | PERF-02 | CDC two-round-trip optimization | Backlog | Init |
| Browser (conditional) | BROWSER-F1 | `godoo[browser]` extra | Gated on Phase 8 go verdict | v1.1 scope |
| Browser (conditional) | BROWSER-F2 | Relax Python floor for Pyodide | Gated on Phase 8 go verdict | v1.1 scope |
| Typed models | TYPED-F1 | Nested relational model fetch | Deferred to v2+ | v1.1 scope |
| Typed models | TYPED-F2 | Typed write/create paths | Deferred to v2+ | v1.1 scope |
| Tech debt | — | `release.yml` Node 20 actions deprecation warnings | Needs version bump | v1.0 close |
| Tech debt | — | `snapshot.py` partial snapshot key for direct container users | Documented limitation | v1.0 close |

### Open Decisions (settle before Phase 6 implementation — already settled for Phases 5-7)

| ID | Decision | Resolution |
|----|----------|------------|
| OD-1 | Partial-read strategy | Settled in Phase 6: subset model via `create_model()` (D-01) |
| OD-2 | Boolean `False`-coercion | Settled in Phase 6: `bool`-annotated fields skip coercion (D-02) |
| OD-3 | httpx-in-Pyodide verdict | Unresolved — empirical spike only (Phase 8 must run) |

### Lessons from RETROSPECTIVE (v1.0)

1. Per-distribution packaging metadata (`readme` key in `pyproject.toml`) must be verified at publish time — a monorepo meta-package README does not propagate to sibling distributions. (Led to unplanned Phase 4.1.)
2. GSD milestone version numbering is independent of package release versioning; keep tag namespaces separate.
3. Update requirement checkboxes and traceability at phase transition, not at milestone close — closing-time reconciliation is error-prone.

---

## 7. Getting Started

### Prerequisites

- Python 3.14 (pinned via `.python-version`)
- `uv` installed (`pip install uv` or OS package manager)
- Docker (for integration tests only)

### Key Directories

```
packages/
  godoo-client/          # Core async client (import: godoo.client)
    src/godoo/client/
      client.py          # OdooClient, OdooClientConfig
      rpc/               # Transport layer (transport.py, protocol.py)
      services/          # Domain services (accounting, cdc, timesheets, ...)
      typed.py           # OdooModel Protocol + Ref[T] (stdlib-only)
      _pydantic_transform.py  # OdooBaseModel + wire transforms (pydantic-backed)
    tests/
  godoo-introspection/   # Schema discovery + codegen (import: godoo.introspection)
    src/godoo/introspection/
      introspector.py    # Introspector + IntrospectionCache
      codegen.py         # CodeGenerator (Pydantic emitter)
      type_mapper.py     # pydantic_field_str (all 20 Odoo ttypes)
      cli.py             # godoo-introspect entrypoint (typer)
    tests/
  godoo-testcontainers/  # Docker test infra (import: godoo_testcontainers)
    src/godoo_testcontainers/
      container.py       # OdooTestContainer + StartedOdooContainer
      snapshot.py        # pg_dump/restore snapshot cache
      harness.py         # TestHarness async-CM
    tests/
```

### Install & Run

```bash
# Install all workspace deps
uv sync

# Install with typed-models extra
uv sync --extra typed

# Run unit tests (no Docker required)
uv run pytest packages/ -m "not integration"

# Run integration tests (requires Docker)
uv run pytest -m integration

# Lint and format check
uv run ruff check . && uv run ruff format --check .

# Type check (all three src trees)
uv run mypy packages/godoo-client/src packages/godoo-testcontainers/src packages/godoo-introspection/src

# Run the CLI (requires a live Odoo instance and env vars)
uv run godoo-introspect generate --output ./models/ --models "res.partner,res.users"
uv run godoo-introspect generate --output ./models/ --all

# Build packages
uv build --package godoo-client
uv build --package godoo-introspection
uv build --package godoo-testcontainers
```

### Where to Look First

- **Client API entry points:** `packages/godoo-client/src/godoo/client/client.py` — `OdooClient`, `OdooClientConfig`
- **Typed read layer:** `packages/godoo-client/src/godoo/client/typed.py` (Protocol + `Ref`) and `_pydantic_transform.py` (wire transforms)
- **CLI:** `packages/godoo-introspection/src/godoo/introspection/cli.py`
- **Tests (unit):** `packages/*/tests/` — 334 tests as of Phase 7 completion
- **CI:** `.github/workflows/test.yml` — lint, mypy, unit tests, integration tests (Odoo 17/18/19)
- **Config:** Root `pyproject.toml` (workspace config, ruff, mypy, pytest, semantic-release)

---

## Stats

| Metric | Value |
|--------|-------|
| Milestone | v1.1 Typed Models & Browser Reach |
| Milestone status | In progress (Phase 8 not started) |
| v1.1 start date | 2026-05-27 |
| v1.1 last activity | 2026-06-01 |
| Duration to date | 6 days (2026-05-27 → 2026-06-01) |
| Phases complete (v1.1) | 3/4 (75%) |
| Plans complete (v1.1) | 7/7 (plans for phases 5-7; Phase 8 plans TBD) |
| Requirements complete (v1.1) | 11/13 (85%) |
| Commits since v1.1 start | 68 (2026-05-27 to 2026-06-01) |
| Total commits in repo | 219 |
| Files changed vs milestone-v1.0 | 129 files, +12,730 insertions, -684 deletions |
| Unit tests at Phase 7 completion | 334 passed |
| Contributors | Marc Fargas (212 commits), semantic-release (4), copilot-swe-agent[bot] (2) |
| PyPI packages | `godoo-client`, `godoo-introspection`, `godoo-testcontainers`, `godoo` (meta) — published 0.2.0 / 0.2.1 |
| v1.0 shipped | 2026-05-22 (5 phases, 14 plans, 26/26 requirements) |
