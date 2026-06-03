---
phase: 11-codegen-metadata-typed-writes
reviewed: 2026-06-03T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - packages/godoo-introspection/src/godoo/introspection/type_mapper.py
  - packages/godoo-introspection/src/godoo/introspection/codegen.py
  - packages/godoo-introspection/tests/test_type_mapper.py
  - packages/godoo-client/src/godoo/client/_pydantic_transform.py
  - packages/godoo-client/src/godoo/client/client.py
  - packages/godoo-client/tests/test_serialize_for_write.py
  - packages/godoo-client/tests/test_typed_writes.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-06-03
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

The phase delivers two features: per-field write-metadata stamping in codegen
(`json_schema_extra` carrying `odoo_readonly` / `odoo_x2many`) and a typed write path
(`_serialize_for_write` + typed `@overload` create/write dispatch). The metadata
stamping logic is correct and well-tested. The readonly/computed exclusion rule (D-04)
is implemented faithfully and matches its tests. The Ref/date/datetime/None transforms
mirror the read side correctly.

However, two design-level defects make the typed write path unusable for its primary
intended workflow (read → modify → write) and unusable with actual codegen output:

1. The x2many guard raises whenever an x2many field is in `model_fields_set`. Reads
   populate `model_fields_set` for every field Odoo returns, so any read-modify-write of
   a model that has x2many fields raises `OdooValidationError` even when the caller
   never touched the relation. This is the exact roundtrip the integration test claims
   to exercise.
2. Codegen always emits `id: int` (required, no default), so a generated model cannot be
   instantiated for `create()` without supplying a fake id. The create tests sidestep
   this by using hand-written `id: int | None = None` fixtures, so the gap is invisible
   in CI.

The unit tests are real and assert behavior (the `_generate_async`-without-`await`
concern from the brief does not apply — that symbol lives in `cli.py`, which is not in
scope, and none of the reviewed tests call it). The integration test, by contrast, is
the only test that would exercise the two blockers above, and it is `@pytest.mark.integration`
(Docker-gated), so the defects never surface in the default unit run.

## Critical Issues

### CR-01: x2many guard breaks read-modify-write for any model with x2many fields

