---
phase: 03-testcontainers-parity
reviewed: 2026-05-22T12:05:46Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py
  - packages/godoo-testcontainers/src/godoo_testcontainers/container.py
  - packages/godoo-testcontainers/src/godoo_testcontainers/harness.py
  - packages/godoo-testcontainers/src/godoo_testcontainers/properties.py
  - packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py
  - packages/godoo-testcontainers/tests/test_container.py
  - packages/godoo-testcontainers/tests/test_harness.py
  - packages/godoo-testcontainers/tests/test_properties.py
  - packages/godoo-testcontainers/tests/test_snapshot.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
  invalidated: 1
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-22T12:05:46Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Adversarial re-review of the testcontainers-parity phase: `OdooTestContainer`,
`TestHarness`, `ConfigParameterHelper`, the snapshot caching module, and their unit
tests. The async-wrapping discipline for the sync testcontainers/pg APIs is generally
followed and the dataclass/conventions match the project standard.

The orchestration logic in `OdooTestContainer.start()` carries the real risk: it has
**no unit coverage** (only constructor attribute tests exist), and that is where the two
BLOCKER defects live — (CR-01) the snapshot **save** path silently ignores the
`ODOO_TESTCONTAINERS_SNAPSHOT=disabled` env override, writing a dump the operator
disabled; and (CR-02) `StartedOdooContainer.cleanup()` leaks the httpx `AsyncClient`
because it calls `logout()` but never `aclose()`.

A prior review pass (`CR-01` of that pass) flagged `seed_resolver.py:35`
(`except FileNotFoundError, json.JSONDecodeError:`) as a syntax error. That is a
**confirmed false positive** — PEP 758 (Python 3.14, which this project pins) permits an
unparenthesized exception tuple, and an AST/parse check confirms it compiles to a
two-element exception tuple. It is also out of this phase's diff scope. Recorded below as
INVALIDATED for traceability.

---

## Critical Issues

### CR-01: Snapshot save bypasses the `enabled`/env-disable gate

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:230-235`
(see also `:112-128`, `:150`)
**Issue:** `make_snapshot_config()` honours `ODOO_TESTCONTAINERS_SNAPSHOT=disabled` by
returning `SnapshotConfig(enabled=False, ...)` (`snapshot.py:170-174`). The **restore**
path respects this because it routes through `has_snapshot()`, which checks `cfg.enabled`
(`snapshot.py:195`). The **save** path does not. The container gates every snapshot side
effect on the *local* `snapshot_enabled` variable (line 90), which is derived solely from
the constructor flag and `seed_info` and never reflects the env override:

```python
if snapshot_enabled and snapshot_cfg is not None and not snapshot_hit:
    ...
    await save_snapshot(pg, snapshot_cfg, self._database, pg_user)
```

`save_snapshot()` itself also never inspects `cfg.enabled` (`snapshot.py:246`). Net
effect with `ODOO_TESTCONTAINERS_SNAPSHOT=disabled`: restore is skipped (so it is always
treated as a "miss"), then a dump is written to disk anyway — the exact opposite of
"disabled". The cache directory is likewise created (line 128) under the same wrong gate,
producing an unwanted `.odoo-testcontainers/snapshots/` tree even when the user opted
out. The unit suite asserts `cfg.enabled` is *computed* correctly
(`test_snapshot.py:112-129`) but never asserts the container/save path *honours* it,
which is why this slipped through.

**Fix:** Gate all snapshot side effects on the resolved `cfg.enabled`, not the local flag:

```python
snapshot_active = snapshot_cfg is not None and snapshot_cfg.enabled
if snapshot_active:
    snapshot_cfg.cache_dir.mkdir(parents=True, exist_ok=True)
...
if snapshot_active and has_snapshot(snapshot_cfg):
    ...
if snapshot_active and not snapshot_hit:
    ...
