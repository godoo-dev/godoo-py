# Phase 5: Directory Rename — Research

**Researched:** 2026-05-27
**Domain:** uv workspace package-directory rename + PEP 420 namespace guard
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Reference sweep scope:** Full repo grep for `packages/godoo/` (and bare `packages/godoo` not followed by `-client`/`-testcontainers`/`-introspection`/`-meta`); every hit updated — docs, READMEs, comments, configs. The 7 enumerated refs are the known minimum, not the ceiling.

**D-02 — build_command cleanup:** Remove the stale trailing `uv build --package godoo` from root `pyproject.toml` `build_command` if it is a leftover duplicate of `--package godoo-client`. Executor must read and confirm before removing.

**D-03 — PEP 420 guard test:** Add a test in `packages/godoo-client/tests/` asserting `godoo.__file__ is None`. Runs in the normal pytest unit pass.

**D-04 — Verification depth:** Local gate before push: `uv sync`, `uv run python -c "import godoo.client"`, and a wheel build. CI (ruff / mypy / pytest / build) must also pass from the new path.

### Claude's Discretion

- Exact ordering of `git mv` vs. reference-update commits.
- How work is split across plans/commits.
- Precise file/test-function name for the PEP 420 guard test (within `packages/godoo-client/tests/`).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. (OD-1/OD-2 belong to Phase 6.)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PKG-01 | Workspace directory `packages/godoo` renamed to `packages/godoo-client` via `git mv`; import namespace stays `godoo.*` (PEP 420) | `git mv` is the only blame-preserving rename; PEP 420 invariant confirmed intact — no top-level `godoo/__init__.py` exists |
| PKG-02 | All path references updated; CI stays green | Complete verified hit list below; every tool-config path catalogued with exact file:line |
| PKG-03 | CI guard test asserts `godoo.__file__ is None` (no stray `__init__.py`) | `packages/godoo/src/godoo/` confirmed to have no `__init__.py`; test can assert `godoo.__file__ is None` |

</phase_requirements>

---

## Summary

Phase 5 is a mechanical directory rename: `packages/godoo/` becomes `packages/godoo-client/`. The Python import namespace (`godoo.*`) does not change — PEP 420 namespace packages decouple the dist/directory name from the import path, and the package carries no top-level `godoo/__init__.py` (verified below). The `godoo-client` dist name and the `[tool.uv.sources]` workspace alias already exist and are authoritative; the rename makes the directory catch up.

The work splits into three atomic pieces: (1) `git mv` the directory, (2) update all hardcoded `packages/godoo/` path references in tool configs and documentation, (3) add the PEP 420 guard test. The uv.lock contains editable path entries pointing at `packages/godoo` and must be regenerated via `uv sync` after the rename.

**Primary recommendation:** One commit for the `git mv` + reference updates (they must be atomic to keep CI green on that commit), a second commit for the guard test.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Directory rename | Filesystem / git | — | `git mv` is a pure VCS operation |
| Tool-config path updates | Build / CI config | — | pyproject.toml, test.yml, mkdocs.yml are config files, not source |
| uv.lock regeneration | Dependency resolver | — | uv detects editable path change and rewrites lock entries |
| PEP 420 guard | Test suite | CI | Lives in the package's own unit tests; CI enforces on every push |

---

## Standard Stack

No new packages are installed in this phase. All tooling is already present.

| Tool | Version (current) | Role in this phase |
|------|-------------------|--------------------|
| `git mv` | — | Blame-preserving directory rename |
| `uv sync` | workspace | Regenerates uv.lock after path change |
| `uv build --package godoo-client` | workspace | Wheel build smoke-test (D-04) |
| `pytest` | >=8 | Runs guard test (D-03) |
| `mypy` | >=1.13 | Validates new path in CI |

---

## Package Legitimacy Audit

No packages are installed in this phase. Section not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
packages/godoo/          (before)
  src/godoo/             <- namespace dir, no __init__.py
    client/              <- dist wheel target (only-include = src/godoo/client)
  tests/
  pyproject.toml         (project.name = "godoo-client")

         git mv
            |
            v

packages/godoo-client/   (after)
  src/godoo/             <- namespace dir, still no __init__.py
    client/              <- wheel target unchanged
  tests/
  pyproject.toml         (no content changes needed)
