# Requirements: godoo-py

**Defined:** 2026-05-18
**Core Value:** The Python family member reaches feature parity with the TypeScript core-3 libraries.

## v1 Requirements

Requirements for the v1 parity milestone. Each maps to a roadmap phase. Sourced from
SEED.md §2 (parity gaps), the codebase map's adjacent bugs, and SEED §5 (release).

### Client

godoo async Odoo client — parity with `@godoo/client`.

- [ ] **CLIENT-01**: User can use `OdooClient` as an async context manager (`async with`) that opens and closes the session/transport
- [ ] **CLIENT-02**: User can stream large result sets via `iter_search_read()`, an auto-paginated async generator
- [ ] **CLIENT-03**: User can thread a context dict into the next RPC call via `with_context(lang=...)`
- [ ] **CLIENT-04**: User can retrieve a model's field metadata via `fields_get()`
- [ ] **CLIENT-05**: User can resolve an XML ID to a numeric record id via `ref(xml_id)`
- [ ] **CLIENT-06**: User can issue a raw, non-standard RPC method via `execute_kw()`
- [ ] **CLIENT-07**: User can fetch binary field data (e.g. attachments) via `read_binary()`
- [ ] **CLIENT-08**: User can create multiple records in one RPC call by passing a list of value dicts to `create`
- [ ] **CLIENT-09**: User can connect to an OAuth-proxied Odoo instance via `OAuthProxyClient` (bearer-token transport)
- [ ] **CLIENT-10**: The `godoo` package ships a `py.typed` PEP 561 marker

### Introspection

godoo-introspection — built from scratch, parity with `@godoo/introspection`.

- [ ] **INTRO-01**: User can retrieve a live model's full schema via an `Introspector` that queries `ir.model` / `ir.model.fields`
- [ ] **INTRO-02**: Introspection results are served from an `IntrospectionCache` keyed by model name, with a live-bypass option
- [ ] **INTRO-03**: User can generate typed Python representations from a live schema via a `CodeGenerator`
- [ ] **INTRO-04**: A type mapper translates Odoo field types (`char`, `many2one`, `selection`, …) to Python type hints
- [ ] **INTRO-05**: User can generate types from the command line via `godoo-introspect --url <url> --db <db> --output <dir>`
- [ ] **INTRO-06**: Selection fields are emitted as `Literal[...]` type hints, preserving the closed-set constraint
- [ ] **INTRO-07**: The `godoo-introspection` package ships a `py.typed` PEP 561 marker

### Testcontainers

godoo-testcontainers — parity with `@godoo/testcontainers`.

- [ ] **TESTC-01**: A local snapshot cache (`pg_dump`/restore keyed by a content hash, under `~/.odoo-testcontainers/snapshots/`) skips re-provisioning when inputs are unchanged
- [ ] **TESTC-02**: User can mount a local custom addons directory into the testcontainer via `addonsPath`
- [ ] **TESTC-03**: A partners provisioner seeds `res.partner` records into the test database
- [ ] **TESTC-04**: A projects provisioner seeds `project.project` + `project.task.type` records
- [ ] **TESTC-05**: A users provisioner seeds `res.users` records with configurable groups
- [ ] **TESTC-06**: A properties provisioner sets `ir.config_parameter` key/value pairs
- [ ] **TESTC-07**: A `TestHarness` fixture composes the provisioners and exposes a clean test API
- [ ] **TESTC-08**: The `godoo-testcontainers` package ships a `py.typed` PEP 561 marker

### Fixes

Bugs in files the parity work already touches (in-scope per the v1 scope decision).

- [ ] **FIXES-01**: `CdcService.get_feed` returns a directly usable async iterator from the class API (no un-awaited generator)
- [ ] **FIXES-02**: Transport timeouts raise `OdooTimeoutError` instead of being collapsed into `OdooNetworkError`
- [ ] **FIXES-03**: User can configure a request timeout on the transport / client config

### Release

SEED §5 — org bootstrap and PyPI publication.

- [ ] **RELEASE-01**: The `godoo-dev/godoo-py` GitHub repo exists and `origin` is configured
- [ ] **RELEASE-02**: The `godoo` client package is renamed to `godoo-client` for PyPI distribution
- [ ] **RELEASE-03**: All three packages are published to PyPI

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

### Compatibility

- **COMPAT-01**: Relax the Python version floor to 3.11/3.12 after auditing 3.14-specific usage

### Client

- **CLIENT-V2-01**: Automatic re-authentication on session expiry for long-running clients

### Performance

- **PERF-01**: `get_cash_balance` uses `read_group` SUM aggregation instead of client-side summing
- **PERF-02**: CDC `get_feed` avoids the per-batch secondary `mail.message` lookup where possible

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| godoo-adoption branch protocol | No separate source repo to shed — does not apply (SEED §3) |
| Full CONCERNS.md test-coverage backfill | v1 covers tests for new and changed code only, not the pre-existing coverage gaps |
| New domain services beyond the existing eight | Parity milestone — not adding scope to the client surface |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLIENT-01 | Phase 1 | Pending |
| CLIENT-02 | Phase 1 | Pending |
| CLIENT-03 | Phase 1 | Pending |
| CLIENT-04 | Phase 1 | Pending |
| CLIENT-05 | Phase 1 | Pending |
| CLIENT-06 | Phase 1 | Pending |
| CLIENT-07 | Phase 1 | Pending |
| CLIENT-08 | Phase 1 | Pending |
| CLIENT-09 | Phase 1 | Pending |
| CLIENT-10 | Phase 1 | Pending |
| INTRO-01 | Phase 2 | Pending |
| INTRO-02 | Phase 2 | Pending |
| INTRO-03 | Phase 2 | Pending |
| INTRO-04 | Phase 2 | Pending |
| INTRO-05 | Phase 2 | Pending |
| INTRO-06 | Phase 2 | Pending |
| INTRO-07 | Phase 2 | Pending |
| TESTC-01 | Phase 3 | Pending |
| TESTC-02 | Phase 3 | Pending |
| TESTC-03 | Phase 3 | Pending |
| TESTC-04 | Phase 3 | Pending |
| TESTC-05 | Phase 3 | Pending |
| TESTC-06 | Phase 3 | Pending |
| TESTC-07 | Phase 3 | Pending |
| TESTC-08 | Phase 3 | Pending |
| FIXES-01 | Phase 1 | Pending |
| FIXES-02 | Phase 1 | Pending |
| FIXES-03 | Phase 1 | Pending |
| RELEASE-01 | Phase 4 | Pending |
| RELEASE-02 | Phase 4 | Pending |
| RELEASE-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-05-18*
*Last updated: 2026-05-18 after roadmap creation*
