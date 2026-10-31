---
id: azure.storage.access
title: Azure Storage: public access, shared keys, SAS and network rules
domain: azure
topic: storage
source_url: https://learn.microsoft.com/azure/storage/blobs/anonymous-read-access-prevent
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Azure Resource Manager Microsoft.Storage 2023-05-01
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [azure, storage]
prerequisites: []
see_also: [https://learn.microsoft.com/azure/storage/common/shared-key-authorization-prevent, https://learn.microsoft.com/azure/storage/common/storage-network-security]
---

# Azure Storage access

## Anonymous access has two switches

- Account level: `properties.allowBlobPublicAccess`. When `false`, no container can be anonymous, whatever the container setting says.
- Container level: `publicAccess` = `None`, `Blob` (anonymous read of blobs if the name is known) or `Container` (anonymous list and read).
- A container is anonymously readable only if **both** allow it. A scanner that reports a container with `publicAccess: Container` on an account with `allowBlobPublicAccess: false` is reporting a false positive.

## Shared Key and SAS

- `allowSharedKeyAccess: false` disables account-key authorization (and account/service SAS signed with keys); access then requires Entra ID (user delegation SAS still works).
- Anyone with `Microsoft.Storage/storageAccounts/listkeys/action` (Owner, Contributor, Storage Account Contributor) can read the keys and therefore all data.

## Network

`networkAcls.defaultAction: Deny` with explicit virtual network rules, IP rules or private endpoints limits where requests can come from; `Allow` means any network (authentication still applies). `publicNetworkAccess: Disabled` forces private endpoints.

## Other settings

`minimumTlsVersion` (TLS1_2 recommended), `supportsHttpsTrafficOnly: true`, soft delete for blobs and containers, immutability for backups.

## Assessment procedure

For each account: record `allowBlobPublicAccess`, `allowSharedKeyAccess`, `networkAcls.defaultAction`, `publicNetworkAccess`, `minimumTlsVersion`; for each container its `publicAccess`. Compute real anonymous exposure as account flag AND container setting.
