# Pitfalls Research

**Domain:** Python async SDK — optional Pydantic typed layer, PEP 420 namespace, uv workspace, Pyodide spike
**Researched:** 2026-05-27
**Confidence:** HIGH (all pitfalls grounded in actual codebase structure, not generic advice)

---

## Critical Pitfalls

### Pitfall 1: Pydantic imported at `import godoo` time via a top-level type annotation

**What goes wrong:**
`from __future__ import annotations` defers *evaluation* of annotations but does not prevent *import* of the annotated module. If any file reachable from `godoo/client/__init__.py` at module-load time contains a top-level `from pydantic import BaseModel` (even inside a `TYPE_CHECKING` block that was accidentally left outside), pydantic is imported for every user — including those who never installed the `[typed]` extra. The error shows up as `ModuleNotFoundError: No module named 'pydantic'` only for users on the default install.

**Why it happens:**
The `from __future__ import annotations` convention is universal in this codebase. Developers see annotation-only imports throughout and may assume a top-level import in a type annotation is safe. It is not — only imports guarded by `if TYPE_CHECKING:` are elided at runtime. A Protocol defined at module scope that inherits from a pydantic class pulls in pydantic unconditionally regardless of `from __future__ import annotations`.

**How to avoid:**
- The transform/validation layer lives in a new submodule `godoo.client.typed` (or similar). Nothing in that module is imported at module load time from any file in the existing `godoo/client/` tree.
- The `OdooModelProtocol` (or duck-type check) used in `client.py` must contain zero pydantic references. `hasattr(model, "__odoo_model__")` is pure-Python. If a Protocol class is used instead, it must live under `TYPE_CHECKING` only and must not inherit from any pydantic class.
- The `@overload` signatures for `read(model: type[T], ...)` and `read(model: str, ...)` use `T` bound to the Protocol — the Protocol import itself must be `if TYPE_CHECKING` only.
- The lazy-dispatch branch (`if hasattr(model, "__odoo_model__")`): the call to `import godoo.client.typed` (or wherever pydantic is used) happens *inside* that branch, never at function definition time.
- Write an import-isolation test (see Technical Debt Patterns below).

**Warning signs:**
- Any `import pydantic` or `from pydantic import` outside a `if TYPE_CHECKING:` block in any file under `packages/godoo/src/godoo/client/`.
- Running `python -c "import sys; import godoo.client; print([k for k in sys.modules if 'pydantic' in k])"` in a venv with no pydantic installed and getting an ImportError rather than an empty list.
- The `[tool.mypy.overrides]` for `pydantic` being removed or set to `ignore_missing_stubs = false` without a corresponding `ignore_missing_imports`.

**Phase to address:** Typed Models phase (feature implementation). Must be a go/no-go gate — do not merge without the isolation test passing in a pydantic-free venv.

---

### Pitfall 2: `from __future__ import annotations` hides pydantic leaks but does not prevent them

**What goes wrong:**
`from __future__ import annotations` makes all annotations strings at runtime (PEP 563). This means `def read(self, model: type[OdooModel], ...)` does not evaluate `OdooModel` at function definition time. Developers may therefore write `OdooModel` as a top-level name (imported outside `TYPE_CHECKING`) thinking the deferred annotation makes it safe. This works under mypy but fails at runtime if `get_type_hints()` or Pydantic's own model validation calls `typing.get_type_hints()` on the client class — which resolves the string annotations and triggers the import.

Additionally, `@overload` decorators are evaluated at definition time for the decorator machinery itself (even though annotations are strings). Any default argument that references pydantic at definition time is still a runtime import.

**Why it happens:**
This project uses `from __future__ import annotations` in every file (project convention). The false sense of safety is strong — "annotations are strings, so nothing is imported." True for the annotation text, not for the import that provides the name.

**How to avoid:**
- Any name used in an annotation that comes from pydantic must be under `if TYPE_CHECKING:`.
- Never use a pydantic class as a default argument value: `def read(self, model: type[T] = BaseModel)` — this evaluates at definition time regardless of annotations future.
- If `get_type_hints()` is ever called on `OdooClient` (e.g., by a framework or introspection tool), ensure the `localns` argument provides any needed pydantic names or that the call is wrapped to avoid it in the default install.
- Run the import isolation test in a subprocess that has no pydantic in its environment (not just "not imported yet" — actually absent from the venv).

