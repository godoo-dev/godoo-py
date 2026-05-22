# Phase 4: Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 4-Release
**Areas discussed:** Rename blast radius, PyPI name strategy, First release version, CI gate for publish

---

## Rename blast radius

| Option | Description | Selected |
|--------|-------------|----------|
| Distribution name only | PyPI name = godoo-client, keep `import godoo`, src dir + workspace deps untouched | |
| Full rename incl. import path | Rename src dir to godoo_client, change imports, update sibling deps | |
| Shared `godoo` namespace (free-text) | Ship godoo-client / godoo-introspection / godoo-testcontainers importable as `godoo.client`, `godoo.introspection`, `godoo.testcontainers` — the PyPI namespace-family way | ✓ |

**User's choice:** Free-text — "we use godoo as a namespace, then we ship godoo-client & godoo-introspection which are importable as godoo.client, godoo.introspection… that would be the PyPI way."
**Notes:** Reflected back and confirmed. This supersedes the earlier "introspection/testcontainers keep names" import-surface assumption; distribution names still match. Captured as D-01/D-02/D-03.

---

## PyPI name strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Fresh first publish | Neither godoo nor godoo-client ever on PyPI | |
| godoo exists — true rename | godoo already published under Marc's account; decide fate of old name | ✓ |

**User's choice:** "godoo exists, it's mine." Follow-up: the `godoo` PyPI package should be **empty** to lock the namespace and display the main README; each other package has its own short README.
**Notes:** Captured as D-04. Old name becomes a namespace-locking placeholder/meta distribution, not yanked.

---

## First release version

| Option | Description | Selected |
|--------|-------------|----------|
| 0.x (e.g. 0.1.0) | Pre-1.0, signals iterating, no stable-API commitment | ✓ |
| 1.0.0 | Declares parity milestone as stable public API | |

**User's choice:** 0.x (recommended option accepted).
**Notes:** Matches existing semantic-release config (allow_zero_version, major_on_zero=false). Captured as D-05.

---

## CI gate for publish

| Option | Description | Selected |
|--------|-------------|----------|
| Unit + lint + mypy only | Fast/deterministic gate; integration runs elsewhere | |
| Include Docker integration tests | Full matrix incl. `pytest -m integration` over ODOO_VERSION before publish | ✓ |

**User's choice:** Include Docker integration tests. Follow-up: CI/CD must be "complete, just as ../godoo-ts. We cannot release without a full test matrix."
**Notes:** Captured as D-06/D-07/D-08. Parity reference is ../godoo-ts/.github/workflows/ci.yml. Existing test.yml already has the matrix + needs-gate; in-scope fix: mypy step omits packages/godoo-introspection/src.

---

## Claude's Discretion

- Hatchling namespace-packaging mechanics (declaring `godoo.*` subpackages without colliding on the namespace root).
- How the empty `godoo` meta/placeholder distribution is built (pure-README shim vs. thin re-export).
- Trusted-publishing PyPI-side configuration steps (manual, outside CI).

## Deferred Ideas

None — discussion stayed within phase scope. The old `godoo` PyPI name's fate was resolved in-scope (D-04), not deferred.
