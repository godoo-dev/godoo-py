# Phase 3: Testcontainers Parity — Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 13 (7 new source files, 4 new test files, 1 modified source, 1 modified __init__)
**Analogs found:** 12 / 13 (1 mechanical — py.typed, no analog needed)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py` | utility | batch + file-I/O | `seed_resolver.py` (dataclass + pure functions) | role-match |
| `packages/godoo-testcontainers/src/godoo_testcontainers/properties.py` | service | request-response | `services/properties/service.py` (class wrapping execute_kw) | exact |
| `packages/godoo-testcontainers/src/godoo_testcontainers/harness.py` | provider | request-response | `container.py` `OdooTestContainer` + `StartedOdooContainer` | exact |
| `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` | provider | batch | self (extend, do not rewrite) | exact |
| `packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py` | config | — | self (extend barrel exports) | exact |
| `packages/godoo-testcontainers/src/godoo_testcontainers/py.typed` | config | — | `packages/godoo/src/godoo/py.typed` | exact |
| `packages/godoo-testcontainers/tests/test_snapshot.py` | test | batch | `tests/test_seed_resolver.py` | exact |
| `packages/godoo-testcontainers/tests/test_properties.py` | test | request-response | `tests/test_seed_resolver.py` + `test_container.py` | role-match |
| `packages/godoo-testcontainers/tests/test_harness.py` | test | request-response | `tests/test_container.py` | role-match |
| `packages/godoo-testcontainers/tests/test_container.py` | test | — | self (extend) | exact |
| `.planning/REQUIREMENTS.md` | config | — | self (charter amendment) | exact |
| `.planning/ROADMAP.md` | config | — | self (charter amendment) | exact |
| `.planning/PROJECT.md` | config | — | self (charter amendment) | exact |

---

## Pattern Assignments

### `snapshot.py` (new — utility, file-I/O + batch)

**Analog:** `packages/godoo-testcontainers/src/godoo_testcontainers/seed_resolver.py`

This file owns: `SnapshotConfig` dataclass, `compute_snapshot_key()`, `_hash_addons_path()`, `has_snapshot()`, `save_snapshot()`, `restore_snapshot()`. It follows the same pure-functions-in-a-module pattern as `seed_resolver.py` but also uses `asyncio.to_thread` wrapping (from `container.py`).

**Imports pattern** — mirror `seed_resolver.py` lines 1–9, add async stdlib:

```python
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
```

**Dataclass pattern** — copy `SeedInfo` shape from `seed_resolver.py` lines 10–13:

```python
@dataclass
class SeedInfo:
    seed_image: str
    seed_modules: list[str]
```

New equivalent for snapshot:

```python
SNAPSHOT_SCHEMA_VERSION = 1
CACHE_CONTAINER_DIR = "/snapshot-cache"

@dataclass
class SnapshotConfig:
    enabled: bool
    key: str       # 16-char hex prefix of sha256
    cache_dir: Path

    @property
    def host_path(self) -> Path:
        return self.cache_dir / f"{self.key}.dump"

    @property
    def container_path(self) -> str:
        return f"{CACHE_CONTAINER_DIR}/{self.key}.dump"
```

**asyncio.to_thread wrapping pattern** — copy from `container.py` lines 38–41, 65, 77, 91:

```python
# All sync testcontainers/subprocess calls MUST use this pattern:
await asyncio.to_thread(pg.start)
await asyncio.to_thread(wait_for_logs, pg, "ready", 90)
await asyncio.to_thread(network.remove)

# New surfaces in snapshot.py follow the same idiom:
result = await asyncio.to_thread(pg.exec, ["pg_dump", "-U", pg_user, "-d", database, "-Fc", "-f", container_path])
```

**ExecResult error check pattern** — new, no codebase precedent; use this shape:

```python
result = await asyncio.to_thread(pg.exec, [...])
if result.exit_code != 0:
    raise RuntimeError(f"pg_dump failed: {result.output.decode(errors='replace')}")
