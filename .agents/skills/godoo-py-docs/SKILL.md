---
name: godoo-py-docs
description: Retrieve, author, move or freshness-check godoo-py documentation — README, docs/, docstrings, Python library targets and project skills — and decide which godoo-py surface a piece of knowledge belongs on, including Atlas markers for Odoo-server behaviour. Work records use godoo-py-capture.
---

# godoo-py documentation

Work in the selected godoo-py checkout. Requests, decisions and remaining work
go to GitHub issues through [godoo-py-capture](../godoo-py-capture/SKILL.md),
not into docs.

## What godoo-py owns

Each claim has one canonical home. godoo-py is that home for:

- **How godoo-py code behaves:** client configuration and environment variables,
  errors, CRUD and typed dispatch, safety guards, domain services, introspection
  and code generation, the `godoo-introspect` CLI, testcontainers, harness and
  snapshots. Its tests prove it.
- **Python library intent:** targets and deliberate differences from the other
  Godoo libraries, in `docs/library-targets.md`.
- **How to work on godoo-py:** checks, release and capture, in `.agents/skills/`,
  `CONTRIBUTING.md` and `docs/development.md`.

Other kinds belong elsewhere. Route them through capture:

- Odoo server behaviour by version, edition or module belongs in Atlas.
- Agent guidance for an MCP tool belongs in the MCP repository.
- Another Godoo component's behaviour belongs in that component.
- Cross-component synthesis belongs with the owner's coordination docs.

godoo-py may *reflect* those claims for its readers, but it cites the owner and
never becomes a second source.

## Choose the surface

| Surface | Holds |
| --- | --- |
| Code comment | Why non-obvious code exists, including a workaround for Odoo behaviour. |
| Docstring | The caller's contract: arguments, results, errors, version limits. mkdocstrings renders these into `docs/api/`. |
| `README.md`, `docs/` | Usage across several APIs, setup and examples. Service guides are in `docs/services/` and guides in `docs/guides/`. Navigation is in `docs/index.md` and `mkdocs.yml`. |
| `docs/library-targets.md` | Desired outcomes and language differences. These are targets, not availability claims. |
| `.agents/skills/` | Maintainer procedures. These never ship in wheels or reach library users. |
| `CHANGELOG.md` | Release history, prepared during version preparation. Do not hand-edit past entries. |

When one fact matters to several readers, write each reflection by hand for its
reader.

## Atlas markers

Text that depends on Odoo server behaviour that can change between versions
names the Atlas fact it relies on. The ID below is only an example of the
form:

- Docstring: `See atlas:base/create-record-basic.`
- Markdown: `<!-- atlas: base/create-record-basic -->`
- Code comment: `# atlas: base/create-record-basic`

Fact IDs are public, but Atlas fact text, verification records and Atlas paths
are not. Write the reflection in your own words and never paste or link Atlas
content. Mark only version-sensitive Odoo behaviour, not every mention of Odoo.

Add a marker only for an ID the Atlas owner has confirmed. If the fact does not
exist yet, send it to Atlas intake through capture first, and add the marker once
the ID exists. A marker records a dependency, not that the text is still right,
and godoo-py's own tests remain the first signal of breakage. A marker that names
an unknown ID is a godoo-py defect to fix here. Atlas reports are advisory and
never gate this repository's CI.

## Retrieve or assess

Open an explicitly named file first. Otherwise search and read the matches in
context:

```sh
rg -n 'QUERY' README.md docs packages/*/src
```

Cite the file and section, or a public GitHub revision for historical claims.
Say what is missing or inaccessible. Queries change nothing.

To assess freshness, compare claims with the current source and tests. Report
each claim as supported, contradicted or unresolved, and keep implementation,
local tests, published wheels and consumer acceptance distinct. A correction
needs edit scope. For research into how something works or why it was chosen,
use explain-system.

## Author or revise

Search the existing coverage and amend its canonical page rather than add a
parallel one. Name a new page for its lasting subject, not for the change or
issue that produced it, and add it to `mkdocs.yml` navigation. In the same
change, fix or remove every existing statement the edit contradicts. Use
technical-writing for composition. Check API names against the source. Do not
present TypeScript-only APIs or targets as available in Python. Label proposed
contracts as proposed.

For a changed user contract, write the smallest proposed guide or example before
implementation. Reconcile it with the verified result afterwards; unmet targets
stay targets. A change with no reader-facing effect needs no docs edit. Docs do
not authorize implementation, release or publication.

Keep private identities, local paths and raw source keys out of this public
repository.

## Move or consolidate

Before moving or removing a page or heading, find its references:

```sh
rg -n 'FILENAME|ANCHOR' README.md CONTRIBUTING.md docs mkdocs.yml .agents
```

Merge only equivalent content. Keep conflicting claims distinct until evidence
settles them, keep dated qualifications, and repair links and navigation.

## Check

```sh
git diff --check
uv run --frozen mkdocs build --strict --site-dir .scratch/site
```

`./scripts/check.py offline` also runs the strict docs build. Docs-only edits
need no Docker or Odoo runs. Report the pages changed and anything unverified.
