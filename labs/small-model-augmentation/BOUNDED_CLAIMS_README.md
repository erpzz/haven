# Bounded claim release prototype

Workstream: #126. Base `53387e74a0ad90786ac3ea16753c8ad99142e9df`. Author: Astra (ChatGPT), 2026-11-25. Review-only; no self-merge.

Implementation: `bounded_claims.py`. Gap/source audit: `BOUNDED_CLAIMS_GAP_ANALYSIS.md`.

## Why

A prose verifier can prove that a citation, number or principal came from retrieved evidence without proving every predicate/relation/time statement in the same sentence.

This prototype uses a stronger contract for workflows that can enumerate trusted claims: **the model does not author the claim payload at all**.

## Bundle

The host owns a `haven.claim-bundle.v1` object:

- `scope`: exact run/tenant/dataset/snapshot/as-of context chosen by the adapter;
- `claims[]`: `{id, citation, payload}`;
- `global_limitations[]`.

A payload is bounded JSON. It may encode whatever exact fields the adapter needs: subject, predicate, object, value, units, state, observation time, etc.

The bundle SHA-256 is order-independent across claim rows but content-bound.

## Candidate

The model can submit only:

`{"bundle_sha256":"…","claims":["claim-id",...]}`

No prose, value, timestamp, citation, predicate, scope or free-form trace is accepted.

The host then returns the exact selected records from the bundle in canonical id order. Candidate ordering is not trusted presentation policy.

## Host controls

- `allowed_ids`: which claims this question/scope may use;
- `required_ids`: claims the model is not allowed to omit;
- `max_claims`;
- optional expected bundle hash.

Use `required_ids` for conflicting evidence/counterevidence or other coverage that must not be cherry-picked away.

For the Purple Tier Zero adapter, `required_ids` is now supplied by deterministic host policy rather than by the model or an ad-hoc caller:

- overview: principals-with-direct-control, control-edge, and reachability totals are mandatory;
- principal: held-control, gain-control, and all reachable-from family totals are mandatory;
- changes: new, changed, and **missing** totals are mandatory even when zero;
- search: match, holder, and Tier Zero target totals are mandatory;
- detailed edges/holder rows remain optional bounded detail.

The Purple policy binds bundle hash, tool, complete allowed IDs, required IDs, and release budget into `haven.purple-claim-coverage.v1`. The result then emits `haven.purple-claim-coverage-receipt.v1`, binding the policy hash, exact candidate bytes, generic release output hash, required IDs and selected IDs. This removes the “safe payload but cherry-picked headline” failure mode without forcing every detail claim into every answer.

Global limitations are always returned independent of model selection.

### Disclosure surfaces

Purple now has a fixed hash-bound disclosure policy.

The **selector model** receives only:
- bundle/policy hashes;
- tool name and release budget;
- opaque claim ID;
- coarse claim kind;
- mandatory/optional bit.

It does **not** receive claim payload values, citations, limitations, platform/snapshot provenance, raw host results, or provenance paths through this selector view.

The **audit/log surface** is the hash/count coverage receipt: status/error codes, bundle/policy/candidate/release/receipt hashes, and required/selected counts/IDs. Raw candidate text and claim payload/provenance are not logged by this receipt.

The **user surface** is the deterministic host renderer: host-rendered claim text, host-rendered citations and global limitations. Raw model candidate text, selector view, coverage policy, raw bundle and raw host result are not user output.

CI injects payload/citation/limitation and malformed-candidate sentinels and proves they cannot appear in selector or coverage/error receipts. This is a disclosure contract for this pipeline, not a claim that the underlying host/source data itself is non-sensitive.

For checkpoint/resume, the Purple adapter also emits `haven.purple-claim-checkpoint-binding.v1`. Its binding SHA covers the exact bundle SHA, coverage-policy SHA, deterministic renderer SHA and #130 run-manifest SHA. #130 remains the recovery authority; the composed runner must use this binding as part of its immutable checkpoint identity. A changed bundle, coverage policy, renderer or underlying run manifest therefore cannot be resumed under the old claim execution identity.

## Author test evidence

Author semantic reproduction before the final scope-hardening refinement: **26/26 PASS**. Final review then added a regression requiring a non-empty host scope; exact final-head clean-checkout execution is intentionally left to Codex/local validation rather than claimed here.

Coverage includes:

