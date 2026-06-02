# Project Research Summary

**Project:** godoo-py
**Milestone:** v1.2 -- Typed Relations, Writes & Error Surface
**Domain:** Async Python Odoo JSON-RPC SDK -- typed layer extension
**Researched:** 2026-06-02
**Confidence:** HIGH

---

## Executive Summary

v1.2 extends godoo's typed layer with three mutually-reinforcing capabilities: `Ref[T]`-driven relation resolution (TYPED-F1), typed write/create via `OdooBaseModel` instances (TYPED-F2), and a restructured error surface (SEED-003). All four researchers converged on the same conclusion: **no new dependencies are required**. Every capability is achievable with the already-declared stack (Python 3.14, Pydantic 2.13.4 behind `godoo[typed]`, stdlib `re`/`collections`). The roadmap must not introduce any new `pyproject.toml` entries.

The recommended build order is sequential by dependency: SEED-003 first (independent, improves the error surface for all subsequent testing), then TYPED-F1 prerequisite (`Ref` gains `_target_cls` + wire-transform extraction), then TYPED-F1 dispatch (`client.read(ref)` / `client.read(list[Ref])`, batched per target model), then TYPED-F2 (`odoo_dump` + typed write/create overloads). Both TYPED-F1 and TYPED-F2 modify `client.py` and `_pydantic_transform.py`; doing them sequentially avoids concurrent edits to the same files. SEED-003 is the lowest-complexity, highest-security-value item and should ship first to close the traceback-leakage gap regardless of the typed feature timeline.

The primary risk cluster is in TYPED-F2: Odoo write semantics diverge from read semantics in three places -- m2o fields must be sent as bare `int` (not `[id, name]` or `Ref`), x2many fields require command tuples (not `list[int]`), and partial-update correctness depends on `model_fields_set` (not `exclude_none`). All three are solvable with a single `odoo_dump` serializer function in `_pydantic_transform.py`, but each requires an explicit design decision before implementation. SEED-003 carries one breaking change: `OdooRpcError.data` renamed to `.raw`. This is the sole API break in v1.2 and must be documented in the changelog and verified with a regression test.

---

## Key Findings

### Recommended Stack

No stack changes for v1.2. The existing stack is sufficient:

- **Pydantic 2.13.4** (`godoo[typed]` extra) -- `model_dump(exclude_unset=True, mode='json')` is the partial-write mechanism; `model_fields_set` is the discriminator between "explicitly set" and "never touched". Verified live against installed 2.13.4.
- **stdlib `typing.get_args` / `get_origin`** -- extracts the `T` class from `Ref[T]` annotations at wire-transform time. Verified: `get_args(Ref[SomeModel])[0]` returns `SomeModel`.
- **stdlib `re`** -- all traceback/path stripping in SEED-003. A filesystem-path regex applied to `data.debug` and `data.message` is sufficient.
- **stdlib `collections.defaultdict`** -- Ref batching by target model class in TYPED-F1.

**Critical: no new entries in `pyproject.toml`.** All features are behind existing gates (`godoo[typed]` optional extra or stdlib-only).

### Expected Features

**Must have (P1 -- all ship in v1.2):**

- **SEED-003-B: Server traceback stripped from `str(exc)` and `to_json()`** -- privacy/security requirement; Odoo `data.debug` contains filesystem paths that must not reach logging sinks
- **SEED-003-A: Structured `model`, `field`, `constraint`, `human_message` attributes on `OdooRpcError`** -- machine-readable error fields; callers catching `OdooValidationError` need programmatic access, not string parsing
- **SEED-003-C: `.raw` escape hatch** -- full unstripped data dict for opt-in debugging; never serialized by `to_json()`
- **TYPED-F2-A/B: `client.create(model, instance)` / `client.write(model, ids, instance)`** -- typed instance paths completing the read-modify-write round-trip
- **TYPED-F1-A/B: `client.read(ref)` and `client.read(list[Ref])` (batched)** -- `Ref[T]` resolution to typed model; one RPC per distinct target model

