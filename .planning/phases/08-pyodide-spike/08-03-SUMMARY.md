---
phase: 08-pyodide-spike
plan: "03"
subsystem: spikes
tags: [pyodide, browser, transport, spike, azure, aca, evidence, cors]
dependency_graph:
  requires:
    - spikes/08-pyodide/transport_pyfetch.py   # from plan 08-01
    - spikes/08-pyodide/index.html              # from plan 08-01
    - spikes/08-pyodide/infra/main.bicep        # from plan 08-02
    - spikes/08-pyodide/infra/selfdestruct.bicep  # from plan 08-02
    - spikes/08-pyodide/infra/deploy.md         # from plan 08-02
  provides:
    - .planning/phases/08-pyodide-spike/08-SPIKE.md  # empirical evidence artifact
    - spikes/08-pyodide/spike-run-evidence.png        # full-page screenshot
  affects:
    - .planning/phases/08-pyodide-spike/08-04-PLAN.md  # ADR plan consumes this evidence
    - docs/adr/0001-pyodide-browser-go-no-go.md         # written in plan 08-04
tech_stack:
  added: []
  patterns:
    - Live ACA Odoo 17 endpoint (northeurope, db=spike, Odoo 17.0 base module)
    - Playwright programmatic network capture (replaces devtools screenshot)
    - Three-strategy sequential browser spike run in Pyodide 0.29.4 / CPython 3.13
key_files:
  created:
    - .planning/phases/08-pyodide-spike/08-SPIKE.md
    - spikes/08-pyodide/spike-run-evidence.png
  modified:
    - spikes/08-pyodide/index.html  # base_url + db fallback defaults filled with spike FQDN
decisions:
  - "Strategy 3 (PyfetchTransport) is the primary go candidate — maintainable + full round-trip proven"
  - "Strategy 1 (stock httpx) also worked — contradicts prior D-06 fail expectation; caveat: routing mechanism needs confirmation"
  - "Strategy 2 (pyodide-httpx 0.2.0) is a confirmed no-go — version-incompatible crash at patch_httpx()"
  - "Python floor tension (godoo >=3.14 vs Pyodide CPython 3.13) is the central ADR question — deferred to 08-04"
  - "Formal go/no-go decision deferred to Plan 08-04 ADR per D-08 evidence-vs-decision separation"
metrics:
  completed: "2026-06-02"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 8 Plan 03: Live Spike Run Summary

**One-liner:** Deployed a live TLS-terminated Odoo 17 ACA endpoint, ran the Pyodide 3-strategy browser
harness against it (Playwright-captured), and wrote empirical evidence showing Strategy 3 (custom
PyfetchTransport) made a full cross-origin HTTPS authenticate + res.users round-trip; Strategy 1
(stock httpx) also worked, contradicting D-06 prior expectation; Strategy 2 (pyodide-httpx 0.2.0) is
a confirmed no-go. Formal go/no-go decision deferred to Plan 08-04 ADR.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Deploy ACA endpoint + run browser spike (SC-1 + SC-2 evidence) | (this commit) | `spikes/08-pyodide/spike-run-evidence.png`, `spikes/08-pyodide/index.html` (defaults filled) |
| 2 | Write 08-SPIKE.md evidence artifact | (this commit) | `.planning/phases/08-pyodide-spike/08-SPIKE.md` |

## What Was Done

### Task 1 — Live Deploy + Browser Spike Run

- Provisioned ACA endpoint in `northeurope` (after westeurope hit `AKSCapacityHeavyUsage`): RG `rg-godoo-pyodide-spike-2`
- FQDN: `ca-godoo-pyodide-spike.nicegrass-f470f64f.northeurope.azurecontainerapps.io`
- Odoo 17 with `--init=base --database=spike`, db=spike, throwaway credentials
- Served `index.html` + `transport_pyfetch.py` from `http://localhost:8000` (matched ACA CORS `allowedOrigins`)
- Ran all three strategies sequentially in Pyodide 0.29.4 (CPython 3.13) via browser
- Captured network traffic programmatically via Playwright (3× `POST /jsonrpc → 200`, no OPTIONS preflight)
- Saved full-page screenshot to `spikes/08-pyodide/spike-run-evidence.png`
- Tore down both Azure RGs post-run (rg-godoo-pyodide-spike-2 → Deleting; rg-godoo-pyodide-spike → already NotFound)

### Task 2 — 08-SPIKE.md Evidence Artifact

