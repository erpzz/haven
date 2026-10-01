# JEV-01 research — TypeSafe Jev as an advisory decision provider

Research date: **2026-10-01**. Status: **DOCUMENTATION_AND_SOURCE_INSPECTED; NO_JEV_EXECUTION**. This is original synthesis for Haven, not a vendor specification, benchmark result, model endorsement, or imported runnable skill. [SOURCES.json](SOURCES.json) records primary references and exact Git source pins. [START_HERE.md](START_HERE.md) is the requested refactor assignment; [ACCEPTANCE.md](ACCEPTANCE.md) separates offline integration from future live qualification.

## What Jev is, and what it is not

The relevant project is **TypeSafe AI's Jev**, introduced on 15 September 2026 as a System One model. It produces bounded judgments rather than generated prose. A useful mental model is a semantic function inside an ordinary application, not a replacement application framework. The official coding-agent guide explicitly distinguishes building software with Jev from using Jev as the generative model behind a coding agent. It cannot replace the Codex engineer, write Haven's answers, or serve as the existing vision-language model. [Introduction](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [coding agents](https://docs.typesafe.ai/introduction/coding-agents).

The reviewed model card identifies **jev-1.13.0**, accessed through a hosted service. Input is **text only**; neither images nor audio/video are accepted. Describing an image in text would evaluate the description, not inspect its pixels. Version aliases can move, so a qualification run should bind the explicit version and validate the returned model identity. The published price is **USD 0.042 per million input tokens; output tokens are free**. Listed capacity is 64k tokens per request, with a separate 32k state-plus-longest-question limit; advertised rate limits are dynamic. These are vendor limits, not Haven budgets. No supported local-weight or self-hosted installation route was established in this research. [Model card](https://docs.typesafe.ai/models).

## Programming model

Provide compact state plus narrow questions. Code assembles state and determines what any returned judgment is allowed to affect. Several independent questions over the same state can be grouped; they do not read one another's answers. A later dependent question needs new state/a separate request. Question IDs alone carry no meaning to the model. Describe the relevant state field in the instructions rather than relying on an ID such as `relevance_note_1`. This design guidance is grounded in the [pinned official skill](https://github.com/typesafe-ai/skills/blob/65a39f393687675ce170e6094757de20370365b9/skills/typesafe-ai/SKILL.md), read as reference only.

| Primitive | Meaning | Haven interpretation |
|---|---|---|
| Choice | Select one defined alternative; return its distribution and confidence. | A suggestion among known eligible handlers, including no match; never an execution grant. |
| Noul | Probability of a yes answer. It has no separate confidence field. | A narrow predicate such as whether an eligible passage supports the question. Not a security decision. |
| Score | Expected position on an ordered rubric; fractional results are meaningful. | Comparable relevance ratings for bounded candidate passages, not an invented percentage of truth. |

Choice criteria are a map; Score criteria are an ordered array. This matters when reading older examples. Confidence describes distribution concentration, not overall correctness or permission. A Noul around 0.5 represents uncertainty between yes and no, not medium intensity. Thresholds need task-specific evaluation, and hard rules must not be averaged away. [API](https://docs.typesafe.ai/api), [confidence](https://docs.typesafe.ai/confidence), [SDK changelog](https://docs.typesafe.ai/sdk/python/changelog).

## Wire contract and integration choice

The documented endpoint is `POST https://api.typesafe.ai/v1/systemone`, with a Bearer credential and JSON containing `model`, `state`, and `questions`. The response identifies its model and contains `answers` plus token `usage`. Expected HTTP errors include 401, 422, 429, and 529. A response may report output tokens even though those tokens are free. Refer to the live [API reference](https://docs.typesafe.ai/api) before implementing rather than copying an older cookbook payload.

The official Python SDK source at `f078f1e208a0d885154dc758344ae4fce77ac168` declares version **0.7.2**, MIT licensing, and Python >=3.10. Its dependencies include **httpx2**, Pydantic and Tenacity. SDK licensing does not license model weights or waive hosted-service terms. Haven's inspected lock instead contains **httpx 0.28.1** and Pydantic 2.13.5. Therefore the preferred first refactor is a small REST adapter using those existing locked dependencies, not a new SDK installation or framework migration. Installed availability still needs host verification. [SDK source](https://github.com/typesafe-ai/typesafe-sdk-python/blob/f078f1e208a0d885154dc758344ae4fce77ac168/pyproject.toml), [Haven lock](https://github.com/erpzz/haven/blob/d9eb68278e6a0c1f1cb84bab09d8e7b089c62cc2/labs/ip01/requirements.lock).

Two SDK hazards deserve explicit future tests. Its normal retry behavior can create more than one provider attempt per apparent application call; `RetryPolicy(max_retries=0)` disables internal retries. Its client documentation says request/response bodies are not redacted merely because authorization headers are. An SDK operation timeout also does not replace Haven's end-to-end deadline. Avoid unconstrained base-URL overrides and last-write-wins `extra_body` overrides of sealed fields. These are integration requirements, not claims that the SDK is malicious. [Retry controls](https://docs.typesafe.ai/sdk/python/api/retries), [async client](https://docs.typesafe.ai/sdk/python/api/clients/async).

## Reliability, performance, and privacy

The official jaggedness guide describes weaknesses with arithmetic, counts, dates, indirect phrasing, adversarial or irrelevant state, and relationships between separately asked questions. Leave exact comparisons and authority logic in code. Schema-conforming output can still be semantically wrong. An injection-detection score is not a substitute for keeping instructions/data separate or restricting capabilities. [Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

The vendor reports large speed/cost advantages in its own workflows. Those are not Haven results, nor an independent guarantee. Its evaluation site describes model-generated reference judgments and vendor-selected tasks. Measure complete application latency, request volume, relevance, errors and user-visible friction on the actual candidate. Do not label hypothetical savings as observed. The existing Haven source-selection baseline is local lexical code, so adding hosted ranking introduces cost and network dependency; it does not automatically replace an expensive existing LLM router. [Vendor introduction](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [evaluation methodology](https://evals.typesafe.ai/).

The model card states customer requests/responses are not used for training. That is **not the same as default zero retention**. The legal landing page offers ZDR to enterprise customers, while the privacy policy describes retained/service-provider processing. Ordinary Haven local-read authority is not authorization to disclose a note or question to TypeSafe. No credentials, household/employer data, personal recordings, protected evaluator assets, or private account content may be used in this phase. Do not infer that a free balance or configured key grants provider spending. [Legal](https://docs.typesafe.ai/legal), [privacy policy](https://typesafe.ai/legal/privacy-policy), [customer agreement](https://typesafe.ai/legal/mca). Contract suitability for future real-user data remains an operator decision, not an approval in this document.

## Exact Haven fit

At inspected commit `d9eb68278e6a0c1f1cb84bab09d8e7b089c62cc2`, `labs/ip01/haven/authority.py::build_context` selects explicit sources or up to eight notes by lexical overlap, appends the selected image, resolves influencing closure, and seals a context. `ApplicationService` separately manages admission and fresh egress checks for the **local-only** model gate. These are actual source observations, not runtime tests performed here. [Authority source](https://github.com/erpzz/haven/blob/d9eb68278e6a0c1f1cb84bab09d8e7b089c62cc2/labs/ip01/haven/authority.py), [application source](https://github.com/erpzz/haven/blob/d9eb68278e6a0c1f1cb84bab09d8e7b089c62cc2/labs/ip01/haven/app.py).

The first use should be **optional source relevance judgments before answer-context sealing**. User-selected sources remain explicit choices; the semantic provider must not silently replace them. Keep deterministic candidate retrieval and fallback. An additional route suggestion is a later optional consumer of the same interface, not a requirement to implement a new planner now. Citation checks, extraction of pre-parsed values, and worker selection remain possible future uses with their own evidence and permissions. Official [RAG passage classification](https://docs.typesafe.ai/cookbooks/classifying_rag_passages) and [intent routing](https://docs.typesafe.ai/patterns/intent-routing) illustrate related patterns; do not import their model versions, extra providers, demo thresholds or outputs as Haven qualification.

### Proposed boundary, not an accepted authority amendment

```text
Synthetic request + explicit source/route selection
                 |
 Local eligibility and relevance candidate snapshot
                 |
 DecisionProvider interface
   + deterministic selector (default; local)
   + Jev adapter (implemented; live gate closed)
   + evaluator-only fake transport (labelled test double)
                 |
 Validate decision + recheck current authority and revisions
                 |
 Seal complete influencing lineage -> existing answer pipeline
                 |
 Fresh release/consume checks -> correctly labelled UI
```

Never await a hosted call while holding the existing synchronous SQLite authority transaction. Snapshot locally, leave the transaction, obtain a bounded advisory result, then revalidate before applying it. A hosted ranker reads all supplied passages: even a rejected passage may influence selection. Its decision and complete input ancestry must remain in downstream lineage, not just the sources finally cited. Early eligibility filtering can prevent B2-style irrelevant exhausted input; deleting an influencing ancestor afterward cannot. H00 and the independent authority reviewer must validate this mapping before semantic selection affects a releasable result.

A future remote request requires a distinct provider-egress gate and attempt ledger. The old `SYNTHETIC_LOCAL_TEXT_IMAGE_ONLY` gate must not be repurposed by changing an endpoint. Closing an HTTP request does not establish that TypeSafe stopped computation or billing. Record uncertainty; never manufacture a local-process STOP_CONFIRMED for a hosted service.

## Recommendation

Proceed with the requested **offline-tested Jev-ready refactor** as a bounded IP-02 addendum, preserving the local generative model and all runtime fixes. Produce working adapter code and a real application seam tested with explicitly synthetic transport, not just another proposal. Keep actual hosted use disabled until separately supplied provider authority, credentials, data rules and numerical budget exist. Promotion of Jev above the deterministic baseline requires real independent measurements later. Research and publication here establish neither those measurements nor a running agent.
