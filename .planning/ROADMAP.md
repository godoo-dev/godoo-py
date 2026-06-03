# Roadmap: godoo-py

## Milestones

- ✅ **v1.0 Parity & Release** — Phases 1-4.1 (shipped 2026-05-22) — full archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Typed Models & Browser Reach** — Phases 5-8 (shipped 2026-06-02) — full archive: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Typed Relations, Writes & Error Surface** — Phases 9-12 (shipped 2026-06-03) — full archive: [milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)

## Phases

<details>
<summary>✅ v1.0 Parity & Release (Phases 1-4.1) — SHIPPED 2026-05-22</summary>

- [x] Phase 1: Client Parity (5/5 plans) — completed 2026-05-19
- [x] Phase 2: Introspection (2/2 plans) — completed 2026-05-21
- [x] Phase 3: Testcontainers Parity (3/3 plans) — completed 2026-05-22
- [x] Phase 4: Release (3/3 plans) — completed 2026-05-22
- [x] Phase 4.1: Package READMEs (1/1 plan, INSERTED) — completed 2026-05-22

Close all Python parity gaps against the TypeScript core-3 libraries, build
`godoo-introspection` from scratch, and ship all three packages to PyPI under the
`godoo-dev/godoo-py` GitHub org. Full phase detail, goals, and success criteria are
preserved in [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md).

</details>

<details>
<summary>✅ v1.1 Typed Models & Browser Reach (Phases 5-8) — SHIPPED 2026-06-02</summary>

- [x] Phase 5: Directory Rename (2/2 plans) — completed 2026-05-28
- [x] Phase 6: Transport Seam & Typed Models Core (3/3 plans) — completed 2026-05-28
- [x] Phase 7: Pydantic CLI Generator (2/2 plans) — completed 2026-06-01
- [x] Phase 8: Pyodide Spike (4/4 plans) — completed 2026-06-02

Instance-derived Pydantic typed models with a typed-read dispatch layer (`client.read(ModelClass, ids)` → `list[ModelClass]`), the `packages/godoo`→`packages/godoo-client` directory rename (PEP 420 namespace preserved), a pluggable transport seam (`Transport` Protocol + `transport_factory` hook), and an empirically grounded Pyodide/browser go/no-go verdict (ADR-0001: GO, deferred to v2.0 pending Pyodide CPython ≥3.14). The Pydantic generator replaces the v1.0 TypedDict generator (breaking, changelog-noted). Full phase detail preserved in [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md).

</details>

<details>
<summary>✅ v1.2 Typed Relations, Writes & Error Surface (Phases 9-12) — SHIPPED 2026-06-03</summary>

- [x] Phase 9: Structured Error Surface (1/1 plan) — completed 2026-06-02
- [x] Phase 10: Typed Relation Resolution (2/2 plans) — completed 2026-06-02
- [x] Phase 11: Codegen Metadata + Typed Writes (3/3 plans) — completed 2026-06-03
- [x] Phase 12: Tech Debt Close-out (3/3 plans) — completed 2026-06-03