```

The `godoo.*` import namespace is unaffected because `src/godoo/` has no `__init__.py` — Python resolves it as a namespace package regardless of the containing directory name.

### Recommended Project Structure (after rename)

```
packages/
├── godoo-client/        # renamed from godoo/
│   ├── src/godoo/       # namespace root — no __init__.py (PEP 420)
│   │   └── client/      # wheel target
│   ├── tests/
│   │   └── test_namespace.py   # new: PEP 420 guard (D-03)
│   └── pyproject.toml
├── godoo-testcontainers/
├── godoo-introspection/
└── godoo-meta/
```

---

## Verified Reference Hit List (D-01)

The full grep of `packages/godoo` (excluding `-client`/`-testcontainers`/`-introspection`/`-meta`) across the repo produces the following actionable hits in **tracked source files** (`.planning/` and `uv.lock` noted separately):

### Files that MUST be updated (tool-config and documentation in repo root)

| File | Line(s) | Current value | New value |
|------|---------|---------------|-----------|
| `pyproject.toml` | 35 | `"packages/godoo/src"` (mypy_path) | `"packages/godoo-client/src"` |
| `pyproject.toml` | 63 | `"packages/godoo/pyproject.toml:project.version"` (version_toml) | `"packages/godoo-client/pyproject.toml:project.version"` |
| `pyproject.toml` | 76–77 | `uv build --package godoo-client && ... uv build --package godoo` (build_command) | Remove stale `uv build --package godoo` trailing line (see D-02 note below) |
| `.github/workflows/test.yml` | 24 | `uv run mypy packages/godoo/src packages/...` | `uv run mypy packages/godoo-client/src packages/...` |
| `mkdocs.yml` | 48 | `paths: [packages/godoo/src, ...]` | `paths: [packages/godoo-client/src, ...]` |
| `CONTRIBUTING.md` | 39 | `uv run mypy packages/godoo/src ...` | `uv run mypy packages/godoo-client/src ...` |
| `CONTRIBUTING.md` | 68, 75, 76 | `packages/godoo/src/godoo/services/...` prose | Update prose |
| `CLAUDE.md` | 12, 28, 92, 110, 115 | various `packages/godoo/...` refs | Update all |

### uv.lock (auto-regenerated, NOT hand-edited)

| Line(s) | Current value | Action |
|---------|---------------|--------|
| 271 | `source = { editable = "packages/godoo" }` | Auto-updated by `uv sync` |
| 288 | `{ name = "godoo-client", editable = "packages/godoo" }` | Auto-updated by `uv sync` |
| 301 | `{ name = "godoo-client", editable = "packages/godoo" }` | Auto-updated by `uv sync` |

**Do not hand-edit `uv.lock`.** Run `uv sync` after the `git mv`; uv will rewrite the editable path entries automatically.

### .planning/ codebase docs (informational prose — update for consistency, not correctness)

These are `.planning/codebase/` snapshot documents (ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, STACK.md, etc.) and `.planning/research/` files. They contain ~100+ `packages/godoo/` references that are descriptive prose, not operative paths. The planner may choose to update these in a follow-up commit or leave them as historical snapshots — they do not affect CI.

**CLAUDE.md** does contain two operative references (the `Structure` section line 12 and the `Linting & Types` run command line 28) that will be wrong post-rename. These should be updated.

### D-02 confirmed: build_command cleanup

The current `build_command` in `pyproject.toml` (lines 72–77) is:

```toml
build_command = """
    uv build --package godoo-client && \
    uv build --package godoo-testcontainers && \
    uv build --package godoo-introspection && \
    uv build --package godoo
"""
```

The trailing `uv build --package godoo` is a stale entry. The dist name is `godoo-client` (line 1 of `packages/godoo/pyproject.toml`: `name = "godoo-client"`); `godoo` as a package name refers to the meta package (`packages/godoo-meta/`). After the rename, `packages/godoo/` no longer exists, so `uv build --package godoo` would either build the meta package (wrong intent) or fail (if uv resolves by directory). **Remove the trailing line.** The meta package is handled by `godoo-meta`, not this entry.

The cleaned `build_command` becomes:

```toml
build_command = """
    uv build --package godoo-client && \
    uv build --package godoo-testcontainers && \
    uv build --package godoo-introspection
"""
```

---

## PEP 420 Namespace Invariant (D-03)

### Verified: no top-level `godoo/__init__.py`

Direct inspection of `packages/godoo/src/godoo/` confirms it contains only:
- `__pycache__/` (generated, gitignored)
- `client/` (the service subdirectory)

No `__init__.py` at the top level of the `godoo/` namespace directory. [VERIFIED: direct ls of packages/godoo/src/godoo/]

This is the PEP 420 invariant: `godoo` is a namespace package. After the rename, `packages/godoo-client/src/godoo/` will have the same structure.

### Guard test (D-03)

Place in `packages/godoo-client/tests/test_namespace.py` (or the planner's chosen name):

```python
# Source: PEP 420 — namespace packages have __file__ == None
import godoo

