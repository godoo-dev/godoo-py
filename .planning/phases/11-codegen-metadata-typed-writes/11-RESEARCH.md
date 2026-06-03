# Phase 11: Codegen Metadata + Typed Writes — Research

**Researched:** 2026-06-03
**Domain:** Pydantic v2 model metadata, write-serializer design, codegen surgery, OdooClient overloads
**Confidence:** HIGH — all claims verified against current source code and live Pydantic 2.13.4

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Typed write path RAISES on any x2many field present in `model_fields_set`. OdooValidationError whose message points the caller to raw `write()` with command tuples (e.g. `(6, 0, [...])`). x2many writing is NOT supported through the typed path in this phase.

**D-02:** Detection is by codegen-emitted metadata, not Python annotation shape. GEN-01 must additionally emit an x2many/relation marker in `json_schema_extra` (e.g. `{"odoo_x2many": True}` or the field's `ttype`). The write guard keys off that metadata so a genuine scalar `list[int]` field never false-positives. This widens GEN-01's scope beyond just the readonly marker.

**D-03:** Codegen marks a field `json_schema_extra={"odoo_readonly": True}` when `readonly=True OR (store=False AND compute is not None)`. The write serializer excludes these from every write payload (create and write alike).

**D-04:** Deliberate refinement of ROADMAP SC-4. Narrower rule keeps non-stored, non-computed fields writable. Planner action: flag the ROADMAP Phase 11 SC-4 wording for a matching tweak.

**D-05 (TEST-01):** Delivered as both a unit test (respx, runs always) and an integration test (`@integration`, Docker-gated). Unit test mirrors Phase 10 TEST-02 respx pattern.

### Claude's Discretion

- **Generated field emit style:** "Field() only where needed" — plain `name: Optional[T] = None` for ordinary fields, `Field(default=None, json_schema_extra={...})` only for fields that carry readonly/x2many metadata.
- **Write-serializer location:** analogue to `_pydantic_transform.py` (natural home alongside `_odoo_wire_transforms`).
- **`None` → `False` bool nuance:** confirmed via live test — `None` → Odoo `False` for set fields; bool-defaulted fields behave correctly because `__pydantic_fields_set__` tracks explicit `False` too.
- **`create`/`write` overload shape:** dispatch via `hasattr(arg, "__odoo_model__")`.
- **`write(instance)` guard when `instance.id is None`:** raise `OdooValidationError`.

### Deferred Ideas (OUT OF SCOPE)

- Bulk/list typed create-write (single instance only per SC)
- x2many writing via the typed path (explicitly raises — D-01)
- Multi-level relation resolution (REL-ADV-01)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GEN-01 | Codegen emits readonly/x2many metadata into `json_schema_extra` per field | `pydantic_field_str()` in `type_mapper.py` + `codegen.py` field line assembly — surgery is minimal; return 4-tuple or extend current 3-tuple; `FieldSchema` already has `readonly`, `store`, `compute` |
| WRITE-01 | `client.create(instance)` creates record from typed instance, returns id | Overload beside existing `create(model, values)` overloads; dispatch on `hasattr(arg, "__odoo_model__")`; serialize via write-serializer |
| WRITE-02 | `client.write(instance)` updates only explicitly-set fields; never sends unset as `None` | Key API: `instance.model_fields_set` — `set[str]` of field names that were explicitly assigned (verified: same object as `__pydantic_fields_set__`) |
| WRITE-03 | Write serializer: `Ref`→int, `None`→`False`, date/datetime→ISO strings | Mirror of `_odoo_wire_transforms`; reuse `_annotation_mentions_ref` + `Ref.id`; `date.isoformat()` and `datetime.isoformat()` produce correct wire strings |
| WRITE-04 | Readonly/computed fields excluded via GEN-01 metadata | `model_fields[name].json_schema_extra` dict access — verified working in Pydantic 2.13.4 |
| WRITE-05 | x2many set-field raises OdooValidationError pointing to raw `write()` | Detect via `json_schema_extra.get("odoo_x2many")` on fields in `model_fields_set` |
| TEST-01 | E2E test: codegen-generated model → `client.read` → `client.write`, closes 999.3 | Unit: respx fixture pattern from `test_rel_resolution.py`; Integration: `@pytest.mark.integration` + testcontainers pattern |
</phase_requirements>

---

## Summary

Phase 11 adds two coordinated capabilities: (1) codegen learns to stamp `json_schema_extra` metadata onto fields so downstream code knows which fields are read-only or x2many without schema lookups at write time; (2) `client.create`/`client.write` gain typed overloads that accept an `OdooBaseModel` instance, serialize only explicitly-set writable fields, and apply the reverse of the existing wire transforms.

The codebase is in excellent shape for this work. All source data (`readonly`, `store`, `compute`) is already projected into `FieldSchema` by the introspector — GEN-01 needs no new RPC calls. The write-serializer is the logical mirror of `_odoo_wire_transforms` which already lives in `_pydantic_transform.py`, making that module the natural home. The `@overload` additive pattern is established by Phase 10's read dispatch. The test pattern (respx + auth fixture) is established by `test_rel_resolution.py`.

The only non-obvious design points are: (a) `pydantic_field_str()` currently returns a 3-tuple — GEN-01 widens it to carry a `json_schema_extra` fragment dict alongside the annotation; (b) the codegen template path gains a conditional `from pydantic import Field` import and changes the default expression from a bare value to `Field(...)` for fields carrying metadata; (c) `OdooBaseModel` instances use `model_fields_set` (Pydantic v2 public API, identical to `__pydantic_fields_set__`) — confirmed live: explicit `None` assignment IS tracked.

**Primary recommendation:** One wave with two concerns that must sequence correctly — GEN-01 + codegen tests first, then write-serializer + client overloads + TEST-01.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| GEN-01 field metadata emission | Introspection package (`type_mapper.py`, `codegen.py`) | — | Codegen owns the generated field string; no client involvement |
| Write serialization (`Ref`→int, `None`→`False`, dates→ISO) | `_pydantic_transform.py` in client package | — | Mirrors the existing forward transform; keeps transforms co-located |
| `client.create(instance)` / `client.write(instance)` overloads | `client.py` CRUD section | `_pydantic_transform.py` (called lazily) | Additive overloads beside existing dict-accepting signatures |
| x2many guard + OdooValidationError | Write serializer (called from `client.py`) | — | Guard fires before any RPC, same layer as other pre-RPC domain validation |
| TEST-01 unit (respx) | `packages/godoo-client/tests/` | — | Wire-level test; no Docker needed |
| TEST-01 integration | `packages/godoo-client/tests/` (or `tests/` root) with `@integration` | testcontainers | Follows existing integration marker pattern |

---

## Standard Stack

No new packages are introduced. This phase uses what is already installed.

### Core (all already present)

| Library | Version (installed) | Purpose in Phase 11 |
|---------|---------------------|---------------------|
| `pydantic` | 2.13.4 [VERIFIED: live `uv run python -c "import pydantic; print(pydantic.__version__)"`] | `model_fields_set`, `FieldInfo.json_schema_extra`, `Field(default=..., json_schema_extra=...)` |
| `httpx` | existing | Transport — unchanged |
| `respx` | existing | Mock HTTP for unit tests |
| `pytest-asyncio` | existing | `asyncio_mode = "auto"`, session-scoped loop |

### No New Dependencies

Phase 11 introduces no new runtime or test dependencies. All capabilities come from Pydantic 2.13.4 already present. [VERIFIED: live Pydantic install]

---

## Package Legitimacy Audit

> Phase installs no new packages. Audit not applicable.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Codegen path (GEN-01):
  FieldSchema(readonly, store, compute, ttype)
       |
       v
  pydantic_field_str() → (annotation_str, default_expr_str, imports, extra_dict)
       |
       v
  codegen.py: if extra_dict → emit Field(default=..., json_schema_extra={...})
              else            → emit plain `= value`
              if any Field() → add `from pydantic import Field` to header imports

Write path (WRITE-01..05):
  OdooBaseModel instance
       |
       v
  client.create(instance) / client.write(instance)
   [hasattr(arg, "__odoo_model__") dispatch — lazy pydantic import]
       |
       v
  _serialize_for_write(instance) [in _pydantic_transform.py]
    1. Iterate instance.model_fields_set
    2. For each field_name:
       a. Check json_schema_extra["odoo_readonly"] → skip
       b. Check json_schema_extra["odoo_x2many"] → raise OdooValidationError
       c. Get value = getattr(instance, field_name)
       d. Transform: Ref → int; None → False; date/datetime → isoformat(); else → as-is
    3. Return dict[str, Any]
       |
       v
  client.call(model_name, "create"|"write", [payload], {})
       |
       v
  JsonRpcTransport → Odoo wire
```

### Recommended Project Structure

Changes confined to existing files. No new modules are strictly required, though `_write_serializer.py` is an option for the serializer (see Patterns section).

```
packages/
├── godoo-introspection/src/godoo/introspection/
│   ├── type_mapper.py       # GEN-01: widen pydantic_field_str() return
│   └── codegen.py           # GEN-01: consume extra_dict, emit Field(), track Field import
├── godoo-client/src/godoo/client/
│   ├── _pydantic_transform.py   # add _serialize_for_write() (natural home)
│   └── client.py                # WRITE-01/02: add @overload + dispatch branch
└── packages/godoo-client/tests/
    └── test_typed_writes.py     # TEST-01 unit + integration
```

### Pattern 1: GEN-01 — Widening pydantic_field_str()

**What:** The function currently returns a 3-tuple `(annotation_str, default_expr_str, imports_set)`. GEN-01 adds a 4th element: `extra_dict: dict[str, bool]` containing the `json_schema_extra` payload for this field (may be empty `{}`). [VERIFIED: live code inspection of `type_mapper.py:29`]

**Metadata emission rule (D-03 + D-02):**
- `readonly=True OR (store=False AND compute is not None)` → `{"odoo_readonly": True}`
- `ttype in ("one2many", "many2many")` → `{"odoo_x2many": True}` (plus `"odoo_readonly": True` if also readonly)
- otherwise → `{}`

**When to emit `Field()`:** only when `extra_dict` is non-empty. Plain scalar fields stay as `name: Optional[str] = None`.

**Field expression examples:**
```python
# Source: direct code inspection of current codegen.py:140 field_lines.append pattern

# No metadata (majority of fields):
name: Optional[str] = None

# Readonly field:
state: Optional[Literal['draft', 'posted']] = Field(default=None, json_schema_extra={"odoo_readonly": True})

# Computed non-stored (also readonly):
amount_total: Optional[float] = Field(default=None, json_schema_extra={"odoo_readonly": True})

# x2many (currently emits list[int] = []):
invoice_line_ids: list[int] = Field(default_factory=list, json_schema_extra={"odoo_x2many": True})

# x2many AND readonly:
invoice_line_ids: list[int] = Field(default_factory=list, json_schema_extra={"odoo_readonly": True, "odoo_x2many": True})
```

**codegen.py changes:**
```python
# Source: codegen.py:139 — unpack becomes 4-tuple
annotation, default, imports, extra = pydantic_field_str(fs, self._in_set, _model_to_classname)

# Field line assembly:
if extra:
    # list fields: default_factory=list instead of default=[]
    if default == "[]":
        default_expr = f"Field(default_factory=list, json_schema_extra={extra!r})"
    else:
        default_expr = f"Field(default={default}, json_schema_extra={extra!r})"
    need_field_import = True
else:
    default_expr = default

field_lines.append(f"    {field_name}: {annotation} = {default_expr}")
```

**Header `from pydantic import Field` injection:**
```python
# codegen.py — add alongside existing pydantic-import tracking
need_field_import = False  # set to True whenever extra is non-empty

# In header assembly, after `from godoo.client._pydantic_transform import OdooBaseModel`:
if need_field_import:
    lines.append("from pydantic import Field")
```

### Pattern 2: Write Serializer

**Location:** `_pydantic_transform.py` — keeps read and write transforms co-located and symmetrical. [ASSUMED] (alternative: standalone `_write_serializer.py`; see Open Questions)

**Implementation:**
```python
# Source: design grounded in _odoo_wire_transforms at _pydantic_transform.py:125
# and verified Pydantic 2.13.4 field API

def _serialize_for_write(instance: OdooBaseModel) -> dict[str, Any]:
    """Serialize an OdooBaseModel instance to an Odoo write payload.

    Only fields in model_fields_set are included. Readonly fields (json_schema_extra
    odoo_readonly=True) are excluded. x2many fields (odoo_x2many=True) in the set
    raise OdooValidationError. Transformations:
      Ref  → int (bare id)
      None → False (Odoo wire convention for cleared fields)
      date/datetime → ISO-format string
    """
    from godoo.client.errors import OdooValidationError  # lazy: avoids circular at module load

    payload: dict[str, Any] = {}
    for field_name in instance.model_fields_set:
        fi = instance.__class__.model_fields.get(field_name)
        if fi is None:
            continue
        extra = fi.json_schema_extra
        extra_dict = extra if isinstance(extra, dict) else {}

        # WRITE-04: skip readonly/computed
        if extra_dict.get("odoo_readonly"):
            continue

        # WRITE-05: raise on x2many
        if extra_dict.get("odoo_x2many"):
            raise OdooValidationError(
                f"Field {field_name!r} is an x2many relation and cannot be written via the typed path. "
                "Use client.write(model, ids, {field: [(6, 0, [ids])]}) with command tuples instead."
            )

        value = getattr(instance, field_name)

        # Ref → bare int id
        if isinstance(value, Ref):
            payload[field_name] = value.id
            continue

        # None (explicitly set) → Odoo False
        if value is None:
            payload[field_name] = False
            continue

        # date/datetime → ISO string (datetime before date — datetime subclasses date)
        if isinstance(value, datetime):
            payload[field_name] = value.isoformat()
            continue
        if isinstance(value, date):
            payload[field_name] = value.isoformat()
            continue

        payload[field_name] = value

    return payload
```

**Bool-defaulted field nuance (read-side D-02 mirror):**
`model_fields_set` tracks `False` when explicitly passed: `M(flag=False)` → `"flag" in instance.model_fields_set`. For a bool field, `value is None` will never be True (type is `bool`, not `Optional[bool]`), so the `None → False` branch never fires for a set bool field. Bool fields set to `False` correctly pass through as-is. [VERIFIED: live test — `m.model_fields_set` contains `"flag"` when `M(flag=False)` called]

### Pattern 3: client.py Overloads

**Pattern:** additive `@overload` beside existing create/write signatures, dispatch via `hasattr(arg, "__odoo_model__")`. Same structure as Phase 10 read dispatch. [VERIFIED: current code at client.py:512-534]

```python
# Source: mirrors Phase 10 read() overload pattern at client.py:212-235

@overload
async def create(self, instance: OdooBaseModel) -> int: ...

@overload
async def create(self, model: str, values: dict[str, Any], **kwargs: Any) -> int: ...

@overload
async def create(self, model: str, values: list[dict[str, Any]], **kwargs: Any) -> list[int]: ...

async def create(  # type: ignore[misc]
    self,
    model: Any,
    values: Any = None,
    **kwargs: Any,
) -> int | list[int]:
    # Typed dispatch
    if hasattr(model, "__odoo_model__"):
        instance = model  # OdooBaseModel instance
        try:
            from godoo.client._pydantic_transform import _serialize_for_write
        except ModuleNotFoundError as exc:
            raise OdooValidationError(
                "Typed writes require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
            ) from exc
        payload = _serialize_for_write(instance)
        return cast("int", await self.call(instance.__odoo_model__, "create", [payload], kwargs))
    # ... existing dict path unchanged
```

```python
# write() typed overload
@overload
async def write(self, instance: OdooBaseModel) -> bool: ...

@overload
async def write(
    self,
    model: str,
    ids: int | list[int],
    values: dict[str, Any],
    **kwargs: Any,
) -> bool: ...

async def write(  # type: ignore[misc]
    self,
    model: Any,
    ids: Any = None,
    values: Any = None,
    **kwargs: Any,
) -> bool:
    # Typed dispatch
    if hasattr(model, "__odoo_model__"):
        instance = model  # OdooBaseModel instance
        if instance.id is None:
            raise OdooValidationError(
                f"Cannot write {instance.__odoo_model__!r}: instance.id is None (record not yet created)."
            )
        try:
            from godoo.client._pydantic_transform import _serialize_for_write
        except ModuleNotFoundError as exc:
            raise OdooValidationError(
                "Typed writes require 'pydantic'. Install with: pip install 'godoo-client[typed]'"
            ) from exc
        payload = _serialize_for_write(instance)
        return cast("bool", await self.call(instance.__odoo_model__, "write", [[instance.id], payload], kwargs))
    # ... existing dict path unchanged
```

**Mypy overload note:** `# type: ignore[misc]` is used by the existing `read()` implementation (client.py:236) when the overloads are numerous. Same pattern applies here.

### Anti-Patterns to Avoid

- **Detecting x2many by annotation shape (`list[int]`):** A genuine scalar `list[int]` field (non-relational) would false-positive. Always key off `json_schema_extra["odoo_x2many"]`. (D-02 in CONTEXT.md)
- **Importing pydantic at module level in client.py:** The project pattern is lazy import inside the dispatch branch body. Violating this breaks the no-pydantic-at-module-level invariant (D-04).
- **Sending `None` as-is:** Odoo expects `False` to clear a field on the wire, not `None`. The serializer must map `None → False` for explicitly-set fields.
- **Skipping the `id` field guard on `write(instance)`:** Writing an instance with `id=None` would issue `write([[None], {...}])` which is an Odoo error. Validate before RPC.
- **Using `model.dict()` or `model.model_dump()`:** These return ALL fields (default-filled), not just the explicitly-set ones. Must iterate `model_fields_set` directly.
- **Breaking existing dict-based `create`/`write` callers:** The overloads are purely additive. Existing call sites `client.create("res.partner", {...})` must continue to work unchanged.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Which fields were explicitly set?" | Custom tracking dict / `__setattr__` override | `instance.model_fields_set` (Pydantic v2 built-in) | Already a `set[str]` tracking every field touched during construction or assignment [VERIFIED: live] |
| "Read field metadata at runtime" | Custom class attribute or registry | `Model.model_fields[name].json_schema_extra` | Pydantic stores `FieldInfo` with `json_schema_extra` at class level [VERIFIED: live] |
| Ref → int conversion | Custom branch in client.py | Reuse `Ref.id` directly | `Ref` is a frozen dataclass with `.id: int`; `isinstance(value, Ref)` is the guard [VERIFIED: typed.py:22] |
| ISO-string serialization | `strftime` or custom format | `date.isoformat()` / `datetime.isoformat()` | These produce `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS` which exactly match Odoo's wire expectations [VERIFIED: live] |

---

## Key Verified Facts

### Pydantic 2.13.4 — model_fields_set behaviour [VERIFIED: live]

- `instance.model_fields_set` and `instance.__pydantic_fields_set__` are the **same object** (a `set[str]`).
- Public API to prefer: `model_fields_set` (the property, per Pydantic v2 docs).
- Tracks every field that was explicitly provided during construction or later assigned:
  - `M(id=1, x=None)` → `model_fields_set == {"id", "x"}` (explicit `None` IS tracked)
  - `M(id=1)` → `model_fields_set == {"id"}` (unset `x` is NOT in the set)
  - `M(flag=False)` → `model_fields_set` contains `"flag"` (explicit `False` IS tracked)
- Default-constructed fields (never explicitly passed) are NOT in `model_fields_set`.

### Pydantic 2.13.4 — json_schema_extra access [VERIFIED: live]

- `Model.model_fields[name].json_schema_extra` returns the dict passed to `Field(json_schema_extra=...)`.
- For fields without `json_schema_extra`, returns `None`.
- Safe pattern: `extra = fi.json_schema_extra; isinstance(extra, dict) and extra.get("odoo_readonly")`.

### FieldSchema — data available for GEN-01 [VERIFIED: types.py + introspector.py:282-302]

`FieldSchema` already carries `readonly: bool`, `store: bool`, `compute: str | None` — all three columns needed to apply D-03 without any new introspector RPC:
- Readonly rule: `field.readonly or (not field.store and field.compute is not None)`
- x2many detection: `field.ttype in ("one2many", "many2many")`

### Current codegen output (baseline) [VERIFIED: live codegen run]

Current `pydantic_field_str()` returns a 3-tuple. For a model with `state` (readonly selection), `amount_total` (computed non-stored float), and `invoice_line_ids` (one2many), the current output is:
```python
state: Optional[Literal['draft', 'posted']] = None       # no metadata
amount_total: Optional[float] = None                      # no metadata
invoice_line_ids: list[int] = []                          # no metadata
```

After GEN-01:
```python
state: Optional[Literal['draft', 'posted']] = Field(default=None, json_schema_extra={"odoo_readonly": True})
amount_total: Optional[float] = Field(default=None, json_schema_extra={"odoo_readonly": True})
invoice_line_ids: list[int] = Field(default_factory=list, json_schema_extra={"odoo_x2many": True})
```

### Current client.py write/create signatures [VERIFIED: client.py:512-545]

```python
# Line 512-534 (create)
@overload
async def create(self, model: str, values: dict[str, Any], **kwargs: Any) -> int: ...

@overload
async def create(self, model: str, values: list[dict[str, Any]], **kwargs: Any) -> list[int]: ...

async def create(self, model: str, values: dict[str, Any] | list[dict[str, Any]], **kwargs: Any) -> int | list[int]:
    ...

# Line 536-545 (write)
async def write(self, model: str, ids: int | list[int], values: dict[str, Any], **kwargs: Any) -> bool:
    ...
```

`write` currently has NO overloads — the typed overload must be added alongside a new `# type: ignore[misc]` implementation signature.

---

## Common Pitfalls

### Pitfall 1: model_dump() returns all fields, not just set ones

**What goes wrong:** `instance.model_dump()` / `instance.model_dump(exclude_unset=False)` returns all fields with their defaults. Using it instead of iterating `model_fields_set` sends unset fields (e.g. `name: None`) to Odoo, overwriting existing values.
**Why it happens:** `model_dump` is the standard Pydantic serialization surface; forgetting `exclude_unset=True`.
**How to avoid:** Always iterate `instance.model_fields_set` directly — never call `model_dump()` in the write-serializer.
**Warning signs:** Unit test sees more keys in the write payload than were set on the fixture instance.

### Pitfall 2: pydantic_field_str() change breaks codegen tests

**What goes wrong:** The 3-tuple return changes to a 4-tuple. Every existing unpack in `codegen.py` and `test_codegen.py` / `test_type_mapper.py` must be updated.
**Why it happens:** `annotation, default, imports = pydantic_field_str(...)` destructures to exactly 3 values.
**How to avoid:** Update the unpack in `codegen.py:139` first, then update all test fixtures that inspect `pydantic_field_str` return values.
**Warning signs:** `ValueError: too many values to unpack` at test time.

### Pitfall 3: list[int] default expression conflict

**What goes wrong:** x2many fields currently emit `list[int] = []`. When metadata is added, `Field(default=[], ...)` is illegal (Pydantic requires `default_factory=list` for mutable defaults).
**Why it happens:** `[]` is a mutable default — Pydantic v2 rejects it with `PydanticUserError`.
**How to avoid:** In codegen, when `extra` is non-empty AND `default == "[]"`, emit `Field(default_factory=list, json_schema_extra=...)` not `Field(default=[], ...)`.
**Warning signs:** `pydantic.errors.PydanticUserError: A non-annotated attribute was detected` or similar on model import.

### Pitfall 4: Breaking existing create() dict callers

**What goes wrong:** Adding a new first-positional-arg overload `create(instance: OdooBaseModel)` where the instance also has `__odoo_model__` can confuse the implementation dispatch.
**Why it happens:** `hasattr(model, "__odoo_model__")` fires on an OdooBaseModel subclass — but existing calls pass a str. Str does not have `__odoo_model__`, so the str path is unaffected. The risk is in the implementation signature arity change.
**How to avoid:** The typed dispatch checks `hasattr(model, "__odoo_model__")` first — strings will never have that attribute. Regression test: existing `client.create("res.partner", {...})` pattern must be covered.
**Warning signs:** Mypy type errors in existing test files calling `create`/`write` with str+dict.

### Pitfall 5: Forgetting the ROADMAP SC-4 wording note

**What goes wrong:** ROADMAP Phase 11 SC-4 reads `readonly=True OR store=False`. D-04 narrows this to `readonly=True OR (store=False AND compute is not None)`. If planner does not note this, the plan checker may flag SC-4 as unmet.
**Why it happens:** D-04 is documented in CONTEXT.md but ROADMAP.md SC-4 was not updated.
**How to avoid:** Planner task must include a one-line update to ROADMAP.md SC-4 wording.
**Warning signs:** Plan checker flags SC-4 as mismatched with implementation.

### Pitfall 6: False → False for bool fields in write direction

**What goes wrong:** The write serializer's `None → False` branch must NOT also convert `False → False` for bool fields (they're already `False`, not `None`). The read-side preserves `False` for bool fields; the write-side simply passes `False` through unchanged.
**Why it happens:** Misreading D-02 (read-side bool preservation) as requiring special write-side logic when none is needed.
**How to avoid:** The write serializer only needs `None → False`. `False` values on bool fields are not `None`, so the `value is None` check correctly skips them. No special bool branch is needed in the write direction.

