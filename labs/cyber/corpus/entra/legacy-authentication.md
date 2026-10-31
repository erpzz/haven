---
id: entra.ca.legacy-auth
title: Blocking legacy authentication with Conditional Access
domain: entra
topic: conditional-access
source_url: https://learn.microsoft.com/entra/identity/conditional-access/policy-block-legacy-authentication
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0
license: original-summary (Haven authored; Microsoft Learn linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id, exchange-online]
prerequisites: [Entra ID P1]
see_also: [https://learn.microsoft.com/entra/identity/conditional-access/concept-conditional-access-conditions]
---

# Blocking legacy authentication

## Why

Legacy protocols (POP, IMAP, SMTP AUTH, older Exchange ActiveSync and other basic-auth clients) cannot perform MFA. Password-spray and credential-stuffing campaigns favour them because a correct password alone is enough.

## What a compliant policy looks like

- `state: enabled`
- `conditions.users.includeUsers: ["All"]`, with exclusions limited to documented emergency-access accounts or service accounts that are being migrated.
- `conditions.applications.includeApplications: ["All"]`
- `conditions.clientAppTypes` contains **both** `exchangeActiveSync` and `other`.
- `grantControls.builtInControls: ["block"]`

## Assessment procedure

1. List enabled policies whose `clientAppTypes` include `exchangeActiveSync` and/or `other` and whose grant is `block`.
2. If only one of the two client types is listed, coverage is partial: report which protocol family remains open.
3. If the policy is report-only, legacy authentication is **not** blocked; the sign-in log will only show "reportOnlyFailure" results.
4. Check exclusions. An excluded group with many members re-opens legacy auth for all of them.
5. Corroborate with sign-in logs: filter `clientAppUsed` for legacy clients over the last 30 days to find who still depends on them before enforcing.

## Remediation

Create or enable a block policy as above, starting in report-only mode for a short observation window, then switch `state` to `enabled`. Security defaults also block legacy authentication, but security defaults and Conditional Access cannot be used together.

## Known limitations

A Conditional Access block happens after the primary credential is validated, so failed sign-ins still reveal whether a password is correct (error 53003 vs 50126). Pair the block with smart lockout and sign-in monitoring.