**Warning signs:**
- `typing.get_type_hints(OdooClient.read)` raising `NameError` in a pydantic-free environment.
- Any pydantic class name appearing as a bare identifier outside `if TYPE_CHECKING:` in `client.py`.

**Phase to address:** Typed Models phase, specifically the `@overload` + dispatch implementation task.

---

### Pitfall 3: `isinstance(model, BaseModel)` or `issubclass(model, BaseModel)` as the dispatch check

**What goes wrong:**
The intuitive dispatch check is `isinstance(model, type) and issubclass(model, BaseModel)`. This requires importing `BaseModel` at the point of the `if` check — which runs at call time, not import time — but it still means `import pydantic` happens on the first typed `read()` call even for callers who did not install `[typed]`. Worse, if pydantic is absent, the first typed call raises `ModuleNotFoundError` with a confusing traceback inside `client.py` rather than a clear `ImportError` at import time of the typed module.

**Why it happens:**
`issubclass(model, BaseModel)` is the natural Python idiom for "is this a pydantic model." It is also the approach shown in most pydantic tutorials for dynamic dispatch.

**How to avoid:**
Use duck-typing: `hasattr(model, "__odoo_model__")`. The `__odoo_model__` attribute is set by the code generator on every generated class. This check requires zero pydantic imports. The generated class *happens* to be a `BaseModel` subclass, but the dispatch decision does not need to know that. The pydantic import happens inside the branch body, inside a `try/import` that raises a clear `ImportError: Install godoo[typed] to use model-class dispatch`.

**Warning signs:**
- Any `issubclass` or `isinstance` call involving `BaseModel` in `client.py` or any file in `godoo/client/`.
- A Protocol class that lists `BaseModel` as a base in its definition.

**Phase to address:** Typed Models phase — enforce this constraint during the `@overload`/dispatch design review before implementation.

---

### Pitfall 4: Partial-read validation failure when `fields=[...]` is passed with a model class

**What goes wrong:**
`client.read(ResPartner, [1], fields=["name", "email"])` fetches only two fields. The Pydantic model for `ResPartner` has `required` fields (at minimum `id`) and dozens of `Optional` fields. If strict validation is attempted, every missing field that Pydantic considers required will raise `ValidationError`. The user gets an inscrutable error listing every field they did not fetch.

Additionally, the current TypedDict codegen emits `id: Required[int]` and everything else as `NotRequired`. The Pydantic codegen will need a parallel design decision. Using `model_validate()` on partial data without `strict=False` or `model_construct()` will always fail for partial reads.

**Why it happens:**
Partial reads are common in Odoo (fetching only display fields for list views). The typed path looks like a drop-in for the raw path. Developers will naturally pass `fields=` expecting it to work the same way.

**How to avoid:**
Make the design decision explicit and enforce it in the implementation:

- **Option A (recommended):** When a model class is passed, `fields` is silently ignored and all model fields are fetched. Document this clearly. The model class carries the authoritative field list via `model_fields` (pydantic). Partial selection stays on the raw string path.
- **Option B:** Use `model_construct(**data)` (skip validation) when `fields` is provided alongside a model class. This gives the typed instance but with no validation — essentially a typed `dict` wrapper. Useful but the type safety is illusory.
- **Option C:** Raise `TypeError` if both a model class and an explicit `fields` list are passed. Clear error, no silent footgun.

Whatever the choice, it must be decided in design (not discovered in QA) and the `@overload` signatures should express it (e.g., Option A: the `type[T]` overload has no `fields` parameter).

**Warning signs:**
- Test suite has no test for `read(ModelClass, ids, fields=["name"])` — the failure mode is invisible until a user hits it.
- The `@overload` for the model-class path accepts `fields: list[str] | None = None` identical to the raw path — this invites the footgun.

**Phase to address:** Typed Models phase, design review step before any implementation.

---

### Pitfall 5: Odoo wire-format edge cases in the transform layer

**What goes wrong:**
Odoo's JSON-RPC responses have several non-obvious wire conventions. Each is a silent data corruption bug if the transform does not handle it:

**5a. `False` for empty across all field types.**
A field with no value returns `False` (not `None`, `""`, `0`, or `[]`). This applies to `char`, `text`, `integer`, `float`, `monetary`, `many2one`, `date`, `datetime`, and `selection`. The current TypedDict codegen already handles this with `str | Literal[False]`, but the Pydantic transform layer must coerce `False → None` before Pydantic sees the value — or use a custom validator. If `False` reaches a `str` field without coercion, Pydantic accepts it as a truthy value and silently stores `False` where `str` was expected (Pydantic v2 with `strict=False`).