---

## Code Examples

### Reading json_schema_extra at runtime

```python
# Source: verified against Pydantic 2.13.4 live
fi = instance.__class__.model_fields.get(field_name)
extra = fi.json_schema_extra if fi is not None else None
extra_dict: dict[str, object] = extra if isinstance(extra, dict) else {}
is_readonly = bool(extra_dict.get("odoo_readonly"))
is_x2many = bool(extra_dict.get("odoo_x2many"))
```

### Iterating model_fields_set for write

```python
# Source: verified against Pydantic 2.13.4 live
payload: dict[str, Any] = {}
for field_name in instance.model_fields_set:
    value = getattr(instance, field_name)
    # transform value here
    payload[field_name] = transformed_value
```

### respx test skeleton (mirrors test_rel_resolution.py pattern)

```python
# Source: test_rel_resolution.py:67-77 + test_typed_dispatch.py:62-73

@respx.mock
@pytest.mark.asyncio
async def test_typed_write_sends_correct_payload(auth_client: OdooClient) -> None:
    respx.post(f"{BASE_URL}/jsonrpc").mock(
        return_value=httpx.Response(200, json=_jsonrpc_result(True))
    )
    instance = SomeModel(id=1, name="Updated")
    result = await auth_client.write(instance)
    assert result is True
    # Inspect the captured request payload
    request_body = respx.calls[0].request.content
    ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TypedDict` codegen (Phase 6) | `OdooBaseModel` (Pydantic `BaseModel`) codegen | v1.1 / Phase 7 | `model_fields_set` is available; TypedDict had no equivalent |
