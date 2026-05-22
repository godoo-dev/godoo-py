---
phase: "03-testcontainers-parity"
plan: 2
subsystem: "godoo-testcontainers"
tags: ["snapshot-cache", "addons-mount", "testcontainers", "pg-dump"]
dependency_graph:
  requires: ["03-01"]
  provides: ["snapshot.py", "container.py-extended"]
  affects: ["03-03"]
tech_stack:
  added: []
  patterns:
    - "asyncio.to_thread wrapping for pg.exec() snapshot operations"
    - "temp-file + atomic os.replace() concurrent snapshot save"
    - "sha256[:16] hex snapshot key with sorted JSON payload"
key_files:
  created:
    - "packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py"
    - "packages/godoo-testcontainers/tests/test_snapshot.py"
  modified:
    - "packages/godoo-testcontainers/src/godoo_testcontainers/container.py"
    - "packages/godoo-testcontainers/tests/test_container.py"
decisions:
  - "Path moved to TYPE_CHECKING in container.py (TC003 ruff rule — not used at runtime)"
  - "Module docstring removed from snapshot.py (E402 ruff rule — after from __future__ causes E402)"
  - "pytest moved to TYPE_CHECKING in test_snapshot.py (TC002 — only used in annotations)"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-22"
  tasks: 3
  files: 4
---

# Phase 3 Plan 2: Snapshot Cache + Addons Mount Summary

**One-liner:** pg_dump/restore snapshot cache keyed by sha256[:16] of provisioner inputs + custom addons bind-mount with `--addons-path` CLI wiring into `OdooTestContainer`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement snapshot.py | 26014b1 | snapshot.py (new) |
| 2 | Wire snapshot + addons into container.py | 5af5d30 | container.py (modified) |
| 3 | Unit tests for snapshot key + container params | 1b2c383 | test_snapshot.py (new), test_container.py (extended) |

## What Was Built

### snapshot.py (new)

New module owning all snapshot cache logic. Key exports:

- `SnapshotConfig` dataclass — `enabled`, `key` (16-char hex), `cache_dir`, plus `host_path` and `container_path` properties
- `compute_snapshot_key()` — sha256[:16] of a stable JSON payload including `properties` dict (D-Snap-1), sorted modules, sorted env, addons content tree
- `_hash_addons_path()` — walks each addons directory, collects `(relative_path, sha256(bytes))` per file ignoring `.git/node_modules/__pycache__/.pytest_cache`, returns per-mount dicts
- `_build_addons_cmd()` — returns `(mounts, targets)` for `with_volume_mapping` + `--addons-path` construction
- `make_snapshot_config()` — factory honouring `ODOO_TESTCONTAINERS_SNAPSHOT=disabled` (D-Snap-2) and `ODOO_TESTCONTAINERS_SNAPSHOT_DIR` env overrides; defaults to `cwd/.odoo-testcontainers/snapshots/` (D-Snap-3)
- `has_snapshot()` — `cfg.enabled and cfg.host_path.exists()`
- `restore_snapshot()` — dropdb / createdb / pg_restore via `asyncio.to_thread(pg.exec, ...)`
- `save_snapshot()` — temp-file + atomic `os.replace()` protocol safe under concurrent pytest workers

Module-level constants: `SNAPSHOT_SCHEMA_VERSION = 1`, `CACHE_CONTAINER_DIR = "/snapshot-cache"`, `ODOO_CORE_ADDONS_PATH = "/usr/lib/python3/dist-packages/odoo/addons"`

### container.py (extended)

`OdooTestContainer.__init__` gains three new keyword-only params:
- `addons_path: Path | list[Path] | None = None`
- `snapshot: bool = True`
- `cache_dir: Path | None = None`

Stored as `self._addons_path`, `self._snapshot_enabled`, `self._cache_dir`.

`start()` insertion points (in order):

1. **After `resolve_seed_info()`:** `snapshot_enabled = self._snapshot_enabled and (seed_info is None)` — seed-image guard; snapshot caching is skipped when a seed image covers the modules
2. **In else branch before `pg.start()`:** `make_snapshot_config(properties={})` + `cache_dir.mkdir()` + `pg.with_volume_mapping(cache_dir, '/snapshot-cache', 'rw')` — bind-mount cache dir rw into pg container
3. **After both pg branches complete:** `restore_snapshot()` on cache hit; sets `snapshot_hit = True`
4. **cmd_parts construction:** `if not seed_info and not snapshot_hit:` guards `--init base` — skipped when snapshot is hit (DB already has base installed)
5. **After cmd_parts, before `with_command`:** `_build_addons_cmd()` extends `cmd_parts` with `--addons-path ODOO_CORE_ADDONS_PATH,/mnt/...` and adds `with_volume_mapping` calls on the odoo container
6. **After module install loop:** `save_snapshot()` on cache miss — non-fatal (logged as warning if save fails)

