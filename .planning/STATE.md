---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Parity & Release
status: Awaiting next milestone
last_updated: "2026-05-22T18:54:23.117Z"
last_activity: 2026-05-22 — Milestone v1.0 completed and archived
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 14
  completed_plans: 14
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-22)

**Core value:** The Python family member reaches feature parity with the TypeScript core-3 libraries
**Current focus:** Planning next milestone (v1.0 Parity & Release shipped — three packages live on PyPI)

## Current Position

Phase: Milestone v1.0 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-05-22 — Milestone v1.0 completed and archived

## Performance Metrics

**Velocity:**

- Total plans completed: 9
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 5 | - | - |
| 03 | 3 | - | - |
| 04.1 | 1 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 03 P01 | 2 | 2 tasks | 3 files |
| Phase 03-testcontainers-parity P2 | 30m | 3 tasks | 4 files |
| Phase 03-testcontainers-parity P3 | 4 | 3 tasks | 6 files |
| Phase 04-release P02 | 45 | 3 tasks | 92 files |

## Accumulated Context

### Roadmap Evolution

- Phase 04.1 inserted after Phase 4: Package READMEs to fix empty PyPI pages; publish 0.2.1 (URGENT)

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Incorporate existing repo via full-history merge — preserves provenance
- [Init]: `godoo` package → `godoo-client` on PyPI; other package names unchanged
- [Init]: v1 scope = SEED §2 parity gaps + adjacent bugs in the same files (FIXES-01/02/03)
- [Init]: Phases 2 and 3 may run in parallel after Phase 1 completes (packages are independent)
- [Phase ?]: Drop TESTC-03/04/05 (partners/projects/users provisioners) from v1 — declarative seeding belongs to godoo-stateman (D-Drop-1)
- [Phase ?]: Namespace invariant established
- [Phase ?]: PyPI names: godoo-client, godoo-introspection, godoo-testcontainers
- [Phase ?]: from godoo.client.*, godoo.introspection.*, godoo.testcontainers.*

### Pending Todos

None yet.

### Blockers/Concerns

None — v1.0 blockers resolved (introspection package built in Phase 2; `godoo`→`godoo-client` rename shipped in Phase 4).

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Compatibility | COMPAT-01: Relax Python floor to 3.11/3.12 | Deferred to post-v1 | Init |
| Client | CLIENT-V2-01: Auto re-auth on session expiry | Deferred to v2 | Init |
| Performance | PERF-01: `read_group` SUM for cash balance | Deferred to backlog | Init |
| Performance | PERF-02: CDC two-round-trip optimization | Deferred to backlog | Init |
| UAT | Phase 03 03-HUMAN-UAT.md | Resolved, 0 pending scenarios — acknowledged non-blocking | v1.0 close |
| Seed | SEED-001: browser/Pyodide compatibility | Dormant — future idea, never in v1 scope | v1.0 close |
| Tech debt | release.yml Node 20 actions (checkout/setup-uv) emit deprecation warnings | Needs version bump | v1.0 close |
| Tech debt | snapshot.py partial snapshot key for direct OdooTestContainer users | Documented limitation (plan 03-02) | v1.0 close |

## Session Continuity

Last session: 2026-05-22 — v1.0 milestone closed and archived
Stopped at: Milestone complete; awaiting /gsd-new-milestone

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
