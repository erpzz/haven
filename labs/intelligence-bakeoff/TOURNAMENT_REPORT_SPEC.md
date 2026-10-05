# Tournament report specification

Report per configuration: exact runtime revision, model revision and quantization, suite revision, repetition count, per-trial pass rate, all-repetitions pass rate, transport failures, tool-selection failures, p50/p95 latency, and usage when available.

Safety boundary failures are reported separately and are non-compensable: any such failure blocks promotion regardless of aggregate score. Do not rank a configuration with a boundary failure above one without it merely because its average is higher.

Runtime comparisons must freeze the model and task suite. Model comparisons must freeze the runtime. Subscription-backed frontier lanes are reference configurations unless the model and runtime are both controlled.

Coding quality and long-context retrieval are separate strata with their own fixtures and tests; they are not folded into one scalar score.
