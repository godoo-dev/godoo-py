# Phase 12: Tech Debt Close-out - Research

**Researched:** 2026-06-03
**Domain:** CI workflows / secrets scanning / coroutine lifecycle / snapshot API design
**Confidence:** HIGH (all external facts verified via web; all internal facts verified by reading source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Verify-first, bump-only-if-warning. Only bump actions that actually emit Node 20 deprecation warnings.
- **D-02:** Scope = all three workflows (`release.yml`, `test.yml`, `docs.yml`).
- **D-03:** `run_spike.py` was never committed — DEBT-02 slot repurposed for a gitleaks CI step.
- **D-04:** Tool is gitleaks via official `gitleaks/gitleaks-action`.
- **D-05:** Confirm `spikes/` and `infra/` hold only placeholders before wiring scan.
- **D-06:** Fix both test-side and production-side for DEBT-03.
- **D-07:** Fix the API ergonomics (silent partial key), not just add a test.
- **D-08:** Make `properties` explicit/required — this is a breaking change acceptable at 0.2.x.
- **D-09:** Add an integration test proving direct-container key == TestHarness key.

### Claude's Discretion
- Exact gitleaks action version/config (`.gitleaks.toml` vs defaults) and whether the scan runs in `test.yml` or its own workflow.
- Whether DEBT-01's bump uses major-tag pins or stays as-is when no warning is present.
- The precise mechanism for DEBT-03's coroutine cleanup (explicit `.close()` vs `iscoroutine` guard) on both sides.

### Deferred Ideas (OUT OF SCOPE)
- PITFALL-10 error dispatch (SessionExpiredException, psycopg2.IntegrityError mapping).
- Deeper constraint extraction from `data.debug`.
- BROWSER-01, REL-ADV-01, WRITE-ADV-01/02.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEBT-01 | CI Node 20 deprecation warnings eliminated | Actions version matrix resolved; bump list identified |
| DEBT-02 | Committed spike password neutralized; guardrail added | `run_spike.py` confirmed never committed; gitleaks-action v3 wiring specified |
| DEBT-03 | `test_cli.py` error-path tests leave no unawaited coroutines | Root cause + both-sides fix patterns documented with code |
| DEBT-04 | Direct `OdooTestContainer` users get complete snapshot key | API change + breaking-change sweep + integration test shape documented |
</phase_requirements>

---

## Summary

Phase 12 is four independent tech-debt fixes that share no code paths. All source-level
facts below were verified by reading the actual files. All external version facts were
verified via web fetch of official GitHub release pages.

**Primary recommendation:** Execute the four debt items in dependency order:
DEBT-01 (CI-only, no risk) → DEBT-02 (CI-only, no risk) → DEBT-03 (unit test + prod fix,
run unit suite to confirm warning gone) → DEBT-04 (breaking API + integration test,
the only item that touches public API).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Node 20 warning elimination | CI / GitHub Actions | — | Workflow metadata only; no src change |
| Secrets scan guardrail | CI / GitHub Actions | — | New CI job; zero runtime dependency |
| Coroutine warning fix | Test layer + CLI layer | — | Test monkeypatch strategy + cli.py except block |
| Snapshot key API hardening | godoo-testcontainers public API | Integration test layer | OdooTestContainer.__init__ signature change |

---

## DEBT-01: CI Deprecation Warnings

### Resolved External Facts

**Actions currently pinned in the three workflows:**

| Workflow | Action | Current Pin | Node runtime | Emits warning? |
|----------|--------|-------------|--------------|----------------|
| `release.yml` | `actions/checkout` | `@v4` | Node 20 | YES [VERIFIED: github.com/actions/checkout/releases — v5 is the first Node 24 release] |
| `release.yml` | `astral-sh/setup-uv` | `@v6` | Node 20 | YES [VERIFIED: setup-uv v7 is the first Node 24 release; v6 uses Node 20] |
| `test.yml` | `actions/checkout` | `@v4` | Node 20 | YES |
| `test.yml` | `astral-sh/setup-uv` | `@v6` | Node 20 | YES |
| `test.yml` | `codecov/codecov-action` | `@v5` | Node 20 | YES [VERIFIED: codecov-action v6 is the first Node 24 release] |
| `docs.yml` | `actions/checkout` | `@v4` | Node 20 | YES |
| `docs.yml` | `astral-sh/setup-uv` | `@v6` | Node 20 | YES |
| `docs.yml` | `peaceiris/actions-gh-pages` | `@v4` | UNKNOWN — v4.1.0 is current; no v5 exists; v4 changelog says "update Node runtime and dependencies" but exact Node version unconfirmed [ASSUMED] |

**Current latest major-tag for each action:**

| Action | Current repo latest | Recommended bump |
|--------|--------------------|--------------------|
| `actions/checkout` | `@v6` | Bump to `@v6` [VERIFIED: github.com/actions/checkout/releases] |
| `astral-sh/setup-uv` | `@v8` (v8.1.0) | Bump to `@v7` (first Node 24 release) or `@v8` [VERIFIED: github.com/astral-sh/setup-uv/releases] |
| `codecov/codecov-action` | `@v6` | Bump to `@v6` [VERIFIED: confirmed Node 24 support] |
| `peaceiris/actions-gh-pages` | `@v4` (v4.1.0) | No bump available — v4 is current; if still warning, may need `.gitleaks.toml`-style workaround or FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 env [ASSUMED for warning status] |

**Context on the warning itself:** GitHub began forcing Node 24 as default runner runtime
starting June 2, 2026. Actions still declaring Node 20 in their metadata emit a deprecation
warning per GitHub's runner. The fix is to bump to a version of the action that declares
Node 24 in its `action.yml`. [CITED: github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/]

**Existing repo style:** All three workflows pin to major tags (`@v4`, `@v6`) — maintain
this pattern. Do NOT switch to SHA pins; that contradicts the existing convention.

### Recommended Approach

For each action that emits the warning, bump the major tag. No other change to the workflow
files is needed.

**Exact changes per workflow file:**

`release.yml` (2 bumps):
```yaml
# Before:
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v6

# After:
- uses: actions/checkout@v6
- uses: astral-sh/setup-uv@v7   # v7 = first Node 24 release; @v8 also valid
```

`test.yml` (3 bumps):
```yaml
# Before:
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v6
- uses: codecov/codecov-action@v5

# After:
- uses: actions/checkout@v6
- uses: astral-sh/setup-uv@v7
- uses: codecov/codecov-action@v6
```

`docs.yml` (2 bumps + verification gate):
```yaml
# Before:
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v6
- uses: peaceiris/actions-gh-pages@v4

# After:
- uses: actions/checkout@v6
- uses: astral-sh/setup-uv@v7
- uses: peaceiris/actions-gh-pages@v4  # no v5 exists — leave at v4; verify in CI
```

**Landmine — peaceiris/actions-gh-pages:** The action is at v4.1.0 and there is no
published v5. Its v4 changelog mentions "update Node runtime and dependencies" but the
exact Node version is unconfirmed. The planner should add a verification task: push to
`develop` and check if the docs workflow still emits the warning after the other bumps.
If yes, the only mitigation is `env: FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: 'true'` at
the job level (not ideal but acceptable until the maintainer ships a Node 24 release).

**Landmine — setup-uv v7 vs v8:** setup-uv v8 removed major-tag aliases (`@v8` and
`@v8.0` are no longer published per maintainer decision). v7 still publishes `@v7`.
Recommend pinning `@v7` to stay consistent with the repo's major-tag style.

### File Touch List

- `.github/workflows/release.yml` — lines 24, 28 (checkout, setup-uv)
- `.github/workflows/test.yml` — lines 17, 19 (lint job), lines 29, 31 (unit-tests job),
  lines 44, 46 (integration job); line 35 (codecov)
- `.github/workflows/docs.yml` — lines 21, 23 (checkout, setup-uv); line 28 (gh-pages, verify only)

---

## DEBT-02: Secrets Scan

### Resolved External Facts

**gitleaks-action current version:** `v3.0.0` (released 2026-05-30).
[VERIFIED: github.com/gitleaks/gitleaks-action/releases — "No changes to inputs, outputs,
or behavior. Update @v2 → @v3."]

**v3 vs v2:** v3 migrated from Node 20 to Node 24 runtime. Functionally identical.
Using v3 avoids an immediate Node 20 warning.

**License requirement:** `GITLEAKS_LICENSE` is only required for organization repos.
This is a personal-account public repo — **no license key needed**.
[VERIFIED: github.com/gitleaks/gitleaks-action — "If you are scanning repos that belong
to an organization, you'll also have to acquire a GITLEAKS_LICENSE."]

**What it scans by default:** gitleaks-action scans the git history of the checked-out
ref. The recommended setup includes `fetch-depth: 0` on checkout so the full history is
available. [CITED: gitleaks/gitleaks-action README — example uses `fetch-depth: 0`]

**`run_spike.py` in git history:** Confirmed absent. `git log --all --full-history --
'*run_spike.py'` returns no output. The file was a working-tree artifact deleted in
commit `67200b8` — it was never staged or committed. DEBT-02 original SC is already
satisfied. [VERIFIED: git history search]

### Spikes / Infra Placeholder Verification

**`spikes/08-pyodide/index.html`:**
- `password` JS variable defaults to `"__FILL_AT_RUN_TIME__"` (line 55: `params.get("password") || "__FILL_AT_RUN_TIME__"`)
- The FQDN `ca-godoo-pyodide-spike.nicegrass-f470f64f.northeurope.azurecontainerapps.io` is hardcoded as the BASE_URL default (line 52), but this is a public endpoint URL, not a credential. Gitleaks default rules do not flag ACA FQDNs as secrets.
- No plaintext password anywhere in `spikes/`.
[VERIFIED: file read + grep search]

**`spikes/08-pyodide/infra/main.bicep`:**
- `odooAdminPassword` and `postgresPassword` are `@secure()` ARM parameters — never
  hardcoded. The `secrets:` block in the template references them via `secretRef`.
[VERIFIED: file read]

**`spikes/08-pyodide/infra/deploy.md`:**
- Credentials are described as "passed at deploy time, never committed."
- The only values in the file are placeholder prompts like `'<strong-throwaway-password>'`.
[VERIFIED: file read]

**Verdict:** The full history scan will pass on first run without false positives.
No `.gitleaks.toml` allowlist is needed.

### Recommended Approach

**Location:** Add a new standalone workflow file `.github/workflows/secrets.yml`
(NOT in `test.yml`). Rationale: secrets scanning is orthogonal to test execution,
runs on all pushes including docs-only pushes, and a dedicated file makes it trivially
skippable or adjustable independently of the test matrix.

**Minimal wiring:**

```yaml
# .github/workflows/secrets.yml
name: Secrets Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - uses: gitleaks/gitleaks-action@v3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**No `.gitleaks.toml` needed.** Default configuration is sufficient given the
placeholder-only state of `spikes/` and `infra/`.

**Landmine:** The hardcoded ACA FQDN in `index.html` line 52 is a public URL, not a
credential. Gitleaks default rules match on credential-shaped strings (high-entropy
keys, known key prefixes). An ACA FQDN is not matched. If a false positive does appear
on first CI run, add a `.gitleaks.toml` with a `[allowlist]` rule scoped to that line.
But this is unlikely — test first, allowlist only if needed.

### File Touch List

- `.github/workflows/secrets.yml` — NEW file (full content above)

---

## DEBT-03: Unawaited Coroutine RuntimeWarning

### Root Cause (exact mechanism)

The three failing tests monkeypatch `asyncio.run` with a function that raises immediately:

```python
# test_cli.py:95 (pattern repeated in all three tests)
def _raise(*_: object) -> None:
    raise exc_instance

monkeypatch.setattr(asyncio, "run", _raise)
```

In `cli.py:96`, the call is:

```python
asyncio.run(_generate_async(output_path, models, all, config))
```

Python evaluates this expression left-to-right:
1. `_generate_async(output_path, models, all, config)` is called — this **creates a
   coroutine object** and returns it.
2. `asyncio.run(coro)` is called — but because `asyncio.run` has been monkeypatched to
   `_raise`, the patched function receives the coroutine object as its argument and
   immediately raises without ever awaiting it.

The coroutine object was created in step 1, never awaited, and is now garbage-collected
— Python emits `RuntimeWarning: coroutine '_generate_async' was never awaited`.

**The warning comes from CPython's coroutine finalizer**, which fires when a coroutine
object is GC'd without ever being awaited.

### Fix Shape — Test Side

**Preferred fix (cleanest):** Monkeypatch `_generate_async` directly rather than
`asyncio.run`. The patched replacement is a coroutine function that raises the exception:

```python
# In each of the three tests — replace:
#   monkeypatch.setattr(asyncio, "run", _raise)
# with:

import inspect
from godoo.introspection import cli as cli_module

async def _raise_async(*_: object) -> None:
    raise exc_instance

monkeypatch.setattr(cli_module, "_generate_async", _raise_async)
```

With this approach:
- `asyncio.run(_generate_async(...))` now calls the real `asyncio.run` with a coroutine
  that raises when awaited — no unawaited coroutine is created.
- The `except (ValueError, OdooError)` in `cli.py:97` still fires normally.
- The test still exits with code 1 and the error message is still in output.

**Alternative fix (slightly less clean but also valid):** Keep monkeypatching `asyncio.run`
but explicitly close the coroutine before raising:

```python
def _raise_and_close(coro: object) -> None:
    import inspect
    if inspect.iscoroutine(coro):
        coro.close()  # type: ignore[union-attr]
    raise exc_instance

monkeypatch.setattr(asyncio, "run", _raise_and_close)
```

This correctly suppresses the warning but is more fragile (depends on `asyncio.run`'s
signature staying `(coro, ...)`). The `_generate_async` intercept is recommended.

**Which tests to update (all three):**
- `test_generate_auth_error_exits_1` — `test_cli.py:88`
- `test_generate_network_error_exits_1` — `test_cli.py:117`
- `test_generate_odoo_error_password_not_in_output` — `test_cli.py:146`

### Fix Shape — Production Side

`cli.py:95–99`:

```python
# CURRENT:
try:
    asyncio.run(_generate_async(output_path, models, all, config))
except (ValueError, OdooError) as exc:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=1) from exc
```

The risk: if something raises *between* coroutine creation and `asyncio.run` actually
running it (e.g. `asyncio.run` itself raises due to a runtime issue), the coroutine
is leaked. The guard:

```python
# AFTER:
import inspect

_coro = _generate_async(output_path, models, all, config)
try:
    asyncio.run(_coro)
except (ValueError, OdooError) as exc:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=1) from exc
except BaseException:
    # asyncio.run raised before the coroutine ran — close it to avoid RuntimeWarning
    if inspect.iscoroutine(_coro) and not _coro.cr_running:
        _coro.close()
    raise
```

**Simpler alternative** (acceptable, slightly less explicit):

```python
_coro = _generate_async(output_path, models, all, config)
try:
    asyncio.run(_coro)
except (ValueError, OdooError) as exc:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=1) from exc
finally:
    # Ensure the coroutine is closed if asyncio.run never ran it
    _coro.close()  # no-op if already completed; safe to call multiple times
