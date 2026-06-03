# Phase 12: Tech Debt Close-out - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 12-tech-debt-close-out
**Areas discussed:** DEBT-01 approach, DEBT-02 disposition, DEBT-03 fix strategy, DEBT-04 disposition

---

## DEBT-02 disposition (committed spike password)

Codebase scout finding: `run_spike.py` was **never committed** (deleted as a working-tree
artifact in commit `67200b8`), so SC-2 is already trivially satisfied.

| Option | Description | Selected |
|--------|-------------|----------|
| Add a secrets-scan CI step | Repurpose the work: add a gitleaks/trufflehog scan step so a committed credential can never recur | ✓ |
| Close as done-with-note | Verify spikes/ holds only placeholders, note DEBT-02 satisfied by 67200b8, ship nothing | |
| Audit spikes/ then close | Grep spikes/ + infra/ for real creds, then close. No new CI | |

**User's choice:** Add a secrets-scan CI step.
**Notes:** Turn a no-op into a durable guardrail. Scanner = **gitleaks** (see follow-up).

---

## DEBT-04 disposition (partial snapshot key)

Codebase scout finding: `compute_snapshot_key()` already hashes `properties`, and
`OdooTestContainer` already passes `_properties_for_key` through — looks already implemented.

| Option | Description | Selected |
|--------|-------------|----------|
| Verify + integration test only | Genuinely done in code; add a parity test and close. No production change | |
| Fix API ergonomics too | Real gap is silent mismatch when `properties=` omitted; add guard/warning + test | ✓ |
| Treat as not-done, investigate | Flag a missing code path for the researcher | |

**User's choice:** Fix API ergonomics too.
**Notes:** Follow-up nailed the behavior: **require explicit `properties`** (breaking change,
acceptable at 0.2.x), plus an integration test proving direct-container ⟺ TestHarness key parity.

---

## DEBT-03 fix strategy (unawaited coroutine RuntimeWarning)

Confirmed live: 3 tests monkeypatch `asyncio.run` to raise, leaving `_generate_async`
never awaited → `RuntimeWarning`.

| Option | Description | Selected |
|--------|-------------|----------|
| Test-side fix | Monkeypatch `_generate_async` / close the coroutine; production untouched | |
| Production-side fix | Make cli.py close the coroutine in its except handler | |
| Both | Fix the tests AND harden cli.py | ✓ |

**User's choice:** Both.
**Notes:** Belt-and-suspenders — tests stop leaking the coroutine, and shipping code is
robust to the asyncio.run-raises scenario independent of test shape.

---

## DEBT-01 approach (CI deprecation warnings)

Actions already on recent majors (`checkout@v4`, `setup-uv@v6`, etc.).

| Option | Description | Selected |
|--------|-------------|----------|
| Verify, bump only if warnings | Confirm whether current versions still warn; bump only what warns; all 3 workflows | ✓ |
| SHA-pin all actions (hardening) | Pin every action to a commit SHA across all 3 workflows regardless of warnings | |
| release.yml only, minimal | Touch only release.yml, clear just its warnings | |

**User's choice:** Verify, bump only if warnings.
**Notes:** Scope = all three workflows (release/test/docs) for consistency. No
bump-for-the-sake-of-it; SHA-pinning hardening explicitly not chosen.

---

## Follow-up decisions

**DEBT-04 behavior:** Require explicit `properties` (vs warn-on-omission / auto-derive).
Strongest guarantee; breaking API change for direct users, flagged for the planner.

**Secrets scanner:** gitleaks (vs trufflehog / let-researcher-pick). Official GitHub Action,
fast, history + working-tree scanning, good public-repo fit.

## Claude's Discretion

- Exact gitleaks action version/config and which workflow hosts the scan.
- DEBT-01 pin style when no warning present.
- DEBT-03 coroutine-cleanup mechanism on both sides.

## Deferred Ideas

Carried (not in scope): PITFALL-10 error dispatch (transport.py), deeper `data.debug`
constraint extraction, and post-v1.2 future requirements (BROWSER-01, REL-ADV-01,
WRITE-ADV-01/02). Discussion stayed within the four debt items.
