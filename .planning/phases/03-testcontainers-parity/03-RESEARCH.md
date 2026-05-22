# Phase 3: Testcontainers Parity — Research

**Researched:** 2026-05-22
**Domain:** Python testcontainers, Docker container lifecycle, pg_dump/restore, Odoo addons, ir.config_parameter JSON-RPC
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-Drop-1:** TESTC-03, TESTC-04, TESTC-05 hard-dropped. Charter amendment tasks are in-scope within this phase.
- **D-Snap-1:** Snapshot key = sha256(stable_json(...))[:16 hex chars]. Inputs: schema_version, odoo_version, postgres_image, modules (sorted/deduped), addons (content-tree hash), database, admin_password, env (sorted), **properties** (sorted ir.config_parameter k/v), user_key.
- **D-Snap-2:** Snapshot enabled by default. Disable via env `ODOO_TESTCONTAINERS_SNAPSHOT=disabled` or `snapshot=False`. Override cache dir via `ODOO_TESTCONTAINERS_SNAPSHOT_DIR` or `cache_dir=Path(...)`.
- **D-Snap-3:** Default cache dir is `cwd/.odoo-testcontainers/snapshots/` (NOT `~/.odoo-testcontainers/snapshots/`).
- **D-Scope-1:** Testcontainers does container lifecycle + module install + `ir.config_parameter` only. Richer seeding belongs to godoo-stateman.
- **D-Props-1:** Properties provisioner sets `ir.config_parameter` k/v only. NOT `project.task_properties_definition`.
- **D-Props-2:** Public API: `h.properties.set(key, value)` and `h.properties.set_many({...})`.
- **D-Harness-1:** `TestHarness` is a thin wrapper with `__aenter__`/`__aexit__`. API shape locked (see CONTEXT.md). Existing `OdooTestContainer.start()` and `StartedOdooContainer.cleanup()` stay callable.
- **D-Addons-1:** `addons_path: Path | list[Path] | None`. Single `Path` → `/mnt/extra-addons`. `list[Path]` → `/mnt/addons-0`, `/mnt/addons-1`, ... (TS-faithful indexing). Full `AddonsMount` dataclass deferred.
- **D-Addons-2:** Mounting a directory does NOT auto-install modules inside it. Orthogonal from `modules=`.

### Claude's Discretion (Planner)

- ConfigParameterService location: default to testcontainers-internal `properties.py` helper (not a new godoo core service).
- `asyncio.to_thread` boundaries for all new sync calls.
- Concurrency rule for snapshot writes: temp + atomic rename + skip-if-exists.
- pytest fixture pattern in docs.
- Snapshot vs seed-image interaction: snapshot applies on non-seed path; seed image IS its own fast path (snapshot caching disabled when seed_info is resolved).
- `schema_version` constant starts at 1.
- `TestHarness` implementation shape: wrapping class or async-cm on StartedOdooContainer — either valid.
- `ir.config_parameter` write: prefer `execute_kw('ir.config_parameter', 'set_param', [key, value])`.
- Odoo `--addons-path` CLI arg plumbing: confirmed below.

### Deferred Ideas (OUT OF SCOPE)

- `harness.apply_stateman(config_path)` hook
- Partner / project / user / task-property provisioners
- Full `AddonsMount` dataclass union (per-mount target/mode customisation)
- Convenience overloads on `properties.set` (int/bool/float coercion)
- General-purpose `ConfigParameterService` on godoo core client
- `get_param` / `delete_param` on properties helper
- Snapshot save/restore via host-side pg_dump
- Multi-version Odoo snapshot sharing
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TESTC-01 | Local snapshot cache (pg_dump/restore keyed by content hash, cwd/.odoo-testcontainers/snapshots/) | Open questions 1, 4, 5 resolved — see Snapshot Mechanics section |
| TESTC-02 | Custom addons mount via addons_path | Open question 2 resolved — see Addons Mount section |
| TESTC-06 | Properties provisioner: ir.config_parameter k/v set_param | Open question 3 resolved — see Properties section |
| TESTC-07 | TestHarness: thin async-cm wrapper composing above + ready OdooClient | All integration points verified — see TestHarness section |
| TESTC-08 | py.typed PEP 561 marker in godoo-testcontainers | Mechanical — same pattern as CLIENT-10, INTRO-07 |
</phase_requirements>

---

## Summary

Phase 3 adds five capabilities on top of the existing `OdooTestContainer`: a pg_dump-based snapshot cache (TESTC-01), a custom addons mount (TESTC-02), an `ir.config_parameter` properties provisioner (TESTC-06), a `TestHarness` async-cm (TESTC-07), and the `py.typed` marker (TESTC-08). The dropped provisioners (TESTC-03/04/05) are documented only as charter amendments.

All five open questions from the brief are resolved with HIGH confidence: the Python `testcontainers` `DockerContainer.exec(cmd)` API surface is confirmed, the Odoo addons-path plumbing is clarified (env var does NOT work in official image — CLI arg required), `ir.config_parameter.set_param` is confirmed available via JSON-RPC, the seed-image/snapshot interaction rule is codified, and the Python atomic-rename pattern mirrors the TS protocol exactly.

No new runtime packages are needed — all dependencies are already in the workspace. The snapshot save/restore runs entirely inside the Postgres container, so no host-side pg_dump is required.

