---
phase: "04-release"
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .github/workflows/test.yml
  - pyproject.toml
  - CLAUDE.md
autonomous: true
requirements:
  - RELEASE-01

must_haves:
  truths:
    - "github.com/godoo-dev/godoo-py exists as a public LGPL-3.0-or-later repository"
    - "git remote 'origin' resolves to github.com/godoo-dev/godoo-py"
    - "Full commit history (including all prior phase work) is present on the remote"
    - "The CI lint job runs mypy against all three src trees (godoo, introspection, testcontainers)"
    - "lint + unit tests pass locally; CI Test workflow is triggered on develop (green confirmed asynchronously)"
    - "CLAUDE.md ## Linting & Types documents the correct three-tree mypy invocation"
    - "test.yml declares 'name: Test' matching the release.yml workflow_run trigger"
  decisions_covered:
    - "D-06: CI parity — full test matrix (lint + unit + integration 17.0/18.0/19.0) runs on every push."
    - "D-08: mypy namespace-package fix — explicit_package_bases + mypy_path cover all three src trees."
    - "D-09: create github.com/godoo-dev/godoo-py as public LGPL-3.0 repo and push full commit history with origin configured."
  artifacts:
    - path: ".github/workflows/test.yml"
      provides: "CI matrix with corrected mypy step covering all three src trees (D-08); declares name: Test matching release.yml trigger"
      contains: "packages/godoo-introspection/src"
    - path: "pyproject.toml"
      provides: "Root config with explicit_package_bases and mypy_path (D-08)"
      contains: "explicit_package_bases"
    - path: "CLAUDE.md"
      provides: "Accurate ## Linting & Types section documenting three-tree mypy invocation"
      contains: "packages/godoo-introspection/src"
  key_links:
    - from: "test.yml lint job"
      to: "pyproject.toml [tool.mypy]"
      via: "uv run mypy reads mypy_path + explicit_package_bases from pyproject.toml"
      pattern: "explicit_package_bases"
    - from: "release.yml workflow_run trigger"
      to: "test.yml name: field"
      via: "workflow_run: workflows: ['Test'] — must match exact workflow name"
      pattern: "name: Test"
    - from: "git remote origin"
      to: "github.com/godoo-dev/godoo-py"
      via: "git push -u origin develop"
      pattern: "godoo-dev/godoo-py"
---

<objective>
Create the GitHub repository godoo-dev/godoo-py, push the full commit history, configure `origin`, correct the CI mypy step to cover all three src trees, and update CLAUDE.md to document the corrected mypy invocation.

Purpose: RELEASE-01 — the public repository must exist with origin configured before any subsequent push or trusted-publishing setup can happen. The D-08 mypy fix is included here because it must be green before the first push triggers CI. CLAUDE.md is updated here because it documents the same mypy command that the CI lint job now runs.

Output: Public GitHub repo with full history, `origin` configured, CI triggered on develop, lint + unit tests verified green locally, CLAUDE.md accurate post-restructure.
</objective>

