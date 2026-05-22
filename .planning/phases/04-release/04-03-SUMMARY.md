---
phase: 04-release
plan: 03
subsystem: release
tags: [pypi, trusted-publishing, semantic-release, hatchling, placeholder-dist]

# Dependency graph
requires:
  - phase: 04-01
    provides: GitHub remote, origin, CI Test workflow, release.yml gate
  - phase: 04-02
    provides: PEP 420 namespace restructure, godoo-client rename, four-dist layout
provides:
  - godoo placeholder distribution (godoo-meta) — metadata-only wheel, family README
  - semantic-release wired for all four distributions (build_command + version_toml)
  - All four distributions published to PyPI at 0.2.0 via trusted publishing
  - release.yml made idempotent with uv publish --check-url
affects: [future releases, any consumer installing from PyPI]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "hatchling bypass-selection = true for a code-free metadata-only distribution"
    - "uv build --package <name> resolves by project.name, not directory name"
    - "uv publish --check-url <index> for idempotent re-runs after partial publish"
    - "PyPI trusted publishing: pending publisher PyPI Project Name must exactly match dist name"

key-files:
  created:
    - packages/godoo-meta/pyproject.toml
    - packages/godoo-meta/README.md
    - .planning/phases/04-release/04-03-spike-findings.md
  modified:
    - pyproject.toml
    - .github/workflows/release.yml
---

# Plan 04-03 — Publish

## Outcome

All four distributions are live on PyPI at **0.2.0** via trusted publishing (no
long-lived tokens). `pip install godoo-client|godoo-introspection|godoo-testcontainers`
each resolve to 0.2.0 and import cleanly in an isolated env; `godoo` installs as a
code-free placeholder whose PyPI page renders the family README.

## Tasks

- **Task 1 — placeholder + spike (committed `18ae7af`):** Created `packages/godoo-meta/`
  (name `godoo`, no `src/`). Resolved the three RESEARCH open questions:
  - Q1: hatchling needs `[tool.hatch.build.targets.wheel] bypass-selection = true` for a
    metadata-only wheel (`only-include = []` is rejected as "no selection option").
  - Q2: `uv build --package godoo` resolves by `project.name` despite the `godoo-meta`
    directory name.
  - Q3: `uv sync` auto-discovers the package via `members = ["packages/*"]`.
  - Wheel verified code-free (only `dist-info`), namespace invariant intact.
- **Task 2 — semantic-release wiring (committed `e959c55`):** Added the
  `packages/godoo-meta/pyproject.toml:project.version` entry to `version_toml` and
  `uv build --package godoo` to `build_command`. Full local build produced four correct
  wheels; namespace invariant held across all four; 298 unit tests green.
- **Task 3 — PyPI setup + publish (CI):** Trusted publishers configured for all four
  distributions; first publish executed via the `release.yml` pipeline on `main`.
  Released as **0.2.0** (semantic-release minor bump from `v0.1.0`).

## Deviations / incidents (resolved)

1. **Auto-fired phantom release.** The Phase 04-01 `main` push triggered the Release
   workflow on pre-restructure code; semantic-release created a `v0.2.0` tag/GitHub
   release/commit but the PyPI publish failed (no publishers yet). Cleaned up (tag +
   release deleted, `main` reset to the restructured tip) before the real publish.
2. **Version regression vs existing PyPI names.** `godoo` (1.0.0) and
   `godoo-testcontainers` (1.0.0) already existed on PyPI under Marc's account from the
   old `marcfargas/godoo`. A 0.2.0 release would be shadowed, so the stale releases were
   **yanked** (godoo 0.0.1+1.0.0, godoo-testcontainers 1.0.0, godoo-introspection 0.1.0)
   so 0.2.0 resolves as latest.
3. **Trusted-publisher claim mismatch.** Initial publishes failed `422 invalid-publisher`
   until publisher fields matched the OIDC claims (owner `godoo-dev`, repo `godoo-py`,
   workflow `release.yml`, env `pypi`). The `godoo-client` pending publisher additionally
   needed its PyPI Project Name set to exactly `godoo-client`.
4. **Partial publish idempotency.** After `godoo-introspection 0.2.0` published but the
   run aborted at `godoo-client`, `release.yml` was changed to
   `uv publish --trusted-publishing always --check-url https://pypi.org/simple/`
   (committed `4c54a4b`) so re-runs skip already-published files and upload only the
   missing ones.

## Verification

- PyPI release lists (non-yanked): `godoo-client` 0.2.0; `godoo-introspection` 0.2.0;
  `godoo-testcontainers` 0.2.0 (1.0.0 yanked); `godoo` 0.2.0 (0.0.1+1.0.0 yanked).
- Clean-env smoke tests (`uv run --isolated --no-project --with <dist>`): all imports OK;
  `godoo-testcontainers` resolves to 0.2.0 (not the yanked 1.0.0).
- `godoo` PyPI description renders the family README (text/markdown).
- GitHub Release `v0.2.0` (Latest), tag `v0.2.0` = `5731623`; `main` = `develop` = `1ccc32b`.
- Full Test matrix (lint + unit + integration 17.0/18.0/19.0) green on `main` before publish.

## Follow-ups (out of scope)

- A separate `Docs` workflow failed on `main` pushes — not on the publish path; worth a
  look in a later pass.
- `release.yml` uses Node-20 actions (deprecation warning); bump `actions/checkout` and
  `setup-uv` when convenient.
