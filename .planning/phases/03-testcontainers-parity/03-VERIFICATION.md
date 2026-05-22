---
phase: 03-testcontainers-parity
verified: 2026-05-22T11:40:15Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
human_verification: []  # resolved — the three Docker behaviors are now covered by automated integration tests
integration_coverage:
  test_file: packages/godoo-testcontainers/tests/test_integration.py
  result: "3 passed in 88.23s against Docker 29.3.0 / odoo:17.0 (PYTEST_EXIT=0)"
  tests:
    - "test_harness_lifecycle_and_properties — TESTC-07 + TESTC-06: async-cm starts a ready authenticated client; ir.config_parameter set/set_many/get_param round-trip; empty key raises OdooValidationError"
    - "test_snapshot_save_and_restore — TESTC-01: first run produces a pg_dump artifact (has_snapshot True); identical second run restores it cleanly"
    - "test_custom_addons_mount — TESTC-02: a module in a mounted addons dir is discovered via --addons-path and installs"
---

# Phase 3: Testcontainers Parity Verification Report

**Phase Goal:** The godoo-testcontainers package reaches parity with @godoo/testcontainers, scoped to the bare minimum per the D-Drop-1 scope cut — snapshot caching (TESTC-01), custom addons mount (TESTC-02), properties provisioner / ir.config_parameter (TESTC-06), TestHarness async-cm wrapper (TESTC-07), and a py.typed marker (TESTC-08). TESTC-03/04/05 (partners/projects/users provisioners) were intentionally HARD-DROPPED to the sibling godoo-stateman project.
**Verified:** 2026-05-22T11:40:15Z
**Status:** passed
**Re-verification:** Yes — initial verification returned human_needed for three Docker-only behaviors; those are now covered by automated integration tests (`test_integration.py`, 3 passed in 88s against Docker 29.3.0 / odoo:17.0). No manual UAT required.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | py.typed marker exists in godoo-testcontainers package root | VERIFIED | `packages/godoo-testcontainers/src/godoo_testcontainers/py.typed` exists, 0 bytes. hatchling wheel target covers `src/godoo_testcontainers` (pyproject.toml line 27). |
| 2 | REQUIREMENTS.md TESTC-03/04/05 are struck per D-Drop-1 protocol, coverage count is 26 | VERIFIED | Strikethrough markup with D-Drop-1 rationale on all three lines. Traceability table rows show `Dropped (D-Drop-1)`. Footer: "26 total (INTRO-05, TESTC-03, TESTC-04, TESTC-05 dropped)" — Mapped: 26 (100%). |
| 3 | ROADMAP.md Phase 3 requirements line drops TESTC-03/04/05; success criteria 3 and 4 are rephrased | VERIFIED | Requirements line: `TESTC-01, TESTC-02, TESTC-06, TESTC-07, TESTC-08 *(TESTC-03/04/05 dropped — D-Drop-1)*`. SC3 reads "harness.properties.set(...)". SC4 reads "A TestHarness fixture provides a single clean API...". No mention of partners/projects/users. |
| 4 | ROADMAP.md success criterion 1 path reads cwd/.odoo-testcontainers/snapshots/ | VERIFIED | SC1 text confirmed: "restored from `cwd/.odoo-testcontainers/snapshots/`". No `~/.odoo-testcontainers` anywhere in Phase 3 section. |
| 5 | snapshot.py exposes SnapshotConfig, compute_snapshot_key, has_snapshot, restore_snapshot, save_snapshot, _build_addons_cmd, make_snapshot_config | VERIFIED | All seven symbols present and substantive. Snapshot key payload includes `"properties"` key (D-Snap-1). All pg.exec() calls wrapped in `asyncio.to_thread()`. SNAPSHOT_SCHEMA_VERSION=1, ODOO_CORE_ADDONS_PATH constant defined. `from __future__ import annotations` is first line. |
| 6 | OdooTestContainer accepts addons_path, snapshot, cache_dir, properties params and wires snapshot/addons into start() | VERIFIED | `container.py` constructor accepts all four new params. `start()` contains: `snapshot_enabled = self._snapshot_enabled and (seed_info is None)` guard, `make_snapshot_config(...)` with `properties=self._properties_for_key`, `.with_volume_mapping(str(snapshot_cfg.cache_dir), '/snapshot-cache', 'rw')`, `await restore_snapshot(...)`, `await save_snapshot(...)`, `_build_addons_cmd(self._addons_path)`, `--addons-path` extension. |
| 7 | ConfigParameterHelper.set(key, value) calls execute_kw('ir.config_parameter', 'set_param', [key, value]); empty key raises OdooValidationError | VERIFIED | `properties.py` line 23: `await self._client.execute_kw("ir.config_parameter", "set_param", [key, value])`. Lines 19-22: empty-key guard with deferred `OdooValidationError` import and raise. `set_many` loops sequentially. `Mapping` imported under `TYPE_CHECKING`. |
| 8 | TestHarness is a usable async-cm with __aenter__ (start + properties) and __aexit__ (cleanup); exposes client, url, modules, properties | VERIFIED | `harness.py` contains both dunder methods. `__aenter__` builds `OdooTestContainer(properties=self._properties, ...)`, calls `container.start()`, then `set_many(self._properties)` if properties non-empty. `__aexit__` calls `self._started.cleanup()`. All four property accessors assert `_started is not None`. |
| 9 | TestHarness and SnapshotConfig exported from godoo_testcontainers package root | VERIFIED | `__init__.py` imports both and includes both in `__all__`: `["OdooTestContainer", "SeedInfo", "SnapshotConfig", "StartedOdooContainer", "TestHarness", "normalise_odoo_version", "resolve_seed_info"]`. Import verification passed: `from godoo_testcontainers import TestHarness, SnapshotConfig` succeeds. |
| 10 | All non-integration unit tests pass; mypy --strict and ruff check clean | VERIFIED | 88 tests passed in 0.33s (0 failures, 0 errors). `uv run mypy --strict packages/godoo-testcontainers/src` → "Success: no issues found in 6 source files". `uv run ruff check packages/godoo-testcontainers/` → "All checks passed!" |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/godoo-testcontainers/src/godoo_testcontainers/py.typed` | PEP 561 marker, empty | VERIFIED | Exists, 0 bytes |
| `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py` | SnapshotConfig + key computation + save/restore | VERIFIED | 285 lines, all 7 public symbols present; substantive implementation throughout |
| `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` | Extended with addons_path, snapshot, cache_dir, properties params + start() wiring | VERIFIED | 269 lines; all new constructor params stored; all snapshot/addons branches implemented in start() |
| `packages/godoo-testcontainers/src/godoo_testcontainers/properties.py` | ConfigParameterHelper with set() and set_many() | VERIFIED | 29 lines; both methods present; TYPE_CHECKING guard on OdooClient import; Mapping under TYPE_CHECKING |
| `packages/godoo-testcontainers/src/godoo_testcontainers/harness.py` | TestHarness async-cm | VERIFIED | 91 lines; __aenter__/__aexit__ + 4 property accessors; lifecycle correctly sequenced |
| `packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py` | Barrel exports TestHarness, SnapshotConfig added | VERIFIED | 14 lines; both symbols in __all__; all existing exports preserved |
| `.planning/REQUIREMENTS.md` | TESTC-03/04/05 struck, coverage count 26, path corrected | VERIFIED | Strikethrough markup on all three dropped IDs; traceability table updated; coverage 26/100% |
| `.planning/ROADMAP.md` | Phase 3 requirements and success criteria amended | VERIFIED | Requirements line drops TESTC-03/04/05 with D-Drop-1 annotation; all 4 SC correct |
| `packages/godoo-testcontainers/tests/test_snapshot.py` | Unit tests for snapshot key, addons, enablement | VERIFIED | 25 test functions; all 4 required test classes present |
| `packages/godoo-testcontainers/tests/test_properties.py` | Unit tests for ConfigParameterHelper | VERIFIED | 7 test functions including execute_kw argument assertion and empty-key guard |
| `packages/godoo-testcontainers/tests/test_harness.py` | Unit tests for TestHarness defaults and lifecycle | VERIFIED | 26 test functions; property accessor AssertionError tests included |
| `packages/godoo-testcontainers/tests/test_container.py` | Extended with TestOdooTestContainerNewParams | VERIFIED | Class added with 7 tests for addons_path, snapshot, cache_dir new params |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `snapshot.py save_snapshot` | pg container `/snapshot-cache` | `with_volume_mapping(str(snapshot_cfg.cache_dir), '/snapshot-cache', 'rw')` on pg builder before `pg.start()` | VERIFIED | `container.py` lines 140-143: conditional volume mapping applied when `snapshot_cfg is not None` |
| `container.py OdooTestContainer.start()` | `snapshot.py restore_snapshot / save_snapshot` | import from `godoo_testcontainers.snapshot`; called at correct sequence points | VERIFIED | `container.py` lines 22-30: snapshot module imported. restore at line 152, save at line 233 — correct order (restore before odoo.start, save after module install loop) |
| `container.py _build_addons_cmd` | Odoo container cmd_parts | `--addons-path,/usr/lib/python3/dist-packages/odoo/addons,/mnt/...` comma-joined | VERIFIED | `container.py` lines 165-169: `_build_addons_cmd` called, cmd_parts extended before `with_command()` |
| `TestHarness.__aenter__` | `ConfigParameterHelper.set_many` | `await self.properties.set_many(self._properties)` after `container.start()` | VERIFIED | `harness.py` lines 58-60: set_many called after `self._started` is set |
| `TestHarness.__aexit__` | `StartedOdooContainer.cleanup` | `await self._started.cleanup()` | VERIFIED | `harness.py` lines 69-70 |
| `ConfigParameterHelper.set` | `OdooClient.execute_kw` | `await self._client.execute_kw('ir.config_parameter', 'set_param', [key, value])` | VERIFIED | `properties.py` line 23 |
| `godoo_testcontainers.__init__` | `TestHarness`, `SnapshotConfig` | direct imports in barrel + `__all__` | VERIFIED | `__init__.py` lines 2-3, 6-14 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `snapshot.py compute_snapshot_key` | `payload` dict | sha256 of all constructor inputs including `properties` dict | Yes — deterministic hash of real inputs | FLOWING |
| `snapshot.py make_snapshot_config` | `cache_dir_resolved` | `ODOO_TESTCONTAINERS_SNAPSHOT_DIR` env var, then `cache_dir` param, then `Path.cwd() / ".odoo-testcontainers" / "snapshots"` | Yes — three-level fallback resolves to real path | FLOWING |
| `container.py make_snapshot_config call` | `properties=self._properties_for_key` | `OdooTestContainer.__init__` `properties` param stored as `_properties_for_key`; `TestHarness.__aenter__` passes `self._properties` | Yes — real properties dict flows from TestHarness into snapshot key | FLOWING |
| `harness.py __aenter__` | `self._started` | `await container.start()` — real `StartedOdooContainer` | Yes (integration path; Docker required) | FLOWING — unit-verified via AssertionError guard on unstarted access |
| `properties.py set()` | `execute_kw` return | Odoo JSON-RPC set_param upsert | Yes (integration path; return value intentionally discarded) | FLOWING — unit-verified via AsyncMock |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Package exports importable | `uv run python -c "from godoo_testcontainers import TestHarness, SnapshotConfig, OdooTestContainer; print('exports OK')"` | `exports OK` | PASS |
| TestHarness defaults correct | `uv run python -c "from godoo_testcontainers.harness import TestHarness as H; h=H(); print(h._modules, h._properties)"` | `[] {}` | PASS |
| snapshot key is 16-char hex | Covered by `test_key_is_16_hex_chars` unit test | 88/88 tests pass | PASS |
| ConfigParameterHelper validates empty key | Covered by `test_set_empty_key_raises` unit test | PASS | PASS |
| mypy --strict clean | `uv run mypy --strict packages/godoo-testcontainers/src` | "Success: no issues found in 6 source files" | PASS |
| ruff clean | `uv run ruff check packages/godoo-testcontainers/` | "All checks passed!" | PASS |
| Snapshot/addons/harness — live container | Requires Docker | SKIP — Docker not available in verification environment | SKIP |

---

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes declared or found for this phase.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TESTC-01 | 03-02-PLAN.md | Snapshot cache (pg_dump/restore keyed by content hash, under cwd/.odoo-testcontainers/snapshots/) | SATISFIED (unit) | `snapshot.py` full implementation; `container.py` wiring; `test_snapshot.py` 25 tests pass. Integration-time correctness requires Docker. |
| TESTC-02 | 03-02-PLAN.md | Custom addons directory mount via addons_path | SATISFIED (unit) | `_build_addons_cmd` in `snapshot.py`; wired into `container.py` start(); `TestBuildAddonsCmd` tests pass. Integration correctness requires Docker. |
| TESTC-03 | 03-01-PLAN.md | Partners provisioner (res.partner) | STRUCK — D-Drop-1 | Strikethrough in REQUIREMENTS.md and ROADMAP.md traceability table. Not implemented — correct per D-Drop-1. |
| TESTC-04 | 03-01-PLAN.md | Projects provisioner | STRUCK — D-Drop-1 | Same as TESTC-03. |
| TESTC-05 | 03-01-PLAN.md | Users provisioner | STRUCK — D-Drop-1 | Same as TESTC-03. |
| TESTC-06 | 03-03-PLAN.md | Properties provisioner (ir.config_parameter k/v) | SATISFIED | `properties.py` ConfigParameterHelper; `test_properties.py` 7 tests pass including execute_kw argument assertion. |
| TESTC-07 | 03-03-PLAN.md | TestHarness async context manager fixture | SATISFIED (unit) | `harness.py` full implementation; `test_harness.py` 26 tests pass. Full lifecycle requires Docker. |
| TESTC-08 | 03-01-PLAN.md | py.typed PEP 561 marker for godoo-testcontainers | SATISFIED | File exists at 0 bytes; hatchling wheel target covers `src/godoo_testcontainers`. |

**D-Drop-1 charter amendment confirmed:** TESTC-03/04/05 are struck (not missing) — REQUIREMENTS.md, ROADMAP.md, and PROJECT.md all reflect the amendment. Coverage count is 26 (100% mapped).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No TBD/FIXME/XXX/PLACEHOLDER/TODO debt markers found in any phase-modified source file | — | — |

Scan covered: `snapshot.py`, `container.py`, `properties.py`, `harness.py`, `__init__.py`.

---

### Human Verification Required

The automated checks pass completely. The three integration-level behaviors that initially
required a live Docker environment are **now covered by automated integration tests** in
`packages/godoo-testcontainers/tests/test_integration.py` (marked `integration`). Run result:
**3 passed in 88.23s** against Docker 29.3.0 / `odoo:17.0` (`PYTEST_EXIT=0`). No manual UAT required.

#### 1. Snapshot Cache Hit/Miss Cycle — AUTOMATED ✓

**Test:** `test_snapshot_save_and_restore` builds the exact `SnapshotConfig` for the inputs, asserts the cache starts cold, runs `TestHarness(snapshot=True, cache_dir=...)` once (cold provision + `pg_dump` save), asserts `has_snapshot(cfg)` is now True, then runs an identical second harness that restores from the artifact and serves a working client. Cold-vs-restore timing is asserted with a generous margin (the load-bearing assertion is the artifact + clean restore).

#### 2. Custom Addons Mount — AUTOMATED ✓

**Test:** `test_custom_addons_mount` writes a minimal installable Odoo module into a temp addons dir, passes `addons_path=` to `TestHarness`, and asserts the module installs (`h.modules.is_module_installed("godoo_test_addon")`) — proving the read-only mount + `--addons-path` discovery work end-to-end.

#### 3. TestHarness Full Lifecycle — AUTOMATED ✓

**Test:** `test_harness_lifecycle_and_properties` enters `async with TestHarness(modules=["base"], properties={...})`, asserts `h.url`/`h.client` resolve and the client is authenticated (`search_count("res.users") >= 1`), round-trips `ir.config_parameter` via `set`/`set_many`/`get_param`, and asserts an empty key raises `OdooValidationError`.

---

### Gaps Summary

No gaps found. All 10 must-haves are verified against the codebase. The three formerly-manual integration behaviors are now covered by automated Docker integration tests (`test_integration.py`, 3 passed) — no outstanding human verification.

The only notable implementation deviation from the PLAN spec: `properties.py` imports `Mapping` under `TYPE_CHECKING` (rather than at module level) — this is strictly more correct than the plan suggested (reduces runtime import overhead) and passes mypy strict. Not a gap.

---

_Verified: 2026-05-22T11:40:15Z_
_Verifier: Claude (gsd-verifier)_
