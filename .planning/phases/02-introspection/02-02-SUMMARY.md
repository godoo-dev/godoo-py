---
phase: 02-introspection
plan: "02"
subsystem: godoo-introspection
tags: [introspection, codegen, typeddict, type-mapper, tdd, typing]
dependency_graph:
  requires:
    - phase: 02-01
      provides: [FieldMeta, ModelSchema, FieldSchema, Introspector — all consumed by codegen.py and type_mapper.py]
  provides: [CodeGenerator, python_type_str, type_mapper.py, codegen.py, 36 unit tests]
  affects: [packages/godoo-introspection]
tech_stack:
  added: []
  patterns: [pure-function type mapper, string-builder code generator, TDD RED/GREEN, importlib for generated-code round-trip test]
key_files:
  created:
    - packages/godoo-introspection/src/godoo_introspection/type_mapper.py
    - packages/godoo-introspection/src/godoo_introspection/codegen.py
    - packages/godoo-introspection/tests/test_type_mapper.py
    - packages/godoo-introspection/tests/test_codegen.py
  modified:
    - packages/godoo-introspection/src/godoo_introspection/__init__.py
key-decisions:
  - "Generated files omit 'from __future__ import annotations': Python 3.14 stores TypedDict annotations as ForwardRef with module='builtins' when exec'd from a calling module that has the future import; get_type_hints() fails to resolve Required/NotRequired. Generated files are standard Python modules — omitting the future import keeps annotations as actual type objects at definition time."
  - "_annotated_field_meta_str() lives in codegen.py (not type_mapper.py): FieldMeta constructor string is a codegen concern; type_mapper.py exposes only python_type_str()"
  - "get_type_hints round-trip test uses importlib.util to load generated file as a proper module: avoids exec/ForwardRef binding issue caused by calling test module's __future__ import"
  - "FieldSchema, ModelSchema, Path all under TYPE_CHECKING in codegen.py: ruff TCH rules are correct — with 'from __future__ import annotations', type annotations are strings; attribute-level runtime access does not require the import name"
patterns-established:
  - "Pure function type mapper: single public function python_type_str(field: FieldSchema) -> str with match/if-elif chain, no side effects except logger.warning for unknown ttypes"
  - "String-builder code generator: lines list accumulation, join at end, no template engine"
  - "TDD RED commit then GREEN commit per task: test file committed when failing, then implementation committed when passing"
requirements-completed: [INTRO-03, INTRO-04, INTRO-06]

duration: 35min
completed: "2026-05-21"
---

# Phase 2 Plan 2: Type Mapper + CodeGenerator Summary

**CodeGenerator emitting typed TypedDict Python modules from ModelSchema via python_type_str() mapping all 20 D-Mapping-1 Odoo ttypes, with 36 unit tests (22 mapper + 14 codegen) and get_type_hints round-trip verification via importlib.**

## Performance

- **Duration:** ~35 minutes
- **Started:** 2026-05-21T07:30:00Z
- **Completed:** 2026-05-21T08:05:00Z
- **Tasks:** 3 (Tasks 1 and 2 TDD, Task 3 verification — test files created in TDD phases)
- **Files modified:** 5

## Accomplishments

- `type_mapper.py` — pure function `python_type_str(field: FieldSchema) -> str` mapping all 20 Odoo ttype families to Python type strings per D-Mapping-1; selection static/dynamic; unknown ttype warning + fallback to `Any`
- `codegen.py` — `CodeGenerator` class with `generate(schema) -> str` (valid TypedDict module string) and `write(schemas, output_dir) -> None` (file I/O with security validation); `_annotated_field_meta_str()` builds compact FieldMeta constructor strings suppressing defaults
- `__init__.py` barrel updated: 6 exports (CodeGenerator added; 5 from Plan 01 preserved)
- 36 unit tests: 22 type_mapper (full D-Mapping-1 coverage) + 14 codegen (compile check, get_type_hints round-trip, write/init file output)

## Task Commits

Each task committed atomically:

1. **Task 1 RED: type_mapper tests** - `0f4d417` (test)
2. **Task 1 GREEN: type_mapper.py implementation** - `da4fe85` (feat)
3. **Task 2 RED: codegen tests** - `8f6ac12` (test)
4. **Task 2 GREEN: codegen.py + __init__.py + test fixes** - `8d28560` (feat)