| `model_dump(exclude_unset=True)` | iterate `model_fields_set` | N/A | `model_dump(exclude_unset=True)` would also work as an alternative for building the base payload, but does not give per-field annotation access needed for Ref/date transforms |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Write-serializer lives in `_pydantic_transform.py` (not a new `_write_serializer.py`) | Architecture Patterns | Low risk; either location works; planner finalizes based on module cohesion preference |
| A2 | `create(instance)` returns a single `int` (not `list[int]`) — per SC which says "returns the new record id" | Pattern 3: client.py Overloads | If Odoo actually returns a list for a single create, the cast would be wrong — but single-instance creates are confirmed to return bare int by existing tests |

---

## Open Questions

1. **Write-serializer module location**
   - What we know: `_pydantic_transform.py` is the natural home (symmetry with `_odoo_wire_transforms`); the lazy-import rule means client.py imports it inside the dispatch branch anyway.
   - What's unclear: Is the module large enough that splitting out a `_write_serializer.py` improves readability?
   - Recommendation: Default to `_pydantic_transform.py`; planner decides at task-creation time based on predicted final module size.

2. **`pydantic_field_str()` return type extension approach**
   - What we know: currently returns `tuple[str, str, frozenset[str]]`; GEN-01 needs a 4th element.
   - What's unclear: Return a 4-tuple `tuple[str, str, frozenset[str], dict[str, bool]]`, or add a named dataclass?
   - Recommendation: 4-tuple with documented contract; consistent with existing 3-tuple style and avoids adding a new dataclass.

