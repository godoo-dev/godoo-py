---
phase: 08-pyodide-spike
artifact: spike-evidence
date: 2026-06-02
endpoint: https://ca-godoo-pyodide-spike.nicegrass-f470f64f.northeurope.azurecontainerapps.io
pyodide_version: "0.29.4"
cpython_version: "3.13"
status: complete
---

# 08-SPIKE.md — Pyodide Browser Spike Evidence

**One-liner:** All three D-06 transport strategies were tested from Pyodide 0.29.4 (CPython 3.13) in a
real browser against a live TLS-terminated ACA Odoo 17 endpoint; Strategy 3 (custom PyfetchTransport)
made a complete authenticate + res.users round-trip over cross-origin HTTPS; Strategy 1 (stock httpx)
also worked (surprising); Strategy 2 (pyodide-httpx 0.2.0) failed with a version-incompatibility crash.

---

## SC-1: Cross-Origin HTTPS Evidence

**Spike endpoint:** `https://ca-godoo-pyodide-spike.nicegrass-f470f64f.northeurope.azurecontainerapps.io`
(ACA-managed TLS cert, Odoo 17, db=spike; endpoint has since been torn down per self-destruct TTL)

**Page origin (CORS source):** `http://localhost:8000` (matched ACA `corsPolicy.allowedOrigins`)

### Strategy 3 — Verbatim result

```
WORKED — session uid=2 db=spike — users=[{'id': 2, 'login': 'admin', 'name': 'Administrator'}]
```

This is the full godoo transport round-trip:
1. `PyfetchTransport.authenticate("admin", "<throwaway>")` → JSON-RPC `common.authenticate` → session uid=2
2. `PyfetchTransport.call("res.users", "read", [[2]], {"fields": ["login", "name"]})` → JSON-RPC `object.execute_kw` → users list

This is an **actual JSON-RPC round-trip**, not an import-only check. The authenticate call returned a
real session uid (2 = admin); the res.users read returned the Administrator account data from the live DB.

### Network evidence (Playwright programmatic capture)

Three `POST https://ca-godoo-pyodide-spike.nicegrass-f470f64f.northeurope.azurecontainerapps.io/jsonrpc → 200`
were recorded (one per strategy that reached the wire — Strategy 2 crashed before the POST).

**No CORS OPTIONS preflight was observed.** The browser treated the requests as permitted without a
preflight. This is consistent with the ACA `corsPolicy` having `allowedOrigins` set to the page origin
(`http://localhost:8000`) at deploy time — the reverse-proxy ingress handles the CORS handshake
transparently. All three POSTs returned HTTP 200.

**Visual evidence:** `spikes/08-pyodide/spike-run-evidence.png` (full-page screenshot, ~333 KB).

This satisfies SC-1: an actual Odoo JSON-RPC call was made from within a Pyodide runtime, cross-origin,
over HTTPS, against a real TLS-terminated Odoo endpoint.

---

## SC-2: Per-Strategy Results

