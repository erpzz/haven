---
id: azure.policy-defender
title: Azure Policy, Defender for Cloud and Resource Graph for posture management
domain: azure
topic: posture
source_url: https://learn.microsoft.com/azure/governance/policy/overview
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Azure Policy / Defender for Cloud / Resource Graph (service, unversioned)
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [azure, azure-policy, defender-for-cloud, resource-graph]
prerequisites: []
see_also: [https://learn.microsoft.com/azure/governance/resource-graph/overview, https://learn.microsoft.com/azure/defender-for-cloud/defender-for-cloud-introduction]
---

# Azure Policy, Defender for Cloud and Resource Graph

## Azure Policy

- Definitions are assigned at management-group, subscription or resource-group scope; initiatives (policy sets) group definitions.
- Effects: `Deny` (blocks non-compliant create/update), `Audit`, `AuditIfNotExists`, `DeployIfNotExists` and `Modify` (remediate via a managed identity), `Append`, `DenyAction`, `Disabled`.
- A newly assigned `Deny` policy does not change existing resources; they show as non-compliant until fixed. `DeployIfNotExists`/`Modify` fix existing resources only through a remediation task.
- Exemptions (`Waiver`, `Mitigated`) remove a scope from evaluation; review them like firewall exceptions.

## Defender for Cloud

- Foundational CSPM (free) gives the secure score and recommendations. Defender CSPM and workload plans (Defender for Servers, Storage, Key Vault, Containers, SQL, ...) are enabled per subscription and add threat detection and attack-path analysis.
- A recommendation is a posture finding; an **alert** is a detection of activity. Do not conflate them.

## Azure Resource Graph

Read-only KQL over resources across subscriptions the caller can read. Tables include `resources`, `authorizationresources` (role assignments and definitions), `securityresources` (Defender assessments), `policyresources`. Results respect the caller's RBAC, so missing rows can mean missing permission, not a missing resource. Paging uses a skip token (default page 100, max 1000).

Example query shape (storage accounts allowing public blob access):

    resources
    | where type =~ 'microsoft.storage/storageaccounts'
    | where properties.allowBlobPublicAccess == true
    | project name, resourceGroup, subscriptionId