```

**Atomic save pattern** — no codebase precedent; standard Python idiom confirmed in RESEARCH.md:

```python
# Temp file in same dir as final file (atomic guarantee requires same filesystem)
suffix = f".{os.getpid()}.{int(time.monotonic_ns() // 1_000_000)}.{secrets.token_hex(4)}.tmp"
tmp_host = cfg.host_path.with_suffix(cfg.host_path.suffix + suffix)
# ... pg_dump to tmp ...
# best-effort cleanup on failure:
with contextlib.suppress(Exception):
    tmp_host.unlink(missing_ok=True)
# atomic rename:
os.replace(tmp_host, cfg.host_path)
```

**Seed-image interaction guard** — insert at top of `OdooTestContainer.start()` (in `container.py`), just after `resolve_seed_info(...)`:

```python
# From RESEARCH.md Open Question 4: snapshot disabled when seed_info is resolved.
# The seed image is already a fast path; snapshot applies to cold postgres:15-alpine only.
snapshot_enabled = self._snapshot_enabled and (seed_info is None)
```

---

### `properties.py` (new — service/helper, request-response)

**Analog:** `packages/godoo/src/godoo/services/properties/service.py` (lines 1–43) + `functions.py` (lines 1–43)

This file is a testcontainers-internal helper, NOT a godoo core service quad. It is a single-file class (no `functions.py`/`types.py` split needed because it is internal and has two methods only).

**Imports pattern** — copy `PropertiesService` header exactly (lines 1–14 of `service.py`):

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from godoo.client import OdooClient
```

Note: `TYPE_CHECKING` guard on `OdooClient` is **mandatory** per project convention (prevents circular imports). Copy this verbatim from every service file.

**Class + constructor pattern** — copy `PropertiesService.__init__` (service.py lines 17–20):

```python
class ConfigParameterHelper:
    """Test-only helper for setting ir.config_parameter key/value pairs."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client
```

**Local validation before RPC pattern** — copy from `timesheets/functions.py` lines 95–97 (raises `OdooValidationError` before making any RPC call):

```python
# From packages/godoo/src/godoo/services/timesheets/functions.py:97
if hours <= 0:
    raise OdooValidationError("Hours must be positive")

# New equivalent in properties.py:
if not key:
    from godoo.errors import OdooValidationError
    raise OdooValidationError("ir.config_parameter key must not be empty")
```

**execute_kw call pattern** — from `client.py` lines 306–317:

```python
# client.execute_kw signature:
async def execute_kw(
    self,
    model: str,
    method: str,
    args: list[Any],
    kwargs: dict[str, Any] | None = None,
) -> Any: ...

# Call site in properties.py:
await self._client.execute_kw("ir.config_parameter", "set_param", [key, value])
```

**set_many pattern** — copy `update_safely_batch` structure from `functions.py` lines 45–53, but sequential (not `asyncio.gather`):

```python
async def set_many(self, values: Mapping[str, str]) -> None:
    """Set multiple ir.config_parameter pairs. Sequential — set_param is not batch-safe."""
    for k, v in values.items():
        await self.set(k, v)
```

---

### `harness.py` (new — provider, request-response)

**Analog:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` (entire file, especially lines 23–166)

`TestHarness` is a thin async-cm wrapper that composes `OdooTestContainer`. It mirrors the `OdooTestContainer`/`StartedOdooContainer` split: the harness holds config in `__init__`, does all work in `__aenter__`, and delegates cleanup to `StartedOdooContainer.cleanup()`.

**Imports pattern** — extend `container.py` lines 1–20:

```python
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from godoo_testcontainers.container import OdooTestContainer, StartedOdooContainer
from godoo_testcontainers.properties import ConfigParameterHelper

if TYPE_CHECKING:
    from godoo import OdooClient
    from godoo.services.modules import ModuleManager
