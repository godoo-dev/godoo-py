---
phase: 11-codegen-metadata-typed-writes
verified: 2026-06-03T00:00:00Z
updated: 2026-06-03T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 11: Codegen Metadata + Typed Writes — Verification Report

**Phase Goal:** Callers can pass a typed `OdooBaseModel` instance into `client.write` or `client.create`, and only explicitly-set, writable fields are sent on the wire.
**Verified:** 2026-06-03
**Status:** passed
**Re-verification:** No — initial verification (post-review, post-fix)

## Context

The code review (11-REVIEW.md) found two blockers after the initial wave of implementation:

- **CR-01** — the x2many guard fired on read-inherited x2many fields, breaking read→modify-scalar→write
- **CR-02** — codegen emitted `id: int` (required, no default), making typed `create()` impossible without a bogus id

Commits 2c33f3f, 3f65e8c, and 00c0823 were applied to fix both blockers. This verification confirms those fixes hold.

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `client.create(instance)` accepts OdooBaseModel instance, returns new id; only `model_fields_set` fields sent, readonly excluded | VERIFIED | `client.py:516-551` typed dispatch branch; `_serialize_for_write` iterates `model_fields_set`; `test_typed_create_returns_new_id` + `test_typed_create_excludes_readonly` pass |
| 2 | `client.write(instance)` sends only `__pydantic_fields_set__`; unset fields never sent as None | VERIFIED | `client.py:553-589` typed dispatch; `_serialize_for_write` iterates `model_fields_set` exclusively (never `model_dump()`); `test_typed_write_sends_only_set_fields` + 36 other unit tests pass |
| 3 | Write serializer converts `Ref`→int, `None`→False, `date`/`datetime`→ISO strings | VERIFIED | `_pydantic_transform.py:386-407`; `test_typed_write_ref_becomes_int`, `test_typed_write_none_becomes_false`, `test_typed_write_date_becomes_iso_string`, `test_typed_write_datetime_becomes_iso_string` all pass |
| 4 | Generated fields include `json_schema_extra={"odoo_readonly": True}` where `readonly=True OR (store=False AND compute is not None)`; plain non-stored fields without compute NOT marked; write serializer uses this to exclude non-writable | VERIFIED | `type_mapper.py:62-65`; `codegen.py:144-153`; ROADMAP SC-4 updated at line 101; D-04 rule matches implementation; `test_readonly_field_excluded_when_set` + `test_computed_field_excluded_when_set` pass |
| 5 | Writing x2many field via typed path raises `OdooValidationError` pointing to raw `write()` with command tuples | VERIFIED | `_pydantic_transform.py:376-384`; raises only when `field_name in user_set` (CR-01 fix); `test_x2many_constructor_kwarg_raises_validation_error`, `test_x2many_explicit_mutation_raises_validation_error`, `test_x2many_error_message_mentions_command_tuples` all pass |
| 6 | End-to-end test feeds codegen-generated model class through `client.read` dispatch then `client.write`, closing backlog 999.3 (TEST-01) | VERIFIED | `test_codegen_read_write_roundtrip` ran on live Odoo 18.0 and PASSED — full read→typed-instance→write-scalar→re-read roundtrip executed end-to-end. Codegen regression test (no-Docker) also added. Additional fix commit 6922d34 applied (strip inline comment before `Field()` embedding, found during integration run). Backlog 999.3 CLOSED. Unit-test evidence: `test_cr01_generated_class_read_then_modify_scalar_does_not_raise`, `test_cr02_generated_class_create_without_id`, `test_cr01_generated_class_x2many_constructor_kwarg_raises`, `test_cr01_generated_class_explicit_x2many_mutation_raises` all pass. |

**Score:** 6/6 truths verified (unit-test evidence; integration half of SC-6 deferred to human verification)

---

## CR-01 Fix Verification (Review Blocker)

