# Technology Stack — godoo-py v1.1 New Features

**Project:** godoo-py
**Researched:** 2026-05-27
**Scope:** NEW dependencies only. Existing stack (Python 3.14, httpx>=0.27, hatchling,
ruff, mypy --strict, pytest-asyncio) is fixed and not re-evaluated here.

---

## Stack Additions Required for v1.1

Three capabilities drive three distinct dependency decisions:

| Capability | New Dep? | Where It Lives | Note |
|------------|----------|----------------|------|
| (A) packages/godoo rename | None | build/packaging | purely mechanical |
| (B) Typed models + codegen CLI | `pydantic>=2.13` | `godoo-client[typed]` optional extra + `godoo-introspection` runtime dep | core default install stays httpx-only |
| (B) CLI surface for the generator | `typer>=0.26` | `godoo-introspection` runtime dep | declared alongside pydantic in introspection's deps |
| (C) Pyodide spike | `pyodide-httpx>=0.2` (spike-only) | NOT added to any package | runtime browser concern, not a library dep |

---

## 1. Pydantic — Optional Extra for Typed Transform Layer

### Recommendation: pydantic>=2.13, as `godoo[typed]` optional extra

**Current version:** 2.13.4 (released 2026-05-06). Supports Python >=3.9 through 3.14 (CPython and PyPy). Confidence: HIGH (verified via PyPI).

**What it gives the generated-model + transform layer:**

Pydantic v2 is the right tool specifically because of Odoo's wire-format quirks. These
transforms are declarative in Pydantic and require hand-written `__post_init__` in
dataclasses:

- `False` → `None` coercion for empty/unset fields (Odoo returns `False`, not `None`)
- many2one `[id, "Display Name"]` → typed `Ref[Model]` via `@field_validator(mode="before")`
- date/datetime strings → `datetime.date` / `datetime.datetime` via Pydantic's built-in coercers
- selection fields → `Literal[...]` (already emitted by CodeGenerator; Pydantic validates at runtime)
- `model_validate(raw_dict)` as the single parse entry point — one call, all transforms applied

The generated models use `model_construct()` for partial reads (fields subset) to skip
validation on missing fields — avoids strict-validation failures when caller passes
`fields=[...]`.

**Why NOT dataclasses for this layer:**
The core convention (dataclasses everywhere) holds for core types. Generated Pydantic
models are the deliberate exception: the value is bidirectional declarative transforms,
which Pydantic does in ~5 lines of annotation vs. hand-written `__post_init__` per
model per field. Static codegen + runtime validation are not mutually exclusive —
Pydantic serves both.

**How optional-dependency declaration works in hatchling/PEP 621:**

```toml
# packages/godoo/pyproject.toml
[project]
name = "godoo-client"
dependencies = ["httpx>=0.27"]           # unchanged — sole runtime dep

[project.optional-dependencies]
typed = ["pydantic>=2.13"]
```

Users install with: `pip install godoo-client[typed]`

Core default install (`pip install godoo-client`) remains httpx-only. PEP 621
`[project.optional-dependencies]` is build-backend-agnostic; hatchling reads it
natively — no plugin needed.

**Dispatch boundary (how core avoids importing pydantic unless typed path runs):**

```python
# client.py — NO top-level pydantic import, ever
from __future__ import annotations
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from pydantic import BaseModel  # type-checker only, zero runtime cost

class OdooClient:
    @overload
    async def read(self, model: str, ids, *, fields=...) -> list[dict]: ...
    @overload
    async def read(self, model: type[T], ids, *, fields=...) -> list[T]: ...

    async def read(self, model, ids, *, fields=None):
        if hasattr(model, "__odoo_model__"):   # duck-type, not isinstance(BaseModel)
            # import pydantic only here, at runtime, only when typed path is taken
            raw = await self._raw_read(model.__odoo_model__, ids, fields=fields)
            return [model.model_validate(r) for r in raw]
        return await self._raw_read(model, ids, fields=fields)
```

`isinstance(x, BaseModel)` is explicitly banned — it would force a pydantic import at
module load time on every install.

**mypy --strict compatibility:**
Pydantic v2 ships its own `py.typed` marker and full type stubs. `model_validate`,
`model_construct`, `field_validator`, `model_validator` are all fully typed. The
`@overload` pair on `read()` is the mypy surface; the typed path's generic `T` is
constrained via a `Protocol` with `__odoo_model__: str`.

---

## 2. CLI Framework for the Introspection Generator

### Recommendation: typer>=0.26, in godoo-introspection (not in core)

**Current versions:** typer 0.26.2 (released 2026-05-27), click 8.4.1 (released
2026-05-22). Confidence: HIGH (verified via PyPI).

**Decision: typer in godoo-introspection runtime dependencies.**

Rationale:

