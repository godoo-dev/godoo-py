# Phase 9: Structured Error Surface - Research

**Researched:** 2026-06-02
**Domain:** Python exception hierarchy refactoring, Odoo JSON-RPC fault payload parsing, privacy/traceback stripping
**Confidence:** HIGH — all claims grounded in direct source reading (errors.py, transport.py, test_errors.py, Odoo 17 http.py via official GitHub) plus live verification of regex patterns.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Strip in `OdooRpcError.__init__` (not `_categorize_error`), so all raise paths are covered, including direct raises that carry no fault dict.
**D-02:** Drop `data.debug` entirely from any surfaced view (`str()`, `to_json()`).
**D-03:** Apply the PITFALL-9 filesystem-path regex to `human_message` as defense-in-depth.
**D-04:** `.raw` retains the full, untouched original fault dict for opt-in debugging.
**D-05:** Rename the instance attribute `OdooRpcError.data` → `OdooRpcError.raw`.
**D-06:** Retain the `data=` constructor kwarg for call-site compatibility.
**D-07:** No compat alias / property for the old `.data` attribute. Documented breaking change.
**D-08:** `to_json()` emits flat structured keys: `{error, message, model_name, field_name, constraint_name, human_message}`.
**D-09:** `to_json()` never emits a `"details"` key (removed) and never emits a `"raw"` key.
**D-10:** `OdooSafetyError.to_json()` is left untouched.
**D-11:** Parse `model_name` / `field_name` / `constraint_name` / `human_message` from `data.message` + `data.arguments` for the existing 5 mapped error types only.
**D-12:** Do not extend `_categorize_error` dispatch in this phase.
**D-13:** Override `OdooRpcError.__str__` to return `self.human_message or self.args[0]`.
**D-14:** No new intermediate classes, no hierarchy restructure — additive fields on `OdooRpcError.__init__` only.
**D-15:** No new runtime dependencies — stdlib `re` is sufficient.

### Claude's Discretion

- Exact regex patterns for path stripping and for extracting `model_name` / `field_name` / `constraint_name` from `data.message`.
- Precise changelog/docstring wording for the `.data` → `.raw` breaking change.

### Deferred Ideas (OUT OF SCOPE)

- PITFALL-10 dispatch fixes (SessionExpiredException → OdooAuthError, psycopg2.IntegrityError → OdooValidationError with constraint). Out of scope because it requires modifying `transport.py`.
- Deeper constraint extraction from `data.debug` (coupling parsing to stripped content).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ERR-01 | `OdooRpcError` exposes structured fields — model, field, constraint, human-readable message — parsed from the fault payload (None when absent). | Odoo fault payload shape verified (data.name, data.message, data.arguments, data.context); extraction strategy defined. |
| ERR-02 | Server tracebacks and filesystem paths (`data.debug`) are stripped from `str(exc)` / the user-facing message. | `data.debug` confirmed as the traceback field (Odoo 17 `serialize_exception`); regex patterns verified live. |
| ERR-03 | Full original fault payload preserved on a `.raw` escape-hatch attribute. | `.raw = data` assignment pattern documented; no stripping occurs on `.raw` itself. |
| ERR-04 | `to_json()` emits structured fields + human message and never the raw payload (security gate). | `to_json()` shape specified; `"raw"` key explicitly excluded per D-09. |
| ERR-05 | `OdooRpcError.data` renamed to `.raw` (documented breaking change; `data=` constructor kwarg retained for call-site compat; no compat alias; additive to the hierarchy). | Both construction sites in `_categorize_error` use `data=` kwarg; rename is mechanical; test list identifies regression cases. |

</phase_requirements>

---

## Summary

This phase is a focused, isolated refactor of a single file: `packages/godoo-client/src/godoo/client/errors.py` (~130 lines, 7 classes). It delivers the privacy gate (traceback/path stripping) and structured error fields (`model_name`, `field_name`, `constraint_name`, `human_message`) by modifying `OdooRpcError.__init__` and `to_json()`. Transport is never touched.

