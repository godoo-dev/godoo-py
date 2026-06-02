# Pitfalls Research

**Domain:** godoo-py v1.2 — Typed Relations (TYPED-F1), Typed Writes (TYPED-F2), Error Hierarchy Restructure (SEED-003)
**Researched:** 2026-06-02
**Confidence:** HIGH (all pitfalls grounded in the actual codebase: `_pydantic_transform.py`, `client.py`, `errors.py`, `transport.py` read directly)

---

## Critical Pitfalls

### Pitfall 1: Typed Write — Sending Read-Only / Computed / Related Fields Back to Odoo

**What goes wrong:**
A caller reads a `res.partner` record into a `ResPartner` Pydantic model and immediately calls `client.write(partner)`. The serialized payload includes computed fields (`display_name`, `__last_update`, `create_date`, `write_date`, `create_uid`, `write_uid`) and relational pseudo-fields (`parent_name`, `commercial_partner_id`). Odoo silently ignores some of these. Others raise a server-side `ValidationError` ("You cannot set a value for a computed field"). The caller sees an opaque `OdooValidationError` with no indication of which field caused it. In the worst case (Odoo silently ignores) the write appears to succeed but a stale computed value was round-tripped, masking the actual stored value on the next read.

**Why it happens:**
The Pydantic model is generated from the live schema via `ir.model.fields`. The codegen produces one field per schema entry — it does not distinguish `store=True` from `store=False` or `readonly=True`. When serializing for write, a naive `model.model_dump(exclude_none=True)` emits every non-None field including `display_name` and `write_date`.

**How to avoid:**
- The serializer for write must explicitly exclude fields where `readonly=True` or `store=False` in the schema. Two mechanisms:
  - **Preferred:** The codegen annotates each field with a Pydantic `Field(json_schema_extra={"odoo_readonly": True})` marker; the write serializer calls `model.model_dump(exclude={f for f, info in model.model_fields.items() if info.json_schema_extra and info.json_schema_extra.get("odoo_readonly")})`.
  - **Alternative:** The write serializer always excludes a hardcoded set of universal Odoo computed fields (`display_name`, `__last_update`, `create_date`, `write_date`, `create_uid`, `write_uid`, `id`) plus excludes all fields annotated `readonly=True` in the Pydantic model metadata.
- The codegen phase (Phase 7 / TYPED-01) must be extended to emit the `readonly` and `store` metadata from `fields_get()` into each generated field's `Field(...)` extras, otherwise TYPED-F2 has no way to know which fields to exclude.
- A typed write should never serialize `id` — the id is passed separately as the record identifier, not as a writable value.

**Warning signs:**
- Integration test writes a freshly-read model back and passes without checking which fields were actually sent in the RPC payload.
- The codegen does not include `readonly` or `store` metadata in the generated `Field(...)`.
- `model.model_dump()` in the write path includes `display_name` in its output.

**Phase to address:** TYPED-F2 — must be decided at the serializer design step, not discovered during integration testing.

---

### Pitfall 2: Typed Write — Incorrect Wire Format for Many2one Fields

**What goes wrong:**
On read, Odoo returns a many2one field as `[1234, "Partner Name"]` — the wire transform converts this to `Ref(id=1234, name="Partner Name")`. On write, the caller wants to set a many2one field to a different partner. The **correct write format** is a bare integer id: `{"partner_id": 5678}`. The **wrong formats** that callers will naturally produce are:
- `{"partner_id": [5678, "New Partner"]}` — Odoo raises `ValidationError: wrong value for ... expected int, got list`.
- `{"partner_id": Ref(id=5678, name="New Partner")}` — serializes to a Python dataclass repr or fails JSON serialization entirely.
- `{"partner_id": {"id": 5678, "name": "New Partner"}}` — Odoo raises `ValidationError: wrong value for ... expected int, got dict`.
- `{"partner_id": None}` — Odoo may raise a required-field constraint violation if the field is required, or silently ignore it, or set it to False depending on the model.

**Why it happens:**
The `Ref` dataclass is introduced by the read-side wire transform. When developers see `partner.partner_id = Ref(id=5678, name="...")` and then serialize the model for writing, the natural serialization of `Ref` is not the bare int that Odoo expects.

