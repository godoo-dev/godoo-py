---
phase: "04-release"
plan: 03
type: execute
wave: 3
depends_on:
  - "04-01"
  - "04-02"
files_modified:
  - packages/godoo-meta/pyproject.toml
  - packages/godoo-meta/README.md
  - pyproject.toml
  - .github/workflows/release.yml
autonomous: false
requirements:
  - RELEASE-03

must_haves:
  truths:
    - "pip install godoo-client installs the async Odoo client from PyPI"
    - "pip install godoo-introspection installs the introspection package from PyPI"
    - "pip install godoo-testcontainers installs the testcontainers package from PyPI"
    - "pip install godoo installs the namespace-locking placeholder (no importable code)"
    - "The godoo PyPI page displays the family README"
    - "All four distributions publish via trusted publishing (no long-lived API tokens)"
    - "The CI release.yml pipeline fires only after the full Test matrix is green on main"
  artifacts:
    - path: "packages/godoo-meta/pyproject.toml"
      provides: "godoo placeholder distribution — no dependencies, no src/ tree, ships only metadata + family README"
      contains: "name = \"godoo\""
    - path: "packages/godoo-meta/README.md"
      provides: "Family README displayed on the godoo PyPI page — describes all three real distributions and their install commands"
    - path: "pyproject.toml"
      provides: "semantic-release config with four-distribution build_command (godoo-client, godoo-introspection, godoo-testcontainers, godoo)"
      contains: "godoo-client"
  key_links:
    - from: "pyproject.toml [tool.semantic_release] build_command"
      to: "packages/godoo-meta/pyproject.toml project.name"
      via: "uv build --package godoo resolves by project.name"
      pattern: "uv build --package godoo"
    - from: "release.yml uv publish"
      to: "PyPI trusted publisher"
      via: "--trusted-publishing always with id-token:write and environment: pypi"
      pattern: "trusted-publishing always"
---

<objective>
Create the godoo placeholder distribution (D-04), add it as a workspace member, wire all four distributions into semantic-release, conduct local build verification for the placeholder (resolving the open questions from RESEARCH.md), set up trusted publishing on PyPI for all four distributions (manual step), and trigger the first publish via the CI pipeline on main.

Purpose: RELEASE-03 — all three real packages and the placeholder are publicly installable from PyPI. The CI pipeline already exists and is correct; this plan completes the remaining wiring (placeholder, corrected build_command) and performs the publish.

Output: Four distributions on PyPI; godoo PyPI page shows family README; `pip install godoo-client` works on Python 3.14.
</objective>

<execution_context>
@C:\Users\marc\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\marc\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/04-release/04-CONTEXT.md
@.planning/phases/04-release/04-RESEARCH.md
@.planning/phases/04-release/04-PATTERNS.md
@.planning/phases/04-release/04-01-SUMMARY.md
@.planning/phases/04-release/04-02-SUMMARY.md

<interfaces>
<!-- Key config contracts for this plan. Extracted from PATTERNS.md and RESEARCH.md. -->

Placeholder target pyproject.toml (from PATTERNS.md §"packages/godoo-meta/pyproject.toml"):
  name = "godoo", version = "0.1.1", no dependencies, no src/ tree
  [tool.hatch.build.targets.wheel] section: see RESEARCH.md Open Question 1 — may need
  explicit `only-include = []` if hatchling errors without a packages key. Verify locally.

Root pyproject.toml [tool.semantic_release] build_command target (from PATTERNS.md):
  uv build --package godoo-client && uv build --package godoo-testcontainers &&
  uv build --package godoo-introspection && uv build --package godoo

Root pyproject.toml [tool.semantic_release] version_toml target:
  Add "packages/godoo-meta/pyproject.toml:project.version" to the array

