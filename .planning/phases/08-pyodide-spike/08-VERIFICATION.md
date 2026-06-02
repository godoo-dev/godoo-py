---
phase: 08-pyodide-spike
verified: 2026-06-02T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 8: Pyodide Spike Verification Report

**Phase Goal:** The team has an empirically grounded, written verdict on whether godoo can run
in a Pyodide/browser environment — what transport strategy works, what Python floor is required —
and an explicit go/no-go decision for committing to a browser build in a future milestone.

**Verified:** 2026-06-02
**Status:** PASS-WITH-CONCERNS
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Actual JSON-RPC call (not import-only) from Pyodide, cross-origin, over HTTPS against a real TLS-terminated Odoo endpoint | VERIFIED | `08-SPIKE.md` §SC-1: S3 returned `uid=2, users=[{'id':2,'login':'admin','name':'Administrator'}]`; Playwright capture shows 3x `POST /jsonrpc → 200`; screenshot committed at `spikes/08-pyodide/spike-run-evidence.png` (201 KB) |
| SC-2 | Written verdict documents all three strategies with worked/failed and error output for failures | VERIFIED | `08-SPIKE.md` §SC-2 table: S1 WORKED, S2 FAILED (verbatim `ModuleNotFoundError` traceback), S3 WORKED — per-strategy outputs, error details, and D-10 maintainability assessment all present |
| SC-3 | Python-floor recommendation: "drop to >=3.12" OR "defer to Pyodide >=3.14" with rationale | VERIFIED | `08-SPIKE.md` §SC-3 and ADR §Python-Floor Options: Option A (defer to Pyodide >=3.14) selected with rationale citing PEP 776/783; Option B described and rejected with cost analysis |
| SC-4 | Explicit go/no-go decision recorded; "go" with breaking changes escalates to v2.0; "no-go" defers BROWSER-F1/F2 | VERIFIED | `docs/adr/0001-pyodide-browser-go-no-go.md` §Decision: "Verdict: GO"; §Consequences states v2.0 escalation and BROWSER-F1/F2 deferral explicitly |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `spikes/08-pyodide/transport_pyfetch.py` | Strategy-3 PyfetchTransport prototype (seeds BROWSER-F1) | VERIFIED | 162 lines, substantive: full Transport Protocol implementation (authenticate, call, aclose, logout, session property), pyfetch-backed, no `import godoo` per D-07 |
| `spikes/08-pyodide/index.html` | Raw Pyodide HTML harness running all 3 strategies | VERIFIED | 239 lines; runs S1/S2/S3 sequentially, credential placeholders `__FILL_AT_RUN_TIME__` in code path; spike FQDN and db defaults committed as documentation |
| `spikes/08-pyodide/README.md` | Spike orientation doc | VERIFIED | Covers serving requirement, filling placeholders, strategy table, verdict sink |
| `spikes/08-pyodide/infra/main.bicep` | ACA Bicep (Odoo+Postgres, HTTPS, CORS) | VERIFIED | 200+ lines; `@secure()` parameters for passwords, no hardcoded credentials |
| `spikes/08-pyodide/infra/selfdestruct.bicep` | Logic App TTL self-destruct Bicep | VERIFIED | Present at expected path |
| `spikes/08-pyodide/infra/deploy.md` | Deploy operating guide | VERIFIED | Step-by-step guide for plan 08-03; credentials passed as params, not committed |
| `spikes/08-pyodide/spike-run-evidence.png` | Full-page screenshot of spike run | VERIFIED | 201,406 bytes; non-empty binary |
| `.planning/phases/08-pyodide-spike/08-SPIKE.md` | Evidence artifact (SC-1/2/3 content) | VERIFIED | Contains all three SC sections, D-10 go-bar assessment, footnote on /jsonrpc deprecation |
| `docs/adr/0001-pyodide-browser-go-no-go.md` | Go/no-go ADR (MADR-style, status accepted) | VERIFIED | MADR sections present (Status, Context, Considered Options, Decision, Consequences); Status: Accepted; explicit GO verdict |
| `mkdocs.yml` (nav entry) | ADR reachable in docs nav | VERIFIED | Line 42-43: `ADR:` section with `adr/0001-pyodide-browser-go-no-go.md` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docs/adr/0001-pyodide-browser-go-no-go.md` | `08-SPIKE.md` | References evidence doc | WIRED | Line 17 and 45: explicit path `.planning/phases/08-pyodide-spike/08-SPIKE.md` |
| `mkdocs.yml` | `docs/adr/0001-pyodide-browser-go-no-go.md` | Nav entry | WIRED | Line 43: `adr/0001-pyodide-browser-go-no-go.md` (docs-root-relative) |
| `index.html` | `transport_pyfetch.py` | `fetch("transport_pyfetch.py")` + `pyodide.runPython(tpSrc)` | WIRED | Lines 192-199: fetches and execs the prototype at runtime |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| BROWSER-02 | 08-01, 08-02, 08-03 | Actual in-browser HTTPS call over HTTPS against real TLS-terminated Odoo endpoint, with written verdict on transport strategy | SATISFIED | SC-1 and SC-2 both verified; `08-SPIKE.md` records the call result and per-strategy verdict |
| BROWSER-03 | 08-03, 08-04 | Python-floor recommendation (drop to >=3.12 or defer to Pyodide >=3.14) and explicit go/no-go decision; "go" with breaking changes escalates to v2.0 | SATISFIED | SC-3 satisfied (Option A chosen with rationale); SC-4 satisfied (ADR records GO, v2.0 escalation, BROWSER-F1/F2 deferral) |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `spikes/08-pyodide/run_spike.py` | 16 | `password=admin` hardcoded in committed file | WARNING | The ACA endpoint was torn down at run-time (self-destruct confirmed in 08-03-SUMMARY); the password grants no access to any live system. However, the SUMMARY.md claim "Throwaway Odoo admin credentials were passed as URL query params at run time only — never committed" is factually false — `run_spike.py` commits the password value literally. The endpoint is destroyed and `admin` is a trivially guessable default, so there is no credential-rotation requirement, but the SUMMARY narrative is inaccurate. |

No `TBD`, `FIXME`, or `XXX` debt markers found in phase-08 files.

---

### Behavioral Spot-Checks

Step 7b: SKIPPED (no runnable entry points — this is a spike producing static evidence artifacts and documentation only; the spike harness requires a live Odoo ACA endpoint, which has been torn down per self-destruct TTL).

---

### Human Verification Required

None. This is a spike phase — its deliverable is an evidence document and a decision document, both of which are statically verifiable from the committed artifacts. No visual or real-time behavior requires human confirmation.

---

## Per-Requirement Assessment

### BROWSER-02 — SATISFIED

**Requirement text:** "A spike runs an actual in-browser (Pyodide) HTTP call over HTTPS against a real TLS-terminated Odoo endpoint — exercising browser TLS-via-fetch, CORS, and mixed-content constraints (plain HTTP / localhost does not satisfy this) — and produces a written verdict on whether stock httpx works or a custom fetch-backed transport is required"

**Assessment:**

- The spike ran from `http://localhost:8000` (page origin) against `https://ca-godoo-pyodide-spike.nicegrass-f470f64f.northeurope.azurecontainerapps.io` (Odoo endpoint). The requirement's localhost/plain-HTTP exclusion applies to the Odoo endpoint, not the page host — confirmed by CONTEXT.md §SC-1 and README.md serving-requirement section. The Odoo endpoint was HTTPS on a managed ACA cert.
- Strategy 3 produced a full `authenticate + res.users` round-trip (uid=2, real data from live DB). Strategy 1 also worked. These are actual JSON-RPC calls, not import-only checks.
- Playwright network capture shows 3x `POST /jsonrpc → 200`; screenshot committed.
- Written verdict present in `08-SPIKE.md`: stock httpx worked (surprising finding), custom PyfetchTransport worked (primary go candidate), pyodide-httpx 0.2.0 failed (no-go).