**Blocker finding:** x2many guard raised on read-inherited x2many fields, breaking read→modify-scalar→write.

**Fix mechanism:** `OdooBaseModel.model_post_init` now seeds `_user_set_fields`:
- Read-built instance (context carries `_READ_CONTEXT_KEY`): `_user_set_fields` starts **empty** — read-inherited x2many not counted as user writes
- User-built instance (no context flag): `_user_set_fields` seeded from `model_fields_set` — constructor kwargs including x2many count as explicit writes
- `__setattr__` adds any post-construction mutation to `_user_set_fields`

`_serialize_for_write` raises only when `field_name in user_set`, not on mere presence in `model_fields_set`.

**Evidence — all four contracts exercised against codegen-produced class:**

| Contract | Test | Result |
|----------|------|--------|
| (a) scalar-only create — no x2many raise | `test_x2many_from_constructor_does_not_raise` | PASS |
| (b) read → modify scalar → write — no raise, x2many omitted | `test_cr01_generated_class_read_then_modify_scalar_does_not_raise` | PASS |
| (c1) x2many constructor kwarg → raise | `test_cr01_generated_class_x2many_constructor_kwarg_raises` | PASS |
| (c2) post-construction x2many mutation → raise | `test_cr01_generated_class_explicit_x2many_mutation_raises` | PASS |

Read path wiring: `client.py:112` calls `target.model_validate(raw, context=READ_VALIDATION_CONTEXT)` via `_validate_typed`. `READ_VALIDATION_CONTEXT = {_READ_CONTEXT_KEY: True}` is exported from `_pydantic_transform.py:27`.

---

## CR-02 Fix Verification (Review Blocker)

**Blocker finding:** Codegen emitted `id: int` (required, no default), preventing typed `create()` without a bogus id.

**Fix:** `codegen.py:227` now emits `    id: int | None = None`.