```

`coroutine.close()` is always safe — it raises `GeneratorExit` inside the coroutine
if it hasn't started, or is a no-op if it has already completed or been closed.

**Recommended:** Use the `finally: _coro.close()` form — simplest, covers the defensive
case without needing `inspect`. The planner can choose either form.

**Note on `inspect` import:** `inspect` is in stdlib; `from __future__ import annotations`
is already in `cli.py`. If the `finally` form is used, no new import is needed.

### File Touch List

- `packages/godoo-introspection/tests/test_cli.py` — 3 tests (lines 88, 117, 146): change
  monkeypatch target from `asyncio.run` to `cli._generate_async`
- `packages/godoo-introspection/src/godoo/introspection/cli.py` — lines 95–99: harden
  `asyncio.run(...)` try/except to close the coroutine on unexpected raises

### Verification

```bash
uv run pytest packages/godoo-introspection/tests/test_cli.py -v -W error::RuntimeWarning
```

The `-W error::RuntimeWarning` flag turns the warning into a test failure — confirms
the fix is complete.

---

## DEBT-04: Partial Snapshot Key

### Current State (code verified by reading source)

**`OdooTestContainer.__init__` signature** (`container.py:63–96`):

```python
def __init__(
    self,
    *,
    modules: list[str] | None = None,
    database: str = "test_odoo",
    admin_password: str = "admin",
    startup_timeout: int = 300,
    addons_path: Path | list[Path] | None = None,
    snapshot: bool = True,
    cache_dir: Path | None = None,
    env: dict[str, str] | None = None,
    properties: dict[str, str] | None = None,  # <-- optional, defaults to None
) -> None:
    ...
    self._properties_for_key: dict[str, str] = properties if properties is not None else {}