**Should have (P2 -- ship in v1.2 if time allows, defer to v1.3):**

- **TYPED-F2-C: X2ManyCommand helper types** -- typed wrappers for `(6,0,ids)`, `(4,id)`, etc.; can launch with `list[int]` ADD-semantics default first
- **TYPED-F1-C: Mixed-type Ref list batching** -- heterogeneous `list[Ref[A] | Ref[B]]`; handled naturally if groups keyed by `__odoo_model__` string

**Defer to v2+:**

- Session-scoped identity map / cross-call result cache
- Multi-level / recursive relation resolution (`depth=N`)
- Lazy-loaded attribute access on `Ref` (requires async properties, not idiomatic Python)

**Explicitly NOT building (anti-features):**

- `model_dump(exclude_none=True)` as the write serializer for `write()` -- loses `model_fields_set` distinction; use `exclude_unset=True` exclusively
- Auto-REPLACE semantics for `list[int]` x2many fields -- silently destructive; explicit `X2ManyCommand.replace()` required
- `fields_get` allowlist caching for computed-field exclusion -- adds extra RPC per model-type; let Odoo raise instead, surface via SEED-003 structured error

### Architecture Approach

All three features fit cleanly into the existing two-file change surface: `_pydantic_transform.py` (the sole Pydantic importer) and `client.py` (the `OdooClient` facade). The Pydantic-optional boundary is the load-bearing architectural constraint -- `typed.py` and `client.py` must never import Pydantic at module level. The `_target_cls` field on `Ref` is a plain `type | None` (stdlib dataclass field); `odoo_dump` and `_extract_ref_target_cls` live in `_pydantic_transform.py`. All write/create paths route through `self.call()`, so the safety guard is free for typed paths. `_categorize_error` in `transport.py` is NOT modified by SEED-003 -- stripping centralizes in `OdooRpcError.__init__` to cover all raise paths.

**Modified files (complete list for v1.2):**

| File | Features |
|------|----------|
| `client/typed.py` | TYPED-F1: add `_target_cls: type \| None` field to `Ref[T]` |
| `client/_pydantic_transform.py` | TYPED-F1: `_extract_ref_target_cls` + m2o branch; TYPED-F2: `odoo_dump` |
| `client/client.py` | TYPED-F1: `@overload read(Ref/list[Ref])` + `_resolve_ref_list`; TYPED-F2: `@overload write/create` |
| `client/errors.py` | SEED-003: `OdooRpcError.__init__` + `to_json()` + extractors; `self.data` -> `self.raw` |
| `client/rpc/transport.py` | NOT MODIFIED |

### Critical Pitfalls

1. **Typed write sends computed/readonly fields to Odoo** -- `model_dump` emits `display_name`, `write_date`, `create_uid`, etc. Odoo raises "Cannot update a readonly field". Prevention: codegen emits `Field(json_schema_extra={"odoo_readonly": True})`; `odoo_dump` excludes these fields. (ODD-3 decision required)

2. **Wrong m2o write format** -- `Ref(id=42, name="ACME")` must become `42` on the wire; `None` must become `False` (not null). Prevention: `odoo_dump` implements `isinstance(v, Ref) -> v.id` and `None -> False` for set fields.

3. **x2many command tuple requirement** -- `list[int]` is not valid for Odoo `write()` on o2m/m2m fields. Odoo raises `ValueError`. Prevention: explicit design decision required (ODD-2).

4. **None vs False vs omitted on partial update** -- `model_dump(exclude_none=True)` loses the `model_fields_set` distinction. Prevention: use `exclude_unset=True`; fields in `model_fields_set` with `None` value -> send `False`; fields not in `model_fields_set` -> omit.

5. **SEED-003 traceback/path leakage** -- `data.debug` contains full server Python traceback with filesystem paths. Must be stripped from `str(exc)` and `to_json()`. `.raw` stores unstripped dict but must never appear in `to_json()`. Required test: `assert "raw" not in exc.to_json()`.