```

**Constructor pattern** — copy `OdooTestContainer.__init__` (container.py lines 45–58), extend with new params:

```python
class TestHarness:
    def __init__(
        self,
        *,
        modules: list[str] | None = None,
        properties: dict[str, str] | None = None,   # ir.config_parameter k/v
        addons_path: Path | list[Path] | None = None,
        snapshot: bool = True,
        cache_dir: Path | None = None,
        database: str = "test_odoo",
        admin_password: str = "admin",
        startup_timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> None:
        self._modules = modules if modules is not None else []
        self._properties = properties if properties is not None else {}
        # ... etc, same None-guard idiom as container.py line 54–58
        self._started: StartedOdooContainer | None = None
```

**async context manager pattern** — mirrors Phase 1 D-14; no direct codebase precedent (OdooClient does NOT have `__aenter__`/`__aexit__`), but the shape is:

```python
async def __aenter__(self) -> TestHarness:
    container = OdooTestContainer(
        modules=self._modules,
        addons_path=self._addons_path,
        snapshot=self._snapshot,
        cache_dir=self._cache_dir,
        database=self._database,
        admin_password=self._admin_password,
        startup_timeout=self._startup_timeout,
        env=self._env,
    )
    self._started = await container.start()
    # Apply properties AFTER container starts and modules are installed
    if self._properties:
        await self.properties.set_many(self._properties)
    return self

async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: object,
) -> None:
    if self._started is not None:
        await self._started.cleanup()
```

**Property accessors pattern** — copy `StartedOdooContainer` field shape (container.py lines 23–31):

```python
@property
def client(self) -> OdooClient:
    assert self._started is not None, "TestHarness not started — use 'async with TestHarness(...) as h:'"
    return self._started.client

@property
def url(self) -> str:
    assert self._started is not None
    return self._started.url

@property
def modules(self) -> ModuleManager:
    assert self._started is not None
    return self._started.module_manager

@property
def properties(self) -> ConfigParameterHelper:
    assert self._started is not None
    return ConfigParameterHelper(self._started.client)
```

---

### `container.py` (modify — extend, do NOT rewrite)

**Analog:** self (lines 44–166 — add new constructor params and wire into `start()`)

**New constructor params** — extend `__init__` signature (lines 44–58) with:

```python
addons_path: Path | list[Path] | None = None,
snapshot: bool = True,
cache_dir: Path | None = None,
```

Store as `self._addons_path`, `self._snapshot_enabled`, `self._cache_dir`.

**Addons wiring** — inside `start()`, after building `cmd_parts` (line 95) and before `DockerContainer(f"odoo:{odoo_ver}")` (line 99), insert:

```python
# TESTC-02: addons mount
from godoo_testcontainers.snapshot import _build_addons_cmd  # or inline helper
mounts, addon_targets = _build_addons_cmd(self._addons_path)
for host_src, container_target, mode in mounts:
    odoo = odoo.with_volume_mapping(host_src, container_target, mode)
if addon_targets:
    core_path = "/usr/lib/python3/dist-packages/odoo/addons"
    cmd_parts.extend(["--addons-path", ",".join([core_path, *addon_targets])])
```

**Snapshot wiring** — insert between postgres start (line 92) and odoo start (line 112):

```python
# TESTC-01: snapshot restore (if hit)
seed_info = resolve_seed_info(...)
snapshot_enabled = self._snapshot_enabled and (seed_info is None)
if snapshot_enabled:
    cfg = compute_snapshot_config(...)
    Path(str(cfg.cache_dir)).mkdir(parents=True, exist_ok=True)
    # bind-mount cache dir into postgres container (must be done BEFORE pg.start())
    # ... see snapshot.py for restore_snapshot() call ...
    if cfg.host_path.exists():
        await restore_snapshot(pg, cfg, ...)
        # skip --init base (snapshot already has base installed)
    else:
        # cold path — save after module install completes
```

**asyncio.to_thread pattern** — same as existing lines 38–41, 65, 77, 91 throughout `start()`. Every new sync call added here follows the exact same idiom.

---

### `__init__.py` (modify — extend barrel exports)

**Analog:** self (lines 1–10)

**Current pattern** (lines 1–10):

```python
from godoo_testcontainers.container import OdooTestContainer, StartedOdooContainer
from godoo_testcontainers.seed_resolver import SeedInfo, normalise_odoo_version, resolve_seed_info

__all__ = [
    "OdooTestContainer",
    "SeedInfo",
    "StartedOdooContainer",
    "normalise_odoo_version",
    "resolve_seed_info",
]
```

**Extension pattern** — add `TestHarness` and `SnapshotConfig` to the barrel:

```python
from godoo_testcontainers.harness import TestHarness
from godoo_testcontainers.snapshot import SnapshotConfig