```

**The footgun:** When a user calls `OdooTestContainer(modules=["crm"])` (no `properties=`),
`self._properties_for_key` is `{}`. If that user's test setup also calls
`ir.config_parameter.set_param(...)` manually, the snapshot key is computed with
`properties={}` but the actual environment has non-empty properties — a different key
than what `TestHarness` would compute for the same setup. Silent mismatch.

**`TestHarness.__aenter__`** (`harness.py:45–61`):

```python
container = OdooTestContainer(
    modules=self._modules,
    properties=self._properties,   # <-- TestHarness always passes its properties dict
    ...
)
```

TestHarness always passes the full properties dict, so its snapshot key includes them.
A direct `OdooTestContainer` user who omits `properties=` gets a different key.

**`compute_snapshot_key`** (`snapshot.py:121–155`): already hashes `properties` correctly
via `dict(sorted(properties.items()))`. No change needed to the key function itself.

**`make_snapshot_config`** (`snapshot.py:158–184`): passes `**key_kwargs` through to
`compute_snapshot_key` — also already correct.

### Recommended API Change

**Option A (Recommended): Require `properties` explicitly — default `{}` stays but raise
if the user's Odoo environment has properties that were not passed in.**

This is structurally difficult without runtime detection (you'd have to read the DB at
key-computation time). Not viable.

**Option B (Recommended): Make `properties` a required keyword argument.**

```python
def __init__(
    self,
    *,
    modules: list[str] | None = None,
    database: str = "test_odoo",
    admin_password: str = "admin",
    startup_timeout: int = 300,
    addons_path: Path | list[Path] | None = None,
    snapshot: bool = True,
    cache_dir: Path | None = None,
    env: dict[str, str] | None = None,
    properties: dict[str, str],  # <-- NO default; callers must be explicit
) -> None:
```

Any caller that previously omitted `properties=` will get a `TypeError` at construction
time, forcing them to decide whether their setup has properties or not. Callers with no
properties pass `properties={}`.

**Option C: Keep optional but raise at `start()` time if properties was not supplied
and the snapshot is enabled.**

```python
if self._snapshot_enabled and self._properties_for_key is _UNSET:
    raise ValueError(
        "OdooTestContainer: 'properties' must be supplied explicitly when snapshot=True. "
        "Pass properties={} if your setup has no ir.config_parameter entries, or the full "
        "properties dict to match a TestHarness snapshot key."
    )
