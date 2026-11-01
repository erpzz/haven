---
id: detection.attack-sigma
title: Mapping observations to MITRE ATT&CK and Sigma detections
domain: detection
topic: detection-engineering
source_url: https://attack.mitre.org/resources/legal-and-branding/terms-of-use/
source_org: MITRE / SigmaHQ
published: null
retrieved: 2026-10-31
product_version: ATT&CK Enterprise (verify the current release); Sigma specification 2.x
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [mitre-attack, sigma]
prerequisites: []
see_also: [https://github.com/SigmaHQ/sigma-specification, https://github.com/mitre-attack/attack-stix-data]
---

# Mapping to ATT&CK and Sigma

## ATT&CK

Techniques have stable ids (`T1110` Brute Force, sub-technique `T1110.003` Password Spraying). Use the STIX 2.1 bundles in mitre-attack/attack-stix-data for authoritative ids, names, platforms and data sources; ATT&CK content is free to use with attribution under MITRE's terms of use. Map an observation to a technique only when the observed behaviour matches it, and record the data source that saw it.

Identity techniques that recur in Entra investigations: T1078.004 Valid Accounts: Cloud Accounts; T1110.003 Password Spraying; T1621 Multi-Factor Authentication Request Generation; T1528 Steal Application Access Token; T1098.001 Additional Cloud Credentials; T1098.003 Additional Cloud Roles; T1556.009 Modify Authentication Process: Conditional Access Policies; T1484.002 Domain or Tenant Policy Modification: Trust Modification.

## Sigma

A Sigma rule is YAML: `title`, `id` (UUID), `status`, `logsource` (`product`, `service`, `category`), `detection` (named selections plus a `condition`), `falsepositives`, `level`, `tags` (e.g. `attack.t1110.003`). pySigma converts rules to backend queries (Splunk, KQL for Microsoft Sentinel, Elasticsearch) through backends and processing pipelines. SigmaHQ rules are under the Detection Rule License (DRL) 1.1, which requires attribution when rules are used or redistributed; pySigma is LGPL-2.1.

## Practice

- A detection fires on telemetry; a posture finding describes a configuration. Link them: "legacy authentication is not blocked" (posture) pairs with a detection for legacy-protocol sign-in failures (activity).
- Validate a rule against known-good and known-bad samples before relying on it; record false-positive sources in `falsepositives`.
