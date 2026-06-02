# Roadmap: godoo-py

## Milestones

- ✅ **v1.0 Parity & Release** — Phases 1-4.1 (shipped 2026-05-22) — full archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [ ] **v1.1 Typed Models & Browser Reach** — Phases 5-8 (in progress)

## Phases

<details>
<summary>✅ v1.0 Parity & Release (Phases 1-4.1) — SHIPPED 2026-05-22</summary>

- [x] Phase 1: Client Parity (5/5 plans) — completed 2026-05-19
- [x] Phase 2: Introspection (2/2 plans) — completed 2026-05-21
- [x] Phase 3: Testcontainers Parity (3/3 plans) — completed 2026-05-22
- [x] Phase 4: Release (3/3 plans) — completed 2026-05-22
- [x] Phase 4.1: Package READMEs (1/1 plan, INSERTED) — completed 2026-05-22

Close all Python parity gaps against the TypeScript core-3 libraries, build
`godoo-introspection` from scratch, and ship all three packages to PyPI under the
`godoo-dev/godoo-py` GitHub org. Full phase detail, goals, and success criteria are
preserved in [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md).

</details>

### v1.1 Typed Models & Browser Reach

- [x] **Phase 5: Directory Rename** — Rename `packages/godoo` → `packages/godoo-client`; update all tool-config paths; guard the PEP 420 namespace in CI (completed 2026-05-28)
- [x] **Phase 6: Transport Seam & Typed Models Core** — Add transport-injection seam on `OdooClientConfig`; build the stdlib-only `godoo.client.typed` module; implement wire transforms; add `@overload` dispatch on `client.read`/`search_read`; enforce import isolation via `godoo[typed]` extra (completed 2026-05-28)
- [x] **Phase 7: Pydantic CLI Generator** — Extend `godoo-introspection` with a Pydantic model emitter and a `godoo-introspect` CLI entrypoint; generated files import from `godoo.client.typed` and carry `__odoo_model__` (completed 2026-06-01)
- [ ] **Phase 8: Pyodide Spike** — Run a real in-browser HTTPS call against a real TLS-terminated Odoo endpoint, record the httpx/transport verdict, and produce a Python-floor recommendation and go/no-go decision

## Phase Details

### Phase 5: Directory Rename

**Goal**: The workspace directory `packages/godoo` is renamed to `packages/godoo-client`, every tool-config path reference is updated, and the PEP 420 `godoo.*` namespace invariant is enforced by a CI guard test
**Depends on**: Nothing (first phase of v1.1)
**Requirements**: PKG-01, PKG-02, PKG-03
**Success Criteria** (what must be TRUE):

  1. `packages/godoo-client/` exists on disk (via `git mv`); `packages/godoo/` no longer exists; `git log --follow` preserves blame history
  2. `uv sync && uv run python -c "import godoo.client"` completes without error; the wheel build produces a valid sdist + wheel from the new path
  3. CI passes: ruff, mypy, and pytest all resolve source paths correctly from the renamed location without manual path patching
  4. A guard test asserts `godoo.__file__ is None` (PEP 420 namespace intact, no stray `__init__.py` promoted godoo to a regular package)
  5. All seven hardcoded `packages/godoo/` references are updated (root `pyproject.toml`: `mypy_path`, `version_toml`, `build_command`; `.github/workflows/test.yml` mypy invocation; `mkdocs.yml` mkdocstrings paths)

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 05-01-PLAN.md — git mv rename + uv sync + update all path references (PKG-01, PKG-02) — DONE 2026-05-28

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-02-PLAN.md — PEP 420 guard test + D-04 local done-gate (PKG-03)

### Phase 6: Transport Seam & Typed Models Core

