# Adapter provenance (from the forge session, 2026-10-31)

Recorded as received. PENDING fields are filled in when the Kaggle runs finish.

## Common base

- Checkpoint: `empero-ai/Qwythos-9B-v2` @ `2178f73a9b5ea28ccd8f6096ef6bac5cd59c9d8b`; `model.safetensors` sha256 `85915acf5a7955f82a47dfe4669b7fe8fd8b58c22a5c1dfbf300b193ca0b7a27`.
- Base GGUF (used for the base re-run): `empero-ai/Qwythos-9B-v2-GGUF` @ `97c11b0`, `Qwythos-9B-v2-MTP-Q4_K_M.gguf` on Slink. The full sha256 is recomputed in `receipt.json`.

## Adapter A: agent reliability v1

- Kaggle kernel `haven-forge-train-qwythos-agent-v1`, version 1, pushed 22:41:37Z.
- Data:
  - generator `forge/agentgen.py` at commit `65b9011` (PR #95), seed 11, produced 22:40:28Z;
  - 640 trajectories (ca 260, rbac 220, host 160) → 1,280 step rows, from 2,896 candidates (drops for answer balance only); grade_failed 0, leak_rejected 0;
  - `sft.jsonl` sha256 `c9d0cb87fe3cf8c4638be09e89e5190244b15d008c4bda556868028d612ee4ee`; `trajectories.jsonl` `0e0f5c32ebc8a3964752a71c52998e74e4fb8d61744455d9beadc5b9195d1e0d`;
  - leakage screen: 101 markers from `eval/scenarios/v1.json`; positive controls passed (receipt in the forge `agent/v1/manifest.json` on Slink).
- Training:
  - QLoRA NF4 with fp16 compute on 2×T4 DDP; LoRA r=32, α=64, dropout 0.05 on language_model `q/k/v/o/gate/up/down/in_proj_*/out_proj`;
  - LR 1e-4 cosine with 3% warmup, 1 epoch, effective batch 16, max length 6,144;
  - loss on the target assistant step only (tool call or JSON plus `<|im_end|>`);
  - trainer commit `65b9011`.
- Export: merge into fp16 → restore MTP tensors → `convert_hf_to_gguf` (b11146) → Q4_K_M. The merged directory is deleted; `adapter/` is kept for a deterministic re-merge.
- GGUF path / sha256: PENDING. Final train loss: PENDING.

## Adapter B: secpatch code review c001

- Kaggle kernel `haven-forge-train-qwythos-c001`, version 2, pushed 22:10:25Z. Version 1 failed in setup on a chat-template assertion, before training.
- Data:
  - forge cycle-1 secpatch (OSV PyPI fix diffs);
  - `sft.jsonl` `b9194ee16a9b…dcc7`: 3,855 rows, 3,748 used at ≤3,072 tokens;
  - `pairs.jsonl` `bb0fb937075d…a2cf`: 355 pairs, from before the forge direction-balancing fix.
- Training: same LoRA settings, max length 3,072, then DPO+NLL (β 0.1, NLL weight 1.0, LR 2e-5); trainer commit `7b5eb49`.
- No cyber eval content and no function-calling rows. It has 21 text-only secpatch "tool_select" rows.
- GGUF path / sha256: PENDING. Final train loss: PENDING.

## Disclosure (verbatim summary of the forge session's statement)

Before writing the generator (~22:31–22:38Z), the forge session had read:
- my handoff, which named tf-01, rbac-01, lg-01, ca-05, fp-01 and "netstat missing → ss";
- `toolenv.py`, `harness.py`, `grade.py`, `azure_rbac.py` and the `entra_ca` rule lines;
- `fixtures/tenants/build.py`, including `weak()` and `hardened()`.

Family by family:
- **host**: informed by tf-01 and the netstat → ss note. Training-target.
- **rbac**, NotActions-in-another-role trap: informed by rbac-01. Training-target.
- **rbac**, reader-without-dataActions and deny assignments: designed from `azure_rbac.py` semantics before rbac-04 was named. Its pattern matches rbac-04, so treat it as design-overlapping.
- **ca**: gap types are modelled on `weak()`; all-pass tenants mirror `hardened()`. Names, ids and values are fresh. Treat CA gains (including held-out ca-02) as informed by eval-fixture design.
- There are no logs, identity, cloud, graph, network or fp rows; ca-03's "other"-only block is not in v1.
- Nothing changed after the baseline message: v1 was generated (22:40Z) and pushed before it arrived. No v2 exists.
- `eval/scenarios/v1.json` was read only programmatically by the leakage screen (one id, ca-04, was seen in a probe output). `eval/answers` was never opened.

## Provenance classes used in the comparison

`classes.json` in this folder, committed before any adapter result. Held-out split: T1 5 (all CA), T2 2 (rbac-02, rbac-05), T3 13.

## Update: Adapter A run 2 (reported by the forge session, 2026-10-31 night)

- Run 1 (kernel version 1) hit CUDA OOM at step 37/80 on a ~6k-token row. **No GGUF was produced.**
- Run 2 (kernel version 2) makes one change: `max_length` 6144 → **5632**, which drops the 45 longest rows (all agent-ca, large tenant snapshots). That leaves 1,235 of 1,280 step rows.
- Data files are byte-identical (`sft.jsonl` `c9d0cb87…ee4ee`); only the length cap in `config.json` changed.
- Effect on classes: none. The dropped rows are CA (T1 already).
- Scheduling decision: wait for both adapters and run base, A and B **back to back in one window**, as pre-registered, rather than splitting into two windows.
