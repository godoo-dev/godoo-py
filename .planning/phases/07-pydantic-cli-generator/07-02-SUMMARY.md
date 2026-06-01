---
phase: 07-pydantic-cli-generator
plan: "02"
subsystem: godoo-introspection
tags:
  - cli
  - typer
  - pydantic
  - codegen
dependency_graph:
  requires:
    - "07-01 (CodeGenerator with Pydantic emitter, Introspector.get_schemas)"
  provides:
    - "godoo-introspect CLI entrypoint (generate command)"
    - "pydantic>=2.13 and typer>=0.26 as direct runtime deps of godoo-introspection"
  affects:
    - "packages/godoo-introspection public API (cli module + [project.scripts])"
tech_stack:
  added:
    - "typer>=0.26 — CLI framework with CliRunner for tests"
    - "pydantic>=2.13 — direct dep (was already transitive; now first-class)"
  patterns:
    - "typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False) + @app.callback() for subcommand dispatch"
    - "sync generate() wrapping asyncio.run(_generate_async()) — typer does not await async defs"
    - "Deferred imports inside function bodies to avoid circular import at module load"
    - "All-flags-present shortcut skips config_from_env() — allows CLI flag-only credential supply"
key_files:
  created:
    - "packages/godoo-introspection/src/godoo/introspection/cli.py"
    - "packages/godoo-introspection/tests/test_cli.py"
  modified:
    - "packages/godoo-introspection/pyproject.toml"
    - "uv.lock"
decisions:
  - "Skip config_from_env() entirely when all four credential flags are explicitly provided — avoids requiring env vars when flags are sufficient"
  - "pretty_exceptions_show_locals=False on Typer — prevents credential values from appearing in exception tracebacks (T-07-05)"
metrics:
  duration: "15m"
  completed: "2026-06-01T21:00:00Z"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
  files_created: 2
requirements:
  - TYPED-01
  - TYPED-02
---

# Phase 07 Plan 02: Pydantic CLI Generator Summary

Wire pydantic>=2.13 and typer>=0.26 as runtime deps of godoo-introspection, create `cli.py` with the typer app and async generate command, and add `test_cli.py` with CliRunner validation tests. After this plan the full quality gate (ruff + mypy + pytest) passes and the CLI is invocable via `godoo-introspect`.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Update pyproject.toml deps and [project.scripts]; regenerate uv.lock | 699975c | packages/godoo-introspection/pyproject.toml, uv.lock |
| 2 | Create cli.py — typer app, generate command, asyncio.run bridge | e87758c | packages/godoo-introspection/src/godoo/introspection/cli.py |
| 3 | Create test_cli.py + format cli.py | 2236dba | packages/godoo-introspection/tests/test_cli.py, cli.py (format) |

## What Was Built

### cli.py — typer CLI entrypoint

- `app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)` — prevents locals dump on unhandled exception (T-07-05)
- `@app.callback()` — required for subcommand dispatch; without it a single-command app runs directly without the `generate` sub-name
- `generate()` — sync def wrapping `asyncio.run(_generate_async(...))` (typer does not await async defs)
- Validation order (fail-fast, before any network): mutual exclusion → neither flag → output dir existence → credential assembly
- Credential assembly: if all four flags provided, constructs `OdooClientConfig` directly; otherwise calls `config_from_env()` and overrides with any explicit flags
- `hide_input=True` on `--password` prevents interactive echo
- `_generate_async()`: authenticate → `ir.model` search_read → fnmatch filter → `Introspector.get_schemas()` → `CodeGenerator.write()` → `typer.echo(f"Generated {N} model(s) to {dir}")`
- Zero-match raises `ValueError("No models matched the given patterns.")` → caught by sync wrapper → exit 1

### test_cli.py — 5 CliRunner tests

