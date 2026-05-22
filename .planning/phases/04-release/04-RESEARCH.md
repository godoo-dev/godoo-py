# Phase 4: Release — Research

**Researched:** 2026-05-22
**Domain:** PyPI namespace packaging (PEP 420), hatchling build config, uv workspace renaming, semantic-release monorepo, GitHub trusted publishing
**Confidence:** HIGH (core mechanics), MEDIUM (hatchling namespace edge cases), HIGH (PyPI/CI)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Adopt a shared `godoo` PEP 420 implicit namespace package — `godoo.client`, `godoo.introspection`, `godoo.testcontainers`. The `azure.*` / `google.cloud.*` pattern. No single distribution owns a top-level `godoo/__init__.py`.
- **D-02:** PyPI distribution names: `godoo-client`, `godoo-introspection`, `godoo-testcontainers`.
- **D-03:** Import migration is in scope — all three packages restructure to `src/godoo/client/`, `src/godoo/introspection/`, `src/godoo/testcontainers/`. Cross-package deps `godoo>=0.1.0` become `godoo-client>=…`; `[tool.uv.sources]` key updates accordingly.
- **D-04:** The existing `godoo` PyPI project (owned by Marc) becomes an empty namespace-locking placeholder. No real code. Hosts the family README on its PyPI page. Each sibling ships its own short README.
- **D-05:** First public release at 0.x (0.1.0). Matches `allow_zero_version = true`, `major_on_zero = false`.
- **D-06:** CI must reach full parity with `godoo-ts` (two-job shape: lint+unit matrix; integration matrix). No release without full matrix green.
- **D-07:** Docker/Odoo integration tests are a hard blocker on the publish path. Complete and correct the existing structure, do not rebuild.
- **D-08:** In-scope CI fix: mypy step currently covers only two src trees — must cover all three after namespace restructure.
- **D-09:** Create `github.com/godoo-dev/godoo-py`, push full commit history, set `origin`. Public repo (LGPL-3.0-or-later).

### Claude's Discretion

- Hatchling mechanics of namespace packaging (how each distribution declares its `godoo.*` subpackage without colliding).
- Exactly how the empty `godoo` meta/placeholder distribution is built.
- Trusted-publishing PyPI-side configuration steps.

### Deferred Ideas (OUT OF SCOPE)

None.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RELEASE-01 | `github.com/godoo-dev/godoo-py` exists, `origin` configured, CI green | D-09; git remote config + GitHub repo creation |
| RELEASE-02 | `godoo` client package renamed to `godoo-client` for PyPI, namespace restructure complete | D-01/D-02/D-03; hatchling namespace config, src layout move, import migration |
| RELEASE-03 | All three packages published to PyPI | D-04; trusted publishing, semantic-release config, placeholder package |
</phase_requirements>

---

## Summary

Phase 4 has three independent-but-sequenced workstreams: (1) create the GitHub remote and push history, (2) restructure the three packages into a shared `godoo.*` PEP 420 implicit namespace and rename the client distribution, and (3) publish all four distributions (three real + one placeholder) to PyPI via the existing trusted-publishing pipeline.

The most technically subtle part is the namespace restructure. The rule is simple but unforgiving: **no distribution may ship a `godoo/__init__.py`**. The current `packages/godoo/src/godoo/__init__.py` file becomes `packages/godoo/src/godoo/client/__init__.py` — its content moves to the subpackage, and the namespace-root directory gets no `__init__.py` at all. Hatchling can ship this correctly using `sources = ["src"]` + `only-include = ["src/godoo/client"]` per distribution, rather than the current `packages = ["src/godoo"]` (which would ship everything under `src/godoo/`, including a namespace-root `__init__.py` if one existed).

The semantic-release and uv-publish infrastructure already works. It needs three targeted corrections: (a) update `version_toml` path from `packages/godoo` to reference `godoo-client`, (b) update `build_command` to use `--package godoo-client`, and (c) add the placeholder `godoo` distribution as a fourth entry.

**Primary recommendation:** Restructure src layout first, verify mypy + ruff pass locally, then wire CI/PyPI — this ordering catches import-migration errors before the publish gate runs.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Namespace packaging (wheel metadata) | Build (hatchling) | — | hatchling builds the wheel; namespace correctness is a build-time concern |
| Import migration (source code) | Source files | Tests | All `from godoo import` / `from godoo_testcontainers import` patterns must change in source and test files |
| Cross-package workspace deps | Root pyproject.toml (uv.sources) | Per-package pyproject.toml | `uv.sources` key is the distribution name; per-package dependency pinning tracks the new name |
| Release versioning | Root pyproject.toml (semantic-release) | Per-package pyproject.toml | Root config drives version bumps across all packages via `version_toml` array |
| Publishing | CI (`release.yml`) + PyPI | — | Trusted publishing via OIDC; `uv publish` reads `dist/` |
| GitHub repo + history | RELEASE-01 (one-time git op) | — | `git remote add` + `git push --tags` |

