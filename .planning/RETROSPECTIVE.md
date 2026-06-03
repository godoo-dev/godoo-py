# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Parity & Release

**Shipped:** 2026-05-22
**Phases:** 5 | **Plans:** 14

### What Was Built
- `godoo-client` — async Odoo JSON-RPC client at TS parity: async-cm lifecycle, ContextVar `with_context`, keyset-paginated `iter_search_read`, `fields_get`/`ref`/`execute_kw`/`read_binary`/bulk-create, configurable timeout, typed error hierarchy, 8 domain services.
- `godoo-introspection` — built from scratch: `Introspector` (3-RPC batch schema fetch + per-instance cache), `CodeGenerator` emitting TypedDict modules across all 20 Odoo ttypes, selection→`Literal[...]`.
- `godoo-testcontainers` — sha256-keyed pg_dump/restore snapshot cache, custom addons bind-mount, `ConfigParameterHelper`, `TestHarness` async-cm.
- Release — public `godoo-dev/godoo-py` repo, PEP 420 `godoo.*` namespace, `godoo`→`godoo-client` rename, four distributions published to PyPI (0.2.0 → 0.2.1) via OIDC trusted publishing with rendered READMEs.

### What Worked
- The `types.py`/`functions.py`/`service.py`/`__init__.py` service quad scaled cleanly — Phase 2 and 3 followed the established shape with no architectural friction.
- Trusted publishing (OIDC) avoided long-lived PyPI tokens entirely — no secret handling on the release path.
- Phases 2 and 3 were independent after Phase 1, allowing parallel-friendly planning.

### What Was Inefficient
- PyPI pages shipped empty after the Phase 4 release because only the `godoo` meta package carried a README — required an unplanned Phase 4.1 hotfix (0.2.1). A pre-publish checklist item for per-distribution `readme` keys would have caught it.
- Requirement bookkeeping drifted: Phase 2's INTRO-* checkboxes and traceability stayed "Pending" through milestone close despite the work shipping — corrected during this close.

### Patterns Established
- PEP 420 implicit namespace packaging for a multi-distribution monorepo; namespace invariant verified by wheel inspection.
- GSD planning milestones are tagged `milestone-vX.Y` to stay out of the semantic-release `vX.Y.Z` package-tag namespace.
- testcontainers sync API is always wrapped in `asyncio.to_thread()`.

### Key Lessons
1. Per-distribution packaging metadata (README, `readme` key) must be verified at publish time — a monorepo meta-package README does not propagate to sibling distributions.
2. GSD milestone version numbering is independent of package release versioning; keep their tag namespaces separate to avoid driving semantic-release into an unintended major bump.
3. Update requirement checkboxes/traceability at phase transition, not at milestone close — closing-time reconciliation is error-prone.

### Cost Observations
- Model mix: not tracked this milestone.
- Notable: first milestone — establishes the baseline.

---

## Milestone: v1.1 — Typed Models & Browser Reach

**Shipped:** 2026-06-02
**Phases:** 4 | **Plans:** 11 | **Tests at close:** 352 passing

### What Was Built

- Typed models layer: `godoo.client.typed` (stdlib-only Protocol + `Ref[T]`), `godoo.client._pydantic_transform` (wire transforms), `@overload` dispatch on `client.read` / `search_read` making `client.read(ModelClass, ids)` → `list[ModelClass]` while leaving the raw `str` path unchanged; behind `godoo[typed]` optional extra.
- Pydantic CLI generator: `godoo-introspect generate` — emits one-file-per-model Pydantic packages from a live Odoo schema; replaces the v1.0 TypedDict generator (breaking, changelog-noted). Selection fields → `Literal[...]`, m2o → `Ref[Model]`/`Ref[int]`, x2many → `list[int]`.
- `packages/godoo` → `packages/godoo-client` directory rename via `git mv` with full blame preservation; PEP 420 `godoo.*` namespace guard test in CI.
- Transport seam: `Transport` Protocol + `transport_factory` hook on `OdooClientConfig` — additive, clean injection point for alternative transports.
- Pyodide spike (decision artifact): real in-browser HTTPS JSON-RPC call (uid + users) via `PyfetchTransport` (Strategy 3); ADR-0001 GO verdict; Python-floor Option A (defer until Pyodide ships CPython ≥3.14); BROWSER-F1/F2 escalated to v2.0 planning.

### What Worked

- The transport seam (BROWSER-01) proved its value immediately: the spike transport slotted in with zero core changes, validating the injection-point pattern.
- Settling OD-1 (All-Optional) and OD-2 (bool annotation skip) before Phase 6 planning avoided mid-implementation reversals — the wire transform passed 100 % of its tests first time.
- Phase 8 being a *decision artifact* milestone (not shipping code) was a clean, well-scoped pattern: the success criteria were a written verdict + go/no-go, not a feature, so the phase closed definitively with the ADR.
- The ACA self-destruct Bicep worked cleanly — the cloud endpoint was live, tested, and torn down in a single session with no cost tail.

### What Was Inefficient

- MILESTONES.md entry produced by the gsd-sdk CLI contained malformed "One-liner:" placeholders that had to be manually corrected at milestone close — CLI templating needs tighter integration with SUMMARY frontmatter.
- STATE.md `percent: 50` bug (CLI set `total_phases: 8` instead of `4`, halving the ratio) was a silent error that required manual correction.
- The codegen → typed-read round-trip test gap (999.3) and the wire-transforms-through-dispatch gap (999.4) were both caught only at audit time. Both could have been identified and added during Phase 6/7 plan review.

