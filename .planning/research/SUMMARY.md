# Research Summary --- godoo-py v1.1 Typed Models and Browser Reach

**Project:** godoo-py
**Domain:** Python async Odoo SDK --- optional Pydantic typed layer + browser transport de-risk
**Researched:** 2026-05-27
**Confidence:** HIGH (core) / MEDIUM (Pyodide --- inherently uncertain, see below)

---

## Executive Summary

v1.1 adds two high-value capabilities to an already-shipped library: instance-specific typed models (a CLI codegen path that emits Pydantic model files, plus a polymorphic read() dispatch layer in core), and a Pyodide/browser spike. The typed-models feature is well-understood and immediately implementable. The architecture is clean: the existing Introspector + CodeGenerator infrastructure is reused as-is; the new PydanticCodeGenerator sits alongside the TypedDict one; and a thin _pydantic_transform.py module inside godoo-client is the single point where pydantic is ever imported at runtime. The headline constraint --- core default install stays httpx-only --- is enforced by duck-typed dispatch on __odoo_model__ and a lazy import, never by isinstance(BaseModel).

The Pyodide situation is a genuine open decision and must not be presented to planners as solvable this milestone. The two researcher threads conflict on the httpx-in-Pyodide question (one found httpx pre-patched and working via a Fetch adapter; the other found httpx blocked by the absence of POSIX sockets, with only urllib3 having native Emscripten support). Both agree on the hard, unambiguous blocker: Pyodide 0.29.x ships CPython 3.13.2, and godoo requires >=3.14. No Pyodide release with Python 3.14 exists yet. The spike primary output is therefore a decision, not a build: drop the Python floor to >=3.12 for a browser build, or defer the entire effort until Pyodide ships Python 3.14.

The directory rename (packages/godoo -> packages/godoo-client) is mechanical and independent of the other two features, but is the highest-risk configuration operation: seven tool-config locations hardcode the filesystem path. It must go first, in a single atomic commit using git mv, followed by a full uv sync + mypy + wheel-build smoke test before any feature work begins.

---

## Stack Additions

No new deps land in godoo-client default install. The sole runtime dep stays httpx>=0.27.

**New optional/tool dependencies:**

- **pydantic>=2.13** --- in godoo-client[typed] optional extra only; also a runtime dep of godoo-introspection (generator needs pydantic to validate schema responses). Current: 2.13.4 (2026-05-06). Supports Python >=3.9 through 3.14.
- **typer>=0.26** --- in godoo-introspection runtime deps; drives the godoo-introspect CLI. Current: 0.26.2 (2026-05-27). Click is vendored inside typer 0.26+; do not declare click as a direct dep.
- **pyodide-httpx 0.2.0** --- spike-only; NOT added to any pyproject.toml.

**STACK.md self-conflict resolved:** The section on what NOT to add says pydantic is not needed in godoo-introspection deps (the generator emits strings). The Integration Notes section says pydantic IS a runtime dep there. Architecture confirms pydantic is needed for runtime schema-response validation. **Verdict: pydantic IS a runtime dep of godoo-introspection.**

---

## Feature Scope

### Table Stakes (must have)

- CLI entrypoint (godoo-introspect) with --url/--db/--user/--password, --output, --format; credentials via env vars preferred over positional args
- Pydantic model emitter: one file per Odoo model + barrel __init__.py
- id: int required; all other fields Optional[T] = None (handles partial reads without ValidationError)
- Wire transform: False -> None for all non-boolean optional fields (Odoo returns False not None for unset fields --- highest-priority transform)
- Wire transform: many2one [id, Display Name] -> Ref dataclass (Ref.id: int, Ref.name: str)
- __odoo_model__: ClassVar[str] on every generated model (satisfies duck-type dispatch)
- @overload pair on OdooClient.read and search_read: str -> list[dict], type[T] -> list[T]
- godoo[typed] optional extra declared in packages/godoo-client/pyproject.toml
- Package rename packages/godoo -> packages/godoo-client

### Differentiators (should have)

- Ref[Model] generic type with informational type parameter (mypy-visible relational type)
- OdooBaseModel shared base in godoo.client.typed carrying @model_validator wire transforms so generated files stay thin
- Selection-field Literal[...] generated from the live instance actual registered values
- --models filter flag for large instances (P2, not blocking launch)

### Anti-Features (explicitly excluded)

