---
plan: 06-03
phase: 06-transport-seam-typed-models-core
status: complete
completed: 2026-05-28
requirements_addressed:
  - TYPED-03
  - TYPED-04
  - TYPED-05
---

# Plan 06-03: Wire Typed Dispatch — Summary

## What Was Built

Wired the typed-read dispatch into `OdooClient`, declared the `godoo[typed]` optional
extra, and added the CI-enforced isolation guard:

- `@overload` pairs on `OdooClient.read` and `OdooClient.search_read` (type[T] BEFORE str — D-03)
- Lazy `from godoo.client._pydantic_transform import derive_partial_model` inside the `hasattr` branch (D-04 / D-08)
- Friendly `OdooValidationError` with install hint when pydantic is absent (Open Q3)
- `[project.optional-dependencies] typed = ["pydantic>=2.13"]` in `packages/godoo-client/pyproject.toml`
- `uv.lock` regenerated and committed together (lockfile-discipline rule)
- Subprocess isolation guard (`test_typed_isolation.py`) — load-bearing TYPED-05 CI canary
- 7-test dispatch suite (`test_typed_dispatch.py`) covering str path, typed path, wire transforms, hasattr D-04 contract, and missing-pydantic friendly error

## Tasks Completed

1. **Task 1** — Added `@overload` pairs + dispatch + lazy import + friendly error to `OdooClient.read` and `search_read`. Used `cast("type[Any]", model)` → `typed_model` to resolve mypy's `str | type[T]` union. Removed `# noqa: PLC0415` (not an enabled ruff rule) and `OdooBaseModel` from the lazy import (unused — `typed_model.model_validate` works because all typed models are `OdooBaseModel` subclasses).

2. **Task 2** — Added `[project.optional-dependencies] typed = ["pydantic>=2.13"]` to `packages/godoo-client/pyproject.toml`. Fixed a TOML ordering bug (section header between key-value pairs made `classifiers` land under `[project.optional-dependencies]`) by rewriting the file with `Set-Content`. Ran `uv sync --extra typed`; `uv.lock` updated.

3. **Task 3** — Created `packages/godoo-client/tests/test_typed_isolation.py`: subprocess spawns a clean Python, runs `import godoo.client`, asserts `'pydantic' not in sys.modules`. 1 passed, mypy + ruff clean.

4. **Task 4** — Created `packages/godoo-client/tests/test_typed_dispatch.py`: 7 tests covering str-read, typed-read, wire-transform, str-search-read, typed-search-read, hasattr D-04 contract, and missing-pydantic friendly error (monkeypatched via `sys.modules["godoo.client._pydantic_transform"] = None`). All 7 passed, mypy + ruff clean.

## Key Files Modified / Created

- `packages/godoo-client/src/godoo/client/client.py` — MODIFIED (overloads + dispatch)
- `packages/godoo-client/pyproject.toml` — MODIFIED (`[project.optional-dependencies]`)
- `uv.lock` — REGENERATED
- `packages/godoo-client/tests/test_typed_isolation.py` — NEW
- `packages/godoo-client/tests/test_typed_dispatch.py` — NEW

## Deviations

- Used `cast("type[Any]", model)` + local `typed_model` alias instead of `# type: ignore[union-attr]` on `model.__odoo_model__` (mypy narrowed the union correctly inside the `hasattr` branch, making the ignore unused; `cast` is the correct pattern).
- Removed `OdooBaseModel` from the lazy import (plan listed it as documentation; ruff flagged it as unused F401). `derive_partial_model` alone is sufficient.
- `# noqa: PLC0415` removed — PLC0415 is a pylint code not in ruff's active rule set; ruff was flagging the noqa directive itself as RUF100.
- TOML ordering bug fixed by rewriting pyproject.toml via PowerShell `Set-Content` (the tool hooks that run `uv run python` failed on the broken intermediate state).
- `test_typed_dispatch.py` fixture uses `AsyncGenerator[OdooClient]` (UP043: removed default `None` arg) with `AsyncGenerator` in `TYPE_CHECKING` block (TC003). `type: ignore` comments on `auth_client.read(Marker, ...)` and `monkeypatch.setitem(...)` removed (mypy resolved both without error).

## Verification

- `uv run mypy --strict packages/godoo-client/src packages/godoo-client/tests/test_typed_dispatch.py packages/godoo-client/tests/test_typed_isolation.py` → no issues
- `uv run ruff check` on all modified/created files → all checks passed
- `uv run pytest packages/godoo-client/tests/test_typed_isolation.py` → 1 passed
- `uv run pytest packages/godoo-client/tests/test_typed_dispatch.py` → 7 passed
- `uv run pytest packages/ -m "not integration"` → 326 passed (318 pre-wave-3 + 8 new)
- `uv sync --frozen --extra typed` → succeeds (lockfile in sync)
- Inline isolation: `python -c "import godoo.client; assert 'pydantic' not in sys.modules"` → passes
- TYPED-04 regression: `test_client.py` all pass (str path unchanged)

## Self-Check: PASSED
