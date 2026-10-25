// main.bicep — ACA environment + multi-container Odoo/Postgres + HTTPS ingress + CORS
//
// Purpose: Provision the throwaway Azure Container Apps endpoint the Pyodide browser
//          spike calls cross-origin over HTTPS (D-02/D-03).  This is NON-SHIPPING
//          committed evidence (D-09) — it lives under spikes/ and never enters any
//          published godoo package.
//
// Deploy via: see deploy.md (plan 08-03, NOT autonomous)
// Resource group: rg-godoo-pyodide-spike (dedicated; torn down by selfdestruct.bicep)
//
// minReplicas RATIONALE: D-02 originally stated minReplicas:0 (≈zero idle cost).
// Research (Pitfall 1) established that Postgres-in-pod is ephemeral — scale-to-zero
// silently destroys the freshly-seeded DB, causing intermittent auth failures between
// deploy and test-run.  The reconciliation: run minReplicas:1 for the active spike
// window and rely on the Logic App self-destruct (selfdestruct.bicep) for cost control
// rather than scale-to-zero.  The TTL is short (≈1 h); cost is trivial.

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------

@description('Azure region for all resources in this resource group.')
param location string = resourceGroup().location

@description('Name of the Container Apps managed environment.')
param envName string = 'cae-godoo-pyodide-spike'

@description('Name of the Container App.')
param appName string = 'ca-godoo-pyodide-spike'

@description('Exact scheme+host+port of the spike page origin, e.g. "https://<user>.github.io" or "http://localhost:8000". NEVER pass "*" — CORS is origin-scoped per D-04/T-08-05.')
param spikePageOrigin string

@description('Odoo database name to create on first boot.')
param odooDatabase string = 'spike'

@description('Odoo admin master password.  Passed at deploy time, never committed.  (T-08-04)')
@secure()
param odooAdminPassword string

@description('Postgres superuser password.  Passed at deploy time, never committed.  (T-08-07)')
@secure()
param postgresPassword string

@description('Postgres username Odoo connects as.')
param postgresUser string = 'odoo'

// ---------------------------------------------------------------------------
// Container Apps managed environment
// ---------------------------------------------------------------------------

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  properties: {
    zoneRedundant: false
  }
}

// ---------------------------------------------------------------------------
// Container App — multi-container pod (Odoo + Postgres share localhost)
//
// ACA multi-container pod topology (D-02):
//   Both containers run in the SAME replica and share the pod network, so they
//   reach each other on 127.0.0.1 (localhost).  Only the Odoo port (8069) is
//   exposed externally via ingress.
//
// Secret lifecycle:
//   ACA secrets are declared in configuration.secrets[] and referenced by
//   secretRef in container env vars.  The @secure() parameter values are passed
//   at deploy time and never appear in the committed Bicep (T-08-04, T-08-07).
// ---------------------------------------------------------------------------

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      // Secrets are declared here; referenced by name in env secretRef below.
      // Values come from @secure() deploy-time parameters — never hardcoded.
      secrets: [
        {
          name: 'odoo-admin-password'
          value: odooAdminPassword
        }
        {
          name: 'postgres-password'
          value: postgresPassword
        }
      ]
      ingress: {
        // external: true — ACA terminates TLS with the managed *.azurecontainerapps.io
        // cert (D-03).  The FQDN is browser-trusted and non-localhost — satisfies SC-1.
        external: true
        targetPort: 8069
        transport: 'http'
        corsPolicy: {
          // allowedOrigins scoped to the EXACT page origin supplied as a parameter —
          // NEVER '*'.  (D-04, T-08-05)
          allowedOrigins: [spikePageOrigin]
          // POST carries the JSON-RPC body; OPTIONS is the CORS preflight that ACA
          // answers automatically at the ingress (reverse-proxy style — no Odoo
          // controller required, satisfying D-04).
          allowedMethods: ['POST', 'OPTIONS']
          // content-type is the only header godoo's /jsonrpc POST sets.
          allowedHeaders: ['content-type']
          // godoo authenticates in the JSON-RPC body, not via cookies — false is
          // correct and avoids the browser's "credentials+wildcard" rejection.
          allowCredentials: false
          maxAge: 3600
        }
      }
    }
    template: {
      containers: [
        // ----------------------------------------------------------------
        // Container 1 — Odoo
        // Official odoo:17 image; HTTP on port 8069.
        // DB init: --init base only (sufficient for res.users auth + reads).
        // Connects to Postgres on localhost (shared pod network, port 5432).
        // ----------------------------------------------------------------
        {
          name: 'odoo'
          image: 'odoo:17'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            // Postgres host — localhost because both containers share the pod.
            {
              name: 'HOST'
              value: '127.0.0.1'
            }
            {
              name: 'PORT'
              value: '5432'
            }
            {
              name: 'USER'
              value: postgresUser
            }
            {
              name: 'PASSWORD'
              secretRef: 'postgres-password'
            }
            {
              name: 'DB_NAME'
              value: odooDatabase
            }
            // Odoo master (admin) password for the DB-create gate.
            {
              name: 'ADMIN_PASSWD'
              secretRef: 'odoo-admin-password'
            }
          ]
          // Initialize only the base module — res.users is sufficient for the spike's
          // common.authenticate + object.execute_kw(res.users, read) round-trip.
          // --database must be explicit: the official odoo:17 entrypoint does NOT read
          // DB_NAME for --init; omitting it leaves --init with no target and the DB
          // empty (root-cause fix).
          // --without-demo=all keeps the DB lean and the boot fast.
          args: [
            '--db_host=127.0.0.1'
            '--db_port=5432'
            '--database=spike'
            '--init=base'
            '--without-demo=all'
          ]
        }
        // ----------------------------------------------------------------
        // Container 2 — Postgres
        // MS-published dev Postgres image (mcr.microsoft.com/k8se/services/postgres:14).
        // No external port exposed — Odoo reaches it on localhost:5432 in-pod.
        // WARNING: storage is ephemeral — data is lost on scale-to-zero (Pitfall 1).
        // minReplicas:1 below prevents this for the spike window.
        // ----------------------------------------------------------------
        {
          name: 'postgres'
          image: 'mcr.microsoft.com/k8se/services/postgres:14'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'POSTGRES_USER'
              value: postgresUser
            }
            {
              name: 'POSTGRES_PASSWORD'
              secretRef: 'postgres-password'
            }
            {
              name: 'POSTGRES_DB'
              value: odooDatabase
            }
          ]
        }
      ]
      scale: {
        // minReplicas:1 — DO NOT change to 0.
        // Rationale: scale-to-zero would destroy the in-pod Postgres container's
        // ephemeral data, breaking the spike between deploy and test-run (Pitfall 1
        // reconciliation of D-02's ≈zero-idle-cost intent).  Cost is bounded by the
        // Logic App self-destruct TTL in selfdestruct.bicep, not by scale-to-zero.
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('Fully-qualified domain name of the Container App HTTPS endpoint (*.azurecontainerapps.io).')
output fqdn string = containerApp.properties.configuration.ingress.fqdn

@description('Full HTTPS base URL — append /jsonrpc for the JSON-RPC endpoint.')
output jsonrpcUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}/jsonrpc'
