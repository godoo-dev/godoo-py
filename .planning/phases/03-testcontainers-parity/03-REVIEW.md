---
phase: 03-testcontainers-parity
reviewed: 2026-05-22T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py
  - packages/godoo-testcontainers/src/godoo_testcontainers/container.py
  - packages/godoo-testcontainers/src/godoo_testcontainers/properties.py
  - packages/godoo-testcontainers/src/godoo_testcontainers/harness.py
  - packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py
  - packages/godoo-testcontainers/tests/test_snapshot.py
  - packages/godoo-testcontainers/tests/test_container.py
  - packages/godoo-testcontainers/tests/test_properties.py
  - packages/godoo-testcontainers/tests/test_harness.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
  invalidated: 1
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-22
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the complete Phase 3 testcontainers-parity implementation: snapshot infrastructure
(`snapshot.py`), container orchestration (`container.py`), config-parameter helper
(`properties.py`), and the `TestHarness` context manager (`harness.py`), plus all unit tests.

The implementation is structurally sound and the async wrapping discipline for testcontainers'
sync API is generally correct. Three critical issues were identified: a syntax error in
`seed_resolver.py` that will crash on import, a credential leak via the `_wait_for_odoo_ready`
readiness probe that logs the admin password, and a missing `aclose()` call on the HTTP
transport in `StartedOdooContainer.cleanup()`. Five warnings cover correctness gaps in the
snapshot save path, the TOCTOU race window in the snapshot existence check, an unchecked
assumption about `seed_info` in `container.py`, command injection via shell-string construction,
and a missing validation guard on `cache_dir` from environment. Three informational items are
also noted.

---

## Critical Issues

### CR-01: ~~SyntaxError in seed_resolver.py~~ — INVALIDATED (false positive)

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/seed_resolver.py:35`
**Status:** INVALIDATED during orchestrator triage. NOT a defect.

The reviewer flagged `except FileNotFoundError, json.JSONDecodeError:` as Python 2 syntax that
would crash on import. This is **incorrect for this project**: godoo-py pins **Python 3.14**, and
**PEP 758** (new in 3.14) allows `except` / `except*` with an unparenthesized exception tuple.
The construct compiles and correctly catches both exceptions. Verified empirically:
`py_compile` exits 0, `import godoo_testcontainers.seed_resolver` succeeds, `mypy --strict`
parses all 48 source files clean, and the full unit suite passes. Additionally, `seed_resolver.py`
was **not modified in Phase 3** (out of review scope). No action required. (Parenthesizing the
tuple would still be a harmless style nicety for readers expecting pre-3.14 syntax, but it is
not a bug and is out of this phase's scope.)

---

### CR-02: Admin password leaked via HTTP POST body in readiness probe

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:252-256`
**Issue:** `_wait_for_odoo_ready` constructs a JSON payload containing the raw
`self._admin_password` and POSTs it to Odoo's session authenticate endpoint. While the password
is not explicitly logged, any HTTP debug middleware, `httpx` event hook, or transport-layer
logging (e.g. `HTTPX_LOG_LEVEL=trace`) will capture the full request body, exposing the
credential. Beyond logging, `_wait_for_odoo_ready` is called up to `max_attempts=60` times during
a module-install retry, meaning the password is serialised into JSON in a hot loop.

More critically: the payload is **also used as a de-facto "Odoo is fully up" probe** — the auth
endpoint is not Odoo-ready-checked, it is used as a liveness check. This architectural concern
is acceptable in test infrastructure, but the credential must not appear in payload dict form
where it can be captured by logging layers.

**Fix:** Use a non-authenticating readiness endpoint instead (e.g. `/web/health` available from
Odoo 16+, or poll `/web/database/selector` which does not require credentials). Fall back to the
current approach only if the health endpoint is unavailable, and pass the password directly
without constructing a loggable dict:
```python
async def _wait_for_odoo_ready(self, url: str, database: str, max_attempts: int = 120) -> None:
    async with httpx.AsyncClient() as http:
        for i in range(max_attempts):
            with contextlib.suppress(httpx.HTTPError):
                resp = await http.get(f"{url}/web/health")
                if resp.status_code == 200:
                    logger.info("Odoo ready (attempt %d)", i + 1)
                    return
            await asyncio.sleep(2)
    raise TimeoutError("Odoo did not become ready")
```
If `/web/health` must remain unavailable for Odoo <16, keep the auth probe but do not store
the password in a named `payload` dict that could be intercepted — pass it inline without a
reusable binding that could be logged.

---

### CR-03: HTTP transport never closed — resource leak in StartedOdooContainer.cleanup()

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:45-53`
**Issue:** `StartedOdooContainer.cleanup()` calls `self.client.logout()` (the synchronous
transport logout that clears the session token) but never calls `await self.client.aclose()`
(which closes the underlying `httpx.AsyncClient` transport). The `OdooClient` documentation
in `client.py` line 435 is explicit: callers must call `aclose()` to release the HTTP
connection pool. In tests that start and stop many containers in a session (e.g. parameterised
integration tests), each call to `cleanup()` leaks an open `httpx.AsyncClient`, which holds
file descriptors and a connection pool.

**Fix:**
```python
async def cleanup(self) -> None:
    logger.info("Cleaning up...")
    self.client.logout()
    await self.client.aclose()          # <-- add this
    for c in [self.odoo_container, self.postgres_container]:
        with contextlib.suppress(Exception):
            await asyncio.to_thread(c.stop)
    if self._network:
        with contextlib.suppress(Exception):
            await asyncio.to_thread(self._network.remove)