**How to avoid:**
- The write serializer must invert the `Ref → [id, name]` read transform: serialize any `Ref`-annotated field as `ref.id` (bare integer). This applies whether the caller set the field to a new `Ref` or preserved the original.
- `None` for a many2one field serializes as `False` on the wire — this is the Odoo convention for clearing a many2one. The serializer must map `None → False` for fields annotated with `Ref[T] | None`.
- A `Ref` with `id=0` or `id=False` is invalid — validate before serialization and raise `OdooValidationError` locally.
- The serializer module (`_pydantic_transform.py` or a new `_write_transform.py`) should implement `serialize_for_write(model) -> dict[str, Any]` as the single authoritative entry point.

**Warning signs:**
- The write path uses `model.model_dump()` or `model.model_dump(mode="json")` without a custom serializer for `Ref` fields — Pydantic's JSON mode will serialize `Ref` as `{"id": ..., "name": ...}`.
- Integration tests only test writing scalar fields (str, int, bool), never a many2one field.
- No test that writes `partner_id=None` (clearing a many2one) and verifies the wire payload contains `False`, not `None`.

**Phase to address:** TYPED-F2 — the write serializer is the core implementation challenge. Must have explicit round-trip tests: read a record, modify a Ref field, write back, read again, assert the related record changed.

---

### Pitfall 3: Typed Write — x2many Fields Require Command Tuples, Not Lists of Ids

**What goes wrong:**
A `one2many` or `many2many` field (e.g., `invoice_line_ids`, `tag_ids`) on a generated model is annotated `list[int]` (the read-side representation after the wire transform). The caller reads a record, sees `invoice.invoice_line_ids = [101, 102, 103]`, removes one id from the list, and writes the model back. The serialized payload `{"invoice_line_ids": [101, 102]}` is **not valid** for Odoo write. The correct format is x2many command tuples:

```python
# Replace entire set:  (6, 0, [101, 102])
# Add existing record: (4, 103)
# Remove (unlink):     (2, 103)
# Disconnect (no delete): (3, 103)
```

Odoo raises `ValueError: Invalid value for ... expected list of (int, int, dict) tuples` or silently fails depending on the Odoo version.

**Why it happens:**
The read-side represents x2many fields as `list[int]` (ids only, after the wire transform from the raw `[101, 102, 103]` returned by Odoo). The symmetric write format looks like it should also accept `list[int]`. It does not. The write API requires explicit command semantics.

**How to avoid:**
- x2many fields **cannot be round-tripped transparently**. The write serializer must either:
  - **Exclude x2many fields entirely** from write unless the caller explicitly provides command tuples via a dedicated API (e.g., `model.set_many2many("tag_ids", [(6, 0, new_ids)])`) — this is the safest option.
  - **Accept a `list[int]` and convert to `(6, 0, ids)` (replace)** — correct only if the caller means "replace the entire set." Document this behavior explicitly.
  - **Raise `OdooValidationError` locally** if an x2many field is included in the write payload and the value is a plain `list[int]` — force the caller to use command tuples explicitly.
- The codegen for TYPED-F2 must distinguish `one2many` / `many2many` from scalar fields and annotate them with a marker in `Field(json_schema_extra={"odoo_x2many": True})` so the serializer can apply the right strategy.
- Do not silently wrap `list[int]` as `(6, 0, ids)` without documenting it — callers who only add one record will accidentally remove the others.

**Warning signs:**
- The write path applies `model.model_dump()` with no special handling for list-of-int x2many fields.
- Integration tests only test models with no x2many fields (e.g., `res.partner` without `child_ids`).
- No test that explicitly verifies the command-tuple format is emitted in the RPC payload for x2many fields.

**Phase to address:** TYPED-F2 — explicitly decide the x2many strategy (exclude / replace / error) at design time before implementation.

---

### Pitfall 4: Typed Write — `False` vs `None` vs Omitted on Write (Partial Update Semantics)

**What goes wrong:**
Odoo's write API semantics for omitted vs `None` vs `False` differ by field type:

- **Omitted field:** Not touched — the server value is unchanged. Correct for partial updates.
- **`False`:** The Odoo convention for "clear this field." For `char` fields: `False` sets the value to `False` (which Odoo stores/reads as `False` — treated as empty string in display). For `many2one`: `False` clears the relation. For `boolean`: `False` sets the boolean to false.
- **`None` / `null` in JSON:** Odoo's `web` controller and `xmlrpc`/`jsonrpc` endpoint accept `null` for some fields and raise for others. Behavior is model-dependent and server-version-dependent.