Completed the typed-models story: `Ref[T]`-driven single-level relation resolution (`client.read(ref)` / `read(list[Ref])`, batched per target model) and typed write/create paths (`client.write(instance)` / `create(instance)` sending only explicitly-set, writable fields with reverse wire transforms). Restructured the RPC error surface (`OdooRpcError` structured fields, traceback/path stripping, `.data`→`.raw` breaking rename). Closed backlog 999.3/999.4 test-coverage gaps and cleared four tech-debt items (Node 24 CI pins + gitleaks scan, spike password removal, RuntimeWarning noise, complete snapshot key). Full phase detail preserved in [milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md).

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Client Parity | v1.0 | 5/5 | Complete | 2026-05-19 |
| 2. Introspection | v1.0 | 2/2 | Complete | 2026-05-21 |
| 3. Testcontainers Parity | v1.0 | 3/3 | Complete | 2026-05-22 |
| 4. Release | v1.0 | 3/3 | Complete | 2026-05-22 |
| 4.1. Package READMEs | v1.0 | 1/1 | Complete | 2026-05-22 |
| 5. Directory Rename | v1.1 | 2/2 | Complete | 2026-05-28 |
| 6. Transport Seam & Typed Models Core | v1.1 | 3/3 | Complete | 2026-05-28 |
| 7. Pydantic CLI Generator | v1.1 | 2/2 | Complete | 2026-06-01 |
| 8. Pyodide Spike | v1.1 | 4/4 | Complete | 2026-06-02 |
| 9. Structured Error Surface | v1.2 | 1/1 | Complete | 2026-06-02 |
| 10. Typed Relation Resolution | v1.2 | 2/2 | Complete | 2026-06-02 |
| 11. Codegen Metadata + Typed Writes | v1.2 | 3/3 | Complete | 2026-06-03 |
| 12. Tech Debt Close-out | v1.2 | 3/3 | Complete | 2026-06-03 |

## Backlog

### Phase 999.1: Rename packages/godoo to packages/godoo-client for dist consistency (SUPERSEDED)

> **Superseded by Phase 5** (Directory Rename) in milestone v1.1. Backlog item promoted to active roadmap.

### Phase 999.2: Update godoo-testcontainers PostgreSQL to v18 (latest stable) (BACKLOG)

**Goal:** [Captured for future planning] Bump the PostgreSQL image pinned by `godoo-testcontainers` to v18 (currently the latest stable). Validate that the Odoo versions exercised in integration tests (17/18/19) start cleanly against PG 18; update any version pin in `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` and related fixtures.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.3: Codegen→typed-read round-trip test (PROMOTED to Phase 11 / TEST-01)

> **Promoted to Phase 11** (Codegen Metadata + Typed Writes) as TEST-01 in milestone v1.2.

### Phase 999.4: Wire-transforms-through-dispatch test (PROMOTED to Phase 10 / TEST-02)

> **Promoted to Phase 10** (Typed Relation Resolution) as TEST-02 in milestone v1.2.

### Phase 999.5: Typed write/read robustness — fail-fast + silent-drop fixes (BACKLOG)

**Goal:** Close correctness gaps in the v1.2 typed write/read dispatch surfaced by code review — restore fail-fast behavior lost when the typed overloads widened required params to `Any = None`, and fix a silent x2many write drop.
**Requirements:** TBD
**Source:** v1.2 post-milestone code review (2026-06-03)
**Findings:**

- **[HIGH] Silent x2many write loss via `model_copy`** — `packages/godoo-client/src/godoo/client/_pydantic_transform.py:376`. `instance.model_copy(update={'line_ids': [...]})` bypasses `model_post_init` and `__setattr__`, so `_user_set_fields` stays stale; `_serialize_for_write` then omits the x2many instead of raising the documented error — the user's write is silently dropped. Fix: reseed `_user_set_fields` on copy, or fall back to `model_fields_set` when `_user_set_fields` is empty.
- **[MED] `create()`/`write()` ship `None` to Odoo when `values` omitted** — `client.py:551,589`. The dict path sends `[None]` / `[[id], None]` to the RPC instead of failing locally. Fix: validate `values` is present on the non-typed dict path before calling.
- **[MED] `read()` returns `[]` when `ids` omitted** — `client.py:292`. The str path coerces missing `ids` to `[]` and silently returns an empty result. Fix: raise on missing ids in the non-typed path.
- **[LOW] Class-vs-instance guard** — `client.py:574`. Passing a model *class* (not instance) to `write`/`create` passes the `hasattr(__odoo_model__)` guard and fails with a bare AttributeError. Fix: require an instance; raise `OdooValidationError` otherwise.

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.6: RPC error-surface hardening (BACKLOG)

**Goal:** Close gaps in the Phase 9 structured error surface found in code review — privacy (server-path leak) and message-extraction robustness.
**Requirements:** TBD
**Source:** v1.2 post-milestone code review (2026-06-03)
**Findings:**

