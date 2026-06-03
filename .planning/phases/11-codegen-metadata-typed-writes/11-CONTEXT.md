# Phase 11: Codegen Metadata + Typed Writes - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Callers can pass a typed `OdooBaseModel` instance into `client.create` or `client.write`, and only explicitly-set, writable fields are sent on the wire. Codegen is taught to emit per-field write-metadata (`json_schema_extra`) so the write serializer knows which fields are read-only and which are x2many.

In scope: GEN-01 (codegen write-metadata), WRITE-01..05 (typed create/write + serializer + readonly exclusion + x2many guard), TEST-01 (codegen→read→write round-trip, closes backlog 999.3).

Out of scope: multi-level relation resolution (REL-ADV-01, deferred), x2many *writing* via the typed path (explicitly raises — see D-01), bulk/list typed create-write (SC speaks of a single instance).

</domain>

<decisions>
## Implementation Decisions

### x2many write policy (ODD-2 — resolved)
- **D-01:** Typed write path RAISES on any x2many field present in `model_fields_set`, per ROADMAP SC-5 — `OdooValidationError` whose message points the caller to raw `write()` with command tuples (e.g. `(6, 0, [...])`). x2many writing is NOT supported through the typed path in this phase.
- **D-02:** Detection is by **codegen-emitted metadata**, not Python annotation shape. GEN-01 must additionally emit an x2many/relation marker in `json_schema_extra` (e.g. `{"odoo_x2many": True}` or the field's `ttype`). The write guard keys off that metadata so a genuine scalar `list[int]` field never false-positives. **This widens GEN-01's scope** beyond just the readonly marker.

### Readonly exclusion rule (ODD-3 / GEN-01 — resolved)
- **D-03:** Codegen marks a field `json_schema_extra={"odoo_readonly": True}` when `readonly=True OR (store=False AND compute is not None)`. The write serializer excludes these from every write payload (create and write alike).
- **D-04:** This is a **deliberate refinement of ROADMAP SC-4**, which reads literally as `readonly=True OR store=False`. The narrower rule keeps non-stored, non-computed fields writable (avoids excluding fields that have a writable inverse / are legitimately settable). **Planner action:** flag the ROADMAP Phase 11 SC-4 wording for a matching tweak so the criterion and the implementation agree. `FieldSchema` already carries `readonly`, `store`, and `compute` — no new introspection needed.

### TEST-01 shape (resolved)
- **D-05:** TEST-01 is delivered as **both** a unit test and an integration test.
  - **Unit (respx, runs always):** feed a codegen-shaped model through `client.read` dispatch then `client.write`; assert payload correctness — only `model_fields_set` ∩ writable fields are sent; `Ref → int`; `None` (on a set field) → Odoo `False`; `date`/`datetime` → ISO string; readonly/non-stored fields excluded; setting an x2many raises `OdooValidationError`. Mirrors Phase 10's TEST-02 respx pattern.
  - **Integration (`@integration`, Docker-gated):** real codegen against a live `godoo-testcontainers` Odoo — generate a class, read a record, write it back, assert against the live instance.
  - Rationale: aligns with project preference to automate rather than punt to manual UAT.

### Claude's Discretion
- **Generated field emit style:** user delegated. Leaning **"Field() only where needed"** — plain `name: Optional[T] = None` for ordinary fields, `Field(default=None, json_schema_extra={...})` only for fields that carry readonly/x2many metadata (minimal diff from current codegen output, keeps the common case readable). Final call at planning based on how `type_mapper.py` / `codegen.py` template the field string and import header (`Field` import becomes conditional or always-on).
- **Within-scope questions handed to the planner/researcher (not yet locked):**
  - Write-serializer **location** — natural analogue to the read transform is a function in `_pydantic_transform.py` (mirror of `_odoo_wire_transforms`); a method on `OdooBaseModel` or a standalone `_write_serializer.py` are alternatives.
  - **`None` → `False` bool nuance** — mirror of D-02 (read-side bool `False`-coercion skip). For a set field, `None` → Odoo `False`; confirm bool-defaulted fields behave correctly given `__pydantic_fields_set__` tracks explicit `False`.
  - **`create`/`write` overload shape & arity** — single instance only (per SC); dispatch via `hasattr(x, "__odoo_model__")` vs `isinstance(x, str)`; model name from `instance.__odoo_model__`.
  - **`write(instance)` guard** when `instance.id is None` (never-created instance) — raise `OdooValidationError`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase governance
- `.planning/ROADMAP.md` — Phase 11 goal, success criteria SC-1..6, GEN-01-before-WRITE-04 dependency note. **SC-4 wording to be reconciled with D-03/D-04.**
- `.planning/REQUIREMENTS.md` — GEN-01, WRITE-01..05, TEST-01 definitions.
- `.planning/PROJECT.md` — Key Decisions D-01 (All-Optional partial read), D-02 (bool `False`-coercion skip — mirror needed write-side).
- `.planning/STATE.md` — ODD-2 (x2many RAISE) and ODD-3 (codegen metadata option A) origin; both now resolved here.

### Prior phase context (carry-forward)
- `.planning/phases/10-typed-relation-resolution/10-CONTEXT.md` — `Ref[T]` frozen-dataclass + `_target_cls`; `read()` dispatch surface; single-level resolution; `OdooValidationError` as canonical pre-RPC exception.
- `.planning/phases/09-structured-error-surface/09-CONTEXT.md` — `OdooValidationError.human_message`; additive-only, mypy --strict, `from __future__ import annotations`.

### Code surfaces this phase edits
- `packages/godoo-client/src/godoo/client/client.py` — add typed `create()` / `write()` overloads beside the Phase-10 `read()` dispatch (current dict `create` ~L518, `write` ~L536).
- `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — `_ref_target_class()` (~L55), `_annotation_mentions_ref()` (~L41), `OdooBaseModel` (~L107), `_odoo_wire_transforms` (~L126) — the write serializer is the reverse of this forward transform; reuse the Ref helpers.
- `packages/godoo-client/src/godoo/client/typed.py` — `Ref[T]` (~L22); serializer reads `ref.id`.
- `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` — `pydantic_field_str()` (~L25): primary GEN-01 surgery site (emit `json_schema_extra` for readonly + x2many).
- `packages/godoo-introspection/src/godoo/introspection/codegen.py` — `CodeGenerator.generate()` (~L97), `pydantic_field_str` call (~L139); assembles the field line + import header.
- `packages/godoo-introspection/src/godoo/introspection/types.py` — `FieldSchema` already carries `readonly`, `store`, `compute` (source data for GEN-01 — no new fields needed).
- `packages/godoo-introspection/src/godoo/introspection/introspector.py` — `FieldSchema` construction (~L282), `readonly`/`store`/`compute` projected from `ir.model.fields` (~L289-291).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_ref_target_class()` / `_annotation_mentions_ref()` in `_pydantic_transform.py` — proven Ref-annotation helpers; the write serializer reuses them for `Ref → int` conversion.
- `_odoo_wire_transforms` (`@model_validator(mode="before")`) — the forward (read) transform; the write serializer is its mirror (`False ← None` on set fields, `int ← Ref`, ISO-string ← `date`/`datetime`).
- `FieldSchema` already fetches `readonly`/`store`/`compute` via the 3-RPC introspection batch — GEN-01 needs no new schema discovery, only to project this metadata into generated `Field(...)`.
- `respx`-based round-trip pattern from Phase 10 TEST-02 — template for TEST-01's unit half.
- `godoo-testcontainers` package — provides the live Odoo for TEST-01's `@integration` half.

### Established Patterns
- Phase 10 `read()` added `@overload`s on `client.py` without breaking the dict API — same additive-overload approach for `create`/`write`.
- Pre-RPC domain validation always raises `OdooValidationError` (with `.human_message`).
- `from __future__ import annotations`, mypy --strict, dataclasses-not-Pydantic for non-model types, additive-only changes.

### Integration Points
- New typed `create`/`write` overloads dispatch on `hasattr(arg, "__odoo_model__")`; model name comes from `instance.__odoo_model__`, record id from `instance.id`.
- GEN-01 metadata (`odoo_readonly`, x2many marker) is the contract between codegen and the write serializer — both must agree on the `json_schema_extra` keys.

</code_context>

<specifics>
## Specific Ideas

- x2many RAISE message must be actionable: point to raw `write()` with command-tuple syntax (e.g. `(6, 0, [ids])`).
- Write serializer should be the literal mirror of `_odoo_wire_transforms` so read/write conversions stay symmetric and reviewable side-by-side.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Bulk/list typed create-write and x2many *writing* via the typed path were considered and explicitly placed out of scope for this phase, not deferred as future capabilities — see Phase Boundary.)

</deferred>

---

*Phase: 11-Codegen Metadata + Typed Writes*
*Context gathered: 2026-06-03*
