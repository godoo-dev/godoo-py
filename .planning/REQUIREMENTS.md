# Requirements: godoo-py — Milestone v1.1 Typed Models & Browser Reach

**Defined:** 2026-05-27
**Core Value:** The Python family member reaches feature parity with the TypeScript core-3 libraries — and now sharpens developer ergonomics with instance-derived typed models while de-risking browser reach.

## v1.1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Packaging

- [x] **PKG-01**: Workspace directory `packages/godoo` is renamed to `packages/godoo-client` (via `git mv`); the import namespace stays `godoo.*` (PEP 420), so no consumer import breaks
- [x] **PKG-02**: All path references are updated and CI stays green — root `pyproject.toml` (`mypy_path`, `[tool.semantic_release] version_toml`, `build_command`), `.github/workflows/test.yml` mypy invocation, and `mkdocs.yml` mkdocstrings paths
- [x] **PKG-03**: A CI guard test asserts the PEP 420 namespace remains intact after the rename (`godoo.__file__ is None`; no stray `__init__.py`)

### Typed Models

- [ ] **TYPED-01**: A developer can generate a Pydantic model package from their live Odoo instance via a `godoo-introspection` CLI command (output path is the consuming project's choice)
- [ ] **TYPED-02**: Generated models reflect instance-specific schema — custom fields, selection values emitted as `Literal`, relational fields typed as `Ref[Model]` (many2one) / `list[int]` (one2many/many2many); no nested fetch
- [x] **TYPED-03**: A developer can call `client.read(ModelClass, ids)` (and `search_read(ModelClass, ...)`) and receive validated, transformed `list[ModelClass]` instances
- [x] **TYPED-04**: The raw string-keyed path (`client.read("res.partner", ids)`) is unchanged and still returns `list[dict[str, Any]]`
- [x] **TYPED-05**: Typed support is opt-in via the `godoo[typed]` extra; the default install stays httpx-only, enforced by a CI test asserting `import godoo` pulls in no pydantic
- [x] **TYPED-06**: A bidirectional wire transform handles Odoo's quirks declaratively — empty `False` → `None`, many2one `[id, "Name"]` → `Ref`, date/datetime strings → `date`/`datetime`, selection → `Literal`
- [x] **TYPED-07**: `Ref[Model]` and the model dispatch `Protocol` (`__odoo_model__`) live in a stdlib-only `godoo.client.typed` module, importable without pydantic; runtime dispatch duck-types (`hasattr`), never `isinstance(BaseModel)`

### Browser Reach

- [x] **BROWSER-01**: A `Transport` `Protocol` plus a `transport_factory` hook on `OdooClientConfig` allows an alternative transport implementation to be injected without changing core (additive infra; ships regardless of the spike verdict)
- [ ] **BROWSER-02**: A spike runs an actual in-browser (Pyodide) HTTP call **over HTTPS** against a real TLS-terminated Odoo endpoint — exercising browser TLS-via-fetch, CORS, and mixed-content constraints (plain HTTP / localhost does not satisfy this) — and produces a written verdict on whether stock httpx works or a custom fetch-backed transport is required
- [ ] **BROWSER-03**: The spike delivers a Python-floor recommendation (drop `requires-python` to `>=3.12` for a browser build, or defer until Pyodide ships CPython ≥3.14) and an explicit go/no-go decision for committing browser support; a "go" with required breaking changes escalates the milestone to v2.0

## Open Decisions (settle at plan/discuss time — do not block scope)

| ID | Decision | Options | Notes |
|----|----------|---------|-------|
| OD-1 | Partial-read strategy when a model class is passed with `fields=[...]` | All-Optional generated fields · `model_construct` (skip validation) · force partial reads onto the raw path | Precision vs ergonomics. Research leans All-Optional; affects TYPED-02/03 codegen. Settle before Phase 6 planning. |
| OD-2 | Boolean `False`-coercion exception in the wire transform | Emit boolean fields as plain `bool` so the validator skips them · inspect `FieldMeta` at runtime | Affects TYPED-06; "emit as plain bool" is the simpler candidate. Settle before Phase 6 planning. |
| OD-3 | httpx-in-Pyodide verdict | Stock httpx via Fetch adapter · custom `AsyncTransport` via `pyfetch` · replace httpx in a browser variant | Researchers conflicted; BROWSER-02 resolves it empirically. Does not block Phases 5-7. |

## Future Requirements

Deferred beyond v1.1; tracked, not in this roadmap.

### Browser (conditional on BROWSER-03 = go)

- **BROWSER-F1**: Ship a browser-compatible client build / `godoo[browser]` extra with the spike-validated transport
- **BROWSER-F2**: Relax the Python floor to support the Pyodide runtime (overlaps deferred COMPAT-01)

### Typed Models

- **TYPED-F1**: Nested relational models (resolve `parent_id`/`child_ids` to full nested instances) — explicitly deferred; v1.1 uses `Ref[Model]`/`list[int]` only
- **TYPED-F2**: Typed write/create paths (`client.create(ModelInstance)`) — v1.1 covers typed reads only

## Out of Scope

| Feature | Reason |
|---------|--------|
| Changing the import namespace away from `godoo.*` | Would break every existing user; the dist rename does not require it (PEP 420 decouples dist name from import path) |
| Nested relational fetch in generated models | Balloons codegen and fetch semantics (multi-round-trip); `Ref[Model]`/`list[int]` is the v1.1 line |
| Pydantic for core (non-typed) types | The "dataclasses, not Pydantic" convention holds for core; the typed layer is the deliberate, isolated exception behind an extra |
| `godoo-testcontainers` in the browser | Docker-bound by construction; out of any Pyodide work |
| Committing a browser build this milestone | Gated behind the BROWSER-02 spike verdict; only the seam + spike are committed |

## Traceability

Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | Phase 5 | Complete |
| PKG-02 | Phase 5 | Complete |
| PKG-03 | Phase 5 | Complete |
| TYPED-01 | Phase 7 | Pending |
| TYPED-02 | Phase 7 | Pending |
| TYPED-03 | Phase 6 | Complete |
| TYPED-04 | Phase 6 | Complete |
| TYPED-05 | Phase 6 | Complete |
| TYPED-06 | Phase 6 | Complete |
| TYPED-07 | Phase 6 | Complete |
| BROWSER-01 | Phase 6 | Complete |
| BROWSER-02 | Phase 8 | Pending |
| BROWSER-03 | Phase 8 | Pending |

**Coverage:**
- v1.1 requirements: 13 total
- Mapped to phases: 13 (Phase 5: 3, Phase 6: 6, Phase 7: 2, Phase 8: 2)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-27*
*Last updated: 2026-05-27 — traceability filled after roadmap creation*
