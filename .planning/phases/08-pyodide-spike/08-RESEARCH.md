# Phase 8: Pyodide Spike - Research

**Researched:** 2026-06-02
**Domain:** Browser Python runtime (Pyodide/Emscripten) HTTP transport + Azure throwaway infra + ADR convention
**Confidence:** HIGH (OD-3 resolution, transport seam, ACA CORS, Pyodide Python version); MEDIUM (Logic App self-destruct exact ARM shape); HIGH (codebase seams — read from source)

## Summary

This is a **spike** — its product is a written verdict (`08-SPIKE.md`) plus a standalone go/no-go ADR. It ships **no** `godoo[browser]` package regardless of outcome (D-09). All ten CONTEXT decisions (D-01..D-10) are LOCKED; this research tells the planner *how* to execute them, not whether.

The headline result resolves **OD-3** empirically-from-documentation before the spike even runs (the spike still confirms it in-browser per SC-1): **stock `httpx.AsyncClient` does NOT work natively in Pyodide and is NOT bundled/pre-patched.** httpx attempts raw socket I/O, which Emscripten cannot provide. The CONTEXT's recorded conflict ("httpx reportedly bundled + pre-patched in Pyodide 0.29.x via a Fetch adapter") is **FALSE** as stated `[VERIFIED: pyodide-http README, Cloudflare engineering blog, GitHub discussion #4999]`. What IS true: (1) `urllib3 >=2.2.0` has *native* Emscripten support via fetch/XHR, (2) `pyodide-http` patches `requests`/`urllib`/`urllib3` (NOT httpx), (3) `pyodide-httpx` 0.2.0 is a separate third-party package that patches httpx via `pyfetch`, and (4) the maintainable path the godoo seam was *designed* for — a custom `pyfetch`-backed transport — is, per Cloudflare's own Pyodide engineering, "fewer than 100 lines of code."

