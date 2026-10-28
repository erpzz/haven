# R02 — One-page integration summary

**Status:** DESIGN_PROPOSAL → H00 review. Research checked 27 September 2026 Eastern. No implementation, model/framework installation, paid inference, accounts, deployment or additional agents started.

**Baseline:** inspected `HAVEN_ASTRA_Cumulative_Starter_v1.0.zip` (SHA-256 `55f693f64c56a9d8f13a6cd5725ab4c427af6ade2e127fe8e71829eca1f1d412`). The later Tonight wrapper preserves its 146 entries byte-for-byte. Actual M0/NIGHT-01 application results were not inspected. M0 ownership, M4 `qwen2.5vl:3b`, M0–M6 gates and every cumulative branch remain unchanged.

**Decision:** prefer a thin Haven coordinator, with bounded jobs and replaceable inference. Haven owns identities, consent, context/memory revisions, budgets, evidence and outcomes. Models propose; authenticated domain services authorize and execute. Timers, readiness rules, receipts and physical recovery must not depend on an LLM.

**Routing:** deterministic code → task-qualified compact local → privacy-eligible cheap hosted → bounded stronger reasoning. Skip unqualified tiers; missing evidence/authority requires refresh, clarification or unavailable—not a stronger model. First local candidates: Qwen3.5-4B and Gemma 3 4B. Later cheap hosted candidate: `gpt-6-luna`; stronger cost candidate: `gpt-6-sol`; later portability comparator: `gemini-3.5-flash-lite`. None is locally qualified or authorized for paid use here.

**Frameworks:** retain Hermes as a bounded challenger and OpenClaw as the single alternative. Hermes' reviewed tool-use guide requires ≥64k configured context; measure full overhead without pretending that equals prompt tokens. Disable automatic learning/review and broad tools in a future trial. OpenClaw documents one trusted boundary per gateway, not adversarial multi-user isolation. Sources and limitations: R02-S01–S05.

**Memory/privacy:** separate user A, user B and explicitly shared data. Filter before retrieval/ranking; retain evidence revisions, capture/receive times, uncertainty and lineage. Revoke across queued contexts, caches, summaries, embeddings and publication. Do not claim application scopes protect plaintext from the host administrator. Cloud fallback never widens consent.

**Workers/resources:** readiness is usually no-model; research, perception, engineering and logistics are finite coordinator jobs. Separate processes only for privilege, native tooling, faults or resource isolation. Start with one accelerator lane, fair user queues, bounded calls, durable cancellation/fencing and atomic budget reservations. Unknown writes reconcile; they do not blindly retry.

**Contract issue:** frozen v1 schemas are synthetic/mock-only and cannot express the richer prose lifecycle. CR-R02-01–05 propose operational job/context/evidence, memory/publication, inference/budget/cancel and broker mappings. No shared schema changed. H04 owns authority; H03 owns scheduling/receipts; H05/H07/H08/H09 retain physical/media/engineering contracts; H06 independently accepts results.

**Next gate:** reconcile actual N1/N2 outputs, then approve one extension: a 40-case no-model private/current/cancelable notebook experiment, reusing N1. Later qualify models and optionally frameworks by cost per fulfilled task, privacy, grounding, latency and all failures/retries. A later five-candidate sensor-fixture campaign requires protected metrics and separate physical permission. No purchases now. Full architecture, exact interfaces, experiments, source register and package boundaries accompany this summary.
