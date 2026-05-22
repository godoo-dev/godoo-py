---
phase: "03-testcontainers-parity"
plan: 1
subsystem: "godoo-testcontainers"
tags: ["py.typed", "charter", "scope-drop", "PEP-561"]
dependency_graph:
  requires: []
  provides:
    - "packages/godoo-testcontainers/src/godoo_testcontainers/py.typed"
    - ".planning/REQUIREMENTS.md (struck TESTC-03/04/05, coverage count 26)"
    - ".planning/PROJECT.md (D-Drop-1 amendments)"
  affects:
    - "packages/godoo-testcontainers (py.typed enables mypy --strict)"
    - ".planning/REQUIREMENTS.md"
    - ".planning/PROJECT.md"
tech_stack:
  added: []
  patterns:
    - "py.typed empty marker (PEP 561) — identical to CLIENT-10 and INTRO-07 precedents"
key_files:
  created:
    - "packages/godoo-testcontainers/src/godoo_testcontainers/py.typed"
  modified:
    - ".planning/REQUIREMENTS.md"
    - ".planning/PROJECT.md"
decisions:
  - "ROADMAP.md already had correct D-Drop-1 + D-Snap-3-amendment text from context gathering — no changes applied"
  - "pyproject.toml already declares hatchling wheel target packages = ['src/godoo_testcontainers'] — py.typed auto-included"
  - "Both packages already have 'Typing :: Typed' classifier — no classifier change needed"
metrics:
  duration: "~2 minutes"
  completed: "2026-05-22T11:16:27Z"
---

# Phase 3 Plan 1: Charter Amendments + py.typed Summary

**One-liner:** py.typed PEP 561 marker added to godoo-testcontainers; TESTC-03/04/05 struck from v1 scope via D-Drop-1 charter amendments across REQUIREMENTS.md and PROJECT.md.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create py.typed PEP 561 marker for godoo-testcontainers | bb07968 | packages/godoo-testcontainers/src/godoo_testcontainers/py.typed (created, 0 bytes) |
| 2 | Charter amendments — strike TESTC-03/04/05, fix path text, update PROJECT.md | fb9ce05 | .planning/REQUIREMENTS.md, .planning/PROJECT.md |

## What Was Built

**Task 1 — py.typed marker (TESTC-08):**
- Created an empty `py.typed` file at `packages/godoo-testcontainers/src/godoo_testcontainers/py.typed`
- File is 0 bytes, identical to the `packages/godoo/src/godoo/py.typed` precedent (CLIENT-10)
- Hatchling wheel target already covers `src/godoo_testcontainers/` — no `pyproject.toml` change needed
- `mypy --strict packages/godoo-testcontainers/src` exits 0 (3 source files, no issues)

**Task 2 — Charter amendments (D-Drop-1 + D-Snap-3-amendment):**
- `REQUIREMENTS.md`: TESTC-03/04/05 struck with D-Drop-1 rationale (declarative seeding belongs to godoo-stateman)
- `REQUIREMENTS.md`: TESTC-01 path corrected from `~/.odoo-testcontainers/snapshots/` to `cwd/.odoo-testcontainers/snapshots/`
- `REQUIREMENTS.md`: Traceability rows for TESTC-03/04/05 marked `Dropped (D-Drop-1)` with strikethrough
- `REQUIREMENTS.md`: Coverage count updated to `26 total (INTRO-05, TESTC-03, TESTC-04, TESTC-05 dropped)`, `Mapped to phases: 26 (100%)`
- `REQUIREMENTS.md`: Footer updated to 2026-05-22 with amendment description
- `PROJECT.md`: Active block replaces `Four resource provisioners (partners, projects, users, properties)` with `Properties provisioner (ir.config_parameter k/v via ConfigParameterHelper)`
- `PROJECT.md`: Key Decisions row added for D-Drop-1
- `ROADMAP.md`: Already had all correct amendments from context gathering phase — no changes required

## Deviations from Plan

None — plan executed exactly as written.

The ROADMAP.md was already correct (Task 2 action described applying edits that the context session had already made). This was confirmed by re-reading the Phase 3 section before attempting any edits. No changes were applied to ROADMAP.md.

## Verification Results

- `py.typed` exists and is 0 bytes: PASSED
- `mypy --strict packages/godoo-testcontainers/src` exits 0: PASSED
- `cwd/.odoo-testcontainers` appears in REQUIREMENTS.md (1 occurrence): PASSED
- `cwd/.odoo-testcontainers` appears in ROADMAP.md (1 occurrence): PASSED
- `~/.odoo-testcontainers` absent from both files: PASSED
- `D-Drop-1` present in REQUIREMENTS.md, ROADMAP.md, PROJECT.md: PASSED
- `Four resource provisioners` absent from PROJECT.md: PASSED
- Coverage count = 26 (100% mapped): PASSED
- All charter verification assertions: PASSED

## Known Stubs

None — this plan creates a marker file and edits planning documents only; no implementation stubs.

## Threat Flags

None — edits are project-local markdown files and an empty packaging marker; no new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

Files created/modified:
- `packages/godoo-testcontainers/src/godoo_testcontainers/py.typed` — FOUND (0 bytes)
- `.planning/REQUIREMENTS.md` — FOUND (contains `cwd/.odoo-testcontainers`, `D-Drop-1`, coverage=26)
- `.planning/PROJECT.md` — FOUND (contains `ConfigParameterHelper`, `D-Drop-1` row)

Commits:
- `bb07968` — FOUND (chore(03-01): add py.typed marker)
- `fb9ce05` — FOUND (docs(03-01): apply D-Drop-1 / D-Snap-3-amendment charter edits)
