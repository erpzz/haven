---
id: windows-ad.hybrid-sync
title: Hybrid identity: Entra Connect, password hash sync and the on-premises boundary
domain: windows-ad
topic: hybrid
source_url: https://learn.microsoft.com/entra/identity/hybrid/connect/whatis-azure-ad-connect
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Entra Connect Sync 2.x / Cloud Sync
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [active-directory, entra-id, entra-connect]
prerequisites: []
see_also: [https://learn.microsoft.com/entra/identity/hybrid/connect/how-to-connect-password-hash-synchronization, https://learn.microsoft.com/entra/identity/role-based-access-control/best-practices]
---

# Hybrid identity: Entra Connect and the on-premises boundary

## Sign-in models

- **Password hash sync (PHS)**: a hash of the AD password hash is synchronised; Entra ID authenticates in the cloud. This is Microsoft's recommended default, and it enables leaked-credential detection.
- **Pass-through authentication (PTA)**: agents on premises validate passwords. Those agent servers are tier 0.
- **Federation (AD FS)**: on-premises AD FS issues tokens. Compromise of the token-signing certificate allows forged tokens for any federated user (ATT&CK T1606.002 / T1484.002).

## The sync server is tier 0

The Entra Connect server holds credentials that can read (with PHS: replicate password data from) the whole domain and write to Entra ID. Protect it like a domain controller:
- tier 0 admins only;
- no internet browsing;
- patched;
- monitored.

The on-premises connector account gets DS-Replication rights for PHS. That is expected, and is why DCSync detections must allow-list it.

## Keep cloud admins cloud-only

Privileged Entra roles should be held by cloud-only accounts, not synchronised ones. Otherwise an on-premises compromise (password reset, attribute changes) extends straight into the tenant. Prowler's `entra_admin_users_cloud_only` checks this.

## Conditional Access and the sync account

The directory synchronisation account signs in non-interactively from the sync server. It is commonly excluded from MFA policies and should be restricted by other means instead (trusted location, a dedicated policy). Prowler's `entra_conditional_access_policy_directory_sync_account_excluded` examines this exclusion.

## Matching and takeover risks

- **Soft match** joins an on-premises object to an existing cloud user by UPN/proxyAddress. **Hard match** joins them by `onPremisesImmutableId`.
- Both can let on-premises admins take over a cloud account. Microsoft blocks soft match onto accounts holding admin roles by default, and hard-match takeover can be blocked (`BlockCloudObjectTakeoverThroughHardMatch`, assessed by Prowler's `entra_directory_sync_object_takeover_blocked`).

## Assessment procedure

1. Identify the sign-in model and every server in the sync and authentication path.
2. Confirm that privileged cloud roles are held by cloud-only accounts.
3. Review the sync account's CA exclusions and the hard/soft-match protections.
4. Check AD FS token-signing certificate custody, or plan migration to PHS.