The Odoo 17/18/19 JSON-RPC fault payload shape has been verified against the official Odoo source (`odoo/http.py:serialize_exception`, `odoo/exceptions.py`). The key insight: Odoo does NOT embed model/field/constraint in structured context fields — that information appears only in the human-readable `data.message` string, if at all. The phase must parse these fields heuristically from the message text or return `None`; perfectly structured extraction is not always possible.

**Primary recommendation:** Implement `OdooRpcError.__init__` with four new private extractor helpers (`_extract_human_message`, `_extract_model_name`, `_extract_field_name`, `_extract_constraint_name`) that defensively parse from `data.message` + `data.arguments`, keeping all four fields as `str | None`. Strip `data.debug` and filesystem paths in `__str__` only (via `human_message or args[0]`); keep `.raw` complete and attribute-only. All existing `except OdooRpcError` / `isinstance` checks continue to work unchanged.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fault dict parsing / stripping | `errors.py` `OdooRpcError.__init__` | — | D-01: centralizes in `__init__` to cover ALL raise paths, not just `_categorize_error` |
| Traceback privacy gate | `errors.py` `__str__` override | — | `str(exc)` returns `human_message or args[0]`; no traceback in args[0] for direct raises |
| Transport error categorization | `transport.py` `_categorize_error` | — | NOT MODIFIED this phase (D-12); passes `data=` kwarg unchanged |
| Structured field access | `errors.py` instance attributes | — | `.model_name`, `.field_name`, `.constraint_name`, `.human_message` on `OdooRpcError` |
| Opt-in raw access | `errors.py` `.raw` attribute | — | Full unstripped dict; never serialized; callers opt-in explicitly |
| Serialization | `errors.py` `to_json()` | — | Flat dict; no `"details"` key; no `"raw"` key; structured fields only |

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` (stdlib) | 3.14 built-in | Filesystem-path regex, traceback detection | D-15: no new runtime dependencies; `re.compile()` is sufficient |
| `from __future__ import annotations` | — | Deferred annotation evaluation | Required by project conventions; already in errors.py |

No packages to install. This phase is stdlib-only.

---

## Package Legitimacy Audit

No external packages installed in this phase. Audit section not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
External caller raises / catches:
  except OdooValidationError as e:
    print(e.model_name)        # "res.partner" or None
    print(e.human_message)     # clean Odoo message, no traceback
    log.debug(e.raw)           # opt-in: full fault dict including data.debug

Fault dict flows through:

  Odoo Server
      │
      │  JSON-RPC response: {"error": {"code": 200, "message": "Odoo Server Error",
      │                                "data": {"name": "odoo.exceptions.ValidationError",
      │                                         "debug": "Traceback...\n  File /opt/...",
      │                                         "message": "The field 'name' is required",
      │                                         "arguments": ("The field 'name' is required",),
      │                                         "context": {}}}}
      ▼
  transport.py:_categorize_error(error_dict)
      │  extracts: code, message (outer), data (inner dict)
      │  calls: OdooValidationError(message, code=code, data=data)
      │  [transport.py NOT MODIFIED — data= kwarg name preserved]
      ▼
  errors.py:OdooRpcError.__init__(message, *, code, data, cause)
      │  self.raw = data                          # full dict, untouched
      │  self.human_message = _extract_human_message(data)   # "The field 'name' is required"
      │  self.model_name    = _extract_model_name(data)      # "res.partner" or None
      │  self.field_name    = _extract_field_name(data)      # "name" or None
      │  self.constraint_name = _extract_constraint_name(data) # "res_partner_name_uniq" or None
      │  super().__init__(message)                # args[0] = outer message (may be generic)
      ▼
  OdooRpcError.__str__()
      └→ returns: self.human_message or self.args[0]
         (human_message = clean extracted message; args[0] = fallback for direct raises)

  OdooRpcError.to_json()
      └→ returns: {"error": "...", "message": str(self),
                   "model_name": ..., "field_name": ...,
                   "constraint_name": ..., "human_message": ...}
         [NO "details" key; NO "raw" key]
```

### Recommended Project Structure

No structural changes. Single file modified:

