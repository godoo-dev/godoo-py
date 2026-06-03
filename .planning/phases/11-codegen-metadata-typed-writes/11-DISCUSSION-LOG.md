# Phase 11: Codegen Metadata + Typed Writes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 11-Codegen Metadata + Typed Writes
**Areas discussed:** x2many write policy, Readonly exclusion rule, Generated field emit style, TEST-01 shape

---

## x2many write policy

SC-5 already locks the RAISE behavior; the open question was *detection*.

| Option | Description | Selected |
|--------|-------------|----------|
| ttype metadata from codegen | GEN-01 emits a relation marker in `json_schema_extra`; write guard checks metadata, not Python shape. Most robust, won't misfire on scalar `list[int]`; widens GEN-01 scope. | ✓ |
| Annotation shape (list[Ref]/list[int]) | Guard inspects annotation; no extra codegen metadata. Simpler, but real `list[int]` scalar false-positives. | |
| You decide | Defer to planning. | |

**User's choice:** ttype metadata from codegen
**Notes:** GEN-01 scope now includes emitting an x2many/relation marker alongside the readonly marker. Ties GEN-01 ↔ WRITE-05.

---

## Readonly exclusion rule

| Option | Description | Selected |
|--------|-------------|----------|
| readonly OR store=False | Literal SC-4. Broadest; also excludes computed-stored fields with writable inverses. | |
| readonly OR (store=False AND compute set) | Keeps non-stored, non-computed fields writable. More precise; deviates from SC-4 literal wording. | ✓ |
| readonly only | Narrowest; ignores store. Risks sending non-stored computed fields. | |

**User's choice:** readonly OR (store=False AND compute set)
**Notes:** Deliberate refinement of ROADMAP SC-4 — planner to flag SC-4 text for a matching tweak so criterion and implementation agree. `FieldSchema` already carries readonly/store/compute.

---

## Generated field emit style

| Option | Description | Selected |
|--------|-------------|----------|
| Field() only where needed | Plain `= None` for normal fields; `Field(...)` only for readonly/x2many. Minimal diff, cleanest common case; two field shapes coexist. | |
| Field() on every field | Uniform `Field(default=...)` everywhere; consistent shape; more verbose. | |
| You decide | Defer to planning based on codegen templating. | ✓ |

**User's choice:** You decide
**Notes:** Claude leans "Field() only where needed"; final call at planning based on `type_mapper.py` / `codegen.py` templating and the conditional `Field` import.

---

## TEST-01 shape

| Option | Description | Selected |
|--------|-------------|----------|
| Both: unit + integration | respx payload-correctness unit test (runs always) + `@integration` live-container round-trip. Most coverage; matches "automate, don't punt to UAT". | ✓ |
| Unit test with respx mock | Fast, no Docker, mirrors Phase 10 TEST-02; doesn't prove real-Odoo behavior. | |
| Integration test, live container | Highest fidelity; Docker-only, slower, no fast unit coverage of edge cases. | |

**User's choice:** Both: unit + integration
**Notes:** Unit asserts set+writable-only payload, Ref→int, None→False, ISO dates, readonly exclusion, x2many raises. Integration does real codegen→read→write against a testcontainer.

---

## Claude's Discretion

- Generated field emit style (see above) — leaning "Field() only where needed".
- Within-scope details handed to planner/researcher: write-serializer location (`_pydantic_transform.py` mirror favored), `None`→`False` bool nuance (D-02 mirror), single-instance create/write overload shape, `write(instance)` guard when `id is None`.

## Deferred Ideas

None — discussion stayed within phase scope. Bulk/list typed create-write and x2many *writing* via the typed path were explicitly scoped out of this phase (not deferred as future capabilities).
