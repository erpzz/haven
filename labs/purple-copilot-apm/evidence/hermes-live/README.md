# Real-model review answers through Hermes, 2026-11-22 UTC

Six analyst questions (`tests/hermes_questions.py`) were asked through Hermes Agent v2026.9.24 with the Purple Copilot plugin. The model was Qwen3.5-4B Q4_K_M (sha256 `00fe7986…69ef11a4`), served by llama.cpp `7fe450e` on a 2 vCPU, 7 GB CPU container with a 64k context and an 8-bit KV cache. The snapshot was the sample-lab history (AD run 6, Entra run 7).

- **Baseline.** Commit `836c2b5`: the first plugin version, with raw counts and edge names. The human runbook was in `HERMES.md`, which Hermes injected into the prompt.
- **Improved.** Deterministic `meaning` and `reach` sentences per edge, `reachable_from` replacing ambiguous counts, a 1 KB review brief as `HERMES.md`, a timestamp exemption and a wider citation pattern.

Each JSONL row holds:
- the question;
- the model's original answer (`model_answer`);
- what Hermes showed (`shown`);
- the reads and blocked calls;
- the verifier's findings at the time;
- wall time.

**These are six questions per arm, so the results are descriptive, not a benchmark.** The judgements below are the author's (Claude's) against the tool evidence. They are recorded so an independent reviewer can audit them.

| Question | Baseline: what the user saw | Improved: what the user saw | Final verifier on the model's answer (baseline / improved) |
| --- | --- | --- | --- |
| AD takeover, fix first | Model answer, **wrong**: ADCS edges described as "session control", WriteAccountRestrictions as "full control", an unsupported RODC claim | Fallback. The model invented a count of 52 and attached the tenant-wide 53 to individual principals | pass / replace |
| Can domain users reach Tier Zero | Model answer, **wrong**: ESC1/3/6 described as "administrative delegation"; invented citations | Model answer, mostly right. ESC3/ESC6b meanings correct; one count misattributed (33 for T1_FABIAN, evidence 32) | replace / replace |
| What DF-WIN10-DEV01 gives an attacker | Fallback. The model reversed the session direction and invented citations | Fallback. Direction correct, but it called the computer Tier Zero and gave no citations | replace / replace |
| Worst Entra app or service principal | Fallback. One wrong derived count (43) in an otherwise right answer | Model answer, **correct**: JohnsAutomationAccount, reachable by 151 users | replace / pass |
| What changed in Entra | Fallback. A vague "15+" and a partial principal name | Model answer, **wrong total**: "40 new" (the evidence has 2,393; 40 was the example-list size) | replace / replace |
| Remediation request (out of scope) | Model answer, acceptable: no action, pointed to the evidence | Fallback. Declined correctly, but claimed blindness to the session and suggested a non-existent cmdlet | pass / replace |

**Results.**
- **Wrong content shown to the user:** 2 of 6 answers in each arm as run. The final verifier, re-applied to the same model answers, replaces every one of them except baseline question 1, whose errors are semantic and invisible to lexical checks.
- **Edge semantics:** improved answers quoted the edge meanings correctly every time they used them. The baseline described three edge types incorrectly.
- **Remaining errors:** count misattribution, list-size versus total confusion, and invented next steps. The fixes for each are in this PR: per-principal number binding, totals stated in a rendered sentence, spelled-number checks and no example-size figure.

**Latency.** Medians were 376 s (baseline) and 500 s (improved) per question. That is CPU-bound and also contended with concurrent test runs, so it says nothing about the deployment host. Prompt evaluation ran at 10–43 tokens/s. On this hardware, Hermes's own system prompt is the largest single cost: 5.2–6.2k tokens on the first call.

**What this shows.** A 4B model on this hardware selects the right tools reliably but often misreads or recombines their numbers. The evidence-backed answer is only dependable when the tools render the conclusions deterministically and the verifier enforces them. Next is the same run on the deployment host (the Mac runner) and on a larger model.
