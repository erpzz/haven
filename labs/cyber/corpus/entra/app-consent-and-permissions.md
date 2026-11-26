---
id: entra.apps.consent
title: App registrations, service principals, OAuth consent and Graph permissions
domain: entra
topic: applications
source_url: https://learn.microsoft.com/entra/identity-platform/permissions-consent-overview
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0 servicePrincipal / oAuth2PermissionGrant / appRoleAssignment
license: original-summary (Haven authored; Microsoft Learn linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id, microsoft-graph, oauth2]
prerequisites: []
see_also: [https://learn.microsoft.com/entra/identity/enterprise-apps/configure-user-consent, https://learn.microsoft.com/graph/permissions-reference]
---

# App registrations, service principals and consent

## Objects

- **Application (app registration)**: the global definition in the home tenant (`appId`, credentials, requested permissions, redirect URIs).
- **Service principal (enterprise application)**: the local instance in each tenant where the app is used. Permissions are granted to the service principal.
- **Delegated permissions** (scopes) let the app act *as the signed-in user*, never beyond what the user can do. Stored as `oAuth2PermissionGrant`; `consentType: AllPrincipals` means an admin consented for every user, `Principal` means one user consented for themselves.
- **Application permissions** (app roles) let the app act *as itself* with no user, across the tenant. Stored as `appRoleAssignment` on the resource service principal (for Graph, appId `00000003-0000-0000-c000-000000000000`). They always need admin consent.

## High-risk permissions

Application permissions that should trigger review: `RoleManagement.ReadWrite.Directory`, `AppRoleAssignment.ReadWrite.All`, `Application.ReadWrite.All`, `Directory.ReadWrite.All`, `Mail.ReadWrite`/`Mail.Read` (all mailboxes), `Files.ReadWrite.All`, `Sites.FullControl.All`, `User.ReadWrite.All`. The first three allow privilege escalation to Global Administrator equivalence.

## Illicit consent grant pattern

An attacker registers a multi-tenant app with a convincing name and phishes users to consent to delegated scopes such as `Mail.Read`, `offline_access`, `Files.Read`. Indicators: a recently created service principal from an unverified publisher, user-level grants (`consentType: Principal`) for mail or file scopes, audit log activity "Consent to application", and sign-ins by the app from unusual locations.

## Controls

- Restrict user consent to verified publishers and low-risk permissions, or disable it; enable the admin consent workflow.
- Review credentials: secrets and certificates on apps that hold high privileges, especially long-lived secrets; prefer certificates or federated credentials.
- Remove unused high-privilege grants.

## Troubleshooting Graph permission errors

- `403 Authorization_RequestDenied` with a delegated token: the user lacks the directory role or the scope was not consented. Delegated access is the intersection of the scope and the user's own rights.
- `403` with an application token: the application permission was requested but admin consent was never granted, or the token was issued before consent (get a new token; check the `roles` claim).
- Check the token: delegated tokens carry `scp`; application tokens carry `roles`.
