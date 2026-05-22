---
phase: 03-testcontainers-parity
verified: 2026-05-22T11:40:15Z
status: human_needed
score: 10/10 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run a real integration test with OdooTestContainer(snapshot=True) twice and confirm the second run restores from snapshot and completes faster"
    expected: "First run saves a .dump file under cwd/.odoo-testcontainers/snapshots/; second run with identical inputs restores it via pg_restore and skips module install"
    why_human: "Requires Docker. pg_dump/restore, container volume-mapping, and timing can only be confirmed against a live container."
  - test: "Run OdooTestContainer(addons_path=Path('./my_addons')) and verify the custom module directory is visible inside the Odoo container"
    expected: "Directory mounted at /mnt/extra-addons (single path) or /mnt/addons-0,1,... (list); --addons-path CLI arg includes both core Odoo path and the mounted target"
    why_human: "Requires Docker. Volume mapping and --addons-path correctness can only be confirmed against a live container."
  - test: "Run async with TestHarness(modules=['base'], properties={'web.base.url': 'http://test'}) as h: and verify h.client, h.modules, h.properties all resolve"
    expected: "Container starts, base is installed, ir.config_parameter web.base.url = http://test is set, h.client returns an authenticated OdooClient"
    why_human: "Requires Docker. Full lifecycle (start + properties RPC) can only be verified against a live Odoo instance."
---

# Phase 3: Testcontainers Parity Verification Report

**Phase Goal:** The godoo-testcontainers package reaches parity with @godoo/testcontainers, scoped to the bare minimum per the D-Drop-1 scope cut — snapshot caching (TESTC-01), custom addons mount (TESTC-02), properties provisioner / ir.config_parameter (TESTC-06), TestHarness async-cm wrapper (TESTC-07), and a py.typed marker (TESTC-08). TESTC-03/04/05 (partners/projects/users provisioners) were intentionally HARD-DROPPED to the sibling godoo-stateman project.
**Verified:** 2026-05-22T11:40:15Z
**Status:** human_needed
**Re-verification:** No — initial verification

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

The automated checks pass completely. Three integration-level behaviors require a live Docker environment to confirm.

#### 1. Snapshot Cache Hit/Miss Cycle

**Test:** Run a test suite that creates `OdooTestContainer(snapshot=True, modules=["base"])` twice with identical inputs.
**Expected:** First run produces a `.dump` file under `cwd/.odoo-testcontainers/snapshots/`. Second run detects the file via `has_snapshot()`, calls `restore_snapshot()`, and skips the `--init base` + module install phase — completing significantly faster.
**Why human:** Requires Docker. Timing comparison, pg_dump/restore correctness, and `snapshot_hit` branch cannot be exercised without a live Postgres container.

#### 2. Custom Addons Mount

**Test:** Create a minimal Odoo addon directory, pass it as `addons_path=Path("./my_addons")` to `OdooTestContainer`, start the container, and exec into Odoo to confirm the directory is visible at `/mnt/extra-addons` and `--addons-path` includes it.
**Expected:** Module discovery succeeds; `odoo --addons-path /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons` is passed as the container command.
**Why human:** Requires Docker. Volume mapping and --addons-path CLI arg can only be confirmed in a live container.

#### 3. TestHarness Full Lifecycle

**Test:** `async with TestHarness(modules=["base"], properties={"web.base.url": "http://test.local"}) as h:` — then call `h.client.search_read("res.partner", [])` and verify `h.properties.set("x", "y")` completes without error.
**Expected:** Container starts, base module is installed, `ir.config_parameter web.base.url` is set to `http://test.local`, `h.client` is an authenticated `OdooClient`.
**Why human:** Requires Docker. Full async-cm lifecycle (start + RPC properties seeding + client authentication) can only be exercised against a live Odoo instance.

---

### Gaps Summary

No gaps found. All 10 must-haves are verified against the codebase. The three human verification items are purely integration-level tests (Docker-required) — they test runtime correctness of already-verified source logic, not missing implementation.

The only notable implementation deviation from the PLAN spec: `properties.py` imports `Mapping` under `TYPE_CHECKING` (rather than at module level) — this is strictly more correct than the plan suggested (reduces runtime import overhead) and passes mypy strict. Not a gap.

---

_Verified: 2026-05-22T11:40:15Z_
_Verifier: Claude (gsd-verifier)_