### Patterns Established

- `@overload` dispatch pattern: first-arg type determines return type; the typed branch uses `hasattr` duck-typing (`__odoo_model__`), never `isinstance(BaseModel)`, keeping the dispatch pydantic-free at the gate.
- Spike-as-milestone pattern: a spike phase with a written verdict + ADR as the deliverable is a clean GSD fit. The phase closes with an explicit go/no-go that feeds v2.0 planning.
- All-Optional partial-read strategy: every generated field is `Optional[T] = None`, plus `__all_optional__ = True` sentinel — `model_construct()` is the documented escape hatch for partial reads.
- Boolean False coercion skip: `bool`-annotated fields bypass the `False → None` wire transform; annotation-driven, not value-driven.

### Key Lessons

1. Plan-time test-gap identification beats audit-time discovery — add "what is NOT tested by these plans?" as a standard checklist item in phase plan reviews, not just verification steps.
2. CLI-generated prose entries (MILESTONES.md key accomplishments) should be reviewed before committing — the auto-generated output was incomplete and needed manual editing.
3. The "spike as decision artifact" milestone type works well when the success criteria are framed as evidence + decision, not code. Treat these phases as their own class in planning templates.

### Cost Observations

- Model mix: not tracked this milestone.
- Notable: Pyodide spike required a real cloud deployment — ACA endpoint stood up and torn down in one session; the self-destruct Logic App worked as designed.

---

## Milestone: v1.2 — Typed Relations, Writes & Error Surface

**Shipped:** 2026-06-03
**Phases:** 4 (9–12) | **Plans:** 9

### What Was Built
Completed the typed-models story across the family: structured RPC error surface (`OdooRpcError` parsed fields + `.raw` escape hatch + traceback/path stripping; `.data`→`.raw` breaking rename), single-level `Ref[T]` typed relation resolution (`client.read(ref)` / `read(list[Ref])`, batched per target model), typed write/create paths (`_serialize_for_write()` sending only set+writable fields with reverse wire transforms; codegen readonly/x2many metadata; x2many guard), and closed the two v1.1 coverage gaps (codegen→read→write integration roundtrip; wire-transforms-through-dispatch). Cleared four tech-debt items (Node 24 CI pins + gitleaks; spike password; RuntimeWarning noise; complete snapshot key).

### What Worked
- Build-order discipline paid off: ERR isolated to `errors.py` first (the one breaking change in isolation), then the REL prerequisite (Ref runtime target) before REL dispatch, then GEN-01 metadata before WRITE-04 readonly exclusion. No rework from ordering.
- Folding TEST-01/02 into the adjacent feature phases (11/10) kept each coverage test next to the code it exercises.
- Settling the open design decisions (ODD-1..4) before planning each phase removed mid-execution churn.

### What Was Inefficient
- Two code-review findings (CR-01 read-inherited x2many; CR-02 `id: int | None`) surfaced during Phase 11 verification rather than planning — caught and fixed pre-verification, but a sharper plan would have anticipated them.
- An extra Phase 11 fix commit (strip inline comment before `Field()` embedding) was only found during the live integration run, not unit tests.
- ERR-01..05 traceability checkboxes drifted stale (`[ ]`/Pending) despite Phase 9 verifying `passed` — caught and corrected during the milestone audit, not at phase close.

### Patterns Established
- Breaking changes isolated to a single dedicated phase (Phase 9 carried the lone `.data`→`.raw` rename).
- Codegen metadata (`json_schema_extra`) as the single source of truth for write-time field exclusion — no hardcoded readonly sets.
- Duck-typed dispatch on `client.read`/`write`/`create` keeps the typed layer importable without Pydantic by default.

### Key Lessons
- Update traceability checkboxes at phase verification, not at milestone audit — stale `[ ]`/Pending rows on `passed` phases create false-incomplete signals.
- Live integration runs catch serialization-shape bugs (inline comments, `id` defaults) that unit tests at `model_validate` level miss — keep an integration roundtrip in scope for any wire-format change.

### Cost Observations
- Config: `model_profile: balanced`, `mode: yolo`, `granularity: coarse`.
- 80 commits over ~2 days (2026-06-02 → 2026-06-03); 440/440 unit tests passing at close.
- Notable: coarse granularity (1–3 plans/phase) kept planning overhead low for a milestone of mostly well-scoped, well-ordered work.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 5 | Baseline — brownfield incorporation, parity build-out, first PyPI release |
| v1.1 | 4 | Typed models + spike-as-decision-artifact; transport seam pattern; All-Optional partial-read; boolean coercion skip |
| v1.2 | 4 | Typed relation resolution + typed writes; structured error surface; build-order discipline; codegen-metadata-as-truth |

### Cumulative Quality

| Milestone | Requirements | Coverage | Notes |
|-----------|--------------|----------|-------|
| v1.0 | 26/26 complete | — | ruff + mypy --strict gate on all src trees |
| v1.1 | 13/13 complete | 352 tests (unit) | 2 test-coverage gaps tracked as tech-debt (999.3, 999.4) |
| v1.2 | 22/22 complete | 440 tests (unit) | Both coverage gaps closed; 0 broken integrations; audit: tech_debt (no blockers) |

### Top Lessons (Verified Across Milestones)

1. CLI-generated documentation (MILESTONES.md, STATE.md) requires a manual review pass at milestone close — auto-generated entries have been incomplete or numerically wrong on both milestones.
2. Test-gap identification belongs in phase plan review, not audit — both v1.0 (traceability drift) and v1.1 (round-trip test gap) were caught only at close.
