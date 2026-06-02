# ADR-0001: Pyodide Browser Support — Go/No-Go Decision

**Date:** 2026-06-02
**Deciders:** Marc Fargas

## Status

Accepted

---

## Context

**Question:** Can godoo run an Odoo JSON-RPC call from within a Pyodide browser runtime, and is a
`godoo[browser]` extra worth committing to in a future milestone?

The Phase 8 spike (`.planning/phases/08-pyodide-spike/08-SPIKE.md`) tested three transport strategies
from Pyodide 0.29.4 (CPython 3.13) against a live TLS-terminated Odoo 17 endpoint on Azure Container
Apps, exercising cross-origin HTTPS JSON-RPC (authenticate + `res.users` read).

The **D-10 go bar** requires at least one strategy that **both** makes a real cross-origin HTTPS
JSON-RPC call **and** is maintainable/sustainable to ship. A success that only works via a brittle,
unmaintainable third-party patch is recorded as conditional/no-go.

A secondary tension surfaced: godoo's monorepo declares `requires-python = ">=3.14"` across all
packages, but current Pyodide ships CPython 3.13 — so godoo is not installable in current Pyodide
as-is. This ADR also resolves the Python-floor direction.

Per the D-08 evidence-vs-decision separation, the per-strategy results and Python-floor analysis
live in the spike evidence document (`08-SPIKE.md`). This ADR applies the D-10 bar to that evidence
and records the durable, fleet-readable decision.

---

## Considered Options

### Transport Strategy Options (D-06)

| Strategy | Result | Maintainable? | D-10 Assessment |
|----------|--------|---------------|-----------------|
| **S1 — Stock httpx** (micropip-installed, no patch) | WORKED (surprise — routes via Pyodide's built-in fetch bridge) | Caveat: the httpx → Pyodide fetch routing mechanism needs confirmation as a stable, documented API before it can be designated the shipping path | Second candidate; not designated primary shipping path |
| **S2 — pyodide-httpx 0.2.0** | FAILED — `ModuleNotFoundError: No module named 'httpx._transports.default'` on `patch_httpx()` (version-incompatible crash) | No — imports a private httpx submodule removed in the httpx version resolved under Pyodide 0.29.4; brittle third-party patch | **Confirmed no-go as a shipping dependency** |
| **S3 — custom PyfetchTransport** (via `transport_factory` seam) | WORKED — full authenticate + `res.users` round-trip, `uid=2` | Yes — depends only on Pyodide's built-in `pyfetch`; no third-party package; uses the existing `transport_factory` extension point (from Phase 6 / BROWSER-01); the prototype is `<100 LOC` | **Satisfies D-10 go bar — primary shipping path** |

For verbatim results, tracebacks, and network evidence, see `.planning/phases/08-pyodide-spike/08-SPIKE.md`.

### Python-Floor Options (D-07 / BROWSER-03)

| Option | Description | Cost | Benefit |
|--------|-------------|------|---------|
| **A — Defer to Pyodide >=3.14** | Keep the single `>=3.14` monorepo floor; browser support ships only after Pyodide bumps its CPython to 3.14 or later | Ships later; gated on Pyodide's release cadence (not godoo's) | Zero floor divergence; monorepo stays coherent; aligns with PEP 776/783 (Emscripten = CPython tier-3 target from 3.14) |
| **B — Drop floor to >=3.12/3.13 for browser build** | Introduce a browser-specific sub-package or build path with `requires-python = ">=3.12"` | Divergent floor; separate CI matrix and type-stub targets for at least one build artifact | Ships on current Pyodide today without waiting on Pyodide's CPython upgrade cadence |

---

## Decision

**Verdict: GO**

The D-10 go bar is met. Strategy 3 (custom `PyfetchTransport` via the `transport_factory` seam) made
a complete cross-origin HTTPS authenticate + `res.users` JSON-RPC round-trip from Pyodide 0.29.4 in a
real browser against a live TLS-terminated Odoo 17 endpoint. It depends only on Pyodide's built-in
`pyfetch`, uses the existing shipped extension point, and requires no third-party patch. It is the
designated maintainable shipping path for `godoo[browser]`.

Strategy 1 (stock httpx) also worked and is a secondary candidate, but its routing mechanism
(httpx → Pyodide fetch bridge) must be confirmed as a stable, documented API before it can be
designated the shipping path.

Strategy 2 (pyodide-httpx 0.2.0) is a confirmed no-go as a shipping dependency: it crashes at
`patch_httpx()` due to a private httpx submodule removal, making it version-brittle and
unmaintainable. It must never be added to any `pyproject.toml`.

**Python-floor decision: Option A — Defer until Pyodide ships CPython >=3.14**

The godoo monorepo `requires-python = ">=3.14"` floor is kept unchanged. Browser support ships as
`godoo[browser]` only after Pyodide bumps its CPython version to 3.14 or later. This aligns with
PEP 776 and PEP 783 (Emscripten = official CPython tier-3 target from 3.14, steering council
approved October 2024) and avoids a divergent floor and split CI matrix. The spike proves the
transport works today (on 3.13 in isolation per D-07), so when Pyodide 3.14 lands, BROWSER-F1
implementation is low-risk.

**Footnote:** Odoo's `/jsonrpc` endpoint is deprecated and scheduled for removal in Odoo 22
(fall 2028). Any future `godoo[browser]` implementation must plan for the successor endpoint.

This ADR establishes the `docs/adr/` convention — it is the first ADR in the godoo-py repository.

---

## Consequences

### If go (this decision)

- **v2.0 escalation:** a "go" for browser support requires introducing a `godoo[browser]` optional
  extra (`BROWSER-F1`) and a relaxed Python-floor build path (`BROWSER-F2`). These are breaking
  changes relative to the v1.x API surface and escalate to **v2.0 planning**. They do not ship in
  the current v1.1 milestone.
- **BROWSER-F1 unblocked:** The non-shipping `PyfetchTransport` prototype (`spikes/08-pyodide/transport_pyfetch.py`,
  committed under D-09) seeds the implementation of `godoo[browser]` when v2.0 planning is activated.
  The transport seam (`OdooClientConfig.transport_factory`) is already shipped in v1.1 (Phase 6 /
  BROWSER-01) and requires no breaking change.
- **BROWSER-F2 gated on Pyodide 3.14:** Under Option A, the Python floor relaxation deferred item
  (`BROWSER-F2`) remains in the backlog pending a Pyodide stable release with CPython >=3.14. When
  that release ships, BROWSER-F2 can be activated with low implementation risk.
- **Strategy 1 caveat:** Before designating stock httpx as an alternative shipping path, confirm that
  the httpx → Pyodide fetch routing is a stable, documented contract in Pyodide's public API. Until
  confirmed, Strategy 3 (PyfetchTransport) is the sole designated path.

### If no-go (not this decision — recorded for completeness)

- `BROWSER-F1` (`godoo[browser]` extra) and `BROWSER-F2` (relax Python floor for Pyodide) would
  be deferred to the backlog with no active v2.0 escalation.
- The `PyfetchTransport` prototype would remain as committed evidence only, with no forward work item.
