---
phase: 05-directory-rename
plan: 01
subsystem: infra
tags: [uv, workspace, git-mv, pyproject, ci, mypy, mkdocs]

# Dependency graph
requires: []
provides:
  - "packages/godoo-client/ with full git blame history (was packages/godoo/)"
  - "uv.lock regenerated; editable paths reference packages/godoo-client"
  - "All tool-config path references updated: pyproject.toml, test.yml, mkdocs.yml, CONTRIBUTING.md, CLAUDE.md"
  - "D-02 stale build_command entry removed (uv build --package godoo)"
  - "D-01 full sweep clean: zero bare packages/godoo refs in tracked source"
affects: [06-typed-models, 07-cli-generator, 08-pyodide-spike]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Directory name aligns with PyPI dist name (packages/godoo-client matches project.name = godoo-client)"
    - "PEP 420 namespace package invariant: packages/godoo-client/src/godoo/ has no __init__.py"

key-files:
  created: []
  modified:
    - packages/godoo-client/  # renamed from packages/godoo/ via git mv (59 files)
    - pyproject.toml          # mypy_path, version_toml (already correct), build_command (D-02 stale line removed)
    - .github/workflows/test.yml  # mypy invocation path
    - mkdocs.yml              # mkdocstrings paths
    - CONTRIBUTING.md         # mypy run command and service path docs (3 edits)
    - CLAUDE.md               # Structure, Linting, Stack, Architecture, Module Design sections (14+ edits)
    - uv.lock                 # regenerated; editable path entries point at packages/godoo-client

key-decisions:
  - "D-01: Full repo sweep applied; zero straggler references in tracked source outside .planning/ history artifacts"
  - "D-02: Confirmed and removed stale 'uv build --package godoo' trailing line from build_command; surviving three entries are godoo-client, godoo-testcontainers, godoo-introspection"
  - "pyproject.toml mypy_path and version_toml were already updated pre-execution; only build_command required editing"

patterns-established:
  - "Directory name = PyPI dist name: follow this for all future packages"

requirements-completed: [PKG-01, PKG-02]

# Metrics
duration: 25min
completed: 2026-05-28
---

# Phase 05 Plan 01: Directory Rename Summary

**`packages/godoo/` renamed to `packages/godoo-client/` via `git mv` (blame preserved); all 8 operative path references updated across 5 config/doc files; uv.lock regenerated; D-02 stale build entry removed; D-01 sweep clean.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-28T00:00:00Z (continuation agent; Task 1 was pre-done)
- **Completed:** 2026-05-28
- **Tasks:** 2 (Task 1 pre-done in working tree; Task 2 completed here)
- **Files modified:** 65 (59 renames + 6 modified)

## Accomplishments

- Atomic rename of packages/godoo/ to packages/godoo-client/ preserving full git blame via `git mv`
- uv.lock regenerated with correct editable path entries (`packages/godoo-client`)
- All 8 operative path references updated: pyproject.toml (build_command D-02), test.yml (mypy path), mkdocs.yml (docstrings path), CONTRIBUTING.md (3 edits), CLAUDE.md (14+ edits covering Structure, Linting, Stack, Architecture, Module Design sections)
- D-01 full sweep: zero bare `packages/godoo` references in tracked source outside historical `.planning/` artifacts
- Smoke check passed: `uv sync` no-op; `import godoo.client` exits 0

## Task Commits

1. **Task 1 + Task 2 (atomic): rename + lock + all reference updates** — `93d7d7b` (chore)

_Tasks 1 and 2 were combined into one atomic commit per plan design: rename must be synchronized with reference updates for CI to stay green._

## Files Created/Modified

- `packages/godoo-client/` — all 59 files renamed from `packages/godoo/` with history preserved
- `pyproject.toml` — removed stale `uv build --package godoo` from `build_command` (D-02); mypy_path and version_toml were already correct
- `.github/workflows/test.yml` — mypy invocation: `packages/godoo/src` → `packages/godoo-client/src`
- `mkdocs.yml` — mkdocstrings paths: `packages/godoo/src` → `packages/godoo-client/src`
- `CONTRIBUTING.md` — mypy run command + service directory paths (3 edits)
- `CLAUDE.md` — Structure list, Linting run command, Stack section (transport.py, config.py, pyproject.toml refs), Conventions (Module Design `__init__.py` ref), Architecture section (Component Responsibilities table, Layers, Key Abstractions, Entry Points, Error Handling) — 14+ individual edits
- `uv.lock` — regenerated via `uv sync`; editable path entries now reference `packages/godoo-client`