**5b. `many2one` is `[id, "Display Name"]` or `False`.**
A `many2one` field in a read result is either `False` (no relation set) or `[1234, "Partner Name"]` (a two-element list). This is not a dict. The transform must detect the list shape and construct a `Ref[Model]` (or named tuple, or dataclass). If `Ref` is itself a Pydantic model, `model_validate([1234, "Partner Name"])` will fail unless a custom `__get_validators__` / `@model_validator` handles the list input.

**5c. Selection values not matching generated `Literal`.**
The codegen captures `selection` values at generation time from the live instance. Odoo allows modules to extend selection fields (e.g., adding a payment method). If a custom module adds `"sepa_ct"` to a selection field after codegen was run, the wire value `"sepa_ct"` arrives but the generated `Literal['manual', 'check_printing']` does not include it. Pydantic raises `ValidationError`. This is instance drift and is inherent to static codegen — but must be documented and handled gracefully (log warning + fall back to the raw dict path rather than raising).

**5d. Datetime timezone / format.**
Odoo returns datetimes as naive UTC strings in the format `"2024-01-15 14:30:00"` (no `T`, no `Z`, no timezone offset). Python's `datetime.fromisoformat()` in 3.14 accepts this but produces a naive datetime. The transform should attach UTC tzinfo explicitly (`datetime.replace(tzinfo=timezone.utc)`) to avoid ambiguity. Date fields are `"2024-01-15"` — `date.fromisoformat()` handles this without issue.

**5e. Monetary/float rounding.**
`monetary` and `float` fields arrive as JSON numbers. JSON → Python float conversion is exact for values representable in IEEE 754, but Odoo's `digits` metadata (e.g., `(16, 2)` for currency) specifies the display precision, not the storage precision. The transform should not re-round the value — round-tripping `12.345` through Python `round(v, 2)` loses data. Store the raw float and let the display layer decide precision.

**How to avoid:**
- Write a dedicated `wire_transform.py` module with one function per ttype group, tested independently of Pydantic with a table of wire values → expected Python values. Test `False` for every ttype group, not just `char`.
- For `many2one`, write a Pydantic custom type that accepts both `False` and `[int, str]` inputs.
- For selection drift: wrap `model_validate()` in a try/except; on `ValidationError` that names a `Literal` field, log at WARNING and return the raw dict instead of raising.
- For datetimes: always attach `timezone.utc` — never leave datetimes naive.
- For monetary: store as `float`, document the `digits` metadata location (`FieldMeta.digits`), do not re-round.

**Warning signs:**
- Transform tests only use `str` values, never `False`.
- `many2one` field type emitted as `tuple[int, str]` in Pydantic model without a custom validator for the `[int, str]` list shape.
- No test for a selection value not in the generated `Literal`.
- Datetimes in tests that use naive `datetime.fromisoformat("2024-01-15 14:30:00")` without asserting `tzinfo`.

**Phase to address:** Typed Models phase — the transform layer is the riskiest part of the implementation.

---

### Pitfall 6: uv-workspace + hatchling dir rename — editable install breakage

**What goes wrong:**
The rename is `packages/godoo` → `packages/godoo-client` (workspace dir name only; dist name is already `godoo-client`; import namespace stays `godoo.*`). After the rename:

- `uv.lock` contains cached paths. `uv sync` after rename without `uv lock --upgrade-package godoo-client` leaves stale editable `.pth` entries pointing at the old path.
- `[tool.hatch.build.targets.wheel] only-include = ["src/godoo/client"]` is a content path inside `src/`, not the workspace dir path — this one is safe. But if any hatch config uses `packages = [...]` referencing the workspace dir name, it breaks.
- The root `pyproject.toml` `[tool.mypy] mypy_path` explicitly lists `"packages/godoo/src"` — this must be updated to `"packages/godoo-client/src"` or mypy silently stops type-checking the core package.
- The CI `test.yml` line `uv run mypy packages/godoo/src ...` has the same hardcoded path.
- `[tool.semantic_release] version_toml` points at `"packages/godoo/pyproject.toml:project.version"` — must update.
- `[tool.coverage.run] source_pkgs = ["godoo.client", ...]` uses the import namespace (safe), not the dir name (safe).