```

Also harden `save_snapshot()` to return early when `not cfg.enabled`.

---

### CR-02: HTTP transport never closed — AsyncClient leak in `cleanup()`

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:45-53`
**Issue:** `cleanup()` calls `self.client.logout()`, which only clears the in-memory
session/password (`transport.py:126-129`). It never calls `await self.client.aclose()`,
the method that closes the underlying `httpx.AsyncClient` connection pool
(`client.py:435-436` → `transport.py:131-133`). Because `OdooClient` deliberately exposes
no `__aenter__/__aexit__` (per CLAUDE.md), the harness is the *only* place expected to
close it. Every container lifecycle therefore leaks an open `AsyncClient`, surfacing as
"Unclosed client session" warnings and exhausting sockets/file descriptors across a
multi-container test session.

**Fix:**
```python
async def cleanup(self) -> None:
    logger.info("Cleaning up...")
    with contextlib.suppress(Exception):
        self.client.logout()
    with contextlib.suppress(Exception):
        await self.client.aclose()        # release the httpx pool
    for c in [self.odoo_container, self.postgres_container]:
        with contextlib.suppress(Exception):
            await asyncio.to_thread(c.stop)
    if self._network:
        with contextlib.suppress(Exception):
            await asyncio.to_thread(self._network.remove)
```

---

## Warnings