## Decisions Made

- **D-01**: Full sweep applied to all tracked source files (*.toml, *.yml, *.yaml, *.md, *.py, *.cfg, *.ini, *.txt); zero straggler references remain. Historical `.planning/phases/0[1-4]-*` and `.planning/phases/05-*` planning artifacts contain old paths as expected point-in-time records — not edited.
- **D-02**: Confirmed `uv build --package godoo` on line 76 of pyproject.toml was the stale duplicate. The dist name is `godoo-client`; after rename there is no workspace member named bare `godoo` (that would resolve to `packages/godoo-meta/`). Removed only the trailing line; surviving three entries are correct.
- **pyproject.toml mypy_path and version_toml pre-updated**: These two fields were already showing `packages/godoo-client` before this execution (a prior agent had partially started). Only `build_command` required editing in pyproject.toml.

## Deviations from Plan

None — plan executed exactly as specified. The only discovery was that two of the three pyproject.toml edits (mypy_path, version_toml) had been pre-applied by the prior partial execution; this was not a deviation, it simply meant fewer edits were needed.

## Issues Encountered

- **Initial staging attempt**: `git add packages/godoo packages/godoo-client` failed because `packages/godoo` no longer exists on disk after `git mv`. Fixed by staging `packages/godoo-client` only — git records the rename correctly from the index.

## Smoke Check Results

| Check | Command | Exit Code |
|-------|---------|-----------|
| uv sync | `uv sync` | 0 (no-op: "Resolved 78 packages, Checked 78 packages") |
| import | `uv run python -c "import godoo.client; print('OK')"` | 0 ("OK") |
| blame preserved | `git log --follow packages/godoo-client/src/godoo/client/client.py` | Shows 4 commits predating rename |

## Historical Planning Artifacts (D-01 informational)

The following `.planning/phases/` files contain bare `packages/godoo` references that were NOT edited — these are sealed point-in-time planning and research records:

- `.planning/phases/05-directory-rename/05-01-PLAN.md` (written before rename)
- `.planning/phases/05-directory-rename/05-02-PLAN.md`
- `.planning/phases/05-directory-rename/05-CONTEXT.md`
- `.planning/phases/05-directory-rename/05-DISCUSSION-LOG.md`
- `.planning/phases/05-directory-rename/05-RESEARCH.md`

These are historical records, not operative path references. They do not affect CI or tooling.

## Requirements Addressed

| ID | Description | Status |
|----|-------------|--------|
| PKG-01 | packages/godoo renamed to packages/godoo-client via git mv; godoo.* namespace unchanged | DONE |
| PKG-02 | All path references updated; CI stays green (mypy, build_command, mkdocs, CONTRIBUTING, CLAUDE.md) | DONE |

D-01 and D-02 context decisions: both fully resolved.

## Next Phase Readiness

- `packages/godoo-client/` is the authoritative package directory; all tooling references the new path
- Plan 05-02 (PEP 420 guard test) is ready to execute — it adds `packages/godoo-client/tests/test_namespace.py`
- No blockers for Phase 06

## Self-Check: PASSED

- `packages/godoo-client/` exists: FOUND
- `packages/godoo/` absent: CONFIRMED (no directory)
- Commit `93d7d7b` exists: CONFIRMED
- `uv run python -c "import godoo.client"` exits 0: CONFIRMED
- D-01 sweep clean: CONFIRMED (zero operative stragglers)
- D-02 stale line removed: CONFIRMED (`grep -c "uv build --package godoo$" pyproject.toml` returns 0)
- `.planning/phases/01-04` deletions untouched: CONFIRMED (not staged in this plan's commit)

---
*Phase: 05-directory-rename*
*Completed: 2026-05-28*
