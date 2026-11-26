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

Global limitations are always returned independent of model selection.

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
5. Host `required_ids` is the anti-cherry-picking mechanism for required conflicts/counterevidence.
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
- It does not make optional claims complete; use `required_ids` when omission matters.
- It does not support arbitrary novel synthesis beyond the enumerated host claims.
- The model must be shown enough claim content to choose ids; claim-context minimization is a separate #131-style problem.

## Not executed / not qualified

- exact committed-head clean-checkout suite;
- adapter from actual Purple Copilot results into claim bundles;
- demonstration against real-model prose-verifier bypass cases;
- Qwythos structured-claim selection accuracy;
- full deterministic user-facing renderer;
- signed/MAC-authenticated claim bundles;
- sensitive-claim disclosure policy;
- checkpoint/run-manifest integration;
- macOS integration;
- independent review.