The v1.1 `_pydantic_transform.py` correctly maps Odoo `False → None` on the **read** side. The **write** side must perform the inverse: `None → False` for fields that were `None` because Odoo sent `False`. But for a **partial update**, fields that are `None` because the caller never set them (they were `None` in the model due to `All-Optional partial-read semantics` from D-01) must be **omitted entirely**, not sent as `False`.

A naive `model.model_dump(exclude_none=True)` silently omits all `None` fields — which is correct for partial updates but wrong if the caller explicitly set a field to `None` intending to clear it.

**Why it happens:**
After D-01 (All-Optional fields with `= None` defaults), there is no runtime distinction between "field was never set" and "field was explicitly set to None to clear it" unless the caller uses an explicit sentinel. Pydantic v2 has `__pydantic_fields_set__` to track which fields were set by the caller — this is the only reliable discriminator.

**How to avoid:**
- The write serializer must use `model.__pydantic_fields_set__` to determine which fields to include:
  - Field in `__pydantic_fields_set__` + value is `None` → send as `False` (caller is clearing the field).
  - Field in `__pydantic_fields_set__` + value is not `None` → serialize normally.
  - Field NOT in `__pydantic_fields_set__` → omit entirely (partial update, do not touch).
- A `Ref`-annotated field explicitly set to `None` → send `False` (clear the many2one relation).
- For `create` (new records), there is no "partial" concept — unset optional fields should be omitted (Odoo uses server defaults), which `exclude_none=True` handles correctly.

**Warning signs:**
- The write serializer uses `model.model_dump(exclude_none=True)` without consulting `__pydantic_fields_set__`.
- No test that: (1) reads a model with partial fields, (2) explicitly sets one field to `None`, (3) writes back, and (4) verifies only the explicitly-set field appears in the RPC payload.
- No test that verifies `None` for a Ref field is sent as `False`, not `null`.

**Phase to address:** TYPED-F2 — this is the subtlest write semantic. Must be documented in the public API and verified in tests.

---

### Pitfall 5: Typed Relation Resolution — N+1 RPC Storm from Naive `client.read(ref)` Per Record

**What goes wrong:**
A caller fetches 200 `account.move` records. Each has a `partner_id: Ref[ResPartner]`. Calling `client.read(ref)` for each partner separately produces 200 sequential RPC calls — one per record. With a typical Odoo instance latency of 50ms per RPC, that is 10 seconds for what should be a single batched `search_read`.

**Why it happens:**
The `Ref[T]` type carries only `id` and `name`. Resolution to the full model requires a read call. If the resolution API is `client.read(ref)` per-ref without batching, callers who loop over records will naturally hit the N+1 pattern, especially because the single-ref API makes it look cheap.

**How to avoid:**
- The primary API for TYPED-F1 must be `client.read(list[Ref[T]])` — batch first, single-ref second. Make the batch form the natural path by not providing `client.read(single_ref)` as a primary API (or by making it internally batch a list of one).
- The batch implementation groups refs by target model (`Ref.__class_getitem__` parameter, i.e., `T`): one `search_read` per distinct `__odoo_model__` across all refs in the list.
- Deduplication: a list of 200 refs where 50 have the same partner id must send ids `{1, 2, ..., n}` deduplicated — never `[1, 1, 1, ...]` in the `ids` RPC argument.
- After the batch RPC, stitch results back to the original ref list by id. A ref that appears multiple times in the input returns the same resolved instance (deduplicated map lookup).
- The API must make the batching contract visible — docstring: "Resolves all refs in a single RPC per distinct target model. Pass a list even for one ref."

**Warning signs:**
- A single-ref convenience method `client.read(ref: Ref[T])` that does not internally queue into a batch.
- Integration test only resolves one ref at a time.
- No test that asserts the number of RPC calls made during resolution of 10 refs to the same model equals 1, not 10.

**Phase to address:** TYPED-F1 — the batch-first design is the entire value proposition of this feature. Must be the core architectural decision.

---

### Pitfall 6: Typed Relation Resolution — Untyped `Ref[int]` With No Target Class

**What goes wrong:**
The codegen emits `Ref[int]` for many2one fields where the target model is not known (e.g., `reference` type fields, or fields where `ir.model.fields.relation` is empty). If TYPED-F1 tries to resolve a `Ref[int]`, there is no `__odoo_model__` to dispatch to — the resolution must fail. The failure mode matters:

- **Silent skip:** Returns the `Ref` unresolved without warning. The caller thinks resolution succeeded.
- **Generic read without type:** Resolves to `dict[str, Any]` instead of a typed model. Breaks the return type contract.
- **AttributeError crash:** `get_args(Ref[int])[0].__odoo_model__` raises `AttributeError: type object 'int' has no attribute '__odoo_model__'`.

**Why it happens:**
`Ref[int]` is a valid annotation for an unresolved m2o where the target model is not introspected. The `T` in `Ref[T]` is intended to be a concrete `OdooBaseModel` subclass, but the codegen emits `Ref[int]` as a fallback. TYPED-F1 must handle this case without crashing.

**How to avoid:**
- Before attempting resolution, check `get_args(ref_annotation)[0]` for the presence of `__odoo_model__`. If absent (`int` or any non-model type), raise a clear `OdooValidationError("Cannot resolve Ref[int]: target model unknown. Use client.read(model_class, [ref.id]) with an explicit model class.")` — never silently skip or crash with `AttributeError`.
- The batch resolver should validate all refs in the input list before issuing any RPC calls — fail fast with a clear error listing which refs are unresolvable, rather than failing mid-batch after some RPCs have been issued.
- The codegen should be updated to emit `Ref["account.move"]` (string model name) rather than `Ref[int]` wherever the target model name is known but no generated class exists yet — enabling future resolution even before the target class is generated.

**Warning signs:**
- `client.read(list[Ref])` accepts `Ref[int]` without error and silently returns the input refs unchanged.
- No test that passes a `Ref[int]` to the resolution API and asserts a clear error is raised.
- `get_args()` call on the type parameter without a guard for `int` or other non-model types.

**Phase to address:** TYPED-F1 — the type guard is a one-liner but must be explicit in the implementation spec.

---

### Pitfall 7: Typed Relation Resolution — Mixed-Model Ref Lists and Zero/Falsy IDs

**What goes wrong:**
Two sub-problems that interact:

**7a. Mixed models:** `client.read([partner_ref, product_ref, partner_ref2])` contains refs from two different target models. The batch must issue two RPCs (one per distinct `__odoo_model__`). If the implementation groups naively by Python type identity (`id(type(ref))`) rather than by `__odoo_model__` string, two independently-generated classes for the same Odoo model (e.g., in a test that regenerates models) produce two separate RPCs for the same model instead of one.

**7b. Zero / falsy IDs:** Odoo sometimes returns `many2one` fields as `[0, ""]` or `[False, ""]` for records in a transient/computed state (e.g., draft invoices with unset fields, or fields computed before save). The read-side wire transform in `_pydantic_transform.py` guards `isinstance(value[0], int)` which accepts `0`. A `Ref(id=0)` that reaches TYPED-F1 causes a read RPC with `ids=[0]` — Odoo returns an empty result, the stitch step finds no match, and the resolution silently drops the ref or raises a `KeyError`.

**How to avoid:**
- Group by `__odoo_model__` string, not by Python type identity. `{ref.__class__.__odoo_model__: [...]}` is robust; `{type(ref): [...]}` is not.
- Filter out `Ref(id=0)` and `Ref(id=False)` before batching — these are "no relation" signals, not valid record ids. Return `None` for these in the result map (consistent with the `None`/False semantics already established for unset relations).
- The wire transform guard in `_pydantic_transform.py` should already exclude `id=0` (Odoo never returns a valid record with id 0), but add an explicit guard: `if value[0] == 0: out[name] = None; continue` before the Ref construction.
- After the batch RPC, stitch by building a `{id: resolved}` dict. Refs not present in the returned dict (id not found on the server) should raise `OdooMissingError` per ref, not silently return `None`.

**Warning signs:**
- Grouping logic uses `type(ref)` or `ref.__class__` as the dict key instead of `ref.__class__.__odoo_model__`.
- No test with a `Ref(id=0)` input.
- No test that verifies two refs to different models produce exactly two RPC calls (mock the transport and count calls).

**Phase to address:** TYPED-F1 — batching correctness is the implementation core.

---

### Pitfall 8: SEED-003 — Breaking `isinstance` Checks on the Restructured Error Hierarchy

