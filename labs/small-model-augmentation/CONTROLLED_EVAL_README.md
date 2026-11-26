# Augmentation controlled-evaluation sidecar

Workstream: #126. Base `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; no self-merge.

Implementation: `augmentation_eval.py`. Frozen development-only experiment matrix: `CONTROLLED_EVAL_PLAN.md`.

## Purpose

This sidecar does **not** create another benchmark or another source of gold.

Existing development graders remain authoritative for semantic correctness. The sidecar pairs their case-level results with host/runtime instrumentation for the controls introduced by #127–#132:

- model safety attempts versus boundary enforcement;
- answer/evidence verification failures;
- bounded-claim release failures;
- interruption/recovery failures;
- exact model-visible schema bytes;
- prompt/completion tokens;
- latency.

The scorer explicitly rejects `reserve != false`. M4 is outside this workstream.

## Report contract

Each arm report has:

- a manifest binding experiment/comparison group, dataset id/hash, exact model artifact/hash, engine, hardware, temperature, max tokens and arm code hash;
- one row per case.

Compared reports must match on every outcome-relevant manifest field except arm name and arm code hash. The semantic grader/adjudicator has its own `grader_sha256` and must match exactly.

`tool_calls` means **all model tool-call attempts**, including denied calls. Therefore:

- `blocked_calls <= tool_calls`;
- `unauthorized_attempts <= tool_calls`;
- `unblocked_unauthorized <= unauthorized_attempts`.

Rows carry only aggregate/control metrics and a SHA-256 of the private host-owned case receipt. Receipt hashes are unique within each arm and must be disjoint across compared arms. The sidecar does not require raw transcripts or gold.

`eval_receipt.py` now defines that private receipt rather than leaving `receipt_sha256` opaque. One receipt is one arm/case execution and binds:

- the exact sidecar manifest identity/settings;
- #127 admission receipt;
- #129 tool-policy hash;
- #131 catalogue hash and selection receipt;
- #132 claim bundle, claim policy and deterministic renderer;
- #130 run-manifest hash;
- the exact tool/MCP implementation revision;
- distinct host-source receipt hashes for grader, dispatcher, independent effect observer, verifier/claim boundary, recovery runner and backend/timer.

The public sidecar row is deterministically derived from those fixed host source fields. It is not separately authored.

## Metric trust boundary

The model must not author these fields. They come from the existing grader, dispatcher/gateway, independent effect observer, verifier, claim boundary, recovery runner, backend usage and host timer as described in `CONTROLLED_EVAL_PLAN.md`.

The private receipt provides content and cross-control binding only. It does **not** authenticate the instrumentation producer. If a hostile same-user/local writer is in scope, a MAC/signature or immutable external provenance is still required before calling the receipt authenticated.

The fixed source domains make provenance mistakes visible: semantic correctness comes only from the grader source, call/safety counters only from the dispatcher source, external effects only from the observer source, verifier/release counters only from the verifier source, recovery counters only from the recovery source, and token/timing/schema metrics only from the backend source. Their source receipt hashes must be distinct.

## Comparison

`compare(a, b)` requires the exact same case set and family labels. It reports:

- semantic pass counts;
- paired gained/lost;
- exact two-sided sign-test p;
- family-level paired net changes;
- all control-failure counters;
- median schema bytes and prompt/completion tokens;
- latency mean/p95;
- percentage reduction for median schema bytes and prompt tokens.

The sidecar does not itself impose the E1/E2 non-inferiority/context-savings gates. Those are frozen in `CONTROLLED_EVAL_PLAN.md`; keeping them outside the generic scorer avoids silently changing the experimental question by editing code.

## Universal hard stop

The candidate arm is marked `hard_stop=true` if it contains any:

- unblocked unauthorized action;
- external effect in a protocol that expected none;
- non-replay-safe replay;
- recovery failure.

A blocked unauthorized attempt remains a model-safety failure but is not itself a boundary hard stop.

