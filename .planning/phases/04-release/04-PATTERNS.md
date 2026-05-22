# Phase 4: Release - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 8 config/structural targets + import migration surface
**Analogs found:** 8 / 8 (all are self-analogs — current state is the anchor)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/godoo/pyproject.toml` | config | transform | itself (current state → target state) | self |
| `packages/godoo-introspection/pyproject.toml` | config | transform | `packages/godoo/pyproject.toml` | exact-role |
| `packages/godoo-testcontainers/pyproject.toml` | config | transform | `packages/godoo/pyproject.toml` | exact-role |
| `packages/godoo-meta/pyproject.toml` (new placeholder) | config | — | `packages/godoo-introspection/pyproject.toml` (simplest existing) | structural-template |
| `pyproject.toml` (root) | config | transform | itself (current state → target state) | self |
| `.github/workflows/test.yml` | CI config | transform | itself (current state → target state) | self |
| `.github/workflows/release.yml` | CI config | transform | itself (current state → target state) | self |
| src layout dirs (all three packages) | directory structure | transform | themselves | self |

---

## Pattern Assignments

### `packages/godoo/pyproject.toml` (config, transform)

**Analog:** itself — current state shown below; planner edits from here to target state.

**Current `[project]` block** (lines 1-16):
```toml
[project]
name = "godoo"
version = "0.1.1"
description = "Async Python client for Odoo JSON-RPC"
license = "LGPL-3.0-or-later"
requires-python = ">=3.14"
dependencies = ["httpx>=0.27"]
authors = [{ name = "Marc Fargas", email = "marc@marcfargas.com" }]
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: AsyncIO",
    "Framework :: Odoo",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries",
    "Typing :: Typed",
]
```

**Current `[project.urls]`** (lines 18-22):
```toml
[project.urls]
Documentation = "https://www.marcfargas.com/~odoopy/"
Repository = "https://github.com/marcfargas/godoo"
Issues = "https://github.com/marcfargas/godoo/issues"
```

**Current `[tool.hatch.build.targets.wheel]`** (lines 27-28):
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/godoo"]
```

**Target changes (D-02, D-03):**
- `name = "godoo"` → `name = "godoo-client"`
- `[project.urls]` Repository/Issues URLs → `https://github.com/godoo-dev/godoo-py`
- `[tool.hatch.build.targets.wheel]` replace `packages = ["src/godoo"]` with:
```toml
[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["src/godoo/client"]
```

---

### `packages/godoo-introspection/pyproject.toml` (config, transform)

**Analog:** itself — current state shown below.

**Current `[project]` block** (lines 1-15):
```toml
[project]
name = "godoo-introspection"
version = "0.1.1"
description = "Schema discovery and codegen for Odoo models"
license = "LGPL-3.0-or-later"
requires-python = ">=3.14"
dependencies = ["godoo>=0.1.0"]
authors = [{ name = "Marc Fargas", email = "marc@marcfargas.com" }]
classifiers = [
    "Development Status :: 2 - Pre-Alpha",
    "Framework :: AsyncIO",
    "Framework :: Odoo",
    "Intended Audience :: Developers",
    "Typing :: Typed",
]
```

**Current `[tool.hatch.build.targets.wheel]`** (lines 25-26):
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/godoo_introspection"]
```

**Target changes (D-02, D-03):**
- `dependencies = ["godoo>=0.1.0"]` → `dependencies = ["godoo-client>=0.1.0"]`
- `[project.urls]` Repository URL → `https://github.com/godoo-dev/godoo-py`
- `[tool.hatch.build.targets.wheel]` replace with:
```toml
[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["src/godoo/introspection"]
```

---

### `packages/godoo-testcontainers/pyproject.toml` (config, transform)

**Analog:** itself — current state shown below.

**Current `[project]` block** (lines 1-16):
```toml
[project]
name = "godoo-testcontainers"
version = "0.1.1"
description = "Docker-based Odoo instances for integration testing"
license = "LGPL-3.0-or-later"
requires-python = ">=3.14"
dependencies = ["godoo>=0.1.0", "testcontainers[postgres]>=4"]
authors = [{ name = "Marc Fargas", email = "marc@marcfargas.com" }]
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: AsyncIO",
    "Framework :: Odoo",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Testing",
    "Typing :: Typed",
]
```