3. **SC-4 ROADMAP update wording**
   - What we know: D-04 narrows `readonly=True OR store=False` to `readonly=True OR (store=False AND compute is not None)`.
   - Recommendation: Planner inserts a task in Wave 1 to update the ROADMAP SC-4 line (one-line text change) so plan checker and verifier see a consistent spec.

---

## Environment Availability

Step 2.6: All dependencies (Python 3.14, uv, Pydantic 2.13.4, respx, pytest-asyncio) confirmed present from prior phase work. No new external tools required.

Docker for integration test: required by `@pytest.mark.integration`. Already used by Phase 10 testcontainers; no new setup needed.

---

## Security Domain

> `security_enforcement: true` (from `.planning/config.json`), ASVS level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — this phase does not touch auth |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes | `OdooValidationError` raised pre-RPC for x2many fields and `id is None` guard |
| V6 Cryptography | no | n/a |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Readonly-field bypass (client passes readonly field via explicit set) | Tampering | Write serializer unconditionally skips `odoo_readonly=True` fields regardless of `model_fields_set` |
| x2many command injection (REPLACE via `list[int]`) | Tampering | Write serializer raises `OdooValidationError` before any RPC if an x2many field is in `model_fields_set` |
| Unset-field leakage (sending `None` for unset fields, overwriting DB values) | Tampering | Serializer iterates `model_fields_set` — never iterates all declared fields |

