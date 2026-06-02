# Phase 8: Pyodide Spike - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce an empirically-grounded **written verdict** on whether `godoo` can run in a
Pyodide/browser environment: which transport strategy works, what Python floor is
required, and an explicit **go/no-go** decision for a future browser build.

This is a **spike** — it produces a decision and evidence, **not a shipping feature**.
No `godoo[browser]` package ships this phase regardless of verdict. Scope is fixed by
ROADMAP.md SC-1..SC-4 and requirements BROWSER-02 / BROWSER-03; this discussion
clarifies only HOW to run the spike.

</domain>

<decisions>
## Implementation Decisions

### Spike Execution Environment
- **D-01:** Run the in-browser test in a **raw Pyodide HTML page** (hand-loaded
  `pyodide.js` + `micropip`). Chosen for the cleanest error surface and full control
  over what's installed; raw tracebacks visible in the console. The result transfers to
  Marimo/JupyterLite because they share the same Pyodide runtime. Re-running in a
  notebook host is explicitly deferred (see Deferred Ideas).

### Test Endpoint & CORS (SC-1 compliance)
- **D-02:** Provision a **throwaway Odoo + Postgres on Azure Container Apps (ACA)**.
  Postgres runs as a **container in the ACA environment — NOT Azure DB for PostgreSQL**
  (which bills continuously and cannot scale to zero).
  - **D-02 (amended 2026-06-02):** Run Postgres at **`minReplicas: 1`** for the spike
    window — NOT `0`. Research established that `minReplicas: 0` with ephemeral container
    storage silently destroys the freshly-seeded test DB on scale-to-zero, breaking the
    spike between deploy and test-run. Cost is controlled by the **Logic App TTL
    self-destruct (D-05)** rather than scale-to-zero. This supersedes the original
    `minReplicas: 0` choice.
- **D-03:** **TLS via the managed cert on the default `*.azurecontainerapps.io` FQDN** —
  browser-trusted, non-localhost. This was chosen specifically to satisfy SC-1's
  explicit bar (a plain-HTTP or localhost call does NOT satisfy the criterion) while
  avoiding self-signed / mkcert browser-trust pain.
- **D-04:** **CORS configured on the ACA ingress**, scoped to the spike page's origin,
  with the OPTIONS preflight handled (reverse-proxy-style; not an Odoo controller).
- **D-05:** **Teardown** — a **dedicated resource group** (e.g.
  `rg-godoo-pyodide-spike`) holding everything, plus a **self-contained Bicep
  self-destruct**: a Consumption **Logic App** (preferred — image-less) *or* an **ACA
  scheduled Job** that runs `az group delete` after a TTL. The user-assigned managed
  identity **and** its RG-scoped Contributor role assignment are declared in the **same
  Bicep template**. RG-scoped Contributor is sufficient for the trigger to delete its
  own RG; the ARM delete continues async after the trigger container/workflow exits. A
  GitHub Actions backstop was explicitly rejected (recent reliability problems).

### Transport Strategy Coverage
- **D-06:** Test **all three strategies regardless of early success** —
  (1) stock httpx via Pyodide's bundled Fetch adapter, (2) `pyodide-httpx` 0.2.0
  (spike-only; **never** added to any `pyproject.toml`), (3) a custom `pyfetch`-backed
  `AsyncTransport` implementing the `Transport` Protocol via the `transport_factory`
  seam. SC-2 requires per-strategy worked/failed evidence with error output for
  failures.
- **D-07:** **Python-floor handling** — test the JSON-RPC transport **in isolation**
  (the call path / a minimal `AsyncTransport` against `/jsonrpc`), **NOT** a full
  `import godoo`. The full package is `>=3.14`-gated and will not load under Pyodide's
  CPython 3.13.2. The Python floor stays an **output recommendation**, not something the
  spike fights to bypass.

### Verdict & Decision Artifacts
- **D-08:** Evidence (per-strategy worked/failed + error output) and the Python-floor
  recommendation → **`08-SPIKE.md` in the phase dir**. The durable **go/no-go decision →
  a standalone ADR** (location/numbering convention TBD — see Canonical References) that
  v2.0 planning reads directly. Separates "evidence" from "the decision the fleet
  depends on".
- **D-09:** **Keep all spike code as non-shipping committed evidence** — the raw Pyodide
  HTML page, the Bicep, and **especially the custom `pyfetch` `AsyncTransport`
  prototype** — under the phase artifacts / `spikes/` dir. Nothing enters a published
  package (honors "no `godoo[browser]` ships this phase"). The custom transport
  prototype seeds BROWSER-F1 if the verdict is "go".
