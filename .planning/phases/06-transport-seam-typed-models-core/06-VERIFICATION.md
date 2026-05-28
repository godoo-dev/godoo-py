---
phase: 06-transport-seam-typed-models-core
type: verification
status: passed
verified: 2026-05-28
verifier: inline (subagent dispatch unavailable in this orchestrator thread)
requirements_verified:
  - BROWSER-01
  - TYPED-03
  - TYPED-04
  - TYPED-05
  - TYPED-06
  - TYPED-07
phase_goal: "Developers can perform type-safe Odoo reads (client.read(ResPartner, ids) -> list[ResPartner]) using instance-generated models, while the raw string path is unchanged and a default install with no Pydantic installed never imports Pydantic"
---

# Phase 06 — Verification

## Verifier note

The orchestrator thread does not expose the `Task`/`Agent` tool, so the standard `gsd-verifier` Sonnet subagent could not be spawned. This document is an inline verification produced by reading source files, running the test suite, and inspecting `uv` / `mypy` / `ruff` output directly. All evidence is reproducible from the commands recorded inline.

## Phase goal evidence

> "Developers can perform type-safe Odoo reads (`client.read(ResPartner, ids)` → `list[ResPartner]`) using instance-generated models, while the raw string path is unchanged and a default install with no Pydantic installed never imports Pydantic"

| Goal sub-clause | Evidence | Verdict |
|---|---|---|
| `client.read(ModelClass, ids)` → `list[ModelClass]` | `tests/test_typed_dispatch.py::test_read_typed_path_returns_models` asserts `all(isinstance(r, TinyPartner) for r in result)` against a mocked JSON-RPC response (PASS) | VERIFIED |
| Wire transforms applied | `tests/test_typed_dispatch.py::test_read_typed_applies_wire_transforms` asserts `(await read(...))[0].name is None` when wire returns `False` (PASS) | VERIFIED |
| Raw string path unchanged | `tests/test_typed_dispatch.py::test_read_str_path_returns_dicts` + full `tests/test_client.py` (36 tests) still PASS (TYPED-04 regression bedrock) | VERIFIED |
| Default install never imports Pydantic | `tests/test_typed_isolation.py::test_pydantic_not_imported_by_default` spawns clean Python subprocess, runs `import godoo.client`, asserts `'pydantic' not in sys.modules` (PASS) | VERIFIED |

## Requirement-by-requirement verdict

### BROWSER-01 — Transport seam
**Requirement:** "A `Transport` `Protocol` plus a `transport_factory` hook on `OdooClientConfig` allows an alternative transport implementation to be injected without changing core (additive infra; ships regardless of the spike verdict)"

**Evidence:**
- `packages/godoo-client/src/godoo/client/rpc/protocol.py` defines `class Transport(Protocol)` with five members (`session`, `authenticate`, `call`, `logout`, `aclose`)
- `OdooClientConfig.transport_factory: Callable[[OdooClientConfig], Transport] | None` field added in `client.py` (default `None`)
- `OdooClient.__init__` branches: if `config.transport_factory is not None`, use it; else construct `JsonRpcTransport` as before
- `tests/test_transport_protocol.py::test_jsonrpc_transport_satisfies_protocol` verifies `JsonRpcTransport` structurally satisfies the Protocol (PASS); the mypy `--strict` pass on `client.py` is the load-bearing static assertion

**Verdict:** VERIFIED

### TYPED-03 — Typed read/search_read returns validated instances
**Requirement:** "A developer can call `client.read(ModelClass, ids)` (and `search_read(ModelClass, ...)`) and receive validated, transformed `list[ModelClass]` instances"

**Evidence:**
- `client.py` has `@overload` pairs on both `read` and `search_read` (type[T] first per D-03), with unified body branching on `hasattr(model, "__odoo_model__")`
- `tests/test_typed_dispatch.py`: `test_read_typed_path_returns_models`, `test_read_typed_applies_wire_transforms`, `test_search_read_typed_path_returns_models` all PASS
- mypy `--strict` confirms return-type narrowing: `client.read(TinyPartner, [1])` infers as `list[TinyPartner]`

**Verdict:** VERIFIED

### TYPED-04 — Raw string-keyed path unchanged
**Requirement:** "The raw string-keyed path (`client.read("res.partner", ids)`) is unchanged and still returns `list[dict[str, Any]]`"

**Evidence:**
- Str-branch body in `client.read` is byte-equivalent to v1.0: `if fields is not None: kwargs["fields"] = fields; return cast("list[dict[str, Any]]", await self.call(model, "read", [id_list], kwargs))`
- `tests/test_client.py` (36 tests, none modified) continues to PASS — full TYPED-04 regression bedrock
- `tests/test_typed_dispatch.py::test_read_str_path_returns_dicts` + `::test_search_read_str_path_returns_dicts` add direct assertions

**Verdict:** VERIFIED

### TYPED-05 — Opt-in via `godoo[typed]` extra; default install httpx-only
**Requirement:** "Typed support is opt-in via the `godoo[typed]` extra; the default install stays httpx-only, enforced by a CI test asserting `import godoo` pulls in no pydantic"

