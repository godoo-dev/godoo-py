---
phase: 06-transport-seam-typed-models-core
type: code-review
depth: standard
status: clean
reviewed: 2026-05-28
reviewer: inline (subagent dispatch unavailable in this orchestrator thread)
files_reviewed:
  - packages/godoo-client/src/godoo/client/rpc/protocol.py
  - packages/godoo-client/src/godoo/client/rpc/__init__.py
  - packages/godoo-client/src/godoo/client/client.py
  - packages/godoo-client/src/godoo/client/typed.py
  - packages/godoo-client/src/godoo/client/_pydantic_transform.py
  - packages/godoo-client/tests/test_transport_protocol.py
  - packages/godoo-client/tests/test_typed.py
  - packages/godoo-client/tests/test_pydantic_transform.py
  - packages/godoo-client/tests/test_typed_isolation.py
  - packages/godoo-client/tests/test_typed_dispatch.py
  - packages/godoo-client/pyproject.toml
findings:
  critical: 0
  warning: 0
  info: 2
---

# Phase 06 — Code Review

## Scope

Reviewed all source and test files added or modified by Phase 6 (Transport Seam & Typed Models Core), comprising:

- 5 source files (`rpc/protocol.py`, `rpc/__init__.py`, `client.py`, `typed.py`, `_pydantic_transform.py`)
- 5 test files (`test_transport_protocol.py`, `test_typed.py`, `test_pydantic_transform.py`, `test_typed_isolation.py`, `test_typed_dispatch.py`)
- 1 config file (`pyproject.toml` — `[project.optional-dependencies]` table added)

Depth: standard. Reviewer: inline (the orchestrator thread does not expose the `Task`/`Agent` tool needed to spawn `gsd-code-reviewer`; this review is a best-effort substitute and is advisory only — non-blocking per workflow contract).

## Critical findings

None.

## Warning findings

None.

## Info findings

### I-1 — Module-level `__partial_model_cache` is unbounded (documented limitation)

**File:** `packages/godoo-client/src/godoo/client/_pydantic_transform.py:19`

`_partial_model_cache: dict[tuple[int, frozenset[str]], type[BaseModel]] = {}` accumulates one entry per `(model_class, field_subset)` pair seen at runtime. In a long-lived process that calls `client.read(M, fields=[...])` with many different `fields=...` lists, this cache grows monotonically.

Acknowledged in code (docstring on `derive_partial_model` and on `clear_partial_model_cache`) and in `.planning/phases/06-transport-seam-typed-models-core/06-RESEARCH.md` Pitfall 4. `clear_partial_model_cache()` is the documented escape hatch.

**Disposition:** accept. Cardinality is bounded by `models x distinct_field_subsets`, which in practice is small. Trade-off favours hit-rate over memory.

### I-2 — `OdooBaseModel` import in `client.py` lazy block was removed as unused

**File:** `packages/godoo-client/src/godoo/client/client.py` (read + search_read)

The original plan (06-03 §4) listed `OdooBaseModel` alongside `derive_partial_model` in the lazy import "as documentation". Ruff F401 flagged it as unused, so it was removed during execution. The dispatch still works correctly because `typed_model.model_validate(...)` resolves on the model class itself (which inherits from `OdooBaseModel`), so the import was never load-bearing — only nominal.

**Disposition:** accept. Documented in `06-03-SUMMARY.md` §Deviations.

## Quality gate evidence

- `uv run mypy --strict packages/godoo-client/src` → clean (57 source files)
- `uv run mypy --strict` on all 5 new test files → clean
- `uv run ruff check` on all changed files → clean
- `uv run pytest packages/ -m "not integration"` → 326 passed
- `uv run python -c "import godoo.client; assert 'pydantic' not in sys.modules"` → passes (inline isolation)
- Subprocess isolation guard (`test_typed_isolation.py`) → passes (load-bearing TYPED-05 evidence)
- `uv sync --frozen --extra typed` → succeeds (lockfile in sync)

## Security review

- **No secrets** added or referenced. No credentials in tests; fixtures use literal strings (`"admin"/"admin"` against `http://odoo.test`).
- **Supply chain:** `pydantic>=2.13` is the canonical Pydantic package (MIT, 9-year history). Documented in `06-RESEARCH.md` Package Legitimacy Audit; no human-verify checkpoint required.
- **Trust boundary:** dispatch keys on `hasattr(model, "__odoo_model__")`. A malicious user-class with this attribute would route to the typed branch and fail at `model_validate` — no privilege escalation, no library-state corruption. Documented threat T-06-09 in 06-03-PLAN, pinned by `test_dispatch_via_hasattr_takes_typed_branch`.
- **Isolation guarantee:** subprocess test enforces that `import godoo.client` does not load pydantic in a clean process — the supply-chain attack surface of the default install is unchanged from v1.0.

## Verdict

**clean** — no critical or warning findings. Two info items are pre-acknowledged limitations with documented escape hatches.

## Next steps

Proceed to regression gate and `verify_phase_goal`.
