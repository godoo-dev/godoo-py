---
phase: 04-release
plan: 02
subsystem: infra
tags: [pep420, namespace-packages, hatchling, uv-workspace, pyproject]

# Dependency graph
requires:
  - phase: 04-01
    provides: GitHub remote configured, origin set, CI green
provides:
  - All 3 packages restructured into shared godoo PEP 420 namespace
  - godoo-client distribution (renamed from godoo)
  - src/godoo/client/, src/godoo/introspection/, src/godoo/testcontainers/ layout
  - hatchling only-include config per distribution
  - All imports migrated (godoo.client.*, godoo.introspection.*, godoo.testcontainers.*)
  - Wheel namespace invariant verified: no godoo/__init__.py in any wheel
  - Namespace coexistence verified in clean venv
affects: [04-03, any future phase importing from godoo.*]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PEP 420 implicit namespace: no __init__.py at godoo/ namespace root in any package tree"
    - "hatchling sources = src + only-include per distribution for namespace safety"
    - "from godoo.client import OdooClient — primary public API surface"
    - "from godoo.introspection import Introspector — introspection public API"
    - "from godoo.testcontainers import OdooTestContainer — testcontainers public API"

key-files:
  created:
    - packages/godoo/src/godoo/client/__init__.py
    - packages/godoo-introspection/src/godoo/introspection/__init__.py
    - packages/godoo-testcontainers/src/godoo/testcontainers/__init__.py
  modified:
    - packages/godoo/pyproject.toml
    - packages/godoo-introspection/pyproject.toml
    - packages/godoo-testcontainers/pyproject.toml
    - pyproject.toml
    - uv.lock

key-decisions:
  - "D-01: Shared godoo PEP 420 implicit namespace confirmed — no godoo/__init__.py ships in any distribution"
  - "D-02: godoo distribution renamed to godoo-client; PyPI names now godoo-client, godoo-introspection, godoo-testcontainers"
  - "D-03: All imports migrated in scope — from godoo.client.*, from godoo.introspection.*, from godoo.testcontainers.*"

patterns-established:
  - "Namespace root invariant: find packages/ -path '*/src/godoo/__init__.py' must always return empty"
  - "hatchling wheel config: sources=['src'] + only-include=['src/godoo/<subpackage>'] per distribution"
  - "Cross-package OdooClient import pattern: from godoo.client.client import OdooClient (TYPE_CHECKING)"

requirements-completed: [RELEASE-02]

# Metrics
duration: 45min
completed: 2026-05-22
---

# Phase 4 Plan 02: Namespace Restructure Summary

**PEP 420 implicit namespace established: three packages coexist under godoo.* without __init__.py poisoning, client renamed to godoo-client, all 298 unit tests and mypy pass**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-22T14:00:00Z
- **Completed:** 2026-05-22T14:45:00Z
- **Tasks:** 3 (tasks 1+3 merged due to test migration being required for Task 1 acceptance)
- **Files modified:** 92 (86 src+test moves/edits, 5 pyproject+lock, 1 ruff fix)

## Accomplishments
- Moved all three source trees into PEP 420 namespace: `src/godoo/client/`, `src/godoo/introspection/`, `src/godoo/testcontainers/`
- No `godoo/__init__.py` at namespace root in any package tree (confirmed via find + wheel inspection)
- All imports migrated: `from godoo.X` → `from godoo.client.X`, `from godoo_introspection.X` → `from godoo.introspection.X`, `from godoo_testcontainers.X` → `from godoo.testcontainers.X`
- godoo distribution renamed to godoo-client with hatchling `only-include` config
- uv workspace resolves `godoo-client = { workspace = true }` correctly
- Three wheels built; namespace invariant verified via `unzip -l | grep godoo/__init__` (zero results all three)
- Coexistence verified: all three wheels installed in clean venv, `import godoo.client, godoo.introspection, godoo.testcontainers` passes
- Full quality gate: ruff check, ruff format --check, mypy (54 files), 298 unit tests — all pass

## Task Commits

1. **Task 1+3: Restructure src layouts and migrate all imports** - `30ca319` (refactor)
2. **Task 2: Update pyproject.toml files** - `714e352` (chore)
3. **Style fix: ruff I001 import ordering** - `697e825` (style)

## Files Created/Modified

### New locations (via git mv)
- `packages/godoo/src/godoo/client/` — entire client source tree (was `src/godoo/`)
- `packages/godoo-introspection/src/godoo/introspection/` — introspection source (was `src/godoo_introspection/`)
- `packages/godoo-testcontainers/src/godoo/testcontainers/` — testcontainers source (was `src/godoo_testcontainers/`)

### Modified configs
- `packages/godoo/pyproject.toml` — name godoo→godoo-client, hatchling only-include, URLs updated
- `packages/godoo-introspection/pyproject.toml` — dep godoo→godoo-client, hatchling only-include, URLs updated
- `packages/godoo-testcontainers/pyproject.toml` — dep godoo→godoo-client, hatchling only-include, URLs updated
- `pyproject.toml` — uv.sources key godoo→godoo-client, coverage source_pkgs updated, semantic-release build_command updated
- `uv.lock` — rebuilt after workspace member rename

## Decisions Made

- Merged Task 3 (test file migration) into Task 1's commit scope — test imports are co-located dependencies of the source moves, and tests must pass as part of the Task 1 acceptance criteria
- Kept `[tool.semantic_release]` build_command without `godoo` (placeholder) entry per plan note "those belong to plan 03"
- Ruff auto-fixed 3 import ordering issues (I001) in transport.py, introspector.py, container.py after import path changes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 3 test migration merged into Task 1 commit**
- **Found during:** Task 1 (src restructure)
- **Issue:** Task 1 acceptance criteria requires `uv run pytest packages/ -m "not integration" -q` to pass, but test files were not yet migrated. Tests fail to import with ModuleNotFoundError before Task 3 can run.
- **Fix:** Migrated all test imports (packages/godoo/tests/, packages/godoo-testcontainers/tests/, packages/godoo-introspection/tests/, tests/conftest.py, tests/integration/) as part of Task 1 execution.
- **Files modified:** 16 test files
- **Committed in:** 30ca319 (part of Task 1 commit)

**2. [Rule 1 - Bug] Ruff I001 import ordering after namespace path changes**
- **Found during:** Task 3 quality gate
- **Issue:** Three files had unsorted import blocks after the `godoo.` → `godoo.client.` path changes
- **Fix:** `uv run ruff check --fix` auto-fixed introspector.py, container.py, rpc/transport.py
- **Files modified:** 3 files
- **Committed in:** 697e825

---

**Total deviations:** 2 auto-fixed (1 task ordering adaptation, 1 ruff format)
**Impact on plan:** Minor — first deviation was necessary for test execution to work. No scope creep.

## Issues Encountered
- On Windows, `/tmp/` does not exist; used `C:/Temp/` for the clean venv coexistence check instead.

## Next Phase Readiness
- Plan 04-03 can proceed: all three distributions build correctly with namespace packaging
- `uv build --package godoo-client`, `uv build --package godoo-introspection`, `uv build --package godoo-testcontainers` all produce correct wheels
- PyPI publish infrastructure ready (semantic-release config, CI release.yml unchanged)
- Blocker: PyPI pending publishers for `godoo-client`, `godoo-introspection`, `godoo-testcontainers`, `godoo` (placeholder) must be configured before first publish

---
*Phase: 04-release*
*Completed: 2026-05-22*
