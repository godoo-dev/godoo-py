---
name: godoo-py-docs
description: Retrieve, author and maintain godoo-py canonical documentation and Python library targets, including proposed contracts before implementation and reconciliation after verification.
---

# Maintain Python documentation

Use the explicitly selected godoo-py checkout. Read AGENTS.md and README.md;
README.md and docs/index.md are the navigation, docs/library-targets.md owns library
intent and language differences, and existing service/API/guides own usage.
Work and open implementation decisions use
[godoo-py-capture](../godoo-py-capture/SKILL.md). Private evidence and provisional
research use owner-paths outside source. Local bindings live in ignored
`.mafe-si.toml`; no HQ checkout or network profile fetch is required.

## Retrieve or assess

Read an explicit file first. Otherwise run `rg -n 'QUERY' README.md docs` from the
selected checkout, read matches in context and follow only relevant links. Cite
the actual file/section or a public GitHub revision for historical claims. State
missing or inaccessible coverage. Queries and report-only freshness assessments
make no content or configuration writes.

For current behavior inspect relevant source and tests. Targets are desired
outcomes, not availability claims. Separate implementation, local tests, installed
wheels, registry publication, runtime and consumer acceptance; retain versions,
dates, attribution and uncertainty. For bounded mechanism or historical rationale
research use explain-system when available without turning explanation into a write.

## Author, consolidate or support delivery

Search existing coverage and amend its canonical page. Use technical-writing for
composition when available; otherwise write for the reader's task with concrete
behavior, exact source-checked API names and useful examples. Label proposed
contracts and unresolved choices explicitly. Do not turn TypeScript-only APIs or
historical observations into Python availability claims. Keep private identities,
local paths and raw source keys out of public docs and metadata.

Before implementing a changed user/operator contract, write the smallest useful
proposed guide/example here. After verification reconcile affected current claims
with the result; retain unmet targets as targets and link distinct remaining work.
No reader-facing impact means no compulsory docs edit. Documentation does not
commission implementation, release, deployment or publication.

Before moving/removing a page or heading, use `rg` on its filename, anchor and
aliases across README.md, docs/, mkdocs.yml, AGENTS.md and .agents/. Inspect incoming
references. Combine equivalent content, preserve meaningful differences and dated
qualifications, repair in-scope links/navigation and state inaccessible/out-of-scope
relationships. Keep actual conflicts explicit until evidence settles them; do not
create parallel ADR/history/review collections or duplicate canonical bodies.

Read actual edited files back, inspect the full diff and untracked additions,
check affected relative links/anchors and mkdocs.yml navigation, then run
`git diff --check`. A docs build, when appropriate, is `uv run mkdocs build --strict
--site-dir /absolute/external/site`; inspect dependencies/setup before running it.
Docs edits need no product/container suites. Use the existing verifier for actual
product proof. Return canonical changed pages, checked behavior and limitations.