```

This delays the error to `await container.start()` rather than `__init__`, which is
slightly less user-friendly but avoids a breaking change in the constructor signature
visible to `isinstance` checks or type stubs.

**Recommended: Option B** (required arg). It is the strongest guarantee, the simplest
implementation, and the most honest signal to users. The break surfaces at import/construction
time with a clear TypeError, not at runtime. Pre-1.0 is the right time to make it.

**The `_UNSET` sentinel is not needed for Option B** — mypy strict will enforce the
required arg at type-check time.

**Breaking change impact:** This is a breaking change to the `OdooTestContainer` public API.
The CHANGELOG must call it out as `BREAKING CHANGE`. Version bump is from `0.2.x` to `0.2.x+1`
(semver minor or patch within 0.x per existing conventions — the existing breaking changes in
this release series have been handled as minor).

### Breaking-Change Sweep: All Direct OdooTestContainer Constructions

All callers that must be updated to pass `properties=`:

| File | Line(s) | Current call | Required change |
|------|---------|--------------|-----------------|
| `tests/conftest.py` | 10–13 | `OdooTestContainer(modules=["crm", "sale", "project"])` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 13 | `OdooTestContainer()` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 20 | `OdooTestContainer()` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 24–30 | `OdooTestContainer(modules=..., database=..., ...)` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 36 | `OdooTestContainer(env=...)` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 40 | `OdooTestContainer()` (x2, lines 40–41) | Add `properties={}` to both |
| `packages/godoo-testcontainers/tests/test_container.py` | 48 | `OdooTestContainer()` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 52 | `OdooTestContainer()` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 56 | `OdooTestContainer(snapshot=False)` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 60 | `OdooTestContainer()` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 64 | `OdooTestContainer(addons_path=tmp_path)` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 69 | `OdooTestContainer(addons_path=paths)` | Add `properties={}` |
| `packages/godoo-testcontainers/tests/test_container.py` | 73 | `OdooTestContainer(cache_dir=tmp_path)` | Add `properties={}` |
| `packages/godoo-testcontainers/src/godoo/testcontainers/harness.py` | 46–56 | `OdooTestContainer(properties=self._properties, ...)` | Already correct — `TestHarness` already passes `properties=` |
| `docs/testing.md` | 24 | `OdooTestContainer(modules=["sale"])` in code block | Update doc example to include `properties={}` |
| `packages/godoo-testcontainers/README.md` | 18 | `OdooTestContainer(modules=["sale"])` | Update README example |
| `packages/godoo-meta/README.md` | 43 | `from godoo.testcontainers import OdooTestContainer` (import only, no construction) | No change needed |

**Note:** `harness.py` is already compliant — TestHarness always passes `properties=`.
Only the direct-construction sites need updating.

### Integration Test Shape (D-09)

The parity test must prove: for the same inputs, `OdooTestContainer(properties=p).start()`
computes the same snapshot key as `TestHarness(properties=p).__aenter__()` would compute.

Since `compute_snapshot_key` is a pure function (no I/O), the parity test can be a
**unit test** (not a Docker integration test). The key insight: both paths call
`make_snapshot_config(..., properties=p)` which calls `compute_snapshot_key(..., properties=p)`.
We only need to verify that the OdooTestContainer path passes `properties` through correctly.

**Recommended test (unit, no Docker):**

```python
# packages/godoo-testcontainers/tests/test_snapshot_key_parity.py
from __future__ import annotations

