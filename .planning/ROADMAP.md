# Roadmap: godoo-py

## Milestones

- ✅ **v1.0 Parity & Release** — Phases 1-4.1 (shipped 2026-05-22) — full archive: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Typed Models & Browser Reach** — Phases 5-8 (shipped 2026-06-02) — full archive: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- 🚧 **v1.2 Typed Relations, Writes & Error Surface** — Phases 9-12 (in progress)

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

### v1.2 Typed Relations, Writes & Error Surface (Phases 9-12)

- [x] **Phase 9: Structured Error Surface** — Restructure `OdooRpcError` with parsed fields, traceback stripping, and `.raw` escape hatch (completed 2026-06-02)
- [ ] **Phase 10: Typed Relation Resolution** — `Ref[T]` carries runtime target class; `client.read(ref)` / `client.read(list[Ref])` resolves typed relations, batched
- [ ] **Phase 11: Codegen Metadata + Typed Writes** — Codegen emits readonly/store metadata; `client.write(instance)` / `client.create(instance)` typed paths with correct wire serialization
- [ ] **Phase 12: Tech Debt Close-out** — CI action bumps, committed password removal, unawaited coroutine warnings, snapshot partial-key fix

## Phase Details

### Phase 9: Structured Error Surface

**Goal**: Callers can handle RPC errors programmatically without parsing strings, and server tracebacks never leak into logs or serialized output.
**Depends on**: Nothing — `errors.py` has no upward dependencies; this phase is self-contained.
**Requirements**: ERR-01, ERR-02, ERR-03, ERR-04, ERR-05
**Success Criteria** (what must be TRUE):

  1. Catching `OdooRpcError` gives direct access to `.model_name`, `.field_name`, `.constraint_name`, `.human_message` attributes (each `str | None`) without string parsing.
  2. `str(exc)` and `to_json()` output never contain filesystem paths or server Python tracebacks (`data.debug` content).
  3. `exc.raw` holds the full original fault dict for opt-in debugging; `to_json()` never emits a `"raw"` key.
  4. Existing `except OdooRpcError` / `except OdooValidationError` catch blocks continue to work unchanged (additive-only hierarchy change).
  5. External callers accessing `exc.data` receive the renamed `.raw` attribute (documented breaking change in changelog; `data=` constructor kwarg retained for call-site compat in `_categorize_error`).

**Plans**: 1 plan

Plans:

- [x] 09-01-PLAN.md -- Refactor OdooRpcError: structured fields, .data->.raw rename, privacy strip, test migration

### Phase 10: Typed Relation Resolution

**Goal**: A caller holding a `Ref[T]` can resolve it to the related typed model instance through `client.read`, without naming the target model, using one batched RPC per distinct target model.
**Depends on**: Phase 9 (structured errors improve error feedback during testing of the new dispatch paths; ERR-01 structured fields surface cleanly when `Ref[int]` guard fires).
**Requirements**: REL-01, REL-02, REL-03, REL-04, REL-05, TEST-02
**Success Criteria** (what must be TRUE):

  1. A `Ref[T]` produced by the wire transform carries the Python target model class at runtime so `client.read(ref)` requires no additional model argument.
  2. `client.read(ref)` returns a single typed model instance (one RPC); `client.read(refs)` for a mixed list of typed Refs issues one batched RPC per distinct target model with ids deduplicated.
  3. Passing an untyped `Ref[int]` (no known target model class) to `client.read` raises `OdooValidationError` with a message that names the cause.
  4. Existing `Ref(id, name)` construction and equality semantics are unchanged — the new `_target_cls` field is `compare=False, hash=False, repr=False`.
  5. Wire transform tests exercise `Ref` / `date` / `datetime` fields through the full `client.read` dispatch chain (not just `model_validate`), closing backlog 999.4.

**Plans**: 2 plans

Plans:
**Wave 1**

- [x] 10-01-PLAN.md — Add `_target_cls` to `Ref[T]`, implement `_ref_target_class()` helper, populate from wire transform, TEST-02 wire-fidelity test

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 10-02-PLAN.md — `client.read(Ref[T])` overloads + dispatch branch (batching, fail-fast guard, order preservation), `test_rel_resolution.py`

### Phase 11: Codegen Metadata + Typed Writes

**Goal**: Callers can pass a typed `OdooBaseModel` instance into `client.write` or `client.create`, and only explicitly-set, writable fields are sent on the wire.
**Depends on**: Phase 10 (stable `_pydantic_transform.py` and `client.py` — shared edit surface; GEN-01 must precede WRITE-04 readonly-field exclusion).
**Requirements**: GEN-01, WRITE-01, WRITE-02, WRITE-03, WRITE-04, WRITE-05, TEST-01
**Success Criteria** (what must be TRUE):

  1. `client.create(instance)` accepts an `OdooBaseModel` instance and returns the new record id; only fields in `model_fields_set` are sent, with read-only fields excluded regardless.
  2. `client.write(instance)` updates the record at `instance.id` using only explicitly-set fields (`__pydantic_fields_set__`); unset fields are never sent as `None`.
  3. The write serializer converts `Ref` → bare int id, `None` (for set fields) → Odoo `False`, and `date`/`datetime` → ISO wire strings.
  4. Generated model fields include `json_schema_extra={"odoo_readonly": True}` where `readonly=True` or `store=False`; the write serializer uses this metadata to exclude computed/readonly fields from all write payloads.
  5. Attempting to write an x2many field via the typed path raises `OdooValidationError` with a message pointing to raw `write()` with command tuples.
  6. An end-to-end test feeds a codegen-generated model class through `client.read` dispatch and then `client.write`, closing backlog 999.3.

**Plans**: TBD

### Phase 12: Tech Debt Close-out

**Goal**: The CI pipeline is warning-free, the spike password is gone from the repo, test output has no `RuntimeWarning` noise, and direct `OdooTestContainer` users get the same complete snapshot key as `TestHarness` users.
**Depends on**: Nothing — all four items are independent fixes in separate files; can be done in any order after Phase 9 completes.
**Requirements**: DEBT-01, DEBT-02, DEBT-03, DEBT-04
**Success Criteria** (what must be TRUE):

  1. `release.yml` CI runs produce no Node 20 deprecation warnings from `actions/checkout` or `setup-uv`.
  2. `run_spike.py` contains no committed plaintext password (value removed or replaced with an env-var reference).
  3. Running the `test_cli.py` error-path tests produces no `RuntimeWarning: coroutine was never awaited` noise.
  4. Direct `OdooTestContainer` users receive a snapshot cache key that includes the properties dict, matching the key produced by `TestHarness`.

**Plans**: TBD

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
| 9. Structured Error Surface | v1.2 | 1/1 | Complete   | 2026-06-02 |
| 10. Typed Relation Resolution | v1.2 | 1/2 | In Progress|  |
| 11. Codegen Metadata + Typed Writes | v1.2 | 0/? | Not started | - |
| 12. Tech Debt Close-out | v1.2 | 0/? | Not started | - |

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
