# Phase 9: Structured Error Surface - Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 2 (1 modified + 1 test file updated)
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/godoo-client/src/godoo/client/errors.py` | exception hierarchy | transform (payload → structured attrs) | itself (current state) | exact — in-place refactor |
| `packages/godoo-client/tests/test_errors.py` | test | transform | itself (current state) | exact — test migration of existing tests |

Both files are self-analogs: this phase is a refactor, not a greenfield addition. The
current code is the starting point and the patterns to copy are extracted from the
current file itself plus the one caller (`transport.py`) that must stay compatible.

---

## Pattern Assignments

### `packages/godoo-client/src/godoo/client/errors.py` (exception hierarchy, transform)

**Analog:** itself — current state is the base to refactor from. `transport.py`
`_categorize_error` is the **read-only call-site** whose signature must be preserved.

---

#### Imports pattern (errors.py lines 1–7)

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from godoo.client.safety import OperationInfo
```

**Phase 9 addition:** `import re` must be added after `from __future__ import
annotations` (stdlib before third-party, per ruff `I` rule). No other imports change.

```python
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from godoo.client.safety import OperationInfo
```

---

#### Module-level compiled regex pattern (new — no existing analog)

Place these constants immediately after the imports and before the first class
definition. Pattern: module-level `SCREAMING_SNAKE` constants for immutable compiled
objects (mirrors `READ_METHODS`/`DELETE_METHODS` frozensets in `safety/__init__.py`
lines 11–29).

```python
# -- Path-stripping patterns (D-03, D-15) ------------------------------------
_POSIX_PATH_RE = re.compile(r'File "(/[^"]+)"')
_WIN_PATH_RE = re.compile(r'File "([A-Za-z]:[^"]+)"')
```

---

#### Private extractor helper pattern (new — no existing analog)

Four module-level `_prefixed` functions returning `str | None`. Pattern mirrors the
private `_categorize_error` method style in `transport.py` (lines 138–168) — defensive
`.get()` access, explicit fallback to `None`, no exceptions raised.

```python
def _strip_paths(text: str) -> str:
    """Replace filesystem paths embedded in Python traceback format strings."""
    text = _POSIX_PATH_RE.sub('File "<server-path>"', text)
    text = _WIN_PATH_RE.sub('File "<server-path>"', text)
    return text


def _extract_human_message(data: dict[str, Any] | None) -> str | None:
    """Return clean human-readable message from fault data, path-stripped as defense-in-depth."""
    if not data:
        return None
    msg: str | None = data.get("message") or None
    if not msg:
        args = data.get("arguments")
        msg = args[0] if args else None
    if msg:
        msg = _strip_paths(msg)
    return msg or None


def _extract_model_name(data: dict[str, Any] | None) -> str | None:
    """Extract Odoo model technical name from fault context dict (e.g. 'res.partner').

    Standard Odoo 17/18/19 exceptions have context={} — returns None in the common case.
    """
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("odoo_model") or ctx.get("model") or None


def _extract_field_name(data: dict[str, Any] | None) -> str | None:
    """Extract field technical name from fault context dict (e.g. 'email')."""
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("field") or ctx.get("field_name") or None


def _extract_constraint_name(data: dict[str, Any] | None) -> str | None:
    """Extract SQL constraint name from fault context dict (e.g. 'res_partner_name_uniq')."""
    if not data:
        return None
    ctx = data.get("context") or {}
    return ctx.get("constraint") or ctx.get("constraint_name") or None
```

---

#### `OdooRpcError.__init__` — current state (errors.py lines 23–35)

```python
def __init__(
    self,
    message: str,
    *,
    code: int | None = None,
    data: dict[str, Any] | None = None,
    cause: Exception | None = None,
) -> None:
    super().__init__(message)
    self.code = code
    self.data = data          # <-- becomes self.raw (D-05)
    if cause is not None:
        self.__cause__ = cause
```

**Phase 9 target shape** — copy this structure, rename `self.data` → `self.raw`,
add four structured fields, add `__str__` override:

```python
def __init__(
    self,
    message: str,
    *,
    code: int | None = None,
    data: dict[str, Any] | None = None,   # kwarg name PRESERVED for transport.py compat (D-06)
    cause: Exception | None = None,
) -> None:
    super().__init__(message)
    self.code = code
    self.raw: dict[str, Any] | None = data           # RENAMED from self.data (D-05)
    self.human_message: str | None = _extract_human_message(data)
    self.model_name: str | None = _extract_model_name(data)
    self.field_name: str | None = _extract_field_name(data)
    self.constraint_name: str | None = _extract_constraint_name(data)
    if cause is not None:
        self.__cause__ = cause                       # error-chaining convention (errors.py:34)

def __str__(self) -> str:
    return self.human_message or self.args[0]        # D-13: never exposes data.debug
```

---

#### `OdooRpcError.to_json()` — current state (errors.py lines 37–42)

```python
def to_json(self) -> dict[str, Any]:
    return {
        "error": "RPC_ERROR",
        "message": str(self),
        "details": self.data,    # <-- leaks raw payload; REMOVED in Phase 9
    }
```