**What goes wrong:**
SEED-003 restructures `OdooError`. Any change to the class hierarchy — renaming a class, changing parent class, splitting a class — silently breaks callers who use `except OdooValidationError` or `isinstance(e, OdooRpcError)`. Because these are `except` clauses (not function calls), there is no static type error; the breakage only surfaces at runtime when an exception that should be caught is not, or when a catch clause that was specific becomes too broad.

Current hierarchy that callers may depend on:
```
OdooError
├── OdooRpcError  ← most catch blocks target this
│   ├── OdooAuthError
│   ├── OdooNetworkError
│   │   └── OdooTimeoutError
│   ├── OdooValidationError
│   ├── OdooAccessError
│   └── OdooMissingError
└── OdooSafetyError  ← NOT a subclass of OdooRpcError (local-only)
```

If SEED-003 adds structured fields by introducing a new intermediate class (e.g., `OdooStructuredError` between `OdooError` and `OdooRpcError`), callers catching `OdooError` still work but callers catching `OdooRpcError` may miss the new class if it does not inherit from `OdooRpcError`.

**Why it happens:**
Python exception hierarchy changes are breaking changes at the semantic level even when they are not at the syntactic level. The new structured fields (`model`, `field`, `constraint`, `human_message`) can be added to existing classes as optional attributes without restructuring the hierarchy at all — but SEED-003's goal may require flattening or splitting.

**How to avoid:**
- **Preserve all existing exception class names and inheritance.** Add structured fields as new optional attributes on the existing classes — this is additive and non-breaking.
- Specifically: `OdooRpcError.__init__` gains optional `model: str | None = None`, `field: str | None = None`, `constraint: str | None = None`, `human_message: str | None = None` kwargs. All existing callers pass only `message`, `code`, `data` — no breakage.
- Keep `OdooSafetyError` as a direct `OdooError` subclass (not `OdooRpcError`) — this is correct and must not change.
- Document the new structured fields in the changelog as the only addition — not a hierarchy change.
- Write a regression test: `assert isinstance(OdooValidationError("x"), OdooRpcError)` and same for all existing classes — these must pass after the restructure.

**Warning signs:**
- SEED-003 implementation adds a new intermediate class in the hierarchy.
- Any existing class is renamed.
- `to_json()` method signature changes (callers who call `.to_json()` directly will break if the return shape changes).

**Phase to address:** SEED-003 — the design decision (additive vs. restructure) must be explicit in the phase spec. Additive is the safe default.

---

### Pitfall 9: SEED-003 — Odoo Traceback / Filesystem Path Leakage in Error Messages

**What goes wrong:**
Odoo's JSON-RPC error payload includes `data.debug` — a full Python traceback from the Odoo server, including:
- Odoo server filesystem paths: `/opt/odoo/addons/account/models/account_move.py`, line 1234
- Module names and line numbers that can be used to fingerprint the Odoo version and addon set
- In some configurations: server hostname, database name, or environment variables embedded in error strings

The current `_categorize_error` in `transport.py` stores the raw `data` dict directly as `OdooRpcError.data`. Any caller who calls `str(exc)`, logs the exception, or calls `exc.to_json()` receives this unfiltered payload — including downstream logging that may send it to Sentry, Datadog, or other external services.

SEED-003's stated goal is to strip server tracebacks and filesystem paths from the user-facing message. Failing to strip them is a **privacy/security issue** for users who expose their Odoo instance details through godoo-based tooling.

**Why it happens:**
`_categorize_error` passes the raw `data` dict through to preserve the full Odoo error context. This was the right default for debugging, but wrong for a library that is used in logging pipelines.

**How to avoid:**
- SEED-003 must define a **stripping function** that processes `data.debug` and `data.message` before storing them in the exception:
  - Strip `data.debug` entirely from the public error message — this is the Odoo Python traceback. Move it into the `.raw` escape hatch only.
  - For `data.message`: strip absolute filesystem paths using a regex: `r'File "(/[^"]+)"'` → `'File "<server-path>"'`. Also strip Windows-style paths.
  - Strip the server hostname if it appears in the message.
  - The stripping must happen in `_categorize_error` before any attribute assignment — never after.
- The `.raw` escape hatch stores the full unstripped `data` dict. Callers who need the traceback for debugging must explicitly opt in via `.raw`. Do not log `.raw` by default.
- The stripped `human_message` field should contain `data.message` after path stripping — this is what callers show to end-users.
- `to_json()` must never include `.raw` in its output — `.raw` is an opt-in escape hatch, not part of the standard serialization.

