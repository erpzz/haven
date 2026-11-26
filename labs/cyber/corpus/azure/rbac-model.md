---
id: azure.rbac.model
title: Azure RBAC: role definitions, scope, inheritance and effective access
domain: azure
topic: rbac
source_url: https://learn.microsoft.com/azure/role-based-access-control/overview
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Azure Resource Manager Microsoft.Authorization 2022-04-01
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [azure, arm]
prerequisites: []
see_also: [https://learn.microsoft.com/azure/role-based-access-control/role-definitions, https://learn.microsoft.com/azure/role-based-access-control/deny-assignments]
---

# Azure RBAC

## Role definitions

A role definition has `Actions`, `NotActions`, `DataActions`, `NotDataActions` and `AssignableScopes`.

- `Actions` are control-plane (management) operations, e.g. `Microsoft.Storage/storageAccounts/read`.
- `DataActions` are data-plane operations, e.g. `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read`.
- `NotActions` / `NotDataActions` **subtract** from the same role's grants. They are **not deny rules**: if another role assignment grants the subtracted operation, the principal has it.
- Effective permissions are the **union** of all role assignments that apply to the principal (directly, via groups) at the scope and its parents.
- Only **deny assignments** block an operation regardless of role assignments. They are created by Azure (managed applications, deployment stacks deny settings), not by ordinary users.

## Built-in roles that matter

- **Owner**: `*` actions, including role assignment.
- **Contributor**: `*` actions except `Microsoft.Authorization/*/Delete`, `Microsoft.Authorization/*/Write`, `Microsoft.Authorization/elevateAccess/Action` and a few blueprint/gallery operations. Cannot assign roles, but can do almost everything else, including `listKeys` on storage accounts (which yields data access) and editing Key Vault access policies in the access-policy model.
- **User Access Administrator** and **Role Based Access Control Administrator**: can create role assignments. Either is a path to Owner-equivalent access unless constrained with conditions.
- **Reader**: read control-plane only; cannot read blob data or secrets.
- Data roles such as **Storage Blob Data Reader** and **Key Vault Secrets User** grant data-plane access without control-plane rights.

## Scope and inheritance

Management group → subscription → resource group → resource. An assignment at a scope is inherited by everything below it. An Owner at a management group is Owner of every subscription under it. The tenant root group sits above all management groups. A Global Administrator can elevate to User Access Administrator at root (`/`) with `elevateAccess`, which is logged in the directory audit and activity log.

## Assessment procedure

1. Collect role assignments with `scope`, `principalId`, `principalType` and role definition (Resource Graph `authorizationresources`).
2. Expand to effective access per principal: union across all scopes at or above the resource.
3. Flag Owner / User Access Administrator / RBAC Administrator at management-group or subscription scope, guests or service principals with those roles, and custom roles with `*` or `Microsoft.Authorization/*` actions.
4. Remember that `NotActions` never protect against another assignment.

## Common false positives

- "Principal X can delete resource Y" when X's only role lists the delete operation in `NotActions` **and** no other assignment grants it: X cannot.
- Reader on a subscription does not expose blob contents (unless the storage account allows anonymous access).