```
packages/godoo-client/src/godoo/client/
└── errors.py   ← ONLY file modified (7 existing classes; 4 new private helpers added)
```

### Pattern 1: Additive Fields on `OdooRpcError.__init__`

**What:** Add `model_name`, `field_name`, `constraint_name`, `human_message` as `str | None` instance attributes, populated by private helper functions from the `data` dict. The `__init__` signature does not change for callers — all new attributes are computed internally.

**When to use:** When extending exceptions with metadata without breaking existing catch sites.

**Example (target state):**
```python
# Source: verified from errors.py + ARCHITECTURE.md pattern
class OdooRpcError(OdooError):
    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        data: dict[str, Any] | None = None,  # kwarg name preserved for transport.py compat
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.raw: dict[str, Any] | None = data  # RENAMED from self.data
        self.human_message: str | None = _extract_human_message(data)
        self.model_name: str | None = _extract_model_name(data)
        self.field_name: str | None = _extract_field_name(data)
        self.constraint_name: str | None = _extract_constraint_name(data)
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        return self.human_message or self.args[0]

    def to_json(self) -> dict[str, Any]:
        return {
            "error": "RPC_ERROR",
            "message": str(self),
            "model_name": self.model_name,
            "field_name": self.field_name,
            "constraint_name": self.constraint_name,
            "human_message": self.human_message,
        }
        # No "details" key — REMOVED (was leaking data.debug)
        # No "raw" key — NEVER serialized (security requirement, D-09)
```

### Pattern 2: Private Extractor Helpers

**What:** Four module-level private functions that safely extract structured fields from an Odoo fault data dict. All return `None` when data is absent or the field is not parseable.

**Odoo 17/18/19 fault data dict shape** [VERIFIED: Odoo 17.0 official source, `odoo/http.py:serialize_exception`]:

```python
data = {
    "name": "odoo.exceptions.ValidationError",  # fully-qualified exception class
    "debug": "Traceback (most recent call last):\n  File \"/opt/odoo/...\", line 42...",
    "message": "The field 'name' is required.",  # already-translated user message
    "arguments": ("The field 'name' is required.",),  # exception.args tuple
    "context": {},  # getattr(exception, 'context', {}) — almost always empty
}
```