**Why it happens:**
The workspace dir name and the dist name were out of sync from the start (`packages/godoo` dir / `godoo-client` dist). The rename closes the gap but requires touching every tool config that uses the filesystem path.

**How to avoid:**
Treat the rename as a search-and-replace across all config files, not just `pyproject.toml`. Checklist:
1. `git mv packages/godoo packages/godoo-client` — preserves history; do not delete+add.
2. Update `packages/godoo-client/pyproject.toml` — already correct (`name = "godoo-client"`).
3. Update root `pyproject.toml`: `mypy_path`, `build_command` in `[tool.semantic_release]`, `version_toml`.
4. Update `.github/workflows/test.yml`: the `mypy` invocation path.
5. Run `uv sync` (regenerates lockfile entries) then verify `uv run python -c "import godoo.client"` works.
6. Check for stale `.egg-info` / `__pycache__` directories under the old path that might confuse Python's import machinery if the old dir still exists transiently.
7. PEP 420 namespace check: confirm `packages/godoo-client/src/godoo/` has **no** `__init__.py` and that no other package under the namespace accidentally gained one during any build cache flush.

**Warning signs:**
- `mypy` passes with no errors but is not checking `godoo.client` (because the path is wrong and mypy silently skips missing paths by default with `explicit_package_bases`).
- `import godoo.client` works in the dev venv but the wheel built with `uv build` does not contain the `godoo/client/` tree (because `only-include` path is evaluated relative to `src/`, which is inside the renamed dir — verify post-build with `tar tzf dist/*.tar.gz | grep godoo`).
- A stray `__init__.py` at `packages/godoo-client/src/godoo/__init__.py` causing namespace collision.

**Phase to address:** Rename phase (first phase of v1.1, before any feature work).

---

### Pitfall 7: PEP 420 namespace collision from a stray `__init__.py`

**What goes wrong:**
PEP 420 implicit namespace packages require that **no** `__init__.py` exists in the shared namespace directory (`src/godoo/`). Currently all three packages have `src/godoo/{client,introspection,testcontainers}/` without a `src/godoo/__init__.py` — correct. If any tool, build step, or developer adds `src/godoo/__init__.py` to any one package, Python's import machinery treats `godoo` as a regular package belonging to that one package. The other two packages' sub-namespaces become unreachable even if all three are installed.

Specific triggers:
- `hatchling` generating an `__init__.py` when regenerating stubs.
- A developer adding `__init__.py` to satisfy a mypy complaint.
- `uv build` with `packages = ["godoo"]` (if used) potentially creating one.
- An IDE "create package" action in the `src/godoo/` directory.

**Why it happens:**
The absence of `__init__.py` is the namespace package mechanism, which is counterintuitive — most Python experience says "directories need `__init__.py` to be packages." The rename phase is a high-risk moment because file system operations may inadvertently create one.

**How to avoid:**
- Add a unit test: `assert not (Path("packages/godoo-client/src/godoo/__init__.py")).exists()` and same for the other two packages. Run this in CI.
- Or: `python -c "import godoo; print(godoo.__file__)"` should print `None` (namespace package) not a file path. Add this as a smoke test.
- Review hatchling `only-include` and `sources` configs to ensure they do not produce `__init__.py` at the namespace level.

**Warning signs:**
- `import godoo.client` works but `import godoo.introspection` fails with `ModuleNotFoundError`.
- `godoo.__file__` is not `None`.
- `godoo.__path__` is a `_NamespacePath` with only one entry instead of three.

**Phase to address:** Rename phase — verify before and after the `git mv`.

---

### Pitfall 8: mypy --strict friction with the `@overload` + TypeVar + Protocol dispatch

**What goes wrong:**
The `@overload` pair for `read()` needs a TypeVar `T` bound to the `OdooModel` Protocol. Several mypy strict-mode constraints interact badly:

**8a. Overload ordering.** mypy evaluates overloads top-to-bottom and uses the first match. `str` is more specific than `type[T]` for the literal string case, but `type[T]` where `T` is bound to a Protocol may overlap with `type[str]`. The overload that takes `type[T]` must come *before* the `str` overload if `type[T]` is more specific, or mypy will report an "overloaded function signatures overlap" error. Test with mypy's `--strict` and both call shapes.