**Primary recommendation:** Implement in three waves: Wave 0 (charter amendments + py.typed), Wave 1 (snapshot cache + addons mount wired into container.py), Wave 2 (properties helper + TestHarness async-cm).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Snapshot cache key computation | Test Infrastructure | — | Pure hash of provisioning inputs; belongs in the testcontainers layer, not the client |
| pg_dump / pg_restore execution | Test Infrastructure | Docker (exec inside container) | Runs inside the Postgres container via exec(); testcontainers layer orchestrates |
| Bind-mount of cache dir | Test Infrastructure | Docker | Volume config at container build time; testcontainers layer owns this |
| Odoo `--addons-path` plumbing | Test Infrastructure | Odoo container config | CLI arg injected by OdooTestContainer.start(); Docker/Odoo handles discovery |
| `ir.config_parameter` write | Test Infrastructure (properties helper) | OdooClient (transport) | Properties helper calls client.execute_kw; client layer owns JSON-RPC transport |
| TestHarness lifecycle | Test Infrastructure | OdooClient (auth) | Harness wraps OdooTestContainer.start() + StartedOdooContainer.cleanup(); no new client surface |
| py.typed marker | Test Infrastructure (package metadata) | — | Empty file at package root; pure packaging concern |

---

## Standard Stack

### Core (all already installed — no new packages)

| Library | Version (installed) | Purpose | Confirmed Via |
|---------|---------------------|---------|---------------|
| `testcontainers[postgres]` | 4.14.2 | Docker container orchestration; `DockerContainer.exec()`, `with_volume_mapping()` | `[VERIFIED: uv run python -c "from importlib.metadata import version; print(version('testcontainers'))"]` |
| `godoo` (workspace) | 0.x | OdooClient, execute_kw, ModuleManager | `[VERIFIED: codebase read]` |
| `httpx` | >=0.27 | Odoo readiness polling (already used in container.py) | `[VERIFIED: codebase read]` |
| `hashlib` (stdlib) | Python 3.14 | sha256 for snapshot key | `[VERIFIED: stdlib]` |
| `tempfile` (stdlib) | Python 3.14 | Temp file for atomic snapshot save | `[VERIFIED: stdlib]` |
| `os` (stdlib) | Python 3.14 | `os.replace()` atomic rename | `[VERIFIED: uv run python -c "import os; print(hasattr(os, 'replace'))"]` |
| `pathlib` (stdlib) | Python 3.14 | Path manipulation for cache dir, addons paths | `[VERIFIED: stdlib]` |
| `json` (stdlib) | Python 3.14 | Stable JSON for key computation | `[VERIFIED: stdlib]` |
| `secrets` (stdlib) | Python 3.14 | Random suffix for temp file name | `[VERIFIED: stdlib]` |

**Installation:** No new packages. All dependencies are already in the workspace lockfile.

### Package Legitimacy Audit

No new external packages are introduced by this phase. All packages used (testcontainers, godoo, httpx) are pre-existing workspace dependencies. No slopcheck needed.

---

## Resolved Open Questions

### Open Question 1: Snapshot Save/Restore Mechanics

**`DockerContainer.exec(cmd)` API surface** (testcontainers-python 4.14.2): [VERIFIED: live inspection]

```python
# Signature (sync — MUST be wrapped in asyncio.to_thread):
def exec(self, command: Union[str, list[str]]) -> ExecResult

# ExecResult is a namedtuple:
ExecResult(exit_code: int, output: bytes)
# Note: unlike TS (exitCode + stderr/stdout), Python gives a single bytes output
# and exit_code. Treat exit_code != 0 as failure; log output.decode() for debug.
```

**pg_dump (save) — runs inside the postgres container:** [VERIFIED: TS reference + API confirmation]

```python
result = await asyncio.to_thread(
    pg.exec,
    ['pg_dump', '-U', pg_user, '-d', database, '-Fc', '-f', container_path]
)
if result.exit_code != 0:
    raise RuntimeError(f"pg_dump failed: {result.output.decode()}")
```

**pg_restore (restore) — three-command sequence inside postgres container:** [VERIFIED: TS reference]

```python
# Step 1: drop existing database
r = await asyncio.to_thread(pg.exec, ['dropdb', '-U', pg_user, database])
if r.exit_code != 0:
    raise RuntimeError(f"dropdb failed: {r.output.decode()}")

# Step 2: recreate it
r = await asyncio.to_thread(pg.exec, ['createdb', '-U', pg_user, database])
if r.exit_code != 0:
    raise RuntimeError(f"createdb failed: {r.output.decode()}")

# Step 3: restore
r = await asyncio.to_thread(pg.exec, [
    'pg_restore', '-U', pg_user, '-d', database,
    '--no-owner', '--role', pg_user, container_path
])
if r.exit_code != 0:
    raise RuntimeError(f"pg_restore failed: {r.output.decode()}")
```

**Bind mount for cache dir:** [VERIFIED: testcontainers API inspection]

```python
# On the postgres container (both PostgresContainer and DockerContainer inherit this):
pg = (
    PostgresContainer(...)
    .with_network(network)
    .with_network_aliases("db")
    .with_volume_mapping(str(cache_dir_host), '/snapshot-cache', 'rw')  # rw needed for pg_dump write
)
```