_Task 3 test files were created and committed during Tasks 1 and 2 TDD RED/GREEN cycles — no separate commit needed._

## Files Created/Modified

- `packages/godoo-introspection/src/godoo_introspection/type_mapper.py` — `python_type_str()` pure function, 20 ttype families, logger.warning for D-Mapping-3 unknown fallback
- `packages/godoo-introspection/src/godoo_introspection/codegen.py` — `CodeGenerator` class with `generate()`/`write()`/`_annotated_field_meta_str()`; security: output_dir.is_dir() validation, field_name.isidentifier() guard, repr() for selection values
- `packages/godoo-introspection/src/godoo_introspection/__init__.py` — added `CodeGenerator` to imports and `__all__` (6 total exports)
- `packages/godoo-introspection/tests/test_type_mapper.py` — 22 pure unit tests, no fixtures, no async; covers all D-Mapping-1 ttypes, boolean no-Literal[False], caplog warning assertion
- `packages/godoo-introspection/tests/test_codegen.py` — 14 tests including compile() validation, importlib-based get_type_hints round-trip, write() file assertions, ValueError on invalid output_dir

## Decisions Made

- **Omit `from __future__ import annotations` in generated files:** Python 3.14 changed annotation storage. When a module with `from __future__ import annotations` exec's code, the exec'd class stores TypedDict annotations as `ForwardRef(module='builtins')`. When `get_type_hints()` tries to resolve `Required[int]`, it looks in `builtins` globals (not the exec namespace), causing `NameError`. Generated files are user-facing Python modules that should import cleanly without `from __future__`; omitting it keeps annotations as actual type objects.
- **`_annotated_field_meta_str()` in codegen.py:** The FieldMeta constructor string builder is a codegen concern. `type_mapper.py`'s public surface is limited to `python_type_str()` — returns only the bare type string. This separation follows the plan's D-Mapping-1/D-Meta-1 design.
- **importlib round-trip test:** Using `importlib.util.spec_from_file_location` + `exec_module` to load the generated .py as a proper module avoids the Python 3.14 ForwardRef module-binding issue that breaks `exec()`-based loading when the test module uses `from __future__ import annotations`.
- **TC (TYPE_CHECKING) imports in codegen.py:** ruff correctly identifies `FieldSchema`, `ModelSchema`, and `Path` as type-annotation-only uses in codegen.py (with `from __future__ import annotations`). These are moved under `TYPE_CHECKING`. Runtime access is via the parameter values (duck-typed attribute access), not via the imported class names.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff TC001 violations — FieldSchema import in type_mapper.py**
- **Found during:** Task 1 GREEN — ruff check
- **Issue:** ruff TC001 flagged `from godoo_introspection.types import FieldSchema` as an application import only used in type annotations (with `from __future__ import annotations`). Also flagged line-too-long E501 on a frozenset literal.
- **Fix:** Moved `FieldSchema` import under `TYPE_CHECKING`; split the `_STR_FALSE_TTYPES` frozenset across multiple lines.
- **Files modified:** type_mapper.py
- **Committed in:** da4fe85