BROWSER-02 is fully satisfied.

### BROWSER-03 — SATISFIED

**Requirement text:** "The spike delivers a Python-floor recommendation (drop `requires-python` to `>=3.12` for a browser build, or defer until Pyodide ships CPython >=3.14) and an explicit go/no-go decision for committing browser support; a 'go' with required breaking changes escalates the milestone to v2.0"

**Assessment:**

- Python-floor recommendation: Option A (defer to Pyodide >=3.14) adopted, rationale documented in `08-SPIKE.md` §SC-3 and ADR §Python-Floor Options. PEP 776/783 (Emscripten = official CPython tier-3 target from 3.14) cited.
- Go/no-go: ADR records explicit "Verdict: GO" with D-10 bar applied.
- v2.0 escalation: ADR §Consequences §"If go" states "v2.0 escalation: a 'go' for browser support requires introducing a `godoo[browser]` optional extra (BROWSER-F1) and a relaxed Python-floor build path (BROWSER-F2). These are breaking changes...and escalate to v2.0 planning."
- BROWSER-F1/F2 backlog deferral explicitly stated.

BROWSER-03 is fully satisfied.

---

## Gaps Summary

No blocking gaps. The phase goal is achieved: empirical evidence exists, the written verdict is substantive, the decision is recorded in a durable ADR, and the ADR is wired into the docs site.