The cache dir must be created on the host BEFORE `pg.start()` is called. Use:
```python
Path(cache_dir_host).mkdir(parents=True, exist_ok=True)
```

**CRITICAL: Restore must happen AFTER postgres starts but BEFORE Odoo starts.** [VERIFIED: TS reference + container.py flow analysis]

Current `container.py` flow:
1. `await asyncio.to_thread(pg.start)` — postgres up
2. `await asyncio.to_thread(odoo.start)` — Odoo started (with or without `--init base`)

New flow with snapshot:
1. `await asyncio.to_thread(pg.start)` — postgres up (cache dir bind-mounted)
2. **IF snapshot hit:** `await restore_snapshot(pg, ...)` — restore DB from dump
3. Odoo command: **no `--init base`** if snapshot hit; normal `--init base` if cold
4. `await asyncio.to_thread(odoo.start)` — Odoo starts against restored/fresh DB
5. Odoo ready, authenticate, modules
6. **IF snapshot miss AND snapshot enabled:** `await save_snapshot(pg, ...)` — save dump

**Seed image case:** When `seed_info` is resolved (`ODOO_SEED_IMAGE` env var), `pg` is a `DockerContainer(seed_info.seed_image)` not a `PostgresContainer`. The same `exec()` and `with_volume_mapping()` methods are available (both inherit from `DockerContainer`). However, the chosen rule (D-Snap-3 planner-discretion) is: **snapshot caching is DISABLED when seed_info is resolved**. The seed image is already a fast-start path; layering snapshot on top adds complexity with no clear benefit. Document this rule in code comments on `snapshot.py`.

---

### Open Question 2: Addons Mount and --addons-path Plumbing

**IMPORTANT FINDING:** The official Odoo Docker image (`odoo:17.0`, `odoo:18.0`, etc.) entrypoint.sh does NOT process an `ADDONS_PATH` environment variable. The TS reference code uses `withEnvironment({ ADDONS_PATH: allAddonsPaths })` but this env var has no effect in the official image. [VERIFIED: WebFetch of raw entrypoint.sh]

**What DOES work:**

The official Odoo Docker image (`odoo/docker` on GitHub) ships with `/etc/odoo/odoo.conf` containing:
```ini
addons_path = /mnt/extra-addons
```

This means `/mnt/extra-addons` is already a registered addons path by default. [VERIFIED: WebFetch of raw odoo.conf + Docker Hub documentation]

**Recommended approach for Python implementation:**

For any `addons_path` (single or list), always pass `--addons-path` as a CLI argument to Odoo. This is more explicit and consistent than relying on odoo.conf. The argument replaces (not appends to) the config file setting, so always include the core addons path. [VERIFIED: Odoo behavior + TS reference]

```python
# Build addons command fragment:
def _build_addons_cmd(addons_path: Path | list[Path] | None) -> tuple[
    list[tuple[str, str, str]],  # (host_src, container_target, mode) for with_volume_mapping
    list[str],                    # container target paths for --addons-path
]:
    if addons_path is None:
        return [], []
    paths = [addons_path] if isinstance(addons_path, Path) else list(addons_path)
    mounts = []
    targets = []
    for i, p in enumerate(paths):
        target = '/mnt/extra-addons' if len(paths) == 1 else f'/mnt/addons-{i}'
        mounts.append((str(p.resolve()), target, 'ro'))
        targets.append(target)
    return mounts, targets
```

Wire into Odoo container:
```python
# In OdooTestContainer.start():
mounts, addon_targets = _build_addons_cmd(self._addons_path)
for host_src, container_target, mode in mounts:
    odoo = odoo.with_volume_mapping(host_src, container_target, mode)

if addon_targets:
    # Core Odoo addons path + custom mounts (--addons-path replaces odoo.conf setting)
    all_addons = ['/usr/lib/python3/dist-packages/odoo/addons', *addon_targets]
    cmd_parts.extend(['--addons-path', ','.join(all_addons)])
```

**Note on `--addons-path` format:** The argument takes a comma-separated list of paths with no spaces. The command string joined with spaces (`" ".join(cmd_parts)`) is safe as long as addon paths contain no spaces — which is the expected case for CI/test environments. The existing `with_command(" ".join(cmd_parts))` pattern is preserved.

**Note on `/usr/lib/python3/dist-packages/odoo/addons`:** This is the standard path for Odoo core addons in the official Debian-based Docker image across versions 17, 18, and 19. [ASSUMED — derived from TS reference and Odoo Debian packaging convention; if wrong, Odoo will fail to find 'base' and emit a clear error.]

---

### Open Question 3: `ir.config_parameter.set_param` JSON-RPC Availability

**`set_param` is exposed via JSON-RPC in Odoo 17, 18, and 19 CE.** It is an `@api.model` method on `ir.config_parameter`, callable via `execute_kw`. [CITED: CONTEXT.md D-Props-2 confirmation + Odoo public API; [ASSUMED: versions 18/19 — same method, stable across versions]]

**Exact invocation via `OdooClient.execute_kw`:**

```python
# Source: packages/godoo/src/godoo/client.py execute_kw signature
# execute_kw(model, method, args, kwargs=None) → routes through client.call()

await client.execute_kw(
    'ir.config_parameter',
    'set_param',
    [key, value],   # positional args to set_param(key, value)
)
```

