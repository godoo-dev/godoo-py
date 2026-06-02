# Phase 9: Structured Error Surface - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Callers can handle RPC errors programmatically without parsing strings, and server
tracebacks / filesystem paths never leak into logs or serialized output.

All changes are isolated to `packages/godoo-client/src/godoo/client/errors.py`.
`transport.py` is **not** modified — stripping and structured-field parsing centralize in
`OdooRpcError.__init__` so that every raise path (including direct raises like
`OdooAuthError("Not authenticated")`) is covered.

Covers requirements **ERR-01 … ERR-05** (SEED-003). This phase resolves the milestone's
one open design decision **ODD-4** (the `.data` → `.raw` rename).

</domain>

<decisions>
## Implementation Decisions

### Stripping (privacy gate — success criterion #2)
- **D-01:** Strip in `OdooRpcError.__init__` (not `_categorize_error`), so all raise paths
  are covered, including direct raises that carry no fault dict.
- **D-02:** Drop `data.debug` **entirely** from any surfaced view (`str()`, `to_json()`).
- **D-03:** Apply the PITFALL-9 filesystem-path regex (`File "/..." → File "<server-path>"`)
  to `human_message` as defense-in-depth, even though `data.message` is normally
  pre-translated and path-free.
- **D-04:** `.raw` retains the **full, untouched** original fault dict for opt-in debugging.

### `.data` → `.raw` rename (ODD-4 — the one sanctioned v1.2 breaking change)
- **D-05:** Rename the instance attribute `OdooRpcError.data` → `OdooRpcError.raw`.
- **D-06:** Retain the `data=` **constructor kwarg** for call-site compatibility (so the
  unchanged `_categorize_error` call sites in `transport.py` keep working).
- **D-07:** **No** compat alias / property for the old `.data` attribute. Documented as a
  breaking change in the changelog (semver-minor on the 0.x series).

### `to_json()` output shape
- **D-08:** Emit **flat structured keys**: `{error, message, model_name, field_name,
  constraint_name, human_message}`. Each parsed field is `str | None`.