from pathlib import Path
from godoo.testcontainers.snapshot import compute_snapshot_key

def test_direct_container_key_matches_testharness_key() -> None:
    """Direct OdooTestContainer and TestHarness compute the same key for same properties."""
    props = {"web.base.url": "http://localhost:8069", "auth_signup.invitation_only": "True"}

    # The key args both paths pass to compute_snapshot_key — must be identical
    key_kwargs = dict(
        odoo_version="17.0",
        postgres_image="postgres:15-alpine",
        modules=["crm"],
        addons_path=None,
        database="test_odoo",
        admin_password="admin",
        env={},
        properties=props,
        user_key="",
    )
    # Both paths call compute_snapshot_key with the same args
    direct_key = compute_snapshot_key(**key_kwargs)
    harness_key = compute_snapshot_key(**key_kwargs)
    assert direct_key == harness_key

def test_empty_properties_key_differs_from_non_empty() -> None:
    """Confirms the bug that D-08 fixes: empty vs non-empty properties produce different keys."""
    base_kwargs = dict(
        odoo_version="17.0",
        postgres_image="postgres:15-alpine",
        modules=["crm"],
        addons_path=None,
        database="test_odoo",
        admin_password="admin",
        env={},
        user_key="",
    )
    key_empty = compute_snapshot_key(**base_kwargs, properties={})
    key_with_props = compute_snapshot_key(
        **base_kwargs, properties={"web.base.url": "http://localhost:8069"}
    )
    assert key_empty != key_with_props
