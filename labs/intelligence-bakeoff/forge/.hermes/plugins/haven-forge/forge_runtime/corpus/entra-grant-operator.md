---
{
  "id": "entra-grant-operator",
  "version": 1,
  "title": "Conditional Access MFA AND OR grant controls compliantDevice alternatives",
  "source_url": "https://learn.microsoft.com/en-us/graph/api/resources/conditionalaccessgrantcontrols?view=graph-rest-1.0",
  "source_license": "CC-BY-4.0 (Microsoft Graph documentation; code samples have separate terms)",
  "content_license": "CC0-1.0 (original short project-authored explanatory card; no copied passages)",
  "attribution": "Microsoft Graph documentation, Microsoft contributors; original Forge paraphrase.",
  "verified_on": "2026-10-31",
  "applicability": "Microsoft Graph v1.0; synthetic per-policy analysis only",
  "verification": "Inspect builtInControls together with operator; never check the presence of mfa alone.",
  "remediation": "Require MFA in a suitable applicable policy after reviewing exclusions and emergency access."
}
---
# Conditional Access MFA AND OR grant controls compliantDevice alternatives

Grant controls use AND or OR. In the supported subset, mfa AND compliantDevice requires both; mfa OR compliantDevice permits the device alternative. This is a per-policy logical requirement, not proof of tenant-wide MFA coverage.
