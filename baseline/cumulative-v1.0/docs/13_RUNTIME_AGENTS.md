# Real useful autonomous agents, separate from development threads

The user wants to explore autonomous agents with real-world function. That is retained as an explicit design objective. It does not mean making every component an LLM or running an unbounded swarm. Development threads help build the system; runtime agents perform ongoing authorized work once implemented and qualified.

## Proposed runtime roles

| Role | Useful autonomous work | Inputs and outputs | Boundary |
|---|---|---|---|
| RA01 Concierge | Completes bounded daily investigations, drafts and reviewed tasks | Scoped context → answer/draft/proposal/receipt | No device authority through everyday tools |
| RA02 Research scout | Reviews approved public sources and proposes useful experiments | Dated sources → evidence cards/priority proposals | No automatic installs, accounts, spending or raw external-code execution |
| RA03 Readiness steward | Checks due inspections, available equipment and stale data | Device observations → qualified readiness state/notification | Cannot certify hardware from heartbeat alone |
| RA04 Perception investigator | Requests permitted observations to resolve a question | Evidence/map → uncertainty and next-view proposal | Cannot invent unseen geometry or command motion directly |
| RA05 Engineering investigator | Proposes designs, experiments and bounded iterations | Approved goal + measurements → artifacts/test proposals | Cannot approve its own fabrication or rewrite success metric |
| RA06 Experiment analyst | Produces reproducible numerical analysis and comparisons | Raw test IDs → analysis artifact + limitations | Cannot fabricate data or silently remove failures |
| RA07 Logistics coordinator | Schedules eligible robot/drone/relay tasks | Qualified resources → bounded allocation proposals | Physical executor and policy own action limits |
| RA08 Communication assistant | Prepares authorized incident summaries and delivery status | Scoped facts → draft/queued message with receipt | Cannot label local storage as responder dispatch |

Independent safety/authorization services and human reviewers are **not** simply additional reasoning agents. Their deterministic rules and external evidence enforce limits even when a model fails.

## Agent job contract

A persistent job has a task ID, authenticated sponsor, domain, purpose, input evidence revisions, permission snapshot/reference, allowed capabilities, maximum tool calls, context/media limits, wall/monotonic deadlines, cost/energy budget, resource lease, cancellation channel, progress checkpoint and output schema. Its result includes actual receipts and unknowns.

States: CREATED, ELIGIBLE, RUNNING, WAITING_FOR_INPUT, WAITING_FOR_APPROVAL, SUSPENDED, COMPLETED, FAILED, CANCELLED, OUTCOME_UNKNOWN. A reboot invalidates volatile leases and uncertain physical permits. Analysis may safely recompute from immutable inputs; physical actions require reconciliation. A due daily reminder follows its separate durable scheduler policy.

## Autonomy levels to qualify

A0 read-only replay and analysis. A1 on-demand proposals with no external effects. A2 permitted low-risk digital actions under explicit or narrow standing grants. A3 supervised physical actions on qualified equipment. A4 repeated bounded physical tasks under a reviewed campaign policy with independent stops. A5 broader adaptive campaigns only after systematic evidence and domain review.

Levels apply per capability/configuration, not to the assistant as a whole. Passing a reminder test does not promote aircraft autonomy. Passing CAD generation does not authorize unattended heater operation. The mature standing-incapacitation path is a separate incident policy, not a global highest-level badge.

## Agent communication

Use typed handbacks and references to canonical state. A worker cannot approve another worker by saying “I trust it.” Cross-agent messages are untrusted until validated and scoped. Share the minimum context; no automatic full-memory broadcast between private users or across daily/medical/physical domains.

The coordinator handles work ownership and resource fairness. Avoid two agents optimizing the same file or controlling the same device. Use an exclusive qualified execution owner per physical resource. A lease expiration triggers the defined recovery policy, not a second owner guessing the previous action failed.

## Self-improvement without self-authorizing

Agents may suggest a new prompt, skill, CAD template, perception model or tool adapter. Save it as a candidate artifact with provenance, tests, license and rollback. It enters a review/qualification pipeline before runtime use. Generated tests cannot be the only evidence validating the generator's own behavior. Keep a protected regression suite and independent fixtures.

An agent may learn which observations are useful through measured experiments; it may not rewrite consent boundaries or erase negative results to improve its score. Evaluate whether learned selection improves held-out performance and cost against a fixed strategy.

## Event-driven operation

Persistent does not mean continuous thought. Trigger jobs from explicit requests, reviewed schedules, new evidence or defined readiness events. Most bookkeeping runs without inference. Bound polling and prevent recursive “agent A asks B to ask A” loops. A scheduler record, not conversational enthusiasm, establishes that background work exists.

Priority policy should preserve human communication and reliable receipts before expensive research. Under resource pressure, pause low-priority design searches and retain checkpoints. Do not delay independent alarms. Costs include idle host power and physical experiments, not only tokens.

## First experiments that prove real usefulness

A research agent that produces source-correct, versioned findings; a readiness agent that detects a stale fixture without issuing false alarms; an engineering agent that improves a measured mount using human-mediated fabrication; an investigator that selects fewer observations for equal localization performance; and a task agent that schedules/remembers accurately across restarts.

Each experiment has a baseline, an authorized scope, raw evidence and a stop rule. “The agent ran all night” is not an outcome. “It improved this measured error under these constraints, and failed here” is.
