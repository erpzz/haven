# Cross-paradigm bake-off: results (2026-10-27)

**Verdict.** The deployed Qwen3.5-4B scored 80/110 held-out (Wilson 95% interval 63.7–80.2). It is itself a hybrid, with 24 Gated DeltaNet linear-attention layers and 8 full-attention layers. No other paradigm beat it on this benchmark and hardware. Under the preregistered rule, all six alternatives scored **worse**: each Wilson upper bound is below 72.7%, and each paired sign test gives p < 0.01.

Where the non-attention paradigms differ is long-context cost, not capability. Every model with recurrent or convolution layers keeps at least 80% of its decode speed at 32K tokens, and its context memory stays small. The pure-attention control keeps 45%, and its KV cache alone takes 4.6 GB at 33K tokens. Among the open checkpoints available now, switching paradigm does not buy capability on owner hardware; the specific model matters far more than its paradigm.

**What a pass means.** The verifier is lexical and single-generator: one procedural episode generator, with one greedy generation per episode and one seed. A pass measures Haven's tool contract, not general intelligence.

- Preregistration: [`PREREGISTRATION.json`](PREREGISTRATION.json), committed in `f508cfa` before any scored inference.
- Sanitized aggregates, including per-family results: [`results/paradigms-20261027.json`](results/paradigms-20261027.json).
- Raw records stay private on the host.

## Tool benchmark (verifier v3, max_tokens 1024, temperature 0)

| model | paradigm | held-out /110 | Wilson 95% | paraphrase /60 | composition /50 | legacy /8 | vs ref gained/lost (sign p) | rule |
|---|---|---|---|---|---|---|---|---|
| **Qwen3.5-4B** | hybrid Gated DeltaNet + attention (24 : 8) | **80** | 63.7–80.2 | 42 | 38 | 4 | reference | — |
| Qwen3-4B | dense transformer (control) | 44 | 31.3–49.3 | 24 | 20 | 4 | 8/44 (4e-7) | WORSE |
| Nemotron 3 Nano 4B | hybrid Mamba-2 + attention (38 : 4) | 62 | 47.0–65.3 | 38 | 24 | 3 | 10/28 (0.0051) | WORSE |
| LFM2.5-8B-A1B | conv + attention hybrid, MoE | 54 | 39.9–58.3 | 29 | 25 | 3 | 10/36 (0.00016) | WORSE |
| Nemotron 3 Nano 30B-A3B | Mamba-2 + attention, MoE, experts in RAM | 49 | 35.6–53.9 | 31 | 18 | 3 | 4/35 (3e-7) | WORSE |
| RWKV-7 G1k 7.2B | pure RNN (exploratory) | 0 | 0.0–3.4 | 0 | 0 | 1 | 0/80 (2e-24) | WORSE* |
| LFM2.5-24B-A2B | conv + attention, MoE, experts in RAM | 47/94 | 40.1–59.9 | 24 | 23/34 | — | 5/27 (0.00011) | WORSE (partial) |

\* RWKV-7's template gives it no view of the tools (see Disclosures), so its zero measures llama.cpp's tool polyfill, not the architecture.

- **Reference vs PR #45.** Under the PR #45 condition (max_tokens 256) the reference scored 76/110. At 1024 it scores 80/110. None of its steps reached the token limit.
- **Complementarity (oracle only).** These figures assume an oracle that picks the better answer per episode; no selector exists. Pairing the reference with Nemotron 3 Nano 4B, or with LFM2.5-8B, would solve 90/110 episodes. Some families favour other models:
  - Nemotron 4B: `cross_user_deny` 5/6 vs 3/6 for the reference.
  - LFM2.5-8B: `missing_note` 5/6 vs 2/6, and `no_tool` 6/6 vs 3/6.
- **Authority violations.** These dominate the Qwen3-4B and Nemotron 30B failures: 22 and 23 respectively, against 1 for the reference.

## Performance

All models loaded with `-c 33280`. Every model ran on the GPU (`-ngl 99`); the two MoE models marked "experts in RAM" also used `--cpu-moe`. All 32K probes fit.

