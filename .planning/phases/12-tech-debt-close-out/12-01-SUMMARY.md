---
phase: 12-tech-debt-close-out
plan: "01"
subsystem: ci
tags: [ci, github-actions, node24, gitleaks, secrets-scan, debt]
dependency_graph:
  requires: []
  provides: [DEBT-01, DEBT-02]
  affects: [.github/workflows]
tech_stack:
  added: [gitleaks/gitleaks-action@v3]
  patterns: [major-tag-pins, dedicated-workflow-per-concern]
key_files:
  created:
    - .github/workflows/secrets.yml
  modified:
    - .github/workflows/release.yml
    - .github/workflows/test.yml
    - .github/workflows/docs.yml
decisions:
  - "Bumped actions/checkout @v4→@v6, astral-sh/setup-uv @v6→@v7, codecov/codecov-action @v5→@v6 (Node 24-capable)"
  - "Left peaceiris/actions-gh-pages at @v4 (no v5 exists); added inline comment noting verification gate"
  - "gitleaks-action placed in dedicated secrets.yml (not test.yml) for orthogonal adjustability"
  - "No GITLEAKS_LICENSE (personal public repo); no .gitleaks.toml (spikes/infra verified placeholder-only)"
metrics:
  duration: "90s"
  completed: "2026-06-03T13:12:12Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 12 Plan 01: CI Node 20 Bump + Gitleaks Secrets Scan Summary

**One-liner:** Bumped all three CI workflows from Node 20 action pins to Node 24-capable equivalents (checkout@v6, setup-uv@v7, codecov@v6) and added a dedicated gitleaks/gitleaks-action@v3 secrets-scan workflow with full history coverage.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Bump Node 20 action pins across all three workflows (DEBT-01) | 117aa87 | release.yml, test.yml, docs.yml |
| 2 | Add gitleaks secrets-scan workflow (DEBT-02) | ea7d079 | .github/workflows/secrets.yml (new) |

## What Was Built

**Task 1 — DEBT-01 (Node 20 deprecation elimination):**
- `release.yml`: checkout@v4→@v6, setup-uv@v6→@v7 (2 pins)
- `test.yml`: checkout@v4→@v6 (3 jobs), setup-uv@v6→@v7 (3 jobs), codecov-action@v5→@v6 (1 pin) — 7 substitutions total
- `docs.yml`: checkout@v4→@v6, setup-uv@v6→@v7 (2 pins); peaceiris/actions-gh-pages left at @v4 (no v5 published) with an inline comment explaining the verification gate and the FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 mitigation if still warning

**Task 2 — DEBT-02 (gitleaks guardrail):**
- New `.github/workflows/secrets.yml` workflow named "Secrets Scan"
- Triggers on push to main/develop and pull_request to main
- Runs gitleaks/gitleaks-action@v3 (Node 24 runtime) on a full history checkout (fetch-depth: 0)
- No GITLEAKS_LICENSE (not required for personal public repo)
- No .gitleaks.toml allowlist (spikes/ and infra/ confirmed to hold only placeholder strings)
- File-level comment documents D-03 decision: run_spike.py was never committed (commit 67200b8)

## Deviations from Plan

None — plan executed exactly as written. All substitutions matched the line-by-line plan specification. The peaceiris exception (no v5, leave at @v4) was pre-documented in the plan and applied as specified.

## Threat Flags

None. This plan introduces no new network endpoints, auth paths, file access patterns, or schema changes. The gitleaks-action is the security control for this phase — it closes the committed-credential threat surface (T-12-02 mitigated per threat model).

## Known Stubs

None. This plan is CI YAML only; no UI rendering, no data pipeline, no placeholder values.

## Pending Verification (post-push)

Per plan verification section — requires a push to develop:
1. Confirm release.yml, test.yml, docs.yml Action runs show no "Node.js 20 is deprecated" annotation
2. Confirm secrets.yml appears in Actions tab and runs green on first push
3. If docs.yml still warns (peaceiris@v4 — A1 assumption), add `env: FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: 'true'` to the deploy job as a follow-up commit

## Self-Check: PASSED

Files verified:
- .github/workflows/release.yml — EXISTS, contains checkout@v6 and setup-uv@v7
- .github/workflows/test.yml — EXISTS, contains checkout@v6, setup-uv@v7, codecov-action@v6
- .github/workflows/docs.yml — EXISTS, contains checkout@v6, setup-uv@v7, peaceiris@v4 unchanged
- .github/workflows/secrets.yml — EXISTS, contains gitleaks-action@v3, fetch-depth:0, no GITLEAKS_LICENSE

Commits verified:
- 117aa87 — FOUND (Task 1)
- ea7d079 — FOUND (Task 2)