**Warning signs:**
- `str(exc)` on any `OdooRpcError` includes a string matching `/opt/odoo` or `/home/` or `C:\odoo`.
- `exc.to_json()` includes `data.debug` in its output.
- The stripping regex is only applied to `data.message`, not to the exception `message` string passed to `super().__init__()`.
- No test that constructs a mock Odoo error response with a full traceback and asserts that `str(exc)` contains no filesystem paths.

**Phase to address:** SEED-003 — the stripping function is the security/privacy requirement. Must have an explicit test with a realistic Odoo error payload before this phase is considered complete.

---

### Pitfall 10: SEED-003 — Incorrect Parsing of Odoo's Varied Fault Payload Shapes

**What goes wrong:**
The current `_categorize_error` (transport.py:138–168) handles two error shapes:
1. `data.exception_type` — explicit Odoo exception type string.
2. `data.name` — Python class name of the Odoo exception (e.g., `odoo.exceptions.ValidationError`).

Odoo's actual fault payload has several additional shapes that the current implementation misses:

**10a. `UserError` (non-validation user messages):** Odoo uses `UserError` for business logic errors ("You cannot delete a posted journal entry"). `exception_type = "user_error"` is handled, but the `data.message` for `UserError` is intended as the human-readable message (it is already translated and safe to show). The `data.debug` for `UserError` usually contains a traceback that the user should NOT see. SEED-003 must distinguish: `ValidationError.message` = field constraint description; `UserError.message` = safe human message.

**10b. `odoo.http.SessionExpiredException`:** Not in the current type map. Returns as a generic `OdooRpcError` instead of `OdooAuthError`. Must add to the name-based dispatch: `"sessionexpiredexception"` → `OdooAuthError`.

**10c. `IntegrityError` (database-level):** Some Odoo constraint violations bubble up as `psycopg2.errors.UniqueViolation` with `exception_type = None` and `data.name = "psycopg2.errors.UniqueViolation"` (or similar). The current code falls through to `OdooRpcError`. SEED-003 should map these to `OdooValidationError` with `constraint` field populated by parsing the constraint name from `data.debug`.

**10d. Missing `data` key entirely:** Some Odoo versions or middleware (nginx, HAProxy) return errors without the `data` key (e.g., `{"error": {"code": 500, "message": "Internal Server Error"}}`). The current code handles this with `data: dict[str, Any] = error_dict.get("data") or {}` — safe, but `exception_type` will be empty string and `name` will be empty string, falling through to `OdooRpcError`. This is correct; verify it does not break with the SEED-003 changes.

**How to avoid:**
- Extend `_categorize_error` with `"sessionexpiredexception"` → `OdooAuthError` in the name-based fallback.
- Add handling for `psycopg2` / `IntegrityError` name patterns → `OdooValidationError` with `constraint` field.
- The SEED-003 structured field `human_message` must be populated from `data.message` (after path stripping), not from the RPC-level `message` string (which is often a generic "Odoo Server Error" that contains the traceback).
- Write unit tests for each fault shape using real Odoo error payload fixtures (not synthetic payloads) — collect real payloads from the integration test container.

**Warning signs:**
- `_categorize_error` is not extended with new patterns in SEED-003 — "error hierarchy restructure" is treated as data-shape change only, not as a parsing improvement.
- The `human_message` field is populated from the RPC-level `message` string (which often includes the raw traceback as a single line).
- No unit test with a `SessionExpiredException` payload.

**Phase to address:** SEED-003 — parsing correctness is a prerequisite for structured fields being meaningful. The stripping and parsing work belong in the same phase.

---

### Pitfall 11: SEED-003 — `.raw` Escape Hatch Leaking When Logged

**What goes wrong:**
The `.raw` attribute stores the full unstripped `data` dict from the Odoo error payload, including tracebacks and filesystem paths. If callers log the exception object using the default Python logging formatting (`logger.exception("error: %s", exc)` or `logging.error("...", exc_info=True)`), the traceback logged by the logging framework includes the exception's `__repr__` or `str()` — neither of which includes `.raw`. However, if any code calls `logger.debug("error raw: %s", exc.raw)` or includes `.raw` in a log format string, the full traceback leaks.

More subtly: if `.raw` is included in `to_json()` output, and that JSON is sent to a structured logging sink (Datadog, Loki, Elasticsearch), every error carries the full server traceback in the log index — exactly the leak SEED-003 is designed to prevent.