### Concern (WARNING, non-blocking)

**`spikes/08-pyodide/run_spike.py` line 16 — hardcoded `password=admin`**

The 08-03-SUMMARY threat-surface scan claims "Throwaway Odoo admin credentials were passed as URL query params at run time only — never committed." This is false. `run_spike.py` commits `password=admin` literally in the URL string. The mitigating factors are strong:

1. The ACA endpoint has been torn down (self-destruct confirmed; FQDN grants no access).
2. `admin` is a trivially guessable Odoo default password, not a generated secret.
3. The file is in `spikes/` (non-shipping) in a public LGPL repo, where the FQDN is also committed.

No rotation is required (no live system). However, the inaccurate SUMMARY narrative is noted.

---

## Evidence List

| Artifact | Location | Key Line(s) |
|----------|----------|-------------|
| SC-1 call result (S3) | `08-SPIKE.md` line 33 | `WORKED — session uid=2 db=spike — users=[{'id': 2, 'login': 'admin', 'name': 'Administrator'}]` |
| SC-1 network evidence | `08-SPIKE.md` lines 42-48 | "Three POST...→ 200 were recorded" |
| SC-2 strategy table | `08-SPIKE.md` lines 59-63 | All three strategies with verbatim outputs |
| SC-3 Python floor | `08-SPIKE.md` lines 79-98 | Option A/B framing with rationale |
| SC-4 go verdict | `docs/adr/0001-pyodide-browser-go-no-go.md` line 58 | "Verdict: GO" |
| SC-4 v2.0 escalation | `docs/adr/0001-pyodide-browser-go-no-go.md` lines 93-97 | Explicit escalation + BROWSER-F1/F2 consequences |
| ADR mkdocs nav | `mkdocs.yml` lines 42-43 | `ADR:` section with `adr/0001-pyodide-browser-go-no-go.md` |
| ADR references spike | `docs/adr/0001-pyodide-browser-go-no-go.md` lines 17, 30, 45 | `08-SPIKE.md` path cited three times |
| Hardcoded password | `spikes/08-pyodide/run_spike.py` line 16 | `password=admin` in URL string |
| Screenshot size | `spikes/08-pyodide/spike-run-evidence.png` | 201,406 bytes (non-empty) |

---

_Verified: 2026-06-02_
_Verifier: Claude (gsd-verifier)_