1. **The CLI dep never touches core.** `godoo-introspection` is a separate package
   (`pyproject.toml` is separate, distributed separately). Adding typer to
   `godoo-introspection`'s `[project.dependencies]` has zero impact on
   `godoo-client`'s httpx-only constraint.

2. **typer over argparse.** argparse is stdlib (zero extra install), but:
   - The generator CLI will need subcommands (`generate`, `inspect`, etc.) and typed
     arg validation — argparse's API grows verbose fast at this scope.
   - The "library, not an app" ethos applies to `godoo-client`. `godoo-introspection`
     IS delivering a developer tool (the generator); ergonomic CLI is a feature, not
     overhead.
   - typer derives CLI from type hints — consistent with the "type-first" posture of
     the whole codebase, and compatible with mypy --strict.

3. **typer over click directly.** As of typer 0.26.0, Click is vendored inside typer
   (no longer an external dependency). typer's API is type-hint-native, matching the
   project's coding style. The developer-facing gain over raw click is meaningful at
   this complexity level.

4. **typer's own deps (rich, shellingham) are acceptable** for a developer tool package.
   rich gives free `--help` formatting. These deps never reach `godoo-client`.

**Where it goes:**

```toml
# packages/godoo-introspection/pyproject.toml
[project]
name = "godoo-introspection"
dependencies = [
    "godoo-client>=0.2",
    "typer>=0.26",
    "pydantic>=2.13",    # the generator emits Pydantic model code; pydantic IS a runtime dep here
                         # (code generation + validation of the schema response)
]

[project.scripts]
godoo-introspect = "godoo.introspection.cli:app"
```

The `godoo-introspect` script entry point installs a terminal command when the package
is installed. Users run: `godoo-introspect generate --url ... --output ./models/`.

**argparse is a valid fallback** if the CLI stays extremely simple (one command, 3-4
args). Re-evaluate if scope is confirmed to be a single `generate` command with no
subcommands — argparse handles that without the extra dep. The recommendation above
assumes at minimum a `generate` + `inspect` subcommand shape.

---

## 3. Pyodide / Browser Spike — Constraints and Facts

### Verdict: httpx IS in Pyodide's bundled packages, but godoo-py needs a Python-version compatibility path before browser use is viable

**Confidence:** HIGH on the technical facts; MEDIUM on the spike scope estimate.

**Key facts (verified via Pyodide changelog and source):**

| Fact | Detail | Source |
|------|--------|--------|
| Pyodide current stable | 0.29.4 (released 2026-05-07) | Pyodide releases |
| Python version bundled | CPython 3.13.2 | Pyodide 0.29.x changelog |
| Python 3.14 in Pyodide | Not yet; PEP 776/783 approved by CPython SC (tier 3 target starting 3.14); no release date | Pyodide roadmap |
| httpx in Pyodide bundled packages | Yes — httpx 0.28.1 added in Pyodide 0.27.x; debug-print fix in 0.29.x | Pyodide changelog (direct) |
| httpx patching mechanism | Cloudflare's `httpx_patch.py` overrides `AsyncClient._send_single_request` with JS Fetch API via Pyodide FFI | cloudflare/pyodide source |
| pyodide-httpx PyPI package | Standalone 0.2.0 (2025-02-16); MPL 2.0; provides `patch_httpx()` call for micropip installs | PyPI |
| Pyodide's bundled httpx is pre-patched | YES — Pyodide's package build applies the patch to its bundled httpx binary; `pyodide-httpx` PyPI is for micropip users outside bundled packages | Pyodide discussion #4999 |
| sockets/threading/multiprocessing | Removed or non-functional in WASM; `socket`, `threading`, `multiprocessing` are present but raise `NotImplementedError` | Pyodide wasm-constraints docs |
| ssl module | Stubbed — methods depending on OpenSSL raise `NotImplementedError`; HTTPS goes via JS Fetch (browser handles TLS) | Pyodide wasm-constraints docs |
| CORS | Odoo must serve `Access-Control-Allow-Origin` headers; browser blocks cross-origin JSON-RPC without them | Pyodide wasm-constraints docs |

**The blocking constraint for godoo-py specifically:**

godoo-py requires Python >=3.14. Pyodide 0.29.x ships CPython 3.13.2. There is no
Pyodide release with Python 3.14 yet (PEP 776 approved, no ship date). This means:

- A Python 3.14-only build of godoo CANNOT be installed in Pyodide today.
- The spike's first question must be: **does the floor drop to >=3.12 for the browser
  build, or do we wait for Pyodide + Python 3.14?**

If the decision is to target current Pyodide (3.13), godoo would need a compat branch or
separate wheel with `requires-python = ">=3.12"`. If we wait for Pyodide + 3.14, the
spike is a future milestone, not v1.1.

**httpx transport story (if/when Python-version gap is resolved):**

