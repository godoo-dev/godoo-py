# Requirements: godoo-py — Milestone v1.2 "Typed Relations, Writes & Error Surface"

**Defined:** 2026-06-02
**Core Value:** Python developers get the same typed read, write, and introspection capabilities as the TypeScript family — with a clean error surface and no new runtime dependencies.

## Design Constraints

- Python-native designs throughout; no new dependencies (Pydantic 2.13 + stdlib already present).
- The error restructure (`OdooRpcError.data` → `.raw`) is a breaking change at the package level — semver minor bump on a 0.x series — but the GSD planning milestone is v1.2.
- Build order: ERR (isolated to `errors.py`, no upward deps) → REL prerequisite (Ref runtime target + wire transforms) → REL dispatch → GEN-01 (codegen metadata) → WRITE. TEST and DEBT fold into adjacent phases or stand alone.

## v1.2 Requirements

### REL — Typed Relation Resolution (TYPED-F1)

- [x] **REL-01**: A typed `Ref[T]` carries its target model class at runtime so it resolves without the caller naming the model.
- [x] **REL-02**: `client.read(ref)` returns the single related typed model instance for a typed `Ref` (one RPC).
- [x] **REL-03**: `client.read(refs)` returns related instances for a list of typed Refs — one batched RPC per distinct target model, ids deduplicated.
- [x] **REL-04**: Resolving an untyped `Ref[int]` (no known target model) raises a clear, typed error.
- [x] **REL-05**: Resolution is single-level only — arbitrary-depth nesting is explicitly out of scope.

### GEN — Codegen Field Metadata

- [x] **GEN-01**: The introspection codegen emits read-only / stored field metadata into each generated model field so the write serializer can exclude non-writable fields precisely. (Must land before WRITE-04.)

### WRITE — Typed Write/Create (TYPED-F2)

- [x] **WRITE-01**: `client.create(instance)` creates a record from a typed model instance and returns the new id.
- [x] **WRITE-02**: `client.write(instance)` updates the record at `instance.id` with only explicitly-set fields (`__pydantic_fields_set__`) — never sends unset fields as `None`.
- [x] **WRITE-03**: Write serializer applies reverse wire transforms — `Ref`→int id, `None`→Odoo `False`, date/datetime→wire strings.
- [x] **WRITE-04**: Read-only/computed fields excluded from write payloads via GEN-01 metadata.
- [x] **WRITE-05**: x2many fields are not serialized by the typed-write path in v1.2; a set x2many field raises a clear error pointing to raw `write()` with command tuples.

### ERR — RPC Error Surface (SEED-003)

- [ ] **ERR-01**: `OdooRpcError` exposes structured fields — model, field, constraint, human-readable message — parsed from the fault payload (None when absent).
- [ ] **ERR-02**: Server tracebacks and filesystem paths (`data.debug`) are stripped from `str(exc)` / the user-facing message.
- [ ] **ERR-03**: Full original fault payload preserved on a `.raw` escape-hatch attribute.
- [ ] **ERR-04**: `to_json()` emits structured fields + human message and never the raw payload (security gate).
- [ ] **ERR-05**: `OdooRpcError.data` renamed to `.raw` (documented breaking change; `data=` constructor kwarg retained for call-site compat; no compat alias; additive to the hierarchy — no new intermediate classes that break `except OdooRpcError`).

### TEST — Coverage Gaps

- [x] **TEST-01** (backlog 999.3): End-to-end test feeds a codegen-generated model class through `client.read()` dispatch — codegen→typed-read round-trip.
- [x] **TEST-02** (backlog 999.4): Test exercises wire transforms (`Ref`/date/datetime) through the full `client.read` dispatch chain, not just `model_validate`.

### DEBT — Tech Debt

- [ ] **DEBT-01**: `release.yml` Node 20 actions (checkout, setup-uv) bumped — deprecation warnings gone.
- [ ] **DEBT-02**: `run_spike.py` committed `password=admin` removed/neutralized.
- [ ] **DEBT-03**: `test_cli.py` error-path tests no longer leave unawaited coroutines (no `RuntimeWarning`).
- [ ] **DEBT-04**: `snapshot.py` partial snapshot-key limitation fixed — direct `OdooTestContainer` users get the same complete key as `TestHarness` users.

## Future Requirements

Deferred beyond v1.2. Tracked but not in current roadmap.

### Browser / Pyodide

- **BROWSER-01**: Browser build (TYPED-F1/F2 via Pyodide) — blocked on Pyodide shipping CPython ≥3.14 (not yet released; GO verdict recorded in ADR-0001).

### Relations — Advanced

- **REL-ADV-01**: Arbitrary-depth relation nesting — single-level covers the common case; recursion/cycle design deferred.

### Typed Write — Advanced

- **WRITE-ADV-01**: x2many typed-write ergonomics (command-tuple helpers).
- **WRITE-ADV-02**: Typed write of nested/child records (e.g. `(0,0,vals)` create-on-write).

## Out of Scope

| Feature | Reason |
|---------|--------|
| Browser build (BROWSER-F1/F2) and SEED-001 | Blocked on Pyodide shipping CPython ≥3.14; not yet released; GO verdict in ADR-0001; escalated to a future milestone |
| Arbitrary-depth relation nesting | Single-level covers the common case; recursion/cycle design deferred to a future milestone |
| x2many typed-write ergonomics (command-tuple helpers) | Deferred; raw `write()` with command tuples remains available |
| Typed write of nested/child records (`(0,0,vals)` create-on-write) | Deferred to a future milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REL-01 | Phase 10 | Complete |
| REL-02 | Phase 10 | Complete |
| REL-03 | Phase 10 | Complete |
| REL-04 | Phase 10 | Complete |
| REL-05 | Phase 10 | Complete |
| GEN-01 | Phase 11 | Complete |
| WRITE-01 | Phase 11 | Complete |
| WRITE-02 | Phase 11 | Complete |
| WRITE-03 | Phase 11 | Complete |
| WRITE-04 | Phase 11 | Complete |
| WRITE-05 | Phase 11 | Complete |
| ERR-01 | Phase 9 | Pending |
| ERR-02 | Phase 9 | Pending |
| ERR-03 | Phase 9 | Pending |
| ERR-04 | Phase 9 | Pending |
| ERR-05 | Phase 9 | Pending |
| TEST-01 | Phase 11 | Complete |
| TEST-02 | Phase 10 | Complete |
| DEBT-01 | Phase 12 | Pending |
| DEBT-02 | Phase 12 | Pending |
| DEBT-03 | Phase 12 | Pending |
| DEBT-04 | Phase 12 | Pending |

**Coverage:**
- v1.2 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-02*
*Last updated: 2026-06-02 — traceability filled by roadmapper (Phases 9-12)*
