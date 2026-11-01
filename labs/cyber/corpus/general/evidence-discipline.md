---
id: general.evidence
title: Evidence discipline: observations, inferences and verification
domain: general
topic: methodology
source_url: https://csrc.nist.gov/pubs/sp/800/115/final
source_org: NIST
published: null
retrieved: 2026-10-31
product_version: NIST SP 800-115 (2008); Haven evidence schema v1
license: original-summary (Haven authored; source linked, not copied)
reuse: training-allowed
verification: author-summary
technologies: [all]
prerequisites: []
see_also: [https://csrc.nist.gov/pubs/sp/800/61/r3/final]
---

# Evidence discipline

## Rules

1. Separate what was **observed** (a field value, a log line, a command's output) from what is **inferred** (a vulnerability, a misconfiguration, an attack).
2. A scanner or tool saying "vulnerable" is a **claim**. Record it as reported until re-derived from raw data or tested in a lab.
3. Cite the exact artifact and location (policy id and field, log record id, command and output line). Display names are not identifiers.
4. State limitations: missing permissions, partial data, sampled logs, version-only detection.
5. Give the next validation step: the query, API call or lab test that would confirm or refute the claim.
6. Never fabricate tool output. If a tool failed, say so and either fix the invocation or report the gap.

## Verification states (Haven)

`reported` → `corroborated` (independently re-derived from raw evidence) or `refuted` (raw evidence contradicts it) or `insufficient_evidence` (references do not resolve, data incomplete) → `confirmed` (human review or controlled lab reproduction only).

## Severity versus confidence

Severity is the impact if true; confidence is how strongly the evidence supports it. A critical-severity claim from a banner-only version match is still low confidence.