**Why it happens:**
`.raw` is an escape hatch for debugging. Developers will naturally include it in debug log statements. The attribute name `.raw` does not signal "do not log."

**How to avoid:**
- `to_json()` must **never** include `.raw`. Verify explicitly with a test: `assert "raw" not in exc.to_json()`.
- The `.raw` attribute docstring must say: "Contains unstripped server data including tracebacks. Do not log or serialize to external sinks."
- Consider naming it `._raw` (private) with a public `get_raw()` method that prints a warning to stderr — but this may be over-engineered; documenting is sufficient.
- The stripping test (Pitfall 9) should also assert that `to_json()` output contains no filesystem paths.

**Warning signs:**
- `to_json()` includes a `"raw"` or `"debug"` key in its output dict.
- Any log statement in godoo's own code that logs `.raw` at a level above DEBUG.
- No test asserting `"raw" not in exc.to_json()`.

**Phase to address:** SEED-003 — the `.raw` exclusion from `to_json()` must be a go/no-go criterion for the phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `model.model_dump(exclude_none=True)` as the write serializer | Works for create (new records) | Loses the `__pydantic_fields_set__` distinction between "never set" and "explicitly cleared" on partial updates | Never for write; acceptable for create only |
| Serializing Ref fields as `{"id": ..., "name": ...}` (Pydantic default JSON) | Zero implementation effort | Odoo raises ValidationError on every write containing a Ref field | Never |
| Emitting x2many fields unchanged in write serializer | Avoids the command-tuple complexity | Silent no-op or Odoo error on any write that touches x2many fields | Never — always either exclude or convert |
| Populating `.raw` from `data.debug` verbatim with no stripping | Zero implementation effort | SEED-003's privacy guarantee is false; tracebacks leak through `.raw` if included in `to_json()` | Never for `to_json()`; `.raw` itself can be verbatim (the point is to keep it out of serialized output) |
| Using `type(ref)` as the batch grouping key instead of `__odoo_model__` | Simpler grouping logic | Two independently-generated classes for the same model produce redundant RPCs | Never |
| Adding a new intermediate class in the error hierarchy for SEED-003 | Cleaner architecture on paper | Breaks all `except OdooRpcError` clauses in existing callers | Never — use additive attributes on existing classes |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Odoo `write()` with a Ref field | Serialize Ref as `{"id": ..., "name": ...}` or `[id, name]` | Serialize as bare `int` (the id only) |
| Odoo `write()` to clear a many2one | Send `None` or omit the field | Send `False` — `None`/`null` behavior is server-version-dependent |
| Odoo `write()` with x2many fields | Send `list[int]` directly | Send command tuples `[(6, 0, ids)]` for replace; exclude if not changing |
| Odoo `write()` with computed fields | Include in serialized payload | Exclude fields where `readonly=True` in schema; they are read-only |
| Odoo error `data.debug` | Log directly for debugging | Strip before user-facing display; store in `.raw` for opt-in debugging |
| `Ref[int]` passed to relation resolver | Silently skip or crash | Raise clear `OdooValidationError` with actionable message |
| Batch resolution with duplicate ids | Send `[1, 1, 1]` to Odoo `read()` | Deduplicate to `{1}` before the RPC; stitch back after |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Single-ref resolution in a loop | N RPCs for N records with the same m2o field | Batch API is the primary API; single-ref is a convenience that internally batches | From the first list of >1 records |
| Fetching all fields on relation resolution | Resolves partner refs but fetches 80 fields when caller needs 3 | Allow `fields` parameter on `client.read(list[Ref[T]], fields=[...])` | Noticeable on models with binary/html fields |
| Partial model cache unbounded growth | Long-lived processes accumulate `_partial_model_cache` entries | `clear_partial_model_cache()` already exists — document when to call it | At >1000 distinct field-subset combinations |
| `create_model()` per unique field subset per batch | If TYPED-F1 derives partial models for related reads, each new field subset creates a new class | Cache by `(model_id, frozenset(fields))` — already implemented in `derive_partial_model()` — ensure TYPED-F1 uses the same cache | From the first repeated resolution |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Including `data.debug` (Odoo traceback) in `to_json()` output | Server filesystem paths, addon names, version info leak to external logging sinks | Exclude from `to_json()`; store only in `.raw` |
| Including `.raw` in `to_json()` output | Same as above — the stripping becomes theater | Explicit test: `assert "raw" not in exc.to_json()` |
| Logging `exc.raw` at INFO or WARNING level | Traceback reaches log aggregators with no opt-in | Document `.raw` as opt-in debug only; only godoo's own DEBUG logging may reference it |
| Serializing write payload without excluding `write_uid`, `create_uid` | These are read-only ownership fields; some Odoo versions raise, others silently ignore | Always exclude from write payload via `readonly=True` field metadata |

