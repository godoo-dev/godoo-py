---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Typed Models & Browser Reach
status: executing
last_updated: "2026-06-01T19:59:33.303Z"
last_activity: 2026-06-01 -- Phase 07 planning complete
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 7
  completed_plans: 5
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-27)

**Core value:** The Python family member reaches feature parity with the TypeScript core-3 libraries
**Current focus:** Phase 06 — transport-seam-typed-models-core

## Current Position

Phase: 06 (transport-seam-typed-models-core) — COMPLETE (2026-05-28)
Phase: 07 (pydantic-cli-generator) — NEXT
Status: Ready to execute
Last activity: 2026-06-01 -- Phase 07 planning complete

```
Progress: [██████████] 100%
```

## Performance Metrics

**Velocity (v1.0 reference):**

- Total plans completed (v1.0): 14 across 5 phases
- Average phase duration: ~1 day
- Total execution time: ~5 days (2026-05-19 to 2026-05-22)

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 5 | - | - |
| 02 | 2 | - | - |
| 03 | 3 | - | - |
| 04 | 3 | - | - |
| 04.1 | 1 | - | - |
| 05 | 2 | - | - |

*v1.1 metrics will populate as phases complete.*

## Accumulated Context

### Roadmap Evolution

- v1.1 Phases 5-8 created 2026-05-27 from research/SUMMARY.md build order
- Phase 999.1 backlog item (dir rename) superseded by Phase 5
- Build order validated by research: rename → transport seam + typed-models core → Pydantic CLI generator → Pyodide spike

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Recent decisions affecting current work:

- [v1.1-init]: Phase 5 = standalone dir rename; must be atomic and go first (7 config locations affected)
- [v1.1-init]: BROWSER-01 (transport seam) rides with typed-models core in Phase 6 — purely additive, establishes seam for spike
- [v1.1-init]: BROWSER-02/03 (Pyodide spike) is a *decision artifact*, not a build — Phase 8 success criteria are written verdict + go/no-go, not shipped code
- [v1.1-init]: Phase 8 depends only on Phase 6 (transport seam), not Phase 7 (CLI generator)
- [v1.1-init]: OD-1 (partial-read strategy) and OD-2 (boolean False-coercion) must be settled before Phase 6 implementation; research recommends All-Optional + OD-2 Option A
- [v1.1-init]: OD-3 (httpx-in-Pyodide) resolved empirically during Phase 8 spike; does not block Phases 5-7

### Open Decisions (settle before relevant phase)

| ID | Settle Before | Decision | Research Recommendation |
|----|---------------|----------|------------------------|
| OD-1 | Phase 6 | Partial-read strategy when `fields=[...]` is passed with a model class | All-Optional generated fields; `model_construct()` only as documented escape hatch |
| OD-2 | Phase 6 | Boolean `False`-coercion in wire transform | Emit boolean fields as plain `bool` (non-optional); `@model_validator` skips coercion for `bool`-annotated fields |
| OD-3 | Phase 8 | httpx vs POSIX socket in Pyodide | Empirical spike only — conflicting researcher findings; must run actual HTTP call |

### Pending Todos

- Settle OD-1 and OD-2 before planning Phase 6

### Blockers/Concerns

None — roadmap is clear; Pyodide/CPython 3.14 gap is a known spike constraint, not a blocker.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Compatibility | COMPAT-01: Relax Python floor to 3.11/3.12 | Deferred to post-v1 | Init |
| Performance | PERF-01: `read_group` SUM for cash balance | Backlog | Init |
| Performance | PERF-02: CDC two-round-trip optimization | Backlog | Init |
| Browser (conditional) | BROWSER-F1: `godoo[browser]` extra | Gated on Phase 8 go verdict | v1.1 scope |
| Browser (conditional) | BROWSER-F2: Relax Python floor for Pyodide | Gated on Phase 8 go verdict | v1.1 scope |
| Typed models | TYPED-F1: Nested relational model fetch | Deferred to v2+ | v1.1 scope |
| Typed models | TYPED-F2: Typed write/create paths | Deferred to v2+ | v1.1 scope |
| Tech debt | release.yml Node 20 actions deprecation warnings | Needs version bump | v1.0 close |
| Tech debt | snapshot.py partial snapshot key for direct container users | Documented limitation | v1.0 close |

## Session Continuity

Last session: 2026-06-01T19:04:59.102Z
Stopped at: Phase 7 context gathered

## Operator Next Steps

- Push `develop` branch to trigger CI (ruff / mypy / pytest / build from packages/godoo-client/)
- After CI is green: settle OD-1 and OD-2 before planning Phase 06 (typed models)
