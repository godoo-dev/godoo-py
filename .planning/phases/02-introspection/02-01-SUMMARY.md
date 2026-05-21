---
phase: 02-introspection
plan: "01"
subsystem: godoo-introspection
tags: [introspection, schema, cache, tdd, typing]
dependency_graph:
  requires: [Phase 1 OdooClient (search_read, OdooMissingError, OdooValidationError)]
  provides: [Introspector, IntrospectionCache, FieldMeta, ModelSchema, FieldSchema, py.typed]
  affects: [packages/godoo-introspection]
tech_stack:
  added: []
  patterns: [frozen dataclass, per-instance cache, TYPE_CHECKING guard, TDD RED/GREEN]
key_files:
  created:
    - packages/godoo-introspection/src/godoo_introspection/py.typed
    - packages/godoo-introspection/src/godoo_introspection/markers.py
    - packages/godoo-introspection/src/godoo_introspection/types.py
    - packages/godoo-introspection/src/godoo_introspection/introspector.py
    - packages/godoo-introspection/tests/__init__.py
    - packages/godoo-introspection/tests/test_introspector.py
  modified:
    - packages/godoo-introspection/src/godoo_introspection/__init__.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
decisions:
  - "INTRO-05 (godoo-introspect CLI) dropped from v1 scope per D-CLI-1; struck from REQUIREMENTS.md and ROADMAP.md; v1 count is now 29"
  - "IntrospectionCache is per-Introspector-instance (not module-global) for test isolation and multi-client safety"
  - "FieldMeta is frozen=True (hashable); ModelSchema is plain @dataclass (not frozen, dict field is unhashable)"
  - "get_schema delegates to get_schemas for DRY batch implementation"
  - "Defensive .get() with defaults for all raw dict access; handles Odoo 'copied' vs 'copy' column name difference"
metrics:
  duration: "8 minutes"
  completed: "2026-05-21T07:05:35Z"
  tasks_completed: 3
  files_created: 7
  files_modified: 3
---

# Phase 2 Plan 1: Schema Fetch + Cache Summary

**One-liner:** Introspector with per-instance IntrospectionCache using batch ir.model + ir.model.fields search_read, typed FieldMeta/ModelSchema/FieldSchema frozen dataclasses, and 12 unit tests with respx mocks.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Amend planning docs (INTRO-05 drop) and create py.typed marker | 2ea4391 | .planning/REQUIREMENTS.md, .planning/ROADMAP.md, py.typed |
| 2 (RED) | Failing tests for Introspector + cache behaviors | e64359a | tests/__init__.py, tests/test_introspector.py |
| 2 (GREEN) | markers.py, types.py, introspector.py — schema fetch + cache | 8ca855f | markers.py, types.py, introspector.py |
| 3 | __init__.py barrel and finalized test_introspector.py | 8c666b8 | __init__.py, introspector.py (format), test_introspector.py (format) |

## What Was Built

### markers.py — FieldMeta frozen dataclass

`FieldMeta` is a `@dataclass(frozen=True)` with 19 attributes: 17 from the `ir.model.fields` projection (ttype, field_description, relation, relation_field, required, readonly, store, index, copy, translate, help, compute, depends, modules, on_delete, size, digits) plus 2 codegen-specific flags (`original_ttype`, `dynamic_selection`). All fields are scalars or immutable tuples, making instances fully hashable. Intended for use in `Annotated[T, FieldMeta(...)]` markers on generated TypedDict fields.

### types.py — ModelSchema and FieldSchema

`FieldSchema` is a `@dataclass(frozen=True)` carrying the full `ir.model.fields` projection including a `selection: list[tuple[str, str]]` for static selection values. `ModelSchema` is a plain `@dataclass` (not frozen) because its `fields: dict[str, FieldSchema]` attribute is unhashable — correct per Pitfall 6 in the research.

### introspector.py — Introspector + IntrospectionCache

`IntrospectionCache` is a plain class with `self._cache: dict[str, ModelSchema]` providing `get/set/invalidate/clear`. Per-instance, not module-global — avoids test isolation failures.

`Introspector` issues:
1. RPC 1: `search_read('ir.model', [('model', 'in', names)], fields=['name', 'model', 'transient'])` — model metadata
2. RPC 2: `search_read('ir.model.fields', [('model', 'in', names)], fields=_IR_FIELDS)` — all 18 field columns in one batch
3. RPC 3 (conditional): `search_read('ir.model.fields.selection', ...)` — only when selection fields with non-empty `selection_ids` exist

All `ir.model.fields` raw dict values are accessed defensively via `.get()` with defaults. `depends` and `modules` are split from comma-separated strings into `tuple[str, ...]`. The `copied` vs `copy` column difference is handled by trying `copied` first with `copy` as fallback.

### __init__.py barrel

Exports 5 public names: `Introspector`, `IntrospectionCache`, `FieldMeta`, `FieldSchema`, `ModelSchema`. No `from __future__ import annotations` in the barrel (follows testcontainers barrel precedent).