---

## Sources

### Primary (HIGH confidence)

- Current source code read directly:
  - `packages/godoo-client/src/godoo/client/_pydantic_transform.py` — OdooBaseModel, wire transforms, Ref helpers
  - `packages/godoo-introspection/src/godoo/introspection/type_mapper.py` — current pydantic_field_str() return shape
  - `packages/godoo-introspection/src/godoo/introspection/codegen.py` — field line assembly, import tracking
  - `packages/godoo-introspection/src/godoo/introspection/types.py` — FieldSchema.readonly/store/compute confirmed present
  - `packages/godoo-client/src/godoo/client/client.py` — current create/write signatures (L512-545)
  - `packages/godoo-client/src/godoo/client/typed.py` — Ref.id confirmed int
  - `packages/godoo-testcontainers/tests/test_integration.py` — integration marker pattern
  - `packages/godoo-client/tests/test_rel_resolution.py` — respx auth_client fixture pattern
- Live Pydantic 2.13.4 verification:
  - `model_fields_set` type, identity with `__pydantic_fields_set__`, explicit-None tracking
  - `Field(json_schema_extra=...)` stores in `FieldInfo.json_schema_extra`
  - `default_factory=list` required for mutable defaults with `Field()`
  - `date.isoformat()` / `datetime.isoformat()` wire string format

### Secondary (MEDIUM confidence)

- Planning artifacts: `.planning/phases/11-codegen-metadata-typed-writes/11-CONTEXT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md` — all consistent with each other

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all verified against installed packages and live source
- GEN-01 surgery sites: HIGH — read actual type_mapper.py and codegen.py line by line
- Write-serializer design: HIGH — verified Pydantic field API live; serializer logic derived from existing _odoo_wire_transforms
- client.py overload pattern: HIGH — read existing create/write and Phase 10 read overloads
- Pitfalls: HIGH — all derived from actual code inspection, not training-data heuristics

**Research date:** 2026-06-03
**Valid until:** 2026-07-03 (stable library stack; Pydantic 2.x API stable)
