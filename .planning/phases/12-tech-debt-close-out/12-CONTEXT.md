# Phase 12: Tech Debt Close-out - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Four independent tech-debt fixes that close out the v1.2 milestone. Each lives in a
separate file and can be done in any order:

- **DEBT-01** — CI workflows are warning-free (no Node 20 deprecation noise).
- **DEBT-02** — no committed plaintext spike password (and a guardrail so it can't recur).
- **DEBT-03** — `test_cli.py` error-path tests leave no unawaited-coroutine `RuntimeWarning`.
- **DEBT-04** — direct `OdooTestContainer` users get a snapshot key that completely and
  correctly reflects their `properties` (no silent partial key).

**Scope anchor:** clarify-and-close. The codebase scout found DEBT-02 and DEBT-04 are
*partly or wholly already satisfied at the code level* — this phase verifies that, fixes
the remaining real gaps, and hardens against recurrence. It does NOT add new capabilities
beyond the four debt items.

</domain>

<decisions>
## Implementation Decisions

### DEBT-01 — CI deprecation warnings
- **D-01:** **Verify-first, bump-only-if-warning.** Researcher/planner confirms whether the
  currently-pinned actions (`actions/checkout@v4`, `astral-sh/setup-uv@v6`,
  `codecov/codecov-action@v5`, `peaceiris/actions-gh-pages@v4`) still emit Node 20
  deprecation warnings on current GitHub runners. Bump **only** the actions that actually
  warn. Do not bump-for-the-sake-of-it.
- **D-02:** **Scope = all three workflows** (`release.yml`, `test.yml`, `docs.yml`) for
  consistency — not just `release.yml`. The SC names `release.yml` but the same actions
  appear across all three; fixing one and leaving the others warning is incoherent.

### DEBT-02 — committed spike password
- **D-03:** **Repurpose the slot into a durable guardrail.** The file (`run_spike.py`) was
  never committed — it was a working-tree artifact deleted in commit `67200b8` (Phase 8),
  so SC-2 ("no committed plaintext password") is already trivially satisfied. Instead of a
  no-op, **add a `gitleaks` secrets-scan step to CI** so a committed credential can never
  recur.
- **D-04:** Tool is **gitleaks** (official `gitleaks/gitleaks-action`), chosen for speed,
  history+working-tree scanning, and good public-repo fit.
- **D-05:** Before wiring the scan, **confirm `spikes/` and `infra/` hold only placeholders**
  (`THROWAWAY`, `__FILL_AT_RUN_TIME__`, deploy-time refs) so the new scan passes on first
  run. Record in the plan that DEBT-02's original SC was already met by `67200b8`.

### DEBT-03 — unawaited coroutine RuntimeWarning
- **D-06:** **Fix both sides (belt-and-suspenders).**
  - **Test-side:** the 3 failing tests (`test_generate_auth_error_exits_1`,
    `test_generate_network_error_exits_1`, `test_generate_odoo_error_password_not_in_output`)
    should stop monkeypatching `asyncio.run` to raise; intercept `_generate_async` itself
    (or close the created coroutine) so no coroutine is left un-awaited.
  - **Production-side:** harden `cli.py` so its `except` handler around
    `asyncio.run(_generate_async(...))` (`cli.py:96`) is robust to the
    `asyncio.run`-raises-before-running scenario (e.g. close the coroutine if still
    un-awaited). Shipping code should not depend on the test's monkeypatch shape.

### DEBT-04 — partial snapshot key for direct container users
- **D-07:** **Fix the API ergonomics, not just add a test.** Root issue is a *silent
  mismatch*: a direct `OdooTestContainer` user whose setup has properties but who omits
  `properties=` gets an empty-properties snapshot key that won't match their actual setup.
- **D-08:** **Make `properties` explicit / required** so the partial-key footgun is
  structurally impossible — either make the arg required, or raise when a properties-bearing
  setup is detected without an explicit `properties=`. ⚠ **This is a breaking change for
  direct `OdooTestContainer` users.** Acceptable at 0.2.x (pre-1.0), but the planner MUST
  call it out as breaking and update any in-repo callers + docs accordingly.
- **D-09:** **Add an integration test** proving a direct `OdooTestContainer` user with
  properties produces the **same** snapshot key as a `TestHarness` user with the same
  properties — the parity guarantee in SC-4. (Per `feedback-automate-dont-punt-to-uat`:
  automate this, don't punt to manual UAT.)

### Claude's Discretion
- Exact gitleaks action version/config (`.gitleaks.toml` vs defaults), and whether the scan
  runs in `test.yml` or its own workflow — planner/researcher decides.
- Whether DEBT-01's bump uses major-tag pins (current style) or stays as-is when no warning
  is present.
- The precise mechanism for DEBT-03's coroutine cleanup (explicit `.close()` vs
  `iscoroutine` guard) on both sides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` — Phase 12 "Tech Debt Close-out" goal, success criteria, DEBT-01..04 mapping.
- `.planning/REQUIREMENTS.md` — DEBT-01, DEBT-02, DEBT-03, DEBT-04 requirement text.

### DEBT-01 (CI)
- `.github/workflows/release.yml` — primary SC target.
- `.github/workflows/test.yml`, `.github/workflows/docs.yml` — in scope per D-02.

### DEBT-02 (secrets)
- `spikes/08-pyodide/` — placeholder strings only; verify before scan.
- `infra/main.bicep`, `infra/deploy.md` — deploy-time credential refs; verify clean.
- Git commit `67200b8` (chore(08)) — documents that `run_spike.py` was never committed.

### DEBT-03 (test warning)
- `packages/godoo-introspection/src/godoo/introspection/cli.py` (~line 96) — `asyncio.run(_generate_async(...))` in try/except.
- `packages/godoo-introspection/tests/test_cli.py` — the 3 error-path tests monkeypatching `asyncio.run`.

### DEBT-04 (snapshot key)
- `packages/godoo-testcontainers/src/godoo_testcontainers/snapshot.py` (~lines 121, 152) — `compute_snapshot_key()` hashing `properties`.
- `packages/godoo-testcontainers/src/godoo_testcontainers/container.py` (~lines 76, 85-96, 141) — `OdooTestContainer` `_properties_for_key` / `make_snapshot_config` flow; `TestHarness` comparison.

### Conventions
- `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md` — house style for the fixes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `compute_snapshot_key(properties=...)` already exists and hashes properties — DEBT-04 is
  a guard/API change around an existing, working hash, not a rewrite.
- `TestHarness` already passes its full properties dict into the key — it's the reference
  behavior the direct-container path must match.

### Established Patterns
- Testcontainers calls are sync, wrapped in `asyncio.to_thread()` — DEBT-04 test must follow.
- CI workflows already pin actions to major tags (`@v4`, `@v6`) — DEBT-01 stays in that style.
- `ruff` + `mypy --strict` quality gate, no new runtime deps — gitleaks is CI-only (dev/CI),
  not a package dependency.

### Integration Points
- DEBT-02 secrets-scan is a new CI step/job — connects only to `.github/workflows/`, no src.
- DEBT-04 breaking change touches `OdooTestContainer.__init__`/`.start()` and any in-repo
  callers (tests, conftest) — sweep for direct constructions.

</code_context>

<specifics>
## Specific Ideas

- DEBT-02 scanner: **gitleaks** specifically (official GitHub Action), not trufflehog.
- DEBT-04 preferred shape: make `properties` **required/explicit** (strongest guarantee),
  accepting the breaking change at 0.2.x rather than a soft warning.
- DEBT-03: fix **both** the tests and `cli.py`, not one or the other.

</specifics>

<deferred>
## Deferred Ideas

Carried from prior phases' `<deferred>` sections — **not** in scope for Phase 12, recorded
so they aren't lost:

- **PITFALL-10 error dispatch (from 09-CONTEXT):** extend `transport.py` `_categorize_error`
  to map `SessionExpiredException` → `OdooAuthError` and `psycopg2.IntegrityError` →
  `OdooValidationError`. Requires touching `transport.py`; its own follow-up phase.
- **Deeper constraint extraction from `data.debug` (from 09-CONTEXT):** pull constraint
  names from stripped traceback. Deferred to avoid coupling parsing to stripped content.
- **Future requirements (REQUIREMENTS.md):** BROWSER-01 (`godoo[browser]` / Pyodide),
  REL-ADV-01 (arbitrary-depth relation nesting), WRITE-ADV-01/02 (x2many + nested typed
  writes). All post-v1.2.

None of these are folded into Phase 12 — discussion stayed within the four-debt-item scope.

</deferred>

---

*Phase: 12-tech-debt-close-out*
*Context gathered: 2026-06-03*
