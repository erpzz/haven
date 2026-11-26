---
id: entra.logs.signin
title: Sign-in and audit logs: fields, error codes and detections
domain: entra
topic: detection
source_url: https://learn.microsoft.com/entra/identity/monitoring-health/concept-sign-ins
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0 signIn / directoryAudit
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id, log-analytics]
prerequisites: []
see_also: [https://learn.microsoft.com/entra/identity-platform/reference-error-codes]
---

# Sign-in and audit logs

## Useful sign-in fields (Graph `signIn`)

`userPrincipalName`, `appDisplayName`, `clientAppUsed` (legacy values include `IMAP4`, `POP3`, `SMTP`, `Exchange ActiveSync`, `Authenticated SMTP`, `Other clients`), `ipAddress`, `location`, `status.errorCode` / `status.failureReason`, `conditionalAccessStatus` (`success`, `failure`, `notApplied`), `appliedConditionalAccessPolicies[]` with each policy's `result` (`success`, `failure`, `notApplied`, `reportOnlySuccess`, `reportOnlyFailure`, ...), `authenticationRequirement` (`singleFactorAuthentication` / `multiFactorAuthentication`), `riskLevelDuringSignIn`, `isInteractive`.

## Error codes worth knowing

- `0`: success.
- `50126`: invalid username or password. Many 50126 failures across many accounts from few IPs is the signature of password spray.
- `50053`: account locked (smart lockout) or sign-in from a malicious IP blocked.
- `50057`: account disabled.
- `50074` / `50076`: strong authentication (MFA) required; the user has not completed it yet. Not by itself a failure of a control.
- `50079`: user must register for MFA.
- `53003`: access blocked by Conditional Access. It implies the password was **correct** (Conditional Access is evaluated after primary authentication).
- `500121`: authentication failed during the strong-authentication request (MFA denied or timed out); repeated 500121 can indicate MFA fatigue.
- `530032`: blocked by a security defaults or authentication policy requirement.

## Patterns

- **Password spray**: one or a few source IPs, many distinct users, low attempts per user, mostly 50126, occasional success or 53003 (correct password found but blocked).
- **Brute force**: one user, many attempts, lockouts (50053).
- **MFA fatigue**: repeated 500121 for one user followed by a success.
- **Legacy-protocol spray**: failures with `clientAppUsed` = IMAP/POP/SMTP; legacy protocols cannot do MFA.
- A success with `authenticationRequirement: singleFactorAuthentication` for an admin means no policy forced MFA for that sign-in.

## Audit log activities (Graph `directoryAudit`)

`Consent to application`, `Add app role assignment to service principal`, `Add member to role`, `Add eligible member to role`, `Update conditional access policy`, `Add service principal credentials`, `Update application – Certificates and secrets management`. Each records `initiatedBy` (user or app) and `targetResources`.

## ATT&CK mapping

Password spray: T1110.003. Valid cloud accounts: T1078.004. Illicit consent / OAuth app abuse: T1528 (steal application access token) and T1098.003 (account manipulation: additional cloud roles) when roles are added. MFA request generation (fatigue): T1621.
