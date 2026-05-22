---
phase: "04-release"
plan: 02
type: execute
wave: 2
depends_on:
  - "04-01"
files_modified:
  - packages/godoo/pyproject.toml
  - packages/godoo-introspection/pyproject.toml
  - packages/godoo-testcontainers/pyproject.toml
  - pyproject.toml
  - packages/godoo/src/godoo/client/__init__.py
  - packages/godoo/src/godoo/client/client.py
  - packages/godoo/src/godoo/client/config.py
  - packages/godoo/src/godoo/client/errors.py
  - packages/godoo/src/godoo/client/py.typed
  - packages/godoo/src/godoo/client/rpc/__init__.py
  - packages/godoo/src/godoo/client/rpc/transport.py
  - packages/godoo/src/godoo/client/rpc/types.py
  - packages/godoo/src/godoo/client/safety/__init__.py
  - packages/godoo/src/godoo/client/services/__init__.py
  - packages/godoo/src/godoo/client/services/accounting/__init__.py
  - packages/godoo/src/godoo/client/services/attendance/__init__.py
  - packages/godoo/src/godoo/client/services/cdc/__init__.py
  - packages/godoo/src/godoo/client/services/mail/__init__.py
  - packages/godoo/src/godoo/client/services/modules/__init__.py
  - packages/godoo/src/godoo/client/services/properties/__init__.py
  - packages/godoo/src/godoo/client/services/timesheets/__init__.py
  - packages/godoo/src/godoo/client/services/urls/__init__.py
  - packages/godoo-introspection/src/godoo/introspection/__init__.py
  - packages/godoo-introspection/src/godoo/introspection/codegen.py
  - packages/godoo-introspection/src/godoo/introspection/introspector.py
  - packages/godoo-introspection/src/godoo/introspection/markers.py
  - packages/godoo-introspection/src/godoo/introspection/type_mapper.py
  - packages/godoo-introspection/src/godoo/introspection/types.py
  - packages/godoo-introspection/src/godoo/introspection/py.typed
  - packages/godoo-testcontainers/src/godoo/testcontainers/__init__.py
  - packages/godoo-testcontainers/src/godoo/testcontainers/container.py
  - packages/godoo-testcontainers/src/godoo/testcontainers/harness.py
  - packages/godoo-testcontainers/src/godoo/testcontainers/properties.py
  - packages/godoo-testcontainers/src/godoo/testcontainers/seed_resolver.py
  - packages/godoo-testcontainers/src/godoo/testcontainers/snapshot.py
  - packages/godoo-testcontainers/src/godoo/testcontainers/py.typed
  - packages/godoo/tests/test_client.py
  - packages/godoo/tests/test_config.py
  - packages/godoo/tests/test_safety.py
  - packages/godoo-testcontainers/tests/test_container.py
  - packages/godoo-testcontainers/tests/test_integration.py
  - packages/godoo-testcontainers/tests/test_snapshot.py
  - packages/godoo-testcontainers/tests/test_seed_resolver.py
  - packages/godoo-testcontainers/tests/test_properties.py
  - packages/godoo-testcontainers/tests/test_harness.py
  - packages/godoo-introspection/tests/test_codegen.py
  - packages/godoo-introspection/tests/test_introspector.py
  - packages/godoo-introspection/tests/test_type_mapper.py
  - tests/conftest.py
  - tests/integration/test_crud.py
  - tests/integration/test_modules.py
autonomous: true
requirements:
  - RELEASE-02

