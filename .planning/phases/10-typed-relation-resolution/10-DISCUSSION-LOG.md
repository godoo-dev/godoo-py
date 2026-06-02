# Phase 10: Typed Relation Resolution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 10-typed-relation-resolution
**Areas discussed:** read() dispatch shape, Mixed-type batch lists, Untyped-ref guard behavior, TEST-02 scope & location

---

## read() Dispatch Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Overload read() | Add `@overload read(self, ref: Ref[T]) -> T` and `@overload read(self, refs: list[Ref[T]]) -> list[T]`; the `read()` body detects `Ref`/list-of-`Ref` and dispatches. No new public method name. | ✓ |
| Dedicated resolve() | Introduce a separate `client.resolve(ref)` / `client.resolve(refs)` method distinct from the existing `read()` overload family. | |

**User's choice:** Overload read()
**Notes:** Matches SC-2 wording ("client.read(ref)") verbatim; single mental model — read resolves anything. No separate `resolve()` method.

---

## Mixed-Type Batch Lists

| Option | Description | Selected |
|--------|-------------|----------|
| Heterogeneous, order-preserved | `read([ref_partner, ref_move])` is allowed; internally group by `_target_cls`, fire one RPC per distinct target model (ids deduplicated), stitch results back into input order. | ✓ |
| Homogeneous-only, raise on mixed | Require all refs in a single `read()` call to share the same target model; raise `OdooValidationError` if the list contains refs pointing at different models. | |

**User's choice:** Heterogeneous, order-preserved
**Notes:** The user asked a clarifying question before deciding: "Does Odoo native read() allow lists?" The orchestrator confirmed that Odoo's ORM `read([ids], fields)` is list-of-ids-per-model, so "one batched RPC per distinct target model" (SC-2) maps 1:1 onto the native protocol. Homogeneous-only would save no RPC and would only shift the partitioning burden onto the caller. Typing note: a genuinely mixed list types as `list[OdooBaseModel]`; a same-model list still infers `list[T]` cleanly via the overload.

---

## Untyped-Ref Guard Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fail-fast, whole call | Validate ALL refs up front; if ANY ref lacks `_target_cls`, raise `OdooValidationError` BEFORE firing any RPC, naming the offending ref(s). Atomic — no partial side effects. | ✓ |
| Resolve-typed, error on untyped subset | Proceed with well-typed refs; raise `OdooValidationError` only for the untyped members (partial resolution with partial failure). | |

**User's choice:** Fail-fast, whole call
**Notes:** Atomic behavior — no partial side effects. `.human_message` must name the ref id and explain it came from an untyped m2o field (e.g. "Cannot resolve Ref(id=42): no target model known — it came from an untyped many2one field."). Error type is locked to `OdooValidationError` (SC-3), which already carries `.human_message` from Phase 9.

---

## TEST-02 Scope & Location

| Option | Description | Selected |
|--------|-------------|----------|
| Split: fidelity vs resolution | TEST-02 in `test_typed_dispatch.py` stays scoped to wire-transform fidelity. New resolution behavior (`_target_cls` propagation, batching, untyped guard, order preservation) goes in a separate `test_rel_resolution.py`. | ✓ |
| One combined dispatch test | Extend the existing `test_typed_dispatch.py` to cover both wire-transform fidelity and the new relation-resolution behavior in a single file. | |

**User's choice:** Split
**Notes:** Separates "transform correctness" from "resolution behavior" so failures localize. TEST-02 (backlog 999.4) wire-transform fidelity is driven through the full `client.read` dispatch chain via respx mocks (not just `model_validate`), lives in `test_typed_dispatch.py`. New file `test_rel_resolution.py` covers `_target_cls` propagation, `read(ref)` batching, untyped guard, and order preservation.

---

## Claude's Discretion

The following code-level decisions were delegated to the researcher/planner — no user-facing impact:

- **Target-class extraction helper approach:** Extend `_annotation_mentions_ref()` to also return the type arg via `get_args()`, vs introduce a sibling helper `_ref_target_class()`, vs inline the extraction directly in `_odoo_wire_transforms`. Any approach is acceptable provided mypy --strict passes and the logic is testable.
- **Overload placement and branch ordering:** Exact placement of the new `@overload` signatures relative to existing `read()` overloads and ordering of the runtime dispatch branches inside the `read()` body.

## Deferred Ideas

None — discussion stayed within phase scope.

---

## Process Note

Advisor mode was active during this discussion, but the orchestrator presented option tables directly for all four gray areas rather than invoking an external research agent. All decisions are internal API design choices (overload shape, batching strategy, guard semantics, test partitioning) with no external best-practice to research — direct option presentation was appropriate.
