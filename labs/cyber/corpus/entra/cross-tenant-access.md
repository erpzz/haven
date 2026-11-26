---
id: entra.cross-tenant
title: Cross-tenant access settings and guest access
domain: entra
topic: external-identities
source_url: https://learn.microsoft.com/entra/external-id/cross-tenant-access-overview
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0 crossTenantAccessPolicy
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id, b2b]
prerequisites: []
see_also: [https://learn.microsoft.com/entra/external-id/cross-tenant-access-settings-b2b-collaboration]
---

# Cross-tenant access settings and guest access

## Model

- **Default settings** apply to every external organisation; **organisational settings** override them for named partner tenants.
- Each has **inbound** (external users coming into your tenant) and **outbound** (your users going to other tenants) rules for B2B collaboration and B2B direct connect, by users/groups and applications.
- **Inbound trust settings** decide whether your Conditional Access accepts the partner's MFA, compliant-device and hybrid-joined claims. Trusting MFA from a partner means your MFA policy is satisfied by their MFA.
- **Tenant restrictions v2** controls which external tenants your users can sign in to from your managed devices and network.

## Assessment

1. Default outbound: are users allowed to collaborate with any tenant? Many organisations restrict outbound to partner tenants to reduce data exfiltration via guest accounts elsewhere.
2. Default inbound trust: is MFA trusted from all tenants? That delegates your MFA assurance to every tenant on the internet; trust should be set per partner.
3. Guests in privileged roles or in groups excluded from Conditional Access.
4. Conditional Access coverage for guests: `includeUsers: All` covers guests; a policy limited to members does not.

## Common false positive

Inbound trust for MFA from a specific, known partner tenant is a deliberate, documented decision, not a misconfiguration.