- Nested model auto-fetch (parent_id auto-fetches the parent) --- N+1 RPC, circular refs, wrong scope boundary
- Dynamic runtime model synthesis via pydantic.create_model() --- statically invisible to pyright/Pylance
- Auto-regeneration at import time --- requires live Odoo at startup, breaks CI
- mypy --strict applied to generated files --- generates noise from Optional chains

### Defer to v1.x/v2+

- godoo[browser] committed build (post-spike decision)
- Ref.fetch(client) auto-fetch helper
- Schema version pinning in generated file headers

---

## Architecture & Build Order

### Component Map

New/modified only. **Unchanged:** all 8 services, JsonRpcTransport, SafetyContext, errors.py, config.py, TypedDict codegen.py, type_mapper.py, IntrospectionCache, godoo-testcontainers, godoo-meta.

| Component | Type | Package | Path |
|-----------|------|---------|------|
| typed.py --- OdooModel Protocol + Ref dataclass | NEW | godoo-client | src/godoo/client/typed.py |
| _pydantic_transform.py --- lazy-pydantic-import module | NEW | godoo-client | src/godoo/client/_pydantic_transform.py |
| OdooClient.read / search_read @overload + dispatch | MODIFIED | godoo-client | src/godoo/client/client.py |
| OdooClient._typed_read (private method) | NEW | godoo-client | src/godoo/client/client.py |
| rpc/protocol.py --- Transport Protocol seam | NEW | godoo-client | src/godoo/client/rpc/protocol.py |
| OdooClientConfig.transport_factory | MODIFIED (None default) | godoo-client | src/godoo/client/client.py |
| pydantic_type_mapper.py | NEW | godoo-introspection | src/godoo/introspection/pydantic_type_mapper.py |
| pydantic_codegen.py --- PydanticCodeGenerator | NEW | godoo-introspection | src/godoo/introspection/pydantic_codegen.py |
| cli.py + [project.scripts] entry | NEW | godoo-introspection | src/godoo/introspection/cli.py |

### Import Isolation (load-bearing constraint)

_pydantic_transform is NEVER in __all__, never in any __init__.py, never at module-load time. Dispatch guard is hasattr(model, "__odoo_model__") --- never isinstance(BaseModel) or issubclass(BaseModel). The OdooModel Protocol and Ref in typed.py are stdlib-only (no pydantic dep).

CI gate: python -c "import godoo.client" in a pydantic-free venv (pydantic not installed) must complete without ImportError.

### Build Order (all researchers agree)

**Step 1 --- Dir rename** (packages/godoo -> packages/godoo-client)

Why first: every subsequent change touches files here; do rename before adding any new files. The rename is a pure filesystem + config update with no logic change.

7 config locations to update: root pyproject.toml (mypy_path, version_toml, build_command), .github/workflows/test.yml (mypy invocation), mkdocs.yml (paths). uv workspace glob and hatchling only-include are both safe.

