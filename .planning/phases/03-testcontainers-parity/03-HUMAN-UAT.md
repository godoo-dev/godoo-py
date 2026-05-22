---
status: partial
phase: 03-testcontainers-parity
source: [03-VERIFICATION.md]
started: 2026-05-22T00:00:00Z
updated: 2026-05-22T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Snapshot hit/miss cycle (TESTC-01)
expected: With Docker available, a first `OdooTestContainer` / `TestHarness` run with snapshot caching enabled provisions the DB and runs `pg_dump` (save). A second run with identical provisioner inputs restores from `cwd/.odoo-testcontainers/snapshots/` via `pg_restore` and completes measurably faster than the first (Odoo `--init base` skipped). Changing any hashed input (modules, addons content, properties, database, admin_password, env) invalidates the cache and forces a fresh provision.
result: [pending]

### 2. Custom addons mount (TESTC-02)
expected: Passing `addons_path=Path("./my_addons")` (or a `list[Path]`) to `OdooTestContainer` / `TestHarness` mounts the directory read-only into the container (`/mnt/extra-addons` for a single path, `/mnt/addons-0,1,...` for a list) and Odoo's `--addons-path` includes both the mounted dir(s) and the core addons path, so a module placed there is discoverable and installable via `modules=[...]`.
result: [pending]

### 3. TestHarness full lifecycle (TESTC-06 + TESTC-07)
expected: `async with TestHarness(modules=[...], properties={...}, ...) as h:` starts the container, installs the requested modules, applies the `ir.config_parameter` properties via `set_param`, and exposes a ready authenticated `OdooClient` as `h.client` plus `h.url`, `h.modules`, `h.properties`. `await h.properties.set(k, v)` and `await h.properties.set_many({...})` set system parameters; `await h.properties.set("", v)` raises `OdooValidationError`. On exit the container is cleaned up.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
