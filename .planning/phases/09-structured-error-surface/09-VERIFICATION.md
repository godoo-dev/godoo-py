---
phase: 09-structured-error-surface
verified: 2026-06-02T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 9: Structured Error Surface — Verification Report

**Phase Goal**: Callers can handle RPC errors programmatically without parsing strings, and server tracebacks never leak into logs or serialized output.
**Verified**: 2026-06-02
**Status**: PASSED
**Re-verification**: No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | D-11 D-08: `.model_name`, `.field_name`, `.constraint_name`, `.human_message` (each `str \| None`) accessible directly on `OdooRpcError` without string parsing | VERIFIED | `errors.py` lines 86-89: all four attributes assigned in `__init__` via private extractors; `TestOdooRpcErrorStructuredFields` (13 test methods) cover all four fields including empty-context cases |
| 2 | D-01 D-02 D-03 D-13 D-15: `str(exc)` and `to_json()` never contain filesystem paths or server Python tracebacks | VERIFIED | `__str__` returns `human_message or args[0]` (line 94); `_strip_paths()` applied to `human_message` (line 30); `to_json()` has no `debug` or `raw` key; `test_no_server_path_in_str`, `test_no_server_path_in_to_json`, `test_windows_path_stripped` all PASS |
| 3 | D-04 D-09: `exc.raw` holds full untouched fault dict; `to_json()` never emits `"raw"` key | VERIFIED | `self.raw = data` (line 85); `to_json()` keys are: `error`, `message`, `model_name`, `field_name`, `constraint_name`, `human_message` — no `raw`, no `details`; `test_raw_holds_full_dict` and `test_to_json_no_raw_key` (all 7 subclasses) PASS |
| 4 | D-10 D-12 D-14: All existing `except OdooRpcError` / `isinstance` checks continue to work unchanged | VERIFIED | Subclass hierarchy unchanged; `OdooSafetyError` untouched; `OdooError` base untouched; `TestOdooAuthError` through `TestOdooSafetyError` pass without modification; `isinstance(err, OdooRpcError)` tested in `TestOdooAuthError.test_inherits_rpc_error` and peers |
| 5 | D-05 D-06 D-07: `OdooRpcError.data` is gone; `data=` constructor kwarg retained; `exc.raw` is the new name | VERIFIED | `self.raw` assigned (line 85); no `self.data` assignment anywhere in class; `not hasattr(err, "data")` asserted in `test_defaults` and `test_data_attribute_removed`; `data=` kwarg present in `__init__` signature (line 80); `transport.py` uses `data=data` kwarg throughout (lines 149-168) — compiles unchanged |

**Score**: 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/godoo-client/src/godoo/client/errors.py` | Structured error surface: `.raw`, `.human_message`, `.model_name`, `.field_name`, `.constraint_name`, `__str__` override, reshaped `to_json()`, `_POSIX_PATH_RE` constant | VERIFIED | File contains all required elements: `_POSIX_PATH_RE` (line 10), `_WIN_PATH_RE` (line 11), `_strip_paths` (line 14), `_extract_human_message` (line 21), `_extract_model_name` (line 34), `_extract_field_name` (line 45), `_extract_constraint_name` (line 53), `__str__` (line 93), reshaped `to_json()` (lines 96-106) |
| `packages/godoo-client/tests/test_errors.py` | Migrated + new tests covering ERR-01 through ERR-05 and privacy gate; `TestOdooRpcErrorStructuredFields` class present | VERIFIED | Class present (line 90), 13 test methods covering all five requirements including POSIX and Windows path privacy gates; `err.raw` replaces `err.data` in migrated assertions |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `transport.py` | `errors.py` | `_categorize_error` passes `data=data` kwarg | VERIFIED | Lines 149, 160, 163, 165, 168 in transport.py all use `data=data`; kwarg name unchanged after `.data`→`.raw` rename; transport.py itself was not modified |
| `test_errors.py` | `errors.py` | `err.raw` replaces `err.data`; `to_json()` flat keys | VERIFIED | `err.raw` used in `test_defaults` (line 53), `test_stores_code_and_data` (line 61), `test_raw_holds_full_dict` (line 142); flat keys asserted in `test_to_json` (lines 73-76) and `test_to_json_flat_keys` (lines 181-187) |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces exception classes, not components that render dynamic data.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 42 unit tests pass | `uv run pytest packages/godoo-client/tests/test_errors.py -q` | 42 passed in 0.11s | PASS |

### Probe Execution

No probes declared or conventional for this phase (error class refactor, not a migration/tooling phase).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| ERR-01 | 09-01 | `.model_name`, `.field_name`, `.constraint_name`, `.human_message` (str \| None) parsed from fault payload | SATISFIED | Attributes assigned in `OdooRpcError.__init__` via private extractors; `TestOdooRpcErrorStructuredFields.test_human_message_extracted`, `test_model_name_none_for_empty_context`, `test_field_name_none_for_empty_context`, `test_constraint_name_none_for_empty_context` all PASS |
| ERR-02 | 09-01 | Server tracebacks and filesystem paths stripped from `str(exc)` / user-facing message | SATISFIED | `_strip_paths()` applied to `human_message`; `__str__` returns `human_message or args[0]` — never touches `data.debug`; POSIX gate (`test_no_server_path_in_str`, `test_no_server_path_in_to_json`) and Windows gate (`test_windows_path_stripped`) PASS |
| ERR-03 | 09-01 | Full original fault payload preserved on `.raw` escape-hatch attribute | SATISFIED | `self.raw = data` stores exact reference; `test_raw_holds_full_dict` confirms identity (`is`) and presence of `"debug"` key in raw |
| ERR-04 | 09-01 | `to_json()` emits structured fields + human message; never the raw payload | SATISFIED | `to_json()` returns 6 flat keys (`error`, `message`, `model_name`, `field_name`, `constraint_name`, `human_message`); `test_to_json_no_raw_key` asserts `"raw" not in to_json()` for all 7 subclasses; `test_to_json_flat_keys` asserts all four structured keys present and `"details"` absent |
| ERR-05 | 09-01 | `.data` renamed to `.raw`; `data=` kwarg retained; no compat alias; hierarchy additive-only | SATISFIED | `not hasattr(err, "data")` confirmed by two tests; `data=` kwarg present in `__init__` signature; no compat alias in source; subclass hierarchy unchanged (no new intermediate classes) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/HACK/placeholder markers found in modified files | — | None |

Stub scan: no `return null`, `return {}`, `return []` patterns in the two modified files in a rendering context. The `or None` fallbacks in extractor functions are intentional sentinel returns for the structured attribute pattern, not stubs.

### Human Verification Required

None. All behaviors are programmatically verifiable and confirmed by the test suite.

### Gaps Summary

No gaps. All five must-have truths are VERIFIED against the actual codebase:

- `errors.py` contains the complete implementation: two compiled path-stripping regexes, five private extractors, `self.raw` (not `self.data`), four structured attributes, `__str__` override, and reshaped `to_json()` with no `raw` or `details` key.
- `test_errors.py` contains `TestOdooRpcErrorStructuredFields` with 13 test methods covering all five requirements including Windows and POSIX path privacy gates.
- `transport.py` was not modified and compiles correctly against the `data=` constructor kwarg.
- 42 unit tests pass with 0 failures (0.11s).

---

_Verified: 2026-06-02T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