Current release.yml: no changes needed to the file itself; build_command update is in root pyproject.toml
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create godoo-meta placeholder distribution and verify it builds (D-04, open questions A1/A2/A3)</name>
  <files>packages/godoo-meta/pyproject.toml, packages/godoo-meta/README.md</files>
  <read_first>
    - .planning/phases/04-release/04-PATTERNS.md §"packages/godoo-meta/pyproject.toml" (full target pyproject template)
    - .planning/phases/04-release/04-RESEARCH.md §"Pattern 3 — The Placeholder Distribution" (rationale and anti-patterns)
    - .planning/phases/04-release/04-RESEARCH.md §"Open Questions" 1, 2, 3 (what to verify locally)
    - .planning/phases/04-release/04-RESEARCH.md §"Pitfall 6" (placeholder must NOT contain a src/godoo/__init__.py)
    - pyproject.toml root (verify `members = ["packages/*"]` picks up godoo-meta automatically)
  </read_first>
  <action>
    Create directory `packages/godoo-meta/` with exactly two files (no src/ tree):

    packages/godoo-meta/pyproject.toml — create with these exact fields:
    - [project]: name = "godoo", version = "0.1.1", description = "Async Odoo SDK for Python — meta package for the godoo family", license = "LGPL-3.0-or-later", requires-python = ">=3.14", dependencies = [] (empty list), readme = "README.md", authors = [{ name = "Marc Fargas", email = "marc@marcfargas.com" }]
    - [project.urls]: Documentation = "https://www.marcfargas.com/~odoopy/", Repository = "https://github.com/godoo-dev/godoo-py"
    - [project] classifiers: "Development Status :: 4 - Beta", "Framework :: AsyncIO", "Framework :: Odoo", "Intended Audience :: Developers"
    - [build-system]: requires = ["hatchling"], build-backend = "hatchling.build"
    - Do NOT add a src/ tree — the placeholder ships no Python code.
    - If the first local build attempt (`uv build --package godoo`) fails because hatchling cannot determine what to include, add `[tool.hatch.build.targets.wheel]` with `only-include = []` (empty list) to produce a metadata-only wheel. This resolves Open Question 1.

    packages/godoo-meta/README.md — write the family README:
    - Title: "godoo — Async Odoo SDK for Python"
    - Brief description: async Odoo JSON-RPC SDK family for Python developers automating or testing Odoo instances
    - Section: "Packages" listing all three installable distributions with their PyPI install commands and import examples:
      - godoo-client: `pip install godoo-client` / `from godoo.client import OdooClient`
      - godoo-introspection: `pip install godoo-introspection` / `from godoo.introspection import Introspector`
      - godoo-testcontainers: `pip install godoo-testcontainers` / `from godoo.testcontainers import OdooTestContainer`
    - Section: "License": LGPL-3.0-or-later
    - Keep it concise — this is a family index, not a tutorial

    After creating the files, run the placeholder build verification:
    - `uv sync` — confirms workspace member discovery via `members = ["packages/*"]`
    - `rm -rf dist/ && uv build --package godoo`
    - `unzip -l dist/godoo-*.whl | grep "godoo/__init__"` — must return zero lines (no importable code shipped)
    - `unzip -l dist/godoo-*.whl` — wheel must contain only metadata files (METADATA, WHEEL, RECORD) and README; no .py files

    If `uv build --package godoo` fails because the directory is named `godoo-meta` and hatchling cannot discover it, rename the directory to `packages/godoo` is not possible (already taken). Instead, confirm that `uv build --package godoo` resolves by project.name (RESEARCH.md A3 assumption) — if it does NOT, the fallback is to run `uv build` from within `packages/godoo-meta/` directly: `cd packages/godoo-meta && uv build`. Record the outcome in the SUMMARY so Plan 03 semantic-release config can be adjusted if needed.
  </action>
  <verify>
    <automated>uv sync && uv build --package godoo && unzip -l dist/godoo-*.whl | grep -c "\.py$"</automated>
  </verify>
  <acceptance_criteria>
    - `packages/godoo-meta/pyproject.toml` exists with `name = "godoo"` and no `dependencies` entries
    - `packages/godoo-meta/` directory contains NO `src/` tree and NO Python source files
    - `uv sync` exits 0 and lists godoo as a workspace member
    - `uv build --package godoo` exits 0 and produces a `.whl` in `dist/`
    - `unzip -l dist/godoo-*.whl | grep "\.py$"` returns zero lines (no importable Python code in wheel)
    - `unzip -l dist/godoo-*.whl | grep "godoo/__init__"` returns zero lines (no namespace-root init)
    - `find packages/ -path "*/src/godoo/__init__.py"` still returns zero results (invariant unchanged)
  </acceptance_criteria>
  <done>godoo placeholder distribution builds successfully, ships no Python code, and does not poison the namespace</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Wire four distributions into semantic-release config and verify full build</name>
  <files>pyproject.toml</files>
  <read_first>
    - pyproject.toml (root, full file — current [tool.semantic_release] section)
    - .planning/phases/04-release/04-PATTERNS.md §"Root pyproject.toml" [tool.semantic_release] target state
    - .planning/phases/04-release/04-RESEARCH.md §"Pattern 5 — semantic-release Config After Rename"
    - .planning/phases/04-release/04-01-SUMMARY.md and 04-02-SUMMARY.md — confirm build_command --package godoo-client works as expected from Task 1 findings
  </read_first>
  <action>
    Update root pyproject.toml [tool.semantic_release]:

    version_toml: add `"packages/godoo-meta/pyproject.toml:project.version"` as the fourth entry in the array (after the existing three)

    build_command: replace `uv build --package godoo` (the first entry, which was the old pre-rename godoo) with `uv build --package godoo-client`. The four-distribution build_command becomes:
    ```
    uv build --package godoo-client && \
    uv build --package godoo-testcontainers && \
    uv build --package godoo-introspection && \
    uv build --package godoo
    ```
    Note: `--package godoo` here refers to the PLACEHOLDER distribution (project.name = "godoo" in packages/godoo-meta/). Confirm that `uv build --package godoo` succeeded in Task 1 before setting this. If Task 1 found that `uv build --package godoo` does not work with the godoo-meta directory name, update the build_command to use the working invocation from Task 1.

    After updating pyproject.toml, run a full four-distribution build to confirm all four succeed:
    - `rm -rf dist/`
    - `uv build --package godoo-client && uv build --package godoo-testcontainers && uv build --package godoo-introspection && uv build --package godoo`
    - Verify `ls dist/` shows eight files (four .whl + four .tar.gz) or at least four .whl files
    - `unzip -l dist/godoo_client-*.whl | grep "godoo/__init__"` → zero lines
    - `unzip -l dist/godoo_introspection-*.whl | grep "godoo/__init__"` → zero lines
    - `unzip -l dist/godoo_testcontainers-*.whl | grep "godoo/__init__"` → zero lines
    - `unzip -l dist/godoo-*.whl | grep "\.py$"` → zero lines

    Note: release.yml itself needs no changes — it runs `uv run semantic-release version` which reads build_command from pyproject.toml. The `uv publish --trusted-publishing always` step uploads everything in dist/ in one pass.
  </action>
  <verify>
    <automated>rm -rf dist/ && uv build --package godoo-client && uv build --package godoo-testcontainers && uv build --package godoo-introspection && uv build --package godoo && python -c "import glob; files=glob.glob('dist/*.whl'); print(f'{len(files)} wheels built'); assert len(files) == 4, f'Expected 4 wheels, got {len(files)}'"</automated>
  </verify>
  <acceptance_criteria>
    - `dist/` contains exactly four .whl files after the full build (one per distribution: godoo_client, godoo_introspection, godoo_testcontainers, godoo)
    - All four `uv build --package ...` commands exit 0
    - None of the four wheels contains `godoo/__init__.py` (namespace invariant across all wheels)
    - Root pyproject.toml [tool.semantic_release] version_toml has four entries including `packages/godoo-meta/pyproject.toml:project.version`
    - Root pyproject.toml [tool.semantic_release] build_command contains `--package godoo-client` (not `--package godoo` for the client distribution)
    - `uv run pytest packages/ -m "not integration" -q` still exits 0 (no regressions from pyproject changes)
  </acceptance_criteria>
  <done>Four-distribution semantic-release config wired; full local build produces four correct wheels; namespace invariant holds across all four</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: PyPI trusted publisher setup + first publish via CI on main</name>
  <what-built>
    Tasks 1 and 2 have: created the godoo placeholder distribution, verified all four wheels build correctly with correct namespace packaging, and updated semantic-release config. All CI checks (lint, unit tests) pass. The repository is public on GitHub and the Test workflow runs on push.

    The release pipeline (release.yml) is already wired: it triggers when the Test workflow concludes success on main, runs semantic-release, and publishes via `uv publish --trusted-publishing always`. The only remaining steps require your PyPI account.
  </what-built>
  <how-to-verify>
    Complete these steps in order:

    STEP 1 — Set up PyPI trusted publishers (manual, one-time):
    Go to https://pypi.org/manage/account/publishing/ and add four pending publishers:
    - Publisher type: GitHub Actions for all four
    - Repository owner: godoo-dev
    - Repository name: godoo-py
    - Workflow filename: release.yml
    - Environment name: pypi
    - PyPI project names (one per publisher): godoo-client, godoo-introspection, godoo-testcontainers, godoo

    For the `godoo` project: if you already own the existing godoo PyPI project (pypi.org/project/godoo), go to that project's settings and add a trusted publisher there instead of creating a pending publisher. If you do NOT own the existing godoo project, stop here and assess before proceeding.

    STEP 2 — Merge develop to main and trigger the pipeline:
    - Confirm the Test workflow is green on develop (lint + unit-tests must be green; integration tests are the full blocker per D-07)
    - `git checkout main && git merge develop --no-ff -m "chore: merge develop for v0.1 release" && git push origin main`
    - This triggers the Test workflow on main. Wait for all three integration matrix jobs to complete (17.0, 18.0, 19.0). The integration jobs require Docker.
    - Once Test succeeds on main, the Release workflow fires automatically.

    STEP 3 — Verify the publish:
    - Check https://github.com/godoo-dev/godoo-py/actions — Release workflow should show success
    - Check https://pypi.org/project/godoo-client/ — should show version 0.1.1
    - Check https://pypi.org/project/godoo-introspection/ — should show version 0.1.1
    - Check https://pypi.org/project/godoo-testcontainers/ — should show version 0.1.1
    - Check https://pypi.org/project/godoo/ — should show version 0.1.1 with the family README displayed

    STEP 4 — Smoke test (post-publish, from a clean env):
    ```bash
    python -m venv /tmp/godoo-smoke && /tmp/godoo-smoke/bin/pip install godoo-client && /tmp/godoo-smoke/bin/python -c "from godoo.client import OdooClient; print('godoo-client OK')"
    /tmp/godoo-smoke/bin/pip install godoo-introspection && /tmp/godoo-smoke/bin/python -c "from godoo.introspection import Introspector; print('godoo-introspection OK')"
    /tmp/godoo-smoke/bin/pip install godoo-testcontainers && /tmp/godoo-smoke/bin/python -c "from godoo.testcontainers import OdooTestContainer; print('godoo-testcontainers OK')"
    ```
    All three must print OK.
  </how-to-verify>
  <resume-signal>
    If publish succeeded: type "published" with the PyPI URLs for all four distributions.
    If any step failed: describe what went wrong (which distribution, what error message). Common issues:
    - "File already exists" on PyPI → version already uploaded; check if a previous partial publish succeeded
    - "Not authorized" on publish → trusted publisher not configured for that distribution
    - Integration tests failed → do not merge to main until they pass (D-07 is a hard blocker)
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PyPI trusted publishing (OIDC) | The release.yml workflow holds `id-token: write` and publishes to environment `pypi`; no long-lived API token stored |
| godoo PyPI name ownership | The existing `godoo` project on PyPI must be owned by Marc's account; publishing the placeholder to an unowned project name would fail |
| Placeholder wheel → pip install | The placeholder wheel must ship no importable Python; any stray .py file could poison the namespace for all users |
| dist/ build artifacts | Stale wheels in dist/ from old distribution names would be uploaded and rejected (or worse, accepted for wrong names) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-03-01 | Spoofing | godoo-client / godoo-introspection / godoo-testcontainers PyPI names | mitigate | Set up pending publishers immediately before first push to main; name reservation only happens on first publish — pending publishers do not reserve names (per RESEARCH.md Pitfall 7). Minimize window between setup and publish. |
| T-04-03-02 | Information Disclosure | Trusted publishing with id-token:write scope | mitigate | Already constrained to `environment: pypi` in release.yml; OIDC token is ephemeral and cryptographically bound to the specific workflow run and branch. No stored secret. |
| T-04-03-03 | Tampering | dist/ stale artifact pollution | mitigate | `rm -rf dist/` before every build (enforced in Task 2 verify step and in semantic-release build_command). |
| T-04-03-04 | Tampering | Placeholder distribution ships importable code | mitigate | Task 1 acceptance criteria: `unzip -l dist/godoo-*.whl | grep "\.py$"` must return zero. Repeated in Task 2 multi-wheel invariant check. |
| T-04-03-05 | Elevation of Privilege | PyPI project takeover via misowned godoo name | mitigate | Confirm PyPI ownership of existing `godoo` project at pypi.org/project/godoo before running Task 3 checkpoint. If not owned, stop — do not attempt publish. |
| T-04-03-06 | Denial of Service | Integration matrix failure blocks release (D-07) | accept | Hard requirement per D-07; integration failure correctly blocks the Release workflow via `workflow_run` trigger. This is a safety gate, not a threat to mitigate. |
| T-04-03-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in this plan; placeholder has no runtime deps. |
</threat_model>