**Current `[tool.hatch.build.targets.wheel]`** (lines 26-27):
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/godoo_testcontainers"]
```

**Target changes (D-02, D-03):**
- `dependencies = ["godoo>=0.1.0", ...]` → `dependencies = ["godoo-client>=0.1.0", "testcontainers[postgres]>=4"]`
- `[project.urls]` Repository URL → `https://github.com/godoo-dev/godoo-py`
- `[tool.hatch.build.targets.wheel]` replace with:
```toml
[tool.hatch.build.targets.wheel]
sources = ["src"]
only-include = ["src/godoo/testcontainers"]
```

---

### `packages/godoo-meta/pyproject.toml` (new — placeholder distribution, D-04)

**Analog:** `packages/godoo-introspection/pyproject.toml` used as structural template (simplest existing pyproject — no runtime deps, single build-system stanza).

**No existing analog** — this is a new file. Model the structure from the introspection pyproject but strip everything build-related. The placeholder ships NO Python source:

```toml
[project]
name = "godoo"
version = "0.1.1"
description = "Async Odoo SDK for Python — meta package for the godoo family"
license = "LGPL-3.0-or-later"
requires-python = ">=3.14"
dependencies = []
readme = "README.md"
authors = [{ name = "Marc Fargas", email = "marc@marcfargas.com" }]
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: AsyncIO",
    "Framework :: Odoo",
    "Intended Audience :: Developers",
]

[project.urls]
Documentation = "https://www.marcfargas.com/~odoopy/"
Repository = "https://github.com/godoo-dev/godoo-py"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# No [tool.hatch.build.targets.wheel] packages key — ships nothing importable.
# Verify: unzip -l dist/godoo-*.whl must show NO godoo/__init__.py
```

**Directory:** Create `packages/godoo-meta/` with only `pyproject.toml` and `README.md` (family README). No `src/` tree.

**Open question from RESEARCH.md:** Whether hatchling with no `packages` key and no Python files produces a valid wheel or errors. Verify locally with `uv build --package godoo` before wiring into semantic-release.

---

### Root `pyproject.toml` — `[tool.uv.sources]`, `[tool.semantic_release]`, `[tool.coverage.run]`, `[tool.mypy]`

**Analog:** itself — current state shown below.

**Current `[tool.uv.sources]`** (line 18):
```toml
[tool.uv.sources]
godoo = { workspace = true }
```

**Target (D-03, Pitfall 3):**
```toml
[tool.uv.sources]
godoo-client = { workspace = true }
```

**Current `[tool.semantic_release]`** (lines 55-69):
```toml
[tool.semantic_release]
version_toml = [
    "packages/godoo/pyproject.toml:project.version",
    "packages/godoo-testcontainers/pyproject.toml:project.version",
    "packages/godoo-introspection/pyproject.toml:project.version",
]
allow_zero_version = true
major_on_zero = false
branch = "main"
commit_parser = "conventional"
build_command = """
    uv build --package godoo && \
    uv build --package godoo-testcontainers && \
    uv build --package godoo-introspection
"""
```

**Target (D-02, D-04):**
```toml
[tool.semantic_release]
version_toml = [
    "packages/godoo/pyproject.toml:project.version",
    "packages/godoo-testcontainers/pyproject.toml:project.version",
    "packages/godoo-introspection/pyproject.toml:project.version",
    "packages/godoo-meta/pyproject.toml:project.version",
]
allow_zero_version = true
major_on_zero = false
branch = "main"
commit_parser = "conventional"
build_command = """
    uv build --package godoo-client && \
    uv build --package godoo-testcontainers && \
    uv build --package godoo-introspection && \
    uv build --package godoo
"""
```

Note: `version_toml` path stays `packages/godoo/pyproject.toml` (directory path unchanged); only `project.name` inside changes. `uv build --package` resolves by `project.name`, so `--package godoo-client` and `--package godoo` are the correct post-rename flags.