---

## Standard Stack

This phase installs no new runtime dependencies. All tools are already present.

### Core (already in dev-dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hatchling | 1.29.0 [VERIFIED: pypi.org/project/hatchling] | Wheel + sdist builder | Already the build backend for all three packages |
| python-semantic-release | 10.5.3 [VERIFIED: pypi.org/project/python-semantic-release] | Automated versioning, changelog, GitHub release | Already configured in root pyproject.toml |
| uv | (workspace) | `uv build --package X`, `uv publish` | Already used in all workflows |

### New (this phase adds)

No new runtime or dev dependencies. The placeholder `godoo` distribution is a new PyPI project but ships no code — its pyproject.toml has no `dependencies`.

---

## Package Legitimacy Audit

This phase installs no new external packages. All tooling (`hatchling`, `python-semantic-release`, `uv`) is already declared and in use.

| Package | Registry | Age | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|
| hatchling | PyPI | ~6 yrs | [OK] | Approved — already in use |
| python-semantic-release | PyPI | ~10 yrs | [OK] (flagged as "classic LLM naming pattern" but established) | Approved — already in use |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
                 ┌──────────────────────────────────────────┐
                 │         src/godoo/           (namespace root — NO __init__.py)
                 │   ┌─────────────┐  ┌──────────────────┐  ┌────────────────────┐
                 │   │  client/    │  │  introspection/  │  │  testcontainers/   │
                 │   │ __init__.py │  │  __init__.py     │  │  __init__.py       │
                 │   └─────────────┘  └──────────────────┘  └────────────────────┘
                 │   dist: godoo-client  dist: godoo-intr.    dist: godoo-tc
                 └──────────────────────────────────────────┘
                              ↓ pip install
           site-packages/godoo/      ← namespace root, no __init__.py
                 client/             ← from godoo-client wheel
                 introspection/      ← from godoo-introspection wheel
                 testcontainers/     ← from godoo-testcontainers wheel

       PyPI project "godoo" (placeholder) → ships no importable code, hosts family README
```

### Recommended Project Structure (post-rename)

```
packages/
├── godoo/                       # distribution: godoo-client
│   ├── pyproject.toml           # name = "godoo-client"
│   ├── README.md                # short README for godoo-client PyPI page
│   └── src/
│       └── godoo/               # namespace root — NO __init__.py here
│           └── client/          # subpackage — HAS __init__.py
│               ├── __init__.py  # barrel re-exports (was src/godoo/__init__.py)
│               ├── client.py
│               ├── config.py
│               ├── errors.py
│               ├── py.typed
│               ├── rpc/
│               ├── safety/
│               └── services/
├── godoo-introspection/         # distribution: godoo-introspection
│   ├── pyproject.toml           # name = "godoo-introspection" (unchanged)
│   ├── README.md
│   └── src/
│       └── godoo/               # namespace root — NO __init__.py here
│           └── introspection/   # subpackage — HAS __init__.py
│               ├── __init__.py
│               ├── codegen.py
│               ├── introspector.py
│               ├── markers.py
│               ├── type_mapper.py
│               ├── types.py
│               └── py.typed
├── godoo-testcontainers/        # distribution: godoo-testcontainers
│   ├── pyproject.toml           # name = "godoo-testcontainers" (unchanged)
│   ├── README.md
│   └── src/
│       └── godoo/               # namespace root — NO __init__.py here
│           └── testcontainers/  # subpackage — HAS __init__.py
│               ├── __init__.py
│               ├── container.py
│               ├── harness.py
│               ├── properties.py
│               ├── seed_resolver.py
│               ├── snapshot.py
│               └── py.typed
└── godoo-placeholder/           # distribution: godoo (placeholder)
    ├── pyproject.toml           # name = "godoo", no dependencies, no packages
    └── README.md                # family/main README