# Add to __all__:
"TestHarness",
"SnapshotConfig",
```

Note: `ConfigParameterHelper` is testcontainers-internal; do NOT export it from the package root unless a consumer asks.

---

### `py.typed` (new — empty marker file)

**Analog:** `packages/godoo/src/godoo/py.typed` (confirmed to exist)
Also: `packages/godoo-introspection/src/godoo_introspection/py.typed` (confirmed to exist)

**Pattern:** empty file. No content. Place at:
`packages/godoo-testcontainers/src/godoo_testcontainers/py.typed`

**pyproject.toml:** already declares `"Typing :: Typed"` classifier and `packages = ["src/godoo_testcontainers"]` — hatchling automatically includes `py.typed` when it sits in the package directory. No pyproject.toml change required (same as `godoo` package — `godoo/pyproject.toml` line 27 is the only wheel target declaration needed).

---

### `tests/test_snapshot.py` (new — unit test, pure functions)

**Analog:** `packages/godoo-testcontainers/tests/test_seed_resolver.py` (lines 1–169)

**Imports + class structure pattern** — copy lines 1–11:

```python
from __future__ import annotations

from pathlib import Path

from godoo_testcontainers.snapshot import (
    SnapshotConfig,
    compute_snapshot_key,
    _hash_addons_path,
)
```

**Test class pattern** — copy `TestNormaliseOdooVersion` / `TestResolveSeedInfo` naming convention:

```python
class TestComputeSnapshotKey:
    def test_identical_inputs_same_key(self) -> None: ...
    def test_different_modules_different_key(self) -> None: ...
    def test_modules_sorted_order_independent(self) -> None: ...
    def test_properties_included_in_key(self) -> None: ...
    def test_key_is_16_hex_chars(self) -> None: ...

class TestSnapshotEnablement:
    def test_disabled_by_env(self, monkeypatch: pytest.MonkeyPatch) -> None: ...
    def test_enabled_by_default(self) -> None: ...

class TestHashAddonsPath:
    def test_none_returns_empty(self) -> None: ...
    def test_single_path(self, tmp_path: Path) -> None: ...
    def test_file_change_changes_hash(self, tmp_path: Path) -> None: ...
```

**monkeypatch env var pattern** — copy `test_seed_resolver.py` lines 151–155:

```python
def test_reads_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODOO_TESTCONTAINERS_SNAPSHOT", "disabled")
    ...
```

**tmp_path fixture pattern** — copy `test_seed_resolver.py` lines 40–45:

```python
def test_found_in_docker_subdir(self, tmp_path: Path) -> None:
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    ...
```

---

### `tests/test_properties.py` (new — unit test, mock-based)

**Analog:** `packages/godoo-testcontainers/tests/test_container.py` (lines 1–39) for test class structure; mock pattern has no direct codebase precedent (use `unittest.mock.AsyncMock`).

**Imports pattern:**

```python
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from godoo_testcontainers.properties import ConfigParameterHelper
```

**AsyncMock pattern** — no codebase precedent; standard pytest-asyncio + unittest.mock:

```python
class TestConfigParameterHelper:
    def _make_client(self) -> MagicMock:
        client = MagicMock()
        client.execute_kw = AsyncMock(return_value=True)
        return client

    async def test_set_calls_execute_kw(self) -> None:
        client = self._make_client()
        helper = ConfigParameterHelper(client)
        await helper.set("mail.catchall.domain", "example.com")
        client.execute_kw.assert_called_once_with(
            "ir.config_parameter", "set_param", ["mail.catchall.domain", "example.com"]
        )

    async def test_set_empty_key_raises(self) -> None:
        helper = ConfigParameterHelper(self._make_client())
        with pytest.raises(Exception):   # OdooValidationError
            await helper.set("", "value")

    async def test_set_many_calls_set_per_key(self) -> None:
        client = self._make_client()
        helper = ConfigParameterHelper(client)
        await helper.set_many({"a": "1", "b": "2"})
        assert client.execute_kw.call_count == 2
