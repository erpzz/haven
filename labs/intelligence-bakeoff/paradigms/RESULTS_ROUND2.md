# Paradigm bake-off round 2 — results (2026-10-27)

Preregistration: `PREREGISTRATION_ROUND2.json`, registered before any round-2
inference. One greedy run per model on the frozen tool suite (verifier v3) and on
the independent adjudicated suite (180 frozen episodes, a different generator and
grader). RTX 2070 SUPER 8 GB + 64 GB RAM, llama.cpp b11146, the same server
arguments as round 1. Session: 4/4 models completed, 100.2 GPU minutes.
Sanitized data: `results/paradigms-20261027-round2.json`.

| model | held-out /110 | Wilson 95% | + receipts | paraphrase /60 | composition /50 | legacy /8 | vs ref (gained/lost, p) | adjudicated /180 (vs ref) |
|---|---|---|---|---|---|---|---|---|
| qwen35-4b | 80/110 | 63.7–80.2 | 83 (+3/−0; strict 82) | 42/60 | 38/50 | 4/8 | reference | 58/180 |
| qwen35-9b | 83/110 | 66.6–82.5 | 89 (+6/−0; strict 89) | 41/60 | 42/50 | 6/8 | 16/13, p=0.711 | 101/180 (51/8, p=9.05e-09) |
| lfm25-8b-a1b | 54/110 | 39.9–58.3 | 75 (+21/−0; strict 74) | 29/60 | 25/50 | 3/8 | 10/36, p=0.000156 | 56/180 (31/33, p=0.901) |
| qwen36-35b-a3b | 81/110 | 64.7–81.0 | 82 (+1/−0; strict 82) | 44/60 | 37/50 | 6/8 | 13/12, p=1 | 121/180 (73/10, p=5.8e-13) |

| model | ctx | load s | peak GPU MiB | peak RSS MiB | KV MiB | recurrent MiB | pp 2K tok/s | pp 8K tok/s | decode @1K | @8K | @32K |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen35-4b | 33280 | 3.2 | 3932 | 2971 | 1040.0 | 50.25 | 2392.22 | 2322.39 | 93.71 | 88.68 | 74.72 |
| qwen35-9b | 33280 | 131.1 | 6218 | 5774 | 1040.0 | 50.25 | 1539.2 | 1511.11 | 59.57 | 57.42 | 51.23 |
| lfm25-8b-a1b | 33280 | 119.1 | 5530 | 5252 | 390.0 | 0.28 | 5132.18 | 5134.46 | 221.02 | 209.35 | 178.59 |
| qwen36-35b-a3b | 33280 | 500.4 | 3278 | 22175 | 650.0 | 62.81 | 333.45 | 337.52 | 34.96 | 36.18 | 34.63 |

The round-1 rows for the 4B and LFM reproduce exactly (greedy decoding), so
round 1 and round 2 are on the same footing.

## Predictions and rules

| preregistered | outcome |
|---|---|
| 35B: tool suite ≥ 76/110 | **held**: 81 |
| 35B: decode 18–30 tok/s at 1K | **missed, on the fast side**: 35.0 |
| 35B kill: < 12 tok/s or < 70/110 | not triggered |
| 9B: tool suite ≥ 84/110 | **missed**: 83 |
| 9B kill: ≤ 80/110 | not triggered |
| LFM: 4B stays ahead on the adjudicated suite | **held, barely**: 58 vs 56, paired 31/33, p=0.90 (a tie) |
| Receipts: strict with-receipts ≥ model-only for every model | **held**: 82/89/74/82 vs 80/83/54/81 |
| Receipts kill: mean strict gain < 1, or strict gains < half the raw gains | not triggered: mean strict gain 7.25; strict/raw 2/3, 6/6, 20/21, 1/1 |

**Default model: unchanged.** The decision rule requires a win on both suites,
with p < 0.05 on the tool suite. The 9B (p=0.71) and the 35B (p=1.0) tie the 4B
there, so neither replaces it. Both clear the 20 tok/s floor and both are now
offered in the Lab catalog as explicit choices with these numbers.

## Reading

- **The two suites disagree, and that is the main finding.** On the tool suite
  the 4B, 9B and 35B are statistically indistinguishable (80/83/81). On the
  independent adjudicated suite they separate sharply: 58 → 101 → 121, with
  paired p of 9e-9 and 6e-13. The tool suite was built as distillation data for the deployed 4B's
  contract and appears to cap out near 80–83 for any competent model. This is
  a hypothesis, not yet a result; see "Next".
- **Experts in RAM is the strongest model measured on this box.** Qwen3.6-35B-A3B
  uses 3.3 GB of VRAM and 22 GB of RAM, and decodes a flat 35 tok/s from 1K to
  32K. Round 1's Nemotron-30B-A3B used the same technique but scored 49/110,
  so the gain comes from this model, not from size alone.
- **Where the 35B wins** (adjudicated passes out of 12 per family, 4B → 35B):
  - refusing an unsafe execute request: 0 → 11
  - spotting a stale premise: 2 → 12
  - applying a conflict rule: 3 → 12
  - resolving distractors: 3 → 12
  - injected tool output: 2 → 9
  - three-step conditional chains: 1 → 5
- **Where the 35B loses:** explicit proposal requests, 12 → 5. It proposes
  less often when asked to.
- **The 4B over-calls tools.** 14 of its 180 adjudicated episodes ended at the
  harness's tool-round limit. The suite logs these as transport failures, but
  they are model behaviour. The ranking holds even if every one of them is
  counted as a pass: at most 72, against 101 and 121.
- **The cost of the 35B is prefill and RAM.** At about 330 tok/s prefill (the
  4B does 2.3K), a 4K-token prompt waits about 12 s for its first token. Its
  22 GB of RAM means it cannot run while Strata (54 GB) is up. Cold load takes
  500 s over the current USB 2 root link.
- **The 9B is the practical middle.** 60 tok/s decode, 1.5K tok/s prefill,
  6.2 GB of VRAM, and a cold load of about 2 minutes.
- **Receipts survive the stricter rule.** Most of their value is still LFM's
  formatting deficit (+20 strict). They add almost nothing to the 35B (+1),
  which already cites its evidence.

## Limits

These results come from one greedy seed. The adjudicated suite is synthetic and
was frozen before round 2, but this is the first time it ranked these models,
so treat it as one strong signal, not a verdict. No breakthrough is claimed
from round 2 alone, per the preregistration. Load seconds include cold reads
over the 480 Mbit/s USB 2 root link (about 40 MiB/s).

## Next (proposed, not preregistered)

1. Preregister round 3 with the disagreement as its question. Score both suites
   on fresh episodes from new generator seeds, so the adjudicated suite is not
   reused after it has been seen. Decide in advance which suite gates the
   default.
2. Run Strata's own model through both suites. It has never been scored on
   either.
3. Run the 35B with receipts and a prefill-friendly context. It needs a short
   system prompt and prompt caching, because prefill is its bottleneck.
