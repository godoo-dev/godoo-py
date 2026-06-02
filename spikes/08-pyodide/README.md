# godoo Pyodide spike — Phase 8

Non-shipping committed evidence (D-09).  Nothing here enters any `pyproject.toml`.

## What this is

A raw Pyodide HTML harness that runs all three D-06 transport strategies
sequentially in the browser, printing per-strategy worked/failed status plus
tracebacks (failures) or result payloads (successes) to the page and the console.

| File | Purpose |
|------|---------|
| `index.html` | Raw Pyodide page — loads `pyodide.js` 0.29.4 + `micropip`; runs all 3 strategies |
| `transport_pyfetch.py` | Strategy-3 prototype — custom `pyfetch`-backed `PyfetchTransport` (seeds BROWSER-F1) |

Infra for the ACA throwaway endpoint is in `infra/` (scaffolded in Plan 02).

---

## Serving requirement — MUST use a real HTTP(S) origin

**The page cannot be opened as a `file://` URL.**
When served from `file://` the browser Origin is `null`, and the CORS policy on the
ACA endpoint will reject every preflight — all three strategies will fail identically
with `TypeError: Failed to fetch`, which is a CORS failure, not a transport failure.

**Options:**

```bash
# Option A — localhost static server (plain-HTTP page → HTTPS endpoint)
# Cross-origin + HTTP-origin-to-HTTPS-endpoint (mixed context) is still a valid
# cross-origin test; SC-1's localhost exclusion applies to the *Odoo endpoint*,
# not the page host.
cd spikes/08-pyodide
python -m http.server 8000
# then open http://localhost:8000/index.html
```

```bash
# Option B — GitHub Pages (HTTPS page → HTTPS endpoint; cleanest SC-1 demonstration)
# Push this directory to a gh-pages branch and serve from
# https://<user>.github.io/<repo>/spikes/08-pyodide/index.html
# Set ACA corsPolicy allowedOrigins to https://<user>.github.io
```

The ACA `corsPolicy.allowedOrigins` (configured in `infra/main.bicep`) must
match the **exact origin** you serve from (scheme + host + port, no trailing slash).

---

## Filling the endpoint placeholders

The committed `index.html` has `__FILL_AT_RUN_TIME__` placeholders for the endpoint
FQDN, DB name, and credentials (T-08-01 — public LGPL repo, no secrets committed).

Pass them as **URL query parameters** in your local working copy:

```
http://localhost:8000/index.html?base_url=https://odoo.YOUR-ENV.azurecontainerapps.io&db=odoo&user=admin&password=THROWAWAY_PASSWORD
```

Plan 02 provisions the ACA endpoint and outputs the FQDN.
The Odoo admin password is generated at deploy time (throwaway, never reused).

**Never commit real values.  Never reuse the throwaway password elsewhere.**

---

## Running the spike

1. Deploy the ACA endpoint (Plan 02): `cd spikes/08-pyodide/infra && az deployment group create …`
2. Note the FQDN from the deployment output.
3. Start the static server: `python -m http.server 8000` from `spikes/08-pyodide/`.
4. Open the page with query params filled (see above).
5. Open browser devtools (F12) — Network tab and Console tab.
6. Watch per-strategy output appear in the page and the console.
7. For CORS failures: inspect the OPTIONS preflight in the Network tab before
   blaming the transport (Pitfall 2 — CORS errors show as opaque `TypeError: Failed to fetch`).

---

## Where the verdict lands

| Artifact | Content |
|----------|---------|
| `.planning/phases/08-pyodide-spike/08-SPIKE.md` | Per-strategy worked/failed table with verbatim tracebacks, resolved version numbers, devtools Network screenshots, Python-floor recommendation |
| `docs/adr/0001-pyodide-browser-go-no-go.md` | Durable go/no-go ADR — status `accepted`; references `08-SPIKE.md` for evidence (D-08 evidence/decision split) |

The ADR at `docs/adr/0001-…` is the artifact that v2.0 planning reads for the
browser-capability direction.

---

## Strategy summary

| # | Name | Expected | D-10 classification |
|---|------|----------|---------------------|
| 1 | stock httpx | FAIL — socket I/O not available under Emscripten | n/a (expected failure, documents the limitation) |
| 2 | `pyodide-httpx==0.2.0` | WORK | Conditional/no-go — brittle third-party patch, low maintenance (3 stars). NEVER add to `pyproject.toml`. |
| 3 | custom `PyfetchTransport` | WORK | **Go candidate** — uses the existing `transport_factory` seam; maintainable (~<100 LOC, Cloudflare's number); seeds BROWSER-F1 |

A "go" verdict requires strategy 3 to succeed (D-10).

---

## What is NOT a dependency

`pyodide-httpx` and `httpx` are installed **in-browser via micropip only** (D-06).
They are NOT in any `packages/*/pyproject.toml` and must never be added there.
This spike is throwaway evidence; productize a browser build only on a "go" verdict
(future phase, gated on BROWSER-F1).