Verify after: uv sync && uv run python -c "import godoo.client" + uv build + tar tzf dist/*.tar.gz | grep godoo/client

**Step 2 --- Transport Protocol seam** (rpc/protocol.py + transport_factory on OdooClientConfig)

Why second: purely additive, zero behaviour change; establishes the seam for Pyodide spike. JsonRpcTransport already satisfies Transport Protocol structurally --- no modification needed.

**Step 3 --- Typed models core** (typed.py, _pydantic_transform.py, @overloads, [typed] extra)

Why third: generated model packages import from godoo.client.typed; core must exist first.

Substeps: 3a typed.py (OdooModel Protocol + Ref, stdlib-only), 3b [typed] extra in pyproject.toml, 3c _pydantic_transform.py (lazy import + clear ImportError message), 3d @overload + _typed_read + dispatch guard in client.py, 3e import-isolation test + wire-transform unit tests. OD-1 and OD-2 must be settled before this step begins.

**Step 4 --- Pydantic CLI generator** (pydantic_codegen.py, cli.py, project.scripts)

Why fourth: emits "from godoo.client.typed import OdooModel" --- Step 3 must exist first. Adds pydantic>=2.13 + typer>=0.26 to godoo-introspection runtime deps.

**Step 5 --- Pyodide spike** (decision-gated; NOT a feature build)

Why last: spike outcome determines whether to commit to browser build. Transport Protocol from Step 2 is the only prerequisite. No code lands in any package until verdict is written.

---

## Watch Out For --- Top Pitfalls

**P1 --- Pydantic import leakage at import time**

from __future__ import annotations defers annotation evaluation but does NOT prevent import of a top-level-referenced module. Any pydantic class outside if TYPE_CHECKING: in godoo/client/ tree breaks the default install with ModuleNotFoundError: No module named pydantic.

Prevention: import-isolation CI test in a pydantic-free venv (pydantic not installed, not just deferred). This is the primary go/no-go gate for Step 3.

**P2 --- isinstance(BaseModel) or issubclass(BaseModel) dispatch**

Forces pydantic import on every read() call regardless of which branch is taken. Even deferred, fires for callers who never installed [typed].

Prevention: use only hasattr(model, "__odoo_model__"). Pydantic enters only inside the branch body, in a try/import that raises a clear Install godoo[typed] message.

**P3 --- Wire-format edge cases (5 failure modes)**

(a) False -> None for all non-boolean fields. (b) many2one arrives as [int, str] list not a dict. (c) Selection drift after codegen: new values not in generated Literal raise ValidationError. (d) Datetime strings are naive UTC ("2024-01-15 14:30:00") --- must attach timezone.utc. (e) Monetary/float must not be re-rounded.

Prevention: wire_transform unit test table: all ttype groups x {normal, False, edge} inputs. Test False for every ttype group.

**P4 --- Rename config blast radius**

7 tool-config paths hardcode packages/godoo/. Missing any one means mypy silently skips core (no error, just wrong coverage), or semantic-release fails to find the version on the next release.

Prevention: use git mv (preserves blame and git log --follow); run uv sync after; verify wheel contents.

**P5 --- PEP 420 namespace collision from stray __init__.py**

src/godoo/ must have NO __init__.py in any package. One stray file makes godoo a regular package and breaks other sub-namespaces silently.

Prevention: CI smoke test: python -c "import godoo; assert godoo.__file__ is None".

**P6 --- @overload + TypeVar + Protocol mypy strict-mode friction**

Three sub-issues: (a) overload ordering --- type[T] overload before str overload to prevent overlap errors; (b) TypeVar variance with bound=OdooModel Protocol; (c) warn_return_any firing on pydantic model_validate return.

Prevention: write @overload signatures first, run mypy on them alone before adding implementation body; use cast(list[T], ...) at pydantic boundary.

**P7 --- Pyodide spike: test actual HTTP calls, not imports**

asyncio.open_connection() -> POSIX socket -> NotImplementedError in Emscripten. Importing godoo.client succeeds (pure Python). The spike does not exist unless it makes a real HTTP call.

Prevention: (1) make an actual Odoo JSON-RPC call; (2) test cross-origin CORS conditions; (3) test in real Marimo or JupyterLite, not just pyodide.runPythonAsync().

---

## Open Decisions (tensions named, not smoothed)

### OD-1: Partial-read strategy --- All-Optional vs model_construct()

**Tension:** FEATURES.md recommends all non-id fields as Optional[T] = None (matching openapi-python-client, ariadne-codegen). ARCHITECTURE.md mentions model_construct() as an option. PITFALLS.md warns model_construct() produces a typed instance without wire-transform guarantees (False->None skipped, many2one not unpacked).

**Tradeoffs:**
- All-Optional: partial reads always work; model_validate() runs wire transforms; IDE shows all fields Optional (accurate --- you may not have fetched them).
- model_construct(): bypasses all validation including wire transforms; essentially a typed dict wrapper.

**Recommended resolution:** All-Optional as the default. model_construct() is a documented escape hatch only, gated behind validate=False. The @overload for type[T] path should not accept a fields kwarg at all, or raise TypeError if both are passed --- prevents the partial-fetch + full-validation footgun. **Must be settled before Step 3 begins; the @overload signature encodes this decision.**

### OD-2: Boolean False-coercion --- concrete design

**Tension:** The @model_validator(mode=before) must convert False -> None for unset optional fields, but False is a valid value for boolean fields. A blanket replacement silently corrupts boolean fields.

**Options:**
- **A (recommended):** Emit boolean fields as plain bool (non-optional, default=False). The @model_validator inspects model_fields and skips coercion for fields whose annotation is bool. Decidable at validation time without a runtime FieldMeta lookup.
- **B:** Tag fields with ttype via ClassVar marker; runtime validator reads tag. More complex.
- **C:** Emit per-field @field_validator only for non-boolean optional fields. Generated files become verbose.

**Recommended resolution:** Option A. **Must be settled before Step 3 wire-transform implementation.**

### OD-3: httpx vs POSIX socket in Pyodide --- genuine researcher conflict

**Tension:** STACK.md found httpx IS bundled + pre-patched in Pyodide 0.29.x via Cloudflare Fetch adapter (httpx_patch.py overrides AsyncClient._send_single_request via JS Fetch API). FEATURES.md found httpx is NOT supported (pyodide-http patches requests/urllib but NOT httpx; Flet issue #4840 shows getaddrinfo NotImplementedError in practice; only urllib3 >=2.2.0 has official native Emscripten support).

This is a genuine conflict between the two researcher agents. The discrepancy is likely: (a) httpx is importable in Pyodide (pure-Python, so yes), and (b) httpx async I/O makes POSIX socket calls Emscripten cannot fulfill. Both may be true in different contexts (Pyodide-bundled httpx has a pre-patched Fetch transport; micropip-installed godoo hits the raw socket wall).

**Resolution:** Only an actual HTTP call test resolves this. OD-3 does not affect Steps 1-4.

**Unambiguous blocker regardless of OD-3:** Pyodide 0.29.x = CPython 3.13.2. godoo requires >=3.14. The spike cannot reach the httpx question until the Python floor decision is made:
- Option A: Drop floor to >=3.12 for a browser-specific build or wheel
- Option B: Wait for Pyodide + Python 3.14 (PEP 776 approved by CPython SC, no ship date)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | pydantic 2.13.4 and typer 0.26.2 verified on PyPI; one STACK.md self-conflict resolved |
| Features | HIGH | SEED-002 decisions already made; research validates and refines; feature dependencies non-circular |
| Architecture | HIGH | Based on direct codebase inspection; all extension points identified; unchanged-component list verified |
| Pitfalls (typed models) | HIGH | All pitfalls grounded in codebase structure; wire-transform edge cases enumerated |
| Pyodide spike | MEDIUM | Python 3.14 blocker is HIGH confidence (Pyodide changelog verified); httpx transport compatibility empirically unresolved; by design |

**Overall:** HIGH for Steps 1-4; MEDIUM for Step 5 scope (spike by nature).

### Gaps to Address

- **OD-1:** settle during requirements before Step 3; @overload signature encodes it
- **OD-2:** settle during requirements before Step 3 wire-transform implementation
- **OD-3:** resolve during Step 5 spike execution only; does not block Steps 1-4
- **pydantic pin:** confirm >=2.13 (not >=2.0) to prevent pydantic v1 installs during Step 3
- **--format default:** confirm whether pydantic or typeddict is the CLI default during Step 4 scoping

---

## Sources

### Primary (HIGH confidence --- verified)
- Pydantic 2.13.4 --- https://pypi.org/project/pydantic/
- Typer 0.26.2 --- https://pypi.org/project/typer/
- pyodide-httpx 0.2.0 --- https://pypi.org/project/pyodide-httpx/
- Pyodide changelog (Python 3.13.2, httpx 0.28.1 added) --- https://pyodide.org/en/stable/project/changelog.html
- Direct codebase inspection: packages/godoo/pyproject.toml, client.py, rpc/transport.py, introspection/codegen.py, introspection/type_mapper.py
- PEP 621 optional-dependencies --- https://packaging.python.org/en/latest/guides/writing-pyproject-toml/

### Secondary (MEDIUM confidence --- community sources)
- Cloudflare httpx_patch.py (Fetch adapter for bundled httpx) --- https://github.com/cloudflare/pyodide/blob/main/packages/httpx/httpx_patch.py
- Pyodide discussion #4999 (bundled vs micropip httpx) --- https://github.com/pyodide/pyodide/discussions/4999
- pyodide-http (patches requests/urllib, NOT httpx) --- https://github.com/koenvo/pyodide-http
- urllib3 Emscripten docs --- https://urllib3.readthedocs.io/en/latest/reference/contrib/emscripten.html
- Flet issue #4840 (httpx + Pyodide getaddrinfo NotImplementedError) --- https://github.com/flet-dev/flet/issues/4840
- marimo CORS issue #3169 --- https://github.com/marimo-team/marimo/issues/3169
- datamodel-code-generator, ariadne-codegen, openapi-python-client, sqlacodegen --- codegen pattern reference
- Pydantic v2 model_validator docs + partial validation issue #5031
- PEP 544 (runtime_checkable Protocol) --- https://peps.python.org/pep-0544/
- SQLAlchemy 2.0 typed select (@overload dispatch precedent)

---
*Research completed: 2026-05-27*
*Ready for roadmap: yes (Steps 1-4); Step 5 is spike-scoped*