must_haves:
  truths:
    - "User can run `from godoo.client import OdooClient` and get OdooClient"
    - "User can run `from godoo.introspection import Introspector` and get Introspector"
    - "User can run `from godoo.testcontainers import OdooTestContainer` and get OdooTestContainer"
    - "No distribution ships a godoo/__init__.py (namespace invariant holds)"
    - "All three wheels installed into a single venv coexist without namespace poisoning"
    - "mypy passes on all three src trees under the new namespace layout"
    - "All unit tests pass under the new import paths"
    - "uv workspace resolves godoo-client as a workspace member"
  decisions_covered:
    - "D-01: shared `godoo` PEP 420 implicit namespace — no top-level `godoo/__init__.py` ships in any distribution."
    - "D-02: PyPI distribution names are godoo-client, godoo-introspection, and godoo-testcontainers (client renamed from godoo)."
    - "D-03: import migration in scope across all three packages — all `from godoo_*` and `from godoo.` references updated to new namespace paths."
  artifacts:
    - path: "packages/godoo/src/godoo/client/__init__.py"
      provides: "Barrel re-exports for godoo.client namespace — OdooClient, OdooClientConfig, errors, safety, services"
      contains: "from godoo.client.client import"
    - path: "packages/godoo-introspection/src/godoo/introspection/__init__.py"
      provides: "Barrel re-exports for godoo.introspection namespace"
      contains: "from godoo.introspection.introspector import"
    - path: "packages/godoo-testcontainers/src/godoo/testcontainers/__init__.py"
      provides: "Barrel re-exports for godoo.testcontainers namespace"
      contains: "from godoo.testcontainers.container import"
    - path: "packages/godoo/pyproject.toml"
      provides: "godoo-client distribution config with hatchling namespace packaging"
      contains: "godoo-client"
  key_links:
    - from: "packages/godoo/pyproject.toml [tool.hatch.build.targets.wheel]"
      to: "src/godoo/client/ directory"
      via: "only-include = [\"src/godoo/client\"]"
      pattern: "only-include"
    - from: "packages/godoo-introspection/pyproject.toml"
      to: "src/godoo/introspection/ directory"
      via: "only-include = [\"src/godoo/introspection\"]"
      pattern: "only-include"
    - from: "pyproject.toml [tool.uv.sources]"
      to: "packages/godoo/pyproject.toml project.name"
      via: "godoo-client = { workspace = true }"
      pattern: "godoo-client"
---

<objective>
Restructure all three packages into a shared `godoo` PEP 420 implicit namespace — moving source trees to `src/godoo/client/`, `src/godoo/introspection/`, `src/godoo/testcontainers/` — and rename the client distribution from `godoo` to `godoo-client`. Migrate all internal and cross-package imports, update pyproject.toml files, and verify the namespace invariant holds across all three built wheels including coexistence in a single venv.

Purpose: RELEASE-02 — the import surface `from godoo.client import OdooClient` / `from godoo.introspection import Introspector` / `from godoo.testcontainers import OdooTestContainer` is the public API. The `azure.*` / `google.cloud.*` pattern requires no `godoo/__init__.py` in any wheel.

Output: All three src trees under `src/godoo/{subpackage}/`, three pyproject.toml files updated with hatchling namespace config, root pyproject.toml updated for the renamed workspace member, all imports migrated, all unit tests passing, wheels buildable with correct namespace layout, coexistence verified in a clean venv.
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

<interfaces>
<!-- Key contracts for this plan. Extracted from PATTERNS.md §"Import Migration Surface". -->
<!-- Executor MUST NOT explore further — all import anchors are enumerated below. -->

