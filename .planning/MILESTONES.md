# Milestones

## v1.1 Typed Models & Browser Reach (Shipped: 2026-06-02)

**Phases completed:** 4 phases, 11 plans
**Delivered:** Instance-derived Pydantic typed models with typed-read dispatch, the packages/godoo→godoo-client rename, a pluggable transport seam, and an empirically-grounded Pyodide/browser go/no-go verdict.

> **Versioning note:** "v1.1" is the GSD *planning* milestone. No new PyPI distribution was
> required by the milestone itself; current package version is 0.2.0/0.2.1. The milestone
> is tagged `milestone-v1.1` to avoid colliding with the semantic-release `vX.Y.Z` tag
> namespace.

**Key accomplishments:**

- `packages/godoo/` renamed to `packages/godoo-client/` via `git mv` (blame preserved); all operative path references updated across 5 config/doc files; PEP 420 namespace guard test (`godoo.__file__ is None`) added to CI.
- `Transport` Protocol + `transport_factory` hook on `OdooClientConfig` — pluggable transport seam that allows alternative transports (e.g. browser-native fetch) without changing core.
- `godoo.client.typed` stdlib-only module (`OdooModel` Protocol, `Ref[T]` dataclass) and `godoo.client._pydantic_transform` with full wire transforms; `@overload` dispatch on `client.read` / `search_read` so `client.read(ModelClass, ids)` → `list[ModelClass]`; default install stays httpx-only (`godoo[typed]` optional extra).
- Pydantic generator in `godoo-introspection` replaces the TypedDict generator (breaking, changelog-noted); `godoo-introspect generate` CLI entrypoint emits one-file-per-model + barrel `__init__.py`; selection fields as `Literal[...]`, m2o as `Ref[TargetClass]` / `Ref[int]`, x2many as `list[int]`.
- Pyodide spike: real in-browser HTTPS JSON-RPC call (`uid` + users via `PyfetchTransport`, Strategy 3); ADR-0001 GO verdict; Python-floor Option A (defer until Pyodide ships CPython ≥3.14); BROWSER-F1/F2 escalated to v2.0 planning.

**Per-phase:**

- **Phase 5 — Directory Rename:** `git mv packages/godoo packages/godoo-client`; 8 path references updated; PEP 420 guard test; CI green.
- **Phase 6 — Transport Seam & Typed Models Core:** `Transport` Protocol + `transport_factory`; `godoo.client.typed` + `_pydantic_transform`; `@overload` read/search_read dispatch; `godoo[typed]` extra; subprocess isolation test.
- **Phase 7 — Pydantic CLI Generator:** TypedDict emitter removed; Pydantic emitter + `type_mapper.py` migration; `godoo-introspect generate` CLI (typer); `pydantic>=2.13` + `typer>=0.26` as runtime deps.
- **Phase 8 — Pyodide Spike:** ACA Bicep (Odoo+Postgres, HTTPS, CORS); PyfetchTransport prototype + raw HTML spike page; in-browser HTTPS JSON-RPC run; ADR-0001 written (GO verdict, Strategy 3, Option A floor).

**Tech-debt incurred:**

- `spikes/08-pyodide/run_spike.py:16` hardcodes `password=admin` (ACA endpoint torn down; trivially guessable default; no rotation needed, but it is committed).
- `test_cli.py` error-path tests leave `_generate_async` coroutines unawaited → `RuntimeWarning` noise in CI output; tests pass, cosmetic.
- Codegen → typed-read round-trip not tested end-to-end (each half tested in isolation); tracked as backlog 999.3.
- Wire transforms not exercised through full `client.read` dispatch (tested at `model_validate` level); tracked as backlog 999.4.

---

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
