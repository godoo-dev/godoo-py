# Deploy & Teardown — Pyodide Spike Azure Endpoint

This document is the operating guide for plan 08-03 (the live deployment step — NOT
autonomous).  It covers the end-to-end sequence from `az login` to reading the FQDN and
wiring it into the spike page, plus the manual teardown backstop.

> **IMPORTANT — No live deployment happens here.**  The Bicep files in this directory are
> authored as plan 08-02 evidence (D-09).  Plan 08-03 is where they are actually deployed.
> This document is the step-by-step guide for that plan.

---

## Prerequisites (Wave-0 gate — verify before running any `az` command)

1. **Azure CLI installed and authenticated:**
   ```bash
   az login
   az account show   # confirm the correct subscription is active
   ```
   If the subscription is wrong, switch it:
   ```bash
   az account set --subscription "<subscription-id-or-name>"
   ```
   SC-1 ("real TLS-terminated Odoo endpoint") cannot be satisfied locally — Azure access
   is a hard requirement, not a nice-to-have.

2. **Bicep CLI available** (bundled with az CLI ≥ 2.20 or install explicitly):
   ```bash
   az bicep version       # should print the bicep version
   az bicep install       # if not already installed
   ```

3. **Spike page origin decided** — you need to know the exact `scheme://host:port` the
   spike HTML page will be served from before deploying, because `spikePageOrigin` is
   baked into the CORS `allowedOrigins` on the ingress.  See the CORS note below.

---

## CORS origin — choose before deploying

The `main.bicep` `spikePageOrigin` parameter must be the **exact origin** the spike page
is served from.  Examples:

| How you serve the page | Origin value to pass |
|------------------------|----------------------|
| GitHub Pages | `https://<your-github-username>.github.io` |
| Local static server (`python -m http.server 8000`) | `http://localhost:8000` |
| Vite / other local dev server (port 5173) | `http://localhost:5173` |

If the page is opened as a `file://` URL, the Origin is `null` and the browser WILL
reject the CORS preflight — serve it from a real HTTP(S) origin.

---

## Step 1 — Create the dedicated resource group

```bash
az group create \
  --name rg-godoo-pyodide-spike \
  --location westeurope
```

> All spike resources live in this single group.  The self-destruct deletes the whole
> group when the TTL fires.  Using a dedicated group means no other resources are at risk.

---

## Step 2 — Deploy `main.bicep` (ACA environment + Odoo + Postgres)

Pass credentials at deploy time — never commit them.  The `@secure()` parameters are
consumed by the Bicep engine and stored as ACA secrets; they never appear in the
deployment outputs.

```bash
az deployment group create \
  --resource-group rg-godoo-pyodide-spike \
  --template-file spikes/08-pyodide/infra/main.bicep \
  --parameters \
    spikePageOrigin='https://<your-page-origin>' \
    odooAdminPassword='<strong-throwaway-password>' \
    postgresPassword='<strong-throwaway-password>' \
    odooDatabase='spike'
```

**Password guidance:** use a strong, randomly-generated password (e.g. `openssl rand -base64
24`).  This is a throwaway DB — the password is never reused; the self-destruct deletes
the whole RG including the DB within the TTL window.

Wait for the deployment to complete (usually 3–5 minutes for ACA provisioning).

---

## Step 3 — Read the FQDN and wire it into the spike page

The deployment outputs the Container App FQDN.  Extract it:

```bash
az deployment group show \
  --resource-group rg-godoo-pyodide-spike \
  --name main \
  --query 'properties.outputs.fqdn.value' \
  --output tsv
```

This prints something like:
```
ca-godoo-pyodide-spike.happyrock-abc12345.westeurope.azurecontainerapps.io
```

The `/jsonrpc` endpoint is then:
```
https://ca-godoo-pyodide-spike.happyrock-abc12345.westeurope.azurecontainerapps.io/jsonrpc
```

**Wire it into the spike HTML page:**  open `spikes/08-pyodide/index.html` and replace the
`ODOO_BASE_URL` placeholder with this HTTPS base URL.  Then serve the page from your
chosen origin (the same one you passed as `spikePageOrigin`).

---

## Step 4 — Wait for Odoo to boot

Odoo initialises the `base` module and creates the `spike` DB on first boot — this takes
roughly 2–3 minutes on a cold start.  Poll readiness:

```bash
# Replace with your actual FQDN
curl -s -o /dev/null -w "%{http_code}" \
  https://ca-godoo-pyodide-spike.<env>.azurecontainerapps.io/web/health
```

A `200` response means Odoo is up.  Alternatively watch the container logs:

```bash
az containerapp logs show \
  --name ca-godoo-pyodide-spike \
  --resource-group rg-godoo-pyodide-spike \
  --tail 50 \
  --follow
```

---

## Step 5 — Deploy `selfdestruct.bicep` (UAMI + RG Contributor + Logic App)

Deploy the self-destruct template **after** the ACA app is running.  The Logic App is
started with a POST to its trigger URL to begin the TTL countdown.

```bash
az deployment group create \
  --resource-group rg-godoo-pyodide-spike \
  --template-file spikes/08-pyodide/infra/selfdestruct.bicep \
  --parameters ttlMinutes=60
```

Retrieve the Logic App trigger URL from the deployment output:

```bash
TRIGGER_URL=$(az deployment group show \
  --resource-group rg-godoo-pyodide-spike \
  --name selfdestruct \
  --query 'properties.outputs.triggerUrl.value' \
  --output tsv)
```

**Start the TTL countdown** — POST to the trigger URL once:

```bash
curl -X POST "$TRIGGER_URL"
```

From this point the Logic App waits `ttlMinutes` (default: 60) then issues an ARM REST
DELETE on `rg-godoo-pyodide-spike`.  The delete is asynchronous and continues server-side
even after the Logic App itself is torn down.

---

## Step 6 — Run the spike (plan 08-03 proper)

Now open the spike page in a browser, open DevTools → Network, and run the three
transport strategies.  Capture:
- Strategy 1 (stock httpx): the full traceback
- Strategy 2 (pyodide-httpx 0.2.0): the call result or failure
- Strategy 3 (custom PyfetchTransport): the successful `res.users` read result

Record findings in `.planning/phases/08-pyodide-spike/08-SPIKE.md`.

---

## Manual teardown backstop

If the Logic App self-destruct **fails** (network blip, Logic App bug, role-assignment
replication delay, etc.), the endpoint and credentials will linger.  The manual backstop
is:

```bash
az group delete \
  --name rg-godoo-pyodide-spike \
  --yes \
  --no-wait
```

> **NOT a GitHub Actions backstop** — D-05 explicitly rejected that approach due to
> recent reliability problems.  The manual `az group delete` is the authoritative
> cleanup path.

Run this command as soon as you notice the self-destruct did not fire, or any time you
want to tear down early.

---

## Verify teardown

After either the Logic App fires or you run the manual backstop, verify the group is gone:

```bash
az group show --name rg-godoo-pyodide-spike 2>&1 | grep -i "could not be found"
# Expected: "...could not be found..." (ResourceGroupNotFound)
```

---

## Cost notes

- ACA Consumption tier: billed per request + CPU/memory while active.  With minReplicas:1
  and a 1-hour TTL the cost is typically < $0.10 USD.
- The Logic App (Consumption): billed per action execution — effectively $0.00 for a
  single-run workflow.
- There is no ongoing cost after the self-destruct fires and the RG is deleted.