**Evidence:**
- `codegen.py:227`: `lines.append("    id: int | None = None")` (confirmed in source)
- `codegen.py:102`: docstring documents the optional-id contract
- `test_cr02_generated_class_create_without_id`: `ResPartner(name="Acme Corp")` succeeds, `instance.id is None` — PASS
- `test_cr02_generated_class_id_not_in_payload`: `_serialize_for_write` drops `id` from payload — PASS
- `_serialize_for_write:357-359` explicitly skips `id` regardless of its presence in `model_fields_set`

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` | 4-tuple `pydantic_field_str()` with D-04 metadata | VERIFIED | Returns `tuple[str, str, frozenset[str], dict[str, bool]]`; extra dict logic at lines 61-65 |
| `packages/godoo-introspection/src/godoo/introspection/codegen.py` | Field() emission, `from pydantic import Field` header, `id: int | None = None` | VERIFIED | Lines 144-153 emit `Field()` when `extra`; line 207-208 conditional `from pydantic import Field`; line 227 `id: int | None = None` |
| `packages/godoo-client/src/godoo/client/_pydantic_transform.py` | `_serialize_for_write()`, `OdooBaseModel.model_post_init`, `__setattr__`, `READ_VALIDATION_CONTEXT` | VERIFIED | All present; CR-01 dirty-tracking at lines 169-196; `_serialize_for_write` at lines 327-408 |
| `packages/godoo-client/src/godoo/client/client.py` | Typed `create`/`write` overloads + dispatch; `OdooBaseModel` under `TYPE_CHECKING` | VERIFIED | Lines 515-589; `OdooBaseModel` in `TYPE_CHECKING` block at line 26; `# type: ignore[misc]` on both impl signatures |
| `packages/godoo-client/tests/test_typed_writes.py` | Unit tests + TEST-01 integration test | VERIFIED | 17 unit tests pass; CR-01/CR-02 tests against codegen-produced classes pass; integration test correctly gated by `@pytest.mark.integration` |
| `packages/godoo-client/tests/test_serialize_for_write.py` | Serializer unit tests | VERIFIED | 20 tests pass; `test_no_set_fields_returns_empty_dict` now asserts `payload == {}` (WR-04 weakness fixed) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `type_mapper.pydantic_field_str()` | `codegen.py` | 4th tuple element `extra` | WIRED | `codegen.py:142` unpacks 4-tuple; `codegen.py:145-153` conditionally emits `Field()`  |
| `codegen.py` | generated module | `need_field_import` flag → `from pydantic import Field` | WIRED | Lines 207-208 |
| `client.py create/write dispatch` | `_pydantic_transform._serialize_for_write` | lazy import inside dispatch branch | WIRED | `client.py:539,579` lazy imports |
| `_serialize_for_write` | `instance.model_fields_set` | iteration | WIRED | `_pydantic_transform.py:356` |
| `_serialize_for_write` | `_user_set_fields` (CR-01) | `object.__getattribute__` | WIRED | `_pydantic_transform.py:351` |
| `_serialize_for_write` | `FieldInfo.json_schema_extra` | `instance.__class__.model_fields.get(field_name).json_schema_extra` | WIRED | `_pydantic_transform.py:363-364` |
| `client.py _validate_typed` | `READ_VALIDATION_CONTEXT` | `model_validate(..., context=READ_VALIDATION_CONTEXT)` | WIRED | `client.py:112`; context flows into `model_post_init.__context` at `_pydantic_transform.py:177` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_serialize_for_write` | `user_set` | `object.__getattribute__(instance, "_user_set_fields")` | Yes — seeded by `model_post_init` from `model_fields_set` or empty set | FLOWING |
| `_serialize_for_write` | `extra_dict` | `fi.json_schema_extra` from pydantic `FieldInfo` populated at class definition | Yes — carries `odoo_readonly`/`odoo_x2many` flags from codegen | FLOWING |
| `codegen.py generate()` | `id` field | hardcoded `"    id: int | None = None"` at line 227 | Yes — always emits optional id | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 437 non-integration tests pass | `uv run pytest packages/ -m "not integration" -q` | 437 passed, 4 deselected, 2 warnings in 7.83s | PASS |
| CR-01/CR-02 contracts pass against codegen class | `uv run pytest ... -k "cr0"` | 5 passed | PASS |
| Serializer tests pass | `uv run pytest test_serialize_for_write.py` | 20 passed | PASS |
| mypy --strict on all src | `uv run mypy packages/*/src` | Success: no issues found in 57 source files | PASS |
| ruff check | `uv run ruff check packages/*/src packages/*/tests` | All checks passed | PASS |

---

## Probe Execution

No probe scripts declared or discovered for this phase.

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| GEN-01 | 11-01-PLAN.md | Codegen emits readonly/stored field metadata into `json_schema_extra` | SATISFIED | `type_mapper.py:61-65`; `codegen.py:144-153`; `test_type_mapper.py` metadata tests |
| WRITE-01 | 11-02-PLAN.md | `client.create(instance)` creates record, returns new id | SATISFIED | `client.py:515-551`; `test_typed_create_returns_new_id` |
| WRITE-02 | 11-02-PLAN.md | `client.write(instance)` sends only `__pydantic_fields_set__` | SATISFIED | `_pydantic_transform.py:356`; `test_typed_write_sends_only_set_fields` |
| WRITE-03 | 11-02-PLAN.md | Ref→int, None→False, date/datetime→ISO | SATISFIED | `_pydantic_transform.py:386-407`; transform tests pass |
| WRITE-04 | 11-02-PLAN.md | Readonly/computed fields excluded from write payloads | SATISFIED | `_pydantic_transform.py:367-369`; `test_readonly_field_excluded_when_set` |
| WRITE-05 | 11-02-PLAN.md | x2many raises `OdooValidationError`; read-inherited x2many omitted (CR-01) | SATISFIED | `_pydantic_transform.py:376-384`; x2many tests pass; CR-01 roundtrip passes |
| TEST-01 | 11-03-PLAN.md | Codegen→typed-read round-trip test (closes 999.3) | SATISFIED | `test_codegen_read_write_roundtrip` ran on live Odoo 18.0 and passed; codegen regression test added; commit 6922d34 fixed inline-comment stripping in codegen output; backlog 999.3 closed |

All 7 phase requirements mapped and covered. No orphaned requirements.

---

## Anti-Patterns Found

No `TBD`, `FIXME`, or `XXX` markers found in phase-touched files. No stub patterns detected.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `test_typed_writes.py` | 54 | `WritePartner` has `id: int` (required) — not the generated shape (CR-02) | INFO | The hand-written fixture with required `id` coexists with the codegen-backed tests in the same file. The codegen-backed CR-02 tests confirm the actual fix. Not a blocker. |

---

## Warnings (from review — status post-fix)

| Review Item | Status | Evidence |
|-------------|--------|----------|
| WR-01: x2many error message used `{field}` non-interpolated literal | RESOLVED | `_pydantic_transform.py:378-382` interpolates `field_name` via f-string |
| WR-04: `test_no_set_fields_returns_empty_dict` only asserted `isinstance(dict)` | RESOLVED | Now asserts `payload == {}` at `test_serialize_for_write.py:62` |
| WR-02: None→False on create could override server defaults | INFO — documented; not a code defect | Serializer docstring notes the semantics; not a blocker |
| WR-03: `write()` guard dead for `id: int` models | RESOLVED by CR-02 fix | `id: int | None = None` makes the guard live |
| WR-05: `derive_partial_model` hash-based name collisions | INFO — pre-existing; not introduced this phase | Not addressed this phase; not a blocker |
| IN-01: Two loggers share same name | INFO — pre-existing | `type_mapper.py:13` and `codegen.py:17` both use `"godoo_introspection.codegen"` |
| IN-02: `repr(dict)` dict ordering | INFO — currently stable; not a blocker | Insertion order is deterministic |
| IN-03: Integration test teardown not in finally | INFO — risk only if assertion fails mid-test | No `try/finally` wrap; not a blocker for unit runs |

---

## Integration Verification — CONFIRMED PASSED

### 1. TEST-01 Integration: Codegen → Read → Write Round-Trip (closes 999.3)

**Test:** `uv run pytest packages/godoo-client/tests/test_typed_writes.py::test_codegen_read_write_roundtrip -x -q -m integration`

**Result: CONFIRMED PASSED** — ran on live Odoo 18.0, 2026-06-03.

Confirmed steps:
1. TestHarness started a Docker Odoo 18.0 instance with base module
2. Introspector fetched `res.lang` schema from the live container
3. CodeGenerator emitted a Python module string with `id: int | None = None` and `from pydantic import Field` where needed
4. `exec()` produced a `ResLang` class with `__odoo_model__ == "res.lang"`
5. `client.search_read(ResLang, [...], limit=1)` returned a typed `ResLang` instance
6. Modifying `instance.name` and calling `client.write(instance)` returned `True`
7. Re-reading the record confirmed the name was updated
8. Restore write succeeded; container left clean

**Additional finding during integration run:** commit 6922d34 applied — strip inline comment before `Field()` embedding. Codegen was emitting `# comment  Field(...)` syntax when field descriptions contained `#` characters; the fix strips the trailing comment so the emitted code is valid Python. A no-Docker codegen regression test was also added to prevent recurrence.

**Backlog 999.3 is closed.**

---

## Gaps Summary

No gaps. All 7 requirements satisfied with codebase evidence. The two review blockers (CR-01 and CR-02) are both fixed and verified with tests that exercise the actual codegen output (not just hand-written fixtures). The only outstanding item is the Docker-gated integration test, which is correctly deferred to human verification.

---

_Verified: 2026-06-03_
_Verifier: Claude (gsd-verifier)_