**Goal**: Developers can perform type-safe Odoo reads (`client.read(ResPartner, ids)` → `list[ResPartner]`) using instance-generated models, while the raw string path is unchanged and a default install with no Pydantic installed never imports Pydantic
**Depends on**: Phase 5
**Requirements**: BROWSER-01, TYPED-03, TYPED-04, TYPED-05, TYPED-06, TYPED-07
**Success Criteria** (what must be TRUE):

  1. `OdooClientConfig` accepts an optional `transport_factory` hook; `JsonRpcTransport` satisfies the new `Transport` `Protocol` structurally with no modification; an alternative transport can be injected and used end-to-end
  2. `client.read("res.partner", ids)` (str path) returns `list[dict[str, Any]]` — unchanged from v1.0, verified by the existing unit tests still passing
  3. `client.read(ResPartner, ids)` (class path) returns `list[ResPartner]` with all wire transforms applied: Odoo `False` → `None` for non-boolean fields; many2one `[id, "Name"]` → `Ref(id=…, name=…)`; date/datetime strings → typed values
  4. In a virtualenv with pydantic not installed, `python -c "import godoo.client"` completes without `ImportError`; pydantic import is only triggered at runtime when the typed dispatch branch is entered
  5. `godoo[typed]` is declared as an optional extra in `packages/godoo-client/pyproject.toml`; `godoo.client.typed` (`OdooModel` Protocol, `Ref` dataclass) is importable without pydantic — no Pydantic import at module load time anywhere in the `godoo.client` tree

**Plans**: 3 plans
Plans:
**Wave 1**

- [x] 06-01-PLAN.md — Transport seam: rpc/protocol.py Transport Protocol, OdooClientConfig.transport_factory field, OdooClient.__init__ injection branch, structural-conformance test (BROWSER-01)

**Wave 2** *(blocked on Wave 1 completion per D-11)*

- [x] 06-02-PLAN.md — godoo.client.typed (OdooModel Protocol + Ref[T] dataclass, stdlib-only) and godoo.client._pydantic_transform (OdooBaseModel + wire transforms + derive_partial_model) with unit tests (TYPED-06, TYPED-07)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 06-03-PLAN.md — @overload pairs on read/search_read with lazy _pydantic_transform import, [typed] optional extra in pyproject.toml, subprocess isolation test, dispatch unit tests (TYPED-03, TYPED-04, TYPED-05)

**Open Decisions**: OD-1 (partial-read strategy) and OD-2 (boolean False-coercion) resolved in 06-CONTEXT.md as D-01 (All-Optional via Pydantic create_model with __base__=) and D-02 (bool annotation skips False→None coercion).

### Phase 7: Pydantic CLI Generator

**Goal**: A developer can run a single CLI command against their live Odoo instance and receive a Pydantic model package — one file per model, plus a barrel `__init__.py` — that is immediately usable with the typed-read layer from Phase 6
**Depends on**: Phase 6
**Requirements**: TYPED-01, TYPED-02
**Success Criteria** (what must be TRUE):

  1. `godoo-introspect generate --output ./models/` (credentials from `config_from_env()` by default; `--url`/`--db`/`--user`/`--password` flags override; `--models pat1,pat2,...` accepts fnmatch-style glob patterns matched against Odoo technical model names; `--all` generates every installed model) completes and writes model files to the specified output path
  2. Generated model files: each model has `id: int` as required; all other fields are `Optional[T] = None`; selection fields use `Literal[…]` with instance-actual registered values; many2one fields typed as `Ref[TargetClass]` when the target is in the generated set (with a cross-import), degraded to `Ref[int]` with a trailing `# <odoo.model>` comment when not; one2many/many2many fields are typed as `list[int]`; all generated files must compile without errors
  3. Every generated model carries `__odoo_model__: ClassVar[str]` set to the Odoo technical name (e.g. `"res.partner"`), enabling `client.read(ResPartner, …)` dispatch without pydantic at dispatch time
  4. `pydantic>=2.13` and `typer>=0.26` are declared as runtime deps of `godoo-introspection` (not extras); the Pydantic emitter **replaces** the TypedDict emitter — the existing TypedDict codegen path and its tests are removed and `type_mapper.py` is migrated to Pydantic type forms; this is a breaking change to the v0.2.0 public API (INTRO-03) and must be changelog-noted at release

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 07-01-PLAN.md — Delete TypedDict artifacts; migrate type_mapper.py to Pydantic forms; replace CodeGenerator.generate() with Pydantic emitter; rewrite test_type_mapper.py and test_codegen.py (TYPED-01, TYPED-02)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 07-02-PLAN.md — pyproject.toml deps + uv.lock; create cli.py typer entrypoint; create test_cli.py (TYPED-01, TYPED-02)

### Phase 8: Pyodide Spike