- exact payload release;
- canonical host order rather than model order;
- no prose/narrative channel;
- no model-authored predicate/value;
- no cross-claim field splicing;
- disallowed/unknown claims;
- required claim authorization and coverage;
- required conflicting/limiting claim;
- forced global limitations;
- exact host scope projection;
- empty/unbound host scope rejection;
- stale candidate after scope change;
- bundle hash binding predicate and timestamp;
- claim-order-independent bundle hash;
- expected-bundle change detection;
- duplicate bundle/candidate claim rejection;
- duplicate JSON-key rejection;
- claim budget;
- returned-copy immutability;
- empty selection when host requires nothing;
- non-finite/malformed payload/candidate rejection.

A malformed-input fuzz probe exercised **30,000** randomized bundle/candidate/config shapes with **0 unhandled exceptions** in the author semantic reproduction.

## Second-pass decisions

1. The model candidate is id-only; no partial structured claim fields are accepted.
2. Bundle scope and exact payload are hash-bound.
3. Model ordering is discarded.
4. Global limitations cannot be omitted.
5. Host `required_ids` is the anti-cherry-picking mechanism; Purple now derives it deterministically for mandatory summary/change totals and hash-binds the coverage policy and release.
6. Claim derivation is explicitly outside this boundary: the adapter must consume verified evidence.
7. The hash is content integrity, not producer authentication.
8. Final review corrected an over-permissive scope check: an empty `{}` scope is now invalid.

## Intended composition

`evidence admission/re-derivation (#105/#128) → host claim adapter → bounded bundle → host allowed/required ids → model id selection → exact release → deterministic renderer`

For Purple Copilot, start with structured high-risk portions such as:

- edge subject/relation/target;
- counts with their exact scope;
- state-change classification;
- observed timestamp;
- limitations/counterevidence.

The existing prose verifier/fallback can remain for conversational framing until controlled evaluation shows how much should migrate.

## Security limits

- A bad host claim adapter can create a bad claim. This module will preserve it exactly.
- SHA-256 does not authenticate a hostile bundle author.
- It does not decide relevance; `allowed_ids` is host policy.
- It does not sanitize sensitive payloads for disclosure.
- Optional detail claims remain intentionally incomplete. Purple's deterministic coverage policy makes summary/change totals mandatory, but it does not claim exhaustive disclosure of every detail edge unless a future host policy requires that.
- It does not support arbitrary novel synthesis beyond the enumerated host claims.
- The model must be shown enough claim content to choose ids; claim-context minimization is a separate #131-style problem.

## Not executed / not qualified

- exact committed-head clean-checkout suite;
- independent review of the actual Purple Copilot coverage-policy integration;
- target-Mac proof that any checkpointed production runner uses the claim checkpoint binding as part of its immutable #130 identity;
- demonstration against real-model prose-verifier bypass cases;
- Qwythos structured-claim selection accuracy;
- full deterministic user-facing renderer;
- signed/MAC-authenticated claim bundles;
- sensitive-claim disclosure policy;
- checkpoint/run-manifest integration;
- macOS integration;
- independent review.


## Activation, rollback, and authenticity decision

Bounded claims are **not a runtime activation in this candidate**. The current Purple `apm/` package has no non-test consumer of `bounded_claim_adapter`; CI asserts that remains true.

The merge/activation split is intentional:

- merging the adapter makes the reviewed host-owned boundary available;
- a later, separate activation PR must explicitly wire it into the runtime;
- until that activation passes its gates, the legacy structured-JSON/runtime output path remains the only active path and therefore the rollback path;
- no merge of this adapter may silently change production/user output semantics.

Minimum activation criteria:
1. #127/E0 local admission and actual first-request evidence is green;
2. controlled E2 mutation evaluation shows zero released-claim mutation failures and no unacceptable semantic regression;
3. the GitGuardian incidents on the Purple candidate are dispositioned;
4. the activation PR has independent review and explicit rollback tests preserving the legacy structured-JSON path.

If activation later fails those criteria or produces unacceptable behavior, disable/remove the bounded-claim runtime consumer and return to the preserved legacy path; the adapter/data structures need not be deleted.

### Authenticity threat-model decision

Current development qualification treats the host-owned producer/process boundary as trusted against **accidental drift and model-originated manipulation**. SHA-256 receipts are content/provenance bindings under that model.

They are **not authentication against a hostile same-user/local writer**. If the deployment threat model includes a process that can forge host-owned files/receipts, activation must add a stronger authenticity layer (for example a keyed MAC/signature backed by a secret unavailable to that writer, or an immutable/external content-addressed provenance service). Hash-only evidence must not be re-labeled as authenticated evidence.

This is an explicit trust decision, not an implicit claim that hashes solve hostile-writer authenticity.