<execution_context>
@C:\Users\marc\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\marc\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-release/04-CONTEXT.md
@.planning/phases/04-release/04-RESEARCH.md
@.planning/phases/04-release/04-PATTERNS.md
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Fix mypy config for namespace packages, CI coverage, and CLAUDE.md docs (D-08)</name>
  <files>pyproject.toml, .github/workflows/test.yml, CLAUDE.md</files>
  <read_first>
    - pyproject.toml (full file — current [tool.mypy] block and [tool.uv.sources])
    - .github/workflows/test.yml (full file — current lint job mypy step; verify top-level `name:` field)
    - CLAUDE.md (full file — find the `## Linting & Types` section to update)
    - .planning/phases/04-release/04-PATTERNS.md §"Root pyproject.toml" and §".github/workflows/test.yml" for exact current-state and target-state TOML/YAML
    - .planning/phases/04-release/04-RESEARCH.md §"Pattern 6" for mypy namespace config rationale
  </read_first>
  <action>
    In pyproject.toml [tool.mypy], add two keys after the existing entries (per D-08 and RESEARCH.md Pattern 6):
    - `explicit_package_bases = true`
    - `mypy_path = ["packages/godoo/src", "packages/godoo-introspection/src", "packages/godoo-testcontainers/src"]`

    The existing [tool.mypy.overrides] block for testcontainers.* stays unchanged.

    In .github/workflows/test.yml:
    1. Verify the top-level `name:` field reads exactly `name: Test`. If it reads anything else (e.g., `name: CI`), update it to `name: Test`. This name must match the `workflow_run: workflows: ["Test"]` trigger in release.yml exactly — the publish gate fires on nothing if the names diverge.
    2. Update the lint job mypy step from:
         `uv run mypy packages/godoo/src packages/godoo-testcontainers/src`
       to:
         `uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src`

    In CLAUDE.md, find the `## Linting & Types` section. Update the documented mypy invocation so it matches the corrected CI step — all three src trees must appear:
      `uv run ruff check . && uv run ruff format . && uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src`
    (The exact existing prose style in that section determines formatting; update the mypy portion only — do not rearrange the section.)

    No other changes to any of these files. Do NOT touch [tool.uv.sources] here — that happens in Plan 02 atomically with the project.name rename. Do NOT touch [tool.semantic_release] — that happens in Plan 03.
  </action>
  <verify>
    <automated>uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src && uv run pytest packages/ -m "not integration" -q</automated>
  </verify>
  <acceptance_criteria>
    - `uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src` exits 0 with no errors
    - pyproject.toml contains `explicit_package_bases = true` under [tool.mypy]
    - pyproject.toml [tool.mypy] mypy_path lists all three src paths
    - .github/workflows/test.yml top-level `name:` field is exactly `name: Test` — verified with: `head -5 .github/workflows/test.yml | grep "name: Test"`
    - .github/workflows/test.yml lint job mypy step contains `packages/godoo-introspection/src`
    - CLAUDE.md `## Linting & Types` section mypy invocation contains `packages/godoo-introspection/src`
    - `uv run pytest packages/ -m "not integration" -q` exits 0 (no regressions)
  </acceptance_criteria>
  <done>mypy passes on all three src trees locally; CI lint step covers introspection; test.yml name matches release.yml trigger; CLAUDE.md documents the corrected invocation</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Create GitHub repo and push full history (D-09, RELEASE-01)</name>
  <files></files>
  <read_first>
    - .planning/phases/04-release/04-RESEARCH.md §"GitHub repo creation and push" for exact gh CLI commands
    - .planning/phases/04-release/04-CONTEXT.md §"Repo" decision D-09
    - pyproject.toml [project.urls] — note current Repository/Issues URLs point to old marcfargas/godoo; these will be corrected in Plan 02 when package pyproject.toml files are updated
    - .github/workflows/release.yml (read the `workflow_run: workflows:` entry to confirm it reads "Test" — must match test.yml `name:`)
  </read_first>
  <action>
    Run the following in sequence (per RESEARCH.md §"GitHub repo creation and push"):

    1. `gh repo create godoo-dev/godoo-py --public --description "Async Python SDK for Odoo" --license LGPL-3.0`
       - If gh CLI is not authenticated or the godoo-dev org requires specific permissions, stop and report the error rather than working around it.
    2. `git remote add origin https://github.com/godoo-dev/godoo-py.git`
    3. `git push -u origin develop`
    4. `git push origin main`
    5. `git push --tags`

    Do NOT force-push. Do NOT push directly to main if CI fails on develop (the integration gate runs on push to main in release.yml). The goal here is history + CI triggered on develop; green confirmation is asynchronous.

    Note: Do NOT commit anything in this task. Task 1 changes are committed by the executor before this task runs. This task only creates the remote and pushes.
  </action>
  <verify>
    <automated>git remote get-url origin && git ls-remote origin HEAD</automated>
  </verify>
  <acceptance_criteria>
    - `git remote get-url origin` returns `https://github.com/godoo-dev/godoo-py.git`
    - `git ls-remote origin HEAD` exits 0 (remote is reachable and has commits)
    - `gh repo view godoo-dev/godoo-py --json visibility,license` returns `{"visibility":"PUBLIC","license":{"key":"lgpl-3.0"}}`
    - The GitHub repo shows the full commit history (not a shallow clone)
    - `grep "name: Test" .github/workflows/test.yml` exits 0 (workflow name matches release.yml workflow_run trigger)
    - CI `Test` workflow is triggered by the develop push (observed in GitHub Actions UI or via `gh run list --repo godoo-dev/godoo-py`); green status confirmed asynchronously — do not block task completion on CI finishing
  </acceptance_criteria>
  <done>github.com/godoo-dev/godoo-py exists, origin is configured, full history is pushed, CI Test workflow triggered on develop (green verified asynchronously)</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Local git → GitHub remote | Full commit history crosses to a public remote; any secret ever committed becomes public |