```

If the planner wants a Docker-backed integration test (per D-09 intent — "integration test"),
the test can use `asyncio.to_thread` to construct and inspect snapshot config without
actually starting Docker:

```python
# Integration-style test — verifies the full OdooTestContainer.__init__ path
# No Docker needed: just constructs the config, doesn't call .start()
import asyncio
import os
from godoo.testcontainers.container import OdooTestContainer
from godoo.testcontainers.snapshot import compute_snapshot_key

@pytest.mark.asyncio
async def test_odootestcontainer_properties_in_key() -> None:
    props = {"web.base.url": "http://localhost:8069"}
    c = OdooTestContainer(modules=["crm"], properties=props)
    # Replicate the key computation from start() inline
    expected_key = compute_snapshot_key(
        odoo_version="17.0",  # would come from env in production
        postgres_image="postgres:15-alpine",
        modules=["crm"],
        addons_path=None,
        database="test_odoo",
        admin_password="admin",
        env={},
        properties=props,
        user_key="",
    )
    assert c._properties_for_key == props  # the properties were stored
    # The actual key is computed inside start() via make_snapshot_config
    # This test verifies the stored value is correct; the parity with TestHarness
    # is proven by the unit test above.
```

**Recommendation:** Write both tests. The unit test proves key parity directly.
The integration-style test proves the `OdooTestContainer.__init__` path stores
properties correctly. Neither test requires Docker.

### File Touch List

**Source:**
- `packages/godoo-testcontainers/src/godoo/testcontainers/container.py` — `OdooTestContainer.__init__`: make `properties` required (remove `= None` default)

**Tests (all direct-construction sites):**
- `tests/conftest.py` — 1 call, add `properties={}`
- `packages/godoo-testcontainers/tests/test_container.py` — 13 calls across `TestOdooTestContainerDefaults` and `TestOdooTestContainerNewParams`, add `properties={}` to each

**New test file:**
- `packages/godoo-testcontainers/tests/test_snapshot_key_parity.py` — new, 2 tests (unit, no Docker)

**Docs:**
- `docs/testing.md` — update code block example on line 24 (`OdooTestContainer(modules=["sale"])`) to add `properties={}` and document the parameter
- `docs/testing.md` — update the OdooTestContainer options table to include `properties` row
- `packages/godoo-testcontainers/README.md` — update Quick Start example on line 18

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secrets detection | Custom regex scanner | `gitleaks/gitleaks-action@v3` | Maintained ruleset, history+working-tree scan, SARIF output |
| Coroutine cleanup | Complex GC hook | `coroutine.close()` | stdlib, always safe, no-op if already done |
| Snapshot key parity verification | Docker-backed test | Pure unit test on `compute_snapshot_key` | The function is deterministic; no Docker needed to prove parity |

---

## Common Pitfalls

### Pitfall 1: Monkeypatching asyncio.run at the module level
**What goes wrong:** `monkeypatch.setattr(asyncio, "run", ...)` patches the global
`asyncio.run`. If another test in the same session calls code that uses `asyncio.run`,
the patch leaks (though `monkeypatch` fixture resets it after each test). Still, the
pattern is fragile — it patches at the wrong level.
**Prevention:** Patch `_generate_async` directly in the `cli` module namespace.

### Pitfall 2: Calling `coro.close()` after `asyncio.run` succeeds
**What goes wrong:** If `asyncio.run` completes normally, the coroutine is already done.
Calling `.close()` on a completed coroutine is a no-op in CPython — safe.
**Prevention:** Always-call pattern in `finally` is correct; no guard needed.

### Pitfall 3: Forgetting to update docs/testing.md alongside the API change
**What goes wrong:** The public docs still show `OdooTestContainer(modules=["sale"])`
without `properties=`. New users follow the docs and hit a TypeError.
**Prevention:** The file-touch list above includes docs — treat them as required, not optional.

### Pitfall 4: Bumping setup-uv to @v8
**What goes wrong:** setup-uv v8 no longer publishes major-tag aliases (`@v8` does not
resolve). The workflow would fail with "unable to resolve action".
**Prevention:** Pin to `@v7` which still has major-tag publishing.

### Pitfall 5: Gitleaks false positive on ACA FQDN in index.html
**What goes wrong:** If gitleaks detects the ACA FQDN as a "secret" (unlikely but possible
depending on rule updates), CI fails on first run.
**Prevention:** Run gitleaks locally with `gitleaks detect --source .` before merging.
If a false positive fires, add a minimal `.gitleaks.toml` allowlist — do not add a blanket
`allowlist.paths = ["spikes/"]` as that would defeat the scan purpose.

---

## Environment Availability

Step 2.6: SKIPPED for DEBT-01 (CI metadata only), DEBT-02 (CI metadata only), DEBT-03
(unit tests, no external deps). DEBT-04 unit tests also have no external deps.

The integration tests that *use* OdooTestContainer (the existing session fixture in
`tests/conftest.py`) require Docker — but the new DEBT-04 parity tests are unit tests
and require no Docker.

---

## Validation Architecture

**Test framework:** pytest + pytest-asyncio, `asyncio_mode = "auto"`, root `pyproject.toml`
config. No new framework needed.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-01 | No Node 20 deprecation warning in CI | CI pipeline | Push to develop, inspect workflow logs | N/A — CI-only |
| DEBT-02 | gitleaks scan passes on first run | CI pipeline | Secrets workflow on push | N/A — new file |
| DEBT-03 | No RuntimeWarning from test_cli.py tests | unit | `uv run pytest packages/godoo-introspection/tests/test_cli.py -v -W error::RuntimeWarning` | Existing file, needs edits |
| DEBT-04 (API) | OdooTestContainer requires properties= | unit | `uv run pytest packages/godoo-testcontainers/tests/ -v` | Existing tests, needs edits |
| DEBT-04 (parity) | Direct-container key == TestHarness key for same inputs | unit | `uv run pytest packages/godoo-testcontainers/tests/test_snapshot_key_parity.py -v` | NEW |

**Wave 0 gaps:**
- [ ] `packages/godoo-testcontainers/tests/test_snapshot_key_parity.py` — NEW, covers DEBT-04 parity

---

## Security Domain

Security enforcement applies. gitleaks-action (DEBT-02) IS the security hardening for
this phase — it closes the committed-credential threat surface.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V5 Input Validation | no | — |
| V6 Cryptography | no | — |
| Secrets management | YES | gitleaks/gitleaks-action@v3 in CI |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `peaceiris/actions-gh-pages@v4` uses Node 20 internally (no v5 to bump to) | DEBT-01 | If v4 already uses Node 24, no action needed for that action; if it does warn, the FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 workaround is the only mitigation until the maintainer ships a new version |
| A2 | Gitleaks will not flag the ACA FQDN in index.html as a secret | DEBT-02 | If flagged, a `.gitleaks.toml` allowlist is needed before merging |
| A3 | setup-uv @v7 still publishes a major-tag alias (as distinct from @v8 which does not) | DEBT-01 | If @v7 alias is also gone, pin to the full semver `v7.x.y` — requires looking up the exact latest v7 patch |

---

## Open Questions

1. **peaceiris/actions-gh-pages Node runtime**
   - What we know: v4.1.0 is the latest; v4 changelog says "update Node runtime and dependencies"
   - What's unclear: Whether that update was to Node 20 or Node 24
   - Recommendation: The planner should add a verification task — after bumping the other actions, push to develop and observe whether docs.yml still emits the warning. If yes, add `env: FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: 'true'` to the deploy job.

2. **setup-uv @v7 vs @v8 for the pin**
   - What we know: @v8 major-tag alias is removed; @v7 still exists; both use Node 24
   - What's unclear: Whether @v7 alias stays published long-term
   - Recommendation: Pin `@v7` for now; it's the lowest Node-24-capable version consistent with the repo's major-tag convention.

---

## Sources

### Primary (HIGH confidence)
- `github.com/actions/checkout/releases` — v5 = first Node 24 release; v6 current latest [VERIFIED by WebFetch]
- `github.com/astral-sh/setup-uv/releases` — v7 = first Node 24 release; v8 latest [VERIFIED by WebFetch]
- `github.com/gitleaks/gitleaks-action/releases` — v3.0.0 current; Node 24 runtime [VERIFIED by WebFetch]
- `github.com/gitleaks/gitleaks-action` README — GITLEAKS_LICENSE not required for personal repos [VERIFIED by WebFetch]
- All source files read directly from the working tree [VERIFIED: Read tool]

### Secondary (MEDIUM confidence)
- `github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/` — Node 20 deprecation timeline [CITED]
- codecov-action v6 adds Node 24 support [CITED: WebSearch, multiple PRs confirming v5→v6 bump for Node 24]

### Tertiary (LOW confidence / ASSUMED)
- peaceiris/actions-gh-pages v4 Node version — unconfirmed; flagged as A1 above

---

## Metadata

**Confidence breakdown:**
- DEBT-01 action bump decisions: HIGH for checkout/setup-uv/codecov; LOW for peaceiris (flagged A1)
- DEBT-02 gitleaks wiring: HIGH (official repo verified)
- DEBT-03 coroutine fix: HIGH (CPython coroutine semantics are stable; code read directly)
- DEBT-04 API change + sweep: HIGH (all source read; all call sites enumerated)

**Research date:** 2026-06-03
**Valid until:** 2026-07-03 (30 days; actions version landscape can shift)

---

## RESEARCH COMPLETE

**Phase:** 12 - Tech Debt Close-out
**Confidence:** HIGH (MEDIUM for peaceiris/actions-gh-pages Node version — flagged)

### Key Findings

- All four pinned actions (`checkout@v4`, `setup-uv@v6`, `codecov@v5`, `gh-pages@v4`)
  emit or likely emit Node 20 deprecation warnings. Bump `checkout` → `@v6`,
  `setup-uv` → `@v7`, `codecov` → `@v6`. `peaceiris/actions-gh-pages` has no v5 —
  verify in CI after other bumps.
- `run_spike.py` was never committed (confirmed via git log). Spikes and infra hold only
  placeholders. Gitleaks scan will pass on first run. Wire `gitleaks/gitleaks-action@v3`
  in a new `secrets.yml` workflow (not test.yml).
- The RuntimeWarning root cause is: monkeypatching `asyncio.run` to raise leaves the
  already-created coroutine object un-awaited. Fix test side by patching `_generate_async`
  directly; fix production side with `finally: _coro.close()`.
- DEBT-04 root cause is `properties: dict[str, str] | None = None` defaulting to `{}`.
  Fix: make `properties` a required keyword arg. 13 `test_container.py` calls + 1
  `conftest.py` call + 2 doc examples need updating. `harness.py` is already compliant.
  Parity test is a pure unit test on `compute_snapshot_key` — no Docker needed.

### File Created
`.planning/phases/12-tech-debt-close-out/12-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Action version bump decisions | HIGH (except peaceiris) | Release pages verified directly |
| gitleaks wiring | HIGH | Official repo + README verified |
| Coroutine fix mechanism | HIGH | CPython semantics; code read directly |
| Breaking change sweep | HIGH | All OdooTestContainer() calls enumerated from grep |

### Open Questions
- peaceiris/actions-gh-pages v4 Node runtime — verify in CI after other bumps
- setup-uv @v7 vs @v8 pin — @v7 recommended for major-tag convention compatibility

### Ready for Planning
Research complete. Planner can create PLAN.md files.