**8b. TypeVar variance.** A TypeVar bound to a Protocol in a `type[T]` parameter position is covariant in the caller context. If the return type is `list[T]`, mypy will flag this as needing a `TypeVar` with no bound (or a bounded covariant TypeVar in a Generic class). The simplest correct pattern: `T = TypeVar("T", bound=OdooModel)` where `OdooModel` is defined as a Protocol with `__odoo_model__: ClassVar[str]`.

**8c. The duck-typed branch.** The implementation body (not the overload signatures) handles both the `str` and `type[T]` cases. mypy sees the implementation signature — which must accept both — as something like `model: str | type[OdooModel]`. The body then narrows: `if isinstance(model, str)` → raw path, else → typed path. mypy needs to see a clean narrowing. `isinstance(model, str)` narrows correctly. The else branch has `model: type[OdooModel]` which mypy can use to type-check the `model.__odoo_model__` access.

**8d. `warn_return_any`.** The typed branch calls into pydantic's `model_validate()` which returns `OdooModel` (the TypeVar). mypy may infer `Any` from the pydantic return type (because pydantic uses a `__class_getitem__` trick that mypy sometimes loses). A `cast(list[T], pydantic_results)` may be necessary, and with `warn_return_any = true` any untyped pydantic call surface will trigger a warning.

**8e. Protocol with `ClassVar`.** `OdooModel` Protocol needs `__odoo_model__: ClassVar[str]`. A Protocol with a `ClassVar` member is valid in Python 3.11+ but mypy has historically had edge cases with `ClassVar` in Protocols. Test this explicitly.

**How to avoid:**
- Write the `@overload` signatures first, run mypy on them alone (no implementation) to verify they satisfy strict-mode overload consistency rules before writing the implementation body.
- Use `cast(list[T], ...)` at the pydantic call boundary to prevent `warn_return_any` from triggering.
- Define `OdooModel` Protocol in a dedicated `godoo.client.typed_protocol` module (under `TYPE_CHECKING` import in `client.py`) to keep mypy's resolution path clean.
- Run mypy with `--show-error-codes` — the errors from overload, TypeVar, and Protocol issues have distinct codes (`[override]`, `[type-var]`, `[misc]`).

**Warning signs:**
- mypy reports `error: Overloaded function signatures 1 and 2 overlap with incompatible return types`.
- mypy reports `error: Return type ... involves type variable with a variance that is not compatible`.
- The typed branch body passes mypy only because of `Any` propagating from pydantic — check with `reveal_type()` at the return statement.

**Phase to address:** Typed Models phase — the `@overload` design step specifically.

---

### Pitfall 9: Pyodide — httpx uses sockets; Pyodide has no sockets

**What goes wrong:**
httpx's async backend (asyncio) uses Python's `asyncio.open_connection()` which ultimately calls `socket.socket()`. Pyodide (Emscripten environment) does not support POSIX sockets. `import httpx` succeeds (httpx is pure-Python), but any actual HTTP call raises `OSError: [Errno 97] Network not reachable` or a similar emscripten-level error. There is no graceful fallback.

**Why it happens:**
"pure-Python" does not mean "browser-safe." httpx is pure Python but its async I/O paths assume POSIX sockets. Pyodide provides a JS `fetch`-backed `XMLHttpRequest`-compatible surface via `pyodide.http`, not a socket surface.

