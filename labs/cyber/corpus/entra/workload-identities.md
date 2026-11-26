---
id: entra.workload-identities
title: Managed identities and workload identity federation
domain: entra
topic: workload-identity
source_url: https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Entra ID / Azure (service, unversioned)
license: original-summary (Haven authored; Microsoft Learn linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id, azure, managed-identity]
prerequisites: []
see_also: [https://learn.microsoft.com/entra/workload-id/workload-identity-federation]
---

# Managed identities and workload identity federation

## Types

- **System-assigned** managed identity: lifecycle tied to one Azure resource; deleted with it.
- **User-assigned** managed identity: a standalone resource that can be attached to many resources; survives them. Anyone who can attach it (needs `Microsoft.ManagedIdentity/userAssignedIdentities/*/assign/action`) can act as it.
- Both are service principals in Entra (`servicePrincipalType: ManagedIdentity`) with no secrets to manage; code obtains tokens from the local instance metadata endpoint (169.254.169.254) or the App Service identity endpoint.

## Workload identity federation

An app registration or user-assigned identity trusts tokens from an external issuer (GitHub Actions, Kubernetes, another cloud) for a specific subject. The `subject` must be narrow, for example `repo:org/repo:ref:refs/heads/main` or `repo:org/repo:environment:prod`. A wildcard-like or pull-request subject lets untrusted workflows obtain the identity.

## Risks to assess

- A managed identity holding Owner/Contributor at subscription or management-group scope: compromise of the hosting resource (SSRF to the metadata endpoint, code execution) becomes control of the subscription.
- Managed identities granted Graph application permissions.
- Federated credentials with broad subjects.

## Assessment procedure

List service principals of type ManagedIdentity, their Azure role assignments with scope, and any Graph app role assignments. Map each identity to the resources that can use it.