| gh CLI → GitHub API | Creates a public repo under godoo-dev org; requires org membership with repo-create permission |
| CI runner → PyPI (future) | Trusted publishing uses OIDC — no long-lived token stored; id-token:write scope is already declared in release.yml |
| release.yml workflow_run trigger | Fires only when workflow named "Test" succeeds on main — test.yml name: field must match exactly |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-01-01 | Information Disclosure | git push to public remote | mitigate | Before pushing, verify `git log --all --full-history --grep="password\|secret\|token\|key" --oneline` returns zero results; verify .env and secrets files are in .gitignore and not tracked |
| T-04-01-02 | Information Disclosure | pyproject.toml [project.urls] | accept | Current URLs reference marcfargas/godoo (old location) — not a secret; URLs updated in Plan 02 to godoo-dev/godoo-py |
| T-04-01-03 | Elevation of Privilege | gh repo create under godoo-dev org | accept | Marc is the org owner; creation is intentional and authorized |
| T-04-01-04 | Tampering | CI workflow permissions (id-token:write) | mitigate | release.yml already scoped to `environment: pypi` gate; id-token:write is only needed for OIDC publish — least-privilege per PyPI trusted publishing docs |
| T-04-01-05 | Tampering | workflow_run trigger name mismatch | mitigate | Task 1 acceptance criteria verifies test.yml `name: Test` with grep; Task 2 acceptance criteria re-checks; mismatched name silently disables the publish gate |
| T-04-01-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in this plan; all tooling already in uv.lock |
</threat_model>

<verification>
After both tasks complete:
- `git remote get-url origin` returns the godoo-dev/godoo-py URL
- `git ls-remote origin HEAD` exits 0
- `uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src` exits 0
- `uv run ruff check . && uv run ruff format --check .` exits 0
- `uv run pytest packages/ -m "not integration" -q` exits 0
- `grep "name: Test" .github/workflows/test.yml` exits 0
- CLAUDE.md `## Linting & Types` mypy invocation includes `packages/godoo-introspection/src`
- GitHub Actions CI `Test` workflow triggered on develop push (green confirmed asynchronously)
</verification>

<success_criteria>
- github.com/godoo-dev/godoo-py is a public LGPL-3.0 repository
- `git remote get-url origin` returns `https://github.com/godoo-dev/godoo-py.git`
- Full commit history is on the remote (not a shallow clone)
- mypy covers all three src trees and passes locally
- CI lint job passes with the corrected mypy invocation (green confirmed asynchronously after push)
- test.yml `name: Test` matches release.yml `workflow_run: workflows: ["Test"]` trigger
- CLAUDE.md documents the corrected three-tree mypy invocation
</success_criteria>

<output>
Create `.planning/phases/04-release/04-01-SUMMARY.md` when done
</output>