### WR-01: `startup_timeout` is accepted, stored, and never used

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:63,73`;
`harness.py:31,41`; consumed nowhere
**Issue:** `OdooTestContainer` and `TestHarness` both accept `startup_timeout` (default
300) and store `self._startup_timeout`, but readiness uses a hardcoded
`max_attempts=120` (`_wait_for_odoo_ready`, line 251 — ~240s, not 300s) and never reads
`self._startup_timeout`. The parameter is dead: a caller raising it for slow CI gets no
effect, and the *actual* timeout silently differs from the documented default. Tests
assert the value is stored (`test_container.py:18`, `test_harness.py:43`) but never that
it has any effect, masking the dead wire.

**Fix:** Convert the timeout (seconds) into an attempt budget and thread it through (sleep
is 2s):
```python
max_attempts = max(1, self._startup_timeout // 2)
await self._wait_for_odoo_ready(url, self._database, max_attempts=max_attempts)
```
Apply the same to the post-install retry at line 224.

---

### WR-02: Module-install retry swallows the original exception and assumes "restart"

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/container.py:219-226`
**Issue:** The retry block catches `Exception` and assumes the cause is an Odoo restart.
A genuine install failure (bad module name, ACL/dependency error) is swallowed, the code
waits up to 60 readiness attempts (~120s), re-authenticates, and retries the identical
call — which fails again, this time surfacing only the *second* error after a long delay.
The first exception is neither logged nor chained, making real failures slow and opaque.

**Fix:** Log the caught exception and narrow to the restart-shaped error types the godoo
client raises:
```python
except (OdooNetworkError, OdooTimeoutError) as exc:
    logger.info("Module install interrupted (server may have restarted): %s", exc)
    await self._wait_for_odoo_ready(url, self._database, max_attempts=...)
    await client.authenticate()
    await mm.install_module(mod)
```

---

### WR-03: Snapshot key claims `properties` are baked in, but the saved dump never contains them

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/harness.py:57-60` vs
`container.py:228-235`, `:78-81`
**Issue:** The snapshot **key** includes `properties` (`snapshot.py:151`,
`container.py:123`), but `TestHarness` applies properties via `set_many()` *after*
`container.start()` returns (line 57-60) — i.e. after `save_snapshot()` has already run
*inside* `start()` (line 233). A snapshot keyed on `{properties: {...}}` therefore does
not actually contain those `ir.config_parameter` rows. With the harness this is masked
because `set_many()` re-runs on every entry (including cache hits), but a bare
`OdooTestContainer` (no harness) that relies on snapshot + properties gets a dump whose
key advertises properties it does not hold. The "Stored for snapshot key accuracy only"
comment documents intent but the key/content split is a latent trap.

**Fix:** Either (a) document explicitly that properties are a key-only input applied by
the harness post-restore and that direct `OdooTestContainer` use does not seed them, or
(b) move property seeding into `OdooTestContainer.start()` before the snapshot save so the
dump and the key agree.

---

### WR-04: `_hash_addons_path` walks the filesystem synchronously on the async start path

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py:53-93`
(invoked from `container.py:113`)
**Issue:** `_hash_addons_path()` runs `os.walk()`, `Path.read_bytes()` on every file, and
`hashlib.sha256()` per file. It is reached synchronously from
`compute_snapshot_key` → `make_snapshot_config`, which is called inline (not via
`asyncio.to_thread`) inside the `async def start()` at line 113. For a large addons tree
(e.g. a full OCA module set) this blocks the event loop for the entire walk + read. CLAUDE.md
mandates wrapping sync filesystem work in `asyncio.to_thread()`.

**Fix:** Wrap the synchronous config builder:
```python
snapshot_cfg = await asyncio.to_thread(
    make_snapshot_config, snapshot_enabled=True, cache_dir=self._cache_dir, ...
)
```

---

### WR-05: `ODOO_TESTCONTAINERS_SNAPSHOT_DIR` is used unresolved — relative/traversal paths flow straight to the write path

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py:176-178`
**Issue:** The env-supplied directory is used as-is: `cache_dir_resolved = Path(env_dir)`.
`SnapshotConfig.host_path` then appends only `{key}.dump`, so the final write path is
fully controlled by the env var. A value like `../../somewhere` silently redirects all
snapshot writes outside the project tree, and the un-canonicalised relative form is hard
to audit in logs. In shared CI where this var may be set by a prior job, the blast radius
is "write a pg_dump file to an attacker-influenced directory".

**Fix:** Canonicalise (and optionally constrain to an expected prefix):
```python
if env_dir:
    cache_dir_resolved = Path(env_dir).resolve()
```

---

## Info

### IN-01: `ConfigParameterHelper` is missing from the package `__all__`

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/__init__.py:6-14`
**Issue:** `ConfigParameterHelper` is a public test helper used by `harness.py`, but it is
not re-exported from the package root, forcing
`from godoo_testcontainers.properties import ConfigParameterHelper`. This breaks the
barrel-export convention used elsewhere in the godoo family (CLAUDE.md).
**Fix:** Import and add `"ConfigParameterHelper"` to `__all__` in `__init__.py`.

---

### IN-02: `TestHarness.properties` builds a fresh helper on every access

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/harness.py:87-90`
**Issue:** Unlike `client`/`url`/`modules` (cached references), `properties` instantiates
a new `ConfigParameterHelper` on each read. `ConfigParameterHelper` is stateless so this
is harmless, but it is inconsistent and makes `h.properties is h.properties` surprisingly
false.
**Fix:** Build the helper once in `__aenter__` and return the stored instance, or document
the intentional statelessness.

---

### IN-03: `OdooValidationError` imported lazily inside `ConfigParameterHelper.set`

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/properties.py:20-22`
**Issue:** The import runs inside `set()` on every empty-key call. There is no circular-
import reason here — `godoo.errors` is a leaf module that does not import testcontainers —
so the lazy import only adds noise and a per-call import lookup.
**Fix:** Move `from godoo.errors import OdooValidationError` to module top level.

---

## Invalidated (carried from prior review pass)

### ~~CR (prior): SyntaxError in seed_resolver.py~~ — INVALIDATED (false positive)

**File:** `packages/godoo-testcontainers/src/godoo_testcontainers/seed_resolver.py:35`
**Status:** NOT a defect. `except FileNotFoundError, json.JSONDecodeError:` is valid under
PEP 758 (Python 3.14, the pinned interpreter): an unparenthesized exception tuple. Verified
this pass by parsing the file with `ast` — the handler resolves to a two-element exception
`Tuple`, catching both types. Also out of this phase's diff scope (file unmodified in
Phase 3). Parenthesizing remains a harmless readability nicety, not a bug.

---

_Reviewed: 2026-05-22T12:05:46Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
