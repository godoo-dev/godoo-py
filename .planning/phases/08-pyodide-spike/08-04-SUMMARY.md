---
phase: 08-pyodide-spike
plan: "04"
subsystem: docs/adr
tags: [adr, pyodide, browser, go-no-go, decision, mkdocs]
dependency_graph:
  requires:
    - .planning/phases/08-pyodide-spike/08-SPIKE.md   # evidence consumed by this ADR
    - .planning/phases/08-pyodide-spike/08-03-SUMMARY.md  # spike run complete
  provides:
    - docs/adr/0001-pyodide-browser-go-no-go.md  # durable go/no-go decision (D-08)
  affects:
    - mkdocs.yml  # ADR nav section added
    - .planning/STATE.md  # phase 8 complete
    - .planning/ROADMAP.md  # phase 8 4/4
tech_stack:
  added: []
  patterns:
    - MADR-style ADR at docs/adr/ (first ADR in repo — establishes convention)
    - mkdocs nav ADR section (docs-root-relative path)
key_files:
  created:
    - docs/adr/0001-pyodide-browser-go-no-go.md
  modified:
    - mkdocs.yml
decisions:
  - "GO: D-10 bar met by Strategy 3 (PyfetchTransport via transport_factory seam)"
  - "Python floor: Option A — defer browser support until Pyodide ships CPython >=3.14"
  - "Browser work escalates to v2.0 planning; BROWSER-F1/F2 remain gated on Pyodide 3.14 release"
  - "Strategy 2 (pyodide-httpx 0.2.0) is a confirmed no-go as a shipping dependency"
  - "docs/adr/ convention established (ADR-0001 is the first ADR in the repo)"
metrics:
  duration: "2 minutes"
  completed: "2026-06-02"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
requirements-completed: [BROWSER-03]
---

# Phase 8 Plan 04: Go/No-Go ADR Summary

**One-liner:** MADR-style ADR recorded at docs/adr/0001: GO decision with Strategy 3 (PyfetchTransport)
as the maintainable shipping path, Option A Python floor (defer to Pyodide CPython >=3.14), browser
work escalating to v2.0 planning.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Write the standalone go/no-go ADR (MADR-style) | 76a252c | `docs/adr/0001-pyodide-browser-go-no-go.md` |
| 2 | Add the ADR to the mkdocs nav | a91d864 | `mkdocs.yml` |

## What Was Done

### Task 1 — MADR-style ADR

Written at `docs/adr/0001-pyodide-browser-go-no-go.md` with sections: Status (`accepted`), Context,
Considered Options, Decision, Consequences.

**Decision: GO.** The D-10 go bar is met. Strategy 3 (custom `PyfetchTransport` via `transport_factory`)
made a complete cross-origin HTTPS authenticate + `res.users` JSON-RPC round-trip. It is the designated
maintainable shipping path. Strategy 1 (stock httpx) also worked but its routing mechanism needs
confirmation before being designated primary. Strategy 2 (pyodide-httpx 0.2.0) is a confirmed no-go.

**Python floor: Option A.** Defer browser support until Pyodide ships CPython >=3.14. Aligns with
PEP 776/783 (Emscripten = CPython tier-3 target from 3.14). Keeps monorepo `>=3.14` floor coherent.

**Consequences stated:**
- GO with required breaking changes escalates to v2.0 planning
- BROWSER-F1 (`godoo[browser]` extra) and BROWSER-F2 (Python floor relax) remain gated — deferred
  to backlog until Pyodide 3.14 ships
- `PyfetchTransport` prototype in `spikes/` seeds BROWSER-F1 implementation
- Strategy 1 caveat: must confirm httpx → Pyodide fetch routing is a stable documented API before
  designating it a shipping path

The ADR references `08-SPIKE.md` for per-strategy evidence (no credential/FQDN committed).
This establishes the `docs/adr/` convention (first ADR in the repository).

### Task 2 — mkdocs nav update

Added an `ADR` section after `Testing` in `mkdocs.yml` with a single entry:
`adr/0001-pyodide-browser-go-no-go.md` (docs-root-relative path). Existing nav, plugins,
`markdown_extensions`, and `mkdocstrings` paths are unchanged. YAML parses cleanly.

## Acceptance Check Results

| Check | Result |
|-------|--------|
| MADR sections (Status, Context, Decision, Consequences) >= 4 | PASS — 4 headings found |
| go/no-go/conditional mention >= 1 | PASS — 11 matches |
| 08-SPIKE reference >= 1 | PASS — 3 references |
| mkdocs.yml nav adr entry >= 1 | PASS — 1 entry |
| YAML parses cleanly | PASS |
| No secret/FQDN/credential in ADR | PASS — grep clean |

## Deviations from Plan

None — plan executed exactly as written. The `Status` section was initially formatted as bold text
(inline metadata) before being promoted to a proper `## Status` heading to satisfy the automated
section-count check. Both approaches are valid MADR; the heading form is more conventional.

## Threat Surface Scan

The ADR is a public documentation file. Verified:
- No FQDN, credential, client name, or firm name appears in the ADR text
- No Azure endpoint references (the torn-down ACA FQDN is referenced only in `08-SPIKE.md`)
- T-08-11 (Information Disclosure) mitigated: ADR contains only technical decision content

## Self-Check: PASSED

- `docs/adr/0001-pyodide-browser-go-no-go.md` exists: FOUND
- Commit 76a252c exists: FOUND (`docs(08): write go/no-go ADR for Pyodide browser support (ADR-0001)`)
- Commit a91d864 exists: FOUND (`docs(08): add ADR nav section to mkdocs.yml`)
