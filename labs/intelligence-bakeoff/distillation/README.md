# Haven Distillation Lab — October 12, 2026

**Status:** implementation candidate; synthetic-data construction and test scripts committed. No model training, benchmark improvement, Windows-host evaluation, GPU memory qualification, cloud usage or deployed agent learning is claimed. This work depends on R02 bakeoff PR #28 and does not replace Haven Model Lab, IP-01, the two-user data boundary or the retained drone/robotics research.

## What is implemented

| Lane | Actual mechanism | What it is NOT |
|---|---|---|
| Verified-success SFT | Re-score local R02 JSONL, retain passing trajectories, and condition the completion on observed tool results | Not off-policy RL; tool calls are not autonomously re-executed |
| Failure-aware foresight | Queue failed traces for review; accept only reviewed, evidence-identified *prospective* targets with a pre-trajectory prompt | An SRD-inspired supervised proxy, **not a replication** of full SRD prospective-policy training |
| On-policy distillation | Opt-in TRL experimental GKDTrainer, student-generated trajectories, teacher token supervision; beta=1 reverse-KL limit, beta=0 forward-KL limit | Not trainable from a frontier chat API that provides only text; not qualified for Haven's 8-GB GPU |
| Skill versus knowledge | Frozen synthetic compositional, learned-fact, unknown-fact and context-grounded probes; exact-match before/after group deltas | Not production-quality, coding, privacy or general reasoning certification |

