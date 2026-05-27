# Phase 5: Directory Rename - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 5-Directory Rename
**Areas discussed:** Reference sweep scope, build_command cleanup, PEP 420 guard test, Verification depth

---

## Reference sweep scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full grep sweep | Grep whole repo for `packages/godoo/` and update every hit, not just the 7 enumerated refs | ✓ |
| Just the 7 enumerated refs | Update only the known list; faster but risks missing a doc/comment | |

**User's choice:** Full grep sweep
**Notes:** Recommended option accepted. Guards against stragglers beyond the enumerated minimum.

---

## build_command cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Remove the stale entry | Drop trailing `uv build --package godoo` if it's a leftover duplicate | ✓ |
| Investigate first, then decide | Read build_command and confirm stale before removing | (folded in) |
| Leave build_command untouched | Defer cleanup to a separate chore | |

**User's choice:** Remove the stale entry
**Notes:** Executor must still confirm the entry is genuinely stale (read current contents) before removing — captured in D-02.

---

## PEP 420 guard test

| Option | Description | Selected |
|--------|-------------|----------|
| Add it in godoo-client's own tests | `packages/godoo-client/tests/`; runs in normal pytest pass | ✓ |
| Add as a root/workspace-level test | Top-level tests/ structural invariant | |
| Skip the guard test this phase | Rely on CI import + wheel build | |

**User's choice:** Add it in godoo-client's own tests
**Notes:** Lives with the package it protects; asserts `godoo.__file__ is None`.

---

## Verification depth

| Option | Description | Selected |
|--------|-------------|----------|
| Local gate + CI green | Executor runs uv sync + import + wheel build locally AND CI passes | ✓ |
| CI green only | Trust CI as the sole gate | |

**User's choice:** Local gate + CI green
**Notes:** Catch path breakage locally before push.

---

## Claude's Discretion

- Commit ordering (git mv vs reference updates) and plan/commit split — left to planner.
- Exact file/test-function name for the PEP 420 guard test — planner's call.

## Deferred Ideas

None — discussion stayed within phase scope.