```

### Pattern 1: Hatchling Namespace Package Configuration

**What:** Each distribution ships only its own subpackage via `sources` + `only-include`, guaranteeing no `godoo/__init__.py` leaks into the wheel.

**When to use:** Every distribution that participates in the `godoo.*` namespace.

```toml
# packages/godoo/pyproject.toml  (godoo-client distribution)
[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["src/godoo/client"]
```

```toml
# packages/godoo-introspection/pyproject.toml
[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["src/godoo/introspection"]
```

```toml
# packages/godoo-testcontainers/pyproject.toml
[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["src/godoo/testcontainers"]
```

**Why not `packages = ["src/godoo"]`:** That option ships *everything* under `src/godoo/` — including any `godoo/__init__.py` if one were present, and all sibling subpackages — into the same wheel. Using `only-include` with `sources` is the surgical approach. [CITED: https://hatch.pypa.io/1.16/config/build/ + https://github.com/pypa/hatch/discussions/819]

**Critical constraint:** The directory `src/godoo/` in every package MUST NOT contain an `__init__.py`. If any wheel ships `godoo/__init__.py` as a regular package, the namespace is poisoned and the other subpackages become unimportable. [CITED: https://packaging.python.org/en/latest/guides/packaging-namespace-packages/]

**Wheel content verification command (run after `uv build`):**

```bash
unzip -l dist/godoo_client-*.whl | grep -E "godoo/"
# Expected: only godoo/client/* entries — NO godoo/__init__.py
```

### Pattern 2: py.typed Placement for Namespace Packages

**What:** PEP 561 specifies that for namespace packages, `py.typed` should be in the submodule, not the namespace root.

```
src/godoo/client/py.typed          ← correct (already exists here as src/godoo/py.typed; must MOVE)
src/godoo/introspection/py.typed   ← correct (already at src/godoo_introspection/py.typed; must MOVE)
src/godoo/testcontainers/py.typed  ← correct (already at src/godoo_testcontainers/py.typed; must MOVE)
```

[CITED: https://peps.python.org/pep-0561/]

### Pattern 3: The Placeholder Distribution

**What:** A distribution named `godoo` that ships NO importable code. Its purpose is to reserve the `godoo` PyPI name and display the family README.

```toml
# packages/godoo-placeholder/pyproject.toml
[project]
name = "godoo"
version = "0.1.0"
description = "Async Odoo SDK for Python — meta package for the godoo family"
license = "LGPL-3.0-or-later"
requires-python = ">=3.14"
dependencies = []   # no runtime deps
readme = "README.md"
authors = [{ name = "Marc Fargas", email = "marc@marcfargas.com" }]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# No [tool.hatch.build.targets.wheel] packages key — ships nothing importable.
# Hatchling will produce a wheel with just the metadata + README.
```

**Why NOT a thin re-export:** A re-export `godoo/__init__.py` that does `from godoo.client import *` would ship a `godoo/__init__.py` in the wheel and instantly poison the namespace — every other subpackage becomes unimportable. The placeholder must ship NO Python source at all. [ASSUMED: The exact hatchling behavior when no `packages` key is set and no `.py` files exist needs verification; expected behavior is an empty wheel with metadata only.]

**PyPI display:** The `readme = "README.md"` in `[project]` causes the README to appear on the `godoo` PyPI project page. [CITED: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/]

### Pattern 4: uv Workspace Sources After Rename

```toml
# root pyproject.toml [tool.uv.sources] — after rename
[tool.uv.sources]
godoo-client = { workspace = true }   # was: godoo = { workspace = true }
```

The `[tool.uv.sources]` key matches `project.name` from the member's `pyproject.toml`, not the directory name. [CITED: https://docs.astral.sh/uv/concepts/projects/workspaces/]

### Pattern 5: semantic-release Config After Rename

```toml
# root pyproject.toml [tool.semantic_release] — after rename
[tool.semantic_release]
version_toml = [
    "packages/godoo/pyproject.toml:project.version",          # unchanged path; project.name is now godoo-client
    "packages/godoo-testcontainers/pyproject.toml:project.version",
    "packages/godoo-introspection/pyproject.toml:project.version",
    "packages/godoo-placeholder/pyproject.toml:project.version",  # added: placeholder
]
build_command = """
    uv build --package godoo-client && \
    uv build --package godoo-testcontainers && \
    uv build --package godoo-introspection && \
    uv build --package godoo
"""
```

`uv build --package` resolves by `project.name` from pyproject.toml, not directory name. [CITED: https://docs.astral.sh/uv/concepts/projects/workspaces/]

**Placeholder versioning:** Pinning the placeholder's version in `version_toml` means semantic-release bumps it in lockstep with the library packages. This is acceptable for a meta-package and avoids needing separate release logic.

**`uv publish` behavior:** `uv publish` uploads all `.whl` and `.tar.gz` files from `dist/`. Building all four distributions into `dist/` then running one `uv publish` publishes all four in a single pass. [CITED: https://docs.astral.sh/uv/guides/package/]

### Pattern 6: mypy invocation after namespace restructure

After the restructure, `src/godoo/` is a namespace root across three separate package directories. mypy needs `explicit_package_bases = True` (or `--explicit-package-bases` flag) and correct `MYPYPATH` to resolve the namespace correctly.

The corrected CI `mypy` step:

```yaml
- run: |
    MYPYPATH=packages/godoo/src:packages/godoo-introspection/src:packages/godoo-testcontainers/src \
    uv run mypy \
      --explicit-package-bases \
      packages/godoo/src \
      packages/godoo-introspection/src \
      packages/godoo-testcontainers/src
```

Or add to root `pyproject.toml [tool.mypy]`:

```toml
[tool.mypy]
explicit_package_bases = true
mypy_path = [
    "packages/godoo/src",
    "packages/godoo-introspection/src",
    "packages/godoo-testcontainers/src",
]
```

Then the CI step becomes simply: `uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src`

[CITED: https://mypy.readthedocs.io/en/stable/running_mypy.html + https://dev.to/negitamaai/namespace-vs-regular-packages-in-python-and-why-mypy-might-be-failing-you-5le]

### Anti-Patterns to Avoid

- **Shipping `godoo/__init__.py` in any wheel:** Immediately breaks the namespace; the other two subpackages become unimportable at runtime. The current `packages = ["src/godoo"]` stanza ships everything under `src/godoo/` — this must be replaced with `only-include`.
- **Using `packages = ["src/godoo"]` for namespace packages:** Because `packages` collapses to the final path component and ships all contents, it will include any `__init__.py` at the namespace root, breaking the namespace. Use `sources = ["src"]` + `only-include = ["src/godoo/client"]` instead.
- **Re-export shim in the placeholder:** A `godoo/__init__.py` in the placeholder ships `godoo/__init__.py` into the wheel — same poisoning effect as above.
- **Forgetting `--explicit-package-bases` in mypy:** Without it, mypy will either fail to find the namespace subpackages or misattribute them, producing false type errors.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PyPI OIDC authentication | Custom token/secret management | `uv publish --trusted-publishing always` | Already in `release.yml`; OIDC is cryptographically stronger than API tokens |
| Semantic versioning + changelog | Custom version bump scripts | `python-semantic-release` | Already configured in root pyproject.toml; handles version_toml, changelog, GitHub release |
| Wheel namespace exclusion | Build hooks to delete `__init__.py` | hatchling `only-include` config | Single-line config is the canonical solution |
| Namespace collision detection | Custom import probes | `unzip -l dist/*.whl | grep godoo/__init__` | Fast, no installation needed |

**Key insight:** The namespace packaging problem is entirely a build-configuration problem, not a code problem. The solution is two lines of TOML per package, not a build hook.

---

## Runtime State Inventory

> Rename/restructure phase — inventory required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — godoo-py is a library, not a service; no databases store import names | None |
| Live service config | None — no external services configured against this repo yet (no remote, no PyPI project for the new names) | None |
| OS-registered state | None — no OS-level registrations | None |
| Secrets/env vars | None using `godoo` or `godoo_testcontainers` import names; CI uses `GITHUB_TOKEN` (environment-scoped) and PyPI OIDC (no stored secret) | None |
| Build artifacts / installed packages | If `uv sync` has been run, the installed editable packages use old import names (`godoo`, `godoo_testcontainers`, `godoo_introspection`) in the `.venv`; `uv sync` after rename will rebuild them | Run `uv sync` after all pyproject.toml + src moves to rebuild editable installs |

**Post-rename verification:** After import migration, run `uv run python -c "from godoo.client import OdooClient; print('OK')"` to confirm the editable install resolves correctly.

---

## Import Migration Surface

### Exhaustive category map

| Category | Old pattern | New pattern | Files affected |
|----------|-------------|-------------|----------------|
| Top-level client barrel import | `from godoo import OdooClient` | `from godoo.client import OdooClient` | `tests/integration/test_crud.py`, `tests/integration/test_modules.py`, any user docs |
| Internal godoo cross-module | `from godoo.client import ...` | `from godoo.client.client import ...` (one extra level) | All service files importing `OdooClient` — **needs careful audit** |
| godoo-testcontainers → godoo | `from godoo import ...` | `from godoo.client import ...` | `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` (lines 14–16), `harness.py`, `properties.py` |
| godoo-testcontainers → godoo.errors | `from godoo.errors import ...` | `from godoo.client.errors import ...` | Multiple testcontainers source files and tests |
| godoo-testcontainers → godoo.services | `from godoo.services.modules import ...` | `from godoo.client.services.modules import ...` | `container.py` line 16 |
| godoo-introspection → godoo | `from godoo.errors import ...` / `from godoo.client import OdooClient` | `from godoo.client.errors import ...` / `from godoo.client.client import OdooClient` | `introspector.py` lines 7, 12 |
| godoo-introspection internal | `from godoo_introspection.codegen import ...` | `from godoo.introspection.codegen import ...` | All introspection source + tests |
| godoo-testcontainers internal | `from godoo_testcontainers.container import ...` | `from godoo.testcontainers.container import ...` | All testcontainers source + tests |
| Cross-package dependency | `godoo>=0.1.0` in introspection + testcontainers pyproject | `godoo-client>=0.1.0` | Both per-package pyproject.toml |
| uv.sources key | `godoo = { workspace = true }` | `godoo-client = { workspace = true }` | Root pyproject.toml |
| coverage source_pkgs | `godoo`, `godoo_testcontainers`, `godoo_introspection` | `godoo.client`, `godoo.testcontainers`, `godoo.introspection` | Root pyproject.toml `[tool.coverage.run]` |
| Codegen emitted import | `"from godoo_introspection.markers import FieldMeta"` (in codegen.py line 159) | `"from godoo.introspection.markers import FieldMeta"` | `packages/godoo-introspection/src/godoo_introspection/codegen.py` (and the corresponding test assertion in `test_codegen.py` line 65) |

**Critical subtlety — internal module paths:** The current source tree is `src/godoo/client.py`. After restructure it becomes `src/godoo/client/client.py`. Every `from godoo.client import OdooClient` inside the godoo package currently resolves to `src/godoo/client.py:OdooClient`. After the move, `from godoo.client import OdooClient` resolves to `src/godoo/client/__init__.py:OdooClient` (if the barrel re-export is correct). The `__init__.py` at `src/godoo/client/__init__.py` should barrel-export everything that the current `src/godoo/__init__.py` exports. Consumers who did `from godoo.client import OdooClient` keep working if `__init__.py` re-exports it — but internal module-to-module imports like `from godoo.client import OdooClient` inside `client.py` itself need to become intra-package relative imports.

---

## Common Pitfalls

### Pitfall 1: Namespace-breaking `__init__.py` at namespace root

**What goes wrong:** Any `__init__.py` placed in `src/godoo/` (across any of the three package trees) gets shipped in a wheel and converts `godoo` from a namespace package to a regular package. The other two subpackages immediately become unimportable.
**Why it happens:** Easy to accidentally create when moving files ("I need an `__init__.py` here for imports to work").
**How to avoid:** After the restructure, verify: `find packages/ -path "*/src/godoo/__init__.py"` must return zero results. Run the wheel inspection command per Pattern 1.
**Warning signs:** `ModuleNotFoundError: No module named 'godoo.testcontainers'` after installing all three.

### Pitfall 2: Hatchling `packages = ["src/godoo"]` ships namespace-root contents

**What goes wrong:** Using `packages = ["src/godoo"]` (the current pattern) ships everything in the `src/godoo/` directory — all three subpackages — into a single wheel. The `godoo-client` wheel would contain `godoo/client/`, `godoo/introspection/`, and `godoo/testcontainers/` plus any `__init__.py`.
**Why it happens:** The `packages` option is correct for single-package distributions, not namespace sub-packages.
**How to avoid:** Use `sources = ["src"]` + `only-include = ["src/godoo/client"]` per distribution.
**Warning signs:** `uv build` produces an oversized wheel; `unzip -l` shows unexpected subpackage directories.

### Pitfall 3: uv workspace can't resolve renamed package

**What goes wrong:** After renaming `packages/godoo/pyproject.toml project.name` to `godoo-client`, the root `pyproject.toml` still has `godoo = { workspace = true }` in `[tool.uv.sources]`. `uv sync` fails with a resolution error.
**Why it happens:** `[tool.uv.sources]` key must match `project.name`, not directory name.
**How to avoid:** Update `[tool.uv.sources]` atomically with the `project.name` rename. Run `uv sync` immediately to verify.
**Warning signs:** `uv sync: Could not find workspace member 'godoo'`.

### Pitfall 4: mypy fails on namespace packages without `explicit_package_bases`

**What goes wrong:** `uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src` raises `Source file found twice under different module names` or `Cannot find implementation or library stub for module named 'godoo.client'`.
**Why it happens:** mypy needs to know the src directories are package roots, not sub-paths.
**How to avoid:** Add `explicit_package_bases = true` and `mypy_path` to `[tool.mypy]` in root `pyproject.toml`.
**Warning signs:** mypy error mentioning "found twice" or "cannot find implementation" for `godoo.*` modules.

### Pitfall 5: `uv publish` publishes all `dist/` contents — stale files cause errors

**What goes wrong:** If `dist/` contains old wheels from before the rename (e.g., `godoo-0.1.1-py3-none-any.whl`), `uv publish` will attempt to upload them. PyPI will reject re-uploads of the same version.
**How to avoid:** Always clear `dist/` before building: `rm -rf dist/`.
**Warning signs:** `uv publish` output shows "File already exists" errors for old distribution names.

### Pitfall 6: Placeholder distribution ships a `godoo/__init__.py`

**What goes wrong:** If the placeholder `godoo` package directory contains a `src/godoo/__init__.py` (even an empty one), hatchling ships it and all three real subpackages lose their imports.
**How to avoid:** The placeholder package directory contains no `src/` tree. Hatchling with no `packages` key and no Python files will produce a metadata-only wheel (just METADATA + RECORD).
**Warning signs:** After installing all four, `import godoo.client` raises `ImportError`.

### Pitfall 7: PyPI pending publisher claimed before first push

**What goes wrong:** The `godoo-client`, `godoo-introspection`, `godoo-testcontainers` names on PyPI are unclaimed. Someone could register them between pending-publisher setup and first publish.
**How to avoid:** Set up pending publishers and push within the same session. Pending publishers do not reserve names — only the first publish does.
**Warning signs:** `uv publish` fails with "Project already claimed" by another user.

### Pitfall 8: `from godoo.client import OdooClient` fails because `__init__.py` barrel is incomplete

**What goes wrong:** After the restructure, the new `src/godoo/client/__init__.py` (moved from `src/godoo/__init__.py`) must re-export everything that the old `src/godoo/__init__.py` did. If any re-export is missing, existing code patterns break.
**How to avoid:** The content of `src/godoo/__init__.py` moves verbatim to `src/godoo/client/__init__.py`, updated with the new internal module paths. Diff the two files before committing.

---

## Code Examples

Verified patterns from official sources:

### hatchling per-distribution namespace config

```toml
# Source: https://hatch.pypa.io/1.16/config/build/ + https://github.com/pypa/hatch/discussions/819
[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["src/godoo/client"]   # ships godoo/client/ into wheel, nothing else
```

### Wheel content verification

```bash
# Source: standard unzip; run after uv build --package godoo-client
unzip -l dist/godoo_client-*.whl | grep "^.*godoo"
# Must show: godoo/client/... files ONLY
# Must NOT show: godoo/__init__.py
```

### mypy config for namespace packages (root pyproject.toml)

```toml
# Source: https://mypy.readthedocs.io/en/stable/running_mypy.html
[tool.mypy]
python_version = "3.14"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
explicit_package_bases = true
mypy_path = [
    "packages/godoo/src",
    "packages/godoo-introspection/src",
    "packages/godoo-testcontainers/src",
]

[[tool.mypy.overrides]]
module = ["testcontainers.*"]
ignore_missing_imports = true
```

### coverage.run source_pkgs after rename

```toml
# Source: root pyproject.toml
[tool.coverage.run]
source_pkgs = ["godoo.client", "godoo.testcontainers", "godoo.introspection"]
branch = true
```

### Trusted publishing pending publisher setup (manual, one-time)

```
PyPI → Account → Publishing → Add a new pending publisher
For each of the four distributions (godoo-client, godoo-introspection, godoo-testcontainers, godoo):
  Publisher type: GitHub Actions
  Repository: godoo-dev/godoo-py
  Workflow: release.yml
  Environment: pypi
  PyPI project name: <distribution name>
```

[CITED: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/]

### GitHub repo creation and push

```bash
# Source: standard git; RELEASE-01 tasks
gh repo create godoo-dev/godoo-py --public --description "Async Python SDK for Odoo" --license LGPL-3.0
git remote add origin https://github.com/godoo-dev/godoo-py.git
git push -u origin develop
git push origin main
git push --tags
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkgutil`-style namespace (`__init__.py` with `extend_path`) | Native implicit namespace (PEP 420, omit `__init__.py`) | Python 3.3 (2012) | No `__init__.py` at namespace root — all three distributions coexist automatically |
| API tokens for PyPI publish | OIDC trusted publishing | PyPI 2022 | No stored secrets; cryptographically bound to specific workflow/branch |
| `uv publish dist/specific-file.whl` | `uv publish` (all `dist/`) | uv 0.4+ [ASSUMED] | Simpler but requires clean `dist/` before build |

**Deprecated/outdated:**
- `pkgutil.extend_path` style namespace `__init__.py`: superseded by PEP 420 for Python 3-only packages. Do not use.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Hatchling with no `packages` key and no Python source produces a metadata-only wheel (no importable code) | Pattern 3 (placeholder) | Placeholder might fail to build or ship unexpected content; verify with `unzip -l dist/godoo-*.whl` |
| A2 | `uv publish` uploads all `.whl` and `.tar.gz` in `dist/`; `--trusted-publishing always` is valid even for multiple packages in one call | Pattern 5, release.yml | If wrong, the release step would need per-package `uv publish` calls or a `--only` flag |
| A3 | `uv build --package godoo` resolves the placeholder by `project.name = "godoo"` regardless of directory name being `godoo-placeholder` | Pattern 5 (semantic-release) | `build_command` would fail; directory must be named `godoo` or the flag must use the directory name |

---

## Open Questions

1. **Does hatchling produce a valid (non-empty) sdist/wheel when no `packages` key is set and there are no Python files?**
   - What we know: hatchling ships whatever is in the include list; with no `packages`/`only-include`, it falls back to auto-detection heuristics.
   - What's unclear: Whether it errors out ("unable to determine which files to ship") or produces a metadata-only wheel.
   - Recommendation: Verify locally before CI integration: `cd packages/godoo-placeholder && uv build`. If it errors, add an explicit `only-include = []` (empty list) or use a minimal `[tool.hatch.build.targets.sdist]` config.

2. **Does `uv build --package godoo` work when the workspace member directory is named `godoo-placeholder`?**
   - What we know: `uv build --package` resolves by `project.name`, not directory name.
   - What's unclear: Whether the workspace member *discovery* (via `members = ["packages/*"]`) also works when directory name ≠ project.name.
   - Recommendation: Name the placeholder directory `packages/godoo/` is already taken by `godoo-client`. Use a distinct directory like `packages/godoo-meta/` but keep `name = "godoo"` in pyproject.toml. Test `uv build --package godoo` after adding the member.

3. **Does semantic-release correctly handle four `version_toml` entries where one package (placeholder) has no code?**
   - What we know: `version_toml` just patches a TOML field; it does not care about package content.
   - What's unclear: Whether PSR's `build_command` failure for the placeholder (if hatchling errors) aborts the entire release.
   - Recommendation: Build the placeholder locally first; ensure `uv build --package godoo` succeeds before wiring it into `build_command`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `gh` CLI | RELEASE-01 (repo creation) | [ASSUMED] | unknown | `git remote add` manually + GitHub UI for repo creation |
| Docker | D-07 integration tests | Required in CI (ubuntu-latest has Docker) | — | None — integration tests are a hard blocker |
| PyPI account with `godoo` project ownership | D-04 placeholder | Must be verified — Marc owns the existing `godoo` PyPI project | — | None; if not owner, D-04 is blocked |

**Missing dependencies with no fallback:**
- PyPI ownership of `godoo` — must be confirmed before RELEASE-03 can proceed. If Marc's account owns the existing `godoo` project, the placeholder publish will claim it. If ownership is unclear, a manual check at pypi.org/project/godoo is needed before any publish attempt.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8+ with pytest-asyncio |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/ -m "not integration" -q` |
| Full suite command | `uv run pytest packages/ tests/ -m integration -v -s` (requires Docker) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RELEASE-01 | GitHub remote configured, push succeeds | manual | `git remote -v && git ls-remote origin` | N/A |
| RELEASE-02 | `from godoo.client import OdooClient` works post-restructure | unit | `uv run pytest packages/godoo/tests/ -m "not integration" -q` | ✅ (tests exist, need import updates) |
| RELEASE-02 | `from godoo.introspection import Introspector` works | unit | `uv run pytest packages/godoo-introspection/tests/ -q` | ✅ (tests exist, need import updates) |
| RELEASE-02 | `from godoo.testcontainers import OdooTestContainer` works | unit | `uv run pytest packages/godoo-testcontainers/tests/ -m "not integration" -q` | ✅ (tests exist, need import updates) |
| RELEASE-02 | Namespace coexistence (no `godoo/__init__.py` in wheels) | smoke | `unzip -l dist/godoo_client-*.whl \| grep "godoo/__init__"` must be empty | ❌ Wave 0: add verification step |
| RELEASE-02 | mypy passes on all three src trees post-restructure | lint | `uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src` | ✅ (config needs update per Pattern 6) |
| RELEASE-03 | All four distributions publish successfully | integration/manual | CI `release.yml` run on `main` | N/A — PyPI CI |
| RELEASE-03 | `pip install godoo-client` resolves + imports work | smoke | Post-publish: `pip install godoo-client && python -c "from godoo.client import OdooClient"` | ❌ Wave 0: post-publish smoke test script |

### Sampling Rate

- Per task commit: `uv run pytest packages/ -m "not integration" -q`
- Per wave merge: `uv run ruff check . && uv run ruff format --check . && uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src`
- Phase gate: Full matrix green in CI before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Wheel inspection smoke test (verify no `godoo/__init__.py` in any wheel) — add as a local script or CI check
- [ ] Post-publish pip-install smoke test — can be a separate CI job that triggers after publish
- [ ] Placeholder build test (`uv build --package godoo` succeeds) — needed before wiring into semantic-release

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | — |
| V6 Cryptography | no | — |

**This phase is infrastructure/packaging only. No new authentication surfaces, user input paths, or cryptographic operations are introduced. The OIDC trusted-publishing mechanism is entirely PyPI-managed.**

---

## Sources

### Primary (HIGH confidence)

- [hatch.pypa.io/1.16/config/build/](https://hatch.pypa.io/1.16/config/build/) — `packages`, `only-include`, `sources` semantics
- [packaging.python.org/en/latest/guides/packaging-namespace-packages/](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/) — native namespace packages, `__init__.py` rules
- [docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) — pending publishers, first-publish behavior
- [mypy.readthedocs.io/en/stable/running_mypy.html](https://mypy.readthedocs.io/en/stable/running_mypy.html) — `explicit_package_bases`, namespace package invocation
- [peps.python.org/pep-0561/](https://peps.python.org/pep-0561/) — `py.typed` placement in namespace packages

### Secondary (MEDIUM confidence)

- [github.com/pypa/hatch/discussions/819](https://github.com/pypa/hatch/discussions/819) — maintainer confirmation that `sources + only-include` is correct for namespace packages
- [github.com/pypa/hatch/discussions/1243](https://github.com/pypa/hatch/discussions/1243) — `only-include` for sphinxcontrib-style namespace packages
- [github.com/pypa/hatch/issues/1894](https://github.com/pypa/hatch/issues/1894) — hatchling does NOT auto-detect PEP 420 namespace packages; explicit config required
- [docs.astral.sh/uv/concepts/projects/workspaces/](https://docs.astral.sh/uv/concepts/projects/workspaces/) — `uv build --package` resolves by `project.name`; `[tool.uv.sources]` key = `project.name`
- [python-semantic-release.readthedocs.io](https://python-semantic-release.readthedocs.io/) — `version_toml` array, `build_command` with `$PACKAGE_NAME`

### Tertiary (LOW confidence — flagged for validation)

- [joshcannon.me/2025/08/16/py-namespace-packages.html](https://joshcannon.me/2025/08/16/py-namespace-packages.html) — namespace package brittleness pitfalls (blog, not official)
- [medium.com/@asafshakarzy/releasing-a-monorepo-using-uv-workspace-and-python-semantic-release](https://medium.com/@asafshakarzy/releasing-a-monorepo-using-uv-workspace-and-python-semantic-release-0dafc889f4cc) — PSR + uv monorepo pattern (community article)

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all tooling already in use; no new packages
- Namespace packaging mechanics: MEDIUM — hatchling docs are thin on namespace packages; `only-include` approach is confirmed by maintainer discussion but not official docs page; must verify with wheel inspection
- Import migration surface: HIGH — direct grep of source files; all import patterns enumerated
- semantic-release config: HIGH — `version_toml` path semantics confirmed; `uv build --package` resolution confirmed
- PyPI trusted publishing: HIGH — official PyPI docs; pending publisher behavior well-documented
- mypy namespace config: MEDIUM — `explicit_package_bases` confirmed from mypy docs; exact behavior with three separate src trees needs local verification

**Research date:** 2026-05-22
**Valid until:** 2026-11-22 (hatchling config API is stable; PyPI trusted publishing is stable)
