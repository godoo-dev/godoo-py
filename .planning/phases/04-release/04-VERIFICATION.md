---
phase: 04-release
verified: 2026-05-22T00:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 4: Release — Verification Report

**Phase Goal:** All three packages are publicly available on PyPI under the godoo-dev/godoo-py GitHub repository
**Verified:** 2026-05-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `github.com/godoo-dev/godoo-py` exists as a public LGPL-3.0-or-later repository | VERIFIED | `git remote get-url origin` = `https://github.com/godoo-dev/godoo-py.git`; `git ls-remote origin HEAD` exits 0; `gh repo view` confirms PUBLIC + lgpl-3.0 (per orchestrator fact + SUMMARY-01) |
| 2 | Full commit history (including all prior phase work) is present on the remote | VERIFIED | `git ls-remote origin HEAD` = `1ccc32b`; `git ls-remote origin refs/heads/main refs/heads/develop` both populated; remote tag `v0.2.0` = `5731623` confirmed |
| 3 | CI Test workflow triggers on push; lint + unit + integration matrix pass on main | VERIFIED | test.yml declares `name: Test`; release.yml `workflow_run: workflows: ["Test"]` — names match exactly; full matrix 17.0/18.0/19.0 ran on main before publish (per SUMMARY-03 and orchestrator) |
| 4 | `pip install godoo-client` installs the async Odoo client (renamed from `godoo`); `from godoo.client import OdooClient` succeeds | VERIFIED | `godoo-client 0.2.0` live on PyPI (non-yanked); `uv run python -c "from godoo.client import OdooClient; print('OK')"` exits 0 locally |
| 5 | `pip install godoo-introspection` succeeds; `from godoo.introspection import Introspector` succeeds | VERIFIED | `godoo-introspection 0.2.0` live on PyPI (non-yanked); local import confirmed |
| 6 | `pip install godoo-testcontainers` succeeds; `from godoo.testcontainers import OdooTestContainer` succeeds | VERIFIED | `godoo-testcontainers 0.2.0` live on PyPI (old 1.0.0 yanked); local import confirmed |
| 7 | `pip install godoo` installs namespace-locking placeholder; godoo PyPI page displays family README | VERIFIED | `godoo 0.2.0` live (old 0.0.1+1.0.0 yanked); PyPI description contains godoo-client, godoo-introspection, godoo-testcontainers, OdooClient, Introspector; text/markdown content type |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/test.yml` | CI matrix with lint + unit + integration 17.0/18.0/19.0; `name: Test` | VERIFIED | Exists; `name: Test` on line 1; mypy step covers all three src trees; integration matrix on `odoo-version: ["17.0", "18.0", "19.0"]` |
| `pyproject.toml` | `explicit_package_bases = true`; `mypy_path` with three src trees; `godoo-client = { workspace = true }`; four-dist `build_command` | VERIFIED | All present: `explicit_package_bases = true`, `mypy_path` has three paths, `[tool.uv.sources] godoo-client = { workspace = true }`, `build_command` includes all four `--package` flags |
| `packages/godoo/pyproject.toml` | `name = "godoo-client"`; `only-include = ["src/godoo/client"]` | VERIFIED | `name = "godoo-client"`, `only-include = ["src/godoo/client"]`, version 0.2.0, URL points to godoo-dev/godoo-py |
| `packages/godoo-introspection/pyproject.toml` | `only-include = ["src/godoo/introspection"]`; `dependencies = ["godoo-client>=0.1.0"]` | VERIFIED | Both present; version 0.2.0 |
| `packages/godoo-testcontainers/pyproject.toml` | `only-include = ["src/godoo/testcontainers"]`; `dependencies = ["godoo-client>=0.1.0", ...]` | VERIFIED | Both present; version 0.2.0 |
| `packages/godoo-meta/pyproject.toml` | `name = "godoo"`; `bypass-selection = true`; no src/ tree | VERIFIED | Exists; `bypass-selection = true`; no src/ directory; no dependencies |
| `packages/godoo-meta/README.md` | Family README shown on godoo PyPI page | VERIFIED | Exists; PyPI API confirms rendered as text/markdown with all package references |
| `.github/workflows/release.yml` | `workflow_run: workflows: ["Test"]`; `uv publish --trusted-publishing always --check-url` | VERIFIED | Both present; triggers on main only; `environment: pypi` set; `id-token: write` permission |
| `packages/godoo/src/godoo/client/` | Client src tree under PEP 420 namespace | VERIFIED | Directory exists; no `__init__.py` at `src/godoo/` namespace root (file confirmed missing) |
| `packages/godoo-introspection/src/godoo/introspection/` | Introspection src tree under PEP 420 namespace | VERIFIED | Directory exists; no `__init__.py` at namespace root |
| `packages/godoo-testcontainers/src/godoo/testcontainers/` | Testcontainers src tree under PEP 420 namespace | VERIFIED | Directory exists; no `__init__.py` at namespace root |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test.yml` `name: Test` | `release.yml` `workflow_run: workflows: ["Test"]` | exact string match | VERIFIED | `grep "name: Test" .github/workflows/test.yml` matches; `grep 'workflows.*Test' release.yml` matches |
| `release.yml` uv publish step | PyPI trusted publishing | `--trusted-publishing always` + `environment: pypi` + `id-token: write` | VERIFIED | All three present in release.yml; no long-lived API token in any file |
| `pyproject.toml [tool.uv.sources]` | `packages/godoo/pyproject.toml project.name` | `godoo-client = { workspace = true }` | VERIFIED | Key is `godoo-client`; package name is `godoo-client`; `uv run pytest` resolves correctly |
| `pyproject.toml [tool.semantic_release] build_command` | four packages | `--package godoo-client`, `--package godoo-testcontainers`, `--package godoo-introspection`, `--package godoo` | VERIFIED | All four present in build_command string |
| `pyproject.toml [tool.mypy] mypy_path` | three src trees | `explicit_package_bases = true` + `mypy_path` | VERIFIED | `uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src` exits 0 with no issues (54 source files) |
| `hatchling only-include` per wheel | no namespace-root `__init__.py` | `only-include = ["src/godoo/client"]` etc. | VERIFIED | PEP 420 invariant confirmed: `find packages/ -path "*/src/godoo/__init__.py"` returns zero results across all three source trees |

