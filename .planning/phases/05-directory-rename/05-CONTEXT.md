# Phase 5: Directory Rename - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Rename the core package directory `packages/godoo/` → `packages/godoo-client/` using
`git mv` (blame-preserving), so the directory name matches the already-live PyPI dist
name (`godoo-client`) and the existing `[tool.uv.sources]` workspace alias.

**Immutable:** the Python import namespace stays `godoo.*` (PEP 420 decouples directory
name from import path — no top-level `__init__.py` is introduced). Updating import paths
or the namespace is explicitly out of scope.

Scoped to requirements PKG-01, PKG-02, PKG-03.

</domain>

<decisions>
## Implementation Decisions

### Reference sweep scope
- **D-01:** Do a **full repo grep sweep** for the literal `packages/godoo/` (and bare
  `packages/godoo` not followed by `-client`/`-testcontainers`/`-introspection`/`-meta`),
  and update **every** hit — docs, READMEs, comments, configs — not just the 7 enumerated
  references. The enumerated list (root `pyproject.toml` mypy_path / version_toml /
  build_command, `.github/workflows/test.yml`, `mkdocs.yml`, the moved
  `packages/godoo/pyproject.toml`) is the known minimum, not the ceiling. Reason: guard
  against stragglers the enumerated list missed.

### build_command cleanup
- **D-02:** Remove the stale trailing `uv build --package godoo` from the root
  `pyproject.toml` `build_command` if verification confirms it is a leftover duplicate of
  `--package godoo-client`. The executor must **read the current build_command and confirm
  the entry is genuinely stale before removing** — do not assume its contents. Goal: keep
  the semantic-release build clean post-rename.

### PEP 420 guard test
- **D-03:** Add the namespace-invariant guard test **in the renamed package's own suite**
  (`packages/godoo-client/tests/`). It asserts `godoo.__file__ is None` (i.e. `godoo` is a
  PEP 420 namespace package with no stray top-level `__init__.py`). It runs in the normal
  pytest unit pass and lives with the package it protects.

### Verification depth
- **D-04:** Prove the rename with a **local gate AND CI green**. The executor must run,
  locally, as an explicit done-gate: `uv sync`, `import godoo.client` (e.g.
  `uv run python -c "import godoo.client"`), and a wheel build — before push. CI
  (ruff / mypy / pytest / build) must also pass from the new location. Reason: catch path
  breakage locally instead of discovering it in CI.

### Claude's Discretion
- Exact ordering of the `git mv` vs. reference-update commits, and how the work is split
  across plans/commits, is left to the planner.
- The precise file/test-function name for the PEP 420 guard test (within
  `packages/godoo-client/tests/`) is the planner's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — PKG-01 (blame-preserving `git mv`), PKG-02, PKG-03; and
  the "Out of Scope" entry locking the `godoo.*` import namespace.
- `.planning/ROADMAP.md` — Phase 5 "Directory Rename" goal + success criteria (the
  PEP 420 guard, the `uv sync` + import + wheel-build checks, the reference baseline).

### Files affected by the rename (the enumerated minimum — sweep for more per D-01)
- `pyproject.toml` (root) — `tool.mypy` `mypy_path`, semantic-release `version_toml`, and
  `build_command` (the `packages/godoo/...` paths + the stale `--package godoo` entry).
- `.github/workflows/test.yml` — mypy invocation referencing `packages/godoo/src`.
- `mkdocs.yml` — mkdocstrings paths referencing `packages/godoo/src`.
- `packages/godoo/pyproject.toml` — moves with the directory (becomes
  `packages/godoo-client/pyproject.toml`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The PyPI dist name `godoo-client` and the `[tool.uv.sources]` workspace alias
  `godoo-client = { workspace = true }` already exist — the rename makes the directory
  catch up to names that are already authoritative. No new naming to invent.

### Established Patterns
- PEP 420 namespace package: `packages/godoo/src/godoo/` has no top-level `__init__.py`,
  which is what lets the directory rename leave the `godoo.*` import path untouched. The
  guard test (D-03) protects this invariant.

### Integration Points
- `packages/godoo-testcontainers` and `packages/godoo-introspection` depend on the core
  package via the **dist name** (`godoo-client`), not the directory path — so their
  dependency declarations should need no change. The full sweep (D-01) still verifies this
  rather than assuming it.

</code_context>

<specifics>
## Specific Ideas

No bespoke requirements — the rename target, method (`git mv`), and verification bar are
fully captured in the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Open decisions OD-1/OD-2 noted in the
roadmap belong to Phase 6, not this phase.)

</deferred>

---

*Phase: 5-Directory Rename*
*Context gathered: 2026-05-27*