**Goal**: The team has an empirically grounded, written verdict on whether godoo can run in a Pyodide/browser environment — what transport strategy works, what Python floor is required — and an explicit go/no-go decision for committing to a browser build in a future milestone
**Depends on**: Phase 6 (transport seam from BROWSER-01 is a prerequisite; no other Phase 7 dependency)
**Requirements**: BROWSER-02, BROWSER-03
**Success Criteria** (what must be TRUE):

  1. The spike executes an actual Odoo JSON-RPC call (not just an import check) from within a Pyodide runtime (Marimo, JupyterLite, or equivalent); the call is cross-origin and made **over HTTPS** against a real TLS-terminated Odoo endpoint, exercising browser TLS-via-fetch, CORS, and mixed-content behaviour — a plain-HTTP or localhost call does NOT satisfy this criterion
  2. A written verdict documents which of the three transport strategies was tested (stock httpx via Pyodide-bundled Fetch adapter / `pyodide-httpx` 0.2.0 / custom `pyfetch`-backed `AsyncTransport`) and which worked or failed, with error output for failures
  3. The verdict includes a Python-floor recommendation: "drop `requires-python` to `>=3.12` for a browser-specific build" OR "defer until Pyodide ships CPython ≥3.14" — with the rationale stated
  4. An explicit go/no-go decision is recorded: a "go" with required breaking changes escalates to v2.0 planning; a "no-go" defers BROWSER-F1/F2 to the backlog

**Plans**: 4 plans
**Note**: BROWSER-02 and BROWSER-03 are a *spike* producing a decision and evidence, not a shipping feature. No `godoo[browser]` package ships this phase regardless of verdict. All spike code is non-shipping committed evidence under `spikes/08-pyodide/` (D-09) and is exempt from the `requires-python >=3.14` gate.
**Open Decision**: OD-3 (httpx vs POSIX socket in Pyodide) is resolved empirically during this spike; does not block Phases 5-7.
Plans:
**Wave 1** *(parallel — disjoint files, both autonomous)*

- [x] 08-01-PLAN.md — PyfetchTransport prototype (strategy 3) + raw Pyodide HTML page running all 3 strategies + README (BROWSER-02)
- [x] 08-02-PLAN.md — ACA multi-container Bicep (Odoo+Postgres, HTTPS ingress, origin-scoped CORS, minReplicas:1) + self-destruct Bicep (UAMI + RG Contributor + Logic App TTL) + deploy notes (BROWSER-02)

**Wave 2** *(blocked on Waves 1; NOT autonomous — live az deployment + in-browser run)*

- [ ] 08-03-PLAN.md — Deploy the endpoint, run the in-browser spike, write 08-SPIKE.md (SC-1 call + SC-2 per-strategy table + SC-3 Python-floor rec) (BROWSER-02, BROWSER-03)

**Wave 3** *(blocked on Wave 2)*

- [ ] 08-04-PLAN.md — Standalone go/no-go ADR (docs/adr/0001, MADR-style, applies D-10 bar) + mkdocs nav entry (BROWSER-03)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Client Parity | v1.0 | 5/5 | Complete | 2026-05-19 |
| 2. Introspection | v1.0 | 2/2 | Complete | 2026-05-21 |
| 3. Testcontainers Parity | v1.0 | 3/3 | Complete | 2026-05-22 |
| 4. Release | v1.0 | 3/3 | Complete | 2026-05-22 |
| 4.1. Package READMEs | v1.0 | 1/1 | Complete | 2026-05-22 |
| 5. Directory Rename | v1.1 | 2/2 | Complete    | 2026-05-28 |
| 6. Transport Seam & Typed Models Core | v1.1 | 3/3 | Complete   | 2026-05-28 |
| 7. Pydantic CLI Generator | v1.1 | 2/2 | Complete    | 2026-06-01 |
| 8. Pyodide Spike | v1.1 | 2/4 | In Progress|  |

## Backlog

### Phase 999.1: Rename packages/godoo to packages/godoo-client for dist consistency (SUPERSEDED)

> **Superseded by Phase 5** (Directory Rename) in milestone v1.1. Backlog item promoted to active roadmap.

### Phase 999.2: Update godoo-testcontainers PostgreSQL to v18 (latest stable) (BACKLOG)

**Goal:** [Captured for future planning] Bump the PostgreSQL image pinned by `godoo-testcontainers` to v18 (currently the latest stable). Validate that the Odoo versions exercised in integration tests (17/18/19) start cleanly against PG 18; update any version pin in `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` and related fixtures.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)