**Phase 9 target shape** — replace `"details"` with four flat structured keys (D-08,
D-09). No `"raw"` key ever emitted:

```python
def to_json(self) -> dict[str, Any]:
    return {
        "error": "RPC_ERROR",
        "message": str(self),
        "model_name": self.model_name,
        "field_name": self.field_name,
        "constraint_name": self.constraint_name,
        "human_message": self.human_message,
        # NO "details" key (removed — was leaking raw payload)
        # NO "raw" key (security gate D-09 — .raw is attribute-only)
    }
```

---

#### Subclass `to_json()` delegation pattern (errors.py lines 58–61, 67–70, etc.)

All five plain subclasses use this identical two-line override. **No changes needed in
any subclass** after the base `to_json()` is reshaped — they inherit the new flat
structure automatically:

```python
# Pattern from OdooAuthError (lines 58–61) — same shape for all subclasses:
def to_json(self) -> dict[str, Any]:
    result = super().to_json()
    result["error"] = "AUTH_ERROR"   # each subclass only changes the "error" key
    return result
```

---

#### `OdooAuthError.__init__` — copy unchanged (errors.py lines 48–56)

This subclass has its own `__init__` solely for the `message` default. The `data=`
kwarg flows through to `super().__init__` unchanged. No modification needed:

```python
def __init__(
    self,
    message: str = "Authentication failed",
    *,
    code: int | None = None,
    data: dict[str, Any] | None = None,
    cause: Exception | None = None,
) -> None:
    super().__init__(message, code=code, data=data, cause=cause)
```

---

#### `OdooSafetyError` — copy unchanged (errors.py lines 109–129)

D-10: left completely untouched. It is not in the `OdooRpcError` hierarchy, already
emits a safe structured `"details"` (OperationInfo), and has no leakage problem.

---

#### `transport.py` call sites — read-only context, not modified

The two call patterns that MUST keep compiling after the rename. Preserved because the
`data=` constructor kwarg is retained (D-06):

```python
# transport.py line 94 — generic raise path
raise self._categorize_error(data["error"])

# transport.py lines 149–168 — _categorize_error returns
return OdooAuthError(message, code=code, data=data)      # line 149
return OdooAccessError(message, code=code, data=data)    # line 151
return OdooValidationError(message, code=code, data=data) # line 153
return OdooMissingError(message, code=code, data=data)   # line 155
# ...and fallback:
return OdooRpcError(message, code=code, data=data)       # line 168
```

All pass `data=data` as keyword argument — the renamed attribute (`self.raw`) is
internal; the constructor kwarg name `data=` survives unchanged.

---

### `packages/godoo-client/tests/test_errors.py` (test, transform)

**Analog:** itself — current state. Migration is mechanical: rename `.data` references,
replace `"details"` key assertions, add new structured-field and privacy-gate tests.

---

#### Imports pattern (test_errors.py lines 1–14) — unchanged

```python
from __future__ import annotations

from godoo.client.errors import (
    OdooAccessError,
    OdooAuthError,
    OdooError,
    OdooMissingError,
    OdooNetworkError,
    OdooRpcError,
    OdooSafetyError,
    OdooTimeoutError,
    OdooValidationError,
)
from godoo.client.safety import OperationInfo
```

---

#### Test cases that MUST be updated (Pitfall 3 — `.data` attribute removal)

**Current tests referencing `err.data` — will raise `AttributeError` after rename:**

```python
# test_errors.py line 52 — MUST change:
assert err.data is None       # → assert err.raw is None

# test_errors.py line 58 — MUST change:
assert err.data == data       # → assert err.raw is data
```

**Current tests asserting `"details"` key — MUST be replaced:**

```python
# test_errors.py line 70 — MUST change:
assert result["details"] == {"key": "val"}
# → assert "details" not in result
# → assert result["model_name"] is None (no context in fixture data)
# → assert result["human_message"] == "val"  (if fixture data has "message" or "arguments")

# test_errors.py line 75 — MUST change:
assert result["details"] is None
# → assert "details" not in result
# → assert result["human_message"] is None   (no data passed)
```

---

#### New test structure to add (success criteria from CONTEXT.md)

Copy the test class structure pattern from `TestOdooRpcError` (lines 43–75). New test
class should be added after `TestOdooRpcError`:

```python
class TestOdooRpcErrorStructuredFields:
    """Tests for Phase 9 structured error surface (ERR-01 … ERR-05)."""

    _FAULT_DATA: dict[str, Any] = {
        "name": "odoo.exceptions.ValidationError",
        "debug": "Traceback (most recent call last):\n  File \"/opt/odoo/addons/account/models.py\", line 42",
        "message": "The field 'name' is required.",
        "arguments": ("The field 'name' is required.",),
        "context": {},
    }

    # ERR-01: structured field access
    def test_human_message_extracted(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert err.human_message == "The field 'name' is required."

    def test_model_name_none_for_empty_context(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert err.model_name is None

    def test_field_name_none_for_empty_context(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert err.field_name is None

    def test_constraint_name_none_for_empty_context(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert err.constraint_name is None

    # ERR-02: privacy gate — no paths/tracebacks in str() or to_json()
    def test_no_server_path_in_str(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert "/opt/odoo" not in str(err)

    def test_no_server_path_in_to_json(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        assert "/opt/odoo" not in str(err.to_json())

    # ERR-03: .raw holds full original dict including data.debug
    def test_raw_holds_full_dict(self) -> None:
        err = OdooRpcError("msg", data=self._FAULT_DATA)
        assert err.raw is self._FAULT_DATA
        assert "debug" in err.raw

    # ERR-04: to_json() never emits "raw" key
    def test_to_json_no_raw_key(self) -> None:
        for cls in [OdooRpcError, OdooAuthError, OdooValidationError,
                    OdooAccessError, OdooMissingError, OdooNetworkError, OdooTimeoutError]:
            err = cls("test", data=self._FAULT_DATA)
            assert "raw" not in err.to_json()

    # ERR-05: .data removed; data= kwarg still accepted; .raw is the new name
    def test_data_attribute_removed(self) -> None:
        err = OdooRpcError("msg", data={"name": "x"})
        assert not hasattr(err, "data")
        assert err.raw == {"name": "x"}

    # D-13: __str__ fallback when no data
    def test_str_fallback_no_data(self) -> None:
        err = OdooAuthError("Not authenticated")
        assert str(err) == "Not authenticated"

    # D-13: __str__ returns human_message when present
    def test_str_returns_human_message(self) -> None:
        err = OdooRpcError("Odoo Server Error", data=self._FAULT_DATA)
        assert str(err) == "The field 'name' is required."

    # ERR-04: to_json() flat structured keys present; no "details" key
    def test_to_json_flat_keys(self) -> None:
        err = OdooValidationError("Odoo Server Error", data=self._FAULT_DATA)
        result = err.to_json()
        assert result["error"] == "VALIDATION_ERROR"
        assert "message" in result
        assert "model_name" in result
        assert "field_name" in result
        assert "constraint_name" in result
        assert "human_message" in result
        assert "details" not in result
        assert "raw" not in result
```

---

#### Tests that remain UNCHANGED

The following test classes require no modifications — they test the class hierarchy and
`error` key values which are unaffected by Phase 9:

- `TestOdooError` (lines 21–36) — tests base class; `"details": None` assertion at
  line 31 stays valid because `OdooError.to_json()` is not modified (D-10 scope).
- `TestOdooAuthError` (lines 83–99) — no `.data` access, no `"details"` assertion.
- `TestOdooNetworkError` (lines 107–120) — no `.data` access, no `"details"` assertion.
- `TestOdooTimeoutError` (lines 128–136) — no `.data` access, no `"details"` assertion.
- `TestOdooValidationError` (lines 144–151) — no `.data` access, no `"details"` assertion.
- `TestOdooAccessError` (lines 159–166) — no `.data` access, no `"details"` assertion.
- `TestOdooMissingError` (lines 174–181) — no `.data` access, no `"details"` assertion.
- `TestOdooSafetyError` (lines 189–226) — entirely outside `OdooRpcError` hierarchy;
  `"details"` key in its output is intentional and preserved (D-10).

---

## Shared Patterns

### Error-chaining convention
**Source:** `errors.py` lines 34–35
**Apply to:** `OdooRpcError.__init__` — unchanged, carry forward as-is
```python
if cause is not None:
    self.__cause__ = cause
```

### `to_json()` subclass delegation
**Source:** `errors.py` lines 58–61 (and repeated for every subclass)
**Apply to:** All 5 subclasses — no changes needed; delegation is preserved
```python
def to_json(self) -> dict[str, Any]:
    result = super().to_json()
    result["error"] = "SUBCLASS_ERROR_CODE"
    return result
```

### `from __future__ import annotations` + TYPE_CHECKING guard
**Source:** `errors.py` lines 1–6
**Apply to:** All modified files — must be first line in every file per project convention

### Module-level private constants (immutable compiled objects)
**Source:** `safety/__init__.py` lines 11–29 (`READ_METHODS`, `DELETE_METHODS` as `frozenset`)
**Apply to:** New `_POSIX_PATH_RE`, `_WIN_PATH_RE` regex constants — same SCREAMING_SNAKE
naming, placed at module level before class definitions

### Defensive dict access pattern
**Source:** `transport.py` `_categorize_error` lines 140–145
**Apply to:** All four `_extract_*` helpers — use `.get()` with `or` fallback, never direct
key access that could `KeyError` on missing/unexpected Odoo payload shapes:
```python
data.get("context") or {}      # safe even when data["context"] is None or missing
data.get("message") or None    # coerce empty string to None
```

---

## No Analog Found

No files in this phase lack an analog. Both files are self-analogs (in-place refactors
of existing code).

---

## Metadata

**Analog search scope:** `packages/godoo-client/src/godoo/client/`, `packages/godoo-client/tests/`
**Files read:** `errors.py` (130 lines), `transport.py` (169 lines), `test_errors.py` (226 lines), `safety/__init__.py` (90 lines)
**Pattern extraction date:** 2026-06-02