`set_param(key, value)` is upsert by design: if the key exists, it updates the value; if not, it creates a new record. This means the properties provisioner does not need to pre-check existence — it can call `set_param` unconditionally. [CITED: CONTEXT.md D-Props-2]

**`set_param` safety classification:** The client's `infer_safety_level("set_param")` will return a non-READ level (likely "WRITE"). Since `OdooTestContainer` creates an `OdooClient` with no safety context (`safety=None` in config), `_guard()` returns immediately — no `OdooSafetyError` will be raised in the testcontainers context. No special handling needed.

**Properties helper call pattern (`set_many`):**
```python
async def set_many(self, values: Mapping[str, str]) -> None:
    for key, value in values.items():
        await self._client.execute_kw('ir.config_parameter', 'set_param', [key, value])
```

The sequentialfor-loop is intentional: `set_param` is not designed for batch RPC; parallelizing with `asyncio.gather` would create concurrent sessions which testcontainers doesn't need.

---

### Open Question 4: Snapshot vs Seed-Image Interaction

**Rule (planner discretion resolved — matches D-Snap-3 planner-discretion note):**

When `resolve_seed_info()` returns a non-None `SeedInfo`, snapshot caching is **disabled** for that start. The seed image is the fast path; the snapshot cache applies only to the cold `postgres:15-alpine` path. This avoids complexity (the seed image DB may not be compatible with the snapshot's pg_dump format) and keeps the two fast paths independent.

```python
# At the start of OdooTestContainer.start():
seed_info = resolve_seed_info(self._modules, odoo_ver)
snapshot_enabled = self._snapshot_enabled and (seed_info is None)
```

Document in `snapshot.py` docstring:
> "Snapshot caching applies to the cold postgres:15-alpine path only. When a seed image is used (ODOO_SEED_IMAGE is set and covers all requested modules), the seed image acts as its own fast path and snapshot caching is skipped."

---

### Open Question 5: Concurrency on Snapshot Writes

**Python equivalent of the TS atomic-rename protocol:** [VERIFIED: live Python testing]

```python
# Source: mirrors TS snapshot-cache.ts saveSnapshot() protocol
import os, secrets, time
from pathlib import Path

CACHE_CONTAINER_DIR = '/snapshot-cache'

async def save_snapshot(
    pg: Any,
    host_path: Path,
    container_path: str,
    database: str,
    pg_user: str,
) -> None:
    """Save a pg_dump snapshot. Skips if file already exists (another worker saved first)."""
    if host_path.exists():
        return  # Another worker beat us — skip

    host_path.parent.mkdir(parents=True, exist_ok=True)

    # Unique temp suffix: pid.timestamp_ms.random_hex
    suffix = f'.{os.getpid()}.{int(time.monotonic_ns() // 1_000_000)}.{secrets.token_hex(4)}.tmp'
    tmp_host = host_path.with_suffix(host_path.suffix + suffix)
    tmp_container = container_path + suffix

    result = await asyncio.to_thread(
        pg.exec,
        ['pg_dump', '-U', pg_user, '-d', database, '-Fc', '-f', tmp_container]
    )
    if result.exit_code != 0:
        # Best-effort cleanup of temp file
        with contextlib.suppress(Exception):
            tmp_host.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump failed: {result.output.decode(errors='replace')}")

    # If another worker saved while we were dumping, discard our temp
    if host_path.exists():
        with contextlib.suppress(Exception):
            tmp_host.unlink(missing_ok=True)
        return

    # Atomic rename: os.replace is atomic on same-filesystem (POSIX and Windows)
    os.replace(tmp_host, host_path)
```

**Key points:**
- `os.replace()` is available on Python 3.14 and is atomic for same-directory renames on all platforms. [VERIFIED: live Python testing]
- `tmp_host` must be in the SAME directory as `host_path` for the atomic guarantee to hold.
- The temp file on the HOST corresponds to the temp path in the container because the cache dir is bind-mounted.
- `host_path.exists()` check at entry is a fast-path skip (no lock needed for this use case — two concurrent saves of the same content both produce valid dumps; last writer wins, but atomicity ensures no reader sees a partial file).

---

## Architecture Patterns

### System Architecture Diagram

```
                    TestHarness (async-cm)
                          │
            ┌─────────────▼─────────────┐
            │     OdooTestContainer      │
            │     start() method         │
            └──┬──────────┬─────────────┘
               │          │
    ┌──────────▼──┐  ┌────▼────────────────────┐
    │  Postgres   │  │  Snapshot Cache          │
    │  Container  │  │  snapshot.py             │
    │  (pg.exec)  │  │  - compute_key()         │
    └──────────┬──┘  │  - has_snapshot()        │
               │     │  - restore_snapshot()    │
               │     │  - save_snapshot()       │
               │     └──────────────────────────┘
    ┌──────────▼──────────────────────────────────┐
    │  Odoo Container                              │
    │  with_volume_mapping (addons mount)          │
    │  --addons-path in cmd_parts                  │
    └──────────────────────────────────────────────┘
               │
    ┌──────────▼──────────────────────────────────┐
    │  OdooClient (authenticated)                  │
    │  ModuleManager  │  Properties helper         │
    │  (existing)     │  properties.py             │
    │                 │  execute_kw(set_param)      │
    └─────────────────────────────────────────────┘
```

### Recommended Project Structure (new files only)

```
packages/godoo-testcontainers/src/godoo_testcontainers/
├── __init__.py             # add TestHarness + SnapshotCache to __all__
├── container.py            # EXTEND — add addons_path, snapshot_enabled, cache_dir params
├── seed_resolver.py        # unchanged
├── snapshot.py             # NEW — SnapshotConfig dataclass + compute_key, has_snapshot,
│                           #       restore_snapshot, save_snapshot
├── properties.py           # NEW — ConfigParameterHelper class (set, set_many)
└── harness.py              # NEW — TestHarness async-cm

packages/godoo-testcontainers/tests/
├── test_container.py       # EXTEND — test new constructor params
├── test_snapshot.py        # NEW — unit tests for key computation, enable/disable logic
├── test_properties.py      # NEW — mock-based test for set/set_many
└── test_harness.py         # NEW — mock-based test for TestHarness async-cm lifecycle
```

```
packages/godoo-testcontainers/src/godoo_testcontainers/py.typed   # NEW — empty marker file
```

### Pattern 1: SnapshotConfig Dataclass

```python
# Source: TS snapshot-cache.ts SnapshotCache interface, adapted to Python dataclasses
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

SNAPSHOT_SCHEMA_VERSION = 1
CACHE_CONTAINER_DIR = '/snapshot-cache'

@dataclass
class SnapshotConfig:
    enabled: bool
    key: str          # 16-char hex
    cache_dir: Path   # host-side directory
    file_name: str    # e.g. "abc123def456789a.dump"

    @property
    def host_path(self) -> Path:
        return self.cache_dir / self.file_name

    @property
    def container_path(self) -> str:
        return f'{CACHE_CONTAINER_DIR}/{self.file_name}'
```

### Pattern 2: Snapshot Key Computation

```python
# Source: TS computeSnapshotKey() — D-Snap-1
import hashlib, json

def compute_snapshot_key(
    *,
    odoo_version: str,
    postgres_image: str,
    modules: list[str],
    addons_path: Path | list[Path] | None,
    database: str,
    admin_password: str,
    env: dict[str, str],
    properties: dict[str, str],   # NEW vs TS — D-Snap-1 addition
    user_key: str = '',
) -> str:
    payload = {
        'schema': SNAPSHOT_SCHEMA_VERSION,
        'odooVersion': odoo_version,
        'postgresImage': postgres_image,
        'modules': sorted(set(modules)),
        'addons': _hash_addons_path(addons_path),
        'database': database,
        'adminPassword': admin_password,
        'env': dict(sorted(env.items())),
        'properties': dict(sorted(properties.items())),   # D-Snap-1 addition
        'userKey': user_key,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=False).encode()).hexdigest()
    return digest[:16]
```

**Addons tree hash** mirrors TS `hashPath()` / `listFiles()`:
```python
# Ignore: .git, node_modules, __pycache__, .pytest_cache  (TS-faithful)
# For each mount: {source: str(resolved), target: str, mode: str, tree: ...}
# tree for a directory: sorted list of {path: relative_path, digest: sha256_hex}
# tree for a file: {exists: True, type: 'file', digest: sha256_hex}
```

**Python vs TS difference:** `json.dumps` with `sort_keys=False` is used intentionally — the dict is pre-sorted, matching TS `JSON.stringify()` behaviour (which uses insertion order). This is not a correctness concern because the key inputs are always the same Python dict structure.

### Pattern 3: ConfigParameterHelper

```python
# Source: D-Props-2 from CONTEXT.md, execute_kw pattern from client.py
from __future__ import annotations
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from godoo.client import OdooClient


class ConfigParameterHelper:
    """Test-only helper for setting ir.config_parameter key/value pairs."""

    def __init__(self, client: OdooClient) -> None:
        self._client = client

    async def set(self, key: str, value: str) -> None:
        """Set a single ir.config_parameter. Upsert — safe to call multiple times."""
        if not key:
            from godoo.errors import OdooValidationError
            raise OdooValidationError("ir.config_parameter key must not be empty")
        await self._client.execute_kw('ir.config_parameter', 'set_param', [key, value])

    async def set_many(self, values: Mapping[str, str]) -> None:
        """Set multiple ir.config_parameter pairs. Iterates set_param per key."""
        for k, v in values.items():
            await self.set(k, v)
```

Note: This class lives in `packages/godoo-testcontainers/src/godoo_testcontainers/properties.py` — it is NOT a new service in the `godoo` core package. The `godoo.client` import is under `TYPE_CHECKING` to match codebase convention.

### Pattern 4: TestHarness Async-CM

```python
# Source: D-Harness-1 from CONTEXT.md, mirrors Phase 1 D-14 OdooClient async-cm pattern
class TestHarness:
    def __init__(
        self,
        *,
        modules: list[str] | None = None,
        properties: dict[str, str] | None = None,
        addons_path: Path | list[Path] | None = None,
        snapshot: bool = True,
        cache_dir: Path | None = None,
        database: str = 'test_odoo',
        admin_password: str = 'admin',
        startup_timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> None: ...

    async def __aenter__(self) -> TestHarness:
        # 1. Build OdooTestContainer with addons_path, snapshot config
        # 2. await container.start() → self._started
        # 3. Set self.client, self.url, self.modules (ModuleManager wrapper)
        # 4. Apply properties: await self.properties.set_many(self._properties)
        # 5. Return self
        ...

    async def __aexit__(self, ...) -> None:
        await self._started.cleanup()

    @property
    def client(self) -> OdooClient: ...
    @property
    def url(self) -> str: ...
    @property
    def modules(self) -> ModuleManager: ...
    @property
    def properties(self) -> ConfigParameterHelper: ...
```

**Note on properties timing:** Properties are applied in `__aenter__` AFTER the container starts and is authenticated. They are applied after module install (modules may add config parameters). Properties are included in the snapshot key (D-Snap-1), so a different `properties=` dict produces a different snapshot key — the snapshot captures the state BEFORE properties are applied (because properties are applied by the harness post-start, not baked into the snapshot). This is the correct design: the snapshot saves DB state after `--init base` + module install; properties are re-applied after each restore.

### Anti-Patterns to Avoid

- **Calling `pg.exec()` synchronously:** Every `pg.exec()` call must be wrapped in `await asyncio.to_thread(pg.exec, [...])`. The exec call runs Docker API synchronously and will block the event loop if called directly.
- **Calling `pg.exec()` before `pg.start()`:** `exec()` raises `ContainerStartException` if called before `start()`. The start sequence is `pg.start()` → `restore` (if hit) → `odoo.start()`.
- **Using ADDONS_PATH env var:** The official Odoo Docker image entrypoint does NOT process `ADDONS_PATH`. Use `--addons-path` in the Odoo command instead.
- **Omitting core addons path from `--addons-path`:** When `--addons-path` is passed as a CLI arg, it replaces the `addons_path = /mnt/extra-addons` in `odoo.conf`. The core Odoo addons path (`/usr/lib/python3/dist-packages/odoo/addons`) must be included explicitly or Odoo will fail to find `base`.
- **Placing tmp snapshot file outside cache dir:** The atomic rename (`os.replace`) is only atomic within the same filesystem/volume. Always create the temp file in the same directory as the final file.
- **Using `NamedTemporaryFile` with `delete=True` (default):** On Windows, a `NamedTemporaryFile` with `delete=True` cannot be opened by another process (Docker daemon) while still open. Use `delete=False` and manage cleanup manually, OR use `tempfile.mkstemp()` instead.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file rename | Custom locking or file swap protocol | `os.replace(tmp, final)` | Same-directory atomic on POSIX and Windows; proven in TS reference |
| Snapshot key hashing | Custom string join + MD5 | `hashlib.sha256(json.dumps(payload).encode()).hexdigest()[:16]` | Mirrors TS exactly; sha256 is collision-resistant |
| Directory tree hashing | `os.walk` with ad-hoc string concat | Walk + per-file sha256; collect `(relative_path, digest)` sorted pairs | TS-faithful; deterministic despite OS ordering |
| pg_dump/restore on host | Install pg tools on CI host | `pg.exec(['pg_dump', ...])` inside the Postgres container | Container always has pg tools; no host dependency |
| ir.config_parameter upsert logic | Search + write/create | `execute_kw('ir.config_parameter', 'set_param', [key, value])` | `set_param` is an upsert by design; no pre-check needed |

**Key insight:** Every complex operation in this phase has a single-function equivalent that handles all edge cases. The snapshot concurrency protocol is 5 lines of Python; the pg_dump/restore is 3 `exec` calls; the upsert is one `execute_kw` call.

---

## Common Pitfalls

### Pitfall 1: Sync testcontainers calls in async context (existing anti-pattern, new surfaces)

**What goes wrong:** `pg.exec(...)` is a sync method that calls Docker's Python SDK. Called directly in async code, it blocks the event loop and hangs the test.
**Why it happens:** `exec()` looks deceptively like it should be async (it's an I/O operation), but testcontainers-python has a 100% sync API.
**How to avoid:** `result = await asyncio.to_thread(pg.exec, ['pg_dump', ...])`
**Warning signs:** Tests hang during snapshot save/restore with no timeout error.

### Pitfall 2: Bind-mount path must exist before container starts

**What goes wrong:** `with_volume_mapping(host_dir, container_dir, 'rw')` does NOT create `host_dir` on the host. Docker silently creates it as root on Linux (resulting in a root-owned directory that the process can't write to) or fails on Windows.
**Why it happens:** Docker volume mapping semantics differ by OS.
**How to avoid:** Call `Path(cache_dir_host).mkdir(parents=True, exist_ok=True)` before calling `pg.start()` whenever snapshot is enabled.
**Warning signs:** `pg_dump` fails with "Permission denied" or "No such file or directory" on the container path.

### Pitfall 3: `--addons-path` replaces, not appends, the config file setting

**What goes wrong:** Custom addons are mounted but `modules=["base"]` install fails — Odoo can't find base.
**Why it happens:** Passing `--addons-path /mnt/extra-addons` overrides the `odoo.conf` `addons_path` entirely. The core addons at `/usr/lib/python3/dist-packages/odoo/addons` are no longer in the search path.
**How to avoid:** Always build the full `--addons-path` including the core Odoo addons directory.
**Warning signs:** Odoo startup log: "No module named 'base'" or "Module 'base' not found".

### Pitfall 4: Snapshot key not including `properties`

**What goes wrong:** Two runs with identical modules but different `properties=` dicts produce the same snapshot key. The second run restores the snapshot and skips re-applying properties — but the snapshot was saved without those properties, so they're missing.
**Why it happens:** D-Snap-1 explicitly adds `properties` to the key hash; forgetting it breaks idempotency.
**How to avoid:** Include `properties` in the `compute_snapshot_key()` payload as a sorted dict.
**Warning signs:** `ir.config_parameter` values are stale after a snapshot restore.

### Pitfall 5: Snapshot saved before module install completes

**What goes wrong:** Snapshot is saved immediately after `odoo.start()` but before modules are installed. Second run restores a DB without the requested modules.
**Why it happens:** Save call placed in the wrong position in the start flow.
**How to avoid:** Call `save_snapshot()` AFTER `await mm.install_module(mod)` loops complete — same pattern as TS reference.
**Warning signs:** Module `is_module_installed()` returns False on second run despite being in `modules=`.

### Pitfall 6: `ExecResult.output` is bytes, not string

**What goes wrong:** `result.output` is compared to a string or printed without decoding.
**Why it happens:** Python testcontainers `ExecResult.output` is `bytes` (from Docker's `exec_run`). TS returns `stderr`/`stdout` as separate strings.
**How to avoid:** Use `result.output.decode(errors='replace')` for error messages.
**Warning signs:** `TypeError: a bytes-like object cannot be interpreted as a str`.

---

## Code Examples

### Verified: `DockerContainer.exec` signature (testcontainers-python 4.14.2)

```python
# Source: live inspection via uv run python
from testcontainers.core.container import DockerContainer, ExecResult
# ExecResult namedtuple:  (exit_code: int, output: bytes)
# Usage (must be wrapped in asyncio.to_thread):
result = await asyncio.to_thread(container.exec, ['pg_dump', '-U', 'odoo', ...])
if result.exit_code != 0:
    raise RuntimeError(result.output.decode(errors='replace'))
```

### Verified: `with_volume_mapping` (testcontainers-python 4.14.2)

```python
# Source: live inspection via uv run python
pg = (
    PostgresContainer('postgres:15-alpine', username='odoo', password='odoo', dbname='test_odoo')
    .with_network(network)
    .with_network_aliases('db')
    .with_volume_mapping('/host/cache/dir', '/snapshot-cache', 'rw')
)
```

### Verified: `execute_kw` for `set_param` (from client.py)

```python
# Source: packages/godoo/src/godoo/client.py execute_kw
await client.execute_kw('ir.config_parameter', 'set_param', [key, value])
# Routes through client.call() → transport.call() → JSON-RPC execute_kw
# set_param is idempotent upsert — safe to call multiple times with same key
```

### Verified: Existing `asyncio.to_thread` pattern in container.py

```python
# Source: packages/godoo-testcontainers/src/godoo_testcontainers/container.py
await asyncio.to_thread(pg.start)
await asyncio.to_thread(wait_for_logs, pg, "ready for start up.", 90)
await asyncio.to_thread(network.remove)
# All new sync calls follow this exact pattern
```

### Verified: py.typed marker (from Phase 1 pattern)

```python
# Source: packages/godoo/src/godoo/py.typed (exists — CLIENT-10)
# New file: packages/godoo-testcontainers/src/godoo_testcontainers/py.typed
# Content: empty file
# pyproject.toml: [tool.hatch.build.targets.wheel] packages = ["src/godoo_testcontainers"]
# hatchling automatically includes py.typed when it's in the package directory
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `container.py` with all logic | Split into `snapshot.py`, `properties.py`, `harness.py` | This phase | Keeps container.py focused; each concern in its own module |
| No snapshot cache | pg_dump/restore keyed by content hash | This phase | Cold init only on first run or when inputs change |
| No addons mount | `--addons-path` CLI arg + volume mapping | This phase | Custom modules discoverable by Odoo without config file changes |
| Direct `OdooTestContainer.start()` usage | `TestHarness` async-cm | This phase | Cleaner fixture pattern; no manual cleanup needed |

**Deprecated/outdated:**
- `REQUIREMENTS.md` TESTC-01 path text (`~/.odoo-testcontainers/snapshots/`) — superseded by `cwd/.odoo-testcontainers/snapshots/` per D-Snap-3. Requires amendment task.
- `REQUIREMENTS.md` TESTC-03/04/05 — dropped per D-Drop-1. Requires amendment task.
- `ROADMAP.md` Phase 3 success criteria 3 and 4 — stale pre-amendment text. Requires amendment task.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Core Odoo addons path in official Docker image is `/usr/lib/python3/dist-packages/odoo/addons` for versions 17, 18, 19 | Addons Mount section | If wrong: Odoo fails to find `base` module; fix = update path constant. Clear error message from Odoo. |
| A2 | `ir.config_parameter.set_param` is callable via JSON-RPC in Odoo 18 and 19 CE (only 17 explicitly confirmed in CONTEXT.md) | Properties section | If wrong: `execute_kw` raises OdooRpcError; workaround = use search+write CRUD directly. Low risk — this method has been stable since Odoo 8. |
| A3 | `pg_dump`, `dropdb`, `createdb`, `pg_restore` are available inside `postgres:15-alpine` | Snapshot Mechanics section | If wrong: `exec()` returns non-zero exit code with "command not found"; fix = add explicit package install step or pin to a postgres image that includes them. `postgres:15-alpine` includes these by default. |

**If this table is empty for a claim**: All other claims were verified via live tool calls, codebase inspection, or official documentation.

---

## Open Questions

1. **Exact value of core Odoo addons path in odoo:18.0 and odoo:19.0**
   - What we know: `/usr/lib/python3/dist-packages/odoo/addons` is correct for 17.0 (Debian-based image). The path has been stable across Odoo Debian packages.
   - What's unclear: Whether 18/19 changed the installation layout.
   - Recommendation: Hard-code the path in a constant (`ODOO_CORE_ADDONS_PATH`) and add a comment noting it applies to official Odoo Debian images 17-19. If a future version changes it, the constant is the single edit point. Alternatively, use an env var override `ODOO_ADDONS_PATH_OVERRIDE` (planner discretion).

2. **`set_param` return value type**
   - What we know: Odoo's `set_param` returns a `bool` (True on success) or raises.
   - What's unclear: Whether the `execute_kw` wrapper returns the bool or whether it can return `None` on some Odoo versions.
   - Recommendation: Ignore the return value of `execute_kw` in `set_param` calls (treat as `None`-safe). The upsert either succeeds or raises `OdooRpcError`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Container lifecycle, pg_dump/restore | Yes | 29.3.0 | — (required) |
| `uv` | Workspace management, test runner | Yes | 0.11.13 | — |
| Python 3.14 | All source code | Yes (via uv) | 3.14 | — |
| `testcontainers` | Container API | Yes | 4.14.2 | — |
| `pg_dump`/`pg_restore` (inside container) | Snapshot save/restore | Yes (in postgres:15-alpine image) | PostgreSQL 15.x | — |
| `pg_dump` on host | (NOT needed) | Yes (18.3) | — | n/a — host pg_dump deliberately excluded (D-Snap deferred) |

**Missing dependencies with no fallback:** None.

---

## Security Domain

`security_enforcement: true` is set in `.planning/config.json`. ASVS Level 1 applies.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No — test infrastructure only; admin credentials are test-only defaults | n/a |
| V3 Session Management | No — testcontainers is not a web session handler | n/a |
| V4 Access Control | No — test infrastructure; no multi-user context | n/a |
| V5 Input Validation | Yes — snapshot key inputs, properties key/value, addons path | Validate: non-empty key (`OdooValidationError`); `Path.exists()` check for addons paths; `key` must not be empty string |
| V6 Cryptography | Partial — SHA-256 for snapshot key (integrity not secrecy) | Use stdlib `hashlib.sha256`; no custom crypto |

### Known Threat Patterns for Test Infrastructure

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `addons_path` | Tampering | Call `Path.resolve()` on all addons path inputs before using in bind mounts or key computation |
| Snapshot poisoning (untrusted cache dir) | Tampering | Cache dir is `cwd/.odoo-testcontainers/snapshots/` — project-local and gitignored; no remote cache support in v1 |
| Empty key for `ir.config_parameter` | Tampering | Raise `OdooValidationError` for empty key in `ConfigParameterHelper.set()` before RPC |
| Temp file left on failure (disk leak) | Denial of Service | Best-effort `unlink(missing_ok=True)` in exception handler of `save_snapshot()` |

---

## Sources

### Primary (HIGH confidence)
- `C:\dev\godoo-dev\godoo-py\packages\godoo-testcontainers\src\godoo_testcontainers\container.py` — existing container API and patterns
- `C:\dev\godoo-dev\godoo-py\packages\godoo\src\godoo\client.py` — `execute_kw`, `call` signatures
- `C:\dev\godoo-dev\godoo-ts\packages\testcontainers\src\snapshot-cache.ts` — TS reference for snapshot key algorithm and save/restore protocol
- `C:\dev\godoo-dev\godoo-ts\packages\testcontainers\src\odoo-container.ts` — TS reference for addons mount approach
- Live Python inspection: `testcontainers==4.14.2` `DockerContainer.exec`, `ExecResult`, `with_volume_mapping`, `DockerContainer.start` return value — confirmed via `uv run python`

### Secondary (MEDIUM confidence)
- Docker Hub official Odoo image documentation — confirms `/mnt/extra-addons` as volume mount target; addons_path in odoo.conf
- WebFetch of `raw.githubusercontent.com/odoo/docker/master/17.0/odoo.conf` — confirms `addons_path = /mnt/extra-addons`
- WebFetch of `raw.githubusercontent.com/odoo/docker/master/17.0/entrypoint.sh` — confirms NO `ADDONS_PATH` env var handling

### Tertiary (LOW confidence)
- WebSearch for Odoo 18/19 core addons path — consistent results pointing to same Debian path; not directly verified against 18/19 source

---

## Metadata

**Confidence breakdown:**
- Snapshot mechanics: HIGH — all Python API calls live-verified; TS reference read in full
- Addons mount: HIGH — entrypoint.sh read directly; odoo.conf read directly; approach clearly defined
- Properties (ir.config_parameter): HIGH — execute_kw surface verified in client.py; method confirmed in CONTEXT.md for Odoo 17; ASSUMED for 18/19
- TestHarness integration: HIGH — all integration points (container.py, cleanup, ModuleManager, OdooClient) verified from source
- py.typed: HIGH — mechanical; precedent in CLIENT-10 and INTRO-07

**Research date:** 2026-05-22
**Valid until:** 2026-08-22 (stable domain — testcontainers API, Odoo JSON-RPC, Python stdlib)