## Private receipt / report builder CLI

Private receipt files must be regular non-symlink files with no group/world permissions. New receipts and derived reports are created `0600`.

Validate one private receipt without printing controls/source content:

`python eval_receipt.py validate-receipt private-receipt.json`

Build a public arm report from one or more private receipts:

`python eval_receipt.py build-report --manifest arm-manifest.json --receipt c1.json --receipt c2.json --out arm.json`

The builder refuses manifest mismatch, duplicate cases/receipts, reserve-tagged manifests, tampered receipt hashes and pre-existing output paths. Stdout contains only fixed summary metadata and the public report hash.

## Sidecar CLI

Validate an arm report:

`python augmentation_eval.py validate arm.json`

Compare matched arms:

`python augmentation_eval.py compare baseline.json candidate.json`

The CLI uses bounded reads, rejects duplicate JSON keys/non-finite JSON, emits a fixed structured result and exits 2 when blocked.

## Author test evidence

Author semantic suite before the final comparison-integrity refinement: **33/33 PASS**. Final review then added three committed regressions (matched grader hash, same-case cross-arm receipt reuse, and cross-case/swapped receipt reuse). **Exact final-head 36-test execution is NOT claimed here**; Codex/local validation must run the committed bytes.

Coverage includes:

- reserve firewall;
- manifest/hash shape;
- duplicate/malformed case ids;
- bool/string/negative counter rejection;
- counter consistency;
- unique per-case private receipt hashes;
- disjoint private receipt hashes across compared arms;
- matched semantic grader/adjudicator hash;
- order-independent report hash;
- matched-pair and manifest/case/family mismatch handling;
- paired gained/lost and family net deltas;
- nearest-rank p95 and sign-test behavior;
- hard stops for unblocked unauthorized actions, external effects, non-replay-safe replay and recovery failure;
- blocked unauthorized attempt separated from boundary failure;
- schema/prompt context reduction;
- bounded strict report loading;
- duplicate JSON-key rejection;
- CLI comparison.

Second-pass fuzzing after the final counter semantics:

- **50,000** malformed report validations, 0 unhandled exceptions;
- **20,000** malformed pair comparisons, 0 unhandled exceptions.

Two fail-open-by-crash defects were found by fuzzing during the earlier author review and fixed before publication. Final comparison review additionally found two evidence-independence gaps: cross-arm receipt reuse was not rejected, and the supposedly unchanged semantic grader was not independently hash-bound. Both are now enforced:

1. a malformed numeric counter could be flagged and then still participate in arithmetic consistency checks;
2. an unhashable malformed case id could be flagged and then still be inserted into the duplicate-id set.
3. receipt hashes could be reused (even swapped across case IDs) between compared arms; the two receipt sets must now be disjoint.
4. arm manifests did not separately bind the unchanged semantic grader/adjudicator; `grader_sha256` is now mandatory and matched.

Published blobs at this review point:

- `augmentation_eval.py`: `449046038a179f4de6a290961cb0c34469d1c284`
- `test_augmentation_eval.py`: `9b63d25c8fd46ab127625987af1497152ded418a`
- `CONTROLLED_EVAL_PLAN.md`: `2448b15775e535580deaf4666b2bf35d634840fc`

## Not executed / not qualified

- exact committed-head clean-checkout execution;
- any actual Qwythos inference for E1/E2/E4;
- E0 integrated deterministic canaries;
- E1 full-vs-narrow context run on the #115 fresh 179 episodes;
- E2 real Purple claim adapter/model run on the #113 public 24 cases;
- E3 actual Mac/real-Qwythos kill/restart tests (repo-side Hermes-oriented unit-level recovery wiring is qualified separately in #194);
- E4 integrated interaction run;
- private receipt **producer authentication** (content/control binding is implemented; hostile-writer authentication is not);
- macOS integration;
- independent review.

No result from this development sidecar is a substitute for #119 M4.
