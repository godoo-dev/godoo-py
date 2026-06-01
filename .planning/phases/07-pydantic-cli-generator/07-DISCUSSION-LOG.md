# Phase 7: Pydantic CLI Generator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01
**Phase:** 7-Pydantic CLI Generator
**Areas discussed:** Emitter architecture (TypedDict vs Pydantic), model selection strategy, relation-target degradation, credential handling, command name

---

## Emitter Architecture: Why Two Generators?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both | Maintain TypedDict emitter (INTRO-03) alongside new Pydantic emitter; user picks via flag or separate command | |
| Replace | Hard-replace TypedDict emitter with Pydantic emitter in Phase 7; TypedDict codegen + tests removed | ✓ |

**User's choice:** Replace — hard replace this phase.

**Notes:** Investigation confirmed the TypedDict emitter is a shipped v1.0 deliverable
(INTRO-03 in `v1.0-REQUIREMENTS.md`), but no downstream use case was identified that
requires both emitters to coexist. Maintaining two emitters doubles the codegen surface
(two `type_mapper.py` forms, two test suites, two output formats) with no clear consumer
benefit at this stage. User chose REPLACE.

Roadmap sync: SC-4 in ROADMAP.md was updated immediately to remove the "TypedDict codegen
path is unaffected" clause and replace it with the breaking-change statement. The
`v1.0-REQUIREMENTS.md` INTRO-03 entry received a supersession annotation; the current
`REQUIREMENTS.md` TYPED-01/02 block received a corresponding note.

Accepted tradeoff (noted explicitly): replacing TypedDict gives up the zero-dependency,
zero-runtime-cost typing of raw `search_read` dicts. Users who relied on INTRO-03 for
purely static annotation without a Pydantic runtime dependency lose that option. User
explicitly accepts this loss.

---

## Model Selection Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed list | `--models res.partner,project.task,...` — exact technical names only | |
| Glob/wildcard | `--models pat1,pat2,...` with fnmatch-style patterns; `*` matches any chars incl. dots | ✓ |
| Module-based | `--module sale` — generate all models contributed by an Odoo module | |

**User's choice:** Glob/wildcard patterns (`--models`) plus `--all` flag.

**Notes:** Exact names are a subset of glob patterns (a literal name with no wildcards
matches only itself). Module-based selection was not requested and adds an ir.module RPC
round-trip. The `fnmatch` stdlib module handles the matching natively. Exactly one of
`--models` or `--all` must be provided; missing → clear error.

---

## Relation Targets (many2one)

| Option | Description | Selected |
|--------|-------------|----------|
| Always `Ref[int]` | Degrade all many2one to `Ref[int]`; no cross-imports between generated files | |
| Transitive auto-include | When target not in selection, auto-add it recursively | |
| Degrade with comment | In-set → `Ref[TargetClass]`; out-of-set → `Ref[int]  # <odoo.model>` | ✓ |

**User's choice:** Degrade with comment — in-set gets `Ref[TargetClass]`; out-of-set gets
`Ref[int]` with a trailing `# <odoo.model>` comment.

**Notes:** Transitive auto-inclusion was explicitly rejected: it can balloon the generated
set unexpectedly (one `res.partner` field pulls in `res.country`, `res.state`, etc.).
The comment preserves navigational context for the developer without forcing generation.
Files must always compile; `Ref[int]` satisfies this with no conditional import.

---

## Credential Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Flags only | All four credentials required as explicit CLI flags; no env-var fallback | |
| Env-var default, flags override | `config_from_env()` as default; `--url`/`--db`/`--user`/`--password` override | ✓ |
| Separate config file | Read from a `.godoo.toml` or similar project config file | |

**User's choice:** Reuse `config_from_env()` as default; flags override.

**Notes:** `config_from_env()` already exists in `godoo-client` and is the established
pattern for all integration tests and user scripts. Reusing it means zero new credential
machinery. Typer's `envvar=` option parameter handles the env-var/flag precedence natively.
Password is never echoed, never logged — enforced by not printing it in error messages and
using Typer's `hide_input=True` for the `--password` option.

---

## Command Name

| Option | Description | Selected |
|--------|-------------|----------|
| `generate-pydantic` | Disambiguated suffix in case a TypedDict variant is added later | |
| `generate` | Plain name — single output format means no disambiguation needed | ✓ |

**User's choice:** `generate`.

**Notes:** Since the TypedDict emitter is being retired (not kept alongside), there is only
one `generate` target. A disambiguation suffix would be misleading. The ROADMAP SC-1 was
updated from `generate-pydantic` to `generate` immediately.

---

## Claude's Discretion

- Exact typer argument / option names and help strings.
- Whether `--output` defaults to `./models/` or is required (required preferred to avoid
  accidental overwrites).
- Whether output dir existence is validated before connecting to Odoo (fail fast preferred).
- Error message wording for missing credentials or unmatched model patterns.

## Deferred Ideas

- Typed write/create paths (TYPED-F2) — deferred to future milestone; v1.1 covers typed reads.
- Nested relational fetch (TYPED-F1) — deferred; `Ref[T]`/`list[int]` is the v1.1 line.
- Re-generation cadence / schema freshness tooling — no diff/warn in scope for Phase 7.