| Strategy | Worked / Failed | Detail |
|----------|-----------------|--------|
| **Strategy 1** — stock httpx (micropip-installed, no patch) | **WORKED** | `WORKED — {'jsonrpc': '2.0', 'id': 1, 'result': 2}`. This **contradicts** the D-06 prior expectation that stock httpx would fail on missing POSIX sockets. Pyodide 0.29.4 routes httpx's `AsyncClient` through Pyodide's built-in `fetch` bridge without requiring `pyodide-httpx`. **Caveat:** the routing mechanism (httpx → Pyodide fetch) should be confirmed as a stable API before relying on Strategy 1 as a shipping path — it may depend on internal Pyodide plumbing rather than a documented contract. |
| **Strategy 2** — pyodide-httpx==0.2.0 | **FAILED** | micropip install of `pyodide-httpx==0.2.0` + `ssl` succeeded, but `patch_httpx()` crashed with `ModuleNotFoundError`. Verbatim traceback: <pre>ModuleNotFoundError: No module named 'httpx._transports.default'<br>Traceback:<br>  File "/lib/python3.13/site-packages/pyodide_httpx/__init__.py", line 3, in patch_httpx<br>    from ._async import patch_async_client<br>  File "/lib/python3.13/site-packages/pyodide_httpx/_async.py", line 6, in &lt;module&gt;<br>    from httpx._transports.default import AsyncResponseStream<br>ModuleNotFoundError: No module named 'httpx._transports.default'</pre>Root cause: `pyodide-httpx 0.2.0` imports a private httpx submodule (`httpx._transports.default`) that was removed or relocated in the httpx version micropip resolves under Pyodide 0.29.4 / CPython 3.13. Confirmed version-incompatible and brittle — **no-go**. |
| **Strategy 3** — custom PyfetchTransport (transport seam) | **WORKED** | `WORKED — session uid=2 db=spike — users=[{'id': 2, 'login': 'admin', 'name': 'Administrator'}]`. Full authenticate + res.users round-trip. Satisfies D-10 go-bar: maintainable (no third-party dependency, uses only Pyodide's built-in `pyfetch`) and provably works against a real cross-origin HTTPS Odoo endpoint. |

---

## SC-3: Python Floor

**Central tension surfaced by this spike:**

The spike ran on **Pyodide 0.29.4 = CPython 3.13**. The godoo monorepo declares `requires-python = ">=3.14"`
across all three packages. This means **godoo is not installable in current Pyodide as-is** — the Python
floor gap is the primary architectural decision the ADR must resolve.

Note: the spike harness (`spikes/08-pyodide/transport_pyfetch.py` and `index.html`) is explicitly exempt
from the `>=3.14` gate (D-09) — these are non-shipping spike artifacts. But any future `godoo[browser]`
extra that users `micropip.install()` would be subject to the same `requires-python` constraint.

### Option A — Defer until Pyodide ships CPython >=3.14

Keep the single `>=3.14` monorepo floor unchanged. Browser support ships only after Pyodide bumps its
CPython version to 3.14 or later. Aligns with PEP 776 (3.14 free-threading) and PEP 783 patterns.

- **Cost:** ships later; gated on Pyodide's release cadence (not under godoo's control).
- **Benefit:** zero floor divergence; monorepo stays coherent; no dual-maintenance of a lower-floor build.

### Option B — Drop the floor to >=3.12 (or >=3.13) for a browser-specific build

Introduce a browser-specific sub-package or conditional build path that declares `requires-python = ">=3.12"`
or `">=3.13"`, allowing `micropip.install("godoo")` to succeed in current Pyodide today.

- **Cost:** creates a divergent `requires-python` floor to maintain; requires the CI matrix and type stubs
  to target a lower Python version for at least one build artifact.
- **Benefit:** ships sooner without waiting on Pyodide's CPython upgrade cadence.
- **Note:** `pyodide-httpx` itself declares `>=3.12`, but it is a confirmed no-go (Strategy 2) and no
  longer provides any argument for Option B.

**The formal go/no-go DECISION and floor choice are deferred to Plan 08-04 ADR** (D-08 evidence-vs-decision
separation — this document is the evidence artifact, not the decision artifact).

---

## Footnote: /jsonrpc Deprecation

Odoo's `/jsonrpc` endpoint is deprecated and scheduled for removal in Odoo 22 (fall 2028). Any browser
transport implementation must plan for the successor endpoint.

---

## D-10 Go-Bar Assessment

The D-10 go-bar requires: "a maintainable transport strategy that makes a real cross-origin HTTPS
JSON-RPC call from within a Pyodide runtime."

**The go-bar is MET:**

- **Strategy 3 (custom PyfetchTransport via the transport seam)** is maintainable — it depends only on
  Pyodide's built-in `pyfetch`, not on any third-party package — and made a complete cross-origin HTTPS
  authenticate + res.users round-trip. This is the primary go candidate.
- **Strategy 1 (stock httpx)** is a second working candidate. It is simpler to use but its routing
  mechanism in Pyodide 0.29.4 needs confirmation as a stable API before it can be declared the shipping
  path.
- **Strategy 2 (pyodide-httpx 0.2.0)** is a confirmed no-go: the package imports a private httpx
  internal that no longer exists in the httpx version resolved under Pyodide 0.29.4.

The **formal go/no-go DECISION** — whether to commit to a browser build at all, which strategy to
designate as the shipping path, and how to resolve the Python floor tension — is deferred to the
**Plan 08-04 ADR** (`docs/adr/0001-pyodide-browser-go-no-go.md`).
