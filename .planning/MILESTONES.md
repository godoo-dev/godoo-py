# Milestones

## v1.0 Parity & Release (Shipped: 2026-05-22)

**Phases completed:** 5 phases, 14 plans, 14 tasks
**Delivered:** The Python godoo family reached feature parity with the TypeScript core-3 libraries and shipped all three packages to PyPI.

> **Versioning note:** "v1.0" is the GSD *planning* milestone (the first milestone of
> this project). The PyPI distributions ship on their own semantic-release cadence and
> were published at **0.2.0 / 0.2.1** during this milestone — there is no `1.0.0`
> package release. The milestone is tagged `milestone-v1.0` to avoid colliding with the
> semantic-release `vX.Y.Z` tag namespace (`v0.1.0`, `v0.2.0`).

**Key accomplishments:**

- Shipped a fully typed async Odoo JSON-RPC client (`godoo-client`) with keyset pagination, ContextVar ambient context, safety guard, and 8 domain services — parity with the TypeScript core.
- Built `godoo-introspection` from zero: live 3-RPC batch schema discovery, per-instance cache, and a `CodeGenerator` that emits installable TypedDict modules for any Odoo model.
- Implemented `godoo-testcontainers` snapshot caching (pg_dump/restore, sha256-keyed, atomic writes) plus a custom addons bind-mount, cutting repeated integration-test setup to near zero.
- Added a `TestHarness` async context manager and `ConfigParameterHelper` (ir.config_parameter provisioner), completing the testcontainers public API.
- Established a PEP 420 implicit namespace (`godoo.client`, `godoo.introspection`, `godoo.testcontainers`) with four co-installable distributions; renamed the core dist to `godoo-client`; verified the namespace invariant via wheel inspection.
- Published all four distributions to PyPI via OIDC trusted publishing (no long-lived tokens); authored client-facing READMEs wired into each `pyproject.toml` so PyPI pages render.

**Per-phase:**

- **Phase 1 — Client Parity:** async context manager, ContextVar `with_context`, keyset-paginated `iter_search_read`, `fields_get`/`ref`/`execute_kw`/`read_binary`/bulk-create, configurable timeout, CdcService fix, PEP 561 marker.
- **Phase 2 — Introspection:** `Introspector` (3-RPC batch fetch + per-instance cache), `FieldMeta` frozen dataclasses, `CodeGenerator` covering all 20 Odoo ttype families.
- **Phase 3 — Testcontainers Parity:** sha256-keyed pg_dump/restore snapshot cache, custom addons bind-mount, `ConfigParameterHelper`, `TestHarness` async-cm.
- **Phase 4 — Release:** public `godoo-dev/godoo-py` repo, PEP 420 `godoo.*` restructure, `godoo`→`godoo-client` rename, four distributions published to PyPI at 0.2.0 via trusted publishing.
- **Phase 4.1 — Package READMEs (inserted):** client-facing READMEs for all three real distributions, `readme` key wired into each `pyproject.toml`; published 0.2.1 so PyPI pages render.

**Issues deferred:**

- TESTC-03/04/05 (declarative partner/project/user seeding provisioners) — dropped from v1, deferred to `godoo-stateman` (D-Drop-1).
- INTRO-05 (`godoo-introspect` CLI) — dropped; the library is the v1 deliverable (D-CLI-1).
- COMPAT-01 (relax Python floor to 3.11/3.12), CLIENT-V2-01 (auto re-auth), PERF-01/02 — tracked for v2/backlog.

**Technical debt incurred:**

- `release.yml` uses Node 20 actions emitting deprecation warnings; `actions/checkout` and `setup-uv` need a version bump.
- A separate Docs workflow was failing on `main` pushes at release time (not on the publish path) — left for a later pass.
- `snapshot.py` snapshot key: direct `OdooTestContainer` users get a partial key (`properties={}`), while `TestHarness` users get the real properties key — documented known limitation (plan 03-02).

**Known deferred items at close:** 2 open artifact items acknowledged as non-blocking — Phase 03 UAT (status `resolved`, 0 pending scenarios) and SEED-001 browser/Pyodide compatibility (dormant future idea, never in v1 scope). See STATE.md → Deferred Items.

---