- Decode figures are tok/s over 128 tokens after a prompt of the given length. "Kept 32K/2K" is the 32K decode rate divided by the 2K rate (see the probe disclosure for why 2K, not 1K).
- Memory is the server's peak GPU usage from per-process nvidia-smi samples, and VmHWM for RAM. RAM includes the memory-mapped weights.

| model | peak GPU MiB | peak RAM MiB | KV MiB | recurrent MiB | pp 2K | pp 8K | decode 2K | 8K | 32K | kept 32K/2K |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-4B | 3924 | 2970 | 1040 | 50 | 2389 | 2332 | 93.2 | 88.7 | 74.7 | 80% |
| Qwen3-4B | **7296** | 2702 | **4680** | — | 3096 | 2625 | 100.3 | 81.1 | 46.3 | **46%** |
| Nemotron 3 Nano 4B | 3350 | 3039 | 520 | 81 | 2844 | 2877 | 104.1 | 101.2 | 91.0 | 87% |
| LFM2.5-8B-A1B | 5530 | 5251 | 390 | 0.3 | **5125** | **5118** | **218.3** | **207.8** | **177.5** | 81% |
| Nemotron 3 Nano 30B-A3B | 2850 | 22262 | 195 | 48 | 366 | 396 | 32.0 | 31.8 | 31.3 | 98% |
| RWKV-7 G1k 7.2B | 4516 | 4661 | — | 33 | 1355 | 1383 | 56.8 | 56.8 | 56.7 | 100% |
| LFM2.5-24B-A2B | 1686 | 14414 | 650 | 0.5 | 522 | 549 | 36.3 | 35.8 | 34.1 | 94% |

**Load time.** Seconds from process start to ready: Qwen3.5-4B 5, Qwen3-4B 66, Nemotron 4B 64, LFM2.5-8B 21, Nemotron 30B 505, RWKV 4, LFM2.5-24B 329. These reflect page-cache state on a USB-2 root disk, not the architecture. The reference file was already cached by the Lab.

## Verdict per paradigm

- **Dense attention (Qwen3-4B): worse.** It scored 44/110, with paired 8/44 against the reference.
  - Its 32K decode rate is 46% of its 2K rate.
  - A 33K context costs 4.6 GB of KV, which puts the server at 7.3 of 8 GB.
  - This is the only paradigm here whose context length is capped by this GPU.
  - Caveat: the comparison with Qwen3.5 is not architecture-isolated, because Qwen3.5 is a newer generation trained on different data.
- **Gated DeltaNet hybrid (Qwen3.5-4B): best on both axes among the 4B models.**
  - It keeps 80% of its decode rate at 32K (79.9% by the preregistered 1K baseline, 0.1 point under the 80% bar).
  - Its context memory is 1.1 GB at 33K, a quarter of the pure-attention model's.
- **Mamba-2 hybrid (Nemotron 3 Nano 4B): worse (62/110, p=0.005), best long-context 4B.**
  - It keeps 87% of its decode rate at 32K and needs 0.6 GB of state.
  - It wins `cross_user_deny` and `list_then_read`.
  - It is the closest challenger, and the strongest case that this paradigm is viable at small scale. It still did not match the reference.
- **Mamba-2 + MoE with experts in RAM (Nemotron 3 Nano 30B-A3B): worse (49/110).**
  - Eight times the parameters bought nothing on this benchmark.
  - It made 23 authority violations.
  - Decode is a flat 31 tok/s, limited by RAM bandwidth for the offloaded experts, and the model needs 22 GB of RAM.
- **LFM2 conv hybrid + MoE (LFM2.5-8B-A1B): worse (54/110), fastest.**
  - Its decode rate is 218 tok/s, 2.3× the reference's.
  - It processes prompts at about 5.1K tok/s, and its recurrent state is 0.3 MiB.
  - It reasons on every step and never hit the 1024-token limit.
- **LFM2 conv hybrid + MoE with experts in RAM (LFM2.5-24B-A2B): worse on the episodes it completed (47/94, paired 5/27).**
  - The 35-minute per-model cap cut the run short (see Disclosures). On the paraphrase track alone, which it completed, it scored 24/60 against the reference's 42/60.
- **Pure RNN (RWKV-7 G1k): capability unmeasured; memory claim confirmed.**
  - Decode is flat at 56.7 tok/s out to 32K, with a constant 33 MiB of state.
  - The 0/110 score reflects the missing tool template, not the model.

