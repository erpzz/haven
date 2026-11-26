# Bounded claim verification gap analysis — 2026-11-25

Workstream: #126. Base main: `53387e74a0ad90786ac3ea16753c8ad99142e9df`.

The current Purple Copilot answer verifier is materially better than unconstrained prose: it rejects unknown citations, numbers absent from retrieved evidence, unknown principal names, links, and some number-to-principal misattribution. The next trust-boundary step is to distinguish **value grounding** from **claim grounding**.

## Exact source reviewed

PR #122 head `f701cd766e7068649c4722874a6ced1b2213fbdf`:
- Purple Copilot review gateway/verifier `apm/review.py` blob `d238c54345f6a4331dda3a560f6679cc9437a9bf`;
- review regression suite `tests/test_review.py` blob `938625dca9b8e17f7b30629bf0f0c7fccaef0a39`;
- isolated investigator boundary `boundary.mjs` blob `d2c72d9ca8ce5ff9072591cfa581c8577600bc33`;
- investigator triage `triage.mjs` blob `621571686eb519780cb78072913a20b8ecaff11a`;
- boundary tests `test-boundary.mjs` blob `9686e037b8d4903491888084ddc31ab6cc957f1c`.

PR #105's independent evidence re-derivation remains upstream of this concern. PR #128's admission prototype is intended to harden the structural evidence intake before claims are projected.

## What the prose verifier proves today

`Verifier.problems()` checks:

- every citation-shaped token exists somewhere in this turn's retrieved results;
- every numeric value exists somewhere in retrieved evidence;
- principal-shaped names exist in retrieved evidence;
- links are not accepted as Tier Zero evidence;
- when a sentence names a known principal, numeric values in that sentence must belong to evidence objects describing that principal.

Those controls catch real hallucination classes and should be retained for free-form fallback mode.

## Remaining claim-binding gaps

1. **Known citation ≠ citation for this sentence.** A citation is checked against the turn-wide set, not against a typed claim record for the sentence. A valid citation can therefore be attached to a different predicate/relation than the one that evidence established.

2. **Known entities ≠ known relation.** Principal names are checked globally. The verifier does not parse or authorize predicates such as `compromised`, `remediated`, `member of`, `controls`, or arbitrary causal statements. Two real entities plus a real citation do not establish a relation between them.

3. **Numbers can be reused under the wrong non-principal predicate.** The principal-specific binding helps when a sentence names a recognized principal, but a turn-wide number can still be reused in a different headline/scope/predicate that does not name a principal.

4. **Timestamps are deliberately stripped, not grounded.** The verifier removes timestamps before numeric checking. This permits useful human-readable observed times, but it also means the verifier does not prove that a timestamp in prose is one actually returned by the cited evidence.

5. **Not every object label is a principal token.** The principal regex is intentionally narrow. Targets/resources or other labels that do not match that form are not generically relation-bound by the answer verifier.

6. **Inference words are not states.** The investigator tests explicitly enforce `eligibility != activation`, `posture pass != remediation`, and `exposure != compromise`; the generic prose verifier cannot enforce those semantic distinctions merely by checking vocabulary/citations.

## Existing stronger pattern

The isolated investigator boundary already demonstrates the stronger approach:

- evidence is filtered to a host-owned scope;
- the model candidate is restricted to exact `ref/state` pairs;
- exact coverage can be required;
- model ordering/prose is discarded;
- the host re-renders trusted records;
- global limitations such as `membership_is_not_compromise` are added by the host.

The deterministic fallback in `review.py` is also safer than accepting unsupported model prose because it is assembled from returned tool fields.

## Prototype in this branch

`bounded_claims.py` generalizes the exact-selection pattern.

A host-owned claim bundle contains:

- immutable scope;
- claim id;
- citation;
- an arbitrary bounded JSON payload that can encode subject/predicate/object/value/time/units/etc.;
- global limitations.

The model candidate contains only:

`{bundle_sha256, claims:[claim-id,...]}`.

It cannot submit prose, predicates, timestamps, values, citations or scope. The host returns canonical copies of the exact selected claim records plus global limitations.

### Host relevance and coverage

`allowed_ids` is a host-owned question/scope boundary. The model cannot select another bundle claim merely because it saw it.

`required_ids` is a host-owned coverage boundary. Use it for:

- conflicting observations that must not be cherry-picked away;
- limitations or counterevidence represented as claims;
- claims that a specific report contract requires.

Global limitations are returned regardless of model selection.

## What this does NOT prove

- It does not determine whether a claim payload is correct. The adapter that creates the bundle must derive claims from admitted/verified evidence.
- It does not authenticate the evidence producer or the bundle. SHA-256 binds content but is not a signature/MAC.
- It does not decide which claims are relevant to the user's question. That is host policy.
- It does not sanitize sensitive claim payloads for disclosure.
- It does not support arbitrary novel synthesis. If a workflow genuinely requires reasoning beyond enumerable trusted claims, it needs a separate verified mechanism or must fall back to prose verification with its known limits.
- It does not make model-selected omission safe unless the host chooses correct `required_ids`.

## Proposed composition

For a strict structured report:

`verified evidence (#105/#128) → host claim adapter → bounded claim bundle → host allowed/required ids → model selects ids only → exact release → deterministic renderer`.

The bundle hash and claim policy should be bound into #130's immutable run manifest. If #131 is used to keep claim/tool context small, catalog/claim-bundle changes must invalidate the same turn before release.

For Purple Copilot, this can initially cover the high-risk structured portions (counts, state changes, edge relations, timestamps, limitations) while leaving conversational framing in the existing verifier/fallback path until evaluation supports a broader migration.