---

## "Looks Done But Isn't" Checklist

- [ ] **TYPED-F2 round-trip test:** Read a record → modify a Ref field → write back → read again → assert related record changed. Without this, the serializer has never been tested end-to-end.
- [ ] **TYPED-F2 partial update test:** Read a model with partial fields → explicitly set one field to `None` → write back → verify only that one field appears in the RPC payload (use `respx` mock to inspect the payload).
- [ ] **TYPED-F2 x2many test:** Any write involving a `one2many` or `many2many` field must verify the command-tuple format in the payload — not just that the write succeeds.
- [ ] **TYPED-F1 batch-count test:** Resolve 10 refs all pointing to the same model — verify exactly 1 RPC was issued (mock transport and count calls).
- [ ] **TYPED-F1 `Ref[int]` guard test:** Pass a `Ref[int]` to the resolver — verify a clear `OdooValidationError` is raised, not an `AttributeError` or silent skip.
- [ ] **SEED-003 path-strip test:** Construct a mock Odoo error with `data.debug` containing `/opt/odoo/addons/account/models.py:1234` — verify `str(exc)` and `exc.to_json()` contain no filesystem path.
- [ ] **SEED-003 `to_json()` no-raw test:** `assert "raw" not in exc.to_json()` for all `OdooRpcError` subclasses.
- [ ] **SEED-003 isinstance regression test:** `assert isinstance(OdooValidationError("x"), OdooRpcError)` — and equivalent for all existing classes — pass after restructure.
- [ ] **SEED-003 `SessionExpiredException` routing test:** A mock payload with `data.name = "odoo.exceptions.SessionExpiredException"` routes to `OdooAuthError`, not `OdooRpcError`.
- [ ] **TYPED-F2 readonly-field exclusion test:** Serialize a model with `display_name` set — verify `display_name` is absent from the write payload.

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Sending read-only/computed fields on write (P1) | TYPED-F2 — codegen metadata + serializer design | Integration test: write a freshly-read model, inspect RPC payload |
| Wrong m2o write format — Ref not bare int (P2) | TYPED-F2 — write serializer | Unit test: `Ref(id=5, name="x")` serializes to `5`; respx mock verifies payload |
| x2many requires command tuples (P3) | TYPED-F2 — serializer + design decision on strategy | Unit test: list[int] x2many field produces command tuple in payload |
| `None` vs `False` vs omitted on partial update (P4) | TYPED-F2 — `__pydantic_fields_set__` serializer | Mock-transport test: unset field omitted; explicitly-None field → `False` |
| N+1 RPC storm from per-ref resolution (P5) | TYPED-F1 — batch-first design | Mock-transport test: 10 refs → 1 RPC call |
| Untyped `Ref[int]` with no target class (P6) | TYPED-F1 — type guard in resolver | Unit test: `Ref[int]` input raises `OdooValidationError` |
| Mixed-model batching + zero ids (P7) | TYPED-F1 — group by `__odoo_model__` string | Unit test: 2 different models → 2 RPCs; `Ref(id=0)` → `None` |
| Breaking `isinstance` checks on error hierarchy (P8) | SEED-003 — additive-only design | Regression test: all existing isinstance assertions pass after restructure |
| Traceback / path leakage in error messages (P9) | SEED-003 — stripping function in `_categorize_error` | Unit test: mock payload with traceback → `str(exc)` has no filesystem paths |
| Incomplete Odoo fault payload parsing (P10) | SEED-003 — extend `_categorize_error` | Unit tests for each fault shape: `UserError`, `SessionExpiredException`, `IntegrityError` |
| `.raw` leaking through `to_json()` (P11) | SEED-003 — `to_json()` exclusion | Unit test: `"raw" not in exc.to_json()` for all subclasses |

---

*Pitfalls research for: godoo-py v1.2 (Typed Relations, Writes & Error Surface)*
*Researched: 2026-06-02*
