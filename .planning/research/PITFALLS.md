# Pitfalls Research

**Domain:** Python Async SDK for Odoo JSON-RPC — RPC client, introspection, state manager, live x-module builder
**Researched:** 2026-04-10
**Confidence:** HIGH (RPC mechanics), MEDIUM (state-manager semantics), HIGH (moduleX ordering/registry)

---

## Layer 1: godoo Core (RPC Client)

### Pitfall 1.1: Pagination — Default Limit Is Not "All Records"

**What goes wrong:**
`search_read` with no `limit` argument returns at most 100 records (Odoo's server-side default). Code that calls `search_read` once and iterates the result silently misses records beyond position 100.

**Why it happens:**
Documentation examples never show pagination. The result looks like a complete list. No error is raised. The call succeeds with a truncated dataset.

**How to avoid:**
Always pass an explicit `limit` when wanting all records, or implement cursor-based pagination using `offset`. For bulk reads, paginate in chunks of 1000 and loop until the returned list length is less than the chunk size. Never use `limit=0` expecting "unlimited" — behavior varies by version and server config.

**Warning signs:**
Counts from `search_count` disagree with `len(search_read(...))` results. Data sets that "shrink" between calls.

**Phase to address:**
godoo-core hardening — add `search_all()` helper that handles pagination transparently, and unit-test it with a respx mock that returns exactly 100 records to verify the loop triggers.

---

### Pitfall 1.2: Naive UTC Datetimes From RPC — No Timezone Conversion

**What goes wrong:**
Odoo stores all `Datetime` values as UTC in PostgreSQL, but the column is `timestamp WITHOUT time zone`. RPC returns datetime strings as naive UTC (e.g., `"2024-03-15 09:30:00"`) with no timezone indicator. Client code that interprets them as local time is silently wrong.

**Why it happens:**
The Odoo web UI converts datetimes to the user's `tz` context before display. RPC does NOT perform this conversion — you always get raw UTC regardless of `context['tz']`. Developers assume the context `tz` applies everywhere.

**How to avoid:**
Always parse RPC datetime strings as UTC-aware (`datetime.fromisoformat(...).replace(tzinfo=timezone.utc)`). When writing, always pass UTC strings. Document this explicitly in the SDK's type annotations and docstrings.

**Warning signs:**
Off-by-one-hour bugs after daylight saving transitions. `write_date` comparisons for drift detection give wrong results when drift check runs in a non-UTC timezone.

**Phase to address:**
godoo-core hardening — add datetime parsing utilities that always return timezone-aware UTC objects. Integration tests should assert timezone correctness.

---

### Pitfall 1.3: CSRF and Session Cookie — JSON-RPC Exemption Is Version-Specific

**What goes wrong:**
Odoo's `http.route(type='json')` endpoints do NOT apply CSRF verification by default. This is consistent across v14–v18. However, Odoo Online (SaaS) and some configurations add a CSRF token requirement on session setup. Custom `web` controllers added by third-party modules may require CSRF even on JSON routes if misconfigured.

**Why it happens:**
Developers assume JSON-RPC is always CSRF-free. It is, for the standard `/web/dataset/call_kw` endpoint. But session creation at `/web/session/authenticate` is an HTTP-type route and behaves differently.

**How to avoid:**
Capture and reuse the session cookie returned by `/web/session/authenticate`. Use `httpx` cookie jar persistence. Do not strip or regenerate cookies between calls. For Odoo 17+ cloud deployments, include the `X-Csrf-Token` header if a 403 is returned on session init.

**Warning signs:**
403 responses on session endpoints. `OdooAuthError` on what looks like a valid login.

**Phase to address:**
godoo-core hardening — existing `transport.py` correctly stores the session but generates a client-side UUID rather than a server-issued session ID (see CONCERNS.md). The cookie jar must persist the real `session_id` cookie returned by Odoo.

---

### Pitfall 1.4: Session Expiry — Transport Does Not Auto-Clear Stale Session

**What goes wrong:**
When the Odoo session expires server-side (default 1 week for standard sessions, 15 minutes for `cb auth` short-lived tokens), subsequent RPC calls return `AccessDenied`. The transport receives `OdooAuthError` but does NOT clear `_session`. The next call retries with the same stale session and fails again, creating an infinite retry loop or silent failure.

**Why it happens:**
As documented in CONCERNS.md: "`call()` checks `if self._session is None` but doesn't check if session has expired server-side." Re-auth requires the caller to explicitly call `authenticate()` again.

**How to avoid:**
On `OdooAuthError`, clear `_session` in transport and raise a specific `OdooSessionExpiredError` subclass. Implement an auto-reauth callback at client level. Integration tests must simulate session expiry.

**Warning signs:**
Repeated `OdooAuthError` on a previously-working client instance. Log shows identical failed call repeated.

**Phase to address:**
godoo-core hardening — fix `transport.py` session expiry path before state-manager depends on long-lived sessions.

---

### Pitfall 1.5: Binary Field Encoding — Base64 Both Directions, Memory for Large Files

**What goes wrong:**
Binary fields are returned from RPC as base64-encoded strings. Writing requires base64-encoded input. Forgetting the encoding on either side produces a silent corruption (Odoo stores the raw string as-is). For files over ~50MB, base64 encoding in-process causes memory errors (documented Odoo issue #26559, #124646 for 16.0).

**Why it happens:**
JSON cannot transmit raw bytes. The base64 contract is implicit and not validated server-side until the value is decoded.

**How to avoid:**
Always use `base64.b64encode(bytes).decode()` for writes and `base64.b64decode(str)` for reads. For large binaries, use `ir.attachment` instead of inline binary fields — attachments have their own upload endpoint that streams. Set a client-side size threshold (suggest 10MB) above which binary writes are refused with a helpful error.

**Warning signs:**
Files appear corrupt after round-trip read/write. MemoryError in Odoo logs for large uploads.

**Phase to address:**
godoo-core hardening — wrap binary encoding/decoding in helpers; document the `ir.attachment` alternative.

---

### Pitfall 1.6: Many2Many / One2Many Write — Command Tuple Format Is Mandatory

**What goes wrong:**
Writing a relational field via RPC requires "magic command tuples" — 3-element lists like `[0, 0, {values}]` (create), `[4, id, False]` (link), `[6, False, [ids]]` (replace set). Passing a plain list of IDs does not work. The (4, id) command does NOT apply to One2Many. The (6, False, ids) replace command on One2Many silently deletes records not in the list.

**Why it happens:**
Odoo's Python `fields.Command` helper class (v15+) exists in ORM code but is not accessible over RPC. External callers must use raw integer codes. Documentation is incomplete on which commands apply to which field type.

**How to avoid:**
Create a `Command` helper in the SDK that mirrors `fields.Command` but outputs the raw tuple format. Document per command which field types support it. Never pass raw ID lists to relational fields.

**Warning signs:**
Write calls succeed (200 OK) but the relational field is not updated. Records are silently deleted from One2Many.

**Phase to address:**
godoo-core hardening — add command tuple helpers to types; integration test all six command codes against a real Odoo instance.

---

### Pitfall 1.7: Context Blindness — `active_test`, `lang`, and `company_id` Affect Results Silently

**What goes wrong:**
By default, `search` and `search_read` respect `active_test=True` from context, meaning archived records (`active=False`) are invisible. Code expecting to find all records of a model silently misses archived ones. Similarly, `lang` in context changes the values of translatable fields, and `allowed_company_ids` controls which multi-company records are accessible.

**Why it happens:**
RPC calls inherit the authenticated user's session context. The user's default context always includes `active_test: True`. No explicit domain for `active` is needed to get this behavior.

**How to avoid:**
When querying for "does this record exist" (e.g., for drift detection), always add `('active', 'in', [True, False])` to the domain or pass `context={'active_test': False}`. When writing translations, always set `context={'lang': target_lang}`. When operating in multi-company, explicitly set `context={'allowed_company_ids': [company_id]}`.

**Warning signs:**
State manager reports drift on records that exist but are archived. Translated values appear to be missing.

**Phase to address:**
godoo-core — document context rules; state-manager plan phase must default to `active_test=False` when checking existence.

---

### Pitfall 1.8: Odoo API Deprecation in v22 / Online 21.1

**What goes wrong:**
The JSON-RPC endpoint `/jsonrpc` and XML-RPC endpoints `/xmlrpc`, `/xmlrpc/2` are scheduled for removal in Odoo 22 (fall 2028) and Online 21.1 (winter 2027). Odoo is migrating to a REST API. Code built exclusively on JSON-RPC will need migration.

**Why it happens:**
Odoo announced this deprecation in 2024. The new REST API is not yet comprehensive (missing HR, payroll, accounting as of 2024) but will expand.

**How to avoid:**
Abstract the transport layer from service logic. The SDK's transport interface should be replaceable so the REST transport can be swapped in when the target version requires it. Track Odoo's REST API coverage expansion.

**Warning signs:**
Odoo 21+ instances returning deprecation warnings in response headers.

**Phase to address:**
godoo-core design — ensure `Transport` is an ABC; REST transport as a future package. Not blocking v1, but architecture must not make migration impossible.

---

## Layer 2: Introspection / Type Generation

### Pitfall 2.1: Computed Fields — Appear in `ir.model.fields` But Are Not Writable

**What goes wrong:**
`fields_get()` and `ir.model.fields` both return computed fields (those with a `depends` clause in ORM). They look like regular fields in the schema. Writing to them via RPC either silently does nothing or raises `ValidationError`. Store-computed fields (`store=True`) ARE writable only if `readonly=False` — but this is set server-side and not always reflected in `ir.model.fields.readonly`.

**Why it happens:**
The distinction between "computed but not stored" and "computed and stored" is in Python class attributes, not in `ir.model.fields` metadata.

**How to avoid:**
During introspection, read `ir.model.fields.store` (True/False) AND check if the field is in `fields_get()` with `readonly: True`. Generate separate type stubs for read-only fields. Tag computed unstored fields as `Annotated[T, ReadOnly]`.

**Warning signs:**
Write call returns 200 but field value unchanged. `ValidationError: 'field_name' field is not stored`.

**Phase to address:**
godoo-introspection — filter or annotate computed fields during code generation.

---

### Pitfall 2.2: Related Fields — Semantics Depend on `store` and Traversal Depth

**What goes wrong:**
Related fields (e.g., `partner_id.country_id.name`) appear as regular fields in the schema. `store=False` related fields cannot be filtered on via domain. Writing to a stored related field writes THROUGH to the related record, potentially mutating shared data unexpectedly.

**Why it happens:**
`ir.model.fields` records for related fields have `related` populated but no indication of traversal path or whether the write side effect is on this model or the related one.

**How to avoid:**
During introspection, read `ir.model.fields.related` (the dotted path string). Tag related fields. Warn when state-manager tries to "create or update" a field value that is a non-stored related field (would be a no-op).

**Warning signs:**
Domain filters on related fields fail with `Invalid domain operator` or silently return empty sets.

**Phase to address:**
godoo-introspection — emit `related_path` metadata in generated types; state-manager must skip non-stored related fields.

---

### Pitfall 2.3: Properties (v17+) — Different Storage Model, Breaks Field Enumeration

**What goes wrong:**
Odoo v17 introduced "Property Fields" (`fields.Properties`). These are container fields that hold a schema + values inline (in JSONB). When reading `ir.model.fields`, a model may appear to have a `properties` field of ttype `properties`, but the actual sub-fields (text, many2one, checkbox, etc.) are stored inside the Properties definition, NOT as separate `ir.model.fields` records.

In v15/v16 the predecessor was `company_dependent` fields backed by `ir.property`. In v17 the Properties feature replaces it with a new field type.

**Why it happens:**
Introspection that iterates `ir.model.fields` and generates one Python field per record misses the dynamic sub-properties entirely.

**How to avoid:**
Detect `ttype == 'properties'` during introspection. Read the `properties_definition` JSONB field from the parent model to enumerate the dynamic sub-fields. Generate a separate typed dict for the properties container. Document that v14/v15/v16 vs v17+ have different mechanisms (`ir.property` vs `fields.Properties`).

**Warning signs:**
Generated types omit known UI-visible fields on project.task or product.template in v17+ instances.

**Phase to address:**
godoo-introspection — version branch for v17+ Properties handling. Integration test against v16 AND v17.

---

### Pitfall 2.4: Selection Field Values — Returned as String Representation, Not List

**What goes wrong:**
`ir.model.fields` returns the `selection` column as a string like `"[('draft', 'Draft'), ('confirmed', 'Confirmed')]"` — a Python list-of-tuples serialized as a string. Parsing this requires `ast.literal_eval`. Fields with dynamic selection (computed via a method) return the string name of the method, not the values.

**Why it happens:**
The field `ir.model.fields.selection` is a `Text` column storing the serialized representation. For dynamic selections backed by a Python method, the introspection layer has no way to enumerate the values without calling that method.

**How to avoid:**
Use `ast.literal_eval` to parse selection strings. Detect when the value looks like a method name (no brackets, no tuples) and flag those as "dynamic selection — values unknown at introspection time". `fields_get()` returns `selection` as an already-parsed list; prefer it over `ir.model.fields.selection` for introspection.

**Warning signs:**
`SyntaxError` or `ValueError` on unparseable selection strings. Generated types have `Literal[...]` with wrong values.

**Phase to address:**
godoo-introspection — use `fields_get()` as primary source for selection values; fall back to `ir.model.fields` only for custom x_fields.

---

### Pitfall 2.5: Company-Dependent Fields — Value Depends on Active Company, Breaks Diff

**What goes wrong:**
Fields with `company_dependent=True` store per-company values. Reading via RPC returns the value for the CURRENT company of the authenticated user. Comparing a field value read as company A against a desired value meant for company B gives false drift positives.

**Why it happens:**
The `company_dependent` contract is implicit. `ir.model.fields.company_dependent` is a boolean visible via introspection, but callers must pass `context={'allowed_company_ids': [target_company_id]}` to read the correct company's value.

**How to avoid:**
Tag company-dependent fields during introspection. State-manager diff must read and write them per-company, scoping each operation with the correct company context. Integration tests must cover multi-company scenarios.

**Warning signs:**
Drift detected on config records that were just written to a different company.

**Phase to address:**
godoo-introspection — annotate company-dependent fields; state-manager — company context scoping in diff logic.

---

### Pitfall 2.6: Module-Specific Fields — `x_` vs Technical vs Installed Module Fields

**What goes wrong:**
`ir.model.fields` contains fields for ALL installed modules, including modules that may not be installed on another target instance. Generated types that include module-specific fields (e.g., `account.move.l10n_es_tbai_tax_id`) will fail at runtime on instances without that module.

**Why it happens:**
Introspection does not gate on module installation status.

**How to avoid:**
During introspection, read `ir.model.fields.modules` (the comma-separated list of module names that define the field). Generate a `__REQUIRES_MODULES__: list[str]` annotation. Optionally generate "base" vs "extended" type variants.

**Warning signs:**
Generated code references fields that don't exist on a different (less-installed) Odoo instance.

**Phase to address:**
godoo-introspection — annotate field-to-module mapping in generated output.

---

## Layer 3: State Manager (Plan/Apply/Diff)

### Pitfall 3.1: Drift Detection With `write_date` — Timezone and Precision Mismatches

**What goes wrong:**
Using `write_date` as a drift signal is unreliable: (1) it is UTC but returned as naive string, (2) it has 1-second precision in older Odoo versions (microseconds in v16+), (3) Odoo server clock may differ from client clock, (4) `write_date` is updated on ANY write including unrelated fields, causing false-positive drift.

**Why it happens:**
`write_date` is the only universally-available "last modified" signal on Odoo records. It seems like the natural drift indicator.

**How to avoid:**
Do not use `write_date` as the sole drift signal. Compare field-by-field against the declared desired state. Only declare drift when desired-field values differ from actual values. `write_date` can be used to short-circuit diff (if `write_date` <= last_apply_time, skip diff) but must not be the only check.

**Warning signs:**
State manager constantly reports "drift" on records that look correct when inspected manually. Plan output is always non-empty even after a fresh apply.

**Phase to address:**
godoo-state-manager — diff algorithm must be field-value-based, not time-based.

---

### Pitfall 3.2: Translation Diffing — v15 vs v16 Incompatibility

**What goes wrong:**
In Odoo v15 and earlier, translations for a field (e.g., `name` in `fr_FR`) are stored in `ir.translation` as separate records. In v16+, translated fields store all language values inline as JSONB in the record's own column. Reading the same field with `context={'lang': 'fr_FR'}` works on both, but writing translations via `context={'lang': 'fr_FR'}` writes only that language's value on v16+. On v15, you must write to `ir.translation` directly.

**Why it happens:**
PR #97692 in the odoo/odoo repo (merged for v16) changed translated field storage fundamentally. Writing `False` to a field on v16+ nullifies it for ALL languages. Writing `""` (empty string) nullifies only the current language.

**How to avoid:**
Version-gate translation write logic. For v16+: write via `context={'lang': code}` for each language. For v15 and below: use `ir.translation` write or the `translate()` model method. The state-manager must detect Odoo version on init and choose the correct write path.

**Warning signs:**
After a multi-language apply, values in one language appear correct but another language is `False` (all-languages null) instead of empty.

**Phase to address:**
godoo-state-manager — version detection at init; translated field write abstracted behind a version-dispatched helper.

---

### Pitfall 3.3: HTML / Markdown Fields — Sanitization Changes the Value

**What goes wrong:**
Odoo applies HTML sanitization on `html` fields (using `fields.Html`). Values written via RPC go through `html_sanitize()` server-side before storage. Reading back the "same" value after write will differ because: (1) attributes are stripped or normalized, (2) `<br>` vs `<br/>` normalization, (3) whitespace is collapsed. Diff logic that compares raw strings will always report drift.

**Why it happens:**
`html_sanitize()` is applied server-side as part of the ORM write, not exposed via RPC. The caller has no visibility into what transformations will occur.

**How to avoid:**
For HTML fields: (1) never diff the raw HTML string directly; (2) parse both sides with an HTML parser (e.g., `lxml.html`) and compare the DOM, or compare a normalized form (strip whitespace, normalize void elements); (3) use a "write then read" round-trip verification in tests to characterize which transformations Odoo applies.

**Warning signs:**
State manager always reports "drift" on HTML-type fields even immediately after apply.

**Phase to address:**
godoo-state-manager — HTML field diff uses normalized comparison, not raw string equality.

---

### Pitfall 3.4: `removeUnmanaged` Semantics Differ Between m2m and o2m

**What goes wrong:**
For a Many2Many field (e.g., tags), "remove unmanaged" means: unlink records not in the desired set (command (3, id) — unlink without delete). For a One2Many field (e.g., invoice lines), "remove unmanaged" means: delete records not in the desired set (command (2, id) — delete). Applying o2m semantics to m2m silently destroys shared records. Applying m2m semantics to o2m leaves orphaned records that accumulate.

**Why it happens:**
Both field types look like "a list of related records" to the declarative DSL. The delete-vs-unlink distinction is a Many2Many vs One2Many contract, not obvious from the field type alone at the DSL level.

**How to avoid:**
The DSL must know the relational type (`ttype` from introspection). Many2Many remove = unlink (command 3). One2Many remove = delete (command 2). Test both cases explicitly. Document in DSL that `remove_unmanaged` has different destructiveness depending on field type.

**Warning signs:**
Shared tags being deleted from unrelated records after an apply. Or orphaned One2Many children accumulating in the database.

**Phase to address:**
godoo-state-manager — `remove_unmanaged` dispatches on `ttype`; integration tests cover both.

---

### Pitfall 3.5: Circular Dependencies Between Resources

**What goes wrong:**
Resource A requires Resource B to exist (e.g., a product.template requires a product.category). Resource B's desired state might reference Resource A's external ID. Or: ir.model A has a Many2one to ir.model B which has a Many2one back to A (self-referential via a parent_id). Creating them in the wrong order results in a foreign-key violation or a lookup failure.

**Why it happens:**
Declarative state managers collect resources and apply them in declaration order without analyzing the dependency graph.

**How to avoid:**
Topologically sort resources before apply. Detect cycles and raise a plan error. Allow "deferred" resolution: create resources without setting the circular references, then patch them in a second pass. Mirror how Odoo module data XML handles `ref()` with a two-pass loader.

**Warning signs:**
`odoo.exceptions.ValidationError` mentioning a missing Many2one target during create. Resources that work in one declaration order but fail in another.

**Phase to address:**
godoo-state-manager — plan phase builds dependency graph and topological sort before emitting apply operations.

---

### Pitfall 3.6: `lookup()` Ambiguity — "Create If Not Found" vs "Error If Not Found"

**What goes wrong:**
The `lookup()` DSL (ported from TS state-manager) resolves a record by domain criteria. If the lookup finds 0 records, two behaviors are valid: (1) error, the expected record is missing — caller should have created it first; (2) create it on the fly with the lookup's fields. Mixing these silently creates duplicate records when a lookup matches 0 due to a wrong domain (e.g., searching by name that was renamed).

**Why it happens:**
The TS `odoo-state-manager` has this ambiguity too. The Python port inherits it.

**How to avoid:**
Make the create-if-missing behavior explicit and opt-in (`lookup(..., create_if_missing=True)`). Default behavior must be "error if not found." When `create_if_missing=True`, also set a `find_duplicate_key` so idempotent re-runs don't create duplicates.

**Warning signs:**
Multiple records matching a lookup domain after several apply runs. Records with unexpected names or default values appearing in the DB.

**Phase to address:**
godoo-state-manager — `lookup()` API design, default to error, explicit flag for upsert.

---

### Pitfall 3.7: Idempotency Requires `xml_id` — External ID Must Be Stable

**What goes wrong:**
Re-running apply without stable external IDs creates duplicate records. Odoo's idempotency mechanism is `ir.model.data` (the external ID table). If the apply does not create `ir.model.data` entries for managed records, the second apply cannot find the first record and creates a new one.

**Why it happens:**
External IDs are optional in Odoo. RPC `create` calls don't auto-register an external ID.

**How to avoid:**
Every resource declared in state-manager must have (or be assigned) a stable external ID. After `create`, immediately call `ir.model.data.create` with `module='__godoo__'`, `name=resource.xml_id`, `model=resource.model`, `res_id=new_id`, `noupdate=True`. Lookup during next apply uses `ir.model.data` first, falling back to the domain only if no external ID record is found.

**Warning signs:**
Running apply twice creates double the records. Records "disappear" on a fresh apply that deletes-and-recreates instead of updating.

**Phase to address:**
godoo-state-manager — external ID registration is mandatory, not optional. Integration test: run apply twice, assert record count unchanged.

---

## Layer 4: moduleX Live-RPC Module Builder

### Pitfall 4.1: `ir.model` Must Have `state='manual'` — And Odoo Enforces the `x_` Prefix

**What goes wrong:**
Creating an `ir.model` record without `state='manual'` silently creates a metadata record but Odoo's registry does NOT create the corresponding database table. The model exists in `ir.model` but is not queryable. Additionally, the model name MUST start with `x_` — any other name raises a `ValidationError` in Studio-created (manual) models.

**Why it happens:**
`state='base'` models are created by Python code at module load time, not via RPC. The `state` field is the registry's gating mechanism. This is checked in `ir_model.py` `_check_manual_name`.

**How to avoid:**
Always set `state='manual'` and enforce the `x_` prefix in the moduleX DSL (not just documentation). Validate the model name format before issuing the RPC. Assert that after create, the model is queryable via `search_read` against the new model name.

**Warning signs:**
`ir.model` record created successfully but subsequent `search_read` on the new model returns "Model not found" or `KeyError` in registry.

**Phase to address:**
godoo-moduleX — name validation in DSL constructor; integration test verifies model is immediately queryable after create.

---

### Pitfall 4.2: `ir.model.fields` Must Also Have `state='manual'` — Field Prefix Required for x_Models

**What goes wrong:**
Fields added via RPC to a manual model must have `state='manual'`. Field names on custom models must start with `x_`. Fields added to EXISTING base models (e.g., `res.partner`) also require `x_` prefix and `state='manual'`. Attempting to create a field named without `x_` on a custom model raises an error. Attempting to create without `state='manual'` creates a phantom `ir.model.fields` record with no corresponding DB column.

**Why it happens:**
Same gating mechanism as models. The ORM's column creation is triggered by `state='manual'` at module load or registry rebuild.

**How to avoid:**
Enforce `x_` prefix and `state='manual'` in the field creation DSL. After creating a field, verify it appears in `fields_get()` of the target model (which queries the live registry, not `ir.model.fields`). There is typically a 1-2 RPC round-trip delay before the field appears in `fields_get` in multi-worker setups (see Pitfall 4.8).

**Warning signs:**
`ir.model.fields` record created but field not in `fields_get()`. Write to the new field raises `KeyError: 'x_myfield'`.

**Phase to address:**
godoo-moduleX — DSL enforces naming convention; field registration includes a verification step.

---

### Pitfall 4.3: `ttype` Enum — Selection Format Is Stringified Python, Not JSON

**What goes wrong:**
When creating a `selection`-type field in `ir.model.fields`, the `selection` column must be a string formatted as a Python list of 2-tuples: `"[('value1', 'Label 1'), ('value2', 'Label 2')]"`. JSON format (`[["value1", "Label 1"]]`) does NOT work. The Odoo ORM uses `ast.literal_eval` to parse this, not `json.loads`.

**Why it happens:**
This is a legacy Odoo format from before JSON became standard. The column is `Text` and the contract is Python-tuple string serialization.

**How to avoid:**
moduleX DSL takes Python-native `list[tuple[str, str]]` as input and serializes via `repr()` or manual construction. Never use `json.dumps` for this value. Include a roundtrip parse test that verifies Odoo accepted the selection list by reading back `ir.model.fields.selection`.

**Warning signs:**
Selection field created but shows no values in the UI. `odoo.exceptions.ValidationError: Invalid selection format`.

**Phase to address:**
godoo-moduleX — `SelectionField` type with proper serialization.

---

### Pitfall 4.4: Many2Many Relation Table Name Collision

**What goes wrong:**
When creating a `many2many` field in `ir.model.fields` without specifying `relation`, `column1`, `column2`, Odoo auto-generates the relation table name from model names. If two custom models have similar names, the auto-generated table name may collide with an existing table, causing `ProgrammingError: relation already exists`. Self-referential many2many on the same model always requires explicit `relation`, `column1`, `column2`.

**Why it happens:**
Odoo's auto-naming algorithm: `'{model1}_{model2}_rel'`. Two different many2many fields with the same comodel from the same source model generate the same table name.

**How to avoid:**
Always explicitly provide `relation`, `column1`, `column2` for many2many fields created via moduleX. Use a deterministic naming scheme: `x_{source_model_snake}_{field_name}_rel`. Validate the relation table name does not already exist in `ir.model.relation`.

**Warning signs:**
`ProgrammingError` from PostgreSQL on field creation. Second many2many field on the same source/target pair fails silently.

**Phase to address:**
godoo-moduleX — `Many2ManyField` DSL always requires explicit relation table naming.

---

### Pitfall 4.5: `ir.ui.view` arch_db — XML Validation Is Server-Side and Strict

**What goes wrong:**
`arch_db` must be valid XML. Odoo validates the arch against the view type's schema before saving. Common failures: unclosed tags, invalid attribute names, wrong XPath in inheritance extensions, using `<xpath>` targets that don't exist in the parent view. The error message is `ValidateError: Invalid XML for View Architecture` — it does not identify which tag is wrong.

**Why it happens:**
The arch is passed as a raw XML string. No client-side validation occurs.

**How to avoid:**
Validate arch XML client-side with `lxml.etree.fromstring()` before sending. For inheritance views, parse the parent arch first and verify the XPath exists before creating the child view. Use `lxml.etree.tostring()` to normalize whitespace. Test arch strings in a dev environment before automating.

**Warning signs:**
`ValidateError` on `ir.ui.view.create`. View record created but not rendered in the UI (sometimes validation is deferred).

**Phase to address:**
godoo-moduleX — ViewBuilder DSL validates XML before RPC; integration tests cover form, list, search view types.

---

### Pitfall 4.6: View Inheritance — `mode` Defaults and `inherit_id` Interaction

**What goes wrong:**
When creating an extension view (inheriting an existing view with XPath overrides), you must set `inherit_id` AND either leave `mode` unset (defaults to `extension`) or explicitly set `mode='extension'`. If `mode='primary'` is set on an extension view, Odoo treats it as a root view for a new model, not as a patch, and the parent view is ignored. The view appears to be created successfully but the UI shows the unpatched parent.

**Why it happens:**
`mode` defaults to `primary` if `inherit_id` is False/unset. When `inherit_id` is set, it defaults to `extension`. The documentation states this but it is easy to miss when building views programmatically.

**How to avoid:**
If creating an extension view: set `inherit_id` AND do NOT set `mode` (let it default to `extension`), OR explicitly set `mode='extension'`. If creating a standalone view variant: set `mode='primary'` and set `inherit_id` to the base view you are branching from.

**Warning signs:**
Extension view created with `mode='primary'` appears as a duplicate root view in the Views list. XPath modifications not applied to the parent.

**Phase to address:**
godoo-moduleX — ViewBuilder DSL sets mode based on whether `inherit_id` is present.

---

### Pitfall 4.7: `ir.model.access` — Missing `group_id` Grants Access to Everyone (Global ACL)

**What goes wrong:**
If `group_id` is NULL (unset) on an `ir.model.access` record, the access rule applies to ALL users, including portal and public users. This is the Odoo "global" ACL. Creating an access record without a group is NOT the same as "default deny" — it is "allow everyone." This is counterintuitive when building a module that should restrict access to specific groups.

**Why it happens:**
Odoo's security model: "if no access record exists, only Superuser can access." But "if an access record exists with no group, everyone can access." The NULL group is a feature (global permission), not an oversight.

**How to avoid:**
Always specify `group_id` in moduleX-created ACLs unless global access is explicitly desired. If you want "only admins," use `base.group_system`. If you want "internal users," use `base.group_user`. Document this contract prominently.

**Warning signs:**
All users can suddenly access a model that was supposed to be restricted.

**Phase to address:**
godoo-moduleX — ACL DSL requires explicit `group_id` or `global=True` flag; default is NOT global.

---

### Pitfall 4.8: Registry Reload — New Fields/Models Are Not Immediately Visible in Other Workers

**What goes wrong:**
When a new `ir.model` or `ir.model.fields` record is created via RPC, Odoo's worker that handled the request updates its own in-memory registry. Other workers (in a multi-worker Gunicorn setup) detect the change via database sequence polling — but this check happens at the START of the NEXT RPC call they receive, not immediately. A subsequent RPC call to a different worker may arrive before that worker reloads its registry, resulting in "Unknown field" or "Unknown model" errors.

**Why it happens:**
Odoo uses two database sequences (`caches` and `registry`) to signal cross-worker cache/registry invalidation. Workers check these at the beginning of each request. In a busy system with many workers, the reload may be delayed by several seconds.

**How to avoid:**
After creating a model or field, issue a no-op RPC (e.g., `ir.model.search([])`) to the same session to confirm the registry has been updated. Add retry logic in moduleX's post-create verification step. In tests, use a single-worker Odoo setup to eliminate race conditions.

**Warning signs:**
Intermittent "Unknown field" errors immediately after field creation, that resolve on retry. Tests pass in isolation but fail when run concurrently.

**Phase to address:**
godoo-moduleX — post-create verification with retry; testcontainers fixture uses single Odoo worker.

---

### Pitfall 4.9: `ir.rule` Domain Is Python eval — Security and Correctness Pitfalls

**What goes wrong:**
`ir.rule.domain_force` is a string that is `safe_eval()`'d server-side by Odoo using a restricted set of variables: `user` (current user recordset), `company_id` (current company singleton), `company_ids` (all accessible company IDs). Any domain syntax valid in Python (e.g., `[('user_id', '=', user.id)]`) works. INVALID: referencing any variable other than those three, using Python builtins, calling methods. Malformed domains raise `ValueError` at query time, not at create time.

**Why it happens:**
The domain is stored as text and only evaluated when a database query using that model is made. There is no validation on write.

**How to avoid:**
Validate the domain string in the SDK before sending: parse with `ast.literal_eval` to check syntax, then statically verify that all variable references are in `{user, company_id, company_ids}`. Provide a `validate_rule_domain(domain_str)` utility. Integration-test by creating the rule and then making a `search_read` call under a non-admin user.

**Warning signs:**
Rule created successfully but `search_read` on the model returns `ValueError: name 'X' is not defined` for non-admin users. Rule appears correct in the UI but all queries fail for affected users.

**Phase to address:**
godoo-moduleX — rule DSL validates domain syntax and variable references at build time.

---

### Pitfall 4.10: Deletion Order — Fields Before Models, Views Before Fields

**What goes wrong:**
Deleting a manual model via RPC before deleting its custom fields raises a PostgreSQL constraint error: the fields hold references to `ir.model` records and their DB columns depend on the table that is being dropped. Deleting `ir.ui.view` records that inherit from other views after deleting the parent view causes orphaned extension views that reference a non-existent `inherit_id`.

**Why it happens:**
`ir.model.fields` has a `model_id` Many2one to `ir.model` without cascade-on-delete from the RPC perspective. The DB-level cascade from module uninstall is Python code in `ir_model.py`, not a DB constraint.

**How to avoid:**
moduleX deletion order: (1) Delete `ir.ui.menu` entries, (2) Delete `ir.actions.act_window`, (3) Delete extension `ir.ui.view` records (children before parents), (4) Delete `ir.rule`, (5) Delete `ir.model.access`, (6) Delete `ir.model.fields` (custom fields on base models first, then x_model fields), (7) Delete `ir.model` records. The same topological sort used in apply is applied in reverse for destroy.

**Warning signs:**
`psycopg2.errors.ForeignKeyViolation` during deletion. Orphaned view records in `ir.ui.view` with non-existent `inherit_id`.

**Phase to address:**
godoo-moduleX — `destroy()` operation uses reverse dependency order; integration test runs full create + destroy cycle.

---

### Pitfall 4.11: `mail.thread` Inheritance — Cannot Be Expressed as `inherit_id` on ir.model

**What goes wrong:**
Adding chatter (mail.thread) to a custom x_model cannot be done by setting `ir.model.inherit_id` to `mail.thread`. `inherit_id` on `ir.model` is NOT the mechanism for mixing in Python behavior — it is for delegation inheritance (`_inherits` in ORM). Adding `mail.thread` behavior requires Python code (`_inherit = ['mail.thread']` in a Python class). This is fundamentally not expressible via RPC.

**Why it happens:**
Odoo Studio achieves chatter on custom models via a different mechanism: it marks `ir.model.mail_thread = True` (a boolean field on ir.model) which installs the `mail.thread` mixin at the ORM level. This field may not exist on all Odoo versions.

**How to avoid:**
Check for `ir.model.mail_thread` boolean field availability (v14+). Set `mail_thread=True` on the `ir.model` record during creation if the target Odoo version supports it. Do NOT attempt to set `inherit_id` to a `mail.thread` ir.model record. Document that chatter requires `mail_thread=True` and may not be supported on all versions.

**Warning signs:**
Custom model has no chatter even after setting `inherit_id` to a mail model. Field `mail_thread` not found on `ir.model` on older versions.

**Phase to address:**
godoo-moduleX — `mail_thread` option in model DSL, version-gated; integration test against v16 and v17.

---

### Pitfall 4.12: xml_id Uniqueness — Module Namespace Collision on Re-runs

**What goes wrong:**
`ir.model.data` (the external ID table) requires `(module, name)` to be unique. If moduleX registers all its records under module `__godoo__` (or a user-chosen logical module name) and the `name` key is derived from the resource identifier, a second create (e.g., apply after partial destroy) will raise a unique constraint violation unless the existing `ir.model.data` record is found and updated.

**Why it happens:**
Re-runs that create resources must either find the existing `ir.model.data` entry or use `ir.model.data.create_or_replace` semantics. Many RPC callers use `create` directly without checking for existing external IDs.

**How to avoid:**
Before creating a resource, search `ir.model.data` for `(module, name)` first. If found, skip creation and use the existing `res_id`. Use `ir.model.data.search_read` as the primary lookup in idempotent apply. The `noupdate=True` flag must be set to prevent module upgrades from wiping managed records.

**Warning signs:**
`odoo.exceptions.ValidationError: External ID already exists` on second apply. Records multiplied after partial destroy + re-apply.

**Phase to address:**
godoo-moduleX and godoo-state-manager — all creates route through an "ensure external ID" helper; integration test runs apply 3x and asserts idempotency.

---

### Pitfall 4.13: `ir.actions.act_window` and `ir.ui.menu` — Binding Requires Model Registry to Be Ready

**What goes wrong:**
Creating a menu item (`ir.ui.menu`) that points to an `ir.actions.act_window` that targets a custom model requires: (1) the model to exist in the registry, (2) the action to exist before the menu item references it, (3) the `res_model` field on `ir.actions.act_window` must match the model name exactly (including `x_` prefix). If any of these are wrong, the menu appears but opens a blank or error screen.

**Why it happens:**
Menu and action creation succeeds even if `res_model` is wrong — Odoo does not validate that `res_model` exists in the registry at action creation time. The error only manifests when the user clicks the menu.

**How to avoid:**
Creation order: model → fields → views → actions → menus. Validate `res_model` against `ir.model.search([('model', '=', res_model)])` before creating the action. After menu creation, verify via `ir.ui.menu.search_read` that the menu exists with the correct action.

**Warning signs:**
Menu created but clicking it shows "Model not found" or empty list view. `ir.actions.act_window` record exists but `search_read` against the target model fails.

**Phase to address:**
godoo-moduleX — create operation enforces order; `act_window` DSL validates `res_model` at build time.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip external ID registration on create | Simpler create code | Duplicate records on re-apply; no idempotency | Never — breaks core contract |
| Use `write_date` as sole drift signal | Simple drift check | False positives/negatives; breaks on multi-write | Never |
| Hardcode module name as `__godoo__` | Avoids configuration | Collision if user deploys two godoo instances | Only for single-tenant dev |
| Skip XML validation before arch_db write | Faster implementation | Runtime `ValidateError` with unhelpful message | Never |
| Ignore multi-worker registry delay in tests | Tests always pass | Intermittent CI failures in prod-like environments | Only in unit tests with mocks |
| Use `limit=0` for "all records" | Looks like "unlimited" | Version-dependent behavior; may return 0 records | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Odoo JSON-RPC auth | Generating client-side session UUID | Capture and reuse `session_id` cookie from Odoo auth response |
| ir.translation (v15) vs JSONB (v16+) | Using same write path for all versions | Version-detect on init, dispatch to `ir.translation` or lang-context write |
| testcontainers-python async | Calling sync API directly in async code | Wrap all testcontainers calls in `asyncio.to_thread()` |
| Odoo multi-worker Gunicorn | Assuming registry state is immediate | Add verification step with retry after model/field creation |
| ir.rule domain eval | Using Python f-string to build domain | Use structured domain builder that only emits allowed variable refs |
| Many2many command codes | Passing plain list of IDs | Use command tuple wrappers; (4, id, False) for link, (6, False, ids) for replace |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `search_read` without limit | Silently truncated at 100 records | Always specify explicit limit or use paginated `search_all()` helper | Any model with >100 records |
| Sequential RPC for field resolution | N+1 pattern; slow introspection | Batch via `fields_get()` on multiple models in one call | >10 models to introspect |
| Fetching all `ir.model.fields` at once | Large payload for wide models (200+ fields) | Request only needed fields via `fields` parameter | Models with >100 fields |
| No connection pool tuning | `httpx` defaults to 10 concurrent connections | Set `limits` on `AsyncClient` for high-concurrency scenarios | >10 concurrent callers |
| Binary field in-memory base64 for large files | MemoryError on Odoo server | Route large binaries through `ir.attachment` | Files >10MB |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Passing credentials in debug logs | Password leak in log aggregators | `OdooClientConfig.__repr__` must mask password |
| HTTP (not HTTPS) for non-localhost | Credentials in plaintext on network | Warn or reject `http://` URLs for non-localhost |
| ir.rule `domain_force` with unsanitized user input | Python code injection via `safe_eval` | Validate domain structure before RPC; never interpolate external strings |
| NULL `group_id` on `ir.model.access` | Global access to restricted model | Require explicit `global=True` flag; default requires group |
| Storing session beyond its TTL | Stale session used for privileged ops after logout | Clear `_session` on `OdooAuthError`; implement auto-reauth |

---

## "Looks Done But Isn't" Checklist

- [ ] **ir.model create:** Verify model is in `ir.model.search` AND in `fields_get()` of a test record — the registry may need a reload cycle
- [ ] **ir.model.fields create:** Verify field appears in `model.fields_get()` not just in `ir.model.fields.search`
- [ ] **ir.ui.view create:** Verify arch renders by loading the view in the UI (or using `ir.ui.view.read_combined`)
- [ ] **ir.model.access create:** Verify non-admin user can actually access the model (not just that the ACL record was created)
- [ ] **Translation write:** Verify ALL target languages have the correct value, not just the one written in the current session
- [ ] **State manager apply:** Run apply twice and verify record count is unchanged (idempotency test)
- [ ] **moduleX destroy:** Verify all `ir.model.data` entries for the module are removed (not just the model/field records)
- [ ] **Many2many field create:** Verify relation table exists in `ir.model.relation` and the table exists in PostgreSQL

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Orphaned x_model after partial create | MEDIUM | Use `ir.model.fields` unlink in order, then `ir.model` unlink; may need manual SQL for orphaned DB columns |
| Duplicate records from non-idempotent apply | MEDIUM | Identify duplicates via `search_count` vs `ir.model.data` count; manual dedup and re-link `ir.model.data` |
| Broken ir.ui.view arch causing 500 on menu click | LOW | Set `active=False` on the broken view record via RPC to disable it; fix arch and re-enable |
| Global ACL accidentally applied | HIGH | Delete the `ir.model.access` record immediately; audit records created by unauthorized users |
| Wrong `on_delete=cascade` on x_field | HIGH | Requires ORM migration — drop the column with cascade, recreate with correct on_delete; data loss if cascade already triggered |
| Translation JSONB null after wrong v16 write | LOW | Re-write all translations per language using `context={'lang': code}` for each installed language |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Pagination truncation | godoo-core hardening | Integration test: model with 150 records, `search_all()` returns all 150 |
| Naive UTC datetime | godoo-core hardening | Unit test: parse RPC datetime string, assert `tzinfo == UTC` |
| Session expiry handling | godoo-core hardening | Integration test: expire session mid-workflow, assert auto-reauth |
| Binary field base64 | godoo-core hardening | Integration test: round-trip binary write/read, compare hashes |
| m2m vs o2m remove semantics | godoo-state-manager | Integration test: `remove_unmanaged` on m2m doesn't delete shared records |
| Translation v15 vs v16 path | godoo-state-manager | Integration test: write translation, read back in each language |
| HTML diff normalization | godoo-state-manager | Unit test: normalized HTML compare returns equal for equivalent HTML |
| Circular dependency sort | godoo-state-manager | Unit test: topological sort with circular graph raises `PlanError` |
| External ID idempotency | godoo-state-manager + moduleX | Integration test: apply 3x, assert 1 record + 1 `ir.model.data` entry |
| ir.model `state='manual'` | godoo-moduleX | Integration test: model queryable immediately after create |
| Many2many relation collision | godoo-moduleX | Integration test: two m2m fields on same source/target model |
| Registry reload delay | godoo-moduleX | Integration test: field created, verified via `fields_get()` with retry |
| ir.rule domain validation | godoo-moduleX | Integration test: rule with valid domain, then `search_read` as non-admin user |
| Deletion order | godoo-moduleX | Integration test: full create cycle then full destroy, assert no orphans |

---

## Sources

- Odoo 18.0 External API Reference: https://www.odoo.com/documentation/18.0/developer/reference/external_api.html
- Odoo 19.0 External RPC API (deprecation notice): https://www.odoo.com/documentation/19.0/developer/reference/external_rpc_api.html
- Odoo Security Reference: https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html
- Odoo Views Reference: https://www.odoo.com/documentation/18.0/developer/reference/backend/views.html (mode/inherit_id)
- Odoo ORM API: https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html
- Odoo Multi-company Guidelines: https://www.odoo.com/documentation/18.0/developer/howtos/company.html
- Odoo v16 JSONB translation PR: https://github.com/odoo/odoo/pull/97692
- ir.model Model Guide (registry mechanics): https://www.dasolo.ai/blog/odoo-data-api-5/odoo-ir-model-guide-167
- ir.model.access Documentation: https://odoo-development.readthedocs.io/en/latest/odoo/models/ir.model.access.html
- OCA/odoorpc issue tracker (pagination): https://github.com/OCA/odoorpc/issues/1
- Odoo GitHub issue #26559 (binary MemoryError): https://github.com/odoo/odoo/issues/26559
- CONCERNS.md: .planning/codebase/CONCERNS.md (session expiry, transport lifecycle, password in memory)
- Odoo Forum: RPC datetime/timezone behavior https://www.odoo.com/forum/help-1/json-rpc-dont-use-context-return-datetime-gmt-and-lang-per-default-85560
- Odoo Forum: adding translations via RPC v16 https://www.odoo.com/forum/help-1/product-template-translation-xml-rpc-with-python-possible-odoo-16-250231

---
*Pitfalls research for: Python Odoo SDK — godoo RPC client, introspection, state-manager, moduleX*
*Researched: 2026-04-10*
