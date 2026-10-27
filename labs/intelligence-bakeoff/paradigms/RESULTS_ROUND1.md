# Paradigm bake-off round 1 — results (2026-10-27)

Preregistration: `PREREGISTRATION.json`. One greedy run per model on the frozen
tool suite (verifier v3), RTX 2070 SUPER 8 GB + 64 GB RAM, llama.cpp b11146.
Session: 7/7 models completed, 109.6 GPU minutes. Sanitized data:
`results/paradigms-20261027-round1.json`.

| model | held-out /110 | Wilson 95% | + receipts | paraphrase /60 | composition /50 | legacy /8 | vs ref (gained/lost, p) | adjudicated /180 |
|---|---|---|---|---|---|---|---|---|
| qwen35-4b | 80/110 | 63.7–80.2 | 83 (+3/−0; strict 82) | 42/60 | 38/50 | 4/8 | reference | — |
| qwen3-4b | 44/110 | 31.3–49.3 | 51 (+7/−0; strict 51) | 24/60 | 20/50 | 4/8 | 8/44, p=4.04e-07 | — |
| nemotron3-nano-4b | 62/110 | 47.0–65.3 | 66 (+4/−0; strict 66) | 38/60 | 24/50 | 3/8 | 10/28, p=0.0051 | — |
| lfm25-8b-a1b | 54/110 | 39.9–58.3 | 75 (+21/−0; strict 74) | 29/60 | 25/50 | 3/8 | 10/36, p=0.000156 | — |
| nemotron3-nano-30b-a3b | 49/110 | 35.6–53.9 | 53 (+4/−0; strict 53) | 31/60 | 18/50 | 3/8 | 4/35, p=3.35e-07 | — |
| rwkv7-g1k-7b | 0/110 | 0.0–3.4 | 0 (+0/−0; strict 0) | 0/60 | 0/50 | 1/8 | 0/80, p=1.65e-24 | — |
| lfm25-24b-a2b | 47/94 | 40.1–59.9 | 54 (+7/−0; strict 52) | 24/60 | 23/34 | None/None | 5/27, p=0.000113 | — |

| model | ctx | load s | peak GPU MiB | peak RSS MiB | KV MiB | recurrent MiB | pp 2K tok/s | pp 8K tok/s | decode @1K | @8K | @32K |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen35-4b | 33280 | 5.0 | 3924 | 2970 | 1040.0 | 50.25 | 2389.24 | 2331.85 | 93.51 | 88.68 | 74.7 |
| qwen3-4b | 33280 | 66.1 | 7296 | 2702 | 4680.0 | — | 3095.94 | 2625.41 | 104.11 | 81.13 | 46.33 |
| nemotron3-nano-4b | 33280 | 64.1 | 3350 | 3039 | 520.0 | 81.09 | 2844.45 | 2876.98 | 14.9 | 101.23 | 91.03 |
| lfm25-8b-a1b | 33280 | 21.1 | 5530 | 5251 | 390.0 | 0.28 | 5125.38 | 5117.87 | 219.9 | 207.83 | 177.48 |
| nemotron3-nano-30b-a3b | 33280 | 505.4 | 2850 | 22262 | 195.0 | 47.62 | 365.72 | 395.83 | 31.84 | 31.77 | 31.29 |
| rwkv7-g1k-7b | 33280 | 4.0 | 4516 | 4661 | — | 33.0 | 1354.51 | 1383.25 | 56.89 | 56.83 | 56.66 |
| lfm25-24b-a2b | 33280 | 329.3 | 1686 | 14414 | 650.0 | 0.47 | 521.93 | 548.73 | 36.3 | 35.8 | 34.1 |

## Reading

- **No architecture beat the deployed Qwen3.5-4B** (80/110). Every paired
  comparison favours the 4B (sign test p ≤ 0.005).
- **LFM2.5-8B-A1B is the speed outlier**: 220 tok/s decode, 5.1K tok/s
  prefill, near-flat to 32K. Its deficit is mostly missing receipts; with
  Haven-rendered receipts it reaches 75 (strict 74) against the 4B's 83
  (strict 82). See `RECEIPTS_20261027.md`.
- **Experts in RAM works on this box**: Nemotron-3-Nano-30B-A3B at about
  32 tok/s and LFM2.5-24B-A2B at about 36 tok/s with `--cpu-moe`, using
  1.7–2.9 GB VRAM. Capability on this suite did not follow size: 49/110 and
  47/94.
- **Pure RNN (RWKV-7)**: 0/110. Its template has no tool rendering, so this
  measures llama.cpp's generic polyfill (labelled exploratory beforehand).
- Long-context cost: the hybrid models (Qwen3.5, Nemotron, LFM) keep 80–100 % of
  their 1K decode rate at 32K; dense Qwen3-4B drops to 45 % and uses 4.7 GB KV.

## Limits

One seed, one synthetic suite. LFM2.5-24B-A2B hit its eval deadline at 94/110
held-out episodes and no legacy episodes. Its paired test covers only those 94.
The Nemotron-4B decode figure at 1K (14.9 tok/s) is a first-request warm-up
outlier; its 2K–32K figures are 91–104 tok/s. Load seconds include cold reads
over the 480 Mbit/s USB 2 root link (about 40 MiB/s).
