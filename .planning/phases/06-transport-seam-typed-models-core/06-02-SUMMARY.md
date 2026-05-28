---
plan: 06-02
phase: 06-transport-seam-typed-models-core
status: complete
completed: 2026-05-28
requirements_addressed:
  - TYPED-06
  - TYPED-07
---

# Plan 06-02: Typed Models Core — Summary

## What Was Built

Built the typed-models core: `godoo/client/typed.py` (stdlib-only `OdooModel` Protocol +
`Ref[T]` frozen generic dataclass) and `godoo/client/_pydantic_transform.py` (sole
pydantic-importing module — `OdooBaseModel` with `@model_validator(mode="before")` wire
transforms and `derive_partial_model` with module-level LRU cache). Unit tests for both.

## Tasks Completed

1. **Task 1** — Created `godoo/client/typed.py` with `OdooModel(Protocol)` (marker with
   `__odoo_model__: ClassVar[str]`) and `Ref[T]` frozen generic dataclass. Stdlib-only,
   zero third-party imports. Upgraded from `Generic[T]` to Python 3.14 `class Ref[T]:` syntax
   (ruff UP046).

2. **Task 2** — Created `godoo/client/_pydantic_transform.py`:
   - `OdooBaseModel(BaseModel)` with `@model_validator(mode="before")` applying four wire
     transforms: False→None (non-bool), m2o `[id, "Name"]`→`Ref`, ISO datetime→`datetime`,
     ISO date→`date`. D-02 boolean preservation handles both bare `bool` AND `bool | None`
     via `_annotation_is(annotation, bool)` helper (A2 guard).
   - `derive_partial_model(model, fields)` with `(id(model), frozenset(fields))` keyed cache.
   - `clear_partial_model_cache()` escape hatch.
   - No `__all__` (internal module per D-08).

3. **Task 3** — Created `tests/test_typed.py` (6 tests: Ref construction, frozen, equality,
   OdooModel marker, subscriptability, Protocol check) and `tests/test_pydantic_transform.py`
   (12 tests: all wire-transform behaviours, partial model, cache, validator inheritance).

## Key Files Created

- `packages/godoo-client/src/godoo/client/typed.py` — NEW
- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — NEW
- `packages/godoo-client/tests/test_typed.py` — NEW
- `packages/godoo-client/tests/test_pydantic_transform.py` — NEW

## Deviations

- `Ref[T]` uses Python 3.14 PEP 695 syntax `class Ref[T]:` instead of `Generic[T]` (ruff UP046).
- `Ref[_TestPartner]` self-reference in test model replaced with `Ref[object]` to avoid mypy
  forward-reference complexity in tests.
- `Optional[fi.annotation]` in `derive_partial_model` expressed as `fi.annotation | None`
  with a None guard (ruff UP045 + mypy safety).
- `test_derive_partial_model_inherits_validator` uses `.model_dump().get("name")` instead of
  direct attribute access (mypy `BaseModel` return type from `derive_partial_model`).

## Verification

- `uv run pytest packages/godoo-client/tests/test_typed.py` → 6 passed.
- `uv run pytest packages/godoo-client/tests/test_pydantic_transform.py` → 12 passed.
- `uv run pytest packages/ -m "not integration"` → 318 passed (300 pre-wave + 18 new).
- `uv run mypy --strict` on all 4 new files → no issues.
- `uv run ruff check` on all 4 new files → all checks passed.
- D-08 isolation invariant upheld: no other `godoo.client` submodule imports pydantic.

## Self-Check: PASSED
