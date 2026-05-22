---
status: resolved
phase: 03-testcontainers-parity
source: [03-VERIFICATION.md]
started: 2026-05-22T00:00:00Z
updated: 2026-05-22T00:00:00Z
resolution: automated
resolution_note: "All three items converted to automated Docker integration tests in packages/godoo-testcontainers/tests/test_integration.py — 3 passed in 88s against Docker 29.3.0 / odoo:17.0. No manual testing performed or required."
---

## Current Test

[resolved — covered by automated integration tests]

## Tests

### 1. Snapshot hit/miss cycle (TESTC-01)
expected: A first run saves a pg_dump snapshot under `cwd/.odoo-testcontainers/snapshots/`; an identical second run restores it and skips Odoo init.
result: passed (automated — `test_snapshot_save_and_restore`: cold run produces artifact, `has_snapshot` True, identical second run restores cleanly)

### 2. Custom addons mount (TESTC-02)
expected: `addons_path=` mounts the directory read-only and `--addons-path` includes it so a module there is discoverable/installable.
result: passed (automated — `test_custom_addons_mount`: a temp module installs via `is_module_installed`)

### 3. TestHarness full lifecycle (TESTC-06 + TESTC-07)
expected: `async with TestHarness(...)` starts the container, installs modules, seeds `ir.config_parameter`, and exposes a ready authenticated `OdooClient`.
result: passed (automated — `test_harness_lifecycle_and_properties`: client authenticated, set/set_many/get_param round-trip, empty key raises OdooValidationError)

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
