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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 5 | Baseline — brownfield incorporation, parity build-out, first PyPI release |

### Cumulative Quality

| Milestone | Requirements | Coverage | Notes |
|-----------|--------------|----------|-------|
| v1.0 | 26/26 complete | — | ruff + mypy --strict gate on all src trees |

### Top Lessons (Verified Across Milestones)

1. (Pending second milestone for cross-validation.)
