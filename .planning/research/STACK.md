# Stack Research

**Domain:** Async Python SDK — Odoo JSON-RPC (introspection codegen, state-manager, moduleX layers)
**Researched:** 2026-04-10
**Confidence:** HIGH (locked choices) / MEDIUM (new-layer deps)

---

## Part 1 — Locked Choice Validation

Are the existing decisions still correct in April 2026?

| Choice | Verdict | Notes |
|--------|---------|-------|
| Python 3.14 | VALID | Python 3.14 is the current stable release. asyncio gained 10–20% single-threaded perf improvements and lock-free data structures in 3.14. mypy 1.20.0 (March 2026) fully supports 3.14 including t-strings and free-threading wheels. |
| asyncio async-only | VALID | asyncio remains the idiomatic Python I/O model. Python 3.14 docs still recommend `async/await` + `asyncio.run()` for I/O-bound work. No compelling reason to layer in trio or anyio for this scope. |
| uv workspace + lockfile | VALID | uv is widely adopted as the gold-standard Python package manager in 2026. uv workspaces with a single `uv.lock` are the recommended multi-package pattern. Only consideration: `uv init` now defaults to `uv_build` (uv's own build backend, available since July 2025). |
| hatchling build backend | VALID WITH FLAG | Still works. `uv_build` is the new default for greenfield uv projects, but hatchling is the right choice here because semantic-release needs to write version strings back into `pyproject.toml` — hatchling supports this via `[tool.hatch.build]` while `uv_build` does not yet provide a stable `hatch-vcs`-equivalent. No migration needed. |
| ruff 0.8+ (now at 0.15.7 installed) | VALID | ruff is the undisputed Python linter/formatter in 2026. Rules set `[E, F, W, I, UP, B, SIM, TCH, RUF]` is still appropriate. No changes needed. |
| mypy --strict | VALID | mypy 1.20.0 released March 2026. Strict mode is correct. Note: mypy 2.0 will enable `--local-partial-types` by default — not a breaking change for godoo since we already use explicit annotations everywhere. |
| pytest-asyncio | NEEDS UPGRADE | Current spec is `>=0.24`. Latest stable is **1.3.0** (November 2025); pre-release 1.4.0a0 exists. **1.x is a breaking change from 0.x**: the deprecated `event_loop` fixture was removed; session-scoped event loops are now configured via `asyncio_default_fixture_loop_scope = "session"` in `pytest.ini_options` (which godoo already uses). The existing config should be compatible with 1.x — but the version pin should be updated to `>=1.0` and tested. Flag for the hardening phase. |
| respx 0.22+ | VALID | respx is still the right httpx mock library. No issues found. |
| httpx 0.27+ (installed 0.28.1) | VALID | httpx includes `py.typed` (confirmed in source: non-empty marker file exists), is fully inline-annotated, and works with mypy --strict. Latest is 0.28.1 (December 2024). No upgrade concern. |
| dataclasses (not Pydantic) | VALID | Correct choice for an SDK layer. Pydantic adds runtime validation overhead and a heavy dependency. Dataclasses are lightweight, stdlib, and mypy-native. |
| testcontainers-python | VALID | testcontainers 4.x+ is the correct package. The sync-API wrapping via `asyncio.to_thread()` convention is still the right approach — the library has not added async support. |
| python-semantic-release 9+ | VALID | Still the right tool for multi-package conventional commit release management on PyPI. |

**Summary of locked-choice concerns:**
1. **pytest-asyncio**: upgrade version pin from `>=0.24` to `>=1.0` and verify session-scope config still works.
2. **hatchling vs uv_build**: Do not migrate. hatchling is the right call given semantic-release's version-write requirements.

---

## Part 2 — New Layer Dependencies

### godoo-introspection (codegen engine)

The introspection package needs to: (a) call the Odoo RPC to get model/field metadata, (b) generate valid typed Python source files (dataclasses), and (c) optionally provide a CLI entrypoint.

#### Code Generation: Jinja2 (not libcst)

| Technology | Version | Purpose | Async-compatible? | mypy --strict? |
|------------|---------|---------|-------------------|----------------|
| **Jinja2** | **3.1.x** | Template-driven `.py` file generation | N/A (codegen is offline, not async) | YES — Jinja2 is fully typed, `py.typed` present |
| libcst | 1.8.6 | CST manipulation/transformation of existing Python files | N/A | YES — classified as Typed, supports 3.14 |

**Use Jinja2, not libcst.** Rationale: introspection is generating Python files from scratch (Odoo schema → dataclass files). libcst is a Concrete Syntax Tree library designed for _modifying existing Python source_ while preserving formatting — that is the wrong primitive for emission. Jinja2 templates are the standard pattern for code generators in the Python ecosystem (protobuf, datamodel-code-generator, OpenAPI generators all use Jinja2 internally). The generated output will be re-formatted by ruff anyway, so CST fidelity is irrelevant.

libcst is the right choice only if godoo-introspection later needs to _patch_ existing generated packages incrementally (e.g., add a field to a file that was already generated). Keep it in consideration for that future scenario.

**Do not use datamodel-code-generator** as a dependency. It targets OpenAPI/JSON Schema/GraphQL inputs and generates Pydantic by default. Odoo's schema is delivered via RPC as Python dicts — there is no OpenAPI spec to feed it. Custom Jinja2 templates are simpler, more controllable, and eliminate a heavy transitive dependency.

#### CLI entrypoint: Typer

| Technology | Version | Purpose | Async-compatible? | mypy --strict? |
|------------|---------|---------|-------------------|----------------|
| **Typer** | **0.24.1** | CLI for `godoo-introspection generate` and `godoo` top-level commands | Partial — no native `async def` support; use `asyncio.run()` wrapper | YES — classified Typed, supports Python 3.14 |

**Use Typer with `asyncio.run()` wrappers.** Rationale: Typer gives type-hint-driven CLI with zero decorator boilerplate, mypy strict compatibility, and Python 3.14 support. Its missing native `async def` support is a non-issue: CLI commands are sync entry points that call `asyncio.run(async_main(...))` — a one-liner pattern that is idiomatic and already recommended in the Typer community. Click is lower-level and verbose; argparse is stdlib but produces untyped spaghetti. Typer is the correct default for a solo-maintainer typed SDK CLI.

**Do not use `async-typer`** (PyPI package, released August 2025). It's an unofficial thin wrapper with minimal maintenance — adding a dependency on a ~200-star community package when `asyncio.run()` costs one line is unjustifiable.

---

### godoo-state-manager (declarative plan/apply/diff/drift)

The state-manager needs: HTML sanitization (for HTML-marked field content), Markdown-to-HTML rendering (for Markdown-marked content), and CSS inlining (for HTML email bodies going into Odoo `mail.template`).

#### HTML Sanitization: nh3

| Technology | Version | Purpose | Async-compatible? | mypy --strict? |
|------------|---------|---------|-------------------|----------------|
| **nh3** | **0.3.4** | Sanitize HTML content before writing to Odoo fields | YES — pure function, no I/O | YES — ships `.pyi` stub file (confirmed in GitHub repo) |
| bleach | 6.x | HTML sanitization | N/A | Partial (unmaintained upstream) |

**Use nh3, not bleach.** Bleach was deprecated in January 2023 when html5lib (its underlying parser) went unmaintained. nh3 is the direct replacement: Rust-backed (Ammonia crate), ~20x faster than bleach, API-compatible, ships `.pyi` stubs, and released 0.3.4 on March 25, 2026 with CPython 3.14 wheel support. The `nh3.clean(html, tags=..., attributes=...)` API mirrors bleach's `clean()`.

#### Markdown Rendering: markdown-it-py

| Technology | Version | Purpose | Async-compatible? | mypy --strict? |
|------------|---------|---------|-------------------|----------------|
| **markdown-it-py** | **4.0.0** | Render Markdown DSL markers to HTML | YES — pure function, no I/O | MEDIUM — no explicit `py.typed` noted on PyPI; verify with `mypy.overrides` if needed |
| mistune | 3.x | Markdown parsing | YES | MEDIUM |

**Use markdown-it-py 4.0.0, not mistune.** Rationale: markdown-it-py is CommonMark compliant, has a clean plugin API (`.use(plugin)`), is a Google Assured Open Source Software member, actively maintained (latest 4.0.0 in August 2025), and is the go-to recommendation from the Python packaging community. Mistune is faster but not CommonMark compliant — edge cases in nested inline parsing can produce incorrect HTML. For state-manager output going into Odoo HTML fields, correctness beats raw speed. 

**Flag:** markdown-it-py 4.0.0 declares `Python >=3.10` but its classifier list stops at 3.13. Run mypy against it before committing — if it lacks inline types, add an `[[tool.mypy.overrides]]` ignore block (same pattern used for testcontainers). This is LOW risk: the library is pure Python and widely used with mypy.

#### CSS Inlining: css-inline

| Technology | Version | Purpose | Async-compatible? | mypy --strict? |
|------------|---------|---------|-------------------|----------------|
| **css-inline** | **0.20.2** | Inline CSS into HTML for Odoo mail.template bodies | YES — pure function, no I/O | MEDIUM — no `py.typed` noted; add mypy override |
| premailer | 3.x | CSS inlining | YES | NO — lxml-based, poor type coverage |

**Use css-inline 0.20.2, not premailer.** css-inline is Rust-backed (Mozilla Servo CSS parser), supports Python 3.9–3.14 including PyPy 3.11, processes HTML in hundreds of microseconds, and supports `inline_many()` for concurrent batch processing at the Rust layer. Latest release is April 2, 2026. Premailer has lxml as a hard dependency (complex C build, poor Windows support), downloads external stylesheets by default (security risk for offline SDK use), and has weaker type coverage.

**Flag:** css-inline does not advertise a `py.typed` marker. Add `[[tool.mypy.overrides]] module = ["css_inline"] ignore_missing_imports = true` alongside the existing testcontainers override. The API surface is small: `css_inline.inline(html)` and `css_inline.inline_fragment(fragment, css)`.

---

### godoo-moduleX (live x-module builder)

moduleX declares models, x-fields, views, menus, ACLs, and record rules, then pushes them into Odoo via RPC. The HTTP transport is already httpx. No new runtime dependencies needed beyond what is already in godoo core.

**No additional runtime deps.** moduleX operates purely through the existing JSON-RPC transport, constructing Odoo domain syntax and field dicts in Python. All type safety comes from generated introspection types.

---

## Recommended Stack — New Layer Summary

### Core Technologies (locked, validated)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.14 | All packages | Current stable; asyncio perf gains in 3.14 |
| asyncio | stdlib | Async I/O | Idiomatic; 10–20% perf improvement in 3.14 |
| httpx | 0.28.1 | JSON-RPC HTTP transport | py.typed, async-first, already in-use |
| uv workspace | 0.4.0+ | Package management | Industry standard 2026 |
| hatchling | 1.x | Build backend | Required for semantic-release version write |
| ruff | 0.15.x | Lint + format | Industry standard, ruff format replaces black |
| mypy 1.20+ | --strict | Type checking | Latest release, full Python 3.14 support |
| pytest + pytest-asyncio 1.x | 9.x / 1.x | Testing | Note: upgrade pin from 0.24 to >=1.0 |
| respx | 0.22+ | HTTP mock | httpx-native mock library |
| testcontainers | 4+ | Integration test containers | Wrap sync API in asyncio.to_thread() |

### New Runtime Dependencies

| Library | Version | Package | Purpose | Async-safe? | mypy --strict? |
|---------|---------|---------|---------|-------------|----------------|
| **Jinja2** | **3.1.x** | godoo-introspection | Generate dataclass `.py` files from Odoo schema | N/A | YES |
| **Typer** | **0.24.1** | godoo-introspection, optional top-level | CLI entrypoints (sync wrappers over async_main) | Via asyncio.run() | YES |
| **nh3** | **0.3.4** | godoo-state-manager | HTML sanitization (Rust-backed, bleach replacement) | YES | YES (.pyi stubs) |
| **markdown-it-py** | **4.0.0** | godoo-state-manager | Markdown-to-HTML rendering, CommonMark compliant | YES | MEDIUM (add override if needed) |
| **css-inline** | **0.20.2** | godoo-state-manager | CSS inlining for Odoo mail.template (Rust-backed) | YES | MEDIUM (add override) |

### Installation

```bash
# godoo-introspection
uv add jinja2 typer --package godoo-introspection

# godoo-state-manager
uv add nh3 markdown-it-py css-inline --package godoo-state-manager

# Upgrade pytest-asyncio pin in workspace pyproject.toml
# Change: "pytest-asyncio>=0.24" → "pytest-asyncio>=1.0"
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Jinja2 (codegen) | libcst | libcst is for modifying existing Python source trees, not emission from scratch. Wrong primitive. |
| Jinja2 (codegen) | datamodel-code-generator | Requires OpenAPI/JSON Schema input; Odoo schema is RPC dicts; adds heavy Pydantic transitive dep |
| Jinja2 (codegen) | ast.unparse() | stdlib ast can emit code, but building an AST programmatically is verbose; Jinja2 templates are readable and maintainable |
| Typer | Click | More verbose; no native type-hint-driven parameter inference; requires manual `@click.option` decorators |
| Typer | argparse | stdlib but produces untyped code; poor DX for solo maintainers |
| nh3 | bleach | Deprecated since January 2023; html5lib unmaintained; 20x slower |
| markdown-it-py | mistune | Not CommonMark compliant; edge cases in nested inline parsing produce wrong HTML |
| markdown-it-py | Python-Markdown | No inline rendering API; extension system is older and less clean |
| css-inline | premailer | lxml hard dep (C build, bad Windows support); downloads external stylesheets by default; poor type coverage |
| css-inline | inlinestyler | Unmaintained (last release 2019) |
| pytest-asyncio 1.x | pytest-asyncio 0.24 | 0.24 is superseded; 1.x removes deprecated event_loop fixture; session-scoped loop config already matches |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `bleach` | Deprecated January 2023; html5lib unmaintained | `nh3` |
| `premailer` | lxml dep (C build complexity); network I/O by default; weak types | `css-inline` |
| `inlinestyler` | Unmaintained since 2019 | `css-inline` |
| `async-typer` | Unofficial, minimal maintenance; `asyncio.run()` wrapper is a one-liner | Typer + `asyncio.run()` |
| `datamodel-code-generator` | Expects OpenAPI/JSON Schema; emits Pydantic; wrong input format for Odoo RPC introspection | Custom Jinja2 templates |
| `libcst` (for initial codegen) | Designed for patching existing source, not fresh emission | Jinja2 (initial emit), libcst (future incremental patching) |
| `aiohttp` | No `py.typed`, weaker type story; httpx already in-use and fully typed | httpx (already in-use) |
| `Pydantic` | Runtime validation overhead; project convention is dataclasses; adds 10MB transitive dep | stdlib dataclasses |

---

## Version Compatibility Notes

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| pytest-asyncio >=1.0 | pytest >=8.0 | 1.x requires pytest 8+; godoo already specifies pytest 8+ |
| mypy 1.20 | Python 3.14 | Full 3.14 support including t-strings confirmed in mypy 1.20.0 release |
| markdown-it-py 4.0.0 | Python >=3.10 | Classifiers stop at 3.13; no 3.14 wheel listed — test with `uv run mypy`; add override if import errors |
| css-inline 0.20.2 | Python 3.9–3.14 | Explicit 3.14 classifier present; Rust wheel available |
| nh3 0.3.4 | Python >=3.8, CPython 3.14 wheel | CPython 3.14t (free-threading) wheel also available |
| Typer 0.24.1 | Python >=3.10 | Python 3.14 classifier present |
| Jinja2 3.1.x | Python >=3.10 | Fully typed, markupsafe dep is py.typed too |

---

## mypy Override Block (add to workspace pyproject.toml)

The following libraries lack `py.typed` but are safe to ignore-import:

```toml
[[tool.mypy.overrides]]
module = ["testcontainers.*"]
ignore_missing_imports = true

# Add when introducing state-manager deps:
[[tool.mypy.overrides]]
module = ["css_inline"]
ignore_missing_imports = true

# Add only if markdown-it-py triggers import errors (likely not needed):
# [[tool.mypy.overrides]]
# module = ["markdown_it.*"]
# ignore_missing_imports = true
```

---

## Sources

- [httpx py.typed confirmed](https://github.com/encode/httpx/blob/master/httpx/py.typed) — empty marker file present; `py.typed` = fully typed
- [nh3 PyPI 0.3.4](https://pypi.org/project/nh3/) — CPython 3.14 wheel, released 2026-03-25
- [nh3 GitHub](https://github.com/messense/nh3) — `.pyi` stub file confirmed in repository
- [markdown-it-py PyPI 4.0.0](https://pypi.org/project/markdown-it-py/) — Python >=3.10, Google Assured OSS, released 2025-08-11
- [css-inline PyPI 0.20.2](https://pypi.org/project/css-inline/) — Python 3.9–3.14, Rust-backed, released 2026-04-02
- [libcst PyPI 1.8.6](https://pypi.org/project/libcst/) — Typed badge, Python 3.14 wheels, released 2025-11-03
- [Typer PyPI 0.24.1](https://pypi.org/project/typer/) — Typed, Python 3.14, released 2026-02-21
- [Typer async issue #88](https://github.com/fastapi/typer/issues/88) — no native async; asyncio.run() is the accepted pattern
- [pytest-asyncio 1.3.0 changelog](https://pytest-asyncio.readthedocs.io/en/stable/reference/changelog.html) — event_loop fixture removed; session scope via ini config
- [mypy 1.20.0 release blog](https://mypy-lang.blogspot.com/2026/03/mypy-120-released.html) — Python 3.14 fully supported; strict mode unchanged
- [uv_build vs hatchling 2025](https://medium.com/@dynamicy/python-build-backends-in-2025-what-to-use-and-why-uv_build-vs-hatchling-vs-poetry-core-94dd6b92248f) — hatchling correct choice when semantic-release writes version strings (MEDIUM confidence)
- WebSearch — bleach deprecation, css-inline vs premailer, Typer vs Click comparisons

---
*Stack research for: godoo new-layer dependencies (introspection codegen, state-manager, moduleX)*
*Researched: 2026-04-10*
