# Phase 4: Release - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Make all three packages publicly installable from PyPI under the
`godoo-dev/godoo-py` GitHub repo. Three concrete deliverables: (1) create the repo +
`origin` and get CI green, (2) restructure the packages into a shared `godoo.*`
namespace and rename the client distribution to `godoo-client`, (3) publish to PyPI.

The release **infrastructure already exists** (semantic-release across all three
pyprojects, trusted PyPI publishing in `release.yml`, a `test.yml` matrix). This phase
*completes and corrects* that infra and threads the namespace rename through it — it
does not build release tooling from scratch, and it adds no library features.

</domain>

<decisions>
## Implementation Decisions

### Package Naming & Namespace
- **D-01:** Adopt a **shared `godoo` PEP 420 implicit namespace package**. The three
  distributions ship as importable subpackages under one namespace — `godoo.client`,
  `godoo.introspection`, `godoo.testcontainers` (the `azure.*` / `google.cloud.*`
  pattern). No single distribution owns a top-level `godoo/__init__.py`.
- **D-02:** PyPI distribution names: `godoo-client`, `godoo-introspection`,
  `godoo-testcontainers`.
- **D-03:** **Import migration is in scope** and touches all three packages:
  - `import godoo` / `from godoo import OdooClient` → `from godoo.client import ...`
  - `import godoo_introspection` → `import godoo.introspection`
  - `import godoo_testcontainers` → `import godoo.testcontainers`
  - src layouts restructure to `src/godoo/client/`, `src/godoo/introspection/`,
    `src/godoo/testcontainers/`
  - cross-package deps `godoo>=0.1.0` (in introspection + testcontainers pyproject)
    become `godoo-client>=…`; `[tool.uv.sources]` key updates accordingly
- **D-04:** The **existing `godoo` PyPI project (owned by Marc) becomes an empty
  namespace-locking placeholder**. It publishes no real code; its sole jobs are to
  reserve the `godoo` name for the family and to host the **main/family README** on its
  PyPI page. Each sibling distribution ships its own **short README**.

### Versioning
- **D-05:** First public release cuts at **0.x (e.g. 0.1.0)** — pre-1.0, no stable-API
  commitment yet. Matches the existing semantic-release config
  (`allow_zero_version = true`, `major_on_zero = false`).

### CI/CD & Release Gate
- **D-06:** CI/CD must reach **full parity with `godoo-ts`** — a complete test matrix.
  **No release without the full matrix green.**
- **D-07:** **Docker/Odoo integration tests are a hard blocker on the publish path.**
  `release.yml` fires only after the `Test` workflow — lint + unit + the integration
  matrix over `ODOO_VERSION` `[17.0, 18.0, 19.0]` — succeeds on `main`. This is already
  structurally present in `test.yml` (`integration` job has `needs: [lint, unit-tests]`,
  `release.yml` triggers on `Test` workflow success); complete and correct it rather
  than rebuild.
- **D-08:** In-scope CI correctness fix: the `lint` job's `mypy` step currently covers
  only `packages/godoo/src` and `packages/godoo-testcontainers/src` — it must cover all
  three src trees (introspection now exists) after the namespace restructure.

### Repo
- **D-09:** Create `github.com/godoo-dev/godoo-py`, push the **full commit history**,
  set `origin`. Public repo (LGPL-3.0-or-later). (RELEASE-01)

### Claude's Discretion
- The hatchling mechanics of namespace packaging (how each distribution declares its
  `godoo.*` subpackage without colliding on the namespace root).
- Exactly how the empty `godoo` meta/placeholder distribution is built (pure-README
  shim vs. a thin re-export package) — D-04 fixes intent (empty, README-hosting), not
  mechanism.
- Trusted-publishing PyPI-side configuration steps (pending-publisher setup is manual
  and outside CI).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CI/CD parity target
- `../godoo-ts/.github/workflows/ci.yml` — the parity reference. Two-job shape: a
  matrixed `ci` job (install → biome check → tsc → build → unit test) and a separate
  matrixed `integration` job using testcontainers. godoo-py CI must match this
  completeness (Python equivalents: ruff + mypy --strict + build + `pytest`; integration
  matrix dimension is `ODOO_VERSION`, not interpreter version).

### Existing godoo-py release infra (complete / correct — do not rebuild)
- `.github/workflows/test.yml` — current `lint` / `unit-tests` (coverage→codecov) /
  `integration` (matrix `ODOO_VERSION` 17.0/18.0/19.0, `needs: [lint, unit-tests]`) jobs.
- `.github/workflows/release.yml` — `python-semantic-release` + `uv publish
  --trusted-publishing always`, triggered by the `Test` workflow concluding `success` on
  `main`.
- `.github/workflows/docs.yml` — docs build.
- `pyproject.toml` → `[tool.semantic_release]` (`version_toml` lists all three package
  pyprojects; `build_command` builds all three via `uv build --package …`) and
  `[tool.uv.sources]` (`godoo = { workspace = true }`).

### Phase scope, requirements & charter
- `.planning/ROADMAP.md` → "### Phase 4: Release" (goal + success criteria).
- `.planning/REQUIREMENTS.md` → RELEASE-01 (repo + origin), RELEASE-02 (rename to
  godoo-client), RELEASE-03 (publish all three).
- `.planning/PROJECT.md` → "## Key Decisions". **Note:** D-01 here *supersedes* the
  prior row "godoo→godoo-client; introspection/testcontainers keep names" — distribution
  names still match, but the *import surface* of all three now moves under `godoo.*`.
- `SEED.md` → §5 (release deliverable — the satellite owns publish), §6(b) (original
  PyPI rename decision, now refined by D-01/D-04).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `test.yml` / `release.yml` / `docs.yml`: a near-complete CI/CD pipeline already
  exists — restructure, don't rebuild. The integration matrix and the publish gate are
  already wired.
- semantic-release is already configured to version and build all three packages in one
  pass; trusted publishing is already declared in `release.yml`.

### Established Patterns
- uv workspace + hatchling per-package builds; each package is `packages/<name>/` with
  its own `pyproject.toml` and `src/<import_name>/` tree.
- Current package dirs: `packages/godoo` (→ `godoo-client`),
  `packages/godoo-introspection`, `packages/godoo-testcontainers`.

### Integration Points
- The rename ripples through: `[tool.uv.sources]`, the `godoo>=0.1.0` dependency in
  both `godoo-introspection` and `godoo-testcontainers` pyprojects, every internal
  import, and the `version_toml` / `build_command` package references in the
  semantic-release config.
- No git remote is configured yet (`git remote -v` is empty) — RELEASE-01 starts from
  zero on the remote side.

</code_context>

<specifics>
## Specific Ideas

- "The PyPI way" the user wants is the namespace-family layout: `godoo.client`,
  `godoo.introspection`, `godoo.testcontainers` — analogous to `azure.*` /
  `google.cloud.*`.
- The `godoo` PyPI page itself should display the **main/family README**; each sibling
  package carries its own **short README**.
- CI/CD must be "complete, just as `../godoo-ts`" — the maintainer is explicit that
  there is no release without a full test matrix passing.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (The fate of the old `godoo` PyPI name was
resolved in-scope as D-04, not deferred.)

</deferred>

---

*Phase: 4-Release*
*Context gathered: 2026-05-22*
