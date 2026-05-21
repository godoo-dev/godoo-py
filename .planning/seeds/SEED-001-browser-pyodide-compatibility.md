---
id: SEED-001
status: dormant
planted: 2026-05-21
planted_during: v1.0 — after Phase 02 completion
trigger_when: when relevant
scope: unknown
---

# SEED-001: Our libraries should, as much as possible, run in browsers (via Pyodide → Marimo, stlite, etc.)

## Why This Matters

_To be filled in. Run `/gsd:capture --seed --enrich SEED-001` to add context._

Initial note: Pyodide-compatible Python libraries unlock usage in browser-native Python
environments — Marimo notebooks, stlite (Streamlit-in-browser), JupyterLite, PyScript.
Concretely, this could mean a `godoo` client that talks to an Odoo instance directly
from a notebook running entirely in the user's browser, no local Python install
required.

## When to Surface

**Trigger:** when relevant

This seed will surface during `/gsd:new-milestone` when the milestone scope matches.

Likely natural trigger: any milestone that touches the HTTP transport, dependency
selection, or packaging/distribution — the points where browser compatibility is
won or lost.

## Scope Estimate

**Unknown** — run `/gsd:capture --seed --enrich SEED-001` to estimate effort.

Open questions to settle when enriching:
- Does `httpx` work in Pyodide? (Pyodide has its own fetch-backed transport; pure-Python
  httpx may need a custom transport adapter.)
- Which of the three packages (`godoo`, `godoo-introspection`, `godoo-testcontainers`)
  are in-scope? `godoo-testcontainers` is Docker-bound and explicitly out.
- CORS — Odoo would need to permit cross-origin JSON-RPC from the notebook origin.

## Breadcrumbs

- `packages/godoo/src/godoo/rpc/transport.py` — sole `httpx` consumer; the load-bearing
  file for any future Pyodide transport adapter.
- Root `pyproject.toml` / `packages/godoo/pyproject.toml` — `httpx>=0.27` is the only
  runtime HTTP dependency; whatever decision is made here will be expressed in these
  files.
- `packages/godoo-testcontainers/` — out of scope by construction (Docker-bound).

## Notes

_Captured via one-shot seed capture. Enrich with trigger, why, and scope at your convenience._
