---
phase: 09-structured-error-surface
plan: "01"
subsystem: errors
tags: [error-surface, privacy, structured-fields, breaking-change]
dependency_graph:
  requires: []
  provides:
    - OdooRpcError.raw (renamed from .data)
    - OdooRpcError.human_message
    - OdooRpcError.model_name
    - OdooRpcError.field_name
    - OdooRpcError.constraint_name
    - privacy gate (POSIX + Windows path stripping in __str__ and to_json)
  affects:
    - packages/godoo-client/src/godoo/client/errors.py
    - packages/godoo-client/tests/test_errors.py
tech_stack:
  added:
    - stdlib re (regex path stripping — D-15, no new runtime deps)
  patterns:
    - module-level compiled regex constants (_POSIX_PATH_RE, _WIN_PATH_RE)
    - private extractor helpers (_strip_paths, _extract_human_message, _extract_model_name, _extract_field_name, _extract_constraint_name)
    - __str__ override (human_message or args[0] — D-13)
    - flat to_json() shape (structured keys, no "details" or "raw")
key_files:
  created: []
  modified:
    - packages/godoo-client/src/godoo/client/errors.py
    - packages/godoo-client/tests/test_errors.py
decisions:
  - "OdooRpcError.data renamed to .raw (D-05); data= constructor kwarg preserved for transport.py compat (D-06)"
  - "to_json() emits flat structured keys {error, message, model_name, field_name, constraint_name, human_message} — no details, no raw (D-08, D-09)"
  - "__str__ returns human_message or args[0] — never exposes data.debug (D-13)"
  - "OdooSafetyError and OdooError base class left untouched (D-10)"
  - "No new runtime dependencies — stdlib re only (D-15)"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-02"
  tasks_completed: 2
  files_modified: 2
---

# Phase 9 Plan 01: Structured Error Surface Summary

**One-liner:** OdooRpcError refactored with `.raw` rename, five structured fields, privacy-safe `__str__`/`to_json()`, and POSIX/Windows path stripping via stdlib `re`.

## What Was Built

Restructured `OdooRpcError` to expose programmatic fault fields and strip server tracebacks from all user-visible output. This is the single sanctioned v1.2 breaking change: `.data` → `.raw`.

**Task 1 — errors.py refactor (commit c2b6c57):**
- Added `import re`, two compiled regex constants `_POSIX_PATH_RE`/`_WIN_PATH_RE`
- Added five private module-level helpers: `_strip_paths`, `_extract_human_message`, `_extract_model_name`, `_extract_field_name`, `_extract_constraint_name`
- Renamed `OdooRpcError.data` → `OdooRpcError.raw` (D-05); `data=` constructor kwarg preserved (D-06)
- Added structured instance fields: `.human_message`, `.model_name`, `.field_name`, `.constraint_name`
- Added `__str__` override returning `self.human_message or self.args[0]` (D-13)
- Reshaped `to_json()` to flat structured keys; removed `"details"` and `"raw"` keys (D-08/D-09)
- No changes to `OdooSafetyError`, `OdooError` base, or any subclass bodies (D-10)
- `transport.py` untouched — `data=` kwarg call sites remain compilable

**Task 2 — test_errors.py migration (commit b7dc011):**
- Migrated 4 broken assertions: `err.data` → `err.raw`, `"details"` key assertions replaced
- Added `not hasattr(err, "data")` assertion to `test_defaults`
- Added `TestOdooRpcErrorStructuredFields` with 13 test methods covering ERR-01..ERR-05:
  - ERR-01: structured field extraction from fault data
  - ERR-02: privacy gate (POSIX `/opt/odoo` and Windows `C:\odoo` paths stripped)
  - ERR-03: `.raw` holds full original fault dict including `"debug"` traceback
  - ERR-04: `to_json()` flat keys for all 7 subclasses; no `"raw"` or `"details"` keys
  - ERR-05: `.data` attribute removed; `data=` kwarg accepted; `.raw` is new name
  - D-13: `__str__` fallback (no data) and `human_message` priority cases

## Verification Results

- `ruff check packages/` + `ruff format --check packages/` → 0 issues
- `mypy packages/godoo-client/src packages/godoo-testcontainers/src packages/godoo-introspection/src` → "no issues found in 57 source files"
- `pytest packages/godoo-client/tests/test_errors.py -v` → 42 passed
- `pytest packages/ -m "not integration"` → 365 passed, 0 failures
- `git diff packages/godoo-client/src/godoo/client/rpc/transport.py` → no output (untouched)

Note: `ruff check .` (whole repo) reports 1 pre-existing issue in `spikes/08-pyodide/transport_pyfetch.py` (I001 import order) — not introduced by this phase, out of scope.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all structured fields are wired to live extractor logic; no placeholder values.

## Threat Flags

No new threat surface introduced. All mitigations from the plan's `<threat_model>` were implemented:

| Threat | Mitigation | Verified by |
|--------|-----------|-------------|
| T-09-01: data.debug in to_json() | "raw" key never emitted | test_to_json_no_raw_key (all 7 subclasses) |
| T-09-02: server path in str(exc) | __str__ returns human_message or args[0]; data.debug never reaches args[0] | test_no_server_path_in_str, test_windows_path_stripped |
| T-09-03: embedded path in data.message | _strip_paths() applied to human_message as defense-in-depth | test_no_server_path_in_str, test_windows_path_stripped |

## Self-Check: PASSED

- FOUND: packages/godoo-client/src/godoo/client/errors.py
- FOUND: packages/godoo-client/tests/test_errors.py
- FOUND: .planning/phases/09-structured-error-surface/09-01-SUMMARY.md
- FOUND: commit c2b6c57 (feat(09-01): structured error surface)
- FOUND: commit b7dc011 (test(09-01): migrate test_errors.py)
