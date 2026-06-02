# Phase 8: Pyodide Spike - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 8-Pyodide Spike
**Areas discussed:** Host environment, CORS-enabled HTTPS Odoo (endpoint + teardown), Strategy coverage + custom transport, Verdict artifact + go/no-go

---

## Host environment

| Option | Description | Selected |
|--------|-------------|----------|
| Raw Pyodide HTML page | Hand-load pyodide.js + micropip; cleanest error surface, result transfers to other hosts | ✓ |
| JupyterLite | Full Jupyter via Pyodide kernel; closer to notebook target but kernel layer obscures errors | |
| Marimo (WASM export) | Most direct SEED match; more setup, marimo async handling could confound | |
| Raw page first, confirm in JupyterLite | Diagnose clean, then confirm in a notebook host | |

**User's choice:** Raw Pyodide HTML page
**Notes:** Confirming in a notebook host deferred — runtime is shared so the verdict transfers.

---

## Endpoint source

| Option | Description | Selected |
|--------|-------------|----------|
| Existing Odoo on your server + CORS shim | Reverse proxy on conductor/dok01 | (proposed, withdrawn) |
| Throwaway Odoo on a VPS w/ Caddy auto-TLS | Disposable clean-room | |
| Managed Odoo.com trial + proxy hop | Free TLS, no CORS control | |
| Azure Container Apps — managed HTTPS + ingress CORS | Throwaway, managed cert, non-localhost | ✓ |

**User's choice:** Azure Container Apps (after correcting course)
**Notes:** Claude initially proposed `conductor` from stale global host notes — user corrected that conductor was decommissioned weeks ago and Azure is the current deployment platform. User's instinct was a throwaway rig (ideally testcontainers + reverse proxy + self-signed cert) and asked whether a TLS/CORS layer belongs in `godoo-testcontainers` or stays local. Claude flagged two blockers: (1) SC-1 explicitly excludes localhost, so a testcontainers-local rig conflicts with the criterion; (2) self-signed certs are rejected by the browser fetch (would need mkcert or manual trust). Resolution: ACA's default `*.azurecontainerapps.io` FQDN gives a browser-trusted managed cert on a non-localhost host, satisfying SC-1 cleanly. Scope-discipline lean: keep the rig ad-hoc, do NOT bake TLS/CORS into godoo-testcontainers during a throwaway spike.

---

## CORS mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Reverse proxy / ingress adds headers + answers preflight | Keeps Odoo untouched, production-representative | ✓ |
| Odoo controller / module sets headers | No proxy, but touches the app, weaker preflight handling | |
| You decide during the spike | Defer | |

**User's choice:** Reverse proxy adds headers + answers preflight (→ ACA ingress CORS)

---

## Teardown / anti-dangling

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated RG + explicit nuke + GH Actions safety net | `az group delete` + scheduled GHA backstop | (rejected — GHA unreliable lately) |
| Dedicated RG + ACA self-destruct Job | In-Azure scheduled job w/ managed identity | ✓ (or Logic App) |
| Dedicated RG + manual teardown only | No automated backstop | |

**User's choice:** Self-contained in Azure — ACA Job **or** Logic App, both Bicep-deployable; identity + role assignment declared in the same deployment.
**Notes:** User asked how to prevent dangling deployments and proposed a self-destruct. Claude noted ACA scales to zero (minReplicas=0) so idle cost is near-zero, the real trap is managed Postgres (must run Postgres as a container), and there's no GA TTL-tag auto-delete. User rejected the GHA backstop (recent reliability problems) and chose a fully self-contained Azure self-destruct, observing the managed identity + role assignment can be part of the Bicep deployment. Claude recorded that RG-scoped Contributor is sufficient to delete the RG itself and the ARM delete continues async after the trigger exits; leaned Logic App for being image-less.

---

## Transport strategy coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Test all three, regardless of early success | Richest per-strategy evidence for SC-2 | ✓ |
| Stop at first success | Faster, thinner verdict | |
| Test 1 & 2 first; build #3 only if both fail | Effort-gated; risks not validating the seam | |

**User's choice:** Test all three regardless of early success

---

## Python floor handling

| Option | Description | Selected |
|--------|-------------|----------|
| Test transport in isolation, not full `import godoo` | Isolates OD-3; floor stays an output | ✓ |
| Temporarily patch requires-python to >=3.12 locally | Tests more of the package; mixes import noise | |
| You decide once hands-on | Defer | |

**User's choice:** Test transport in isolation

---

## Verdict artifact location

| Option | Description | Selected |
|--------|-------------|----------|
| SPIKE findings doc in phase dir + ADR for go/no-go | Evidence with the phase, durable decision as ADR | ✓ |
| Single SPIKE.md holding everything | Simplest, less discoverable decision | |
| GSD spike-findings skill (wrap-up) | Auto-discoverable, heavier ceremony | |

**User's choice:** 08-SPIKE.md (evidence) + standalone ADR (go/no-go)

---

## Spike code retention

| Option | Description | Selected |
|--------|-------------|----------|
| Commit all as non-shipping evidence under phase/spikes dir | Reproducible; prototype seeds BROWSER-F1 | ✓ |
| Keep only the writeup, discard the code | Cleanest repo, loses the rig/prototype | |

**User's choice:** Commit all spike code (HTML page, Bicep, custom pyfetch transport) as non-shipping evidence

---

## Go/no-go threshold

| Option | Description | Selected |
|--------|-------------|----------|
| A maintainable strategy works end-to-end | Brittle-hack-only success = conditional/no-go | ✓ |
| Any successful call = go | Lower bar, faster, risks unshippable path | |
| You decide when you see the results | Defer | |

**User's choice:** A maintainable strategy works end-to-end

---

## Claude's Discretion

- Logic App vs ACA Job for the self-destruct (leaning Logic App, image-less).
- Exact CORS allowed-origin value, minimal Odoo modules for the test DB, ACA scaling/SKU params.

## Deferred Ideas

- Building a reusable TLS/reverse-proxy/CORS layer into `godoo-testcontainers` (productize only on a "go" verdict).
- BROWSER-F1 (`godoo[browser]` extra) and BROWSER-F2 (relax Python floor) — gated on "go".
- Re-running the winning strategy in JupyterLite/Marimo to confirm.
