# BREAKWATER — proof-carrying attack-path interruption plans

**Status:** experimental, self-contained, offline. This is an early implementation of an organizational defense-planning workflow, **not** evidence that an actual Ukrainian NGO is protected or that the product is the first of its kind.

## Product thesis

Existing platforms already share indicators, generate rules, map defensive techniques, and manage incident response. Our distinctive hypothesis is a **locally evaluated, evidence-linked interruption plan**: take an explicitly enumerated set of potential attack paths, assess which defender-side controls are claimed to interrupt them, and produce the least-cost candidate control changes **plus a machine-readable list of every still-uncovered path**. Keep organizational telemetry and asset inventories local.

Unlike a generic IOC feed, this attempts to answer: *Which small, reversible safeguards interrupt all attack paths we have modeled for this specific organization?* It does not assume anything about IP geolocation or attacker's ownership.

MITRE D3FEND already provides defensive countermeasure mappings: https://d3fend.mitre.org/about/ . More comprehensive optimization and attack-graph approaches predate this concept. Novelty is a **product hypothesis in workflow, auditability, civilian accessibility, and local privacy**, not a claimed new algorithm.

## Execute

```bash
python research/ukraine-civilian-cyber-defense/breakwater/breakwater.py research/ukraine-civilian-cyber-defense/breakwater/examples/clickfix-hypothetical.json --output breakwater-plan.json
python -m unittest discover -s research/ukraine-civilian-cyber-defense/tests -v
```

The example references [CERT-UA's UAC-0277 September 2026 advisory](https://cert.gov.ua/article/6319983). Its hypothetical alternative attack paths and control-step mappings are **analyst assumptions**, not assertions that the advisory documented every possible path.

### Contract (JSON manifest)
- `source_url`: HTTPS link to the cited public report.
- `attack_paths`: up to 40 uniquely identified paths, each with ordered, distinct step IDs. Enumerated paths are *not* guaranteed to cover a full campaign.
- `controls`: up to 16 unique controls, each with `interrupts` step IDs, `state`, `scope`, `rollback`, integer `effort` and `disruption`.
- `state=attested` only receives **model-level recognition** if `validated_utc` is within 30 days and `evidence_reference` exists. This is an unverified operator attestation, not independent validation.
- `state=candidate` represents a proposed control, never deployed automatically. `unavailable` is ignored.
- Cost model: `effort + 3×disruption`. Exact bounded set-cover selection returns the least-cost candidate combination for the remaining model paths. The weights are provisional assumptions; they are not scientifically calibrated.

### Truthfulness and security

- **No remote connections, data uploads, credential handling, live threat interactions, endpoint modifications or automatic defensive policy changes.**
- A plan covering every **modeled** path does **not** demonstrate real-world attack prevention. Unknown bypasses, unmodeled paths and faulty efficacy assumptions remain.
- Current first version does **not** empirically verify control operation, rank exploit likelihood or ingest a tenant. Runbook-driven validation and signed evidence are next work.
- Never publish real beneficiary network details or local evidentiary attestations. Use only authorized data; keep reports local.
- `NO_SUPPORTED_PLAN` identifies paths with no candidate mitigation. `PROPOSED_ONLY` does not mean anything is installed. `ATTESTED_IN_MODEL` means only user-supplied evidence references and dates met freshness rules.

### Next iterations (no speculative production claims)

1. Allow a consenting administrator to export privacy-preserving attestations of actually **tested** safeguards with control identifiers, test method and timestamp. Validation must not run destructive test traffic.
2. Add a separately verified check for Microsoft tenant protections, initially read-only and permission-scoped. Flag unsafe mappings as unverified rather than guessing.
3. Map D3FEND defensive techniques to prevention steps and add testable rollback runbooks.
4. Produce signed and expiring *defense capsules* that partner NGOs can verify locally, without exposing raw incident logs. This is an **unbuilt research feature**, not a completed privacy guarantee.
5. Compare independently with MISP/OpenCTI/CrowdSec and existing academic attack-graph planners; measure whether recommendations reduce operator time or false positives.

**Success criterion:** A consenting NGO can demonstrate that a recommended reversible control is installed and actually blocks a relevant harmless test case, while the same test's nonblocked path is explicitly surfaced. Until then: model-level planning only.