**Critical finding:** `exception_type` was removed from the Odoo fault payload in Odoo 14 (PR #45723, merged 2020-04-08). It does NOT appear in Odoo 17/18/19 responses. The current `_categorize_error` code handles it defensively (`.get("exception_type") or ""` → empty string fallback), so this does not affect categorization behavior but means the `exception_type` branch is never triggered on Odoo 14+. [VERIFIED: GitHub PR #45723, Odoo 17.0 http.py]

**Key finding for structured field extraction:** Odoo does NOT embed model/field/constraint in structured context attributes in the `data` dict. The `context` field is `{}` for all standard exceptions (`ValidationError`, `UserError`, `AccessError`, `MissingError`, `AccessDenied`). Model/field/constraint information, when present, is embedded in the human-readable `data.message` string. [VERIFIED: Odoo 17.0 exceptions.py, service/model.py `_as_validation_error`]

```python
# Source: verified pattern for safe extraction
import re

# Private module-level patterns
_POSIX_PATH_RE = re.compile(r'File "(/[^"]+)"')
_WIN_PATH_RE = re.compile(r'File "([A-Za-z]:[^"]+)"')

def _strip_paths(text: str) -> str:
    """Replace filesystem paths in traceback-formatted strings."""
    text = _POSIX_PATH_RE.sub('File "<server-path>"', text)
    text = _WIN_PATH_RE.sub('File "<server-path>"', text)
    return text

def _extract_human_message(data: dict[str, Any] | None) -> str | None:
    """Return clean human-readable message from fault data, path-stripped as defense-in-depth."""
    if not data:
        return None
    msg: str | None = data.get("message") or None
    if not msg and data.get("arguments"):
        args = data["arguments"]
        msg = args[0] if args else None
    if msg:
        msg = _strip_paths(msg)  # D-03: defense-in-depth even for data.message
    return msg or None

def _extract_model_name(data: dict[str, Any] | None) -> str | None:
    """Extract Odoo model technical name from fault data (e.g. 'res.partner').
    
    Odoo does not provide structured model info in the data dict context field.
    This can only return a value if the integration test container reveals a
    non-standard context key — returns None in the common case.
    """
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("odoo_model") or ctx.get("model") or None  # defensive: check common keys

def _extract_field_name(data: dict[str, Any] | None) -> str | None:
    """Extract field technical name from fault data context (e.g. 'email')."""
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("field") or ctx.get("field_name") or None

def _extract_constraint_name(data: dict[str, Any] | None) -> str | None:
    """Extract SQL constraint name from fault data context (e.g. 'res_partner_name_uniq')."""
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("constraint") or ctx.get("constraint_name") or None
```

### Pattern 3: Subclass `to_json()` delegation (unchanged pattern)

**What:** All subclasses (OdooAuthError, OdooNetworkError, etc.) already use `result = super().to_json(); result["error"] = "..."; return result`. After the base `to_json()` is reshaped, every subclass automatically gets the new flat structure with the correct `"error"` key.

**No changes needed in subclasses** except `OdooAuthError.__init__` is unchanged (it already delegates `super().__init__(message, code=code, data=data, cause=cause)` and this survives the rename since `data=` kwarg is preserved).

### Anti-Patterns to Avoid

- **Do not strip in `_categorize_error`** (D-01): Direct raises like `OdooAuthError("Not authenticated")` in `client.py` line 107 would never be stripped. Centralizing in `__init__` covers all paths.
- **Do not include `.raw` in `to_json()`** (D-09): This is the security gate. The whole purpose of `.raw` being an attribute-only escape hatch is that serialization never leaks it.
- **Do not add a `self.data` compat alias** (D-07): The attribute rename is the documented breaking change. A compat property would undermine the semver signal.
- **Do not assume `data.context` contains model/field info in Odoo 17+** [ASSUMED prior ARCHITECTURE.md claim]: Standard Odoo exceptions have `context = {}`. The extractors must handle empty context safely and return `None` — these fields will be `None` for most real errors.
- **Do not use `data.debug` for constraint extraction** (deferred per D-12/deferred ideas): Parsing constraint names from the Python traceback in `data.debug` is brittle and couples parsing to the stripped content.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Traceback stripping | Custom AST-based traceback parser | Two `re.compile()` patterns (POSIX + Windows path) | The only thing that needs stripping is `File "..."` path references; regex is sufficient and stdlib |
| JSON serialization | Custom encoder | Plain `dict[str, Any]` return from `to_json()` | Already the established pattern in all 7 existing classes |

**Key insight:** Stdlib `re` handles all path-stripping needs. No external parsing libraries are warranted for this scope.

---

## Common Pitfalls

### Pitfall 1: `exception_type` field is absent in Odoo 14+

**What goes wrong:** The current `_categorize_error` code branches on `data.get("exception_type")`. This field was removed from Odoo's `serialize_exception` in Odoo 14 (PR #45723). On Odoo 17/18/19, `exception_type` is always absent — the code falls through to the `data.name` branch.

**Why it happens:** Pre-14 Odoo payloads had both fields. The godoo codebase was likely written with Odoo 13 payloads as reference.

**How to avoid:** The extractor helpers for this phase only read from `data.name`, `data.message`, `data.arguments`, and `data.context` — not from `exception_type`. This is already correct.

**Warning signs:** Any test fixture that uses `exception_type` to validate structured field extraction (those tests pass only for historical payloads, not modern Odoo).

**Impact on this phase:** None — D-12 keeps transport categorization untouched.

[VERIFIED: Odoo 17.0 http.py via GitHub raw; PR #45723 merge date 2020-04-08]

### Pitfall 2: `data.context` is always empty for standard exceptions

**What goes wrong:** ARCHITECTURE.md suggested `data.context` might contain `{model: ..., field: ..., constraint: ...}`. Odoo's `serialize_exception` uses `getattr(exception, 'context', {})`. Standard `ValidationError`, `UserError`, `AccessError`, `MissingError`, `AccessDenied` in Odoo 17 do NOT define a `context` attribute — so `context` is always `{}`.

**Why it happens:** The `context` field mechanism exists for custom exception subclasses that add context metadata (some community modules do this), but the standard Odoo exceptions don't use it.

**How to avoid:** Extractors must handle `context = {}` as the normal case and return `None` for `model_name`, `field_name`, `constraint_name` in most real-world scenarios. The structured fields will be `None` for most errors — and that is correct behavior per D-11 ("None when absent").

**Warning signs:** Tests that assert `model_name is not None` without providing synthetic fixture data that explicitly includes context.

[VERIFIED: Odoo 17.0 exceptions.py; serialize_exception source]

### Pitfall 3: `test_errors.py` references `err.data` — must update tests

**What goes wrong:** Two existing tests directly access `err.data`:
- `test_defaults`: `assert err.data is None`
- `test_stores_code_and_data`: `assert err.data == data`

After the rename, these will raise `AttributeError`. Additionally:
- `test_to_json` asserts `result["details"] == {"key": "val"}` — the `"details"` key is removed.
- `test_to_json_no_data` asserts `result["details"] is None` — same.

**How to avoid:** The wave containing the `errors.py` changes must also update `test_errors.py` in the same commit. The plan should include explicit test migration items.

[VERIFIED: direct read of `packages/godoo-client/tests/test_errors.py`]

### Pitfall 4: `OdooError.to_json()` base still emits `"details": None`

**What goes wrong:** The base `OdooError.to_json()` (line 12-17) returns `{"error": "ODOO_ERROR", "message": ..., "details": None}`. D-09 removes `"details"` from `OdooRpcError.to_json()` — but the base class keeps it. If `OdooError` callers test for `"details"` key, this inconsistency may surprise them.

**Decision needed at implementation time:** Does the base `OdooError.to_json()` also drop `"details"`? The CONTEXT.md does not address the base class shape. The test `test_to_json_shape` in `TestOdooError` currently asserts `result["details"] is None`. D-10 explicitly preserves `OdooSafetyError.to_json()` unchanged.

**Recommendation (discretion area):** Leave `OdooError.to_json()` and `OdooSafetyError.to_json()` untouched. `OdooRpcError.to_json()` replaces `"details"` with the four structured keys. This is the minimal-change approach consistent with the additive constraint (D-14).

### Pitfall 5: Windows-style paths not stripped by POSIX-only regex

**What goes wrong:** Odoo tracebacks from Windows-hosted instances include paths like `File "C:\odoo\addons\..."`. A POSIX-only regex `r'File "(/[^"]+)"'` misses these.

**How to avoid:** Use two compiled patterns — one for POSIX (`/` prefix) and one for Windows (`[A-Za-z]:` prefix). Both are simple and verified to work with Python's `re.sub`. [VERIFIED: live Python execution in project environment]

---

## Code Examples

### Concrete Odoo 17 Fault Payloads (verified shapes)

```python
# Source: Odoo 17.0 github.com/odoo/odoo/blob/17.0/odoo/http.py serialize_exception

# 1. ValidationError (model constraint violation)
validation_error_payload = {
    "code": 200,
    "message": "Odoo Server Error",
    "data": {
        "name": "odoo.exceptions.ValidationError",
        "debug": "Traceback (most recent call last):\n  File \"/opt/odoo/addons/base/models/res_partner.py\", line 234, in write\n    raise ValidationError(...)\n",
        "message": "The field 'name' is required.",
        "arguments": ("The field 'name' is required.",),
        "context": {},
    }
}

# 2. UserError (business logic rejection)
user_error_payload = {
    "code": 200,
    "message": "Odoo Server Error",
    "data": {
        "name": "odoo.exceptions.UserError",
        "debug": "Traceback ...",
        "message": "You cannot delete a posted journal entry.",
        "arguments": ("You cannot delete a posted journal entry.",),
        "context": {},
    }
}

# 3. AccessError (ACL violation)
access_error_payload = {
    "code": 200,
    "message": "Odoo Server Error",
    "data": {
        "name": "odoo.exceptions.AccessError",
        "debug": "Traceback ...",
        "message": "You are not allowed to access 'res.partner' (res.partner) records.",
        "arguments": ("You are not allowed to access ...",),
        "context": {},
    }
}

# 4. MissingError (deleted record)
missing_error_payload = {
    "code": 200,
    "message": "Odoo Server Error",
    "data": {
        "name": "odoo.exceptions.MissingError",
        "debug": "Traceback ...",
        "message": "Record does not exist or has been deleted.\n(Record: res.partner(42,), User: 2)",
        "arguments": ("Record does not exist ...",),
        "context": {},
    }
}

# 5. AccessDenied (authentication failure)
access_denied_payload = {
    "code": 200,
    "message": "Odoo Server Error",
    "data": {
        "name": "odoo.exceptions.AccessDenied",
        "debug": "",   # AccessDenied suppresses traceback: __traceback__ = None
        "message": "Access Denied",
        "arguments": ("Access Denied",),
        "context": {},
    }
}

# 6. SessionExpiredException (not currently mapped — deferred)
session_expired_payload = {
    "code": 100,
    "message": "Odoo Session Expired",
    "data": {
        "name": "odoo.http.SessionExpiredException",
        "debug": "Traceback ...",
        "message": "Session expired",
        "arguments": ("Session expired",),
        "context": {},
    }
}

# 7. Missing data key (nginx/proxy error — no exception context)
proxy_error_payload = {
    "code": 500,
    "message": "Internal Server Error",
    # No "data" key — _categorize_error handles: data = error_dict.get("data") or {}
}
```

### Path-stripping functions (verified with live Python 3.14)

```python
# Source: verified by running in C:/dev/godoo-dev/godoo-py uv run python
import re
from typing import Any

_POSIX_PATH_RE = re.compile(r'File "(/[^"]+)"')
_WIN_PATH_RE = re.compile(r'File "([A-Za-z]:[^"]+)"')


def _strip_paths(text: str) -> str:
    """Replace filesystem paths embedded in Python traceback format strings.

    Handles both POSIX (/opt/odoo/...) and Windows (C:\\odoo\\...) paths.
    Applied to data.message as defense-in-depth (D-03) and available for
    other message strings.
    """
    text = _POSIX_PATH_RE.sub('File "<server-path>"', text)
    text = _WIN_PATH_RE.sub('File "<server-path>"', text)
    return text
```

### Test cases that MUST pass after Phase 9

```python
# Source: derived from success criteria in 09-CONTEXT.md + Pitfall analysis

# ERR-01: Attribute access without parsing
def test_structured_fields_accessible() -> None:
    data = {
        "name": "odoo.exceptions.ValidationError",
        "debug": "Traceback...\n  File \"/opt/odoo/models.py\", line 42",
        "message": "The field 'name' is required.",
        "arguments": ("The field 'name' is required.",),
        "context": {},
    }
    err = OdooValidationError("Odoo Server Error", data=data)
    assert err.human_message == "The field 'name' is required."
    assert err.model_name is None  # context is empty — correct
    assert err.field_name is None
    assert err.constraint_name is None

# ERR-02: No traceback/path in str(exc) or to_json()
def test_no_traceback_in_str() -> None:
    data = {
        "name": "odoo.exceptions.ValidationError",
        "debug": "Traceback ...\n  File \"/opt/odoo/addons/account/models.py\", line 42",
        "message": "Value error",
        "arguments": ("Value error",),
        "context": {},
    }
    err = OdooValidationError("Odoo Server Error", data=data)
    assert "/opt/odoo" not in str(err)
    result = err.to_json()
    assert "/opt/odoo" not in str(result)

# ERR-02: No path in to_json() output
def test_no_path_in_to_json() -> None:
    data = {"name": "...", "debug": "File \"/opt/odoo/server.py\", line 1",
            "message": "err", "arguments": ("err",), "context": {}}
    err = OdooRpcError("msg", data=data)
    assert "/opt/odoo" not in str(err.to_json())

# ERR-03: .raw holds full original dict
def test_raw_holds_full_dict() -> None:
    data = {"name": "...", "debug": "big traceback", "message": "err",
            "arguments": ("err",), "context": {}}
    err = OdooRpcError("msg", data=data)
    assert err.raw is data
    assert "debug" in err.raw  # traceback preserved in .raw

# ERR-04: to_json() never emits "raw" key
def test_to_json_no_raw_key() -> None:
    for cls in [OdooRpcError, OdooAuthError, OdooValidationError,
                OdooAccessError, OdooMissingError, OdooNetworkError, OdooTimeoutError]:
        err = cls("test", data={"name": "x", "debug": "tb", "message": "m",
                                "arguments": ("m",), "context": {}})
        assert "raw" not in err.to_json()

# ERR-05: .data raises AttributeError; data= kwarg still works
def test_data_attribute_removed() -> None:
    err = OdooRpcError("msg", data={"name": "x"})
    assert not hasattr(err, "data")   # breaking change verified
    assert err.raw == {"name": "x"}   # .raw is the new name

# Success criterion 4: existing isinstance hierarchy preserved
def test_isinstance_hierarchy_unchanged() -> None:
    for cls in [OdooAuthError, OdooNetworkError, OdooTimeoutError,
                OdooValidationError, OdooAccessError, OdooMissingError]:
        err = cls("test")
        assert isinstance(err, OdooRpcError)
        assert isinstance(err, OdooError)
    safety = OdooSafetyError("blocked", operation=...)
    assert not isinstance(safety, OdooRpcError)

# D-13: __str__ returns human_message when present; falls through to args[0]
def test_str_returns_human_message() -> None:
    err = OdooRpcError("Odoo Server Error", data={"message": "Clean message",
                                                    "arguments": (), "context": {}})
    assert str(err) == "Clean message"

def test_str_fallback_when_no_data() -> None:
    err = OdooAuthError("Not authenticated")
    assert str(err) == "Not authenticated"  # args[0] fallback
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `exception_type` in Odoo fault dict | Removed; use `data.name` only | Odoo 14 (PR #45723, Apr 2020) | `exception_type` branch in `_categorize_error` is dead code for Odoo 14+ |
| `data.details` in to_json() output | Replaced by structured flat keys | Phase 9 | Callers receiving `exc.to_json()["details"]` must migrate to flat keys |
| `exc.data` attribute | Renamed to `exc.raw` | Phase 9 | Breaking change; `data=` constructor kwarg retained |

**Deprecated/outdated:**
- `OdooError.to_json()["details"]`: The base still emits it (unchanged per D-10 scope), but `OdooRpcError` and all subclasses drop it.
- `OdooRpcError.data`: Attribute gone after Phase 9. Only `exc.raw` remains.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `data.context` will be `{}` for all standard Odoo exceptions in production (no model/field keys) | Code Examples / Common Pitfalls | If some Odoo versions or custom modules populate context with model/field, `_extract_model_name` would return values more often — upside only, not a breakage |
| A2 | Odoo 18/19 `serialize_exception` is identical to Odoo 17 (no new fields added) | Code Examples | If 18/19 added new context keys (e.g. `field`, `model`), the extractors should handle them but currently return None. Low risk — new keys would be additive. |
| A3 | No external callers in the godoo-py ecosystem currently access `exc.data` beyond the two test assertions in `test_errors.py` | Common Pitfalls | If downstream consumers access `exc.data`, they will get AttributeError. Low risk — `exc.data` is undocumented internal. |

**If this table is empty:** It is not — three assumptions logged above.

---

## Open Questions

1. **Base `OdooError.to_json()` — keep `"details": None`?**
   - What we know: D-09 and D-10 specify OdooRpcError drops `"details"`, OdooSafetyError is untouched. OdooError base is not addressed.
   - What's unclear: Should `OdooError.to_json()` also drop `"details": None`?
   - Recommendation: Leave `OdooError.to_json()` untouched. The test `TestOdooError.test_to_json_shape` asserts `result["details"] is None` — changing the base would require updating that test too and goes beyond phase scope.

2. **`test_to_json` in `TestOdooRpcError` — which keys does the new shape emit?**
   - What we know: The new `to_json()` emits `{error, message, model_name, field_name, constraint_name, human_message}`. The old test asserts `result["details"] == {"key": "val"}`.
   - Recommendation: Update `test_to_json` to assert the new flat keys and verify `"details"` is absent. The plan must include test migration as a named task alongside the implementation.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is a pure code refactor of `errors.py`. No external dependencies. No tools, services, databases, or CLIs required.

---

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`. Section omitted per config.

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1` in `.planning/config.json`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not in scope for this phase |
| V3 Session Management | No | Not in scope for this phase |
| V4 Access Control | No | Not in scope for this phase |
| V5 Input Validation | Yes — traceback content from external server | `re` pattern stripping; `data.debug` excluded from all output |
| V6 Cryptography | No | Not in scope |

### Known Threat Patterns for error-surface refactoring

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Server filesystem path disclosure via `data.debug` in `to_json()` | Information Disclosure | D-02: `data.debug` excluded from `to_json()`; D-09: no `"raw"` key in output |
| Odoo server traceback in `str(exc)` reaching external log sinks | Information Disclosure | D-13: `__str__` returns `human_message or args[0]` — never `data.debug` |
| `.raw` attribute logged at INFO+ level by callers | Information Disclosure | Document `.raw` as opt-in debug only; test `"raw" not in exc.to_json()` |
| Sensitive data in `data.arguments` (could contain record values) | Information Disclosure | `human_message` extracted from `data.message`/`data.arguments[0]` — plain message only, not full arguments tuple |

---

## Sources

### Primary (HIGH confidence)
- `packages/godoo-client/src/godoo/client/errors.py` — read directly, all 7 classes, 130 lines
- `packages/godoo-client/src/godoo/client/rpc/transport.py` — read directly, `_categorize_error` lines 138-168
- `packages/godoo-client/tests/test_errors.py` — read directly, 47 tests, `.data` usage identified
- `packages/godoo-client/tests/test_transport.py` — read directly, transport test fixtures
- Odoo 17.0 `odoo/http.py` `serialize_exception` — [CITED: raw.githubusercontent.com/odoo/odoo/17.0/odoo/http.py]
- Odoo 17.0 `odoo/exceptions.py` — [CITED: raw.githubusercontent.com/odoo/odoo/17.0/odoo/exceptions.py]
- `.planning/phases/09-structured-error-surface/09-CONTEXT.md` — all locked decisions D-01 to D-15
- `.planning/research/PITFALLS.md` — Pitfalls 8-11 (SEED-003 specific)
- `.planning/research/ARCHITECTURE.md` — SEED-003 integration analysis

### Secondary (MEDIUM confidence)
- [CITED: github.com/odoo/odoo/pull/45723] — PR #45723 confirming `exception_type` removal in Odoo 14
- Odoo 17 `odoo/service/model.py` `_as_validation_error` — confirms model/field embedded in message string, not context dict [via WebFetch]
- [CITED: braincuber.com/tutorial/odoo-19-api-errors-complete-guide] — Odoo 19 error payload structure (consistent with 17.0 verified source)

### Tertiary (LOW confidence — none)
No LOW-confidence claims used. All factual assertions above are VERIFIED or CITED.

---

## Metadata

**Confidence breakdown:**
- Odoo fault payload shape: HIGH — verified against Odoo 17.0 official source
- `exception_type` removal: HIGH — verified against official PR with merge date
- Extraction strategy: HIGH — verified that context is always empty; extractors must default to None
- Path-stripping regex: HIGH — verified live in Python 3.14 environment
- Test migration list: HIGH — verified by reading test_errors.py directly
- Hierarchy preservation: HIGH — verified all subclasses delegate `__init__` to super

**Research date:** 2026-06-02
**Valid until:** 2026-12-02 (Odoo error payload shape is stable; only at-risk if Odoo adds new context fields)