godoo's `JsonRpcTransport` uses `httpx.AsyncClient` exclusively. In Pyodide's bundled
environment, httpx is already patched to use JS Fetch — no code change in godoo needed.
For micropip-installed godoo (outside Pyodide bundle), the user would need
`pyodide-httpx` and call `patch_httpx()` before instantiating `OdooClient`. This could
be wrapped in a `godoo.pyodide` compat module (thin, optional).

**testcontainers** is Docker-bound and explicitly out of scope for any browser target.

**godoo-introspection** could work in browser if the Python version gap is bridged — it
only needs httpx (for schema queries) and pydantic (for validation). The codegen output
would be written to a virtual filesystem (emscripten's MEMFS), not the user's disk.
Whether that's useful is a design question for the spike.

**No packages to add to any pyproject.toml for the spike.** The spike is an experiment;
deps land if/when browser support becomes a milestone deliverable.

---

## Version Table

| Library | Verified Version | Constraint to Use | Where |
|---------|-----------------|-------------------|-------|
| pydantic | 2.13.4 | `>=2.13` | `godoo-client[typed]` optional extra |
| typer | 0.26.2 | `>=0.26` | `godoo-introspection` runtime dep |
| click | 8.4.1 (vendored in typer) | via typer | transitive only |
| pyodide-httpx | 0.2.0 | N/A for v1.1 | spike-only, not in any package dep |

---

## What NOT to Add

| What | Why Not |
|------|---------|
| pydantic in `[project.dependencies]` (unconditional) | Breaks the "httpx-only default install" constraint; must stay optional |
| pydantic in `godoo-introspection` main deps | The generator emits Pydantic *code* — it does not need pydantic at runtime to emit text. Keep it optional unless the introspection package also does runtime validation (confirm during scoping). |
| click as a direct dep | Vendored inside typer 0.26+; adding click separately creates a double-dep |
| pyodide-httpx in any package dep | It's a browser-runtime concern; library users on CPython would install an irrelevant dep |
| aiohttp or alternative HTTP client | httpx is established, works in Pyodide (patched), and is the sole transport layer — no reason to add complexity |
| pydantic-settings | Not needed; config_from_env uses stdlib os.environ directly |

---

## Integration Notes

### (A) Workspace rename — no new deps

`packages/godoo` → `packages/godoo-client` is a directory rename + `pyproject.toml`
`[tool.hatch.build.targets.wheel]` path update. The `godoo.*` import namespace (PEP
420 implicit namespace package) is unaffected. No dependency changes.

### (B) Typed models — two-package integration

`godoo-client` gains:
- `[project.optional-dependencies] typed = ["pydantic>=2.13"]`
- `@overload` pair on `read()`, `search_read()` (and potentially `write()` return paths)
- A `Protocol` with `__odoo_model__: str` for mypy to constrain `type[T]`
- Duck-type dispatch (`hasattr(model, "__odoo_model__")`) — never `isinstance(BaseModel)`
- Pydantic imported only inside the typed dispatch branch at runtime

`godoo-introspection` gains:
- `typer>=0.26` in `[project.dependencies]`
- `[project.scripts] godoo-introspect = "godoo.introspection.cli:app"`
- The CLI reads the live schema via `OdooClient.fields_get()` (existing), passes it to
  `CodeGenerator` (existing), and writes Pydantic model source to `--output` path
- The CodeGenerator output changes from TypedDict to BaseModel subclasses (or supports
  both via `--format` flag)

### (C) Pyodide spike — no package changes in v1.1

The spike is an investigation, not a feature. Output is a technical decision:
- YES with no changes → godoo-py works in Pyodide once the 3.14 floor is met
- YES with thin compat layer → add a `godoo.pyodide` module (no new package dep)
- NO / wait → defer to a future milestone after Pyodide ships Python 3.14

Nothing lands in a pyproject.toml until the spike reaches a conclusion.

---

## Sources

- Pydantic 2.13.4 on PyPI: https://pypi.org/project/pydantic/
- Typer 0.26.2 on PyPI: https://pypi.org/project/typer/
- Click 8.4.1 on PyPI: https://pypi.org/project/click/
- pyodide-httpx 0.2.0 on PyPI: https://pypi.org/project/pyodide-httpx/
- Pyodide wasm-constraints docs: https://pyodide.org/en/stable/usage/wasm-constraints.html
- Pyodide changelog (httpx 0.28.1 added, Python 3.13.2 upgrade): https://pyodide.org/en/stable/project/changelog.html
- Cloudflare httpx_patch.py (Fetch API transport): https://github.com/cloudflare/pyodide/blob/main/packages/httpx/httpx_patch.py
- Pyodide discussion #4999 (pyodide-httpx rationale, bundled vs. micropip): https://github.com/pyodide/pyodide/discussions/4999
- PEP 621 optional-dependencies reference: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Hatch dependency config: https://hatch.pypa.io/dev/config/dependency/
