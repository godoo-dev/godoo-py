---
phase: "03-testcontainers-parity"
plan: 3
subsystem: "godoo-testcontainers"
tags: ["testcontainers", "properties", "harness", "async-cm", "ir.config_parameter"]
dependency_graph:
  requires:
    - "03-02"  # snapshot cache + addons mount wired into container.py
  provides:
    - "ConfigParameterHelper (set, set_many via execute_kw ir.config_parameter)"
    - "TestHarness async-cm (start + properties + cleanup)"
    - "Package barrel exports: TestHarness, SnapshotConfig"
  affects:
    - "godoo_testcontainers package public API"
    - "OdooTestContainer (properties key param added)"
tech_stack:
  added: []
  patterns:
    - "TYPE_CHECKING guard for OdooClient import in testcontainers-internal helper"
    - "Deferred OdooValidationError import inside method body (local-precondition-validation)"
    - "Async context manager (TestHarness.__aenter__/__aexit__)"
    - "ConfigParameterHelper property instantiated on-demand (stateless helper)"
key_files:
  created:
    - "packages/godoo-testcontainers/src/godoo_testcontainers/properties.py"
    - "packages/godoo-testcontainers/src/godoo_testcontainers/harness.py"
    - "packages/godoo-testcontainers/tests/test_properties.py"
    - "packages/godoo-testcontainers/tests/test_harness.py"
  modified:
    - "packages/godoo-testcontainers/src/godoo_testcontainers/container.py"
    - "packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py"
decisions:
  - "ConfigParameterHelper is testcontainers-internal (properties.py), not a godoo core service quad (D-Harness-1)"
  - "OdooValidationError imported with deferred import inside method to avoid circular imports"
  - "TestHarness.properties accessor instantiates ConfigParameterHelper on each access (stateless — no caching needed)"
  - "Test file uses 'from ... import TestHarness as Harness' alias to suppress pytest PytestCollectionWarning"
  - "Mapping moved to TYPE_CHECKING block in properties.py per ruff TC003; Path moved to TYPE_CHECKING in harness.py"
metrics:
  duration: "4 minutes"
  completed_date: "2026-05-22"
  tasks_completed: 3
  files_changed: 6
---

# Phase 3 Plan 3: Properties Provisioner + TestHarness Summary

**One-liner:** ir.config_parameter provisioner (ConfigParameterHelper) + TestHarness async-cm wrapping OdooTestContainer with post-start properties seeding and snapshot key accuracy.

## What Was Built

### ConfigParameterHelper (properties.py)
Testcontainers-internal helper class with two public async methods:
- `set(key, value)` — calls `execute_kw("ir.config_parameter", "set_param", [key, value])`. Guards empty key with `OdooValidationError` before any RPC (T-03-03-01 mitigation).
- `set_many(values)` — sequential loop over `set()` (not `asyncio.gather` — `set_param` is not batch-safe).

Pattern: `OdooClient` imported under `TYPE_CHECKING` only. `Mapping` also moved to `TYPE_CHECKING` block per ruff TC003. `OdooValidationError` imported with deferred import inside the method body to avoid circular imports.

### OdooTestContainer extension (container.py)
Added `properties: dict[str, str] | None = None` parameter to `__init__`, stored as `self._properties_for_key`. The old hardcoded `properties={}` in the `make_snapshot_config` call is replaced with `properties=self._properties_for_key`. This ensures that different `properties=` dicts produce different snapshot keys (D-Snap-1 full-flow coverage), preventing stale snapshot restores.

The container itself does NOT call `set_param` — that remains TestHarness's responsibility.

### TestHarness async-cm (harness.py)
Thin async context manager composing `OdooTestContainer`:
- Constructor accepts all `OdooTestContainer` params plus `properties: dict[str, str] | None`.
- `__aenter__`: builds `OdooTestContainer(properties=self._properties, ...)`, calls `container.start()`, then applies properties via `self.properties.set_many(self._properties)` post-start.
- `__aexit__`: delegates to `self._started.cleanup()`.
- Property accessors (`client`, `url`, `modules`, `properties`) all guard against unstarted state with `AssertionError`.
- `properties` accessor returns `ConfigParameterHelper(self._started.client)` on each access (stateless helper — no caching).

### Package barrel (__init__.py)
Added `TestHarness` (from `.harness`) and `SnapshotConfig` (from `.snapshot`) to imports and `__all__`. `ConfigParameterHelper` intentionally not exported (testcontainers-internal per D-Harness-1).

### Unit tests
- `test_properties.py`: 7 tests covering `set()` execute_kw call shape, `OdooValidationError` on empty key (with no-RPC-call guard), `set_many()` call count, empty-dict noop, key-value preservation, empty-value acceptance.
- `test_harness.py`: 24 tests covering default attribute values, custom param storage, `None`-to-empty normalization, and `AssertionError` guards on unstarted property accessors.

## Verification Results

- `uv run mypy --strict packages/godoo-testcontainers/src` — 0 issues (6 source files)
- `uv run ruff check packages/godoo-testcontainers/` — 0 issues
- `uv run pytest packages/ -m "not integration"` — all tests pass
- `from godoo_testcontainers import TestHarness, SnapshotConfig, OdooTestContainer` — works
- `from godoo_testcontainers.properties import ConfigParameterHelper` — works

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Code Style] Ruff TC003: Mapping and Path moved to TYPE_CHECKING blocks**
- **Found during:** Task 1 (properties.py) and Task 2 (harness.py)
- **Issue:** `from collections.abc import Mapping` and `from pathlib import Path` were runtime imports but only used in type annotations (which become strings with `from __future__ import annotations`)
- **Fix:** Moved both to `if TYPE_CHECKING:` blocks per ruff TC003 rule
- **Files modified:** `properties.py`, `harness.py`

**2. [Rule 1 - Code Style] Ruff B017: Specific exception type instead of Exception in tests**
- **Found during:** Task 3 (test_properties.py)
- **Issue:** `pytest.raises(Exception)` triggers ruff B017 (blind exception assertion)
- **Fix:** Import `OdooValidationError` from `godoo.errors` and use it directly in `pytest.raises(OdooValidationError)`
- **Files modified:** `test_properties.py`

**3. [Rule 1 - Code Style] Import alias in test_harness.py to suppress PytestCollectionWarning**
- **Found during:** Task 3 (test_harness.py)
- **Issue:** Pytest attempts to collect `TestHarness` as a test class (name starts with `Test`) but emits `PytestCollectionWarning` because it has `__init__`
- **Fix:** `from godoo_testcontainers.harness import TestHarness as Harness` alias in test file
- **Files modified:** `test_harness.py`

## Known Stubs

None — all data sources are wired. `ConfigParameterHelper.set_many` iterates the caller's dict; no placeholder values.

## Threat Flags

No new security-relevant surface introduced beyond what was planned. T-03-03-01 (empty key guard) was explicitly mitigated.

## Self-Check: PASSED

- `packages/godoo-testcontainers/src/godoo_testcontainers/properties.py` — FOUND
- `packages/godoo-testcontainers/src/godoo_testcontainers/harness.py` — FOUND
- `packages/godoo-testcontainers/tests/test_properties.py` — FOUND
- `packages/godoo-testcontainers/tests/test_harness.py` — FOUND
- Commit `60a5f70` (Task 1) — FOUND
- Commit `48090d0` (Task 2) — FOUND
- Commit `225ce5e` (Task 3) — FOUND