```

---

### `tests/test_harness.py` (new — unit test, mock-based lifecycle)

**Analog:** `packages/godoo-testcontainers/tests/test_container.py` (lines 1–39)

**Pattern:** test `__init__` param storage (copy `TestOdooTestContainerDefaults` exactly), plus mock-based async-cm lifecycle tests.

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from godoo_testcontainers.harness import TestHarness


class TestTestHarnessDefaults:
    def test_default_options(self) -> None:
        h = TestHarness()
        assert h._modules == []
        assert h._properties == {}
        assert h._snapshot is True
        assert h._database == "test_odoo"
        assert h._admin_password == "admin"

    def test_custom_modules(self) -> None:
        h = TestHarness(modules=["crm"])
        assert h._modules == ["crm"]

    def test_addons_path_single(self, tmp_path: Path) -> None:
        h = TestHarness(addons_path=tmp_path)
        assert h._addons_path == tmp_path

    def test_addons_path_list(self, tmp_path: Path) -> None:
        paths = [tmp_path / "a", tmp_path / "b"]
        h = TestHarness(addons_path=paths)
        assert h._addons_path == paths
```

---

### `tests/test_container.py` (modify — extend existing)

**Analog:** self (lines 1–39)

Extend with new constructor param tests following the existing `TestOdooTestContainerDefaults` class pattern:

```python
class TestOdooTestContainerNewParams:
    def test_addons_path_default_none(self) -> None:
        c = OdooTestContainer()
        assert c._addons_path is None

    def test_snapshot_default_true(self) -> None:
        c = OdooTestContainer()
        assert c._snapshot_enabled is True

    def test_snapshot_false(self) -> None:
        c = OdooTestContainer(snapshot=False)
        assert c._snapshot_enabled is False

    def test_addons_path_single_path(self, tmp_path: Path) -> None:
        c = OdooTestContainer(addons_path=tmp_path)
        assert c._addons_path == tmp_path
```

---

### Charter amendment files (`.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/PROJECT.md`)

No code patterns apply. These are plain markdown edits per CONTEXT.md `D-Drop-1` and `D-Snap-3-amendment`. The planner should treat them as prose edits, not code generation tasks.

---

## Shared Patterns

### 1. `from __future__ import annotations` — every file

**Source:** all existing `.py` files — `container.py` line 1, `seed_resolver.py` line 1, every service file.
**Apply to:** all new `.py` files: `snapshot.py`, `properties.py`, `harness.py`, all test files.

```python
from __future__ import annotations
```

### 2. TYPE_CHECKING guard for OdooClient

**Source:** `packages/godoo/src/godoo/services/properties/service.py` lines 4–9; `module_manager.py` lines 8–10.
**Apply to:** `properties.py`, `harness.py` (anywhere `OdooClient` is used as a type annotation but not at runtime).

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from godoo.client import OdooClient
```

### 3. asyncio.to_thread wrapping for all sync testcontainers calls

**Source:** `container.py` lines 38–41 (`c.stop`), line 65 (`network.create`), line 77 (`pg.start`), line 78 (`wait_for_logs`), line 91 (`pg.start`), line 112 (`odoo.start`), line 165 (`network.remove`).
**Apply to:** all new sync calls in `snapshot.py` (`pg.exec` for pg_dump/restore) and any new `container.py` sync calls (bind-mount volume setup is declarative — no wrapping needed there; `.exec()` calls need wrapping).

```python
# Pattern (copy from container.py line 77):
await asyncio.to_thread(pg.start)

# New surfaces:
result = await asyncio.to_thread(pg.exec, ["pg_dump", "-U", pg_user, ...])
```

### 4. OdooValidationError for local precondition failures

**Source:** `packages/godoo/src/godoo/services/timesheets/functions.py` lines 95–97; `attendance/functions.py` lines 31–34.
**Apply to:** `properties.py` `ConfigParameterHelper.set()` (empty key guard).

```python
# Pattern (from timesheets/functions.py):
from godoo.errors import OdooValidationError
if hours <= 0:
    raise OdooValidationError("Hours must be positive")

# New surface (properties.py):
if not key:
    from godoo.errors import OdooValidationError
    raise OdooValidationError("ir.config_parameter key must not be empty")
```

### 5. contextlib.suppress for best-effort cleanup

**Source:** `container.py` lines 36–38 and lines 163–165.
**Apply to:** `snapshot.py` temp-file cleanup in `save_snapshot()` exception handler.

```python
# Pattern (from container.py lines 36–38):
with contextlib.suppress(Exception):
    await asyncio.to_thread(c.stop)

