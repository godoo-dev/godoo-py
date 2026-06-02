# Roadmap: godoo-py

## Milestones

- ✅ **v1.0 Parity & Release** — Phases 1-4.1 (shipped 2026-05-22) — full archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Typed Models & Browser Reach** — Phases 5-8 (shipped 2026-06-02) — full archive: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

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

<details>
<summary>✅ v1.1 Typed Models & Browser Reach (Phases 5-8) — SHIPPED 2026-06-02</summary>

- [x] Phase 5: Directory Rename (2/2 plans) — completed 2026-05-28
- [x] Phase 6: Transport Seam & Typed Models Core (3/3 plans) — completed 2026-05-28
- [x] Phase 7: Pydantic CLI Generator (2/2 plans) — completed 2026-06-01
- [x] Phase 8: Pyodide Spike (4/4 plans) — completed 2026-06-02

Instance-derived Pydantic typed models with a typed-read dispatch layer (`client.read(ModelClass, ids)` → `list[ModelClass]`), the `packages/godoo`→`packages/godoo-client` directory rename (PEP 420 namespace preserved), a pluggable transport seam (`Transport` Protocol + `transport_factory` hook), and an empirically grounded Pyodide/browser go/no-go verdict (ADR-0001: GO, deferred to v2.0 pending Pyodide CPython ≥3.14). The Pydantic generator replaces the v1.0 TypedDict generator (breaking, changelog-noted). Full phase detail preserved in [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md).

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Client Parity | v1.0 | 5/5 | Complete | 2026-05-19 |
| 2. Introspection | v1.0 | 2/2 | Complete | 2026-05-21 |
| 3. Testcontainers Parity | v1.0 | 3/3 | Complete | 2026-05-22 |
| 4. Release | v1.0 | 3/3 | Complete | 2026-05-22 |
| 4.1. Package READMEs | v1.0 | 1/1 | Complete | 2026-05-22 |
| 5. Directory Rename | v1.1 | 2/2 | Complete | 2026-05-28 |
| 6. Transport Seam & Typed Models Core | v1.1 | 3/3 | Complete | 2026-05-28 |
| 7. Pydantic CLI Generator | v1.1 | 2/2 | Complete | 2026-06-01 |
| 8. Pyodide Spike | v1.1 | 4/4 | Complete | 2026-06-02 |

## Backlog

### Phase 999.1: Rename packages/godoo to packages/godoo-client for dist consistency (SUPERSEDED)

> **Superseded by Phase 5** (Directory Rename) in milestone v1.1. Backlog item promoted to active roadmap.

### Phase 999.2: Update godoo-testcontainers PostgreSQL to v18 (latest stable) (BACKLOG)

**Goal:** [Captured for future planning] Bump the PostgreSQL image pinned by `godoo-testcontainers` to v18 (currently the latest stable). Validate that the Odoo versions exercised in integration tests (17/18/19) start cleanly against PG 18; update any version pin in `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` and related fixtures.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.3: Codegen→typed-read round-trip test (BACKLOG)

**Goal:** [Captured for future planning] Add an end-to-end test that feeds a `godoo-introspection` codegen-generated Pydantic model class through `client.read(ModelClass, ids)` dispatch. Surfaced by the v1.1 milestone audit (2026-06-02): codegen importlib-roundtrip and typed-read dispatch are each tested in isolation, leaving the codegen-output ↔ read-dispatch contract verified by inspection only. Suggested test: `test_generate_importlib_roundtrip_with_client_read` — generate/load a model, then dispatch it through `client.read`. Tech-debt, non-blocking.
**Requirements:** TBD (touches the TYPED-01 / TYPED-02 → TYPED-03 boundary)
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.4: Wire-transforms-through-dispatch test (BACKLOG)

**Goal:** [Captured for future planning] Add a typed-dispatch test that exercises the `Ref` / `date` / `datetime` wire transforms through the full `client.read` chain. Surfaced by the v1.1 milestone audit (2026-06-02): these transforms are tested at `OdooBaseModel.model_validate` level in `test_pydantic_transform.py`, but no `test_typed_dispatch.py` case uses a model with `Ref`/`date` fields, so they are not exercised end-to-end through dispatch. Suggested: a dispatch test using a model with `Ref` and `date`/`datetime` fields. Tech-debt, non-blocking.
**Requirements:** TBD (touches TYPED-06)
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)
