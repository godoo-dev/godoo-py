# Working in godoo-py

Read [README.md](README.md) for the package boundary and developer documentation.
Library intent belongs in [Python targets](docs/library-targets.md). The public
[organization overview](https://github.com/godoo-dev/.github/blob/main/profile/README.md)
provides sibling orientation; normal work does not require fetching it.

Use [.agents/skills/godoo-py-verification/SKILL.md](.agents/skills/godoo-py-verification/SKILL.md)
for native checks, installed-wheel proof and owned disposable Odoo18 verification.
Its package/offline/service paths are separate from hosted policy or publication.
Use the installed mafe-si procedures for scoped delivery. Work, open decisions
and acceptance evidence belong in this repository's GitHub issues through
[godoo-py-capture](.agents/skills/godoo-py-capture/SKILL.md). Documentation retrieval,
authoring and bounded maintenance use
[godoo-py-docs](.agents/skills/godoo-py-docs/SKILL.md). Local category bindings in
ignored `.mafe-si.toml` override inherited routes. The shared legacy store is
historical migration evidence, not new intake. Do not create parallel planning
journals. Historical GSD/Perficio gates do not govern current work.

Keep useful API and engineering guidance in the existing developer docs. Inspect
source before claiming an API is available, and distinguish source, tests,
publication, runtime and consumer acceptance. For a changed user contract, consult
the project docs procedure before implementation and reconcile the affected target
after verification. Documentation alone grants no release or deployment authority.

Preserve unrelated edits. Check status, branch, worktree ownership and active users
before changes; do not switch/reset the primary branch or alter another worker's
checkout. Use owner-paths for notes and evidence outside source. Report cross-project
dependencies, conflicts and needed handoffs to Marc in the current conversation.
Inter-agent communication, delegates, inboxes and agent messages through shared files or trackers are forbidden. Existing grants and
resource holdings survive routing changes.

Python 3.14+, uv workspace and PEP 420 `godoo.*` namespace packages. Public imports
start at `godoo.client`, `godoo.introspection` or `godoo.testcontainers`.
Core types use dataclasses; the optional generated typed-model layer uses Pydantic.
Keep async service functions and lazy service accessors; wrap synchronous container
work in `asyncio.to_thread()`. See [contributing](CONTRIBUTING.md) and
[development](docs/development.md). Do not run Docker/live workflows for doc edits.
