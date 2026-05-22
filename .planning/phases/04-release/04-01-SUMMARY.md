---
phase: "04-release"
plan: 01
subsystem: "ci-infra"
tags: ["github", "ci", "mypy", "namespace-packages", "release"]
dependency_graph:
  requires: []
  provides:
    - "github.com/godoo-dev/godoo-py public repo with full history"
    - "git remote origin configured"
    - "mypy covering all three src trees via explicit_package_bases + mypy_path"
    - "CI Test workflow with corrected lint job"
    - "CLAUDE.md Linting & Types section accurate"
  affects:
    - ".github/workflows/test.yml"
    - "pyproject.toml"
    - "CLAUDE.md"
tech_stack:
  added: []
  patterns:
    - "explicit_package_bases = true + mypy_path in [tool.mypy] for PEP 420 namespace package support"
    - "gh repo create with --license LGPL-3.0 for godoo-dev org"
key_files:
  created: []
  modified:
    - "pyproject.toml — [tool.mypy] added explicit_package_bases + mypy_path for 3 src trees"
    - ".github/workflows/test.yml — lint job mypy step extended to packages/godoo-introspection/src"
    - "CLAUDE.md — Linting & Types section updated with three-tree mypy invocation"
    - "packages/godoo-testcontainers/src/godoo_testcontainers/container.py — ruff format fix"
    - "packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py — ruff format fix"
    - "packages/godoo-testcontainers/tests/test_properties.py — ruff format fix"
    - "packages/godoo-testcontainers/tests/test_snapshot.py — ruff format fix"
decisions:
  - "No main branch push (main doesn't exist locally; it's created by semantic-release on first release)"
  - "Formatting fix committed as separate deviation commit rather than amending Task 1"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-22"
  tasks_completed: 2
  files_modified: 7
requirements:
  - RELEASE-01
---

# Phase 04 Plan 01: GitHub Repo + CI Fix Summary

**One-liner:** Public repo godoo-dev/godoo-py created with full history; mypy namespace-package config via `explicit_package_bases` + `mypy_path` covering all three src trees.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix mypy config, CI coverage, CLAUDE.md docs (D-08) | 459bf1e | pyproject.toml, .github/workflows/test.yml, CLAUDE.md |
| 2 | Create GitHub repo + push full history (D-09, RELEASE-01) | f3e9642 | remote push; formatting fix for 4 testcontainers files |

## What Was Built

**Task 1** added two keys to `[tool.mypy]` in the root `pyproject.toml`: `explicit_package_bases = true` and `mypy_path` listing all three src trees (`packages/godoo/src`, `packages/godoo-introspection/src`, `packages/godoo-testcontainers/src`). This is the D-08 fix for PEP 420 namespace package support in mypy. The `.github/workflows/test.yml` lint job's mypy step was extended to include the third tree. CLAUDE.md `## Linting & Types` now documents the three-tree invocation. mypy confirmed 0 errors across 54 source files; 298 unit tests passed.

**Task 2** created `github.com/godoo-dev/godoo-py` as a public LGPL-3.0 repository under the godoo-dev org, configured `origin`, and pushed the full commit history (develop branch + v0.1.0 tag). CI Test workflow was triggered on the develop push. Note: `main` branch does not exist locally — it will be created by semantic-release on the first release from develop. Tags were pushed (v0.1.0).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff format pre-existing drift in 4 testcontainers files**
- **Found during:** Task 2 — CI first push revealed ruff format --check failure
- **Issue:** 4 files had formatting drift that wasn't caught locally (likely Windows CRLF vs LF differences or ruff version drift): `container.py`, `snapshot.py`, `test_properties.py`, `test_snapshot.py`
- **Fix:** Ran `uv run ruff format` on the 4 files; re-ran full quality gate (ruff check + format + mypy + pytest — all pass); committed as a separate fix commit
- **Files modified:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py`, `snapshot.py`, `tests/test_properties.py`, `tests/test_snapshot.py`
- **Commit:** f3e9642

**2. [Rule 3 - Blocking issue clarification] No local `main` branch to push**
- **Found during:** Task 2 `git push origin main`
- **Issue:** The project has only `develop` as active branch — `main` exists only as a concept for clean merges via semantic-release. There is no local `main` ref.
- **Fix:** Skipped `git push origin main` (nothing to push). develop + tags pushed successfully. `main` will be created by semantic-release when the first release fires. Not a bug — the plan assumed main existed.
- **Files modified:** None

## Verification Results

| Check | Result |
|-------|--------|
| `git remote get-url origin` | `https://github.com/godoo-dev/godoo-py.git` |
| `git ls-remote origin HEAD` | exits 0, returns commit hash |
| `gh repo view` visibility | PUBLIC |
| `gh repo view` license | lgpl-3.0 |
| `uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src` | Success: no issues found in 54 source files |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 82 files already formatted |
| `uv run pytest packages/ -m "not integration"` | 298 passed |
| `grep "name: Test" .github/workflows/test.yml` | matches |
| `grep "packages/godoo-introspection/src" CLAUDE.md` | matches |
| CI Test workflow triggered on develop push | confirmed (run 26291862648 in_progress) |

## Known Stubs

None — this plan made no code changes to library source; all changes were config and CI.

## Threat Flags

None — no new network endpoints, auth paths, or security-relevant surfaces introduced. The public repo push was intentional and authorized (T-04-01-03 accepted; T-04-01-01 mitigated — git log grep returned only benign matches: keyset pagination commit, snapshot key computation commit).

## Self-Check: PASSED

- `pyproject.toml` contains `explicit_package_bases = true` — FOUND
- `.github/workflows/test.yml` contains `packages/godoo-introspection/src` — FOUND
- `CLAUDE.md` contains `packages/godoo-introspection/src` — FOUND
- Commit 459bf1e exists — VERIFIED
- Commit f3e9642 exists — VERIFIED
- `github.com/godoo-dev/godoo-py` is reachable — VERIFIED via `git ls-remote`
