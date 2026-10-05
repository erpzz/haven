# Runtime bakeoff fairness audit

PR #28 is a useful runnable prototype, but its current eight cases are a smoke suite rather than the broader R02 qualification program.

Key corrections before drawing a winner: freeze the same model for runtime comparison; freeze the same runtime for model comparison; record exact runtime/model/suite revisions; report every repetition instead of best-of-many; report task reliability across all repetitions; keep boundary failures outside aggregate averages; capture effective prompt/tool context and retry behavior; add controlled malformed-call and repair cases; add correction, missing-evidence, conflicting-evidence, multi-step, distractor-context, and bounded coding strata; and maintain a protected holdout that is not used for prompt tuning.

The current note-tool gateway correctly overwrites the model-provided identity value before dispatch. A production-shaped follow-up should remove identity from model-controlled tool arguments entirely and bind it only in the trusted gateway. The scorer should also inspect model-visible evidence traces for forbidden material rather than checking only the final prose.

Hermes may replace measured orchestration conveniences such as provider plumbing, tool-loop mechanics, and selected context/scheduling features. Haven must continue to own identity binding, eligibility and egress policy, approval gates, cancellation fencing, evidence-ledger semantics, budget policy, and all physical authority boundaries.

Subscription-backed frontier configurations should be labeled reference/worker lanes unless both model and runtime are controlled. They are useful ceilings, but they cannot establish a Hermes-versus-thin runtime result.

Recommendation: harden the suite/reporting first, then run thin versus Hermes with one identical qualified local model. Only after that runtime control should the local-model tournament select a default.
