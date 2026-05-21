# Roadmap: godoo-py

## Overview

Close all Python parity gaps against the TypeScript core-3 libraries, build the
godoo-introspection package from scratch, and ship all three packages to PyPI. The
existing `godoo` client and `godoo-testcontainers` packages work today; this milestone
fills the named gaps, fixes adjacent bugs already in scope, and ends with a public
release under the `godoo-dev/godoo-py` GitHub org.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Client Parity** - Close all godoo client gaps and fix in-scope transport/service bugs (completed 2026-05-19)
- [x] **Phase 2: Introspection** - Build godoo-introspection from scratch (Introspector, cache, codegen, library) (completed 2026-05-21)
- [ ] **Phase 3: Testcontainers Parity** - Close all godoo-testcontainers gaps (snapshot cache, addons, provisioners, harness)
- [ ] **Phase 4: Release** - Create the GitHub repo, rename godoo→godoo-client on PyPI, publish all three packages

## Phase Details

### Phase 1: Client Parity

**Goal**: The godoo client package reaches full parity with @godoo/client and all adjacent transport/service bugs are fixed
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: CLIENT-01, CLIENT-02, CLIENT-03, CLIENT-04, CLIENT-05, CLIENT-06, CLIENT-07, CLIENT-08, CLIENT-10, FIXES-01, FIXES-02, FIXES-03
**Success Criteria** (what must be TRUE):

  1. User can use `async with OdooClient(...)` for automatic session open/close without calling `authenticate()` and `aclose()` manually
  2. User can stream arbitrarily large Odoo result sets via `async for record in client.iter_search_read(...)` without loading all records into memory
  3. User can call `client.with_context(lang="fr_FR").search_read(...)` and the context dict is threaded through to the next RPC call only
  4. User can call `fields_get()`, `ref()`, `execute_kw()`, `read_binary()`, and bulk `create` with a list of dicts — all return correct typed results
  5. `CdcService.get_feed` works correctly from the class API, transport timeouts raise `OdooTimeoutError` (not `OdooNetworkError`), and a configurable request timeout is respected

**Plans**: 4 plans
Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Transport fixes: configurable timeout + OdooTimeoutError (FIXES-02, FIXES-03)
- [x] 01-02-PLAN.md — CDC get_feed fix + py.typed marker (FIXES-01, CLIENT-10)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-03-PLAN.md — Client lifecycle + with_context + iter_search_read (CLIENT-01, CLIENT-02, CLIENT-03)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-04-PLAN.md — Client CRUD methods: fields_get, ref, execute_kw, read_binary, bulk create (CLIENT-04/05/06/07/08)

### Phase 2: Introspection

**Goal**: The godoo-introspection package is fully implemented, tested, and ships a working library matching @godoo/introspection parity
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: INTRO-01, INTRO-02, INTRO-03, INTRO-04, INTRO-06, INTRO-07 *(INTRO-05 dropped — D-CLI-1)*
**Success Criteria** (what must be TRUE):

  1. User can instantiate `Introspector(client)` and call `.get_schema("res.partner")` to receive a live field map from a running Odoo instance
  2. Subsequent calls to `Introspector.get_schema` for the same model return cached results; passing `bypass_cache=True` forces a fresh fetch
  3. User can call `CodeGenerator(introspector).generate(schema)` and receive a valid Python module string with a TypedDict, with `selection` fields rendered as `Literal[...]`
  4. Calling `CodeGenerator(introspector).write(schemas, output_dir)` writes one `.py` file per requested model into the output directory (library API — no CLI entry point)
  5. The `godoo-introspection` package includes a `py.typed` marker and passes `mypy --strict`

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Schema fetch + cache: Introspector, IntrospectionCache, ModelSchema, FieldSchema, FieldMeta, py.typed, tests (INTRO-01, INTRO-02, INTRO-07)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Type mapping + code generation: type_mapper, CodeGenerator, tests (INTRO-03, INTRO-04, INTRO-06)

### Phase 3: Testcontainers Parity

**Goal**: The godoo-testcontainers package reaches full parity with @godoo/testcontainers — snapshot caching, custom addons, four provisioners, and TestHarness
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: TESTC-01, TESTC-02, TESTC-03, TESTC-04, TESTC-05, TESTC-06, TESTC-07, TESTC-08
**Success Criteria** (what must be TRUE):

  1. A second test run with unchanged provisioner inputs completes faster than the first (snapshot restored from `~/.odoo-testcontainers/snapshots/` via pg_dump/restore)
  2. User can pass `addons_path=Path("./my_addons")` to `OdooTestContainer` and the custom module directory is mounted into the container
  3. User can call `harness.partners.create(...)`, `harness.projects.create(...)`, `harness.users.create(...)`, and `harness.properties.set(...)` to seed test data without writing raw RPC calls
  4. A `TestHarness` fixture provides a single clean API composing all four provisioners and exposes a ready `OdooClient`
  5. The `godoo-testcontainers` package includes a `py.typed` marker and passes `mypy --strict`

**Plans**: TBD

### Phase 4: Release

**Goal**: All three packages are publicly available on PyPI under the godoo-dev/godoo-py GitHub repository
**Mode:** mvp
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: RELEASE-01, RELEASE-02, RELEASE-03
**Success Criteria** (what must be TRUE):

  1. `github.com/godoo-dev/godoo-py` exists with the full commit history, `origin` points to it, and CI passes
  2. `pip install godoo-client` installs the async Odoo client (the internal package is renamed from `godoo` to `godoo-client`)
  3. `pip install godoo-introspection` and `pip install godoo-testcontainers` both succeed and import correctly on Python 3.14

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 (Phases 2 and 3 may run in parallel after Phase 1 completes)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Client Parity | 5/5 | Complete    | 2026-05-19 |
| 2. Introspection | 2/2 | Complete   | 2026-05-21 |
| 3. Testcontainers Parity | 0/? | Not started | - |
| 4. Release | 0/? | Not started | - |