**How to avoid:**
The spike must test actual HTTP *calls*, not just imports. The test is: spin up a local HTTP server, load Pyodide (e.g., via playwright + Pyodide's CDN), call `client.search(...)`, assert a response. If this fails, the result is "httpx requires a custom `pyodide-fetch` transport adapter."

The custom transport path is: implement `class PyodideFetchTransport(httpx.AsyncBaseTransport)` that maps to `pyodide.http.pyfetch()`. This is feasible (pyodide.http.pyfetch returns an awaitable) but is a nontrivial transport implementation. Treat the spike as a go/no-go for committing to this work in v1.1.

**Warning signs:**
- The spike only tests `import godoo.client` in a Pyodide environment — that is not the spike. The spike fails if sockets are not tested.
- Assuming `anyio[trio]` or another async backend solves the problem — it does not; the socket constraint is at the OS level, not the Python async framework level.

**Phase to address:** Pyodide Spike phase — the spike exists precisely to surface this and produce a verdict (build custom transport / defer / out of scope).

---

### Pitfall 10: Pyodide CORS — Odoo must allow cross-origin JSON-RPC

**What goes wrong:**
A browser-side client making `fetch()` to an Odoo instance on a different origin (different domain, port, or scheme) is subject to CORS. Odoo's JSON-RPC endpoint (`/jsonrpc`) does not send CORS headers by default. The browser blocks the request before it reaches Odoo. `pyodide.http.pyfetch()` is subject to the same browser CORS enforcement.

This is a **deployment constraint**, not a code constraint. No amount of transport adapter work in godoo fixes it — the Odoo server must be configured.

**Why it happens:**
The spike is run against `localhost` where CORS is often irrelevant (same origin as the dev server). The failure only surfaces in real browser-to-remote-Odoo scenarios.

**How to avoid:**
- Document as a requirement in the Pyodide spike verdict: "Odoo must be configured with `--db-filter` and a reverse proxy that adds `Access-Control-Allow-Origin` for the notebook origin."
- The spike should test against an Odoo instance on a different port to simulate CORS conditions.
- Consider whether the target environments (Marimo, stlite, JupyterLite) use a same-origin proxy by default — some do.

**Warning signs:**
- Spike verdict is "it works" but was tested on `localhost:8069` from `localhost:8888` (same host, CORS applies but browsers may not enforce `localhost` → `localhost` strictly depending on the port difference).
- No mention of CORS in the spike's conclusion.

**Phase to address:** Pyodide Spike phase — the verdict document must explicitly address CORS.

---

### Pitfall 11: Pyodide event loop — `asyncio.run()` and `asyncio.get_event_loop()` do not work in the browser

**What goes wrong:**
In Pyodide, there is already a running event loop managed by the browser's event model. Calling `asyncio.run(coroutine)` raises `RuntimeError: This event loop is already running`. The pattern `await client.read(...)` only works inside an async context. In Marimo / JupyterLite / stlite, top-level `await` is supported (the notebook runtime handles it), but in a synchronous script or plain `<script>` tag it is not.

**Why it happens:**
godoo's entire public API is `async def`. This is correct for the Python async ecosystem but requires the caller environment to be async-aware. Browser notebook runtimes generally are, but the difference needs to be communicated clearly.

**How to avoid:**
- The spike should test in the exact target environment (Marimo WASM, JupyterLite) not just in a generic Pyodide test harness.
- If a sync-compatible surface is needed (e.g., for `<script>` usage), consider providing `asyncio.ensure_future()` + `await` wrappers — but this is out of scope for v1.1 and should not be designed speculatively.

**Warning signs:**
- Spike tests only via `pyodide.runPythonAsync(code)` (which handles the event loop), not from a real notebook environment.
- No note in the spike verdict about which notebook environments are supported.

**Phase to address:** Pyodide Spike phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skipping the import-isolation test | Faster implementation | Silent pydantic leakage breaks default-install users; discovered at release time | Never — this is the primary constraint of the typed layer |
| Using `model_construct()` instead of `model_validate()` for partial reads | Avoids ValidationError on partial reads | Typed instance has no runtime validation; type safety is illusory | Only if documented clearly and gated behind an explicit `validate=False` flag |
| Generating Pydantic models with all fields `Optional` | Avoids partial-read failures | All fields appear optional in IDE; the whole value of typed models is lost | Never — defeats the purpose |
| Hardcoding `pydantic>=2` without a lower bound test | Simplicity | Pydantic v1 users (still common in Odoo ecosystem) get a confusing import error | Acceptable only if the `[typed]` extra pins `pydantic>=2` explicitly |
| Skipping `git mv` and doing delete+add for the rename | Slightly simpler | Git blame and `git log --follow` break on all files in the package | Never — use `git mv packages/godoo packages/godoo-client` |
| Pyodide spike using only `import` tests | Fast spike | Does not answer the actual question (do HTTP calls work?) | Never for a spike that is the go/no-go decision |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Pydantic v2 `model_validate()` with Odoo wire data | Pass raw dict directly; pydantic rejects `False` for `str` fields | Pre-process with `wire_transform()` before `model_validate()`, or use custom `@field_validator(mode="before")` per ttype group |
| Odoo `many2one` read result | Treat `[1234, "Name"]` as a list and validate against `list[int]` | Define a custom Pydantic type `M2ORef` that accepts both `False` and `[int, str]` list shapes |
| Pydantic `model_json_schema()` on generated models | Schema includes `Literal[False]` unions; OpenAPI/JSON Schema tools reject `Literal[False]` | Document this; generated models are for internal godoo use, not for API schema export |
| uv workspace `godoo-client` dep in other packages | `packages/godoo-introspection/pyproject.toml` declares `godoo-client>=0.1.0`; after rename the workspace source must still resolve | `[tool.uv.sources] godoo-client = { workspace = true }` in root `pyproject.toml` ties the workspace name to the dist name — verify this still resolves after the dir rename |
| Pyodide `pyodide.http.pyfetch()` | Assumes it mirrors `httpx`'s interface | It does not — `pyfetch` returns a `pyodide.http.FetchResponse`, not an `httpx.Response`; the custom transport must map between the two |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching all model fields when a model class is passed | N×100 fields returned when caller only needs 5; slow queries on large Odoo instances | Provide a field-list override, or let the model class expose a `__fields_to_fetch__` class variable that defaults to the full field list | Noticeable at models with binary/text fields (e.g., `ir.attachment`) |
| Running codegen against a live instance on every test | Integration test suite takes 5 minutes generating models before the first assertion | Generate models once into a fixture directory; check them into the test fixtures; only re-generate in dedicated integration tests | From the first integration test run |
| `model_validate()` per record in Python loop | Pydantic validation is fast but not free; validating 10k records in a loop is measurable | Validate in batch using `TypeAdapter(list[T]).validate_python(records)` | At >1k records per call |

---

## "Looks Done But Isn't" Checklist

- [ ] **Optional-extra isolation:** `python -c "import godoo.client"` in a pydantic-free venv raises no `ImportError`. Not just "it doesn't import pydantic" — pydantic must not be installed at all.
- [ ] **Namespace package integrity:** `python -c "import godoo; assert godoo.__file__ is None"` passes after rename.
- [ ] **mypy path after rename:** `uv run mypy packages/godoo-client/src ...` (new path) invoked in CI — the old path silently passes mypy because it skips a missing directory.
- [ ] **Overload completeness:** both call shapes (`read("res.partner", [1])` and `read(ResPartner, [1])`) type-check correctly under mypy strict AND pyright — test with both type checkers if possible.
- [ ] **Wire transform coverage:** every ttype group has a unit test with `False` as the wire value — `char`, `integer`, `float`, `many2one`, `date`, `datetime`, `selection`, `one2many`.
- [ ] **Semantic-release path:** `version_toml` in root `pyproject.toml` points at `packages/godoo-client/pyproject.toml` (not `packages/godoo/pyproject.toml`) — else semantic-release will fail to bump the version on the next release.
- [ ] **Pyodide spike verdict is documented:** the spike produces a written verdict (`SEED-001` status updated, or a spike result committed) — not just "we tried it."
- [ ] **`[typed]` extra declared:** `packages/godoo-client/pyproject.toml` has `[project.optional-dependencies] typed = ["pydantic>=2"]` — without this, `pip install godoo-client[typed]` fails.

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Pydantic top-level import leakage (P1, P2) | Typed Models — implementation | Import-isolation test in pydantic-free venv in CI |
| `isinstance(BaseModel)` dispatch check (P3) | Typed Models — design review | Code review gate: no `issubclass`/`isinstance` with `BaseModel` in `client.py` |
| Partial-read validation failure (P4) | Typed Models — design review | Explicit decision logged; overload signature encodes the decision |
| Wire-format edge cases (P5) | Typed Models — transform layer | Unit test table: all ttype × {normal, `False`, edge} inputs |
| uv-workspace + hatchling rename breakage (P6) | Rename phase | Post-rename smoke: `uv sync && uv run python -c "import godoo.client"` + wheel build check |
| PEP 420 namespace collision (P7) | Rename phase | `assert godoo.__file__ is None` test in CI |
| mypy `@overload` + TypeVar friction (P8) | Typed Models — overload implementation | mypy strict + pyright clean on `client.py` |
| Pyodide — no sockets (P9) | Pyodide Spike | Spike test makes an actual HTTP call, not just an import |
| Pyodide — CORS (P10) | Pyodide Spike | Spike verdict explicitly addresses CORS requirements |
| Pyodide — event loop (P11) | Pyodide Spike | Spike tested in real Marimo/JupyterLite environment |

---

*Pitfalls research for: godoo-py v1.1 (Rename + Typed Models + Pyodide Spike)*
*Researched: 2026-05-27*