Current barrel: packages/godoo/src/godoo/__init__.py
```python
from godoo.client import OdooClient, OdooClientConfig
from godoo.config import config_from_env, create_client
from godoo.errors import (OdooAccessError, OdooAuthError, OdooError,
    OdooMissingError, OdooNetworkError, OdooRpcError, OdooSafetyError,
    OdooTimeoutError, OdooValidationError)
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
After move to src/godoo/client/__init__.py, `from godoo.X` → `from godoo.client.X`
(e.g., `from godoo.client.client import OdooClient, OdooClientConfig`)

Key cross-package import anchors (from PATTERNS.md):
- container.py:14-16: from godoo import ... → from godoo.client import ...
- harness.py:6-13: from godoo_testcontainers.* → from godoo.testcontainers.*
- introspector.py:7,12: from godoo.errors → from godoo.client.errors
- codegen.py:8,13-14,159: from godoo_introspection.* → from godoo.introspection.*
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Restructure src layouts — move all three package source trees</name>
  <files>
    packages/godoo/src/godoo/client/__init__.py,
    packages/godoo/src/godoo/client/client.py,
    packages/godoo/src/godoo/client/config.py,
    packages/godoo/src/godoo/client/errors.py,
    packages/godoo/src/godoo/client/py.typed,
    packages/godoo/src/godoo/client/rpc/__init__.py,
    packages/godoo/src/godoo/client/rpc/transport.py,
    packages/godoo/src/godoo/client/rpc/types.py,
    packages/godoo/src/godoo/client/safety/__init__.py,
    packages/godoo/src/godoo/client/services/__init__.py,
    packages/godoo/src/godoo/client/services/accounting/__init__.py,
    packages/godoo/src/godoo/client/services/accounting/functions.py,
    packages/godoo/src/godoo/client/services/accounting/service.py,
    packages/godoo/src/godoo/client/services/accounting/types.py,
    packages/godoo/src/godoo/client/services/attendance/__init__.py,
    packages/godoo/src/godoo/client/services/attendance/functions.py,
    packages/godoo/src/godoo/client/services/attendance/service.py,
    packages/godoo/src/godoo/client/services/attendance/types.py,
    packages/godoo/src/godoo/client/services/cdc/__init__.py,
    packages/godoo/src/godoo/client/services/cdc/field_cache.py,
    packages/godoo/src/godoo/client/services/cdc/functions.py,
    packages/godoo/src/godoo/client/services/cdc/resolver.py,
    packages/godoo/src/godoo/client/services/cdc/service.py,
    packages/godoo/src/godoo/client/services/cdc/types.py,
    packages/godoo/src/godoo/client/services/mail/__init__.py,
    packages/godoo/src/godoo/client/services/mail/functions.py,
    packages/godoo/src/godoo/client/services/mail/service.py,
    packages/godoo/src/godoo/client/services/mail/types.py,
    packages/godoo/src/godoo/client/services/modules/__init__.py,
    packages/godoo/src/godoo/client/services/modules/module_manager.py,
    packages/godoo/src/godoo/client/services/modules/types.py,
    packages/godoo/src/godoo/client/services/properties/__init__.py,
    packages/godoo/src/godoo/client/services/properties/functions.py,
    packages/godoo/src/godoo/client/services/properties/service.py,
    packages/godoo/src/godoo/client/services/timesheets/__init__.py,
    packages/godoo/src/godoo/client/services/timesheets/functions.py,
    packages/godoo/src/godoo/client/services/timesheets/service.py,
    packages/godoo/src/godoo/client/services/timesheets/types.py,
    packages/godoo/src/godoo/client/services/urls/__init__.py,
    packages/godoo/src/godoo/client/services/urls/functions.py,
    packages/godoo/src/godoo/client/services/urls/service.py,
    packages/godoo/src/godoo/client/services/urls/types.py,
    packages/godoo-introspection/src/godoo/introspection/__init__.py,
    packages/godoo-introspection/src/godoo/introspection/codegen.py,
    packages/godoo-introspection/src/godoo/introspection/introspector.py,
    packages/godoo-introspection/src/godoo/introspection/markers.py,
    packages/godoo-introspection/src/godoo/introspection/type_mapper.py,
    packages/godoo-introspection/src/godoo/introspection/types.py,
    packages/godoo-introspection/src/godoo/introspection/py.typed,
    packages/godoo-testcontainers/src/godoo/testcontainers/__init__.py,
    packages/godoo-testcontainers/src/godoo/testcontainers/container.py,
    packages/godoo-testcontainers/src/godoo/testcontainers/harness.py,
    packages/godoo-testcontainers/src/godoo/testcontainers/properties.py,
    packages/godoo-testcontainers/src/godoo/testcontainers/seed_resolver.py,
    packages/godoo-testcontainers/src/godoo/testcontainers/snapshot.py,
    packages/godoo-testcontainers/src/godoo/testcontainers/py.typed
  </files>
  <read_first>
    - .planning/phases/04-release/04-PATTERNS.md §"Src Layout — Current Tree Shapes" (full current tree for all three packages)
    - .planning/phases/04-release/04-RESEARCH.md §"Recommended Project Structure (post-rename)" (exact target layout)
    - .planning/phases/04-release/04-PATTERNS.md §"Import Migration Surface" — barrel content that must move verbatim (with updated paths) to src/godoo/client/__init__.py
    - .planning/phases/04-release/04-RESEARCH.md §"Pitfall 1" and §"Pitfall 2" (namespace-root __init__.py rules)
    - packages/godoo/src/godoo/__init__.py (current barrel content to carry forward)
  </read_first>
  <action>
    Perform three directory restructures using git mv to preserve history:

    PACKAGE 1 — godoo client:
    - Create `packages/godoo/src/godoo/client/` directory.
    - `git mv packages/godoo/src/godoo/__init__.py packages/godoo/src/godoo/client/__init__.py`
    - `git mv packages/godoo/src/godoo/client.py packages/godoo/src/godoo/client/client.py`
    - `git mv packages/godoo/src/godoo/config.py packages/godoo/src/godoo/client/config.py`
    - `git mv packages/godoo/src/godoo/errors.py packages/godoo/src/godoo/client/errors.py`
    - `git mv packages/godoo/src/godoo/py.typed packages/godoo/src/godoo/client/py.typed`
    - `git mv packages/godoo/src/godoo/rpc packages/godoo/src/godoo/client/rpc`
    - `git mv packages/godoo/src/godoo/safety packages/godoo/src/godoo/client/safety`
    - `git mv packages/godoo/src/godoo/services packages/godoo/src/godoo/client/services`
    - CRITICAL: Verify `packages/godoo/src/godoo/` contains NO `__init__.py` after the moves. The namespace-root directory must exist as an empty directory (only the `client/` subdir inside it).

    PACKAGE 2 — godoo-introspection:
    - Create `packages/godoo-introspection/src/godoo/introspection/` directory.
    - `git mv packages/godoo-introspection/src/godoo_introspection packages/godoo-introspection/src/godoo/introspection`
    - CRITICAL: After the move, `packages/godoo-introspection/src/godoo/` must contain NO `__init__.py`.

    PACKAGE 3 — godoo-testcontainers:
    - Create `packages/godoo-testcontainers/src/godoo/testcontainers/` directory.
    - `git mv packages/godoo-testcontainers/src/godoo_testcontainers packages/godoo-testcontainers/src/godoo/testcontainers`
    - CRITICAL: After the move, `packages/godoo-testcontainers/src/godoo/` must contain NO `__init__.py`.

    After ALL three moves, update internal imports in ALL moved files:

    godoo client internal imports (all files under src/godoo/client/):
    - All `from godoo.X` references become `from godoo.client.X` (e.g., `from godoo.errors import` → `from godoo.client.errors import`)
    - In client/__init__.py (barrel): update all `from godoo.X` → `from godoo.client.X`
    - In client.py: any self-references that used `from godoo.` must become `from godoo.client.`
    - In services/*/functions.py and service.py: `from godoo.client import OdooClient` (TYPE_CHECKING) becomes `from godoo.client.client import OdooClient`
    - In rpc/transport.py: `from godoo.errors import` → `from godoo.client.errors import`
    - In safety/__init__.py: any `from godoo.` refs → `from godoo.client.`

    godoo-introspection internal imports (all files under src/godoo/introspection/):
    - All `from godoo_introspection.X` → `from godoo.introspection.X`
    - All `from godoo.errors import` → `from godoo.client.errors import`
    - All `from godoo.client import OdooClient` (TYPE_CHECKING) → `from godoo.client.client import OdooClient`
    - In codegen.py line 159: the string `"from godoo_introspection.markers import FieldMeta"` → `"from godoo.introspection.markers import FieldMeta"` (this is a string literal emitted by codegen, not a Python import statement)

    godoo-testcontainers internal imports (all files under src/godoo/testcontainers/):
    - All `from godoo_testcontainers.X` → `from godoo.testcontainers.X`
    - All `from godoo import OdooClient` / `from godoo import OdooClientConfig` → `from godoo.client import OdooClient` / `from godoo.client import OdooClientConfig`
    - All `from godoo.errors import` → `from godoo.client.errors import`
    - All `from godoo.services.modules import` → `from godoo.client.services.modules import`

    All files must retain `from __future__ import annotations` as their first line (per CLAUDE.md convention).
  </action>
  <verify>
    <automated>uv run pytest packages/ -m "not integration" -q</automated>
  </verify>
  <acceptance_criteria>
    - `find packages/ -path "*/src/godoo/__init__.py"` returns zero results (namespace invariant)
    - `uv sync` exits 0 (workspace still resolves — note: project.name not yet changed in this task; that is Task 2)
    - `uv run python -c "from godoo.client import OdooClient"` exits 0
    - `uv run python -c "from godoo.introspection import Introspector"` exits 0
    - `uv run python -c "from godoo.testcontainers import OdooTestContainer"` exits 0
    - `uv run pytest packages/ -m "not integration" -q` exits 0 (all unit tests pass)
    - `uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src` exits 0
    - No file under any `src/godoo/` directory-level (the namespace root) contains an `__init__.py`
  </acceptance_criteria>
  <done>All three src trees restructured under src/godoo/{subpackage}/; all internal imports updated; namespace invariant holds; unit tests pass</done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Update pyproject.toml files for namespace packaging and rename godoo → godoo-client</name>
  <files>
    packages/godoo/pyproject.toml,
    packages/godoo-introspection/pyproject.toml,
    packages/godoo-testcontainers/pyproject.toml,
    pyproject.toml
  </files>
  <read_first>
    - packages/godoo/pyproject.toml (full file — current state per PATTERNS.md §"packages/godoo/pyproject.toml")
    - packages/godoo-introspection/pyproject.toml (full file — current state per PATTERNS.md §"packages/godoo-introspection/pyproject.toml")
    - packages/godoo-testcontainers/pyproject.toml (full file — current state per PATTERNS.md §"packages/godoo-testcontainers/pyproject.toml")
    - pyproject.toml (root, full file — current [tool.uv.sources], [tool.coverage.run], [tool.semantic_release])
    - .planning/phases/04-release/04-PATTERNS.md §"Root pyproject.toml" for target states
    - .planning/phases/04-release/04-RESEARCH.md §"Pattern 1" (hatchling namespace config), §"Pattern 3" (placeholder), §"Pattern 4" (uv sources), §"Pattern 5" (semantic-release)
  </read_first>
  <action>
    Make these TOML changes atomically (all four files in one commit):

    packages/godoo/pyproject.toml:
    - `name = "godoo"` → `name = "godoo-client"`
    - [project.urls] Repository → `https://github.com/godoo-dev/godoo-py`
    - [project.urls] Issues → `https://github.com/godoo-dev/godoo-py/issues`
    - [tool.hatch.build.targets.wheel]: replace `packages = ["src/godoo"]` with `sources = ["src"]` and `only-include = ["src/godoo/client"]` (two separate TOML keys in the same stanza)

    packages/godoo-introspection/pyproject.toml:
    - `dependencies = ["godoo>=0.1.0"]` → `dependencies = ["godoo-client>=0.1.0"]`
    - [project.urls] Repository → `https://github.com/godoo-dev/godoo-py`
    - [project.urls] Issues → `https://github.com/godoo-dev/godoo-py/issues` (add if not present)
    - [tool.hatch.build.targets.wheel]: replace `packages = ["src/godoo_introspection"]` with `sources = ["src"]` and `only-include = ["src/godoo/introspection"]`

    packages/godoo-testcontainers/pyproject.toml:
    - `dependencies = ["godoo>=0.1.0", "testcontainers[postgres]>=4"]` → `dependencies = ["godoo-client>=0.1.0", "testcontainers[postgres]>=4"]`
    - [project.urls] Repository → `https://github.com/godoo-dev/godoo-py`
    - [project.urls] Issues → `https://github.com/godoo-dev/godoo-py/issues` (add if not present)
    - [tool.hatch.build.targets.wheel]: replace `packages = ["src/godoo_testcontainers"]` with `sources = ["src"]` and `only-include = ["src/godoo/testcontainers"]`

    Root pyproject.toml:
    - [tool.uv.sources]: `godoo = { workspace = true }` → `godoo-client = { workspace = true }`
    - [tool.coverage.run] source_pkgs: `["godoo", "godoo_testcontainers", "godoo_introspection"]` → `["godoo.client", "godoo.testcontainers", "godoo.introspection"]`
    - [tool.semantic_release] version_toml: path stays `packages/godoo/pyproject.toml:project.version` (directory path unchanged); no change needed here
    - [tool.semantic_release] build_command: `--package godoo` → `--package godoo-client` (the first entry only; the other two distribution names are unchanged)

    After editing all four files, run `uv sync` immediately to verify workspace resolution. If `uv sync` fails with "Could not find workspace member 'godoo'", the [tool.uv.sources] key and the project.name rename must be aligned — check both files before proceeding.
  </action>
  <verify>
    <automated>uv sync && uv run python -c "from godoo.client import OdooClient; from godoo.introspection import Introspector; from godoo.testcontainers import OdooTestContainer; print('all three coexist')"</automated>
  </verify>
  <acceptance_criteria>
    - `packages/godoo/pyproject.toml` has `name = "godoo-client"` and `only-include = ["src/godoo/client"]`
    - `packages/godoo-introspection/pyproject.toml` has `dependencies = ["godoo-client>=0.1.0"]` and `only-include = ["src/godoo/introspection"]`
    - `packages/godoo-testcontainers/pyproject.toml` has `dependencies = ["godoo-client>=0.1.0", ...]` and `only-include = ["src/godoo/testcontainers"]`
    - Root `pyproject.toml` has `godoo-client = { workspace = true }` and `source_pkgs = ["godoo.client", "godoo.testcontainers", "godoo.introspection"]`
    - `uv sync` exits 0 (godoo-client resolves as workspace member)
    - `uv run python -c "from godoo.client import OdooClient; from godoo.introspection import Introspector; from godoo.testcontainers import OdooTestContainer; print('ok')"` exits 0
    - `uv run pytest packages/ -m "not integration" -q` exits 0
    - `uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src` exits 0
  </acceptance_criteria>
  <done>All pyproject.toml files updated; godoo-client resolves correctly in uv workspace; hatchling namespace config set for all three distributions; all tests still pass</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Migrate test file imports and verify wheel namespace invariant across all three distributions</name>
  <files>
    packages/godoo/tests/test_client.py,
    packages/godoo/tests/test_config.py,
    packages/godoo/tests/test_safety.py,
    packages/godoo-testcontainers/tests/test_container.py,
    packages/godoo-testcontainers/tests/test_integration.py,
    packages/godoo-testcontainers/tests/test_snapshot.py,
    packages/godoo-testcontainers/tests/test_seed_resolver.py,
    packages/godoo-testcontainers/tests/test_properties.py,
    packages/godoo-testcontainers/tests/test_harness.py,
    packages/godoo-introspection/tests/test_codegen.py,
    packages/godoo-introspection/tests/test_introspector.py,
    packages/godoo-introspection/tests/test_type_mapper.py,
    tests/conftest.py,
    tests/integration/test_crud.py,
    tests/integration/test_modules.py
  </files>
  <read_first>
    - .planning/phases/04-release/04-PATTERNS.md §"Test File Import Migration — Concrete Anchors" (full table with old → new import mappings for every test file)
    - .planning/phases/04-release/04-RESEARCH.md §"Import Migration Surface" (categories table for remaining test files)
    - packages/godoo/tests/test_client.py (read before editing — verify lines 12-13 imports)
    - packages/godoo-testcontainers/tests/test_container.py (read before editing — verify imports)
    - tests/conftest.py (read before editing — line 4 import)
  </read_first>
  <action>
    Migrate imports in every test file per the PATTERNS.md §"Test File Import Migration" anchor table:

    packages/godoo/tests/test_client.py:
    - Line 12: `from godoo.client import OdooClient, OdooClientConfig, _ambient_context` → `from godoo.client.client import OdooClient, OdooClientConfig, _ambient_context`
    - Line 13: `from godoo.errors import OdooAuthError, ...` → `from godoo.client.errors import OdooAuthError, ...`

    packages/godoo/tests/test_config.py and test_safety.py:
    - Migrate any `from godoo.X` → `from godoo.client.X` (read files first to identify all instances)

    packages/godoo-testcontainers/tests/ (all files):
    - All `from godoo_testcontainers.X` → `from godoo.testcontainers.X`
    - All `from godoo import` → `from godoo.client import`
    - All `from godoo.errors import` → `from godoo.client.errors import`
    - test_integration.py: per PATTERNS.md anchor — TestHarness, seed_resolver, snapshot imports

    packages/godoo-introspection/tests/ (all files):
    - All `from godoo_introspection.X` → `from godoo.introspection.X`
    - test_codegen.py line 65: assertion string `"from godoo_introspection.markers import FieldMeta"` → `"from godoo.introspection.markers import FieldMeta"`

    tests/conftest.py:
    - Line 4: `from godoo_testcontainers import OdooTestContainer` → `from godoo.testcontainers import OdooTestContainer`

    tests/integration/test_crud.py:
    - Line 8: `from godoo import OdooClient` (TYPE_CHECKING) → `from godoo.client import OdooClient`

    tests/integration/test_modules.py:
    - Line 8: `from godoo_testcontainers import StartedOdooContainer` (TYPE_CHECKING) → `from godoo.testcontainers import StartedOdooContainer`

    After migrating ALL test imports, build all three wheels and verify the namespace invariant across every distribution:
    - `rm -rf dist/`
    - `uv build --package godoo-client && uv build --package godoo-introspection && uv build --package godoo-testcontainers`
    - `unzip -l dist/godoo_client-*.whl | grep "godoo/__init__"` → must return zero lines (no namespace-root __init__)
    - `unzip -l dist/godoo_introspection-*.whl | grep "godoo/__init__"` → must return zero lines
    - `unzip -l dist/godoo_testcontainers-*.whl | grep "godoo/__init__"` → must return zero lines
    - `unzip -l dist/godoo_client-*.whl | grep "godoo/"` → output must show ONLY `godoo/client/...` entries

    After the wheel checks, perform the coexistence check — this is the actual namespace-poisoning failure scenario:
    - Create a fresh venv: `python -m venv /tmp/godoo-coexist-test`
    - Install all three built wheels: `/tmp/godoo-coexist-test/bin/pip install dist/godoo_client-*.whl dist/godoo_introspection-*.whl dist/godoo_testcontainers-*.whl`
    - `/tmp/godoo-coexist-test/bin/python -c "import godoo.client, godoo.introspection, godoo.testcontainers; print('coexistence OK')"` — this must exit 0
    - If it fails with `ImportError: cannot import name ...` or a namespace conflict error, the `only-include` hatchling config in one of the three wheels is wrong — inspect `unzip -l dist/<failing-wheel>` to identify which wheel is shipping the wrong content.
  </action>
  <verify>
    <automated>uv run ruff check . && uv run ruff format --check . && uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src && uv run pytest packages/ -m "not integration" -q</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest packages/ -m "not integration" -q` exits 0 — all unit tests pass with new import paths
    - `uv run ruff check .` exits 0 — no linting errors in test files
    - `uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src` exits 0
    - `unzip -l dist/godoo_client-*.whl | grep "godoo/__init__"` returns zero lines (namespace invariant in godoo-client wheel)
    - `unzip -l dist/godoo_introspection-*.whl | grep "godoo/__init__"` returns zero lines (namespace invariant in godoo-introspection wheel)
    - `unzip -l dist/godoo_testcontainers-*.whl | grep "godoo/__init__"` returns zero lines (namespace invariant in godoo-testcontainers wheel)
    - `unzip -l dist/godoo_client-*.whl | grep "godoo/"` shows only `godoo/client/` entries
    - `/tmp/godoo-coexist-test/bin/python -c "import godoo.client, godoo.introspection, godoo.testcontainers"` exits 0 (coexistence verified in clean venv)
    - `find packages/ -path "*/src/godoo/__init__.py"` returns zero results
    - `find packages/ -name "godoo_testcontainers" -o -name "godoo_introspection"` returns zero results (old directory names gone)
  </acceptance_criteria>
  <done>All test imports migrated; full unit test suite passes; all three wheels verified to contain no namespace-root __init__.py; all three wheels coexist correctly in a clean venv</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| src/godoo/ namespace root | No __init__.py must exist here across any of the three package trees; a stray __init__.py poisons all three distributions |
| Wheel contents | hatchling must not include any sibling subpackage content or namespace-root __init__.py in any wheel |
| uv workspace resolution | [tool.uv.sources] key must match project.name exactly; desync causes resolution failure |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-02-01 | Tampering | src/godoo/ namespace root | mitigate | Post-restructure invariant check: `find packages/ -path "*/src/godoo/__init__.py"` must return zero; enforced in every task's acceptance criteria |
| T-04-02-02 | Tampering | hatchling wheel contents — all three distributions | mitigate | Wheel inspection via `unzip -l dist/<wheel>.whl | grep "godoo/__init__"` must return zero lines for ALL THREE wheels; run in Task 3 acceptance criteria |
| T-04-02-03 | Denial of Service | uv workspace desync on rename | mitigate | [tool.uv.sources] key renamed atomically with project.name in Task 2; `uv sync` run immediately as verification |
| T-04-02-04 | Information Disclosure | codegen.py emitted import string | mitigate | The string `"from godoo_introspection.markers import FieldMeta"` is code generated and emitted to user files — must be updated to `"from godoo.introspection.markers import FieldMeta"` in codegen.py line 159; covered by test_codegen.py line 65 assertion |
| T-04-02-05 | Tampering | namespace coexistence — stray __init__.py in any wheel | mitigate | Task 3 clean-venv coexistence check: install all three built wheels into a fresh venv and verify `import godoo.client, godoo.introspection, godoo.testcontainers` exits 0 — catches the actual failure scenario missed by per-wheel inspection alone |
| T-04-02-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed in this plan; all tooling already in uv.lock |
</threat_model>

<verification>
After all three tasks complete and committed:
- `find packages/ -path "*/src/godoo/__init__.py"` returns zero results
- `uv run python -c "from godoo.client import OdooClient; from godoo.introspection import Introspector; from godoo.testcontainers import OdooTestContainer; print('OK')"` exits 0
- `uv run pytest packages/ -m "not integration" -q` exits 0
- `uv run ruff check . && uv run ruff format --check .` exits 0
- `uv run mypy packages/godoo/src packages/godoo-introspection/src packages/godoo-testcontainers/src` exits 0
- `unzip -l dist/godoo_client-*.whl | grep "godoo/__init__"` returns zero lines
- `unzip -l dist/godoo_introspection-*.whl | grep "godoo/__init__"` returns zero lines
- `unzip -l dist/godoo_testcontainers-*.whl | grep "godoo/__init__"` returns zero lines
- Clean-venv coexistence: `import godoo.client, godoo.introspection, godoo.testcontainers` exits 0
- `uv sync` exits 0
- `git push origin develop` triggers CI and lint + unit-tests pass
</verification>

<success_criteria>
- `from godoo.client import OdooClient` resolves correctly post-restructure
- `from godoo.introspection import Introspector` resolves correctly
- `from godoo.testcontainers import OdooTestContainer` resolves correctly
- No `godoo/__init__.py` exists in any src tree or in any of the three wheels
- godoo-client wheel contains only `godoo/client/*` entries
- All three wheels coexist in a clean venv without namespace collisions
- All unit tests pass; mypy and ruff both exit 0
- uv workspace resolves godoo-client correctly
</success_criteria>

<output>
Create `.planning/phases/04-release/04-02-SUMMARY.md` when done
</output>