<verification>
After all tasks complete (including checkpoint):
- `pip install godoo-client` installs successfully on Python 3.14
- `python -c "from godoo.client import OdooClient"` exits 0 in a clean venv
- `pip install godoo-introspection` installs successfully
- `python -c "from godoo.introspection import Introspector"` exits 0
- `pip install godoo-testcontainers` installs successfully
- `python -c "from godoo.testcontainers import OdooTestContainer"` exits 0
- pypi.org/project/godoo displays the family README (not an error page)
- pypi.org/project/godoo-client shows version 0.1.1
- GitHub Actions Release workflow shows completed successfully
</verification>

<success_criteria>
- All four distributions are on PyPI under version 0.1.1
- `pip install godoo-client && python -c "from godoo.client import OdooClient"` succeeds in a clean Python 3.14 environment
- `pip install godoo-introspection && python -c "from godoo.introspection import Introspector"` succeeds
- `pip install godoo-testcontainers && python -c "from godoo.testcontainers import OdooTestContainer"` succeeds
- The godoo PyPI page displays the family README
- The publish was done via trusted publishing (no long-lived API token used)
- The full Test matrix (lint + unit + integration 17.0/18.0/19.0) was green on main before publish
</success_criteria>

<output>
Create `.planning/phases/04-release/04-03-SUMMARY.md` when done
</output>
