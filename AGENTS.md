# Working in godoo-py

Read [README.md](README.md) for the package boundary and developer documentation.
Product intent is maintained in the local [godoo HQ README](/home/marc/dev/godoo-dev/godoo-hq/README.md)
and its linked targets. This absolute local route also works from linked worktrees;
it is not a prerequisite for users installing these libraries independently.

Use the installed mafe-si procedures for scoped delivery and coordination. Work,
open decisions and acceptance evidence belong in the locally bound
`~~project tracker`. Resolve its command/root from local mafe-si guidance rather
than hardcoding them in tracked docs. Read the tracker agent guidance before
unfamiliar operations; use explicit `--root` and `--json` and inspect warnings.
Do not create parallel planning journals here. Perficio is dormant. Historical
GSD phase/adoption/report-back gates do not govern current work.

Keep useful API and engineering guidance in the existing developer docs. Inspect
source before claiming an API is available, and distinguish source, tests,
publication, runtime and consumer acceptance. For a changed user contract, consult
HQ's docs procedure before implementation and reconcile the affected target after
verification. Documentation alone grants no release or deployment authority.

Preserve unrelated edits. Check status, branch, worktree ownership and active users
before changes; do not switch/reset the primary branch or alter another worker's
checkout. Use owner-paths for notes and evidence outside source. For a new
cross-project introduction or shared-resource contention, follow
`/home/marc/dev/marc-hq/fleet/AGENTS.md` through coordinate-projects. Established
exchanges and independent authorized work continue directly.

Python 3.14+, uv workspace and PEP 420 `godoo.*` namespace packages. Public imports
start at `godoo.client`, `godoo.introspection` or `godoo.testcontainers`.
Core types use dataclasses; the optional generated typed-model layer uses Pydantic.
Keep async service functions and lazy service accessors; wrap synchronous container
work in `asyncio.to_thread()`. See [contributing](CONTRIBUTING.md) and
[development](docs/development.md). Do not run Docker/live workflows for doc edits.
