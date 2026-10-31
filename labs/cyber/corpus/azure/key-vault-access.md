---
id: azure.keyvault.access
title: Key Vault: access policy model versus Azure RBAC, network and deletion protection
domain: azure
topic: key-vault
source_url: https://learn.microsoft.com/azure/key-vault/general/rbac-access-policy
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Azure Resource Manager Microsoft.KeyVault 2023-07-01
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [azure, key-vault]
prerequisites: []
see_also: [https://learn.microsoft.com/azure/key-vault/general/security-features, https://learn.microsoft.com/azure/key-vault/general/soft-delete-overview]
---

# Key Vault access

## Two authorization models

- `properties.enableRbacAuthorization: true`: data-plane access (secrets, keys, certificates) is controlled by Azure RBAC data roles: Key Vault Administrator, Key Vault Secrets Officer, Key Vault Secrets User, Key Vault Crypto User, Key Vault Reader (metadata only, no secret values).
- `false` (legacy **access policy** model): `properties.accessPolicies[]` lists object ids with permissions such as `secrets: [get, list]`. Any principal with `Microsoft.KeyVault/vaults/write` on the vault (Contributor, Key Vault Contributor) can add an access policy for itself, so in this model **Contributor effectively means data access**. Microsoft recommends the RBAC model.

## Other controls

- Soft delete is always on for new vaults (7–90 day retention). `enablePurgeProtection: true` prevents permanent deletion during retention, protecting against ransomware-style destruction; it cannot be turned off once enabled.
- Network: `networkAcls.defaultAction: Deny` plus private endpoints or selected networks; `publicNetworkAccess`.
- Logging: diagnostic settings sending `AuditEvent` to Log Analytics record every secret read.

## Assessment procedure

1. Record the authorization model.
2. RBAC model: list data-role assignments at vault, resource group, subscription and management-group scope (inherited).
3. Access-policy model: list access policies **and** every principal with vault write permission (they can grant themselves).
4. Check purge protection, network default action and diagnostic logging.

## Common false positives

- Key Vault Reader or the subscription Reader role does not reveal secret values.
- In the RBAC model, entries left in `accessPolicies` are ignored.
