# Haven first-party model selection and routing transparency contract

Status: **engineering contract; partially implemented**. This document does not assert deployment or live browser acceptance.

## Product boundary

Haven owns the user experience, model registry, experiment lifecycle, routing
policy and audit trail. Open WebUI is an optional compatibility/service layer,
not the Haven frontend. Reuse Haven's Model Lab, model scout, approved-node
scheduler, engineer executor, evaluator and existing inference gateway rather
than building competing control planes.

A T3-inspired picker means **searchability, favorites, meaningful model
information and per-model configuration**, not a reskinned Open WebUI model
dropdown.

## Identity and operational state

Each row must identify its entity type. A *route selector* is not a model:

| Entity | Example | Must never be confused with |
|---|---|---|
| Artifact | Qwen GGUF revision + SHA-256 + quantization | `haven-slink` |
| Installation | artifact stored on Slink at reviewed path | inference worker |
| Runtime | loaded backend and verified capabilities | saved catalog entry |
| Node | Slink CPU/GPU or enrolled Mac | model |
| Provider | local worker or approved hosted service | artifact |
| Routing alias | `haven-slink`, `haven-auto` | real weight identity |
| Experiment | preregistered benchmark / adapter / LoRA run | production deployment |

Use distinct statuses: DISCOVERED, COMPATIBILITY_UNREVIEWED, ADMITTED_TO_CATALOG,
INSTALLED, LOADING, READY, BUSY, OFFLINE, BLOCKED_BY_JOB, and UNSUPPORTED.
Never infer READY from a static catalog card.

## Per-request routing trace

The gateway's initial `haven.routing` object reports:

- `requested.selector` and requested provider id;
- Lab job's `resolved.provider_id`, worker, reported model, SHA-256 if present,
  digest provenance, compute and egress;
- `execution.job_id`, completion state, finish reason, tools-dropped flag;
- recorded `selection_reason`;
- `fallback: UNDETERMINED` and `identity_attestation: NOT_VERIFIED` until
  backend event provenance makes more precise claims possible.

This is *not* proof of physical model weights. Do not equate the backend's
reported display model with an independently attested artifact. The model
picker must expose these uncertainties rather than hide them.

Next version should capture admission candidates and rejection reasons,
explicitly tracked fallback events, queue/warm/cold-load timings, scheduler
policy version, model-affinity pinning, and trusted artifact digest matching.
History must be tied to authenticated per-user job ownership before exposing
retrieval endpoints. No raw prompts, chat history or API keys in receipts.

## Router modes

1. **Manual:** pin exact available model artifact + node + runtime profile.
   Do not silently substitute. If unavailable, return actionable conflict.
2. **Auto (local):** consider only authorized enrolled private nodes and
   already-eligible models; rank by measured, comparable evidence plus
   latency/resources; explain selection and rejection reasons.
3. **Compare:** send the same immutable evaluation case to selected models
   with pinned seed/profiles. Preserve hardware, context, tools and receipts.
4. **Hosted:** separate explicit choice and per-conversation egress consent;
   local-only MUST never silently become hosted.

All modes must use the same registry, scheduler and receipt schema.

## Experience acceptance

From the native Haven interface, the operator should:

1. Search/filter/favorite installed and discoverable models and identify
   which cards are real artifacts vs provider destinations.
2. Inspect quantization, revision/digest, required disk/RAM/VRAM, model family,
   tested capabilities, historical speed and held-out evaluation provenance.
3. Choose a compatible model and compute lane; see exact cold-load cost,
   resource contention and active GPU owner before confirming a switch.
4. Send a real browser request with requested/resolved/executed identity and
   expanded trace; independently inspect a safe per-job receipt.
5. Search Hugging Face metadata, explicitly review then download/verify/import
   an allowed artifact, and start it without harming any active job.
6. Run side-by-side real-model comparisons with archived prompts/results in
   the owner's private experiment workspace and sanitized public receipts.
7. Inspect training jobs, versioned adapters, independent held-out evaluation,
   promotions and rollbacks without conflating them with serving deployment.

## Implementation status at this commit

- Available in gateway branch: signed identity; revocation; alias-vs-provider
  labeling in `/v1/models`; requested/resolved route facts in nonstream JSON,
  streaming terminal SSE and private content-free receipts.
- Still missing: first-party native model picker, accurate artifact/install
  inventory API, search/favorites UI, automatic quality-aware router,
  routing decision candidate trace and proven fallback events, experiment UI.
- Current Open WebUI cannot be relied upon to display Haven-specific response
  extensions; this is an API foundation only.
- No live Slink deployment, GPU experiment interruption, or real-browser
  verification was performed by this code change.

Merge/deploy gates: green gateway tests, adversarial role tests, Slink-specific
runtime tests with signed frontend credentials, GPU-owner preservation, manual
model pinning, per-chat egress consent, and browser acceptance on the target
deployment revision.