### Tests

`test_snapshot.py` (25 tests, all sync):
- `TestComputeSnapshotKey` — identical inputs, different modules, order-independence for modules and properties, D-Snap-1 properties coverage, 16-hex-char validation, user_key invalidation, env order independence
- `TestSnapshotEnablement` — enabled by default, disabled by param, disabled by env (case-insensitive), cache dir default (`cwd/.odoo-testcontainers/snapshots/`), param override, env override
- `TestBuildAddonsCmd` — None returns empty, single path → `/mnt/extra-addons`, list → `/mnt/addons-0,1`, ro mode, resolved absolute paths
- `TestSnapshotConfigPaths` — host_path, container_path, key-based filename

`test_container.py` extension (8 new tests):
- `TestOdooTestContainerNewParams` — default None for addons_path/cache_dir, default True for snapshot, snapshot=False, single/list addons_path, custom cache_dir

## Verification Results

```
uv run pytest packages/godoo-testcontainers/tests/ -m "not integration" -q
51 passed in <1s

uv run mypy --strict packages/godoo-testcontainers/src
Success: no issues found in 4 source files

uv run ruff check packages/godoo-testcontainers/
All checks passed!
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff E402: module docstring after from __future__ import**
- **Found during:** Task 1 (ruff check)
- **Issue:** Module-level docstring placed after `from __future__ import annotations` triggers E402 (module level import not at top of file) for all subsequent imports
- **Fix:** Removed module docstring from snapshot.py; docstring content preserved as inline comments on the constants they describe
- **Files modified:** `snapshot.py`
- **Commit:** 5af5d30 (ruff fix included in Task 2 commit)

**2. [Rule 1 - Bug] Ruff TC003: `Path` import at module level in container.py**
- **Found during:** Task 2 (ruff check)
- **Issue:** `from pathlib import Path` at module level in container.py triggers TC003 because `Path` is only used in type annotations (deferred to strings by `from __future__ import annotations`)
- **Fix:** Moved `from pathlib import Path` into `if TYPE_CHECKING:` block
- **Files modified:** `container.py`
- **Commit:** 5af5d30

**3. [Rule 1 - Bug] Ruff TC002: `pytest` import at module level in test_snapshot.py**
- **Found during:** Task 3 (ruff check)
- **Issue:** `import pytest` at module level triggers TC002 because `pytest.MonkeyPatch` is only used in type annotations
- **Fix:** Moved `import pytest` into `if TYPE_CHECKING:` block
- **Files modified:** `test_snapshot.py`
- **Commit:** 1b2c383

**4. [Rule 1 - Bug] Ruff SIM108: if/else block where ternary is preferred**
- **Found during:** Task 1 (ruff check)
- **Issue:** `make_snapshot_config` used an if/else block to set `enabled`
- **Fix:** Replaced with `enabled = (False if ... else snapshot_enabled)` ternary
- **Files modified:** `snapshot.py`
- **Commit:** 5af5d30

## Known Stubs

None — all exported functions are fully implemented. `properties={}` passed to `make_snapshot_config` in `container.py` is intentional: the harness (plan 03-03) supplies the real properties dict; `OdooTestContainer` itself does not know the harness-level properties, so the snapshot key computed here is a partial key that plan 03-03's `TestHarness` will override by computing its own `SnapshotConfig` with the real properties dict.

## Self-Check: PASSED

- [x] `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py` — FOUND
- [x] `packages/godoo-testcontainers/tests/test_snapshot.py` — FOUND
- [x] Commit 26014b1 — FOUND (feat: implement snapshot.py)
- [x] Commit 5af5d30 — FOUND (feat: wire snapshot cache + addons mount)
- [x] Commit 1b2c383 — FOUND (test: add snapshot unit tests)
- [x] `uv run mypy --strict packages/godoo-testcontainers/src` exits 0
- [x] `uv run ruff check packages/godoo-testcontainers/` exits 0
- [x] 51 non-integration tests pass
