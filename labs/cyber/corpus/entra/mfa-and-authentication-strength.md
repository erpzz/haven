---
id: entra.auth.mfa-strength
title: MFA, authentication strengths and phishing-resistant methods
domain: entra
topic: authentication
source_url: https://learn.microsoft.com/entra/identity/authentication/concept-authentication-strengths
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0 authenticationStrengthPolicy
license: original-summary (Haven authored; Microsoft Learn linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id, microsoft-graph]
prerequisites: [Entra ID P1 for Conditional Access]
see_also: [https://learn.microsoft.com/entra/identity/conditional-access/policy-admin-phish-resistant-mfa, https://learn.microsoft.com/entra/identity/conditional-access/howto-conditional-access-policy-all-users-mfa]
---

# MFA, authentication strengths and phishing-resistant methods

## Grant control `mfa` versus authentication strength

- `builtInControls: ["mfa"]` accepts any registered second factor, including SMS, voice and push notifications. These are **not** phishing resistant: an adversary-in-the-middle proxy can relay the prompt and steal the session cookie.
- `grantControls.authenticationStrength` names an authentication strength policy. Three are built in, with fixed ids:
  - `00000000-0000-0000-0000-000000000002` Multifactor authentication (same methods as the `mfa` control).
  - `00000000-0000-0000-0000-000000000003` Passwordless MFA.
  - `00000000-0000-0000-0000-000000000004` Phishing-resistant MFA: FIDO2 security keys and passkeys, Windows Hello for Business and certificate-based multifactor authentication.
- Custom strengths list `allowedCombinations`. A custom strength is phishing resistant only if **every** allowed combination is (`fido2`, `windowsHelloForBusiness`, `x509CertificateMultiFactor`). One `sms` or `microsoftAuthenticatorPush` combination makes the whole strength phishable.

## Operator semantics that change the answer

- `operator: OR` with `["mfa", "compliantDevice"]` means a user on a compliant device is **not** asked for MFA. Such a policy does not "require MFA"; it requires MFA *or* a compliant device.
- `operator: AND` with `["mfa", "compliantDevice"]` requires both.
- A policy can use either `mfa` in `builtInControls` or an authentication strength, not both together.

## Assessment procedure

1. For each target population (all users, administrators, guests), find enabled policies covering all cloud apps and all client app types.
2. Check the grant: does every way of satisfying it involve MFA? For admins, is the strength phishing resistant?
3. Resolve exclusions and role scope: `includeRoles` covers only users who **actively** hold the role at sign-in. PIM-eligible users are covered once they activate.
4. Report-only and disabled policies do not count.

## Common false positives

- Flagging "MFA not required" when a different enabled policy with an authentication strength covers the population.
- Flagging an `OR` policy as compliant because the `mfa` string appears in the control list.

## Remediation

Require the Phishing-resistant MFA strength for privileged roles. Require MFA (or a stronger strength) for all users. Register at least two phishing-resistant methods for each administrator before enforcing, and test with the What If tool and report-only mode first.
