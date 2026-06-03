---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Typed Relations, Writes & Error Surface
status: planning
last_updated: "2026-06-03T11:21:14.549Z"
last_activity: 2026-06-03
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
  percent: 38
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-27)

**Core value:** The Python family member reaches feature parity with the TypeScript core-3 libraries
**Current focus:** Phase 12 — tech debt close out

## Current Position

Phase: 12
Plan: Not started
Status: Ready to plan
Last activity: 2026-06-03

```
Phase 9  [          ] Not started
Phase 10 [          ] Not started
Phase 11 [###       ] 1/3 plans complete
Phase 12 [          ] Not started
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
| 07 | 2 | - | - |
| 10 | 2 | - | - |
| 11 | 3 | - | - |

*v1.2 metrics will populate as phases complete.*
| Phase 10-typed-relation-resolution P01 | 20m | 2 tasks | 5 files |
| Phase 10-typed-relation-resolution P02 | 5 | 2 tasks | 2 files |
| Phase 11-codegen-metadata-typed-writes P02 | 30 | 2 tasks | 3 files |
| Phase 11-codegen-metadata-typed-writes P03 | 20min | 2 tasks | 2 files |

## Accumulated Context

### Roadmap Evolution

- v1.1 Phases 5-8 created 2026-05-27 from research/SUMMARY.md build order
- Phase 999.1 backlog item (dir rename) superseded by Phase 5
- Build order validated by research: rename → transport seam + typed-models core → Pydantic CLI generator → Pyodide spike
- v1.2 Phases 9-12 created 2026-06-02 from research/SUMMARY.md + REQUIREMENTS.md build order
- Phase 999.3 (codegen→typed-read round-trip) promoted to Phase 11 as TEST-01
- Phase 999.4 (wire-transforms-through-dispatch) promoted to Phase 10 as TEST-02

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Recent decisions affecting current work:

- [v1.1-init]: Phase 5 = standalone dir rename; must be atomic and go first (7 config locations affected)
- [v1.1-init]: BROWSER-01 (transport seam) rides with typed-models core in Phase 6 — purely additive, establishes seam for spike
- [v1.1-init]: BROWSER-02/03 (Pyodide spike) is a *decision artifact*, not a build — Phase 8 success criteria are written verdict + go/no-go, not shipped code
- [v1.1-init]: Phase 8 depends only on Phase 6 (transport seam), not Phase 7 (CLI generator)
- [v1.2-init]: Phase 9 = standalone ERR surface; isolated to errors.py, contains the one breaking change (`.data`→`.raw`) in isolation
- [v1.2-init]: Phase 10 = REL-01 (Ref._target_cls) + REL-02..05 dispatch + TEST-02 (wire-transforms-through-dispatch exercises the same dispatch chain being built)
- [v1.2-init]: Phase 11 = GEN-01 (codegen metadata) must precede WRITE-04 (readonly exclusion); TEST-01 (codegen→typed-read round-trip) closes 999.3 alongside the codegen change
- [v1.2-init]: Phase 12 = DEBT-01..04 independent cleanup; placed last so it does not block typed-layer work
- [v1.2-init]: TEST-01/02 folded into Phases 11/10 respectively (coarse granularity; test belongs adjacent to the feature it covers)
- [Phase ?]: read() uses Any + None default for Ref overload compatibility
- [11-01]: D-04 narrowed readonly rule: readonly=True OR (store=False AND compute is not None); plain non-stored inverse fields are writable
- [11-01]: from pydantic import Field emitted only when at least one field carries extra metadata (conditional header)
- [11-01]: x2many fields use Field(default_factory=list, ...) not mutable default=[] to avoid PydanticUserError
- [Phase ?]: WRITE-01..05: _serialize_for_write iterates model_fields_set, skips odoo_readonly, raises on odoo_x2many, Ref->int, None->False, datetime/date->ISO
- [Phase ?]: 11-03: _serialize_for_write skips id field — record identifier is passed separately in [[model.id], payload], not part of the write values dict

### Open Decisions (settle before relevant phase)

| ID | Settle Before | Decision | Research Recommendation |
|----|---------------|----------|------------------------|
| OD-1 | Phase 6 | Partial-read strategy when `fields=[...]` is passed with a model class | All-Optional generated fields; `model_construct()` only as documented escape hatch |
| OD-2 | Phase 6 | Boolean `False`-coercion in wire transform | Emit boolean fields as plain `bool` (non-optional); `@model_validator` skips coercion for `bool`-annotated fields |
| OD-3 | ~~Phase 8~~ | ~~httpx vs POSIX socket in Pyodide~~ | **RESOLVED (08-04 ADR):** GO — Strategy 3 (PyfetchTransport) meets D-10 bar; Python floor Option A (defer to Pyodide 3.14) |
| ODD-1 | Phase 10 | Ref runtime target-class mechanism (`_target_cls` field name + annotation type) | Option A: `_target_cls: type \| None = field(default=None, compare=False, hash=False, repr=False)` |
| ODD-2 | Phase 11 | x2many write default strategy (ADD / EXCLUDE / RAISE for `list[int]`) | RAISE — forces explicitness; safest vs silent-destructive REPLACE; owner must confirm |
| ODD-3 | Phase 11 | Read-only/computed field exclusion on write (codegen metadata vs hardcoded set) | Option A (codegen metadata `json_schema_extra={"odoo_readonly": True}`); depends on GEN-01 landing first |
| ODD-4 | Phase 9 | SEED-003 `.data`→`.raw` rename scope; `to_json()` shape; backward-compat alias for `"details"` key | Breaking rename; `data=` constructor kwarg retained; no compat alias; `to_json()` drops `"details"`, adds structured fields |

### Pending Todos

- Settle ODD-1 before planning Phase 10
- Settle ODD-2 and ODD-3 before planning Phase 11
- Settle ODD-4 before planning Phase 9

### Blockers/Concerns

None — roadmap is clear; open design decisions require owner judgment (not research).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260601-w2x | Fix 10 phase 06/07 code-review findings (pydantic transform, typed dispatch, codegen, cli) | 2026-06-01 | b21e35c | [260601-w2x-fix-phase-06-07-code-review-findings-pyd](./quick/260601-w2x-fix-phase-06-07-code-review-findings-pyd/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Compatibility | COMPAT-01: Relax Python floor to 3.11/3.12 | Deferred to post-v1 | Init |
| Performance | PERF-01: `read_group` SUM for cash balance | Backlog | Init |
| Performance | PERF-02: CDC two-round-trip optimization | Backlog | Init |
| Browser (v2.0) | BROWSER-F1: `godoo[browser]` extra | GO verdict received (ADR-0001); escalated to v2.0 planning; gated on Pyodide CPython >=3.14 | v1.1 scope |
| Browser (v2.0) | BROWSER-F2: Relax Python floor for Pyodide | GO verdict received (ADR-0001, Option A); gated on Pyodide 3.14 stable release | v1.1 scope |
| Typed models (v2+) | REL-ADV-01: Arbitrary-depth relation nesting | Single-level (v1.2) covers common case; recursion/cycle design deferred | v1.2 scope |
| Typed models (v1.3+) | WRITE-ADV-01: x2many typed-write ergonomics (command-tuple helpers) | RAISE strategy ships v1.2; helpers deferred | v1.2 scope |
| Typed models (v1.3+) | WRITE-ADV-02: Typed write of nested/child records | Deferred to future milestone | v1.2 scope |
| Tech debt | release.yml Node 20 actions deprecation warnings | Addressed in Phase 12 (DEBT-01) | v1.0 close |
| Tech debt | snapshot.py partial snapshot key for direct container users | Addressed in Phase 12 (DEBT-04) | v1.0 close |

## Session Continuity

Last session: 2026-06-03T11:21:14.534Z
Stopped at: Phase 12 context gathered

## Operator Next Steps

- Run Phase 11 Plan 02 (WRITE-01..05: _serialize_for_write + client.create/write typed overloads)
- Settle ODD-4 (`.data`→`.raw` scope) then run `/gsd:plan-phase 9`
- Settle ODD-1 before planning Phase 10
