# Intelligence, models, agent frameworks and economics

**Design proposal plus dated primary-source findings.** The existing M4 local advisory baseline is unchanged. This chapter concerns the broader everyday/engineering assistant. Model selection is a measured engineering decision, not a personality choice or a permission level.

## Recommended starting arrangement

Own a thin Haven coordinator, domain records, permission gates and evidence rendering. Make inference replaceable through a provider interface. Start with one queued generation at a time on the existing PC and bounded context; measure whether a second concurrent user needs scheduling, a separate worker or different hardware. Preserve CPU/memory headroom for receipts and control supervision.

Compare that arrangement with Hermes as a separate synthetic benchmark, not a replacement deployed into the active M0 tree. The source register distinguishes Hermes agent software [R22–R23], Meta Muse as a hosted product [R24], model weights [R25–R26], model serving and tool protocols. A generous framework tool catalog is not an argument for enabling all of it.

Candidate new local evaluations: Qwen3.5 4B and Gemma3 4B for bounded everyday tasks, selected pictures and structured extraction. Preserve Qwen2.5-VL 3B for planned M4. Exact digest, quantization, runtime and context are qualification inputs. Do not extrapolate downloadable file size to total GPU memory. Current API pricing from earlier artifacts is historical until refreshed; this package deliberately contains no approved provider tariff or forecast bill.

## Routing before reasoning

1. Ordinary code handles accepted receipts, timers, arithmetic, data normalization, freshness, authorization, constraints and established recovery.
2. A compact qualified local model handles the tasks it passes, with only relevant evidence.
3. A low-cost hosted model can handle privacy-eligible work that local inference fails to complete adequately.
4. Stronger reasoning is available for bounded difficult synthesis or experiment design after scope/spend approval.
5. Independent human/domain authority resolves permissions, medical judgment, hazard qualification and policy changes. It is not simply the most expensive rung of an inference ladder.

Choose privacy-eligible routes first. Do not upload Kennedy's measurements because local inference is slow or a cloud tier is free. Output-schema success is necessary for some contracts but not a truthfulness guarantee [R27]. Model self-reported confidence is not a calibrated probability or an authorization token.

## Context and memory economics

A selected context packet contains task intent, principal/scope, a limited current-state snapshot, relevant evidence IDs and excerpts, allowed response/action types, and uncertainty. It does not contain the entire household history. Use scoped IDs/full-text/tag retrieval before proposing a vector database. Fetching fewer relevant records helps both privacy and cost.

Hermes has framework-specific context requirements [R23]; evaluate its full prompt/skill/tool footprint rather than applying thin-coordinator context assumptions to it. Record automatic memory/skill mutations and whether they can be reviewed, revoked or disabled. A generated skill is an untrusted code artifact that cannot expand authority until reviewed and promoted.

## Proposed budget controls, not approved spending

Before a paid call, reserve a conservative maximum cost from a per-task and per-user/household ledger. Bound input, output/reasoning, media, tool calls, retries and wall time. Reconcile actual usage after completion and release reservations. Provider billing dashboards can lag; application caps still need margin and cannot guarantee a vendor invoice limit by themselves.

Use `policies/model_budget.example.json` as an inert planning example with cloud disabled and rates unset. The first hosted benchmark requires explicit provider/data approval. On budget exhaustion, continue deterministic receipts and already authorized reminders; return a clear degraded explanation instead of looping or bypassing privacy.

Model-work example formula:

`monthly inference = sum(calls_i * input_tokens_i / 1e6 * rate_input_i + calls_i * billable_output_tokens_i / 1e6 * rate_output_i + media_i + tool_i + cache_i)`.

Add storage, subscriptions, network backhaul, electricity, depreciation, maintenance, failed experiments and operator time separately. Count a five-step investigation as five or more inference calls, not one user request. Local marginal electricity is `extra_watts / 1000 * hours * measured_price_per_kWh`; compare against the PC's counterfactual sleeping state, not assume free always-on compute.

## Benchmark design

Use synthetic two-user fixtures. Compare identical tasks, result schemas and maximum effort—not only default vendor settings. Measure grounded success, unsupported claim rate, privacy errors, correct clarification, proposed tool arguments, appropriate abstention, median/tail latency, cold start, memory, energy when measurable, retries and cost per accepted task. Separate speech, text, image and reasoning workloads.

Test ambiguous recipients, stale measurements, image prompt injection, wrong evidence IDs, long distracting context, concurrent user requests, revoked sharing mid-generation, malformed model output, timeout, budget exhaustion and model restart. A stronger model must pass the same privacy and action boundaries. Do not reward a model for confidently completing an unauthorized task.

## Voice and glasses

Evaluate local speech recognition and synthesis separately using candidate projects such as whisper.cpp and Kokoro [R37–R38]. This is a proposed economical pipeline, not a promise of native realtime experience. Model/voice licenses and actual pronunciation, accents, noise, barge-in and latency need evaluation.

Prefer explicit pictures/short clips and local quality selection to continuous cloud video. Do not invoke an LLM on every Watch sample. A user-facing feeling of continuity should come from durable state and responsive UI, not nonstop token generation.

## Framework decision gate

H02 returns one recommendation: thin coordinator, a narrowly configured framework integration, or a clearly bounded hybrid. Include portability, provider independence, schedules, household separation, skill trust, attack surface, latency/context overhead and maintenance cost. H04 reviews permissions and H06 reviews measurements. No framework switch is implicitly approved by a favorable research note.