6. **N+1 RPC storm** -- calling `client.read(ref)` in a loop produces one RPC per ref. Prevention: batch-first design; `_resolve_ref_list` groups by `_target_cls.__odoo_model__` string (not Python type identity) and issues one read per distinct model.

---

## Open Design Decisions

These four decisions were independently flagged by multiple researchers and have NOT been resolved by the research phase. They must be resolved by the project owner before or during phase planning. Each is load-bearing for its feature.

---

### ODD-1: Ref runtime target-class mechanism

**Decision required for:** TYPED-F1

| Option | Mechanism | Status |
|--------|-----------|--------|
| **A (field -- recommended)** | `_target_cls: type \| None = field(default=None, compare=False, repr=False, hash=False)` on `Ref[T]` dataclass | All four researchers favor this; backward-compatible; `compare=False, hash=False` preserves equality semantics; stdlib-safe |
| **B (`__class_getitem__`)** | Override `Ref.__class_getitem__` to return a parameterized subclass | Requires metaclass machinery; breaks `frozen=True` semantics; higher complexity |

**Recommended:** Option A. Wire-transform populates `_target_cls` from `get_args(annotation)[0]` when that arg has `__odoo_model__`, else `None`.

**Owner action:** Confirm field name (`_target_cls` vs `model_class`) and annotation type (`type | None` vs `type[T] | None`). The `type | None` form avoids generic variance complexity; callers `cast()` themselves when needed.

---

### ODD-2: x2many write strategy

**Decision required for:** TYPED-F2

When a `list[int]` appears in `model_fields_set` for an x2many field, `odoo_dump` must choose:

| Strategy | Wire output | Risk |
|----------|-------------|------|
| **REPLACE `(6, 0, ids)`** | All existing relations removed; replaced with ids | **Silently destructive** -- a caller adding one id accidentally removes all others |
| **ADD `(4, id, 0)` per id** | Each id linked; existing relations preserved | Cannot remove relations without explicit commands |
| **EXCLUDE** | x2many fields omitted unless explicit command tuples provided | Safest; callers must opt in |
| **RAISE** | `OdooValidationError` if `list[int]` x2many in write payload | Forces explicitness; requires X2ManyCommand types |

FEATURES.md recommends ADD as the default (least destructive), with REPLACE requiring explicit `X2ManyCommand.replace([ids])`. PITFALLS.md flags REPLACE without documentation as the primary data-loss vector.

**Owner action:** Choose ADD / EXCLUDE / RAISE as the `list[int]` default. Confirm whether X2ManyCommand helpers ship in v1.2 Phase 4 or are deferred to v1.3.

---

### ODD-3: Read-only / computed field exclusion on write

**Decision required for:** TYPED-F2 + codegen interaction

| Strategy | How | When available |
|----------|-----|---------------|
| **A (codegen metadata -- preferred)** | Codegen emits `Field(json_schema_extra={"odoo_readonly": True})` for fields where `readonly=True` or `store=False`. `odoo_dump` introspects `model_fields` to build exclusion set. | Requires codegen to emit the metadata -- not confirmed present in v1.1 output |
| **B (hardcoded universal set -- fallback)** | `odoo_dump` always excludes `{"id", "display_name", "__last_update", "create_date", "write_date", "create_uid", "write_uid"}` regardless of model. | Available immediately; incomplete (does not cover custom computed fields) |

**Owner action:** Confirm whether v1.1 codegen already emits `readonly`/`store` metadata in generated `Field(...)` extras. If yes, use A. If no: extend codegen first (adds scope), or ship B as explicit fallback and defer A to v1.3.

---

### ODD-4: SEED-003 `.data` -> `.raw` rename scope

**Decision required for:** SEED-003 (the one breaking change in v1.2)

Scope to confirm:

