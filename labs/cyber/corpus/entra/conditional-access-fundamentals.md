---
id: entra.ca.fundamentals
title: Conditional Access policy model and evaluation
domain: entra
topic: conditional-access
source_url: https://learn.microsoft.com/entra/identity/conditional-access/overview
source_org: Microsoft
published: null
retrieved: 2026-10-31
product_version: Microsoft Graph v1.0 conditionalAccessPolicy
license: original-summary (Haven authored; Microsoft Learn linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [entra-id, microsoft-graph]
prerequisites: [Entra ID P1 for Conditional Access]
see_also: [https://learn.microsoft.com/graph/api/resources/conditionalaccesspolicy]
---

# Conditional Access policy model and evaluation

## Policy shape (Graph `conditionalAccessPolicy`)

A policy has `state`, `conditions`, `grantControls` and `sessionControls`.

- `state` is one of `enabled`, `disabled` or `enabledForReportingButNotEnforced` (report-only). Only `enabled` policies enforce anything. A report-only policy records what it *would* have done in the sign-in log but never blocks or challenges a user. Treat a report-only policy as **not a control** when assessing coverage.
- `conditions.users` holds `includeUsers`, `excludeUsers`, `includeGroups`, `excludeGroups`, `includeRoles`, `excludeRoles` and optionally `includeGuestsOrExternalUsers` / `excludeGuestsOrExternalUsers`. The special value `All` in `includeUsers` targets every user, including guests. `GuestsOrExternalUsers` targets guests only. `None` targets nobody.
- `conditions.applications.includeApplications` accepts app IDs or the special values `All`, `Office365` and `MicrosoftAdminPortals`.
- `conditions.clientAppTypes` accepts `all`, `browser`, `mobileAppsAndDesktopClients`, `exchangeActiveSync` and `other`. Legacy authentication protocols are represented by `exchangeActiveSync` and `other`.
- Other conditions: `signInRiskLevels`, `userRiskLevels` (Identity Protection, P2), `platforms`, `locations`, `devices` (filter), `authenticationFlows.transferMethods` (`deviceCodeFlow`, `authenticationTransfer`).
- `grantControls.builtInControls` can contain `block`, `mfa`, `compliantDevice`, `domainJoinedDevice`, `approvedApplication`, `compliantApplication` and `passwordChange`. `grantControls.operator` is `AND` or `OR`. `grantControls.authenticationStrength` references an authentication strength policy by `id`.

## Evaluation rules that matter for assessments

1. All applicable `enabled` policies are evaluated together. Requirements from every matching policy must be satisfied (logical AND across policies).
2. `block` wins: if any applicable enabled policy blocks, access is blocked regardless of other grants.
3. **Exclusions beat inclusions.** A user excluded by `excludeUsers`, `excludeGroups` or `excludeRoles` is out of scope even if also included. An excluded group therefore silently removes every one of its members from the control.
4. A policy only applies when *all* of its configured conditions match. A policy restricted to `clientAppTypes: [browser]` does not cover desktop clients.
5. Within `grantControls`, `OR` means any one listed control satisfies the policy; `AND` means all are needed.

## Assessment checklist

- Confirm `state == enabled` before counting a policy as coverage.
- Resolve exclusions: list each excluded user/group/role and check whether it is a documented emergency-access account or an over-broad group.
- Check that application scope is `All` (or the intended set) and that `clientAppTypes` is not narrowing coverage unintentionally.
- Record the policy `id`, not only `displayName`; display names are not unique.

## Common false positives

- A tool reports "MFA not enforced" because it only looked at one policy while another enabled policy covers the same users.
- A tool counts a report-only policy as enforcing (false negative) or a disabled duplicate as a gap when an enabled equivalent exists (false positive).
- Excluding emergency-access accounts from a blocking policy is *expected*, not a weakness, provided those accounts are monitored and protected with phishing-resistant credentials.