# New surface (snapshot.py):
with contextlib.suppress(Exception):
    tmp_host.unlink(missing_ok=True)
```

### 6. logger = logging.getLogger per module

**Source:** `container.py` line 20; `module_manager.py` line 12.
**Apply to:** `snapshot.py`, `properties.py` (if logging is needed), `harness.py`.

```python
# container.py line 20:
logger = logging.getLogger("godoo.testcontainers")

# New modules:
logger = logging.getLogger("godoo.testcontainers.snapshot")
logger = logging.getLogger("godoo.testcontainers.harness")
```

### 7. Dataclass for configuration objects

**Source:** `seed_resolver.py` lines 10–13 (`SeedInfo`); `container.py` lines 23–31 (`StartedOdooContainer`).
**Apply to:** `SnapshotConfig` dataclass in `snapshot.py`. No Pydantic.

```python
# Pattern (seed_resolver.py lines 10–13):
@dataclass
class SeedInfo:
    seed_image: str
    seed_modules: list[str]
```

### 8. Barrel __init__.py with explicit __all__

**Source:** `__init__.py` lines 1–10 (current); `packages/godoo/src/godoo/services/properties/__init__.py` lines 1–13.
**Apply to:** `__init__.py` extension (add `TestHarness`, `SnapshotConfig`).

```python
# Pattern (current __init__.py lines 4–10):
__all__ = [
    "OdooTestContainer",
    "SeedInfo",
    "StartedOdooContainer",
    "normalise_odoo_version",
    "resolve_seed_info",
]
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `snapshot.py` save/restore functions | utility | file-I/O async | pg_dump/restore via `container.exec` is new territory; no Python codebase precedent — RESEARCH.md provides the exact protocol (Open Question 1 patterns) |
| `py.typed` | config | — | Mechanical empty file — no code pattern needed; precedent confirmed at `packages/godoo/src/godoo/py.typed` and `packages/godoo-introspection/src/godoo_introspection/py.typed` |

---

## Key Observations for Planner

1. **`container.py` is the extension anchor.** Every new capability (addons mount, snapshot cache) wires into `OdooTestContainer.start()` at specific points in the existing flow. The planner must map each insertion point precisely: bind-mounts go on the `pg` container builder (before `pg.start()`); snapshot restore goes after `pg.start()` and before `odoo.start()`; snapshot save goes after the module install loop.

2. **`TestHarness` is thin by design.** It holds config in `__init__`, delegates entirely to `OdooTestContainer.start()` in `__aenter__`, and calls `StartedOdooContainer.cleanup()` in `__aexit__`. The only logic it adds is applying `properties` via `ConfigParameterHelper.set_many()` post-start.

3. **`properties.py` is a single-file helper, not a module quad.** It is testcontainers-internal. The `services/properties/` quad in the godoo core package is a different thing (it handles `project.task_properties_definition` fields, not `ir.config_parameter`). The naming similarity is coincidental; do not confuse them.

4. **`snapshot.py` `_build_addons_cmd` helper** may also live in `container.py` if the planner prefers — the function is small and only called from `container.py`. Either location is acceptable; put it where it minimises imports.

5. **No new runtime packages.** All stdlib and testcontainers APIs are confirmed available. No `pyproject.toml` dependency changes are needed.

6. **`py.typed` does not require a `pyproject.toml` change** for `godoo-testcontainers` because `[tool.hatch.build.targets.wheel] packages = ["src/godoo_testcontainers"]` already causes hatchling to include all files under that directory.

---

## Metadata

**Analog search scope:** `packages/godoo-testcontainers/src/`, `packages/godoo-testcontainers/tests/`, `packages/godoo/src/godoo/services/`
**Files read:** `container.py`, `seed_resolver.py`, `__init__.py`, `services/properties/functions.py`, `services/properties/service.py`, `services/properties/__init__.py`, `services/modules/module_manager.py`, `tests/test_container.py`, `tests/test_seed_resolver.py`, `packages/godoo/pyproject.toml`, `packages/godoo-testcontainers/pyproject.toml`
**Pattern extraction date:** 2026-05-22