Primary research motivating this experiment: [SRD (2026-10-06)](https://arxiv.org/abs/2610.08077) and [On-Policy Distillation Teaches New Skills but Not New Knowledge (2026-10-07)](https://arxiv.org/abs/2610.09639). Framework reference: [TRL GKD trainer](https://huggingface.co/docs/trl/gkd_trainer). This implementation is intentionally narrower than those papers.

## 1. Validate without a GPU

From `labs/intelligence-bakeoff`:

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s distillation/tests -v
```

The second suite checks task holdouts, principal matching, reviewed-annotation gates, dataset integrity, prompt masking, dry-run behavior and independent skill/factual diagnostic scoring. **A test file being committed is not evidence that it has executed successfully.**

## 2. Produce synthetic rollouts

Run the existing R02 harness against a local, explicitly loaded model using the same known fixtures:

```powershell
python bakeoff.py --base-url http://127.0.0.1:8080/v1 --model YOUR_BACKEND_MODEL_ID --label pre-distillation --repetitions 3
python score.py runs/pre-distillation.jsonl
python distillation/pipeline.py --runs runs/pre-distillation.jsonl --synthetic-only
```

Generated files under the gitignored `distillation/data/`:
- `manifest.json`: deterministic train-task/holdout-task IDs and actual counts.
- `success.jsonl`: **passing only**, grounded in serialized observed tool results.
- `review_queue.jsonl`: unsuccessful attempts **not** used as training targets.
- `foresight.jsonl`: empty unless reviewed hindsight annotations were provided.
- `policy_prompts.jsonl`: task prompts for genuine GKD student rollouts (not precomputed teacher completions).

Review each failed row and construct an optional local JSONL file containing `task`, exact `source_digest`, `reviewed: true`, a meaningful `evidence` citation, and `foresight`. Use the digest of the *original* exact run record (the queue has it). Rebuild with:

```powershell
python distillation/pipeline.py --runs runs/pre-distillation.jsonl --annotations distillation/data/approved_hindsight.jsonl --synthetic-only
```

Do **not** automatically convert a failed answer into a target; a model cannot approve its own failure analysis. Foresight inputs intentionally exclude the trajectory. Use a separate foresight adapter so the ordinary assistant does not learn to emit failure predictions in place of answers.

## 3. Pilot lightweight LoRA training, explicitly

Haven Model Lab's Qwen3.5-4B **GGUF inference model is not a Hugging Face training checkpoint**. Do not pretend that directly fine-tuning the GGUF is supported. First pilot the mechanics with the *separate* text-only `Qwen/Qwen3-0.6B` base, using fp16 LoRA and small batches. This does **not** train Haven's existing 4B champion. Run only after reviewing the locally produced examples and dependencies (`torch`, `transformers`, `peft`).

Dry-run first:

```powershell
python distillation/train_sft.py --data distillation/data/success.jsonl
python distillation/train_sft.py --data distillation/data/foresight.jsonl
python distillation/train_sft.py --data distillation/fixtures/knowledge_sft.jsonl
```

The foresight recipe correctly refuses to train if there are no approved records. To *actually* run one of the nonempty recipes on a CUDA host with already cached compatible model weights, append `--execute`. If intentionally downloading new model weights, additionally append `--allow-download`. Files and adapters are saved only to a gitignored local folder. No training or downloads occur on a dry run. Training does not install its Python dependencies for you.

Upstream Unsloth's Qwen3.5 guide quotes roughly **10 GB for 4B bf16 LoRA** and advises against Qwen3.5 QLoRA for quality reasons. That exceeds our 8-GB GPU before runtime overhead. RTX 2070 Super is Turing; prefer fp16 over assuming native bf16 support. A serious Qwen3.5-4B adapter requires a separately qualified larger-memory training setup. The 64-GB system RAM is helpful for data preparation, but it is not equivalent to GPU VRAM.

## 4. Run real on-policy teacher supervision (larger GPU only)

After provisioning compatible local teacher/student weights and optional dependencies (`trl`, `datasets`, `peft`, PyTorch/Transformers):

```powershell
python distillation/train_opd.py --prompts distillation/data/policy_prompts.jsonl --beta 1
python distillation/train_opd.py --prompts distillation/data/policy_prompts.jsonl --beta 0
```

Those are metadata/dataset **dry-runs**. Actual runs require `--execute`, model files present locally or explicit `--allow-download`, and a CUDA GPU. The default memory gate is 16 GB; an advanced `--override-memory-gate` is provided for separately measured small-model experiments, **not** as evidence that an 8-GB run will fit. Always use different output directories for beta variants and preserve baseline receipts.

TRL GKD needs model forward passes providing teacher token probabilities, not just an API text response. Compared with GKD, a teacher-generated JSONL SFT dataset is a different, weaker kind of distillation; label it accordingly. An HTTP remote-teacher logits adapter is **not implemented**.

## 5. Evaluate separate abilities before any promotion

The `fixtures/knowledge_sft.jsonl` contains three **invented, synthetic** facts for the factual-learning control; the evaluation asks differently phrased questions about the same facts. Unseen-catalog questions test whether the model refuses to invent missing facts. Retrieval probes put evidence inside the prompt. Composition probes test rule chaining without those catalog facts.

Run exactly the same frozen probes before and after each experiment, against an explicitly loaded model. For adapters, serve the corresponding Hugging Face checkpoint/adapter via a compatible *local* inference server; Model Lab's GGUF engine does not automatically load PEFT adapters:

```powershell
python distillation/evaluate.py run --model BASE_MODEL --base-url http://127.0.0.1:8080/v1 --output distillation/runs/before.jsonl
python distillation/evaluate.py run --model TRAINED_MODEL --base-url http://127.0.0.1:8080/v1 --output distillation/runs/after.jsonl
python distillation/evaluate.py compare --before distillation/runs/before.jsonl --after distillation/runs/after.jsonl
```

Also rerun the original R02 privacy/authority/tool-use suite. **Promotion requires** no new cross-user leakage or forbidden actions, equal task sets, no degraded known-answer or tool scores, and meaningful repeatable improvement on genuinely held-out non-synthetic coding/agent tasks. The included tiny probes are instrumentation smoke tests, not evidence of improved model intelligence.

## Privacy, authority and limits

- The GitHub repository is **public**. Do not commit run JSONL, review queues, teacher completions, model weights, adapters, local databases, logs, real user prompts, employer data, private household notes, secrets or credentials. The generated directories are gitignored. Synthetic-only is enforced for the checked-in fixture task definition; do not use this pipeline on real Haven data without a new review of identity, data consent and leakage boundaries.
- Principal mismatches and unfamiliar task IDs are rejected. Task-level deterministic holdouts are excluded from every training export. A scored "pass" is only a pass of the existing synthetic mechanical scorer; it is not a general statement of answer quality.
- There are no autonomous agent actions, scheduled jobs, devices, physical outputs, silent API calls, force merges or purchases here. No user-specific memory is exported.
- SRD-inspired foresight SFT is a **proxy**. Reproducing the paper's prospectively trained representations, full RLVR/RL objectives, and long-horizon trajectory acquisition remains future work. It must not be reported as done.
- No training may overwrite a non-empty output adapter folder; no network download is initiated unless explicitly permitted during an `--execute` run.

## Acceptance gates / next decision

1. Run both pure-stdlib test suites and the deterministic synthetic example conversion on a developer machine.
2. Generate a few genuine local Qwen3.5-4B bakeoff trajectories, review their content/labels, and inspect success/failure counts.
3. Perform 0.6B fp16 LoRA pilot; collect actual RTX 2070 SUPER peak VRAM, elapsed time, and stability.
4. Evaluate baseline versus adapters on frozen skill, factual, RAG, tool/privacy and a larger coding suite, repeating runs.
5. Decide whether results justify a separately provisioned training GPU for Qwen3.5-4B and genuine beta=0/beta=1 GKD.

This is an **additive R02 experiment**; maintain the retained two-person privacy, daily assistant, robotics, drones, RF/spatial, safety and independent review scope.