**2. [Rule 1 - Bug] Python 3.14 get_type_hints ForwardRef resolution failure in exec context**
- **Found during:** Task 2 GREEN — test_generate_get_type_hints_round_trip failure
- **Issue:** The test called `exec(compiled_code, ns)` then `typing.get_type_hints(cls, globalns=ns)`. With `from __future__ import annotations` in both the generated file and the test module, Python 3.14 stores TypedDict annotations as `ForwardRef(module='builtins')`. `get_type_hints` resolves via the ForwardRef's `__forward_module__` attribute (which is `'builtins'`), ignoring the `globalns` parameter. `Required` is not in `builtins`, so `NameError` is raised.
- **Fix:** (a) Removed `from __future__ import annotations` from the generated file header (generated files are user-facing modules — they don't need it, and without it annotations are eagerly evaluated as real type objects). (b) Changed the test to use `importlib.util` to load the generated .py as a proper module with its own module context, avoiding the ForwardRef binding issue entirely.
- **Files modified:** codegen.py, test_codegen.py
- **Committed in:** 8d28560

**3. [Rule 1 - Bug] ruff TC001/TC002/TC003 violations in codegen.py and test files**
- **Found during:** Task 2 GREEN — ruff check after implementation
- **Issue:** `Path`, `FieldSchema`, `ModelSchema` flagged as annotation-only imports in codegen.py (TC001/TC003). `pytest` flagged as annotation-only in test_type_mapper.py (TC002). `tempfile` unused in test_codegen.py after removing exec-based approach.
- **Fix:** Moved `Path`, `FieldSchema`, `ModelSchema` under `TYPE_CHECKING` in codegen.py; moved `pytest` under `TYPE_CHECKING` in test_type_mapper.py; removed unused `tempfile` import from test_codegen.py; applied `ruff format` for import sorting.
- **Files modified:** codegen.py, test_codegen.py, test_type_mapper.py
- **Committed in:** 8d28560

---

**Total deviations:** 3 auto-fixed (all Rule 1 bugs)
**Impact on plan:** All fixes required for correctness and ruff/mypy compliance. The get_type_hints deviation is the most significant — it reveals a Python 3.14 behavior difference from the RESEARCH.md assumption. The fix (no `from __future__ import annotations` in generated files) is actually the more correct approach for user-facing code.

## Issues Encountered

- Python 3.14's annotation evaluation changed compared to earlier versions. The RESEARCH.md Pitfall 5 noted that `from __future__ import annotations` in generated files could cause issues, but the actual mechanism in 3.14 (ForwardRef with `module='builtins'`) was not fully anticipated. The importlib-based test approach resolves this cleanly for the test suite.

## Test Results

```
48 passed in 0.32s
  14 codegen tests
  12 introspector tests (from Plan 01)
  22 type_mapper tests
```

## Quality Gates

| Gate | Result |
|------|--------|
| `ruff check packages/godoo-introspection/` | PASS - no violations |
| `ruff format --check packages/godoo-introspection/` | PASS - all formatted |
| `mypy packages/godoo-introspection/src` | PASS - no issues (strict) |
| `pytest packages/godoo-introspection/ -m "not integration"` | PASS - 48/48 |
| `from godoo_introspection import CodeGenerator, Introspector, FieldMeta, ModelSchema, FieldSchema, IntrospectionCache` | PASS |
| `compile(CodeGenerator(None).generate(schema), "<s>", "exec")` | PASS |
| `get_type_hints(ResPartner, include_extras=True)` via importlib | PASS |

## Known Stubs

None — all type mapping and code generation logic is fully implemented. No placeholder values flow to any output.

## Threat Surface Scan

No new network endpoints or auth paths introduced. `codegen.py` writes files to disk via `output_dir / filename`. The threat T-02-05 (path traversal) is mitigated: `output_dir.is_dir()` validates the output directory before any write. T-02-06 (identifier injection): `field_name.isidentifier()` guard before emitting. T-02-07 (selection value injection): `repr()` used for all string values in the FieldMeta constructor string. T-02-08 (help text disclosure): `repr()` escapes safely. No new threats beyond the plan's threat model.

## Next Phase Readiness

- `godoo-introspection` package is complete for Phase 2 scope: Introspector (Plan 01) + CodeGenerator (Plan 02)
- `from godoo_introspection import CodeGenerator, Introspector, FieldMeta, ModelSchema, FieldSchema, IntrospectionCache` works
- Generated TypedDict files are importable at runtime and support `get_type_hints(include_extras=True)` for FieldMeta extraction
- Ready for state-manager or domain-filter consumers that call `Introspector.get_schema()` then `CodeGenerator.generate()`

## Self-Check: PASSED

Files exist:
- `packages/godoo-introspection/src/godoo_introspection/type_mapper.py` - exists
- `packages/godoo-introspection/src/godoo_introspection/codegen.py` - exists
- `packages/godoo-introspection/src/godoo_introspection/__init__.py` - updated (6 exports)
- `packages/godoo-introspection/tests/test_type_mapper.py` - exists (22 tests)
- `packages/godoo-introspection/tests/test_codegen.py` - exists (14 tests)

Commits verified:
- 0f4d417 - test(02-02): add failing tests for python_type_str
- da4fe85 - feat(02-02): implement type_mapper.py
- 8f6ac12 - test(02-02): add failing tests for CodeGenerator
- 8d28560 - feat(02-02): implement codegen.py + __init__.py + test fixes
