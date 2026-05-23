# Roadmap: godoo-py

## Milestones

- ✅ **v1.0 Parity & Release** — Phases 1-4.1 (shipped 2026-05-22) — full archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

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

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Client Parity | v1.0 | 5/5 | Complete | 2026-05-19 |
| 2. Introspection | v1.0 | 2/2 | Complete | 2026-05-21 |
| 3. Testcontainers Parity | v1.0 | 3/3 | Complete | 2026-05-22 |
| 4. Release | v1.0 | 3/3 | Complete | 2026-05-22 |
| 4.1. Package READMEs | v1.0 | 1/1 | Complete | 2026-05-22 |

## Backlog

### Phase 999.1: Rename packages/godoo to packages/godoo-client for dist consistency (BACKLOG)

**Goal:** [Captured for future planning]
**Requirements:** TBD
**Plans:** 0 plans

Context: the PyPI dist is already named `godoo-client` (`packages/godoo/pyproject.toml`),
but the workspace directory is still `packages/godoo`. Rename the directory to
`packages/godoo-client` to close the directory↔dist-name gap. The import module name
(`godoo`) is a separate decision — clarify whether it stays `godoo` or also changes.

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)