```

---

## Warnings

### WR-01: TOCTOU race in save_snapshot — pre-dump exists check is not atomic

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py:254-283`
**Issue:** The "fast-path skip" at line 254 (`if cfg.host_path.exists(): return`) and the
"post-dump skip" at line 276 are described as handling concurrent workers, but the window
between the pre-dump check and `pg.exec(pg_dump)` is not atomic. Under `pytest-xdist` with
multiple workers, two workers can both pass the pre-dump check, both call `pg_dump`, and both
attempt `os.replace(tmp_host, cfg.host_path)`. The second `os.replace` silently overwrites the
first completed dump — not a crash but a potential write of a partial or in-progress dump file
over a complete one if the second worker finishes pg_dump before the first worker's atomic rename.

More specifically: the temp file naming includes `pid + monotonic_ns + random`, which avoids
temp-file collision. However if worker-1 completes pg_dump, passes the post-dump skip check (no
file yet), then worker-2 completes pg_dump AND renames its temp file first (race), then
worker-1's rename overwrites the valid file. Both files are valid pg_dump outputs so the result
is still correct, but the race produces unnecessary double work and a spurious overwrite.

This is a minor correctness concern in tests only, but the code comment claims the design is
"safe under concurrent pytest workers" — that claim is overstated.

**Fix:** Add a file lock (e.g. `filelock` or `fcntl`) around the post-dump rename, or accept
the design as intentional best-effort and update the comment to accurately reflect the race
window.

---

### WR-02: `seed_info` accessed without None guard in module install loop

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:215`
**Issue:** Line 215:
```python
to_install = [m for m in self._modules if m not in seed_info.seed_modules] if seed_info else self._modules
```
The ternary is correct as written, but the `else` branch (`self._modules`) is the cold-start
path. The issue is the `if seed_info` guard: when `seed_info is not None` but
`seed_info.seed_modules` is an empty list (a valid `SeedInfo` where the seed image has no
pre-installed modules), `to_install` becomes `self._modules` in full — which is the correct
behaviour. However if `resolve_seed_info` ever returns a `SeedInfo` with `seed_modules=[]`
(possible if the config's `"modules"` key is an empty list — see `seed_resolver.py:58`), the
code silently treats it as "seed covers nothing" and re-installs everything. This is correct by
accident but is surprising and untested.

More concretely: the `seed_info` branch at line 97 sets `pg_user, pg_password = "admin", "admin"`
but the snapshot path at line 150 uses `pg_user` (which could be "admin" from the seed path),
then calls `restore_snapshot(pg, snapshot_cfg, self._database, pg_user)` — but
`snapshot_enabled` is `self._snapshot_enabled and (seed_info is None)` at line 90, so when
`seed_info` is set, `snapshot_enabled` is already False, so `snapshot_cfg` is None. The
snapshot guard at line 150 is `if snapshot_enabled and snapshot_cfg is not None` — safe.

The actual gap is narrower: there is no test asserting that when a seed image is provided but
does not cover all requested modules, `to_install` contains only the uncovered modules.

**Fix:** Add a unit test for the `to_install` computation when `seed_info.seed_modules` is a
subset of `self._modules`. The production code is functionally correct but the coverage gap
means a future refactor could silently regress.

---

### WR-03: Shell-string command construction enables argument injection

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:178`
**Issue:** Line 178:
```python
.with_command(" ".join(cmd_parts))
```
`cmd_parts` is assembled from caller-controlled values: `self._database`, `self._modules` (via
`--init base`), and `addon_targets` (derived from `addons_path`). `with_command()` in
testcontainers passes the string to Docker as a shell command string (not an exec array),
meaning a database name containing spaces or shell metacharacters (e.g. `"test; rm -rf /data"`)
would be interpreted by the shell inside the container.

In a test-infrastructure context the attacker would need control over test configuration, so the
practical severity is low — but a test framework that accepts a `database` parameter from, say,
a CI environment variable or pytest fixtures populated from untrusted sources is a realistic
injection vector.

**Fix:** Quote shell-unsafe values or, if testcontainers supports it, pass the command as a list
(exec form) rather than a string (shell form):
```python
# Prefer exec form if the Docker SDK supports it via with_command(list):
.with_command(cmd_parts)   # passes as JSON array → exec form, no shell interpolation
```
If `with_command` requires a string, shell-quote each element:
```python
import shlex
.with_command(shlex.join(cmd_parts))
```

---

### WR-04: `ODOO_TESTCONTAINERS_SNAPSHOT_DIR` env var is not validated — path traversal possible

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py:176-178`
**Issue:**
```python
env_dir = os.environ.get("ODOO_TESTCONTAINERS_SNAPSHOT_DIR", "")
if env_dir:
    cache_dir_resolved = Path(env_dir)
