# Phase 9: Structured Error Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 9-structured-error-surface
**Mode:** default interactive
**Areas discussed:** Stripping location & scope, to_json() output shape, Parsing completeness, __str__ behavior

---

## Area 1 — Stripping Location & Scope

**Question:** Where should traceback/path stripping happen, and how aggressive?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `__init__`, debug-only + path regex | Strip in `OdooRpcError.__init__` (covers all raise paths), drop `data.debug` entirely, run PITFALL-9 path regex over `human_message` as defense-in-depth; `.raw` keeps full untouched dict | ✓ |
| (b) `__init__`, debug-only (no msg regex) | Same placement but skip the path regex pass over `data.message` / `human_message` | |
| (c) `_categorize_error` | Strip at the transport categorization layer — only covers RPC-originated raises, not direct raises | |

**User's choice:** (a) — Strip in `OdooRpcError.__init__`, drop `data.debug` entirely, run PITFALL-9 path regex over `human_message` as defense-in-depth; `.raw` retains the full untouched fault dict for opt-in debugging.

**Notes:** Placement in `__init__` is the only location that covers direct raises (e.g. `OdooAuthError("Not authenticated")`) as well as RPC-originated raises via `_categorize_error`. Defense-in-depth regex on `human_message` guards against the unusual case where `data.message` already contains a filesystem path.

---

## Area 2 — to_json() Output Shape

### Question 2a: Shape after the rename?

**Question:** What shape should `to_json()` emit after the rename?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Flat structured keys | `{error, message, model_name, field_name, constraint_name, human_message}` — each parsed field `str \| None`; no `"details"`; never `"raw"` | ✓ |
| (b) Nested `"structured"` dict | Top-level `"structured": {model_name, field_name, ...}` sub-object | |
| (c) Reuse `"details"` with safe dict | Keep existing `"details"` key, populate with parsed fields | |

**User's choice:** (a) — flat keys; `"details"` key removed entirely; `"raw"` never emitted (attribute-only for debugging).

**Notes:** Flat shape is the simplest for callers; eliminates the current inconsistency between subclasses that emit `"details"` and `OdooAuthError` which already omits it.

### Question 2b: Touch OdooSafetyError.to_json()?

**Question:** Touch `OdooSafetyError.to_json()`?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Leave it untouched | `OdooSafetyError` is a local, non-RPC error already emitting a safe structured `details` (OperationInfo); no leakage problem | ✓ |
| (b) Align to new shape | Normalize `OdooSafetyError.to_json()` to match the new flat-key shape | |

**User's choice:** (a) — leave untouched; `OdooSafetyError` is outside the `OdooRpcError` hierarchy and has no leakage problem.

**Notes:** The `"details"` key in `OdooSafetyError.to_json()` is intentional — it carries `OperationInfo` (operation, model, ids, safety_level), not unstructured server data. Aligning it would remove useful caller information for no safety gain.

---

## Area 3 — Parsing Completeness

**Question:** How much fault-payload parsing is in scope?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Existing 5 types only | Parse `model_name` / `field_name` / `constraint_name` / `human_message` for the existing 5 mapped error types (Auth, Network/Timeout, Validation, Access, Missing); fields `None` when absent; `transport.py` untouched | ✓ |
| (b) + PITFALL-10 dispatch fixes | Also extend `_categorize_error` to map `SessionExpiredException` → `OdooAuthError` and `psycopg2.IntegrityError` → `OdooValidationError` with constraint | |
| (c) + constraint from debug | Also extract constraint names from `data.debug` tracebacks before stripping | |

**User's choice:** (a) — parse for the existing 5 mapped error types only; `transport.py` stays untouched this phase.

**Notes:** Options (b) and (c) both require touching `transport.py`, which violates the phase boundary (all changes isolated to `errors.py`). Both are explicitly captured as deferred ideas.

---

## Area 4 — __str__ Behavior

**Question:** What should `str(exc)` return?

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `human_message or args[0]` | Override `OdooRpcError.__str__` to return `self.human_message` when set, else fall through to `self.args[0]` | ✓ |
| (b) Keep Exception default | Leave `__str__` unoverridden — `str(exc)` continues to return the generic top-level message (e.g. `"Odoo Server Error"`) | |

**User's choice:** (a) — override `OdooRpcError.__str__` to return `self.human_message or self.args[0]`.

**Notes:** Accepted minor behavior change: callers matching `str(exc) == "Odoo Server Error"` will now get `data.message` (stripped) instead when a fault dict is present. Direct raises (no fault dict, `human_message is None`) are unaffected — they fall through to `args[0]` unchanged.

---

## Confirmed Decision — ODD-4: .data → .raw Rename

**Context:** This is the one sanctioned v1.2 breaking change, resolved by this discussion session.

- Rename the instance attribute `OdooRpcError.data` → `OdooRpcError.raw`.
- Retain the `data=` **constructor kwarg** so the unchanged `_categorize_error` call sites in `transport.py` keep compiling.
- **No** compat alias / property for the old `.data` attribute — documented as a breaking change in the changelog (semver-minor on the 0.x series).

---

## Claude's Discretion

- Exact regex patterns for path stripping (PITFALL-9) and for extracting `model_name` / `field_name` / `constraint_name` from `data.message` (PITFALL-11) — implement per research guidance.
- Precise changelog/docstring wording for the `.data` → `.raw` breaking change.

---

## Deferred Ideas

1. **PITFALL-10 dispatch fixes** — extend `_categorize_error` to map `SessionExpiredException` → `OdooAuthError` and `psycopg2.IntegrityError` → `OdooValidationError` (with constraint name). Out of scope here because it requires modifying `transport.py`; candidate for a focused follow-up phase.
2. **Deeper constraint extraction from `data.debug`** — pulling constraint names from the traceback content before stripping. Deferred to avoid coupling parsing logic to content that is being stripped for privacy reasons.
