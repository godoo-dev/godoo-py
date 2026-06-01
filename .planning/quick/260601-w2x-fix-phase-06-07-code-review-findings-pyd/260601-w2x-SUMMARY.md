---
quick_id: 260601-w2x
phase: quick
plan: 260601-w2x
subsystem: godoo-client, godoo-introspection
tags: [wire-transform, typed-dispatch, codegen, cli, correctness, security]
dependency_graph:
  requires: []
  provides: [wire-transform-correctness, typed-dispatch-correctness, codegen-safety, cli-error-handling]
  affects: [godoo-client, godoo-introspection]
tech_stack:
  added: []
  patterns: [list-origin-check-before-false-coercion, structural-import-detection, id-injection-search-read]
key_files:
  created: []
  modified:
    - packages/godoo-client/src/godoo/client/_pydantic_transform.py
    - packages/godoo-client/src/godoo/client/typed.py
    - packages/godoo-client/src/godoo/client/client.py
    - packages/godoo-client/tests/test_pydantic_transform.py
    - packages/godoo-client/tests/test_typed_dispatch.py
    - packages/godoo-introspection/src/godoo/introspection/codegen.py
    - packages/godoo-introspection/src/godoo/introspection/type_mapper.py
    - packages/godoo-introspection/src/godoo/introspection/cli.py
    - packages/godoo-introspection/tests/test_codegen.py
    - packages/godoo-introspection/tests/test_cli.py
    - packages/godoo-introspection/tests/test_type_mapper.py
decisions:
  - "Ref.name widened to str | None (from str) to support restricted display names without a separate type"
  - "list-origin detection scans Union args to handle list[T] | None uniformly"
  - "pydantic_field_str returns 3-tuple (annotation, default, frozenset[str]) — breaking change updated in all callers and tests"
  - "_model_to_classname raises ValueError (not returns None) so invalid classnames propagate loudly"
metrics:
  duration: "~35 minutes"
  completed: "2026-06-01T21:23:00Z"
  tasks_completed: 5
  files_modified: 11
---

# Phase quick Plan 260601-w2x: Fix Phase 06/07 Code Review Findings Summary

**One-liner:** Closed 10 correctness/safety gaps in godoo-client wire transforms, typed dispatch, and godoo-introspection codegen/CLI with 17 new unit tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| A | Fix x2many False→[] and m2o [id,False]→Ref in wire transform | 3f11228 | _pydantic_transform.py, typed.py, test_pydantic_transform.py |
| B | Inject 'id' in search_read typed path; wrap ValueError as OdooValidationError | 1a1c942 | client.py, test_typed_dispatch.py |
| C | Codegen reserved-name/keyword/classname guards, LF writes, structural imports | 66643ef | codegen.py, type_mapper.py, test_codegen.py |
| D | Catch OdooError in CLI generate wrapper | 86f04dd | cli.py, test_cli.py |
| E | Full quality gate | — | (no code changes; all checks green) |
| fix | Ruff violations + test_type_mapper 3-tuple API update | 82674ed | 4 test files |

## Findings Fixed

| # | Finding | Fix |
|---|---------|-----|
| 1 | x2many `False` not coercing to `[]` | List-origin check fires before generic False→None rule |
| 2 | `search_read` typed path missing `id` injection | `dict.fromkeys(["id", *fields])` before RPC call |
| 3 | m2o `[id, False]` raises ValidationError | Accept `value[1] is False`; produce `Ref(id=id, name=None)` |
| 4 | Pydantic reserved names (e.g. `model_config`) emitted as fields | `_PYDANTIC_RESERVED_NAMES` frozenset guard in field loop |
| 5 | Python keywords (e.g. `class`) emitted as fields | `keyword.iskeyword()` guard in field loop |
| 6 | `OdooAuthError`/`OdooNetworkError` propagate as raw tracebacks | Extended `except ValueError` to `except (ValueError, OdooError)` |
| 7 | `ValueError` from `derive_partial_model` leaks unwrapped | `try/except ValueError → raise OdooValidationError` at both dispatch sites |
| 8 | Numeric-starting models produce `SyntaxError` class names | `_model_to_classname` raises `ValueError` if result not `.isidentifier()` |
| 9 | CRLF written to generated files on Windows | Both `write_text` calls use `newline="\n"` |
| 10 | Import detection re-parses annotation strings | `pydantic_field_str` returns `frozenset[str]` imports; codegen uses set membership |

## New Tests Added

- `test_pydantic_transform.py`: 3 new tests (x2many False→[], optional list, m2o restricted name)
- `test_typed_dispatch.py`: 5 new tests (id injection, no duplicate, read no-injection, ValueError→OdooValidationError ×2)
- `test_codegen.py`: 7 new tests (reserved name, keyword, invalid classname ×2, LF newlines, type_mapper imports, structural date import)
- `test_cli.py`: 3 new tests (auth error exit 1, network error exit 1, password-not-in-output)

**Total new tests: 18** (plan said 17; an additional ValueError test for `read()` was correctly separated).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_typed_dispatch.py RPC body inspection path**
- **Found during:** Task B (RED phase)
- **Issue:** The tests captured `params.kwargs` but the transport sends kwargs as `params.args[6]` (7th element of execute_kw args array). The test never captured any fields.
- **Fix:** Added `_extract_rpc_fields()` helper that correctly inspects `params.args[6]` dict.
- **Files modified:** `test_typed_dispatch.py`
- **Commit:** 1a1c942

**2. [Rule 1 - Bug] test_type_mapper.py expected 2-tuples from pydantic_field_str**
- **Found during:** Task E (quality gate)
- **Issue:** Existing tests compared `pydantic_field_str(...)` against 2-tuple literals; now returns 3-tuples (Finding #10 change is a breaking API change for callers).
- **Fix:** Updated all tests in `test_type_mapper.py` to unpack 3-tuples and assert the imports frozenset explicitly.
- **Files modified:** `test_type_mapper.py`
- **Commit:** 82674ed

**3. [Rule 2 - Missing critical functionality] Ruff violations in new test code**
- **Found during:** Task E (quality gate)
- **Issue:** `RUF012` (mutable default), `TC002` (pytest in TYPE_CHECKING), `RUF059` (unused unpacked vars), `E501` (line too long)
- **Fix:** Used `Field(default_factory=list)`, moved pytest import, prefixed unused vars with `_`
- **Files modified:** `test_pydantic_transform.py`, `test_cli.py`, `test_codegen.py`
- **Commit:** 82674ed

## Quality Gate

```
uv run ruff check .          → All checks passed!
uv run ruff format --check . → 92 files already formatted
uv run mypy ...              → Success: no issues found in 57 source files
uv run pytest packages/ -m "not integration" → 352 passed, 3 deselected, 2 warnings
```

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. All changes are internal to transformation logic and CLI error handling. T-w2x-02 (password not in OdooError output) verified by `test_generate_odoo_error_password_not_in_output`.

## Self-Check

### Created files exist
- `.planning/quick/260601-w2x-fix-phase-06-07-code-review-findings-pyd/260601-w2x-SUMMARY.md` ✓

### Commits exist
- 3f11228 ✓ (Task A)
- 1a1c942 ✓ (Task B)
- 66643ef ✓ (Task C)
- 86f04dd ✓ (Task D)
- 82674ed ✓ (quality gate fixes)

## Self-Check: PASSED