- **[MED] Bare server paths leak** — `packages/godoo-client/src/godoo/client/errors.py:11`. The path-strip regexes only match the `File "..."` traceback format; bare absolute paths embedded in `data['message']` (now surfaced by the new `__str__`) pass through to `str(exc)` and `to_json()['human_message']`. Partial regression of ERR-02/ERR-04. Fix: strip bare absolute paths too, or separate the debug payload from the display string at parse time.
- **[MED] `arguments`-as-string → first character** — `errors.py:28`. `_extract_human_message` indexes `args[0]` guarded only by truthiness; when `arguments` is a plain string, `human_message` becomes its first character. Fix: `isinstance(args, (list, tuple))` before indexing.
- **[MED] `to_json()` 'details' inconsistency** — `errors.py:104`. `OdooRpcError.to_json()` dropped the `details` key while `OdooError`/`OdooSafetyError` still emit it → KeyError for consumers reading `result['details']`, plus a non-uniform shape across one hierarchy. Fix: make the key set consistent across the hierarchy.
- **[LOW] No actionable message for empty-message faults** — `errors.py:28`. A psycopg2 IntegrityError relayed with `message=''`/`arguments=[]` yields `human_message=None`; the constraint detail survives only in `raw['debug']`, which is excluded from `to_json()`. Fix: derive a safe fallback (e.g. from `data['name']`) or expose a sanitized constraint summary.

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.7: Typed relation resolution edge cases (BACKLOG)

**Goal:** Harden `Ref[T]` resolution against malformed inputs and unresolved annotations — deferred hardening from the v1.2 milestone audit, now confirmed reachable by code review.
**Requirements:** TBD
**Source:** v1.2 post-milestone code review (2026-06-03) + v1.2 milestone audit
**Findings:**

- **[MED] Mixed-list Ref crashes with AttributeError** — `client.py:257`. `read(list[Ref])` enters the Ref branch on `model[0]` only; a heterogeneous list (`[Ref(...), 42]`) reaches `(42)._target_cls` → bare AttributeError instead of `OdooValidationError`. Fix: validate every element is a `Ref` before `_target_cls` access.
- **[MED] ForwardRef target unresolvable** — `packages/godoo-client/src/godoo/client/_pydantic_transform.py:77`. `_ref_target_class` uses `isinstance(arg, type)`; an unresolved `ForwardRef` in multi-file generated models (one-file-per-model codegen with cross-module `Ref[T]` under `from __future__ import annotations`, no `model_rebuild()`) stamps `_target_cls=None`, making the Ref permanently unresolvable. Fix: resolve forward refs (`get_type_hints`/`model_rebuild`) or stamp the target lazily by model name.

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.8: Typed-layer cleanup & caching (BACKLOG)

**Goal:** Reduce duplication and avoidable per-record work in the typed layer (code-review cleanup themes; no behavior change).
**Requirements:** TBD
**Source:** v1.2 post-milestone code review (2026-06-03)
**Items:**

- Dedupe the `try/except ImportError` `_serialize_for_write` loader copy-pasted verbatim in `client.create()` and `client.write()`.
- Collapse the co-recursive `_annotation_mentions_ref` + `_ref_target_class` walkers in `_pydantic_transform.py` (they traverse the same annotation tree and have already diverged once; drift risk — relates to the 999.7 ForwardRef fix).
- Extract shared constants for the `"odoo_readonly"` / `"odoo_x2many"` `json_schema_extra` keys (currently bare string literals duplicated across `type_mapper.py` and `_pydantic_transform.py`; a rename on one side silently disables the readonly/x2many write guards).
- Cache per-class annotation reflection + readonly/x2many classification to avoid `get_args`/`get_origin` per m2o field per record on large reads; replace the O(n²) list-membership id dedup in `read(list[Ref])` with a per-model set.

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)