- **D-09:** `to_json()` **never** emits a `"details"` key (removed) and **never** emits a
  `"raw"` key (success criterion #3) — `.raw` is attribute-only.
- **D-10:** `OdooSafetyError.to_json()` is **left untouched** — it is a local, non-RPC error
  outside the `OdooRpcError` hierarchy, already emits a safe structured `details`
  (OperationInfo), and has no leakage problem.

### Fault-payload parsing (ERR-01)
- **D-11:** Parse `model_name` / `field_name` / `constraint_name` / `human_message` from
  `data.message` + `data.arguments` for the **existing 5 mapped error types only**
  (Auth, Network/Timeout, Validation, Access, Missing). Fields are `None` when absent.
- **D-12:** Do **not** extend `_categorize_error` dispatch in this phase (keeps `transport.py`
  untouched). PITFALL-10 dispatch additions are deferred (see Deferred Ideas).

### `__str__` behavior
- **D-13:** Override `OdooRpcError.__str__` to return `self.human_message or self.args[0]`.
  Direct raises (no fault dict, `human_message is None`) fall through to `args[0]` unchanged;
  payload-constructed errors stringify to the specific stripped `data.message` instead of the
  generic top-level message. Accepted minor behavior change for callers matching
  `str(exc) == "Odoo Server Error"`.

### Additive-only constraint (carried forward / locked)
- **D-14:** No new intermediate classes, no hierarchy restructure — add structured fields as
  optional attributes on `OdooRpcError.__init__` only. Every existing `except OdooRpcError`
  / `isinstance` check must keep working unchanged (success criterion #4).
- **D-15:** No new runtime dependencies — stdlib `re` is sufficient for path/traceback
  stripping.

### Claude's Discretion
- Exact regex patterns for path stripping and for extracting `model_name` / `field_name` /
  `constraint_name` from `data.message` — implement per PITFALL-9/PITFALL-11 guidance.
- Precise changelog/docstring wording for the `.data` → `.raw` breaking change.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/ROADMAP.md` § "Phase 9: Structured Error Surface" — goal, success criteria, ERR list
- `.planning/REQUIREMENTS.md` § "ERR — RPC Error Surface (SEED-003)" — ERR-01 … ERR-05
- `.planning/seeds/SEED-003-rpc-error-categorization.md` — originating seed (privacy + DX drivers, scope)

### Research (must read — concrete patterns)
- `.planning/research/PITFALLS.md` — Pitfalls 8–11 are the SEED-003 pitfalls (path-strip regex,
  parsing correctness, "looks done but isn't" checklist)
- `.planning/research/SUMMARY.md` § "Key Findings" + § "ODD-4 (.data→.raw rename scope)"
- `.planning/research/ARCHITECTURE.md` § "Current OdooRpcError" + § "Hard constraints"
- `.planning/STATE.md` § "Open Decisions" (ODD-4) — now resolved by this CONTEXT.md

### Target code
- `packages/godoo-client/src/godoo/client/errors.py` — the ONLY file modified (7 classes, ~130 lines)
- `packages/godoo-client/src/godoo/client/rpc/transport.py` — `_categorize_error` (line 138) and
  call site `raise self._categorize_error(...)` (line 94); **read-only context, not modified**

### Parity reference (informational, not binding)
- `../godoo-ts/packages/client/src/types/errors.ts` — TS error surface (carries `data`/`details`,
  no stripping or structured fields yet; Python intentionally goes further — not bound to TS shape)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OdooAuthError.to_json()` already omits `details` entirely — the cleanest possible strip;
  generalize its safe behavior across the hierarchy.
- All subclasses delegate `__init__` to `OdooRpcError` and override only `to_json()` via
  `result = super().to_json(); result["error"] = "..."`. Adding params to `OdooRpcError.__init__`
  and reshaping the base `to_json()` is therefore the single change point for all subclasses.

### Established Patterns
- `cause=exc` + `self.__cause__ = cause` error-chaining convention (errors.py:34) — unchanged.
- `to_json()` on every error class for structured serialization — preserved, reshaped to flat keys.
- `from __future__ import annotations` + `mypy --strict` — new optional `str | None` fields must
  be typed accordingly.

### Integration Points
- `_categorize_error` (transport.py) constructs every RPC error with `data=data`; the `data=`
  kwarg name MUST survive the `.data`→`.raw` rename for these call sites to keep compiling.
- Phase 10's `Ref[int]` guard will raise `OdooValidationError`; its `human_message` field is
  referenced by Phase 10 success criterion 3 (ERR-01) — clean structured surface benefits it.

</code_context>

<specifics>
## Specific Ideas

- Success criteria are exact and testable: (1) attribute access without parsing; (2) no paths/
  tracebacks in `str()`/`to_json()`; (3) `.raw` present, `to_json()` has no `raw` key;
  (4) existing catch blocks unchanged; (5) `.data`→`.raw` with `data=` kwarg retained, no alias.
- The privacy gate (#2) is the load-bearing security requirement — test it explicitly with a
  fault dict containing a `data.debug` traceback and absolute filesystem paths.

</specifics>

<deferred>
## Deferred Ideas

- **PITFALL-10 dispatch fixes** — extend `_categorize_error` to map `SessionExpiredException`
  → `OdooAuthError` and `psycopg2.IntegrityError` → `OdooValidationError` (with constraint
  name). Out of scope here because it requires modifying `transport.py` (this phase keeps
  transport untouched). Candidate for a focused follow-up phase.
- **Deeper constraint extraction from `data.debug`** — pulling constraint names out of the
  traceback we otherwise strip. Deferred to avoid coupling parsing to stripped content.

</deferred>

---

*Phase: 9-structured-error-surface*
*Context gathered: 2026-06-02*
