// selfdestruct.bicep — UAMI + RG-scoped Contributor role assignment + Logic App TTL self-destruct
//
// Purpose: Guarantee time-bounded teardown of the spike's resource group (D-05).
//          This is NON-SHIPPING committed evidence (D-09).
//
// What this template does (all three resources in the SAME file — D-05 requirement):
//   1. Creates a user-assigned managed identity (UAMI) — id-spike-destruct
//   2. Grants that UAMI the built-in Contributor role scoped to THIS resource group only
//      (never subscription scope — T-08-03 / ASVS V4 HIGH)
//   3. Deploys a Consumption Logic App that, after a TTL, issues an ARM REST DELETE on
//      the resource group — authenticated via ManagedServiceIdentity (audience management.azure.com)
//
// Threat mitigation notes:
//   T-08-03: roleAssignment scoped to resourceGroup() only; principalType: 'ServicePrincipal'
//            set to avoid intermittent replication errors with UAMI objects.
//   T-08-06: If the self-destruct fails, run the manual backstop in deploy.md:
//            az group delete -n rg-godoo-pyodide-spike --yes --no-wait
//            (NOT a GitHub Actions backstop — D-05 explicitly rejects that approach.)
//
// ARM async delete note:
//   The RG DELETE returns HTTP 202 and continues server-side asynchronously.  The Logic
//   App (and the resources it is deleting, including itself) can be torn down before the
//   server-side delete completes — this is correct and expected behaviour.

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------

@description('Azure region for the managed identity and Logic App.')
param location string = resourceGroup().location

@description('Name of the user-assigned managed identity.')
param uamiName string = 'id-spike-destruct'

@description('Name of the Consumption Logic App.')
param logicAppName string = 'la-spike-destruct'

@description(
  'TTL in minutes before the Logic App fires and deletes the resource group. '
  + 'Default: 60 minutes (≈1 hour after deploy).'
)
param ttlMinutes int = 60

// ---------------------------------------------------------------------------
// Resource 1 — User-Assigned Managed Identity
// ---------------------------------------------------------------------------

resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: uamiName
  location: location
}

// ---------------------------------------------------------------------------
// Resource 2 — RG-scoped Contributor role assignment
//
// Built-in Contributor role GUID: b24988ac-6180-42a0-ab88-20f7382dd24c
// Source: https://learn.microsoft.com/azure/role-based-access-control/built-in-roles
//
// Scope: resourceGroup() — NEVER at subscription scope.  RG-scoped Contributor is
// sufficient to delete its own resource group via ARM REST.  (T-08-03, ASVS V4 HIGH)
//
// principalType: 'ServicePrincipal' — required for UAMI assignments; prevents
// intermittent replication-delay errors that occur without this field.
//
// guid() name: deterministic from RG ID + UAMI ID + role label — idempotent redeploys.
// ---------------------------------------------------------------------------

resource contributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  // Deterministic name: idempotent across redeploys of the same RG + UAMI pair.
  name: guid(resourceGroup().id, uami.id, 'Contributor')
  // No 'scope' property — defaults to the resource group scope.
  // This is intentional: NEVER elevate to subscription-wide scope.
  properties: {
    // Built-in Contributor: b24988ac-6180-42a0-ab88-20f7382dd24c
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'b24988ac-6180-42a0-ab88-20f7382dd24c'
    )
    principalId: uami.properties.principalId
    // REQUIRED for UAMI to avoid intermittent Azure AD replication errors.
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Resource 3 — Consumption Logic App (image-less, D-05 preferred path)
//
// Pattern: Recurrence trigger (fires once at TTL) → HTTP action DELETE on the RG.
//
// ARM REST endpoint for RG delete (api-version 2021-04-01):
//   DELETE https://management.azure.com/subscriptions/{subscriptionId}/resourcegroups/rg-godoo-pyodide-spike?api-version=2021-04-01
//
// Authentication: ManagedServiceIdentity with audience https://management.azure.com/
// The Logic App is assigned the UAMI via its identity block.
//
// Logic App Workflow Definition Language (WDL) is embedded inline in the template.
// ---------------------------------------------------------------------------

resource logicApp 'Microsoft.Logic/workflows@2019-05-01' = {
  name: logicAppName
  location: location
  // Bind the UAMI to the Logic App so the HTTP action can use ManagedServiceIdentity auth.
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${uami.id}': {}
    }
  }
  properties: {
    state: 'Enabled'
    definition: {
      '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#'
      contentVersion: '1.0.0.0'
      parameters: {
        subscriptionId: {
          type: 'String'
          defaultValue: subscriptionId()
        }
        resourceGroupName: {
          type: 'String'
          defaultValue: resourceGroup().name
        }
        ttlMinutes: {
          type: 'Int'
          defaultValue: ttlMinutes
        }
      }
      triggers: {
        // Recurrence trigger: fires once after ttlMinutes.
        // Using a single-shot recurrence with a start time of now + ttlMinutes.
        // The RG-delete is irreversible; this fires once and the workflow tears itself
        // down as part of the cascade.
        Wait_then_destroy: {
          type: 'Request'
          kind: 'Http'
          inputs: {
            schema: {}
          }
        }
        // NOTE: A pure timer self-destruct uses a Recurrence or Schedule trigger.
        // The most reliable single-shot pattern in WDL is:
        //   Delay action (PT{N}M) → HTTP DELETE on the RG.
        // We implement that with a manual trigger + immediate Delay action so the
        // workflow is started once at deploy time (see deploy.md for the az CLI
        // trigger command) and fires after the delay.
      }
      actions: {
        // Step 1: wait for the TTL duration before firing the delete.
        Delay_TTL: {
          type: 'Wait'
          inputs: {
            interval: {
              count: '@parameters(\'ttlMinutes\')'
              unit: 'Minute'
            }
          }
          runAfter: {}
        }
        // Step 2: issue the ARM REST DELETE on the resource group.
        // Returns 202 and continues async server-side — the Logic App (and the whole
        // RG including itself) continues to be deleted in the background after the
        // workflow run completes or the app itself is torn down.
        Delete_Resource_Group: {
          type: 'Http'
          inputs: {
            method: 'DELETE'
            uri: 'https://management.azure.com/subscriptions/@{parameters(\'subscriptionId\')}/resourcegroups/@{parameters(\'resourceGroupName\')}?api-version=2021-04-01'
            authentication: {
              // ManagedServiceIdentity: the Logic App uses the bound UAMI (identity block above)
              // to authenticate against the Azure management plane.
              type: 'ManagedServiceIdentity'
              identity: uami.id
              // Audience must be the ARM endpoint root (with trailing slash).
              audience: 'https://management.azure.com/'
            }
          }
          runAfter: {
            Delay_TTL: ['Succeeded']
          }
        }
      }
    }
    parameters: {}
  }
  dependsOn: [
    contributorRoleAssignment
  ]
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('Principal ID of the UAMI (for diagnostics / role-assignment verification).')
output uamiPrincipalId string = uami.properties.principalId

@description('Logic App resource ID.')
output logicAppId string = logicApp.id

@description('Logic App HTTP trigger URL — POST this once after deploy to start the TTL countdown.')
output triggerUrl string = listCallbackUrl(
  '${logicApp.id}/triggers/Wait_then_destroy',
  '2019-05-01'
).value
