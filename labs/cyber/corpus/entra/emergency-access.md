---
id: entra.emergency-access
title: Emergency access (break-glass) accounts
domain: entra
topic: resilience
source_url: https://learn.microsoft.com/entra/identity/role-based-access-control/security-emergency-access
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Entra ID (service, unversioned)
license: original-summary (Haven authored; Microsoft Learn linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id]
prerequisites: []
see_also: [https://learn.microsoft.com/entra/identity/conditional-access/plan-conditional-access]
---

# Emergency access accounts

## Purpose

Two or more cloud-only accounts with permanent Global Administrator, used only when normal admin access fails (federation outage, MFA provider outage, a Conditional Access misconfiguration that locks everyone out).

## Recommended configuration

- Cloud-only (`*.onmicrosoft.com`), not synchronised, not federated, not tied to an individual.
- Strong phishing-resistant credentials (FIDO2 keys or certificate-based authentication) kept in separate secure locations. Microsoft requires MFA for admin portal sign-in, so plan a phishing-resistant method rather than no MFA.
- **Excluded from Conditional Access policies**, at least from every policy that could lock them out, typically via a dedicated exclusion group containing only these accounts. The exclusion group itself must be protected (role-assignable, monitored).
- Sign-in alerting: every sign-in by these accounts should page someone.
- Regular validation that the accounts still work.

## Assessment procedure

1. Confirm at least two emergency accounts are declared and hold Global Administrator.
2. For every enabled Conditional Access policy, resolve whether the emergency accounts are in scope (directly, via groups or via roles such as Global Administrator) and not excluded.
3. Any enabled policy that applies to them is a lockout risk; a policy whose grant is `block` is the most severe.
4. Check that no *other* accounts are hidden in the emergency exclusion group.

## Common false positives

- A policy scoped to a group that does not contain the emergency accounts does not need to exclude them.
- A "missing exclusion" on a disabled or report-only policy is not a current lockout risk.
