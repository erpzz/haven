# Evidence admission gap analysis — 2026-11-25

Workstream: #126. Proposed implementation: `evidence_admission.py`. Base `main`: `53387e74a0ad90786ac3ea16753c8ad99142e9df`.

This is an **additive pre-verifier boundary**, not a replacement for Haven Cyber's domain-specific independent verifier or Purple Copilot's answer verifier. The correct integration order is:

`producer / normalizer → strict evidence admission → existing Haven Cyber re-derivation → model-facing rendering → existing answer verifier`.

## Exact source reviewed

- PR #105 head `69f7ae3725b7a4a832a4ce17317d6351eb2a5293`
  - `labs/cyber/haven_cyber/evidence.py` blob `31a9c60e732df84d30af8f4a8ee0eb5c1be5c9d7`
  - `labs/cyber/haven_cyber/verifier.py` blob `eb0b84200f11566fccc84712220aee701d83e7f1`
  - `labs/cyber/tests/test_evidence_and_verifier.py` blob `dabe6b714187fcb4d3fd076af839d1aea4925f40`
  - `SECURITY_EVIDENCE_SCHEMA.md` blob `e0e570be464ea339a865f46ce2a303b8a78f8a6f`
- PR #122 head `f701cd766e7068649c4722874a6ced1b2213fbdf`
  - Purple Copilot `apm/review.py` and `tests/test_review.py`
  - integrated investigator boundary/triage from #114/#116.

## Gaps in the PR #105 evidence intake contract

These findings are source-reading results, not claims that the existing verifier is generally unsafe.

1. **Duplicate observation IDs are ambiguous.** `verify()` builds `obs = {o.id: o for o in bundle.observations}`. Duplicate IDs silently last-win before a finding resolves its evidence. The admission gate rejects duplicate artifact hashes, observation IDs and finding IDs.

2. **Finding artifact lineage is not cross-checked.** Existing completeness requires a failing finding to have a non-empty `artifacts[]`, but consistency follows each observation's `artifact` and does not require `Finding.artifacts` to equal the artifacts actually supporting its observations. The admission gate requires exact lineage equality.

3. **A producer can arrive pre-verified.** The schema says verification is set by the verifier, but intake does not require the producer state to be exactly `reported` with empty verification notes. The existing verifier catches `confirmed` self-certification but other pre-set states are not an intake rejection. The admission gate rejects every pre-verified state/note.

4. **Inline artifacts bypass byte-hash verification.** `load_artifact()` returns `inline[sha]` directly when supplied and does not re-hash original raw bytes. Parsed objects cannot prove the recorded byte hash. The new gate intentionally verifies raw artifact bytes from a bounded root; an integration that needs inline artifacts should transport their original bytes, not only parsed objects.

5. **Artifact paths are not confined by the verifier.** Existing code accepts absolute paths and joins relative paths to `root` without a containment check. The strict profile permits only relative, traversal-free paths and verifies the resolved target remains under the supplied root (including symlink escape detection).

6. **Malformed artifact JSON can escape the verifier as an exception.** Existing `load_artifact()` calls `json.loads` without turning parse/duplicate-key failures into evidence problems. The gate rejects malformed JSON, duplicate keys and non-finite JSON before pointer verification.

7. **Python equality is not exact JSON-value equality.** Existing comparison uses `actual != o.value`; in Python, `True == 1`. The schema describes the observation value as exactly what was there, so the gate performs recursive type-strict comparison.

8. **Missing/unknown schema can be normalized silently by `EvidenceBundle.from_dict`.** It defaults absent `schema` to the current schema and dataclass construction is not a semantic validator. The gate requires exactly `haven-cyber-evidence-v1` and exact top-level/object shapes.

9. **Only failing findings are required to carry evidence.** A `pass` is also a material security conclusion. The strict profile requires both `pass` and `fail` findings to carry observation + artifact lineage; `fail` additionally requires remediation.

10. **RFC 6901 root semantics differ.** Existing `json_pointer_get` treats both `""` and `"/"` as the document root; RFC 6901 uses `""` for root and `"/"` for a member whose key is the empty string. The gate validates escape syntax and uses the RFC behavior.

## What the new gate deliberately does not do

- It does not independently decide whether HCA/Maester/Prowler findings are correct. Keep PR #105's separately written `recheck()` predicates.
- It does not establish producer identity or authenticity by itself.
- It does not validate a tenant, contact Graph, execute tools, or act on remediation.
- It does not replace Purple Copilot's model-output citation/number/principal verifier.
- It does not accept already-correlated/post-verifier bundles; this is specifically a producer-to-verifier admission profile.
- It does not make absolute-path evidence stores illegal everywhere. It defines a stricter contract for untrusted/model-adjacent evidence. Integration must decide how live collectors stage artifacts under a trusted root.

## Second-pass defects caught in this work

Author re-review/final-diff review found three defects in the new gate itself:
- malformed finding reference arrays could reach `set()` and crash on unhashable values after being flagged; fixed by guarding all lineage operations behind validated string-list types;
- the CLI originally used `read_bytes()` before applying the bundle-size check; fixed by reading at most `MAX_BUNDLE_BYTES + 1`.

These are retained in the regression suite. Author review is not independent qualification.