```
The environment-supplied path is used as-is without resolution or validation. A value like
`../../etc` or an absolute path outside the project tree would silently redirect all snapshot
files. The `SnapshotConfig.host_path` property then appends only `/{key}.dump`, so the final
write path is entirely controlled by the environment variable. In a shared CI environment where
`ODOO_TESTCONTAINERS_SNAPSHOT_DIR` could be set by a prior job or by a supply-chain attack on
CI env configuration, this allows writing files to arbitrary filesystem locations.

**Fix:**
```python
if env_dir:
    cache_dir_resolved = Path(env_dir).resolve()
    # Optional: assert it is under an expected prefix, e.g. the project root
```
At minimum call `.resolve()` so relative traversal sequences (`../..`) are canonicalised to
their absolute form, making it easier to audit in logs.

---

### WR-05: `snapshot.py` walks the filesystem synchronously in the async call path

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py:53-93`
**Issue:** `_hash_addons_path()` is a synchronous function that calls `os.walk()`,
`Path.read_bytes()` (reading every file in every addons directory), and `hashlib.sha256()` for
each file. It is called from `compute_snapshot_key()`, which is called from
`make_snapshot_config()`, which is called inline in `OdooTestContainer.start()` at line 113 —
an `async def` function — **without** being wrapped in `asyncio.to_thread()`.

For large addons directories (e.g. a full OCA module tree with hundreds of Python files), this
blocks the event loop for the duration of the filesystem walk and all the file reads. The
project convention (CLAUDE.md) is explicit: sync filesystem/subprocess calls in async code must
be wrapped in `asyncio.to_thread()`.

**Fix:**
```python
# In OdooTestContainer.start(), replace:
snapshot_cfg = make_snapshot_config(...)

# With:
snapshot_cfg = await asyncio.to_thread(make_snapshot_config, ...)
```
`make_snapshot_config` itself is synchronous, so wrapping the call is the right fix. Alternatively,
refactor `_hash_addons_path` to use `asyncio.to_thread` internally, but that changes it to
`async def`, which would require propagating async through `compute_snapshot_key` and
`make_snapshot_config` — the wrapper approach is simpler.

---

## Info

### IN-01: `compute_snapshot_key` includes `admin_password` in the hash payload — value is visible in debug logs if payload is ever logged

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py:148-154`
**Issue:** The `payload` dict passed to `json.dumps()` includes `"adminPassword": admin_password`
in plain text. The result is hashed and never stored, but if a future debugging aid ever logs
`payload` (e.g. `logger.debug("Snapshot key payload: %s", payload)`), the admin password
appears. The current code does not log it, but the structure is one `logger.debug` away from a
credential leak.

**Fix:** No immediate code change required, but document in a comment that this dict must never
be logged. Alternatively, include only `hashlib.sha256(admin_password.encode()).hexdigest()` in
the payload (so the password is pre-hashed before insertion):
```python
"adminPassword": hashlib.sha256(admin_password.encode()).hexdigest(),
```
This does not change the key (any change to the password still produces a different hash), but
removes the plaintext credential from the intermediate structure.

---

### IN-02: `ConfigParameterHelper` missing from `__all__` in `__init__.py`

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py:6-14`
**Issue:** `ConfigParameterHelper` is exported by `properties.py` and used in `harness.py`, but
it is not listed in `__all__`. Users who need direct access to it (e.g. to apply properties
outside a `TestHarness`) must import it from the sub-module path
(`from godoo_testcontainers.properties import ConfigParameterHelper`), not from the package
root. This is inconsistent with the barrel-export pattern used by every other godoo package
(per CLAUDE.md conventions).

**Fix:**
```python
from godoo_testcontainers.properties import ConfigParameterHelper

__all__ = [
    "ConfigParameterHelper",
    "OdooTestContainer",
    ...
]
```

---

### IN-03: `test_snapshot.py` imports `pytest` only under `TYPE_CHECKING` — type annotation applied to runtime parameter

**File:** `packages/godoo-testcontainers/tests/test_snapshot.py:12-15`
**Issue:**
```python
if TYPE_CHECKING:
    from pathlib import Path
    import pytest
```
`Path` is imported under `TYPE_CHECKING` only. However `tmp_path: Path` and
`monkeypatch: pytest.MonkeyPatch` are parameter annotations on test functions. With
`from __future__ import annotations` (line 1), annotations are strings at runtime, so this works
correctly — pytest resolves fixture injection by name, not annotation type. No runtime error
occurs.

However `import pytest` is also under `TYPE_CHECKING`, and `pytest.MonkeyPatch` appears only
in annotations, which is safe. This pattern is unconventional for test files: `pytest` is
a test-time dependency and should simply be imported at the top level. The current structure is
correct but confusing to readers who might assume pytest is a production dependency being
guarded against.

**Fix:** Move `import pytest` out of the `TYPE_CHECKING` block in test files (the guard is
appropriate for production modules to avoid runtime circular imports, not for test files):
```python
from pathlib import Path
import pytest
```

---

_Reviewed: 2026-05-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
