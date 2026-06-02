# Phase 10: Typed Relation Resolution - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

A caller holding a `Ref[T]` resolves it to the related typed model via `client.read(ref)` — no target-model arg needed, with one batched RPC per distinct target model.

</domain>

<decisions>
## Implementation Decisions

### read() Dispatch Shape

- **D-01: Overload `client.read()`.** Add `@overload read(self, ref: Ref[T]) -> T` and `@overload read(self, refs: list[Ref[T]]) -> list[T]`. The `read()` body detects `Ref` / list-of-`Ref` and dispatches. No separate `resolve()` method. Rationale: matches SC-2 wording ("client.read(ref)") verbatim; single mental model — read resolves anything.

### Mixed-Target Lists

- **D-02: Heterogeneous, order-preserved.** `read([ref_partner, ref_move])` is allowed. Internally group refs by `_target_cls`, fire one native Odoo `read(ids)` per distinct target model (ids deduplicated), then stitch results back into input order. Rationale: Odoo's native ORM `read` is list-of-ids-per-model, so "one batched RPC per distinct target model" (SC-2) maps 1:1 onto the protocol; homogeneous-only would save no RPC, only shift partitioning onto the caller. Typing note: a genuinely mixed list types as `list[OdooBaseModel]`; a same-model list still infers `list[T]` cleanly via the overload.

### Untyped-Ref Guard

- **D-03: Fail-fast on the whole call.** Validate ALL refs up front; if ANY ref lacks `_target_cls` (an untyped `Ref[int]`), raise `OdooValidationError` BEFORE firing any RPC, naming the offending ref(s). Atomic — no partial side effects. `.human_message` names the ref id and explains it came from an untyped m2o field (e.g. "Cannot resolve Ref(id=42): no target model known — it came from an untyped many2one field."). Error type is locked to `OdooValidationError` (SC-3, gained `.human_message` in Phase 9).

### Test Scope (TEST-02)

- **D-04: Split fidelity from resolution.** TEST-02 stays scoped to wire-transform FIDELITY (`Ref`/`date`/`datetime` driven through the full `client.read` dispatch chain via respx mocks, not just `model_validate`) and lives in `packages/godoo-client/tests/test_typed_dispatch.py`. NEW relation-resolution behavior (`_target_cls` propagation, `read(ref)` batching, untyped guard, order preservation) gets its own `packages/godoo-client/tests/test_rel_resolution.py`. Rationale: separates "transform correctness" from "resolution behavior" so failures localize.

### Carry-Forward / Locked Context

The following are locked from success criteria and prior phases — do not re-open:

- `Ref` stays `@dataclass(frozen=True)`; gains `_target_cls: type | None = field(default=None, compare=False, hash=False, repr=False)`. Existing `Ref(id, name)` construction and equality/hash semantics unchanged (SC-4). The wire transform passes `_target_cls` as a keyword arg at construction.
- Single-level resolution ONLY — no recursion / depth-nesting (REL-05; REL-ADV-01 deferred to a future milestone).
- No new runtime dependencies (Pydantic 2.13 already in the `godoo[typed]` extra). `from __future__ import annotations` everywhere; `mypy --strict`. Changes are ADDITIVE — existing `except OdooRpcError` catch blocks must survive untouched.

### Out of Scope (Phase Boundary)

Arbitrary-depth nesting (REL-ADV-01), x2many relation resolution, codegen field metadata (GEN-01, Phase 11), typed write/create paths (WRITE-01..05, Phase 11), tech-debt items (DEBT-01..04, Phase 12). No `errors.py` modification (Phase 9 already shipped the structured error surface).

### Claude's Discretion

The following code-level decisions are delegated to the researcher/planner — no user-facing impact:

- How the wire transform extracts the target class from a `Ref[T]` annotation: extend `_annotation_mentions_ref()` to also return the type arg via `get_args()`, vs a sibling helper `_ref_target_class()`, vs inlining in `_odoo_wire_transforms`. Code-level only.
- Exact placement of the new `@overload` signatures and runtime branch ordering inside `read()`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning Artifacts
- `.planning/ROADMAP.md` — § Phase 10: Typed Relation Resolution (goal + 5 success criteria)
- `.planning/REQUIREMENTS.md` — § REL (REL-01..REL-05, TEST-02)
- `.planning/PROJECT.md` — § Key Decisions (D-01 All-Optional partial reads, D-02 bool-coercion skip)

### Core Implementation Files
- `packages/godoo-client/src/godoo/client/typed.py` — current `Ref[T]` frozen dataclass (must gain `_target_cls`)
- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — `OdooBaseModel._odoo_wire_transforms` (m2o tuple → `Ref` at ~line 130-138), `_annotation_mentions_ref()` (~line 39-49)
- `packages/godoo-client/src/godoo/client/client.py` — `OdooClient.read()` dispatch + `@overload` signatures (~line 192-244)
- `packages/godoo-client/src/godoo/client/errors.py` — `OdooValidationError` (`.human_message` from Phase 9)

### Tests
- `packages/godoo-client/tests/test_typed_dispatch.py` — existing dispatch test (TEST-02 extends this)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `typed.py` :: `Ref[T]` (frozen dataclass) — add `_target_cls: type | None = field(default=None, compare=False, hash=False, repr=False)`; equality/hash semantics are unchanged because `compare=False, hash=False`.
- `_pydantic_transform.py` :: `OdooBaseModel._odoo_wire_transforms` — m2o `[id, "Name"]` → `Ref(...)` conversion; must also populate `_target_cls` from the field annotation. This is the injection point.
- `_pydantic_transform.py` :: `_annotation_mentions_ref()` — detects `Ref` in an annotation; natural extension point for extracting the target class via `get_args()`.
- `client.py` :: `OdooClient.read()` — dispatch entry; gains `Ref[T]` / `list[Ref[T]]` overloads + batching logic (group by `_target_cls`, dedupe ids, preserve order).
- `errors.py` :: `OdooValidationError` — raised by the untyped-ref fail-fast guard; already carries `.human_message` (Phase 9).

### Established Patterns
- `from __future__ import annotations` in every file; `TYPE_CHECKING` imports for `OdooClient` in services to avoid circular imports.
- All service functions are async; mypy --strict on all `src/` directories.
- `OdooValidationError` is the correct exception for domain-level precondition failures raised before any RPC call.
- Additive-only changes: existing `except OdooRpcError` catch blocks must not be disrupted.

### Integration Points
- The wire transform (`_odoo_wire_transforms`) is where `_target_cls` is populated — it has access to the field's annotation at transform time.
- `OdooClient.read()` is the resolution entry point; the batching and order-preservation logic lives here.
- Legacy services use `_m2o_id()`/`_m2o_name()` on raw `[id, "Name"]` lists — that is the pre-typed v1.0 pattern and is NOT part of this typed path; do not touch it.

</code_context>

<specifics>
## Specific Ideas

- The fail-fast guard error message should be specific: `"Cannot resolve Ref(id=42): no target model known — it came from an untyped many2one field."` (names the ref id, explains root cause).
- Mixed-list result type is `list[OdooBaseModel]` when refs are heterogeneous; same-model list infers `list[T]` cleanly via the overload — this is the expected typing outcome, not a limitation to work around.
- TEST-02 (backlog 999.4) wire-transform fidelity test stays in `test_typed_dispatch.py`; new resolution behavior test is `test_rel_resolution.py`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-Typed Relation Resolution*
*Context gathered: 2026-06-02*
