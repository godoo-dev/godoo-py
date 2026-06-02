---
phase: 08-pyodide-spike
plan: "01"
subsystem: spikes
tags: [pyodide, browser, transport, spike, evidence]
dependency_graph:
  requires: []
  provides:
    - spikes/08-pyodide/transport_pyfetch.py   # PyfetchTransport prototype (seeds BROWSER-F1)
    - spikes/08-pyodide/index.html              # Pyodide 3-strategy runner (Plan 03 executes this)
    - spikes/08-pyodide/README.md               # How to serve + run + where verdict lands
  affects:
    - .planning/phases/08-pyodide-spike/08-SPIKE.md  # Plan 03 fills this with empirical results
    - docs/adr/0001-pyodide-browser-go-no-go.md      # Plan 03 writes the go/no-go decision
tech_stack:
  added: []
  patterns:
    - pyfetch-backed async transport (structurally satisfying the 5-member Transport Protocol)
    - double-await on FetchResponse.json() (Pitfall 4 guard)
    - URL-query-param placeholder injection (no committed secrets, T-08-01)
key_files:
  created:
    - spikes/08-pyodide/transport_pyfetch.py
    - spikes/08-pyodide/index.html
    - spikes/08-pyodide/README.md
  modified: []
decisions:
  - "PyfetchTransport constructs synchronously (no await in __init__) to satisfy the transport_factory Callable contract"
  - "index.html fetches transport_pyfetch.py from same origin at run time rather than inlining it — keeps the source single-authored and avoids duplication"
  - "strategy 1 isolated from patch_httpx() — runs before any pyodide-httpx import (Pitfall 3)"
metrics:
  duration: "3 minutes"
  completed: "2026-06-02T09:15:09Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 0
---

# Phase 8 Plan 01: Pyodide spike artifacts (transport + harness) Summary

**One-liner:** pyfetch-backed PyfetchTransport prototype (strategy 3) + raw Pyodide HTML
harness running all three D-06 transport strategies with per-strategy pass/fail output,
`__FILL_AT_RUN_TIME__` credential placeholders, and serving/verdict documentation.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Custom pyfetch AsyncTransport prototype (strategy 3) | `08d4ba3` | `spikes/08-pyodide/transport_pyfetch.py` |
| 2 | Raw Pyodide HTML page + README | `d3aad70` | `spikes/08-pyodide/index.html`, `spikes/08-pyodide/README.md` |

## What Was Built

### Task 1 — `transport_pyfetch.py`

A standalone `PyfetchTransport` class that structurally satisfies the 5-member
`Transport` Protocol at `packages/godoo-client/src/godoo/client/rpc/protocol.py`:

- `session` `@property` returning `OdooSessionInfo | None`
- `async def authenticate(username, password)` — posts `common.authenticate` envelope
- `async def call(model, method, args, kwargs)` — posts `object.execute_kw` envelope with
  args ordering `[db, uid, password, model, method, args, kwargs]`
- `def logout()` — **sync**, clears session + password
- `async def aclose()` — no-op (pyfetch holds no client)

Key properties:
- First line is `from __future__ import annotations`
- Local `OdooSessionInfo` dataclass mirrors `uid: int, session_id: str, db: str` exactly
- Double-await on `resp.json()` correctly guards Pitfall 4
- Synchronously constructible (`__init__` takes no `await`)
- No `import godoo` — exempt from the `>=3.14` gate (D-07/D-09)

### Task 2 — `index.html` + `README.md`

Raw Pyodide 0.29.4 page that runs all three D-06 strategies sequentially:

- **Strategy 1 (stock httpx):** installed via micropip, attempted unpatched before any
  `patch_httpx()` call (isolation, Pitfall 3). Expected to FAIL — full traceback is the
  SC-2 evidence.
- **Strategy 2 (pyodide-httpx==0.2.0):** pins `pyodide-httpx==0.2.0` + `ssl` via micropip,
  applies `patch_httpx()`, then makes the same POST; captures resolved httpx version
  alongside the result (version skew is a known risk).
- **Strategy 3 (PyfetchTransport):** fetches `transport_pyfetch.py` from the same static
  origin, exec's it in Pyodide, constructs `PyfetchTransport` synchronously, then
  `await authenticate(...)` + `await call("res.users", "read", ...)` to prove the
  full round-trip.

Each strategy writes worked/failed + traceback-or-result to a visible `<pre>` element
AND the console. Endpoint / DB / credentials are `__FILL_AT_RUN_TIME__` placeholders
passed via URL query params. `credentials: 'include'` is never set.

README documents: the file:// CORS rejection / real-origin serving requirement,
both serving options (`python -m http.server` vs GitHub Pages), placeholder fill
instructions, and where the verdict and ADR land.

## Deviations from Plan

None — plan executed exactly as written.

The one minor implementation choice not specified by the plan: `index.html` fetches
`transport_pyfetch.py` from the same static origin at run time rather than inlining
the source. This is strictly better — it keeps the prototype single-authored and
avoids the maintenance burden of keeping an inline copy in sync.

## Known Stubs

Intentional by design (D-09, T-08-01):

- `__FILL_AT_RUN_TIME__` placeholders in `index.html` for `BASE_URL`, `DB`, `USER`,
  `PASSWORD` — filled via URL query params at run time from a local working copy.
  These are not stubs blocking the plan's goal; they are the security control that
  keeps secrets out of the public repo. Plan 03 fills them when the ACA endpoint is
  provisioned.

## Threat Flags

No new threat surface beyond what the plan's `<threat_model>` already captures:

| Flag | File | Description |
|------|------|-------------|
| T-08-01 mitigated | `index.html` | Endpoint FQDN + creds are `__FILL_AT_RUN_TIME__` placeholders — no real secret committed |
| T-08-02 accepted | `index.html` | `pyodide-httpx==0.2.0` installed in-browser only via micropip; never in any `pyproject.toml` |

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `spikes/08-pyodide/transport_pyfetch.py` exists | FOUND |
| `spikes/08-pyodide/index.html` exists | FOUND |
| `spikes/08-pyodide/README.md` exists | FOUND |
| commit `08d4ba3` exists | FOUND |
| commit `d3aad70` exists | FOUND |