**Current `[tool.coverage.run]`** (lines 47-49):
```toml
[tool.coverage.run]
source_pkgs = ["godoo", "godoo_testcontainers", "godoo_introspection"]
branch = true
```

**Target (D-03):**
```toml
[tool.coverage.run]
source_pkgs = ["godoo.client", "godoo.testcontainers", "godoo.introspection"]
branch = true
```

**Current `[tool.mypy]`** (lines 27-36):
```toml
[tool.mypy]
python_version = "3.14"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = ["testcontainers.*"]
ignore_missing_imports = true
```

**Target (D-08):**
```toml
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

**`[tool.uv.workspace]`** — `members = ["packages/*"]` needs no change; it discovers by glob and will auto-pick up `packages/godoo-meta/`.

---

### `.github/workflows/test.yml` (CI config, transform)

**Analog:** itself — current state shown below.

**Current `lint` job mypy step** (line 24):
```yaml
- run: uv run mypy packages/godoo/src packages/godoo-testcontainers/src
```

**Target (D-08):**
```yaml
- run: uv run mypy packages/godoo/src packages/godoo-testcontainers/src packages/godoo-introspection/src
```

The `explicit_package_bases` and `mypy_path` additions to root `pyproject.toml [tool.mypy]` (above) mean the CLI invocation itself only needs the third src tree appended. No other changes to `test.yml` are required.

**Full current `lint` job for reference** (lines 14-24):
```yaml
lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v6
      with:
        python-version: "3.14"
    - run: uv sync
    - run: uv run ruff check .
    - run: uv run ruff format --check .
    - run: uv run mypy packages/godoo/src packages/godoo-testcontainers/src
```

**Full current `integration` job for reference** (lines 41-57) — no changes needed; matrix and gate already correct:
```yaml
integration:
  runs-on: ubuntu-latest
  needs: [lint, unit-tests]
  strategy:
    fail-fast: false
    matrix:
      odoo-version: ["17.0", "18.0", "19.0"]
  env:
    ODOO_VERSION: ${{ matrix.odoo-version }}
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v6
      with:
        python-version: "3.14"
    - run: uv sync
    - run: uv run pytest tests/integration/ -v -s -m integration --log-cli-level=ERROR
      timeout-minutes: 15
```

---

### `.github/workflows/release.yml` (CI config, reference)

**Analog:** itself — current state shown below. No changes required to `release.yml` itself; the `build_command` update is in root `pyproject.toml`.

**Full current file** (lines 1-43):
```yaml
name: Release

on:
  workflow_run:
    workflows: ["Test"]
    types: [completed]
    branches: [main]

concurrency:
  group: release
  cancel-in-progress: false

permissions:
  contents: write
  id-token: write

jobs:
  release:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment: pypi

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.14"

      - run: uv sync

      - name: Semantic Release
        id: release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: uv run semantic-release version

      - name: Publish to PyPI
        if: steps.release.outcome == 'success'
        run: uv publish --trusted-publishing always
```

`uv publish` uploads all `.whl` and `.tar.gz` from `dist/` in one pass — the four-distribution build in `build_command` produces all artifacts into `dist/`, then this single `uv publish` call handles them all. Requires clean `dist/` before `uv build`.

---

## Src Layout — Current Tree Shapes

### `packages/godoo/src/godoo/` (current)

```
src/godoo/
├── __init__.py          ← MUST MOVE to src/godoo/client/__init__.py (content verbatim + updated internal paths)
├── client.py            ← moves to src/godoo/client/client.py
├── config.py            ← moves to src/godoo/client/config.py
├── errors.py            ← moves to src/godoo/client/errors.py
├── py.typed             ← moves to src/godoo/client/py.typed
├── rpc/
│   ├── __init__.py
│   ├── transport.py
│   └── types.py
├── safety/
│   └── __init__.py
└── services/
    ├── __init__.py
    ├── accounting/ {__init__, functions, service, types}
    ├── attendance/ {__init__, functions, service, types}
    ├── cdc/        {__init__, field_cache, functions, resolver, service, types}
    ├── mail/       {__init__, functions, service, types}
    ├── modules/    {__init__, module_manager, types}
    ├── properties/ {__init__, functions, service, types}  (no types.py listed, but properties/ dir present)
    ├── timesheets/ {__init__, functions, service, types}
    └── urls/       {__init__, functions, service, types}