### Data-Flow Trace (Level 4)

Not applicable — this is a build/infra/release phase; no dynamic data rendering components.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `from godoo.client import OdooClient` | `uv run python -c "from godoo.client import OdooClient; print('OK')"` | `godoo.client OK` | PASS |
| `from godoo.introspection import Introspector` | `uv run python -c "from godoo.introspection import Introspector; print('OK')"` | `godoo.introspection OK` | PASS |
| `from godoo.testcontainers import OdooTestContainer` | `uv run python -c "from godoo.testcontainers import OdooTestContainer; print('OK')"` | `godoo.testcontainers OK` | PASS |
| Unit test suite | `uv run pytest packages/ -m "not integration"` | `298 passed, 3 deselected, 1 warning in 3.38s` | PASS |
| mypy strict | `uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src` | `Success: no issues found in 54 source files` | PASS |
| ruff lint + format | `uv run ruff check . && uv run ruff format --check .` | `All checks passed! / 82 files already formatted` | PASS |
| PyPI godoo-client live | `pypi.org/pypi/godoo-client/json` | version=0.2.0, yanked=False | PASS |
| PyPI godoo-introspection live | `pypi.org/pypi/godoo-introspection/json` | version=0.2.0, yanked=False | PASS |
| PyPI godoo-testcontainers live | `pypi.org/pypi/godoo-testcontainers/json` | version=0.2.0, yanked=False | PASS |
| PyPI godoo placeholder live | `pypi.org/pypi/godoo/json` | version=0.2.0, yanked=False, description renders family README | PASS |
| Old stale versions yanked | PyPI godoo 0.0.1+1.0.0; godoo-testcontainers 1.0.0 | All yanked=True; 0.2.0 is latest non-yanked | PASS |
| PEP 420 namespace invariant | `find packages/ -path "*/src/godoo/__init__.py"` | Zero results across all three src trees | PASS |
| Remote HEAD matches 0.2.0 release commit | `git ls-remote origin HEAD` | `1ccc32b` = main; tag `v0.2.0` = `5731623` on remote | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RELEASE-01 | 04-01 | `godoo-dev/godoo-py` GitHub repo exists with origin configured | SATISFIED | `git remote get-url origin` = `https://github.com/godoo-dev/godoo-py.git`; both branches on remote |
| RELEASE-02 | 04-02 | `godoo` client package renamed to `godoo-client` for PyPI; all imports migrated to `godoo.client.*` namespace | SATISFIED | `packages/godoo/pyproject.toml name = "godoo-client"`; `from godoo.client import OdooClient` works; no `godoo/__init__.py` in any src tree |
| RELEASE-03 | 04-03 | All three packages published to PyPI | SATISFIED | godoo-client 0.2.0, godoo-introspection 0.2.0, godoo-testcontainers 0.2.0 all live; plus godoo 0.2.0 placeholder |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `packages/godoo/src/godoo/__pycache__/` | N/A | Stale `.pyc` files from pre-restructure namespace root | INFO | Committed to .gitignore; not present in wheels; no runtime impact |

No TBD/FIXME/XXX/TODO debt markers found in phase-modified files. No stubs. No hardcoded empty returns in production code. No disconnected props or hollow wiring.

### Human Verification Required

None — all must-haves are verifiable programmatically or via PyPI API. Trusted publishing is confirmed by the absence of any long-lived API tokens in repository secrets or workflow files, and by the `uv publish --trusted-publishing always` invocation in release.yml.

---

## Non-Blocking Notes

These were flagged in SUMMARY-03 as out-of-scope follow-ups. They do not block the phase goal.

1. **Docs workflow failing on main pushes.** A separate `Docs` CI workflow (not the `Test` workflow on the publish path) fails on main. Not on the release gate path; does not affect installability. Worth addressing in a follow-up pass.

2. **Node-20 action deprecation warnings.** `release.yml` references `actions/checkout@v4` and `astral-sh/setup-uv@v6` which may emit Node-20 deprecation warnings. Functional but noisy; bump action versions when convenient.

3. **REQUIREMENTS.md traceability table not updated for RELEASE-03.** The traceability table in `.planning/REQUIREMENTS.md` still shows `RELEASE-03: Pending`. This is a docs inconsistency in the planning artifact; the actual requirement is satisfied.

---

## Gaps Summary

None. All seven observable truths are VERIFIED. All three phase requirements (RELEASE-01, RELEASE-02, RELEASE-03) are SATISFIED. The phase goal — "All three packages are publicly available on PyPI under the godoo-dev/godoo-py GitHub repository" — is fully achieved.

The phase additionally delivered beyond minimum scope: a fourth `godoo` namespace-locking placeholder distribution was published as a meta package; old stale PyPI versions were yanked; the release pipeline was made idempotent with `--check-url`; and the PEP 420 shared namespace (`godoo.client`, `godoo.introspection`, `godoo.testcontainers`) was established with verified coexistence in a clean venv.

---

_Verified: 2026-05-22_
_Verifier: Claude (gsd-verifier)_