**Primary recommendation:** Plan the spike to test all three D-06 strategies in a raw Pyodide HTML page (D-01) against a throwaway ACA Odoo over its managed-cert HTTPS FQDN (D-02/D-03). Expect strategy 1 (stock httpx) to FAIL (capture the traceback as SC-2 evidence), strategy 2 (`pyodide-httpx`) to WORK but be flagged brittle/low-maintenance, and strategy 3 (custom `pyfetch` `AsyncTransport` via `transport_factory`) to WORK and be the maintainable "go" candidate per D-10. The custom transport is tested **in isolation** against `/jsonrpc` (D-07) — never via `import godoo` (the package is `>=3.14`-gated; Pyodide ships CPython 3.13). Python-floor recommendation: **"defer a shipped browser build until Pyodide ships CPython >=3.14"** (PEP 776/783 restore Emscripten as a CPython tier-3 target *starting 3.14*), with the fallback option of a `>=3.12` browser-specific build documented as the alternative — leave the final wording to the verdict author with both options framed.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BROWSER-02 | An actual in-browser (Pyodide) HTTP call over HTTPS against a real TLS-terminated Odoo endpoint (not localhost/plain-HTTP), exercising browser TLS-via-fetch, CORS, mixed-content — plus a written verdict on whether stock httpx works or a custom fetch transport is required | OD-3 resolution (httpx fails natively); three-strategy how-to + failure modes (Strategies section); ACA managed-cert HTTPS FQDN gives browser-trusted non-localhost TLS (Azure Infra section); ACA `corsPolicy` config (CORS section); `pyfetch` POST-to-`/jsonrpc` recipe (Code Examples) |
| BROWSER-03 | Python-floor recommendation (drop `requires-python` to `>=3.12` for a browser build, OR defer until Pyodide ships CPython >=3.14) + explicit go/no-go decision; a "go" with breaking changes escalates to v2.0 | Pyodide ships CPython 3.13 (0.28+/0.29.x); PEP 776/783 restore Emscripten tier-3 *from 3.14*; `pyodide-httpx` itself requires `>=3.12` (Python-Floor Reality section); ADR convention + location (ADR Convention section); go-bar criteria D-10 (Don't-Hand-Roll / verdict structure) |
</phase_requirements>

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Run the in-browser test in a **raw Pyodide HTML page** (hand-loaded `pyodide.js` + `micropip`). Cleanest error surface; full control; raw tracebacks in console. Result transfers to Marimo/JupyterLite (shared runtime). Notebook re-run is deferred.
- **D-02:** Provision a **throwaway Odoo + Postgres on Azure Container Apps (ACA)**. Postgres runs as a **container in the ACA environment — NOT Azure DB for PostgreSQL** (bills continuously, cannot scale to zero). Set `minReplicas: 0` so idle cost ≈ zero.
- **D-03:** **TLS via the managed cert on the default `*.azurecontainerapps.io` FQDN** — browser-trusted, non-localhost. Chosen to satisfy SC-1's bar (plain-HTTP/localhost does NOT satisfy) while avoiding self-signed/mkcert browser-trust pain.
- **D-04:** **CORS configured on the ACA ingress**, scoped to the spike page's origin, OPTIONS preflight handled (reverse-proxy-style; not an Odoo controller).
- **D-05:** **Teardown** — a dedicated resource group (e.g. `rg-godoo-pyodide-spike`) holding everything, plus a self-contained Bicep **self-destruct**: a Consumption **Logic App** (preferred — image-less) *or* an **ACA scheduled Job** running `az group delete` after a TTL. The user-assigned managed identity **and** its RG-scoped Contributor role assignment are declared in the **same Bicep template**. RG-scoped Contributor is sufficient for the trigger to delete its own RG; the ARM delete continues async after the trigger exits. GitHub Actions backstop explicitly rejected.
- **D-06:** Test **all three strategies regardless of early success** — (1) stock httpx via Pyodide's Fetch adapter, (2) `pyodide-httpx` 0.2.0 (spike-only; **never** in any `pyproject.toml`), (3) a custom `pyfetch`-backed `AsyncTransport` implementing the `Transport` Protocol via `transport_factory`. SC-2 requires per-strategy worked/failed evidence with error output for failures.
- **D-07:** **Python-floor handling** — test the JSON-RPC transport **in isolation** (a minimal `AsyncTransport` against `/jsonrpc`), **NOT** a full `import godoo`. The package is `>=3.14`-gated and will not load under Pyodide's CPython 3.13. The Python floor stays an **output recommendation**, not something the spike fights to bypass.
- **D-08:** Evidence (per-strategy worked/failed + error output) + Python-floor recommendation → **`08-SPIKE.md` in the phase dir**. The durable go/no-go decision → a **standalone ADR** (location/numbering TBD) that v2.0 planning reads. Separates "evidence" from "the decision the fleet depends on."
- **D-09:** **Keep all spike code as non-shipping committed evidence** — the raw Pyodide HTML page, the Bicep, and **especially the custom `pyfetch` `AsyncTransport` prototype** — under the phase artifacts / `spikes/` dir. Nothing enters a published package. The custom transport prototype seeds BROWSER-F1 if "go".
- **D-10:** **Go bar** — "go" requires at least one strategy that **both** makes the cross-origin HTTPS call **and** is maintainable/sustainable to ship (e.g. stock httpx Fetch adapter, or the custom Transport via the existing seam). A success that only works via a brittle/unmaintainable workaround is recorded as **conditional / no-go**.

### Claude's Discretion
- Logic App vs ACA Job for the self-destruct (D-05): researcher recommends, leaning **Logic App**.
- Exact CORS allowed-origin value, the minimal Odoo modules the test DB needs, and the ACA scaling/SKU parameters — left to research/planning.

### Deferred Ideas (OUT OF SCOPE)
- Building a reusable TLS/reverse-proxy/CORS layer into `godoo-testcontainers` — deferred (productize only on "go").
- **BROWSER-F1** (`godoo[browser]` extra) and **BROWSER-F2** (relax Python floor for Pyodide) — gated on "go"; out of scope.
- Re-running the winning strategy in JupyterLite / Marimo — deferred (raw-page result is sufficient; shared runtime).
</user_constraints>

## Project Constraints (from CLAUDE.md)

These apply to any committed Python in the spike. **Exception (D-09):** the custom transport *prototype* is **non-shipping evidence** that lives under `spikes/` (or phase artifacts) and does **NOT** enter any published package — so it need **not** satisfy the `requires-python >=3.14` gate (indeed it cannot; Pyodide is 3.13). It SHOULD still follow style conventions so it reads as godoo code and can seed BROWSER-F1.

- Python 3.14 for shipped packages; `from __future__ import annotations` first line of every file.
- `TYPE_CHECKING` for `OdooClient` / `OdooSessionInfo` imports to avoid circular imports.
- **Dataclasses, not Pydantic** for core types (`OdooSessionInfo`, `OdooClientConfig` are dataclasses).
- All service/transport functions are `async`.
- ruff line-length 120; selects `E, F, W, I, UP, B, SIM, TCH, RUF`. `ruff format`.
- `mypy --strict` on `src/` (the prototype lives outside `src/`, so it is not in the strict-checked set unless the planner adds it; the planner should decide whether to lint the spike dir).
- Conventional commits: `feat`, `fix`, `chore`, `ci`, `docs` with scope in parens.
- develop branch for work, main for clean merges.
- **Never commit `docs/superpowers/`.**

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| In-browser HTTP call | Browser / Client (Pyodide WASM) | — | The entire question is whether the *browser* fetch layer can carry an Odoo JSON-RPC POST; there is no Python server tier here |
| TLS termination | CDN / Edge (ACA managed ingress) | — | Browser trusts the `*.azurecontainerapps.io` managed cert; godoo does no TLS itself |
| CORS preflight (OPTIONS) | API / Ingress (ACA `corsPolicy`) | — | D-04: reverse-proxy-style at the ingress, NOT an Odoo controller — ACA answers OPTIONS before the request reaches Odoo |
| Odoo JSON-RPC business logic | API / Backend (Odoo container) | — | `common.authenticate` + `object.execute_kw` over `/jsonrpc` |
| Data persistence | Database (Postgres container) | — | **Ephemeral** — Postgres-in-ACA loses state on scale-to-zero (see Pitfall 1) |
| Self-destruct teardown | Control plane (Logic App + managed identity) | ARM async delete | Image-less Consumption Logic App calls `management.azure.com` DELETE on the RG with RG-scoped Contributor |
| Transport injection seam | Client config (`OdooClientConfig.transport_factory`) | — | The custom `pyfetch` transport plugs in here; no core change |

## Standard Stack

This is a spike — the "stack" is **spike tooling**, not shipped dependencies. Nothing here goes into any `pyproject.toml` (D-06, D-09).

### Core (spike runtime, loaded in-browser)
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Pyodide | 0.29.4 (latest stable) | The browser CPython runtime under test | The shared runtime for Marimo/JupyterLite/stlite/PyScript (SEED-001); D-01 raw page hand-loads `pyodide.js` |
| CPython (in Pyodide) | **3.13** (since Pyodide 0.28; 0.29.x is 3.13.x) | The interpreter version that gates `import godoo` (>=3.14) | Confirms D-07: the full package will NOT import; transport tested in isolation |
| `micropip` | bundled with Pyodide | In-page package install for strategy 2 | Standard Pyodide install mechanism |
| `pyodide.http.pyfetch` | bundled with Pyodide | The fetch-backed async HTTP primitive for strategy 3 | Native Pyodide API; the maintainable transport foundation |

### Supporting (per-strategy, spike-only)
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| stock `httpx` | whatever `micropip install httpx` resolves (pure-Python wheel) | Strategy 1 — expected to FAIL on raw socket I/O | Load via micropip; attempt `AsyncClient().post(...)`; capture traceback |
| `pyodide-httpx` | **0.2.0** (released 2025-02-16, `requires-python >=3.12`) | Strategy 2 — patches httpx via `pyfetch`+`run_sync` | `micropip.install(["pyodide-httpx", "ssl"])` then `patch_httpx()` |
| custom `pyfetch` `AsyncTransport` | spike prototype (D-09) | Strategy 3 — implements the `Transport` Protocol; the "go" candidate | Inject via `transport_factory`; tested standalone against `/jsonrpc` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| custom `pyfetch` transport | `urllib3 >=2.2.0` native Emscripten + httpx-on-urllib3 | httpx does not use urllib3 as its transport (it has its own `httpcore`); `urllib3` native support helps `requests`/`pyodide-http`, NOT httpx directly. Not a clean fit for godoo's httpx-based `JsonRpcTransport`. |
| Logic App self-destruct | ACA scheduled Job running `az group delete` | Job needs a container image + the `az` CLI baked in; Logic App is image-less and calls the ARM REST DELETE directly. **Recommend Logic App** (D-05 lean confirmed). |
| Postgres container in ACA | Azure DB for PostgreSQL Flexible Server | Bills continuously, cannot scale to zero — violates the ≈zero-idle-cost intent (D-02 explicitly rejects it). |
| ACA managed-cert FQDN | self-signed / mkcert cert | Browser-trust pain; D-03 explicitly chose managed cert to avoid it. |

**Installation (in-page, spike only — NOT a pyproject change):**
```python
# Strategy 1 (expected to fail):
await micropip.install("httpx")
# Strategy 2:
await micropip.install(["pyodide-httpx", "ssl"])
# Strategy 3: no install — uses bundled pyodide.http.pyfetch
```

**Version verification performed:**
- Pyodide latest stable = **0.29.4**; built with **Python 3.13** since 0.28 `[CITED: github.com/pyodide/pyodide/releases, pyodide.org changelog]`.
- `pyodide-httpx` latest = **0.2.0**, released **2025-02-16**, `Requires: Python >=3.12` `[CITED: pypi.org/project/pyodide-httpx/]`.
- PEP 776 (Emscripten Runtime support) + PEP 783 (Emscripten Packaging) restore Emscripten as a CPython **tier-3 target from Python 3.14** `[CITED: Pyodide release search; PEP 776/783]`.

## Package Legitimacy Audit

> The spike installs `pyodide-httpx` and `httpx` **in-browser via micropip only**. Neither enters any `pyproject.toml` (D-06/D-09), so the slopcheck/registry gate applies as documentation diligence rather than a dependency-tree change. slopcheck was **not run** in this session; the packages below are tagged from registry + authoritative-source cross-checks. The planner does **not** need a `checkpoint:human-verify` install gate because no project dependency manifest is modified — but the spike author should pin exact versions in the HTML page.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `httpx` | PyPI | mature (years) | very high | github.com/encode/httpx | not run | Approved (stock, well-known) — used to *demonstrate failure*, not to ship |
| `pyodide-httpx` | PyPI | ~1 yr (0.2.0 = 2025-02-16) | low (3 GitHub stars, niche) | github.com/CNSeniorious000/pyodide-httpx | not run | Approved for **spike-only** in-page use; `[WARNING: low-maintenance third-party patch — 3 stars, 17 commits. NEVER add to any pyproject.toml (D-06). Pin ==0.2.0 in the HTML page.]` |
| `pyodide-http` | PyPI | mature | moderate | github.com/koenvo/pyodide-http | not run | Reference only — does NOT patch httpx (patches requests/urllib/urllib3); not used by the spike directly |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious:** `pyodide-httpx` is low-popularity but is the legitimate, author-attributed (CNSeniorious000, building on Hood Chatham/Cloudflare's work) httpx patch referenced from Pyodide discussion #4999. Spike-only; never a shipped dependency. `[ASSUMED: legitimacy via authoritative discussion thread, not slopcheck]`

## OD-3 Resolution (HIGHEST PRIORITY — resolves the genuine researcher conflict)

**The question:** Does `httpx.AsyncClient` work under Pyodide today, and via what mechanism? What Pyodide version ships what httpx?

**Answer (HIGH confidence, multi-source):**

1. **Stock httpx does NOT work natively in Pyodide and is NOT bundled or pre-patched.** httpx's default transport (`httpcore`) opens raw TCP sockets; Emscripten/Pyodide has no POSIX socket layer for outbound network, so this fails. There is no Pyodide-bundled "httpx Fetch adapter." `[VERIFIED: pyodide-http README states it patches requests/urllib/urllib3 — httpx is conspicuously absent; GitHub discussion #4999 "I made a package to patch httpx in pyodide" exists *precisely because* stock httpx does not work; Cloudflare engineering blog describes patching httpx to use Fetch]`. **The CONTEXT-recorded claim that "httpx is bundled + pre-patched in Pyodide ~0.29.x via a Fetch adapter" is FALSE.** The spike's strategy-1 attempt will produce the failing traceback that documents this for SC-2.

2. **What IS true about the ecosystem:**
   - `urllib3 >=2.2.0` has **official native Emscripten support** (uses JS `fetch`, falls back to `XMLHttpRequest`). This is real and current `[CITED: urllib3 emscripten docs]`. But httpx does not route through urllib3 — so this does not make httpx work.
   - `pyodide-http` (koenvo) patches `requests` / `urllib` / `urllib3` — **not httpx** `[VERIFIED: pyodide-http README]`.
   - `pyodide-httpx` 0.2.0 (CNSeniorious000) patches httpx specifically, via `pyfetch` + `run_sync`, supporting both sync and `AsyncClient` `[VERIFIED: PyPI + discussion #4999]`.
   - Cloudflare's Pyodide team patches httpx/aiohttp onto the Fetch API for Workers; **"the httpx patch is quite simple — fewer than 100 lines of code"** `[CITED: blog.cloudflare.com/python-workers]`. This is the engineering basis for strategy 3 being maintainable (D-10 "go" candidate).

3. **The "NotImplementedError on POSIX sockets" half of the conflict is the accurate half** — raw socket calls are unavailable under Emscripten, which is exactly why stock httpx fails and why a fetch-based transport is required.

**Planning consequence:** The verdict's expected shape is *"stock httpx fails (traceback); pyodide-httpx works but is a brittle third-party patch; the custom pyfetch transport works and is maintainable → GO via strategy 3 (or conditional-go if only strategy 2 succeeds)."* The spike must still **prove this in-browser** (SC-1) — documentation alone does not satisfy BROWSER-02.

## The Three Transport Strategies (D-06) — concrete how-to + failure modes

### Strategy 1 — stock httpx via "Pyodide's Fetch adapter"
- **How to load:** `await micropip.install("httpx")`; then `async with httpx.AsyncClient() as c: r = await c.post(url, json=payload)`.
- **Expected result:** **FAIL.** No Fetch adapter is auto-installed; httpx tries socket I/O.
- **Failure mode to capture (SC-2):** an `OSError` / `BlockingIOError` / connection error originating from `httpcore`/socket layer under Emscripten (the exact exception text is the evidence — capture `repr(exc)` and the full traceback to the console/`08-SPIKE.md`). Do **not** pre-write the exact error string; record what the browser actually emits.
- **Why test it anyway (D-06):** SC-2 requires documenting that the "easy path" does not work, with the real traceback.

### Strategy 2 — `pyodide-httpx` 0.2.0
- **How to load:** `await micropip.install(["pyodide-httpx", "ssl"])` then:
  ```python
  from pyodide_httpx import patch_httpx
  patch_httpx()           # monkeypatches httpx transports onto pyfetch
  import httpx
  async with httpx.AsyncClient() as c:
      r = await c.post(url, json=payload)
  ```
- **Status/maintenance:** v0.2.0 (2025-02-16), `requires-python >=3.12`, MPL-2.0, **3 stars / 17 commits** — low community footprint. Author proposed merging into `pyodide-http`; not yet upstreamed. Supports `AsyncClient`.
- **Expected result:** **WORKS** for a cross-origin POST (it is purpose-built). 
- **D-10 classification:** A success here alone is **conditional / no-go to *ship*** — it is a brittle, low-maintenance third-party patch and `[WARNING]` must never enter a `pyproject.toml`. Record it as "works as a spike, not a shipping dependency."
- **Failure modes to watch:** the `ssl` package dependency must be installed alongside; version skew between `pyodide-httpx` 0.2.0 and the httpx version micropip resolves can break the monkeypatch — capture the resolved httpx version in the evidence.

### Strategy 3 — custom `pyfetch`-backed `AsyncTransport` (the maintainable "go" candidate)
This is the strategy the **transport seam was built for** (Phase 6, BROWSER-01). The prototype implements the `Transport` Protocol structurally and is injected via `transport_factory` — **no core change**.

**EXACT `Transport` Protocol surface** (verified from `packages/godoo-client/src/godoo/client/rpc/protocol.py` — note the path is `godoo/client/rpc/`, NOT `godoo/rpc/` as CLAUDE.md states; CLAUDE.md is stale here):
```python
class Transport(Protocol):
    @property
    def session(self) -> OdooSessionInfo | None: ...
    async def authenticate(self, username: str, password: str) -> OdooSessionInfo: ...
    async def call(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any: ...
    def logout(self) -> None: ...                # NOTE: sync
    async def aclose(self) -> None: ...
```
`OdooSessionInfo` is a dataclass `OdooSessionInfo(uid: int, session_id: str, db: str)` at `godoo/client/rpc/types.py`.

**EXACT `transport_factory` signature** (verified from `godoo/client/client.py:91`):
```python
transport_factory: Callable[[OdooClientConfig], Transport] | None = None
# Called once in OdooClient.__init__ (client.py:99-102):
#   self._transport = config.transport_factory(config) if config.transport_factory else JsonRpcTransport(...)
```
The factory is **synchronous** (`Callable[..., Transport]`) — it constructs the transport eagerly; the transport's *methods* are async. The prototype therefore must be constructible synchronously (no `await` in `__init__`); all network work happens in `authenticate`/`call`. (Phase 6 deferred "async transport factory" — see Phase 6 deferred ideas; the spike confirms sync construction is sufficient.)

**The wire path to replicate** (verified from `JsonRpcTransport`, `transport.py`): the prototype must POST to `{base_url}/jsonrpc` with a JSON-RPC 2.0 envelope. `authenticate` uses `service="common", method="authenticate", args=[db, username, password, {}]` and stores `OdooSessionInfo(uid, session_id=uuid4, db)`. `call` uses `service="object", method="execute_kw", args=[db, uid, password, model, method, args, kwargs]`. (The spike prototype may simplify error categorization — full `_categorize_error` parity is not required for evidence, but mirroring the happy path + raising on `"error"` in the response is.)

- **Expected result:** **WORKS** and is **maintainable** → satisfies the D-10 "go" bar.
- **Failure modes to watch:** `pyfetch` returns a `FetchResponse` whose `.json()` is itself awaitable (`await resp.json()`); forgetting the second `await` is the classic bug. CORS preflight failures surface as opaque `TypeError: Failed to fetch` in the browser (see Pitfall 2). Mixed-content (an `http://` URL from an `https://` page, or vice versa) is blocked by the browser — the ACA HTTPS FQDN (D-03) avoids this.

See **Code Examples** for the full strategy-3 prototype skeleton and the `pyfetch` POST recipe.

## Python-Floor Reality (D-07, BROWSER-03)

- **Pyodide ships CPython 3.13** (0.28 introduced 3.13; 0.29.x continues it). CONTEXT's "3.13.2" is consistent with this `[CITED: pyodide.org changelog / releases]`.
- The full `godoo` package is `requires-python >=3.14` on **all** packages (`godoo-client`, `godoo-introspection`, `godoo-testcontainers`, `godoo-meta` — verified). Therefore `import godoo` **cannot** run under Pyodide 0.29.x. D-07's isolation mandate is correct and non-negotiable: test a **minimal standalone `AsyncTransport`** against `/jsonrpc`, never `import godoo`.
- **Emscripten is a CPython tier-3 target *from Python 3.14*** (PEP 776 runtime support, PEP 783 packaging; steering council approved Oct 2024). This is the crux of the floor recommendation: a *properly supported* Pyodide CPython 3.14 is on the horizon but **not yet shipped** in stable Pyodide.
- **Framing for the verdict (both options, author picks):**
  - **Option A (recommended default): "Defer a shipped browser build until Pyodide ships CPython >=3.14."** Rationale: keeps a single `>=3.14` floor across the whole monorepo; aligns with the official Emscripten-from-3.14 trajectory; avoids a forked browser-only build matrix. The spike still proves the transport works *today* (on 3.13 in isolation), so when Pyodide 3.14 lands, BROWSER-F1 is low-risk.
  - **Option B (alternative): "Drop `requires-python` to `>=3.12` for a browser-specific build."** Rationale: enables shipping a browser variant *now* on current Pyodide; cost is a divergent floor and a separate build/test matrix for the browser extra. Note `pyodide-httpx` itself is `>=3.12`, so 3.12 is the realistic floor if shipping today.
- The Python floor is an **output recommendation**, not something the spike engineers around (D-07).

## Azure Throwaway Endpoint (D-02..D-05) — Bicep/CLI specifics for SC-1

### Topology (one ACA app, multi-container pod)
- A single **dedicated resource group** `rg-godoo-pyodide-spike` holds everything (D-05).
- One Container App with **two containers in the same `template.containers[]`** (multi-container pod): the Odoo container and a Postgres container `[CITED: ACA multi-container docs; mcr.microsoft.com/k8se/services/postgres:14 is the MS-published dev Postgres image]`. They share `localhost` networking inside the replica, so Odoo connects to Postgres on `127.0.0.1:5432`.
- **External ingress** on the Odoo container's port (Odoo HTTP = 8069) with the managed cert on the `*.azurecontainerapps.io` FQDN (D-03) → browser-trusted HTTPS, non-localhost. This satisfies SC-1's TLS-via-fetch bar.

> **CRITICAL PLANNING CONSTRAINT (see Pitfall 1):** Postgres-as-a-container-in-the-pod is **ephemeral and not persistent**, and `minReplicas: 0` (D-02) means the *whole pod* (Odoo **and** Postgres) scales to zero, **losing the database** on every cold-stop. The spike must (a) accept that the DB is re-created on each cold start (Odoo DB-init on boot), OR (b) keep `minReplicas: 1` for the brief spike window and rely on the self-destruct (D-05) for cost control rather than scale-to-zero. The planner must resolve this explicitly — it directly contradicts the naive reading of D-02. **Recommendation:** run the spike with `minReplicas: 1` for the active test window (cost is trivial for the short TTL) and let the Logic App self-destruct (D-05) deliver the ≈zero-idle-cost guarantee by deleting the entire RG. Document this as the reconciliation of D-02's intent.

### CORS on the ACA ingress (D-04) — verified config
ACA answers OPTIONS preflight **automatically** when `corsPolicy` is set on `ingress` — no Odoo controller needed (satisfies D-04's reverse-proxy-style requirement) `[CITED: learn.microsoft.com/azure/container-apps/cors]`.

ARM/Bicep `ingress.corsPolicy` shape (verified):
```bicep
ingress: {
  external: true
  targetPort: 8069
  transport: 'http'
  corsPolicy: {
    allowedOrigins: [ spikePageOrigin ]   // e.g. 'https://<user>.github.io' or 'http://localhost:8000' if served locally over plain HTTP — see note
    allowedMethods: [ 'POST', 'OPTIONS' ] // JSON-RPC is POST; OPTIONS for preflight
    allowedHeaders: [ 'content-type' ]    // the only header godoo's POST sets
    allowCredentials: false               // JSON-RPC auth is in the body, NOT cookies — keep false
    maxAge: 3600
  }
}
```
- **`allowCredentials` MUST stay `false`** if `allowedOrigins` is ever `*`, and even with an explicit origin, godoo's `/jsonrpc` auth carries credentials in the JSON body (db/user/password), not a cookie — so `false` is correct and avoids the browser's "credentials + wildcard" rejection.
- **Exact allowed-origin value (Claude's discretion):** must be the **exact scheme+host+port the spike page is served from**. If the spike HTML is opened as a `file://` URL the Origin is `null` and CORS will reject it — the page MUST be served over HTTP(S) from a real origin. **Recommendation:** serve the raw page from a simple static host whose origin you control (e.g. GitHub Pages `https://<user>.github.io` for a true cross-origin HTTPS-to-HTTPS test, which is the cleanest SC-1 demonstration), OR a `localhost:PORT` static server (cross-origin but plain-HTTP page → HTTPS endpoint, which is still a valid cross-origin + mixed-context exercise; note SC-1's localhost exclusion applies to the *Odoo endpoint*, not the page host). Set `allowedOrigins` to that exact origin.

### Self-destruct (D-05) — Logic App (recommended) vs ACA Job
**Recommend: Consumption Logic App** (image-less, native ARM HTTP action). Mechanism:
- A **recurrence trigger** (or a single Delay action) waits the TTL (e.g. 60 min), then an **HTTP action** calls the ARM REST DELETE on the RG:
  ```
  DELETE https://management.azure.com/subscriptions/{subscriptionId}/resourcegroups/rg-godoo-pyodide-spike?api-version=2021-04-01
  ```
  authenticated with the Logic App's **managed identity** (`authentication.type = 'ManagedServiceIdentity'`, audience `https://management.azure.com/`).
- The ARM RG-delete is **async** — it returns 202 and continues server-side after the Logic App (and the resources it is deleting, including itself) are torn down `[CITED: Azure Resource Groups Delete REST API; self-destruct pattern blog]`.
- **Managed identity + role assignment in the SAME Bicep** (D-05):
  ```bicep
  resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = { name: 'id-spike-destruct', location: location }

  // RG-scoped Contributor (built-in role b24988ac-6180-42a0-ab88-20f7382dd24c)
  resource ra 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
    name: guid(resourceGroup().id, uami.id, 'Contributor')
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
      principalId: uami.properties.principalId
      principalType: 'ServicePrincipal'   // REQUIRED for UAMI to avoid intermittent replication errors
    }
  }
  ```
  RG-scoped Contributor is sufficient to delete its own RG (D-05 correct).
- **ACA Job alternative (rejected lean):** a scheduled Job needs a container image with `az` CLI baked in to run `az group delete`. More moving parts than the image-less Logic App. Use only if Logic App ARM-action auth proves fiddly.
- **GitHub Actions backstop: rejected (D-05).** Do not add one.

### Minimal Odoo modules the test DB needs (Claude's discretion)
- **Just the `base` module** (always installed). `base` provides `res.users` (for `common.authenticate`) and trivially-readable models (`res.users`, `res.company`, `res.partner`). A JSON-RPC `execute_kw('res.users', 'read', [[uid]], {'fields': ['login','name']})` or `('res.users','search_read',...)` is the trivial model-read that proves the round-trip — no extra modules required.
- Initialize the Odoo DB with admin credentials via env (`--init base`, or Odoo's auto DB-create on first boot with `ADMIN_PASSWD`/`-d` set). The official `odoo` Docker image plus the Postgres container env (`POSTGRES_USER/PASSWORD/DB`) is the standard pairing.

## Architecture Patterns

### System Architecture Diagram
```
                          (cross-origin, HTTPS)
 ┌──────────────────────┐   POST /jsonrpc      ┌─────────────────────────────────────┐
 │  Browser tab          │  ───────────────────▶│ Azure Container Apps ingress         │
 │  (served from origin  │   OPTIONS preflight  │  • managed TLS cert (*.azurecontainer│
 │   O = the spike host) │  ◀───── 204 + CORS ──│    apps.io)  → browser-trusted       │
 │                       │   hdrs (corsPolicy)  │  • corsPolicy answers OPTIONS        │
 │  Pyodide 0.29 (3.13)  │                      │    (allowedOrigins=[O])              │
 │   ├ S1 stock httpx ───┼─▶ FAIL (socket I/O)  └──────────────┬──────────────────────┘
 │   ├ S2 pyodide-httpx ─┼─▶ pyfetch (works,                    │ localhost (in-pod)
 │   │     [brittle]     │     brittle)         ┌───────────────▼───────────────┐
 │   └ S3 custom         │                      │ Replica (multi-container pod)  │
 │      AsyncTransport ──┼─▶ pyfetch (works,    │  ┌──────────┐   ┌───────────┐  │
 │      via transport_   │     maintainable→GO) │  │  Odoo    │──▶│ Postgres  │  │
 │      factory          │                      │  │ :8069    │   │ :5432     │  │
 └──────────────────────┘                       │  └──────────┘   └───────────┘  │
                                                │   (DB ephemeral; see Pitfall 1)│
                                                └────────────────────────────────┘
   ┌─────────────────────────────────────────────┐
   │ Self-destruct (same RG, same Bicep)          │   after TTL:  DELETE management.azure.com
   │  UAMI ──(RG-scoped Contributor)── Logic App ─┼──────────────▶ /resourcegroups/rg-...  (async)
   └─────────────────────────────────────────────┘
```

### Recommended Spike Artifact Structure (D-09 — non-shipping, committed evidence)
```
spikes/08-pyodide/                 # or .planning/phases/08-pyodide-spike/artifacts/
├── index.html                     # raw Pyodide page (D-01): loads pyodide.js, runs all 3 strategies
├── transport_pyfetch.py           # the custom AsyncTransport prototype (strategy 3) — seeds BROWSER-F1
├── infra/
│   ├── main.bicep                 # ACA env + multi-container app + ingress corsPolicy
│   ├── selfdestruct.bicep         # UAMI + RG-scoped Contributor + Logic App (D-05)
│   └── deploy.md / deploy.sh       # az CLI deploy + teardown notes
└── README.md                      # how to run the spike + where the verdict lives
```
**NOT** under any `packages/*/src/` (would pull it into the >=3.14 / mypy-strict shipped surface). The planner decides whether to ruff/format the spike dir (cosmetic) — it must NOT be in the packaged build.

### Pattern: custom Transport implements the Protocol structurally
**What:** A standalone class with the 5 Protocol members, constructed synchronously, doing all I/O via `pyfetch` in the async methods.
**When to use:** Strategy 3.
**Why it satisfies D-10:** It reuses the *existing shipped seam* (`transport_factory`) — no fork of core, no monkeypatch, ~<100 LOC (Cloudflare's number for the equivalent httpx patch). That is "maintainable/sustainable to ship."

### Anti-Patterns to Avoid
- **`import godoo` inside Pyodide** — fails the >=3.14 gate (D-07). Test the transport in isolation.
- **Adding `pyodide-httpx` to any `pyproject.toml`** — D-06 forbids it; it is in-page micropip only.
- **`file://` spike page** — Origin is `null`; CORS rejects. Serve from a real HTTP(S) origin.
- **`allowCredentials: true` with wildcard origin** — browser rejects; and godoo doesn't use cookie auth anyway.
- **Relying on `minReplicas: 0` to keep the DB** — scale-to-zero destroys the Postgres container's data (Pitfall 1).
- **Forgetting the second `await`** on `pyfetch(...).json()` — `FetchResponse.json()` is itself a coroutine.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser HTTP from Python | A custom XHR/socket shim | `pyodide.http.pyfetch` (bundled) | Native fetch-backed; handles the browser networking boundary correctly |
| TLS for a browser-trusted endpoint | self-signed/mkcert + browser trust dance | ACA managed cert on `*.azurecontainerapps.io` (D-03) | Browser-trusted out of the box; avoids cert-import pain |
| CORS preflight handling | An Odoo controller / nginx sidecar | ACA `ingress.corsPolicy` (D-04) | ACA auto-answers OPTIONS at the ingress |
| httpx-in-browser (if you wanted it generic) | Re-deriving the patch from scratch | reference `pyodide-httpx` 0.2.0 / Cloudflare's <100-LOC patch | Already solved; for godoo the *custom transport* is cleaner than patching httpx globally |
| Teardown automation | A cron VM / external scheduler | image-less Consumption Logic App + ARM DELETE (D-05) | No image, no CLI to maintain; native ARM async delete |

**Key insight:** The entire browser-HTTP problem in Pyodide reduces to "route through the Fetch API." godoo's Phase-6 transport seam means the *correct* answer (strategy 3) is not a hack but the intended extension point — which is exactly why D-10 makes it the "go" candidate.

## Common Pitfalls

### Pitfall 1: Postgres-in-pod + `minReplicas: 0` silently destroys the test DB
**What goes wrong:** D-02 says Postgres-as-container + `minReplicas: 0`. But the Postgres container shares the pod lifecycle; scale-to-zero stops it and its data is gone (no persistent volume). Next cold start = empty DB = auth fails.
**Why it happens:** ACA multi-container pods are stateless by default; the dev Postgres image has no persistence wired.
**How to avoid:** For the active spike window run `minReplicas: 1`; rely on the Logic App self-destruct (D-05) — not scale-to-zero — for cost control. Document this as the reconciliation of D-02's ≈zero-idle-cost intent. (Alternative: accept Odoo re-initializing `base` on each boot, which adds cold-start latency.)
**Warning signs:** Intermittent auth failures after the app idles; "database does not exist" from Odoo on a cold request.

### Pitfall 2: CORS/mixed-content failures surface as opaque `TypeError: Failed to fetch`
**What goes wrong:** A preflight failure, a missing `Access-Control-Allow-Origin`, or a mixed-content block all show up in Pyodide as a generic `TypeError` with no useful body — easy to misread as "pyfetch is broken."
**Why it happens:** The browser blocks the request before any response reaches Python; the error is intentionally opaque for security.
**How to avoid:** Verify CORS in the **browser devtools Network tab** (look at the OPTIONS response headers) BEFORE blaming the transport. Confirm `allowedOrigins` exactly matches the page origin. Ensure page and endpoint scheme are compatible (HTTPS page → HTTPS endpoint is cleanest). Capture the devtools Network evidence alongside the Python traceback in `08-SPIKE.md`.
**Warning signs:** All three strategies "fail" identically with `Failed to fetch` — that's a CORS/origin problem, not a transport problem.

### Pitfall 3: Conflating "stock httpx works" with "pyodide-httpx works"
**What goes wrong:** After `patch_httpx()` succeeds (strategy 2), it's tempting to record "httpx works in Pyodide" — but that's the *patched* httpx. Stock httpx (strategy 1) still fails.
**Why it happens:** Same `import httpx` symbol; the monkeypatch is invisible.
**How to avoid:** Run strategy 1 in a **fresh page/runtime** with no `patch_httpx()` applied; record its traceback separately. Per-strategy isolation is what SC-2 demands.

### Pitfall 4: `pyfetch().json()` double-await + response reuse
**What goes wrong:** `FetchResponse.json()` returns a coroutine; `body` can only be consumed once.
**How to avoid:** `data = await (await pyfetch(...)).json()` — or capture the response, then `await resp.json()` exactly once. Don't also call `resp.string()` on the same response.

### Pitfall 5: `requires-python >=3.14` on ALL packages blocks even partial import
**What goes wrong:** Trying to `micropip.install` the godoo wheel under Pyodide fails resolution on the 3.14 marker.
**How to avoid:** Don't install the wheel at all (D-07). Hand-write the minimal `AsyncTransport` in the spike page / `transport_pyfetch.py`. The prototype need not satisfy the gate (D-09).

## Code Examples

### `pyfetch` POST to /jsonrpc (strategy 3 core)
```python
# Source: pyodide.org/en/stable/usage/api/python-api/http.html (pyfetch) + godoo JsonRpcTransport wire path
import json
from pyodide.http import pyfetch

async def jsonrpc(base_url: str, params: dict) -> dict:
    payload = {"jsonrpc": "2.0", "method": "call", "id": 1, "params": params}
    resp = await pyfetch(
        f"{base_url}/jsonrpc",
        method="POST",
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload),
        # mode/credentials default to browser CORS behaviour; do NOT set credentials='include'
        # (godoo auth is in the body, not cookies) — keeps allowCredentials=false valid
    )
    data = await resp.json()          # NOTE: .json() is itself awaitable
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["result"]
```

### Custom AsyncTransport prototype skeleton (strategy 3, D-09 evidence — seeds BROWSER-F1)
```python
# Source: structural conformance to godoo/client/rpc/protocol.py Transport Protocol
# NON-SHIPPING spike artifact — lives in spikes/, not packages/*/src/. Need not target 3.14.
from __future__ import annotations
import json, uuid
from dataclasses import dataclass
from typing import Any
from pyodide.http import pyfetch

@dataclass
class OdooSessionInfo:           # mirror of godoo.client.rpc.types.OdooSessionInfo
    uid: int
    session_id: str
    db: str

class PyfetchTransport:          # structurally satisfies the 5-member Transport Protocol
    def __init__(self, base_url: str, db: str) -> None:
        self._base = base_url.rstrip("/")
        self._db = db
        self._session: OdooSessionInfo | None = None
        self._password: str | None = None

    @property
    def session(self) -> OdooSessionInfo | None:
        return self._session

    async def _rpc(self, params: dict[str, Any]) -> Any:
        resp = await pyfetch(f"{self._base}/jsonrpc", method="POST",
                             headers={"Content-Type": "application/json"},
                             body=json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1, "params": params}))
        data = await resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data["result"]

    async def authenticate(self, username: str, password: str) -> OdooSessionInfo:
        uid = await self._rpc({"service": "common", "method": "authenticate",
                               "args": [self._db, username, password, {}]})
        if not uid:
            raise RuntimeError("auth failed")
        self._session = OdooSessionInfo(uid=uid, session_id=str(uuid.uuid4()), db=self._db)
        self._password = password
        return self._session

    async def call(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        assert self._session is not None
        return await self._rpc({"service": "object", "method": "execute_kw",
                                "args": [self._db, self._session.uid, self._password, model, method, args, kwargs]})

    def logout(self) -> None:
        self._session = None
        self._password = None

    async def aclose(self) -> None:
        return None  # pyfetch holds no client to close
```
(Injected in real godoo via `OdooClientConfig(..., transport_factory=lambda cfg: PyfetchTransport(cfg.url, cfg.database))` — but in the spike it is exercised standalone, not through `import godoo`.)

### ACA ingress corsPolicy (Bicep) — see Azure Infra section for the full block
### Logic App self-destruct UAMI + roleAssignment (Bicep) — see Azure Infra section

## ADR Convention (D-08) — where the go/no-go decision lives

**Scout result:** the repo has **no existing ADR directory or precedent.** Checked `docs/`, `docs/adr/`, `.planning/adrs/`, `.planning/decisions/`, `mkdocs.yml` nav (Home / Getting Started / Services / Guides / API Reference / Testing — no ADR/decisions section). No `*adr*` files exist outside `.venv`. `[VERIFIED: filesystem scan + mkdocs.yml read]`

**Recommendation for the planner (establish the convention this phase):**
- **Location:** create **`docs/adr/`** (MADR-style, the de-facto Python-ecosystem default) and add an **`ADR` section to `mkdocs.yml` nav** so v2.0 planning (and users) can read it. `docs/` is already the mkdocs source root, so the ADR ships in the docs site — appropriate for a durable, fleet-readable decision (D-08 says "v2.0 planning reads it directly").
  - *Alternative considered:* `.planning/adrs/` — keeps it in the planning surface but NOT in the published docs site; D-08's "v2.0 planning reads it" leans toward planning-adjacent, but a durable architecture decision about a *shipped capability direction* belongs in `docs/`. **Recommend `docs/adr/`**; let Marc confirm at plan/discuss time (this is the one genuinely new convention being introduced — flag it as an assumption).
- **Numbering:** `docs/adr/0001-pyodide-browser-go-no-go.md` (zero-padded sequential, MADR convention). This is ADR-0001 since none exist.
- **Split (D-08):** *evidence* (per-strategy worked/failed + tracebacks + Python-floor rec) → **`.planning/phases/08-pyodide-spike/08-SPIKE.md`**; *the durable go/no-go decision* (with status `accepted`, context, decision, consequences, and the v2.0-escalation note) → **`docs/adr/0001-...md`**. The ADR references the SPIKE doc for evidence.

## Security Domain

> `security_enforcement` is null in config (treat as ENABLED per agent default). ASVS L1, block-on: high. The Azure infra has a real, if short-lived, threat surface — the planner needs this for its `<threat_model>` block.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes (Odoo admin creds in the spike) | Throwaway DB, throwaway admin password, never reused; password lives in body over HTTPS only |
| V3 Session Management | minimal | godoo session is a client-side `uuid4` + uid; no server cookie in the JSON-RPC path |
| V4 Access Control | **yes (HIGH)** | UAMI has RG-scoped **Contributor** — can delete its own RG. Scope to exactly the spike RG; never subscription scope. `principalType: 'ServicePrincipal'` set. |
| V5 Input Validation | low | Spike POSTs a fixed JSON-RPC envelope; no user-supplied input surface |
| V6 Cryptography | n/a (delegated) | TLS via ACA managed cert; no hand-rolled crypto |
| V1/V14 Config | **yes (HIGH)** | Publicly-reachable Odoo with CORS — see threats below |

### Known Threat Patterns for this spike
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Public Odoo endpoint with admin login reachable from the internet for the TTL window | Spoofing / Elevation | Strong throwaway admin password; short TTL; self-destruct deletes the whole RG; never reuse the password elsewhere |
| UAMI with RG-scoped Contributor could delete more than intended / be abused if leaked | Elevation / Tampering | Scope to the single spike RG only (never subscription); UAMI lifetime is the RG lifetime; role assignment torn down with the RG |
| Overly-permissive CORS (`allowedOrigins: '*'`) lets any site call the endpoint | Information Disclosure | Scope `allowedOrigins` to the **exact** spike page origin (D-04); `allowCredentials: false` |
| Self-destruct fails → endpoint + creds linger billing/exposed | Denial-of-control | Verify the Logic App fired (it deletes the RG); a manual `az group delete` is the documented backstop in `deploy.md` (NOT GitHub Actions — D-05) |
| Secrets (Odoo admin password, Postgres password) committed in Bicep/HTML | Information Disclosure | Per secrets-handling rule: pass via deploy-time parameters / `az` env, never hardcode in the committed Bicep or `index.html`. Use Bicep `@secure()` params. |
| Mixed-content / downgraded transport | Tampering | HTTPS-only via the managed cert (D-03); the page should be HTTPS too for the cleanest demonstration |

## Validation Architecture

> `nyquist_validation` is **false** in config — automated test-gating is off for this milestone. Included here narrowly because the spike's *evidence capture* is itself testable and SC-2 demands per-strategy pass/fail with error output. This is **manual/observational** validation, not an automated pytest suite.

### Per-strategy evidence capture (the spike's "validation")
| What | How it's validated | Pass/Fail recorded as |
|------|--------------------|-----------------------|
| SC-1: actual JSON-RPC call, cross-origin, HTTPS, real TLS Odoo | Run the raw page (D-01) against the ACA managed-cert FQDN; observe a non-error `result` in the response | A captured successful `execute_kw` result (e.g. `res.users` read) pasted into `08-SPIKE.md` + devtools Network screenshot |
| SC-2: which of 3 strategies worked/failed + error output | Run each strategy in isolation (fresh runtime for S1); capture `repr(exc)` + traceback for failures, `result` for successes | A 3-row table in `08-SPIKE.md` with verbatim tracebacks |
| SC-3: Python-floor recommendation | Document Pyodide CPython = 3.13 vs godoo `>=3.14`; state Option A/B with rationale | A "Python Floor" section in `08-SPIKE.md` |
| SC-4: explicit go/no-go | Apply the D-10 bar to the strategy results | `accepted` ADR at `docs/adr/0001-...md` with `go` / `no-go` / `conditional` |

**No automated test harness is in scope** (this is a throwaway browser spike; `nyquist_validation: false`). The "test" is the human-run page + captured artifacts. Do NOT add a pytest suite for the spike.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Azure subscription + `az` CLI | Provisioning the ACA endpoint (D-02..D-05) | unverified (Marc's machine) | — | None — SC-1 requires a real TLS-terminated cloud Odoo; no fallback. Planner must confirm `az login` + subscription access as a wave-0 gate. |
| Bicep CLI (`az bicep`) | Deploying main.bicep / selfdestruct.bicep | unverified | — | Author ARM JSON directly (more verbose) |
| A browser (Chromium/Firefox) | Running the raw Pyodide page (D-01) | yes (dev machine) | current | — |
| Static HTTP(S) host for the spike page | Serving a real Origin (not `file://`) | trivially available | — | `python -m http.server` for a localhost origin |
| Docker (for `godoo-testcontainers`) | NOT needed — spike uses cloud Odoo | n/a | — | n/a (out of scope) |

**Missing dependencies with no fallback:** Azure subscription access — the planner MUST make `az login` + an active subscription a Wave-0 precondition; SC-1's "real TLS-terminated Odoo endpoint" cannot be satisfied locally.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| "Pyodide can't do HTTP" | `pyfetch` (async) + `pyxhr` (sync, added in 0.29) + native `urllib3` Emscripten | urllib3 2.2.0 (2024); pyxhr in Pyodide 0.29 | Browser Python HTTP is solved *for fetch-based clients*; httpx still needs a patch/custom transport |
| Emscripten = unofficial Pyodide hack | Emscripten = official CPython **tier-3 target from 3.14** | PEP 776/783, approved Oct 2024 | The Python-floor recommendation hinges on this — proper support arrives with 3.14 |
| httpx "just works" assumption | httpx needs a Fetch-based transport (custom or `pyodide-httpx`) | ongoing | Directly resolves OD-3; shapes the verdict |

**Deprecated/outdated:**
- The `/jsonrpc` (and `/xmlrpc`, `/xmlrpc/2`) endpoints are **deprecated, scheduled for removal in Odoo 22 (fall 2028)** `[CITED: Odoo 19 external_rpc_api docs]`. Irrelevant for the spike (it works today and godoo's `JsonRpcTransport` already targets `/jsonrpc`), but worth a one-line note in the verdict as a longer-term consideration for any shipped browser build.
- CONTEXT's "httpx bundled + pre-patched in Pyodide 0.29.x" — **outdated/incorrect**; superseded by the OD-3 resolution above.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ADR should live at `docs/adr/0001-...md` (MADR-style) with an mkdocs nav entry | ADR Convention | LOW — no existing convention; this *establishes* one. If Marc prefers `.planning/adrs/`, trivial to relocate. Flag at plan/discuss. |
| A2 | Serving the spike page from GitHub Pages (or a localhost static server) is acceptable for the SC-1 cross-origin demonstration | Azure Infra / CORS | LOW — SC-1 excludes localhost/plain-HTTP for the *Odoo endpoint*, not the page host; HTTPS-to-HTTPS via GitHub Pages is the cleanest. Confirm the page-origin choice. |
| A3 | Running the spike with `minReplicas: 1` (not 0) for the active window, with self-destruct delivering cost control, is the right reconciliation of D-02 | Pitfall 1 / Azure Infra | MEDIUM — contradicts a naive reading of D-02's `minReplicas: 0`. The Postgres-ephemerality constraint is real; planner must surface this to Marc. |
| A4 | `pyodide-httpx` 0.2.0 will successfully patch whatever httpx micropip resolves at spike time | Strategy 2 | MEDIUM — version skew between the patch and resolved httpx could break it; the spike empirically confirms. Capture resolved versions. |
| A5 | The `base` module alone suffices for auth + a trivial model read | Azure Infra (modules) | LOW — `base` always provides `res.users`; standard Odoo. |
| A6 | Stock httpx (strategy 1) will fail under Pyodide | OD-3 / Strategy 1 | LOW — strongly evidenced (pyodide-http omits httpx; the whole reason pyodide-httpx exists). The spike confirms with the actual traceback. |
| A7 | `slopcheck` legitimacy of `pyodide-httpx` (not run this session) | Package Audit | LOW — spike-only, never a shipped dep; legitimacy backed by Pyodide discussion #4999 authorship. |

## Open Questions

1. **ADR location (`docs/adr/` vs `.planning/adrs/`)** — *What we know:* no precedent exists; D-08 wants v2.0 planning to read it. *Unclear:* Marc's preference for docs-site vs planning-surface. *Recommendation:* `docs/adr/0001` + mkdocs nav; confirm at plan/discuss (A1).
2. **`minReplicas: 0` vs DB persistence** — *What we know:* Postgres-in-pod is ephemeral; scale-to-zero loses it. *Unclear:* whether Marc accepts `minReplicas: 1` for the window. *Recommendation:* `minReplicas: 1` + self-destruct for cost (A3).
3. **Spike page hosting origin** — *What we know:* must be a real HTTP(S) origin, not `file://`. *Unclear:* GitHub Pages vs localhost static server. *Recommendation:* GitHub Pages for the cleanest HTTPS-to-HTTPS cross-origin demonstration (A2).
4. **Whether to lint/mypy the spike dir** — *What we know:* it's non-shipping (D-09) and can't target 3.14. *Recommendation:* exclude `spikes/` from the packaged build and the strict-mypy set; optionally `ruff format` for readability. Planner decides.

## Sources

### Primary (HIGH confidence)
- `packages/godoo-client/src/godoo/client/rpc/protocol.py`, `.../rpc/transport.py`, `.../rpc/types.py`, `.../client/client.py` — exact Transport Protocol, wire path, `transport_factory` signature (read from source).
- `.planning/phases/06-transport-seam-typed-models-core/06-CONTEXT.md` — D-06/D-07 Phase 6 transport-seam decisions.
- pyodide.org changelog / github.com/pyodide/pyodide/releases — Pyodide 0.29.4, CPython 3.13 since 0.28.
- pypi.org/project/pyodide-httpx/ — v0.2.0, 2025-02-16, requires-python >=3.12.
- learn.microsoft.com/azure/container-apps/cors — exact `corsPolicy` ARM/Bicep shape, auto-OPTIONS.
- learn.microsoft.com/azure/azure-resource-manager/bicep/scenarios-rbac + roleAssignments template — UAMI role-assignment Bicep.
- learn.microsoft.com REST: Resource Groups - Delete (api-version 2021-04-01) — async RG delete for self-destruct.

### Secondary (MEDIUM confidence)
- github.com/koenvo/pyodide-http (README) — patches requests/urllib/urllib3, NOT httpx.
- github.com/pyodide/pyodide/discussions/4999 — "I made a package to patch httpx in pyodide" (pyodide-httpx origin).
- blog.cloudflare.com/python-workers — "the httpx patch is quite simple — fewer than 100 lines of code"; Fetch-API patching of httpx/aiohttp.
- urllib3.readthedocs.io/.../emscripten.html — native Emscripten support from 2.2.0.
- learn.microsoft.com ACA multi-container docs; mcr.microsoft.com/k8se/services/postgres image.
- odoo.com/documentation/19.0 external_rpc_api — `/jsonrpc` deprecation (Odoo 22).

### Tertiary (LOW confidence — flagged for in-browser confirmation)
- Exact failing exception text for stock httpx under Pyodide — **must be captured empirically** (the spike produces it; do not pre-write it).
- Exact `pyodide-httpx` 0.2.0 ↔ resolved-httpx version compatibility — confirm at spike time.

## Metadata

**Confidence breakdown:**
- OD-3 resolution (httpx fails / fetch required): **HIGH** — three independent authoritative sources (pyodide-http README omission, discussion #4999, Cloudflare blog).
- Transport seam / Protocol / factory: **HIGH** — read directly from current source; CLAUDE.md's `godoo/rpc/` path is stale (actual: `godoo/client/rpc/`).
- Pyodide CPython version (3.13) & 3.14-from-Emscripten: **HIGH** — official changelog + PEP references.
- ACA CORS / multi-container / self-destruct Bicep: **HIGH** for CORS shape; **MEDIUM** for exact Logic App ARM-action wiring (verified pattern, exact JSON left to plan).
- Postgres-ephemerality reconciliation of D-02: **HIGH** that it's a real constraint; **MEDIUM** that `minReplicas:1` is the chosen fix (needs Marc).
- ADR convention: **MEDIUM** — recommendation, not an existing fact (A1).

**Research date:** 2026-06-02
**Valid until:** ~2026-07-02 for Pyodide/pyodide-httpx specifics (Pyodide moves fast; re-check version + pyodide-httpx maintenance before executing). ACA/Bicep + codebase seams stable ~90 days.