- **D-10:** **Go bar** — "go" requires at least one strategy that **both** makes the
  successful cross-origin HTTPS call **and** is maintainable/sustainable to ship (e.g.
  stock httpx Fetch adapter, or the custom Transport via the existing seam). A success
  that only works via a brittle/unmaintainable workaround is recorded as
  **conditional / no-go**.

### Claude's Discretion
- Logic App vs ACA Job for the self-destruct (D-05): researcher recommends, leaning
  **Logic App** (image-less, native ARM "delete resource group" action).
- Exact CORS allowed-origin value, the minimal Odoo modules the test DB needs, and the
  ACA scaling/SKU parameters — left to research/planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & decision
- `.planning/ROADMAP.md` — Phase 8 entry: goal, SC-1..SC-4, BROWSER-02/03 mapping, and
  **OD-3** (httpx vs POSIX socket in Pyodide — resolved empirically this phase).
- `.planning/REQUIREMENTS.md` — **BROWSER-02** (actual in-browser HTTPS call + written
  verdict), **BROWSER-03** (Python-floor recommendation + go/no-go decision).
- `.planning/seeds/SEED-001-browser-pyodide-compatibility.md` — origin motivation
  (browser-native Python: Marimo, JupyterLite, stlite, PyScript).

### Transport seam (already shipped — Phase 6)
- `.planning/phases/06-introspection-transport-seam/06-CONTEXT.md` (or the Phase 6
  CONTEXT under `.planning/phases/06-*/`) — **D-06** (Transport Protocol surface:
  `authenticate` / `call` / `aclose` / `logout` / `session`) and **D-07**
  (`transport_factory` signature). Confirm the exact dir name during scout.
- `packages/godoo-client/src/godoo/rpc/protocol.py` — the `Transport` Protocol the
  custom `pyfetch` transport must satisfy structurally. **Confirm the exact module path
  during codebase scout** (CLAUDE.md documents `…/godoo/rpc/`; verify before relying on
  it).
- `packages/godoo-client/src/godoo/rpc/transport.py` — `JsonRpcTransport`
  (`httpx.AsyncClient` + `await self._client.post(...)`) — the call path under test.

### To verify (not yet a path)
- **ADR location/numbering convention for godoo-py** — researcher/planner determines
  where the go/no-go ADR lives (check for `docs/adr/`, `.planning/adrs/`, or existing
  ADR precedent in the repo).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OdooClientConfig.transport_factory` seam — injection point for the custom `pyfetch`
  transport; no core client changes needed to swap in a browser transport.
- `Transport` Protocol (5 methods) — the custom `AsyncTransport` implements it
  structurally.

### Established Patterns
- All service functions are `async` — compatible with the browser async model.
- The **client package has no `asyncio.to_thread` / threading / file-I/O** (those live
  only in `godoo-testcontainers`, which is out of scope). So the only browser-compat
  question is whether `httpx.AsyncClient` works under Emscripten — exactly the OD-3
  question.

### Integration Points
- A `pyfetch`-backed `AsyncTransport` plugs in via `transport_factory` and is tested in
  isolation against `/jsonrpc` (per D-07), without importing the 3.14-gated package.

</code_context>

<specifics>
## Specific Ideas

- **SC-1 explicitly excludes localhost and plain-HTTP:** "a plain-HTTP or localhost call
  does NOT satisfy this criterion." The ACA managed-cert FQDN approach (D-02/D-03) was
  chosen precisely to honor this without self-signed cert pain.
- **OD-3 is a genuine researcher conflict** (httpx reportedly bundled + pre-patched in
  Pyodide 0.29.x via a Fetch adapter, vs. only `urllib3 ≥2.2.0` having official native
  Emscripten support and POSIX socket calls raising `NotImplementedError`). It is
  resolved **only** by the actual in-browser call test — hence "test all three" (D-06).

</specifics>

<deferred>
## Deferred Ideas

- **Building a reusable TLS / reverse-proxy / CORS layer into `godoo-testcontainers`** —
  considered (the user raised it), deferred. A spike is throwaway evidence; productize a
  browser-test harness only if the verdict is "go" (future phase).
- **BROWSER-F1** (`godoo[browser]` extra) and **BROWSER-F2** (relax the Python floor for
  Pyodide) — gated on a "go" verdict; out of scope this phase.
- **Re-running the winning strategy in JupyterLite / Marimo** to confirm the verdict in a
  real notebook host — considered (host-env option), deferred; the raw-page result is
  sufficient for the verdict since the runtime is shared.

</deferred>

---

*Phase: 8-Pyodide Spike*
*Context gathered: 2026-06-02*