## Next falsifiable experiment

Hold the reference's family and paradigm fixed and raise only the scale:

- **Model:** Qwen3.6-35B-A3B, a Gated DeltaNet hybrid MoE with ~3B active parameters.
- **Placement:** experts in RAM through llama.cpp's expert cache.
- **Condition:** exactly the condition above.

**Prediction:** it beats 80/110 under the preregistered rule (Wilson lower bound above 72.7%, sign test p < 0.05) and decodes at ≥ 25 tok/s.

**If it does not:** neither paradigm (this run) nor scale with offloading is the lever on this host. The next target should then be the tool contract and prompt rather than the model.

A round-2 preregistration and download for this model are already in progress (`haven-fetch-qwen36`), so this experiment should not be duplicated.

A cheaper follow-up comes out of the complementarity numbers. Test whether any selector that runs at inference time, and never consults the verifier, can recover part of the 10-episode oracle gap between the reference and Nemotron 4B.

## Disclosures

- **Unscored CPU checks.**
  - Before any GPU run, the tool-call format of Nemotron 4B, LFM2.5-8B and RWKV-7 was checked on 2–3 training episodes each, on CPU and unscored.
  - The Nemotron check ran before the preregistration commit. It informed nothing except the decision that the default parser works.
- **Token limit.** max_tokens is 1024, against 256 in PR #45, so that always-reasoning templates are not truncated by construction. The reference was re-run under this condition.
- **RWKV-7 template.**
  - The community GGUF's template does not render tools or tool results. llama.cpp's generic polyfill is all the model sees.
  - 57 of its 118 episodes hit `MAX_TOOL_ROUNDS` because it invented tool names, and 48 steps reached the token limit.
  - Treat the score as exploratory.
- **"Transport failures" in the JSON.** Every one is a `MAX_TOOL_ROUNDS` loop, not a network error:

  | model | loops |
  |---|---|
  | RWKV | 57 |
  | Nemotron 30B | 9 |
  | LFM2.5-24B | 5 |
  | Nemotron 4B | 4 |
  | Qwen3.5-4B | 2 |
  | LFM2.5-8B | 1 |
  | Qwen3-4B | 0 |

- **LFM2.5-24B cut short.**
  - `session.py` caps each model's eval at 35 minutes; the preregistration does not record this default.
  - The stretch model finished 94 of 118 episodes: all of paraphrase, 34 of 50 composition, and no legacy episodes.
  - Its paired test covers only the 94 completed held-out episodes; 16 are unpaired.
- **1K probe is a warm-up.**
  - The 1K probe is the first request after load, and it includes warm-up: every model's prompt processing is slower at 1K than at 2K. For example, Qwen3.5-4B runs at 655 tok/s at 1K against 2389 at 2K.
  - For Nemotron 4B the warm-up also depressed decode, to 14.9 tok/s against 104 at 2K. That figure is invalid.
  - The table therefore uses 2K as the baseline for "kept". The preregistered 1K figures are in the JSON. Using them changes no long-context conclusion except for Qwen3.5-4B, which lands 0.1 point under the 80% bar.
- **Licenses.** The Nemotron models are under the NVIDIA Open Model License. The LFM2.5 models are under the LFM Open License v1.0. Neither is Apache-2.0; read them before deploying.
- **Strata restore: not completed.**
  - The session released the GPU lease at 02:46 UTC and started `haven-strata`.
  - At 02:53:44 something else stopped Strata, seven minutes into its roughly 15-minute load. A Model Lab GPU engine then started.
  - Strata was not restarted afterwards, so as not to contend with the new GPU owner.
  - The Lab's CPU engine that was connected at the start was not touched by this session.
  - Afterwards: a later round-2 session's restore at 16:37 UTC also failed. Strata's engine missed its 900-second ready limit, probably because the bake-offs had evicted its expert pages from the page cache and the root disk is USB-2. A manual start at 16:54 succeeded. Strata answered at 17:08 UTC, with the Lab connected to it.
- **Session time.** GPU time was 109.6 minutes (00:56:49–02:46:25 UTC), and the whole session took 117.1 minutes. Downloads came to 49,520,295,232 bytes in five files, all SHA-256 verified at pinned revisions.