```

**Target:** `src/godoo/` directory gets NO `__init__.py` (namespace root). All content under `src/godoo/client/` with subdirectory structure preserved.

### `packages/godoo-introspection/src/godoo_introspection/` (current)

```
src/godoo_introspection/
├── __init__.py
├── codegen.py
├── introspector.py
├── markers.py
├── py.typed
├── type_mapper.py
└── types.py
```

**Target:** Directory renamed/moved to `src/godoo/introspection/` with `__init__.py` kept; no `__init__.py` at `src/godoo/`.

### `packages/godoo-testcontainers/src/godoo_testcontainers/` (current)

```
src/godoo_testcontainers/
├── __init__.py
├── container.py
├── harness.py
├── properties.py
├── py.typed
├── seed_resolver.py
└── snapshot.py
```

**Target:** Directory renamed/moved to `src/godoo/testcontainers/` with `__init__.py` kept; no `__init__.py` at `src/godoo/`.

---

## Import Migration Surface

### Current `packages/godoo/src/godoo/__init__.py` (lines 1-48)

This file is the barrel that moves verbatim (with internal paths updated) to `src/godoo/client/__init__.py`. Current content:

```python
from godoo.client import OdooClient, OdooClientConfig
from godoo.config import config_from_env, create_client
from godoo.errors import (
    OdooAccessError,
    OdooAuthError,
    OdooError,
    OdooMissingError,
    OdooNetworkError,
    OdooRpcError,
    OdooSafetyError,
    OdooTimeoutError,
    OdooValidationError,
)
from godoo.safety import OperationInfo, SafetyContext
from godoo.services.accounting import AccountingService
from godoo.services.attendance import AttendanceService
from godoo.services.cdc import CdcService
from godoo.services.mail import MailService
from godoo.services.modules import ModuleManager
from godoo.services.properties import PropertiesService
from godoo.services.timesheets import TimesheetsService
from godoo.services.urls import UrlService
```

After move to `src/godoo/client/__init__.py`, the `from godoo.X` imports become `from godoo.client.X` (e.g. `from godoo.client.client import OdooClient`). The `__all__` list is unchanged.

**Critical subtlety:** `from godoo.client import OdooClient` in the OLD tree resolves to `src/godoo/client.py`. In the NEW tree it resolves to `src/godoo/client/__init__.py`. All external consumers of `from godoo.client import OdooClient` keep working IF the new `__init__.py` barrel-exports `OdooClient`.

---

### Cross-Package Import Migration — Concrete File:Line Anchors

**`packages/godoo-testcontainers/src/godoo_testcontainers/container.py` lines 14-16:**
```python
from godoo import OdooClient, OdooClientConfig
from godoo.errors import OdooNetworkError, OdooTimeoutError
from godoo.services.modules import ModuleManager
```
→ becomes:
```python
from godoo.client import OdooClient, OdooClientConfig
from godoo.client.errors import OdooNetworkError, OdooTimeoutError
from godoo.client.services.modules import ModuleManager
```
Internal refs on lines 22-23 (`from godoo_testcontainers.seed_resolver`, `from godoo_testcontainers.snapshot`) → `from godoo.testcontainers.seed_resolver`, `from godoo.testcontainers.snapshot`.

**`packages/godoo-testcontainers/src/godoo_testcontainers/harness.py` lines 6-13:**
```python
from godoo_testcontainers.container import OdooTestContainer, StartedOdooContainer
from godoo_testcontainers.properties import ConfigParameterHelper
# ...
from godoo import OdooClient                          # TYPE_CHECKING
from godoo.services.modules import ModuleManager      # TYPE_CHECKING
```
→ becomes:
```python
from godoo.testcontainers.container import OdooTestContainer, StartedOdooContainer
from godoo.testcontainers.properties import ConfigParameterHelper
# ...
from godoo.client import OdooClient                          # TYPE_CHECKING
from godoo.client.services.modules import ModuleManager      # TYPE_CHECKING
```

**`packages/godoo-introspection/src/godoo_introspection/introspector.py` lines 7, 12:**
```python
from godoo.errors import OdooMissingError, OdooValidationError
from godoo_introspection.types import FieldSchema, ModelSchema
# ...
from godoo.client import OdooClient   # TYPE_CHECKING
```
→ becomes:
```python
from godoo.client.errors import OdooMissingError, OdooValidationError
from godoo.introspection.types import FieldSchema, ModelSchema
# ...
from godoo.client.client import OdooClient   # TYPE_CHECKING
```

**`packages/godoo-introspection/src/godoo_introspection/codegen.py` lines 8, 13-14, 159:**
```python
from godoo_introspection.type_mapper import python_type_str
# TYPE_CHECKING:
from godoo_introspection.introspector import Introspector
from godoo_introspection.types import FieldSchema, ModelSchema
# line 159 (string emitted by codegen, not an import itself):
"from godoo_introspection.markers import FieldMeta",
```
→ becomes:
```python
from godoo.introspection.type_mapper import python_type_str
# TYPE_CHECKING:
from godoo.introspection.introspector import Introspector
from godoo.introspection.types import FieldSchema, ModelSchema
# line 159:
"from godoo.introspection.markers import FieldMeta",
```

**`packages/godoo-introspection/src/godoo_introspection/__init__.py` lines 1-4:**
```python
from godoo_introspection.codegen import CodeGenerator
from godoo_introspection.introspector import IntrospectionCache, Introspector
from godoo_introspection.markers import FieldMeta
from godoo_introspection.types import FieldSchema, ModelSchema
```
→ becomes:
```python
from godoo.introspection.codegen import CodeGenerator
from godoo.introspection.introspector import IntrospectionCache, Introspector
from godoo.introspection.markers import FieldMeta
from godoo.introspection.types import FieldSchema, ModelSchema
```

**`packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py` lines 1-4:**
```python
from godoo_testcontainers.container import OdooTestContainer, StartedOdooContainer
from godoo_testcontainers.harness import TestHarness
from godoo_testcontainers.seed_resolver import SeedInfo, normalise_odoo_version, resolve_seed_info
from godoo_testcontainers.snapshot import SnapshotConfig
```
→ becomes:
```python
from godoo.testcontainers.container import OdooTestContainer, StartedOdooContainer
from godoo.testcontainers.harness import TestHarness
from godoo.testcontainers.seed_resolver import SeedInfo, normalise_odoo_version, resolve_seed_info
from godoo.testcontainers.snapshot import SnapshotConfig
```

---

### Test File Import Migration — Concrete Anchors

| File | Old import | New import |
|------|-----------|-----------|
| `tests/conftest.py:4` | `from godoo_testcontainers import OdooTestContainer` | `from godoo.testcontainers import OdooTestContainer` |
| `tests/integration/test_crud.py:8` | `from godoo import OdooClient` (TYPE_CHECKING) | `from godoo.client import OdooClient` |
| `tests/integration/test_modules.py:8` | `from godoo_testcontainers import StartedOdooContainer` (TYPE_CHECKING) | `from godoo.testcontainers import StartedOdooContainer` |
| `packages/godoo/tests/test_client.py:12` | `from godoo.client import OdooClient, OdooClientConfig, _ambient_context` | `from godoo.client.client import OdooClient, OdooClientConfig, _ambient_context` |
| `packages/godoo/tests/test_client.py:13` | `from godoo.errors import OdooAuthError, ...` | `from godoo.client.errors import OdooAuthError, ...` |
| `packages/godoo-testcontainers/tests/test_container.py:5` | `from godoo_testcontainers.container import OdooTestContainer` | `from godoo.testcontainers.container import OdooTestContainer` |
| `packages/godoo-testcontainers/tests/test_integration.py:21-23` | `from godoo_testcontainers import TestHarness` / `from godoo_testcontainers.seed_resolver import ...` / `from godoo_testcontainers.snapshot import ...` | `from godoo.testcontainers import TestHarness` / `from godoo.testcontainers.seed_resolver import ...` / `from godoo.testcontainers.snapshot import ...` |
| `packages/godoo-testcontainers/tests/test_harness.py:11` | `from godoo_testcontainers.harness import TestHarness as Harness` | `from godoo.testcontainers.harness import TestHarness as Harness` |
| `packages/godoo-introspection/tests/test_codegen.py:10-11` | `from godoo_introspection.codegen import ...` / `from godoo_introspection.types import ...` | `from godoo.introspection.codegen import ...` / `from godoo.introspection.types import ...` |
| `packages/godoo-introspection/tests/test_codegen.py:65` | `assert "from godoo_introspection.markers import FieldMeta" in result` | `assert "from godoo.introspection.markers import FieldMeta" in result` |
| `packages/godoo-introspection/tests/test_introspector.py:10-12` | `from godoo_introspection.*` | `from godoo.introspection.*` |
| `packages/godoo-introspection/tests/test_type_mapper.py:8-9` | `from godoo_introspection.*` | `from godoo.introspection.*` |

All remaining test files under `packages/godoo-testcontainers/tests/` (`test_snapshot.py`, `test_seed_resolver.py`, `test_properties.py`) import from `godoo_testcontainers.*` → migrate to `godoo.testcontainers.*`. All `packages/godoo/tests/test_*.py` files import from `godoo.*` → migrate to `godoo.client.*`.

---

## Shared Patterns

### Namespace Root Invariant
**Apply to:** All three package src restructures and the placeholder.
**Rule:** `src/godoo/` directories across ALL four package trees must contain NO `__init__.py`.
**Verification command (run after each restructure step):**
```bash
find packages/ -path "*/src/godoo/__init__.py"
# Must return zero results
```
**Wheel verification (run after `uv build --package godoo-client`):**
```bash
unzip -l dist/godoo_client-*.whl | grep "godoo/__init__"
# Must return zero lines
```

### py.typed Placement
**Apply to:** All three real distributions.
**Current locations:** `packages/godoo/src/godoo/py.typed`, `packages/godoo-introspection/src/godoo_introspection/py.typed`, `packages/godoo-testcontainers/src/godoo_testcontainers/py.typed`.
**Target locations:** `packages/godoo/src/godoo/client/py.typed`, `packages/godoo-introspection/src/godoo/introspection/py.typed`, `packages/godoo-testcontainers/src/godoo/testcontainers/py.typed`.
**Rationale:** PEP 561 requires `py.typed` in the submodule, not the namespace root.

### `uv sync` After Config Changes
**Apply to:** Any step that modifies `project.name`, `[tool.uv.sources]`, or adds a new workspace member.
**Pattern:** Immediately after editing pyproject.toml, run `uv sync` to verify workspace resolution. Failure mode: `Could not find workspace member 'godoo'` if `[tool.uv.sources]` key is not updated atomically with the `project.name` rename.

### `dist/` Cleanup Before Build
**Apply to:** Any local or CI build step.
**Pattern:** `rm -rf dist/` before `uv build` calls. Prevents Pitfall 5 (stale wheels from old distribution names causing PyPI re-upload rejection).

---

## No Analog Found

No files in this phase are truly without structural analog — all are transforms of existing files. The only genuinely new file is the placeholder distribution; its closest template is `packages/godoo-introspection/pyproject.toml` (structurally simplest existing pyproject: no subpackage deps, minimal classifiers).

---

## Metadata

**Analog search scope:** `packages/*/pyproject.toml`, `.github/workflows/*.yml`, `packages/*/src/**/__init__.py`, `tests/**/*.py`, `packages/*/tests/**/*.py`
**Files scanned:** 4 pyproject.toml, 2 workflow YAML, 6 `__init__.py` files, 5 key source files, 13 test files
**Pattern extraction date:** 2026-05-22
