# LoRA and post-training research plan

## What an adapter is

A LoRA adapter adds, for selected weight matrices W (d_out × d_in), a low-rank update ΔW = B·A, where A is r × d_in and B is d_out × r, with r ≪ d (typically 8–64), scaled by α/r. The base weights stay **frozen**: only A and B train. That is why the 9B base can be quantized to 4-bit during training (QLoRA) and why one base can carry several adapters.
- **Loading and switching:** PEFT attaches adapters by name and can switch or disable them per request. llama.cpp loads GGUF LoRA files with `--lora` (scale adjustable), or the adapter can be merged into the bf16 weights and re-quantized.
- **Size:** for Qwythos at r=16 on all language-model projections, the adapter is roughly 0.1–0.2 B parameters (a few hundred MB in fp16), against a 19.3 GB bf16 base.

## What LoRA can and cannot do

- **Learns well:** behaviour and format. Examples: calling a tool instead of answering from memory; reading an error and trying an alternative; emitting the requested JSON; refusing to guess; consistent evidence labelling; domain-specific reasoning *patterns* (report-only enforces nothing; exclusions beat inclusions; NotActions are not denies).
- **Learns poorly:** large volumes of new facts, and facts that change. Retrieval is the right layer for product details, versions and advisories, with citations. Continued pretraining could inject knowledge but costs far more, forgets more, and still goes stale.
- **Forgetting and regressions:**
  - narrow data can raise false positives; forge cycle 1 on the 4B student raised FPR to 0.31 while held-out accuracy rose by 0.22;
  - it can degrade general reasoning and cause format overfitting.
  - Mitigations: low rank, short training, mixing in general and negative or no-tool examples, and gating promotion on held-out accuracy **and** FPR against the unchanged base.

## Compatibility with Qwythos (verified facts; see the environment audit)

- **Trainable source:** the bf16 HF checkpoint (`Qwen3_5ForConditionalGeneration`) is on Slink, with tokenizer and chat template. The Q4_K_M GGUF is **not** a training format.
- **Architecture:** hybrid Gated DeltaNet + full attention. LoRA targets must cover both layer types:
  - attention `q/k/v/o_proj`;
  - the linear-attention `in_proj_*` and `out_proj`;
  - MLP `gate/up/down_proj`, restricted to `language_model` (not the vision tower).
  - The forge `qlora_probe.py` regex already does this.
- **Memory:** the untied 248k-vocab embedding and lm_head are about 1 B parameters each. On small GPUs they are kept on CPU, with logits computed only at answer positions (forge trainer technique).
- **Hardware:**
  - Slink's 8 GB RTX 2070S: **blocked for the 9B**, measured today (NF4 weights 3.33 GiB loaded; backward failed with `CUBLAS_STATUS_ALLOC_FAILED`).
  - Kaggle 2× T4 16 GB: the working lane. The forge session is training a Qwythos adapter there right now (`haven-forge-train-qwythos-c001`, secpatch data). T4 has no bf16, so compute is fp16 with a GradScaler.
- **Serving the result:** either merge into bf16, convert to GGUF and quantize to Q4_K_M, or convert the PEFT adapter with llama.cpp's LoRA converter and load it with `--lora`. The second path must be checked for the DeltaNet `in_proj` tensor names; until then, merge-and-requantize is the safe path.
- **Licence:** Apache-2.0 base, so adapters and merged weights can be distributed with attribution.

## Experiments

| | A: agent reliability | B: cyber domain reasoning | C: small specialist |
|---|---|---|---|
| Goal | call the right tool with thinking **off**, recover from tool errors, stop guessing, finish in the requested JSON | enterprise identity/cloud reasoning patterns | tool selection, finding normalization and routine classification, so Qwythos keeps the hard cases |
| Evidence it matters | baseline: thinking-off Qwythos made **0 tool calls** in condition C; thinking-on calls tools but costs 5–10× latency | baseline A/B errors: report-only treated as enforcing, "other"-only block treated as complete, NotActions treated as deny, 53003 misread | the HCA rules and normalizers are deterministic; a 4B model can learn to drive them |
| Data | grader-verified trajectories in the `toolenv` tool format; failure-recovery and `not_applicable` rows | assessor- and verifier-labelled synthetic tenants and RBAC sets; corpus-grounded rationales | the same trajectories, truncated to the routing decision |
| Base | Qwythos-9B-v2 | Qwythos-9B-v2 | Qwen3.5-4B (forge student; QLoRA proven on T4) |
| Loss | every assistant turn including XML tool calls (forge trainer is being extended for this) | final turn | routing turn |

**One adapter or several?**
1. Train A and B separately, then a combined A+B at the same total steps.
2. Compare on the same held-out split, by category.
3. Separate adapters can be served side by side only if switching cost is acceptable; llama.cpp applies them at load time.
- Prior expectation: A carries most of the benefit, because the tools already answer the B-type questions correctly when called.

## Data format

OpenAI-style messages per row:
- `system`: the harness system prompt plus the tool system prompt;
- `user`: the task, synthetic artifacts and answer format;
- `assistant`: content plus `tool_calls`;
- `tool`: the real tool output;
- final `assistant`: JSON only.

`tools` holds the five schemas from `eval/toolenv.py`, and `enable_thinking=false`. The trainer renders rows through Qwythos's own chat template, so the tokens match serving.

## Training configuration (starting point)

QLoRA NF4 with double quantization, fp16 compute (T4); r=16, α=32, dropout 0.05; LR 1e-4 cosine with 3% warmup; effective batch 16; 1–2 epochs; max length 3,072 (trajectories with tool output; tenant JSON is the long part). Gradient checkpointing; embeddings and lm_head on CPU; logits only on assistant tokens. Save checkpoints every 100 steps plus the best on a dev split carved from training data (never the eval set).

## Resource budget

- **9B on Kaggle 2× T4:** the forge session's Qwythos run is the measured reference. The forge probe on comparable rows (768–1,536 tokens) is the per-step basis.
- **Expected run:** ≈600–1,000 trajectories × 2 epochs fits one free 12 h session. The free tier gives ≈30 GPU-hours a week.
- **Evaluation:** on Slink at ≈7 s per item with thinking off, 55 scenarios × 3 conditions ≈ 20–30 min.

## Held-out evaluation

`labs/cyber/eval` has 55 scenarios, 20 of them `split=heldout`, with answers in a separate canary-tagged file.
- **Condition D** = condition C with the adapter served at the endpoint: `python -m haven_cyber.eval.harness --endpoint … --conditions A,B,C --out runs/eval/<adapter>`.
- **Promotion rule:** held-out pass ≥ base, with the false-positive count ≤ base, reported per category, and the secpatch held-out checked for general regression.

## Pilot status (honest)

- **Not started by this session.**
- The cyber trajectory dataset is not built yet. The forge session has agreed to build the generator on `toolenv`/`grade.py` once the owner approves.
- The Kaggle lane is occupied by the forge Qwythos secpatch adapter (≈9 h at last report).
- The only local GPU cannot fit 9B QLoRA (measured).
- **Reproducible next step:** build the dataset (forge session) → train with the forge trainer on Kaggle using the configuration above → serve on Slink :8095 with the adapter merged → run condition D.