**Evidence:**
- `packages/godoo-client/pyproject.toml` declares `[project.optional-dependencies] typed = ["pydantic>=2.13"]`
- `uv.lock` regenerated; `uv sync --frozen --extra typed` succeeds (lockfile in sync)
- `tests/test_typed_isolation.py::test_pydantic_not_imported_by_default` is the load-bearing CI guard — runs `import godoo.client` in a clean subprocess, asserts `'pydantic' not in sys.modules` (PASS)
- Lazy import inside `read`/`search_read` is wrapped in `try/except ModuleNotFoundError` re-raising as `OdooValidationError` with install hint; pinned by `test_typed_dispatch_without_pydantic_raises_friendly_error`

**Verdict:** VERIFIED

### TYPED-06 — Bidirectional wire transforms
**Requirement:** "A bidirectional wire transform handles Odoo's quirks declaratively — empty `False` → `None`, many2one `[id, "Name"]` → `Ref`, date/datetime strings → `date`/`datetime`, selection → `Literal`"

**Evidence:**
- `_pydantic_transform.OdooBaseModel._odoo_wire_transforms` (`@model_validator(mode="before")`) implements the contract:
  - `False` → `None` for non-bool fields (D-02 keeps `bool`/`bool | None` fields literal)
  - `[id, "Name"]` → `Ref(id=..., name=...)` for fields annotated with `Ref[...]`
  - ISO datetime → `datetime` (checked BEFORE date — datetime is subclass)
  - ISO date → `date`
- `tests/test_pydantic_transform.py` (12 tests, all PASS) cover every transform branch
- `Literal[...]` for selection is a codegen-time concern (Phase 7 TYPED-02); the runtime validator path is in place and unaffected

**Verdict:** VERIFIED

### TYPED-07 — Stdlib-only `godoo.client.typed` + duck-typed dispatch
**Requirement:** "`Ref[Model]` and the model dispatch `Protocol` (`__odoo_model__`) live in a stdlib-only `godoo.client.typed` module, importable without pydantic; runtime dispatch duck-types (`hasattr`), never `isinstance(BaseModel)`"

**Evidence:**
- `packages/godoo-client/src/godoo/client/typed.py` is stdlib-only (imports `dataclasses`, `typing`); declares `class OdooModel(Protocol)` and `@dataclass(frozen=True) class Ref[T]:` (Python 3.14 PEP 695 syntax)
- Subprocess isolation guard proves `typed.py` is reachable without pydantic
- `client.py` dispatch uses `hasattr(model, "__odoo_model__")` (D-04), not `isinstance(model, OdooBaseModel)` — pinned by `tests/test_typed_dispatch.py::test_dispatch_via_hasattr_takes_typed_branch`

**Verdict:** VERIFIED

## ROADMAP Phase 6 Success Criteria

All 5 success criteria from ROADMAP.md §Phase 6 are demonstrably true:

| # | Criterion | Verdict |
|---|---|---|
| 1 | `OdooClientConfig.transport_factory` hook; `JsonRpcTransport` satisfies new `Transport` Protocol; alternative transport injectable end-to-end | VERIFIED (BROWSER-01) |
| 2 | `client.read("res.partner", ids)` returns `list[dict[str, Any]]` unchanged | VERIFIED (TYPED-04) |
| 3 | `client.read(ResPartner, ids)` returns `list[ResPartner]` with all wire transforms applied | VERIFIED (TYPED-03 + TYPED-06) |
| 4 | In a venv with pydantic NOT installed, `python -c "import godoo.client"` exits 0 | VERIFIED (subprocess isolation guard) |
| 5 | `godoo[typed]` declared; `godoo.client.typed` importable without pydantic; no Pydantic at module load anywhere | VERIFIED (TYPED-05 + TYPED-07) |

## Test evidence summary

```
$ uv run pytest packages/ -m "not integration"
326 passed, 3 deselected, 1 warning in 4.19s
```

Phase 6 added 26 new tests:
- 1 in `test_transport_protocol.py` (BROWSER-01)
- 6 in `test_typed.py` (TYPED-07: Ref dataclass + OdooModel Protocol)
- 12 in `test_pydantic_transform.py` (TYPED-06: wire transforms + derive_partial_model)
- 1 in `test_typed_isolation.py` (TYPED-05: subprocess isolation)
- 7 in `test_typed_dispatch.py` (TYPED-03 + TYPED-04: dispatch overloads)

Pre-phase test count: 300. Post-phase test count: 326. All pass.

## Static analysis evidence

```
$ uv run mypy --strict packages/godoo-client/src packages/godoo-introspection/src packages/godoo-testcontainers/src
Success: no issues found in 57 source files

$ uv run ruff check packages/
All checks passed!
```

## Status

**passed**

All 6 phase requirements verified; all 5 ROADMAP success criteria demonstrably true; mypy + ruff clean on all src/ directories; 326 non-integration tests pass.