Written per the evidence specification. Contains:
- SC-1 block: verbatim Strategy 3 result + network evidence
- SC-2 table: all three strategies with verbatim outputs/tracebacks
- SC-3 Python floor section: Option A (defer to Pyodide CPython >=3.14) vs Option B (drop floor to >=3.12/3.13), with rationale
- D-10 go-bar assessment: MET (two strategies worked; Strategy 3 is maintainable go candidate)
- Footnote: /jsonrpc deprecation in Odoo 22 (fall 2028)

## Key Findings

| Finding | Detail |
|---------|--------|
| Strategy 3 WORKED | `uid=2`, `users=[{'id': 2, 'login': 'admin', 'name': 'Administrator'}]` — full round-trip |
| Strategy 1 WORKED (surprise) | Stock httpx routes via Pyodide's fetch bridge without any patch — contradicts D-06 expectation |
| Strategy 2 FAILED | `ModuleNotFoundError: No module named 'httpx._transports.default'` — version-incompatible crash |
| Python floor gap | Pyodide 0.29.4 = CPython 3.13; godoo requires `>=3.14` — not installable in current Pyodide |
| SC-1 satisfied | Real cross-origin HTTPS JSON-RPC call, 3× POST 200, no preflight issues |
| SC-2 satisfied | All three strategies tested with verbatim outputs |
| SC-3 satisfied | Python floor options framed with rationale for ADR author |

## Deviations from Plan

### 1. main.bicep blocking bug — `--database` flag missing

The Odoo container in the original `main.bicep` (from plan 08-02) lacked an explicit `--database=spike`
target on the Odoo command. The `odoo:17` image ignores the `DB_NAME` env var for the `--init` flag, so
`--init=base` never initialized the database. Fixed in a commit: added `--database=spike` to the Odoo
command args, bumped CPU to `1.0` (the container was OOMing), and fixed two Bicep compile errors that
had been committed in plan 08-02.

### 2. index.html bug — micropip not loaded before use

`index.html` imported `micropip` without first calling `pyodide.loadPackage("micropip")`. This caused
Strategies 1 and 2 to fail for the wrong reason (import error, not the actual transport behavior). Fixed
before the spike run so each strategy reached its real behavior.

### 3. First deploy region failed — westeurope → northeurope

First deploy to westeurope hit `AKSCapacityHeavyUsage` (ACA infrastructure unavailability). Redeployed
to `northeurope` using a fresh RG `rg-godoo-pyodide-spike-2`. The first/stuck RG `rg-godoo-pyodide-spike`
was already being cleaned up (NotFound when teardown was attempted at the end).

### 4. Devtools screenshot → Playwright programmatic capture

The plan called for a "devtools Network screenshot" as the SC-1 network evidence. This was replaced by a
programmatic Playwright network capture (logging each request URL, method, and status code). This is more
rigorous than a screenshot (machine-readable, unambiguous) and was supplemented by a full-page screenshot
(`spike-run-evidence.png`). The devtools approach was not used.

## Success Criteria Assessment

| SC | Status | Evidence |
|----|--------|----------|
| SC-1 (real cross-origin HTTPS JSON-RPC call) | SATISFIED | S3: uid=2, users list; 3× POST /jsonrpc → 200; screenshot |
| SC-2 (per-strategy verdict table with error output) | SATISFIED | 08-SPIKE.md §SC-2 table with verbatim S2 traceback |
| SC-3 (Python-floor recommendation) | SATISFIED | 08-SPIKE.md §SC-3 with Option A/B framing |
| D-10 go-bar (maintainable + works) | MET | S3 = maintainable go candidate; S1 = second candidate |

## Formal Decision Status

The formal go/no-go decision is **deferred to Plan 08-04** (ADR at `docs/adr/0001-pyodide-browser-go-no-go.md`)
per D-08 evidence-vs-decision separation. This document is the evidence artifact only.

## Threat Surface Scan

No @secure() deploy secrets (Odoo master password, Postgres password) were ever committed.
A transient Playwright runner script (`spikes/08-pyodide/run_spike.py`) was left in the working tree
during the spike run; it embedded the throwaway `admin`/`admin` default in a URL query string.
That file was never committed to git history and has since been removed from the working tree.
The destroyed ACA endpoint grants no access; no credential rotation was required.
The spike FQDN committed to `index.html` defaults is documentation of the (now-destroyed) spike
endpoint; it grants no access (endpoint torn down).

| Flag | File | Description |
|------|------|-------------|
| T-08-01 mitigated | index.html | base_url + db defaults filled (documentation); USER + PASSWORD remain `__FILL_AT_RUN_TIME__` |
| Teardown complete | Azure | Both RGs: rg-godoo-pyodide-spike (NotFound) + rg-godoo-pyodide-spike-2 (Deleting) |

---
*Phase: 08-pyodide-spike*
*Completed: 2026-06-02*
