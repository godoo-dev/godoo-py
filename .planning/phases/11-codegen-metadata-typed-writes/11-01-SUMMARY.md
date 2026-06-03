---
phase: 11-codegen-metadata-typed-writes
plan: "01"
subsystem: godoo-introspection
tags: [codegen, metadata, pydantic, type-mapper, GEN-01]
dependency_graph:
  requires: []
  provides: [GEN-01]
  affects: [11-02-PLAN.md]
tech_stack:
  added: []
  patterns:
    - "4-tuple return from pydantic_field_str (annotation, default, imports, extra_dict)"
    - "Conditional Field() emission in codegen based on extra_dict"
    - "D-04 readonly rule: readonly=True OR (store=False AND compute is not None)"
key_files:
  created: []
  modified:
    - packages/godoo-introspection/src/godoo/introspection/type_mapper.py
    - packages/godoo-introspection/src/godoo/introspection/codegen.py
    - packages/godoo-introspection/tests/test_type_mapper.py
    - packages/godoo-introspection/tests/test_codegen.py
decisions:
  - "D-04 implemented: readonly flag requires readonly=True OR (store=False AND compute is not None); plain non-stored inverse fields (store=False, compute=None) are writable"
  - "from pydantic import Field emitted only when at least one field carries extra metadata"
  - "x2many fields use Field(default_factory=list, ...) not Field(default=[], ...) to avoid PydanticUserError"
metrics:
  duration: "~25m"
  completed: "2026-06-03"
  tasks: 3
  files: 4
---

# Phase 11 Plan 01: Codegen Metadata (GEN-01) Summary

**One-liner:** Widened `pydantic_field_str()` to 4-tuple emitting `odoo_readonly`/`odoo_x2many` metadata in `json_schema_extra`, enabling the Wave 2 write serializer to skip readonly/computed fields without schema lookups.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| T1-RED | Add failing GEN-01 metadata tests (8 new) | 9370242 | test_type_mapper.py |
| T1-GREEN | Widen pydantic_field_str() to 4-tuple + update all unpacks | 69444f3 | type_mapper.py, codegen.py, test_type_mapper.py, test_codegen.py |
| T2-RED | Add failing codegen Field() emission tests (4 new) | f462e27 | test_codegen.py |
| T2-GREEN | Emit Field() + conditional pydantic import in codegen.py | 1fb4efe | codegen.py |
| T3 | ROADMAP.md SC-4 D-04 wording verified (already correct) | — | ROADMAP.md |

## What Was Built

### Task 1: `pydantic_field_str()` 4-tuple return

`type_mapper.py` now returns `tuple[str, str, frozenset[str], dict[str, bool]]`:

- `extra["odoo_readonly"] = True` when `field.readonly or (not field.store and field.compute is not None)` — D-04 rule
- `extra["odoo_x2many"] = True` when `ttype in ("one2many", "many2many")`
- Empty dict for plain writable scalar fields

All ~20 existing test unpacks widened to 4-tuple (unused 4th var uses `_extra` per RUF059). 8 new metadata-assertion tests added covering all edge cases including D-04 refinement (plain non-stored inverse fields are writable).

### Task 2: `codegen.py` Field() emission

`codegen.generate()` now:

- Unpacks the full 4-tuple from `pydantic_field_str()`
- When `extra` is non-empty: emits `Field(default_factory=list, json_schema_extra=...)` for x2many (avoids `PydanticUserError` on mutable default) or `Field(default=<val>, json_schema_extra=...)` for other metadata fields; sets `need_field_import = True`
- When `extra` is empty: emits bare default (no change from v1.0 behavior)
- Adds `from pydantic import Field` to the header only when `need_field_import` is True

4 new codegen tests verify: readonly Field emission, x2many default_factory, import presence/absence.

### Task 3: ROADMAP.md SC-4 verification

SC-4 already contained the correct D-04 wording from planning. No edit needed. Grep verification passed: `store=False AND compute is not None` present at line 101.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] codegen.py 3-tuple unpack broken before Task 2 was started**

- **Found during:** Task 1 GREEN phase (running full test suite after type_mapper.py change)
- **Issue:** `codegen.py` line 139 still used `annotation, default, imports = pydantic_field_str(...)` — raised `ValueError: too many values to unpack` when running `test_cli.py`
- **Fix:** Updated the unpack to `annotation, default, imports, _extra = ...` in the same commit as Task 1 GREEN (69444f3)
- **Files modified:** `codegen.py`
- **Note:** This was the codegen.py unpack referenced in Task 2 `<action>` — fixed early as a prerequisite to keep the test suite green throughout

**2. [Rule 1 - Bug] RUF059 lint errors on unused `extra` variable names in tests**

- **Found during:** ruff check after Task 1 GREEN
- **Issue:** 22 RUF059 violations — unpacked `extra` variable was never used in existing type-mapper tests not checking metadata
- **Fix:** Renamed unused `extra` to `_extra` in all existing tests that don't check metadata; `test_codegen.py` uses `_` as the 4th positional discard
- **Files modified:** `test_type_mapper.py`, `test_codegen.py`

## Known Stubs

None. All metadata emission is fully wired: type_mapper computes and returns extra_dict; codegen consumes it and emits Field() with json_schema_extra. No placeholder or TODO values in generated output.

## Threat Flags

None. Added metadata flags are boolean values (`odoo_readonly`, `odoo_x2many`) — no sensitive schema data (labels, selection values) is added beyond what codegen already emits.

## Self-Check: PASSED

- [x] `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` exists and returns 4-tuple
- [x] `packages/godoo-introspection/src/godoo/introspection/codegen.py` exists with Field() emission
- [x] `packages/godoo-introspection/tests/test_type_mapper.py` has 8 new metadata tests
- [x] `packages/godoo-introspection/tests/test_codegen.py` has 4 new Field() emission tests
- [x] All 78 introspection tests pass
- [x] mypy --strict exits 0 on packages/godoo-introspection/src
- [x] ruff check + format --check exit 0
- [x] ROADMAP.md SC-4 contains "store=False AND compute is not None"
- [x] Commits 9370242, 69444f3, f462e27, 1fb4efe verified in git log