def test_godoo_is_namespace_package() -> None:
    """Assert godoo is a PEP 420 namespace package with no stray __init__.py."""
    assert godoo.__file__ is None, (
        "godoo.__file__ is not None — a stray __init__.py was introduced. "
        "This would break the namespace package layout and could prevent "
        "other packages from contributing to the godoo.* namespace."
    )
```

The existing `packages/godoo/tests/__init__.py` is a test-suite marker, not a `godoo` namespace file — it moves with the directory and is harmless.

---

## Sibling Package Dependency Declarations (D-01 verification)

Both `packages/godoo-testcontainers/pyproject.toml` and `packages/godoo-introspection/pyproject.toml` declare:

```toml
dependencies = ["godoo-client>=0.1.0"]
```

[VERIFIED: direct read of both pyproject.toml files]

They depend on the **dist name** `godoo-client`, not a directory path. The root `pyproject.toml` wires the workspace alias:

```toml
[tool.uv.sources]
godoo-client = { workspace = true }
```

uv resolves `godoo-client` by workspace discovery (scanning `packages/*` for `project.name = "godoo-client"`), not by directory name. After renaming the directory to `packages/godoo-client/`, uv will find the same `pyproject.toml` with the same `project.name = "godoo-client"` and re-resolve correctly. **No changes needed in sibling package pyproject.toml files.**

---

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — library package, no database | None |
| Live service config | None — no external services reference this path | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no env vars reference `packages/godoo/` | None |
| Build artifacts | `uv.lock` has 3 editable path entries pointing at `packages/godoo` (lines 271, 288, 301) | Regenerate via `uv sync` after `git mv`; do NOT hand-edit |

---

## Common Pitfalls

### Pitfall 1: mypy silently passes with wrong path
**What goes wrong:** If `packages/godoo/src` is removed from `mypy_path` but `packages/godoo-client/src` is not added, mypy reports zero errors (it simply skips a missing path). CI passes but core package is no longer type-checked.
**How to avoid:** Update `pyproject.toml` `mypy_path` and `.github/workflows/test.yml` mypy invocation atomically with the rename.
**Warning signs:** mypy reports no errors on code with deliberate type errors introduced in `packages/godoo-client/src/`.

### Pitfall 2: uv.lock editable paths not updated
**What goes wrong:** `uv sync` fails or installs from the wrong location if `uv.lock` still references `packages/godoo`.
**How to avoid:** Run `uv sync` after the `git mv`; never hand-edit the lock file.
**Warning signs:** `uv sync` exits with an error about a missing workspace member.

### Pitfall 3: Stale `uv build --package godoo` in build_command
**What goes wrong:** `python-semantic-release` runs `uv build --package godoo` on the next release. After the rename, `packages/godoo/` no longer exists. `uv build --package godoo` may build the meta package instead (because the dist named `godoo` is `packages/godoo-meta/`) or fail — either outcome is wrong.
**How to avoid:** Remove the stale line per D-02 as part of this phase's reference sweep.

### Pitfall 4: Stray `__init__.py` introduced
**What goes wrong:** If any build tool or developer creates `packages/godoo-client/src/godoo/__init__.py`, the namespace package collapses to a regular package, preventing other packages from contributing to the `godoo.*` namespace.
**How to avoid:** D-03 guard test catches this. Never add `__init__.py` to the top-level namespace directory.
**Warning signs:** `godoo.__file__` is not `None` — the guard test fails.

### Pitfall 5: `git rm` + `git add` instead of `git mv`
**What goes wrong:** Git treats the move as a deletion and re-addition, destroying blame history. `git log --follow packages/godoo-client/src/godoo/client.py` will find nothing.
**How to avoid:** Always use `git mv packages/godoo packages/godoo-client`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lock file update | Manual path edits in `uv.lock` | `uv sync` | uv regenerates lock atomically; hand edits break checksums |
| Detecting missing `__init__.py` | Custom shell script | pytest guard test (`godoo.__file__ is None`) | Runs in CI automatically |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8 with pytest-asyncio >=0.24 |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/ -m "not integration" -q` |
| Full suite command | `uv run pytest packages/ -v --cov --cov-report=xml -m "not integration"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PKG-01 | `packages/godoo-client/` exists; `packages/godoo/` absent | smoke / filesystem | `git mv` + `uv sync` exit 0 | N/A (shell gate) |
| PKG-01 | `git log --follow` preserves blame | manual spot-check | `git log --follow packages/godoo-client/src/godoo/client/client.py` | N/A (manual) |
| PKG-02 | `uv sync` completes; `import godoo.client` works; wheel builds | smoke | `uv run python -c "import godoo.client"` + `uv build --package godoo-client` | N/A (shell gate) |
| PKG-02 | mypy passes from new path | CI | `.github/workflows/test.yml` lint job | Exists |
| PKG-03 | `godoo.__file__ is None` | unit | `uv run pytest packages/godoo-client/tests/test_namespace.py -q` | Wave 0 gap |

### Wave 0 Gaps

- [ ] `packages/godoo-client/tests/test_namespace.py` — covers PKG-03 (new file, written as part of this phase)

---

## D-04 Local Done-Gate (exact commands)

Run these in order before pushing:

```bash
# 1. After git mv and reference updates:
uv sync

# 2. Import smoke test
uv run python -c "import godoo.client; print('OK')"

# 3. Wheel build smoke test
uv build --package godoo-client

# 4. Full unit test pass (includes PKG-03 guard test)
uv run pytest packages/ -m "not integration" -q

# 5. mypy from new path
uv run mypy packages/godoo-client/src packages/godoo-testcontainers/src packages/godoo-introspection/src

# 6. ruff
uv run ruff check . && uv run ruff format --check .
```

All six must exit 0 before push.

---

## Security Domain

Not applicable. This phase makes no changes to authentication, session management, input validation, cryptography, or network transport. No ASVS categories apply.

---

## Open Questions

None. The rename target, method, verification bar, and complete reference list are all determined. The planner has full information to write PLAN.md files without further research.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `pyproject.toml` (root), `.github/workflows/test.yml`, `mkdocs.yml`, `packages/godoo/pyproject.toml`, `packages/godoo-testcontainers/pyproject.toml`, `packages/godoo-introspection/pyproject.toml` — all path references verified line-by-line
- Direct `ls` of `packages/godoo/src/godoo/` — confirmed no `__init__.py`
- `uv.lock` grep — confirmed 3 editable path entries at lines 271, 288, 301
- `CONTRIBUTING.md` — contains 2 additional operative path references
- `CLAUDE.md` — contains 5 bare `packages/godoo` references needing update

### Secondary (MEDIUM confidence)
- uv workspace resolution behavior: `[tool.uv.sources]` alias ties to dist name, not directory name — inferred from uv docs; behavior confirmed by examining sibling package `dependencies = ["godoo-client>=0.1.0"]` declarations which use dist name only [ASSUMED: uv re-resolves workspace members by scanning pyproject.toml project.name, not directory name — verify with `uv sync` after git mv]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | uv workspace resolution uses `project.name` from pyproject.toml to match `[tool.uv.sources]` workspace aliases, not the directory name | Sibling Package Dependency Declarations | If uv also keys on directory name, sibling packages may fail to resolve `godoo-client` after rename — `uv sync` would fail with "workspace member not found". Mitigation: `uv sync` is the first step in D-04; failure surfaces immediately. |

---

## Metadata

**Confidence breakdown:**
- Reference hit list: HIGH — every file read directly; line numbers confirmed
- PEP 420 invariant: HIGH — direct `ls` of namespace directory
- uv workspace re-resolution after rename: MEDIUM — one assumption (A1); mitigated by D-04 gate
- build_command cleanup: HIGH — `packages/godoo/pyproject.toml` `project.name = "godoo-client"` confirms `--package godoo` is distinct from `--package godoo-client`

**Research date:** 2026-05-27
**Valid until:** 2026-07-01 (stable tooling, no fast-moving dependencies)