### tests/test_introspector.py — 12 tests

Follows `test_cdc.py`/`test_urls.py` pattern. Multi-RPC mocking uses `iter([resp1, resp2, ...])` as `side_effect` on `respx.post().mock()`. Covers:
- FieldMeta hashable, all 19 default attributes correct
- ModelSchema not hashable (TypeError on hash())
- get_schemas([]) raises OdooValidationError
- Missing model raises OdooMissingError
- get_schema returns ModelSchema with FieldSchema fields
- Caching: second call uses cache (call_count == 2, not 4)
- bypass_cache=True forces fresh fetch (call_count == 4)
- Batch: two models in one RPC (not per-model)
- Selection fields populated from ir.model.fields.selection
- Dynamic selection: empty selection_ids → empty selection list
- IntrospectionCache invalidate works correctly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mypy error in _coerce_str_or_none return type**
- **Found during:** Task 2 GREEN — mypy run
- **Issue:** `return value` where value was typed `Any` but return is `str | None`; mypy flagged this despite isinstance check
- **Fix:** Changed to `return str(value)` to satisfy mypy
- **Files modified:** introspector.py
- **Commit:** 8ca855f

**2. [Rule 1 - Bug] Mypy error in selection_map fid assignment**
- **Found during:** Task 2 GREEN — mypy run
- **Issue:** `raw_fid` was inferred as `Any | None` but `int()` expects a non-None value
- **Fix:** Added explicit `raw_fid: Any = sel.get("field_id")` type annotation
- **Files modified:** introspector.py
- **Commit:** 8ca855f

**3. [Rule 1 - Bug] Ruff import sort violation in test file**
- **Found during:** Task 3 ruff check
- **Issue:** Blank line between stdlib and local imports in test file was considered unsorted
- **Fix:** `uv run ruff check --fix` applied auto-fix; ruff format applied to introspector.py and test file
- **Files modified:** tests/test_introspector.py, introspector.py
- **Commit:** 8c666b8

**4. Path drift (worktree absolute-path safety #3099)**
- **Found during:** Task 1 verification
- **Issue:** Initial Edit/Write calls used `C:\dev\godoo-dev\godoo-py\...` (main repo) instead of the worktree path `C:\dev\godoo-dev\godoo-py\.claude\worktrees\agent-accc32266fe27f09a\...`
- **Fix:** Re-applied all Task 1 edits (REQUIREMENTS.md, ROADMAP.md, py.typed) to the correct worktree paths before committing
- **Impact:** None — no incorrect commits; corrected before staging

## Test Results

```
12 passed in 0.27s
```

All 12 test cases green.

## Quality Gates

| Gate | Result |
|------|--------|
| `ruff check packages/godoo-introspection/` | PASS — no violations |
| `ruff format --check packages/godoo-introspection/` | PASS — all formatted |
| `mypy packages/godoo-introspection/src` | PASS — no issues (strict) |
| `pytest packages/godoo-introspection/tests/test_introspector.py -v` | PASS — 12/12 |
| `from godoo_introspection import Introspector, FieldMeta, ModelSchema, FieldSchema, IntrospectionCache` | PASS |
| `py.typed` exists and is zero bytes | PASS |
| REQUIREMENTS.md: INTRO-05 not active, count = 29 | PASS |

## Known Stubs

None — all schema fetch logic is implemented with real (mocked) RPC calls in tests. No placeholder values flow to any output.

## Threat Surface Scan

No new network endpoints or auth paths introduced. `Introspector` uses the existing `OdooClient.search_read()` — trust boundary is the existing RPC layer already handled by `JsonRpcTransport`. Input validation threats T-02-01 and T-02-02 are mitigated (OdooValidationError for empty names list and empty string names). T-02-03 and T-02-04 accepted as documented in the plan's threat model.

## Self-Check: PASSED

Files exist:
- `packages/godoo-introspection/src/godoo_introspection/py.typed` — exists, 0 bytes
- `packages/godoo-introspection/src/godoo_introspection/markers.py` — exists
- `packages/godoo-introspection/src/godoo_introspection/types.py` — exists
- `packages/godoo-introspection/src/godoo_introspection/introspector.py` — exists
- `packages/godoo-introspection/src/godoo_introspection/__init__.py` — updated
- `packages/godoo-introspection/tests/__init__.py` — exists
- `packages/godoo-introspection/tests/test_introspector.py` — exists

Commits verified:
- 2ea4391 — chore(02-01): drop INTRO-05 from planning docs and add py.typed marker
- e64359a — test(02-01): add failing tests for Introspector, IntrospectionCache, FieldMeta, ModelSchema
- 8ca855f — feat(02-01): implement markers.py, types.py, and introspector.py — schema fetch + cache
- 8c666b8 — feat(02-01): complete __init__.py barrel and finalize test_introspector.py