**File:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py:282-288`
**Issue:**
`_serialize_for_write` iterates `instance.model_fields_set` and raises
`OdooValidationError` for any field carrying `odoo_x2many=True`. When a record is read
through the typed path (`search_read(GeneratedClass, ...)` / `read(GeneratedClass, ...)`),
pydantic's `model_validate` adds *every* key present in the raw Odoo dict to
`model_fields_set` — including x2many fields, which Odoo returns by default as a list of
ids. The wire transform even has explicit handling to coerce `False`→`[]` for list-origin
fields (lines 138-150), confirming x2many values flow into the model on read.

Consequence: the canonical workflow — read a record, change one scalar field, call
`client.write(instance)` — raises `OdooValidationError("Field 'line_ids' is an x2many
relation ...")` even though the caller never touched `line_ids`. This is precisely the
roundtrip `test_codegen_read_write_roundtrip` (test_typed_writes.py:312) claims to
validate; it only passes if `res.lang` happens to expose no x2many field in its default
`search_read` projection. For `res.partner`, `account.move`, etc., the typed write path
is unusable.

The unit tests hide this because they only ever set x2many fields *explicitly*
(`WritePartner(id=1, line_ids=[1,2])`) — they never construct an instance via
`model_validate` with x2many data the way a real read does.

**Fix:** Only treat an x2many field as a hard error when its value actually changed, or
skip unmodified x2many fields the way readonly fields are skipped. The simplest correct
behavior is to exclude x2many fields from the payload by default (like readonly) rather
than raising, and document that x2many mutation requires the dict path with command
tuples:
```python
# WRITE-05: x2many cannot be written through the typed scalar path — skip, do not raise.
# Raising would break every read-modify-write of a model that has x2many relations,
# because reads stamp x2many fields into model_fields_set.
if extra_dict.get("odoo_x2many"):
    continue
```
If a hard error is genuinely desired, gate it on the value differing from the
default/last-read value rather than mere membership in `model_fields_set`, and add a unit
test that builds the instance via `model_validate({...,"line_ids":[1,2]})` and then writes
an unrelated scalar.

### CR-02: Generated models cannot be used with the typed `create()` path

**File:** `packages/godoo-introspection/src/godoo/introspection/codegen.py:224`
and `packages/godoo-client/src/godoo/client/client.py:520-547`
**Issue:**
Codegen unconditionally emits `id: int` — required, no default (line 224, plus the
docstring at client.py:101 documents "`id: int` always (no Optional, no default)").
A `create()` call constructs a *new* record that has no id yet, but a generated model
cannot be instantiated without one: `ResPartner(name="X")` raises a pydantic
`ValidationError` for the missing required `id`. The only way to call
`create(ResPartner(...))` is to pass a bogus id (`ResPartner(id=0, name="X")`), which then
lands in `model_fields_set` — though `_serialize_for_write` does correctly drop `id`
(line 270), so the bogus id is at least not sent.

The create tests do not catch this because every create fixture is hand-written with
`id: int | None = None` (`NullableIdPartner` line 70, `WritePartnerWithReadonly` line 261),
which is *not* the shape codegen produces. No test instantiates an actual codegen-emitted
class for `create()`. The integration test only exercises `write()`, never `create()`.

Consequence: the typed create path advertised by the `create(instance)` overload
(client.py:512) does not work with real codegen output.

**Fix:** Emit `id` as optional on generated models so instances can be built for create,
e.g.:
```python
# id field — optional so instances can be constructed for create();
# _serialize_for_write drops id from write/create payloads regardless.
lines.append("    id: int | None = None")
```
This still serializes correctly (id is dropped from the payload) and keeps reads sound
(Odoo always returns id). Add a create test that instantiates a class produced by
`CodeGenerator.generate(...)` (via `exec`, mirroring the integration test) to lock in the
contract.

## Warnings

### WR-01: x2many error message uses a literal-looking `{field: ...}` that is not interpolated

**File:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py:284-288`
**Issue:** The raised message contains `client.write(model, ids, {field: [(6, 0, [ids])]})`.
The `{field}` and `[ids]` here are inside a plain (non-f) string literal, so they print
verbatim. That is intentional as guidance, but `{field}` reads like a broken f-string
interpolation and may confuse a reader into thinking the field name was meant to be
substituted. Either make it an explicit placeholder (`<field>`, `<ids>`) or interpolate
the actual field name.
**Fix:**
```python
f"Field {field_name!r} is an x2many relation and cannot be written via the typed path. "
f"Use client.write(model, ids, {{{field_name!r}: [(6, 0, [<ids>])]}}) with command tuples instead."
```
(Becomes moot if CR-01 is resolved by skipping instead of raising.)

### WR-02: `None`→`False` coercion clears any explicitly-None scalar, including on create

**File:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py:297-300`
**Issue:** Any field explicitly set to `None` serializes to `False`. On the write path
this is the documented Odoo "clear field" convention and is fine. But the same serializer
backs `create()` (client.py:540). On create, sending `False` for unset-but-defaulted
scalar fields can override Odoo server-side defaults (e.g. a char field that Odoo would
default to a computed value gets forced to `False`/empty). Because only `model_fields_set`
fields are included, this only bites when the caller explicitly assigns `None`, but a
read-modify-create flow (clone a read instance, create a copy) would carry many `None`s
that then wipe server defaults. Consider documenting that `None` means "clear" on both
paths, or distinguishing create (omit) from write (clear).
**Fix:** At minimum document the create-path semantics in the `create` docstring and in
`_serialize_for_write`'s docstring; ideally pass a `mode` so create omits `None` fields
rather than forcing `False`.

### WR-03: Typed `write()` guards `model.id is None` but generated `id: int` can never be None

**File:** `packages/godoo-client/src/godoo/client/client.py:570-573`
**Issue:** The guard `if model.id is None:` is dead for codegen-emitted classes, whose
`id: int` is required and non-optional (CR-02). It only fires for hand-written models with
optional id. The guard is correct defensively, but its only test
(`test_typed_write_id_none_raises`, test_typed_writes.py:230) again relies on the
hand-written `NullableIdPartner`, not codegen output, so it does not validate the path
that ships. Once CR-02 makes id optional on generated models, this guard becomes the real
safety net — keep it, and add a test using an actual generated class.
**Fix:** No code change required for correctness; add a codegen-backed test once CR-02 is
addressed so the guard is exercised against the shipped model shape.

### WR-04: `test_no_set_fields_returns_empty_dict` asserts almost nothing

**File:** `packages/godoo-client/tests/test_serialize_for_write.py:54-62`
**Issue:** The test's only assertion is `assert isinstance(payload, dict)`. The comment
acknowledges the behavior "depends on pydantic version; either case is valid," so the
test deliberately avoids asserting the payload contents. This is a non-assertion: it
passes regardless of whether the serializer correctly drops `id` or accidentally includes
other fields. It provides essentially no regression protection.
**Fix:** Pin the behavior for the pinned pydantic version. Either assert
`payload == {}` (id must always be dropped) or construct the instance in a way that makes
`model_fields_set` deterministic and assert the exact resulting keys.

### WR-05: `derive_partial_model` embeds `abs(hash(field_key))` in the class name — collisions possible

**File:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py:228-232`
**Issue:** The derived model is named
`f"{model.__name__}__partial__{abs(hash(field_key))}"`. `abs()` of a Python hash can
collide across different `frozenset(fields)` values (and hash randomization makes the name
non-deterministic across processes). The *cache* is keyed correctly on `frozenset(fields)`,
so behavior is sound, but two distinct partials of the same base model can receive the
identical generated class name, which surfaces as confusing `__name__`/repr and harms
debuggability of validation errors (the name is what users see in `OdooValidationError`
messages from `_validate_typed`).
**Fix:** Build a deterministic, collision-free suffix from the sorted field names, e.g.
`"__partial__" + "_".join(sorted(field_key))` (truncate/hash only if length is a concern),
so the name is stable and unique per field set.

## Info

### IN-01: Two loggers share the same name across modules

**File:** `packages/godoo-introspection/src/godoo/introspection/type_mapper.py:13` and
`packages/godoo-introspection/src/godoo/introspection/codegen.py:17`
**Issue:** Both modules call `logging.getLogger("godoo_introspection.codegen")`. The
type_mapper logger therefore reports under the codegen module's name, which makes warnings
(e.g. the unknown-ttype fallback at type_mapper.py:120) appear to originate from codegen.
The test `test_unknown_ttype_logs_warning` works precisely because it filters on
`"godoo_introspection.codegen"`, masking the mislabeling.
**Fix:** Use `logging.getLogger("godoo_introspection.type_mapper")` in `type_mapper.py`.

### IN-02: x2many `default_factory=list` plus `repr(extra)` produces unstable dict ordering in generated source

**File:** `packages/godoo-introspection/src/godoo/introspection/codegen.py:143-149`
**Issue:** The metadata dict is emitted with `f"...json_schema_extra={extra!r}"`. `extra`
is built by insertion order (`odoo_readonly` then `odoo_x2many`), so output is currently
stable, but relying on `repr(dict)` for codegen output is fragile — any future reordering
of the insertion in `type_mapper.py` silently changes generated file bytes and churns
diffs. Consider sorting keys when rendering for deterministic output.
**Fix:** `json_schema_extra={dict(sorted(extra.items()))!r}` or build the literal explicitly.

### IN-03: Integration test leaves a dangling write if assertions fail mid-test

**File:** `packages/godoo-client/tests/test_typed_writes.py:363-381`
**Issue:** `test_codegen_read_write_roundtrip` mutates a live `res.lang` record and only
restores the original name at the very end (lines 379-381). If any assertion between the
write and the restore fails (e.g. line 377), the restore never runs and the container is
left dirty. With `snapshot=False` and a session-scoped harness this could leak state into
other tests.
**Fix:** Wrap the mutate/assert/restore block in `try/finally`, restoring the original
name in `finally`.

---

_Reviewed: 2026-06-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
