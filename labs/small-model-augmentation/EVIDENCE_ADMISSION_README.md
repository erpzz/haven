# Strict evidence admission prototype

Workstream: #126. Base: `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; no self-merge.

The implementation is `evidence_admission.py`; source audit and integration rationale are in `EVIDENCE_GAP_ANALYSIS.md`.

## Purpose

PR #105 already has a valuable independent domain verifier. This package adds a fail-closed **producer-to-verifier admission boundary** so ambiguous or malformed evidence cannot reach that verifier as if its structure and lineage were trustworthy.

The intended order is:

`producer / normalizer → evidence admission → existing independent re-derivation → model rendering → answer verifier`.

## Enforced properties

- exact `haven-cyber-evidence-v1` schema and object shapes;
- unique artifact hashes, observation IDs and finding IDs;
- relative traversal-free artifact paths under a caller-supplied root;
- exact finding ↔ observation ↔ artifact lineage;
- producer findings enter only as `reported` with no verification notes;
- both pass and fail conclusions carry evidence; fail also carries remediation;
- bounded bundle and artifact reads;
- strict duplicate-key/non-finite JSON rejection;
- RFC 6901 pointer syntax and resolution;
- recursive type-strict observation equality (so JSON boolean `true` cannot validate recorded integer `1`);
- fixed-code/redacted receipts.

## Author tests and second pass

Initial implementation: 16/16 unit tests passed in the ChatGPT Linux sandbox.

Mandatory second pass then found two defects in this package itself:
1. malformed finding reference arrays could be flagged and then still crash during `set()`/membership logic;
2. the CLI originally called `read_bytes()` before applying the bundle size limit.

Both were fixed. A local semantic rerun of the complete logic plus second-pass cases passed **19/19** in 4.281 s, including malformed reference arrays, non-finite/non-JSON observation values and bounded file reads.

Final published blobs after the fixes:
- `evidence_admission.py`: `0daa7495a1778c740a444b8f2a3a7b5385b9e953`
- `test_evidence_admission.py`: `b17170ccfea01b02f90936d07094d0943a29e817`

**Exact final-commit clean-checkout execution is NOT claimed.** The sandbox could not resolve `raw.githubusercontent.com` when attempting to pull the commit back for execution. The connector was used to re-read the final files, but it cannot execute them. A clean-checkout run is therefore explicitly assigned to the Codex/local validation queue.

## Integration constraints

- Do not replace PR #105's `recheck()` domain predicates.
- Do not treat this gate as producer authentication.
- Existing inline parsed-object evidence cannot prove a byte hash; integration should supply original artifact bytes or stage them under a trusted root.
- This strict intake profile intentionally rejects absolute artifact paths. Confirm real producer compatibility before wiring.
- The path root is assumed to be a trusted local staging directory. A same-user concurrent filesystem attacker and symlink TOCTOU hardening are not qualified here.
- No live tenant, model, MCP process, network assessment, macOS integration, CI or M4 reserve was used.