| Test | Coverage |
|------|----------|
| `test_generate_requires_models_or_all` | exit 1, "provide --models" in output |
| `test_generate_models_and_all_mutually_exclusive` | exit 1, "mutually exclusive" in output |
| `test_generate_bad_output_dir` | exit 1, "does not exist" in output |
| `test_generate_password_not_in_output` | secret string absent from all output |
| `test_generate_happy_path_writes_files` | 4-RPC mock → exit 0 → res_lang.py + __init__.py written |

### pyproject.toml — deps and [project.scripts]

```toml
dependencies = [
    "godoo-client>=0.1.0",
    "pydantic>=2.13",
    "typer>=0.26",
]

[project.scripts]
godoo-introspect = "godoo.introspection.cli:app"
```

## Quality Gate Results

- `uv run ruff check .` — PASSED
- `uv run ruff format --check .` — PASSED (92 files, 0 changed)
- `uv run mypy packages/godoo-client/src packages/godoo-testcontainers/src packages/godoo-introspection/src` — PASSED (57 files)
- `uv run pytest packages/ -m "not integration"` — PASSED (334 tests, up from 329 in plan 01)
- `uv run godoo-introspect --help` — exits 0, shows "generate" as subcommand
- `uv run godoo-introspect generate --help` — exits 0, shows all options including `--password`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Optional[str] → str | None (UP045 ruff violations)**
- **Found during:** Task 2 ruff check after cli.py creation
- **Issue:** Plan specified `Optional[str]` in function signatures but ruff UP045 requires `str | None` (Python 3.10+ union syntax)
- **Fix:** Replaced all `Optional[str]` with `str | None` in cli.py; removed `Optional` from typing imports
- **Files modified:** `cli.py`
- **Commit:** e87758c

**2. [Rule 1 - Bug] config_from_env() called even when all flags are provided**
- **Found during:** Task 3 test run — `test_generate_happy_path_writes_files` failed with "Missing required environment variables"
- **Issue:** The original credential assembly always called `config_from_env()` first, then overrode with flags. But when all four flags are explicitly supplied in tests (no env vars set), `config_from_env()` raised `OdooError`
- **Fix:** Added fast path: if all four credential flags are not None, construct `OdooClientConfig` directly without calling `config_from_env()`
- **Files modified:** `cli.py`
- **Commit:** 2236dba

**3. [Rule 1 - Bug] test_cli.py import/formatting issues**
- **Found during:** Task 3 full quality gate run
- **Issue:** ruff flagged unused `pytest` import (F401), `Path` not in `TYPE_CHECKING` block (TC003), and unsorted imports (I001)
- **Fix:** Removed `pytest`, moved `Path` to `TYPE_CHECKING` block, ran `ruff check --fix` for import ordering
- **Files modified:** `test_cli.py`
- **Commit:** 2236dba

## Known Stubs

None — all code paths fully wired. CLI connects Pydantic emitter from Plan 01 to a developer-facing entrypoint.

## Threat Flags

No new security-relevant surface beyond what was planned. All T-07-05 through T-07-09 mitigations implemented:
- T-07-05: `hide_input=True` on `--password`; `pretty_exceptions_show_locals=False` on Typer constructor; password never in `typer.echo()` or logger calls
- T-07-06: `Path(output).is_dir()` validated before any network connection
- T-07-07: `config_from_env()` error message names variable names (e.g., `ODOO_URL`) not values — echo verbatim is safe
- T-07-08: `fnmatch.fnmatch()` is stdlib pattern matching, no code execution surface
- T-07-09: `[project.scripts]` entry `"godoo.introspection.cli:app"` matches the actual file path

## Self-Check: PASSED

Files exist:
- `packages/godoo-introspection/src/godoo/introspection/cli.py` — FOUND
- `packages/godoo-introspection/tests/test_cli.py` — FOUND
- `packages/godoo-introspection/pyproject.toml` updated with pydantic/typer/scripts — CONFIRMED
- `uv.lock` regenerated — CONFIRMED

Commits exist: 699975c, e87758c, 2236dba — all in worktree-agent branch.