- **Breaking:** `self.data` -> `self.raw` on the instance. The `__init__` kwarg name stays `data=` (no call-site changes in `_categorize_error`). Only external callers accessing `exc.data` must migrate.
- **Additive (not breaking):** New keyword-only params on `OdooRpcError.__init__`: `model_name`, `field_name`, `constraint_name`, `human_message` -- all default `None`.
- **Security requirement:** `data.debug` (server Python traceback with filesystem paths) stripped from `str(exc)` and `to_json()`. `.raw` stores full unstripped dict. `to_json()` must never include a `"raw"` key.
- **`__str__` behavior:** Returns `self.human_message or self.args[0]` -- the cleaner extracted message, not the raw RPC message.

**Owner action:** Confirm scope is correct and 0.x minor version bump is acceptable. Confirm `to_json()` shape and whether any backward-compat alias for `"details"` (the current key) is needed.

---

## Implications for Roadmap

Suggested phase structure (4 phases):

### Phase 1: SEED-003 -- Structured Error Surface

**Rationale:** Independent of both typed features. Highest security value (traceback stripping). Lowest complexity. Ships a usable improvement immediately and ensures all subsequent integration testing benefits from clean error messages. Contains the one breaking change in isolation.

**Delivers:** Structured model/field/constraint/human_message on OdooRpcError; server tracebacks stripped from str(exc) and to_json(); .raw escape hatch; extended fault-payload parsing (SessionExpiredException, IntegrityError routing).

**Features addressed:** SEED-003-A, SEED-003-B, SEED-003-C, SEED-003-D

**Pitfalls to avoid:** P8 (preserve existing isinstance hierarchy -- additive only), P9 (traceback stripping), P10 (incomplete fault-payload parsing), P11 (.raw must not appear in to_json())

**Research flag:** Standard patterns -- no additional research phase needed. Architecture file provides exact line numbers and verified current state.

**ODD to resolve before planning:** ODD-4

---

### Phase 2: TYPED-F1 Prerequisite -- Ref._target_cls + Wire Transform

**Rationale:** Required foundation for TYPED-F1 dispatch. Isolated change: only `typed.py` and `_pydantic_transform.py`. No changes to `client.py`. Easy to test in isolation.

**Delivers:** `Ref[T]` carries runtime target model class; existing `Ref(id, name)` construction backward-compatible; wire transform populates `_target_cls` from annotation `get_args` when target has `__odoo_model__`, else `None`.

**Features addressed:** TYPED-F1 infrastructure

**Pitfalls to avoid:** P6 (`Ref[int]` must yield `_target_cls=None`, not crash), P7 (group by `__odoo_model__` string, not Python type identity)

**Research flag:** Standard patterns -- no additional research phase needed.

**ODD to resolve before planning:** ODD-1

---

### Phase 3: TYPED-F1 Dispatch -- client.read(ref) / client.read(list[Ref])

**Rationale:** Depends on Phase 2 (Ref must carry `_target_cls`). Adds `@overload` signatures and `_resolve_ref_list` batch logic to `client.py`. Closes backlog item 999.3.

**Delivers:** `client.read(ref)` resolves a single `Ref[T]` to `T | None`; `client.read(list[Ref])` batches by target model (one RPC per distinct `__odoo_model__`); per-call id deduplication; `Ref[int]` raises clear `OdooValidationError`.

**Features addressed:** TYPED-F1-A, TYPED-F1-B, TYPED-F1-D (dedup is free with batching), TYPED-F1-C (mixed-type via `__odoo_model__` grouping)

**Pitfalls to avoid:** P5 (N+1 prevention), P6 (Ref[int] guard), P7 (mixed-model grouping; zero-id guard)

**Research flag:** Standard patterns -- architecture file provides exact @overload signatures and _resolve_ref_list skeleton.

---

### Phase 4: TYPED-F2 -- Typed Write / Create

**Rationale:** Depends on Phases 2/3 being stable (shares `_pydantic_transform.py` and `client.py`). Sequential edits safer for single-maintainer repo. Completes the read-modify-write round-trip.

**Delivers:** `odoo_dump(instance)` serializer; typed `@overload` on write and create; correct m2o (Ref -> int), date/datetime (mode='json'), partial-update (exclude_unset=True + model_fields_set for None -> False), and x2many handling per ODD-2 decision.

**Features addressed:** TYPED-F2-A, TYPED-F2-B (and optionally TYPED-F2-C if X2ManyCommand helpers are in scope)

**Pitfalls to avoid:** P1 (readonly field exclusion -- ODD-3), P2 (m2o wire format), P3 (x2many command tuples -- ODD-2), P4 (None vs False vs omitted)

**Research flag:** ODD-2 and ODD-3 must be resolved before this phase is planned. Once resolved, patterns are standard.

---

### Phase Ordering Rationale

- SEED-003 first: independent, security-relevant, contains the one breaking change in isolation.
- TYPED-F1 split into prerequisite + dispatch: the `_target_cls` extension is small and testable alone; separating it lowers risk for the dispatch phase.
- TYPED-F2 last: highest pitfall density (4 critical pitfalls); requires ODD-2 and ODD-3 resolved; benefits from SEED-003 structured errors in test feedback.

### Research Flags

All phases have standard, well-documented patterns. No additional research phase is needed before planning any phase. The four Open Design Decisions (ODD-1 through ODD-4) are the only blockers -- they require owner judgment, not additional research.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All API claims verified live against pydantic 2.13.4 and installed source files. No new dependencies. |
| Features | HIGH | Odoo RPC write semantics cross-verified against official docs and existing client patterns. Anti-features are well-argued and consistent across researchers. |
| Architecture | HIGH | All claims sourced from direct source reading with line numbers. No training-data assumptions. |
| Pitfalls | HIGH | All pitfalls grounded in actual codebase inspection. Test checklist is complete and actionable. |

**Overall confidence:** HIGH

### Gaps to Address

- **ODD-2 (x2many default strategy):** Requires owner decision on acceptable default semantics (ADD vs EXCLUDE vs RAISE) -- not resolvable by research.
- **ODD-3 (readonly field exclusion):** Requires owner to inspect v1.1 codegen output and confirm whether `json_schema_extra` metadata is already emitted.
- **ODD-4 (to_json() shape):** Requires owner to decide whether the existing `"details"` key needs a backward-compat alias or can be cleanly replaced.
- **X2ManyCommand helpers scope:** Owner to confirm whether TYPED-F2-C ships in v1.2 Phase 4 or is deferred to v1.3.

---

## Sources

### Primary (HIGH confidence -- verified against source or live)

- `packages/godoo-client/src/godoo/client/typed.py` -- Ref[T] current state (lines 22-34)
- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` -- wire transforms, m2o branch (lines 130-138)
- `packages/godoo-client/src/godoo/client/errors.py` -- OdooRpcError hierarchy (lines 20-43)
- `packages/godoo-client/src/godoo/client/rpc/transport.py` -- _categorize_error (lines 138-168)
- `packages/godoo-client/src/godoo/client/client.py` -- OdooClient (lines 1-565)
- Pydantic 2.13.4 model_dump API -- verified live via uv run python (2026-06-02)
- get_args(Ref[SomeModel])[0] returns class -- verified live (2026-06-02)
- model_dump(exclude_unset=True) and model_fields_set -- verified live (2026-06-02)
- model_dump(mode='json') date to ISO string -- verified live (2026-06-02)

### Secondary (MEDIUM confidence -- cross-verified documentation)

- Odoo 17.0 External API docs -- create/write method semantics
- odoo-development.readthedocs.io x2many command tuples -- command codes 0-6
- FastAPI body-updates docs -- exclude_unset PATCH pattern
- Pydantic serialization docs -- model_dump and model_fields_set
- Odoo JSON-RPC error structure guide -- data.name, data.debug, data.message, data.arguments fields

---

*Research completed: 2026-06-02*
*Ready for roadmap: yes -- pending resolution of ODD-1 through ODD-4*
