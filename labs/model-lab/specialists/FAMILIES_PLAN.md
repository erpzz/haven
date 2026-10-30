# SPEC-2: paired specialist model families (medical, cyber, speech-to-text)

Registered 2026-10-30 by the Claude lead, at the owner's request for "a high-parameter version and a lower one
that I can actually run", trained with published frontier post-training methods plus a bounded self-improvement
loop. Status: **PLANNED**. Nothing below is trained, measured or deployed unless a receipt says so.

## What "how Claude was made" can and cannot mean here

Claude's internal training recipe is not available to this project. What is public, and what this plan uses:

1. Start from a strong pretrained model. Pretraining at that scale is out of reach and is not attempted.
2. Supervised fine-tuning on verified data (TS-1/TS-2 showed verification and teacher coverage matter more than volume).
3. Reinforcement learning from verifiable rewards (GRPO-style) where answers can be checked mechanically.
4. AI feedback against a written constitution (Anthropic's published Constitutional AI method): the model critiques
   and revises its own answers against Haven's rules; revised-over-original pairs train a preference step (DPO).
5. Distillation from the large model of each family into the small one, the usual teacher/student pairing.

Training data comes from recorded ground truth, permissively licensed public datasets and the open-weight large
models. Claude designs, builds and audits the pipeline; Claude-generated text is not a training target for these
families by default (this also keeps clear of the provider-terms question about training competing models).

## The families

| domain | large (rented GPU, or Mac/Slink with offload) | small (runs on owner hardware) | why this pair |
|---|---|---|---|
| medical | `google/medgemma-27b-text-it` (Gemma 3, 27B, HAI-DEF terms, gated) | `google/medgemma-1.5-4b-it` (Gemma 3, 4.3B, text+image, gated) | same tokenizer family: the 4B can draft for the 27B (speculative decoding) and receive logit distillation |
| cyber (defensive) | `openai/gpt-oss-120b` base, cyber-adapted here (Apache-2.0, MoE ~5B active) | `cyber-pal-security/CyberPal2.0-20B` (gpt-oss-20b, Apache-2.0, MoE ~3.6B active) | same tokenizer; both MoE, so expert offload keeps the 20B usable on Slink's 8 GB GPU; Foundation-Sec-8B-Reasoning is the outside baseline |
| speech-to-text | `nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B` (NVIDIA licence, 30B MoE ~4B active, 40 languages, diarization) | `nvidia/nemotron-3.5-asr-streaming-0.6b` (streaming); `nvidia/parakeet-tdt-0.6b-v3` (CC-BY-4.0) as alternative | large model pseudo-labels the owner's own audio (kept local) to adapt the small streaming model |

Licences marked "other" or gated must be accepted by the owner on Hugging Face before download; mirrors do not
remove the terms. Each family's weights are pinned by revision and SHA-256 in the acquisition receipt.

## Pipeline per family

```
baseline (large, small, outside reference) on frozen held-out sets
  -> SFT on verified data            (large; LoRA/QLoRA)
  -> RLVR rounds                     (large; rewards below)
  -> constitution critique/revise -> DPO   (large)
  -> distill large -> small          (sequence-level on verified outputs; logit KD where tokenizers match)
  -> bounded self-improvement loop   (both; below)
  -> quantize (GGUF/MLX) + measure on owner hardware, with the small model as speculative draft for the large one
```

Verifiable rewards and gates:

| domain | reward / filter | held-out sets (frozen, hashed before training) | must not regress |
|---|---|---|---|
| medical | exact answer on MedQA/MedMCQA-style training items; rubric-checked escalation behaviour | MedQA test, PubMedQA labelled, MMLU medical subsets, a Haven safety set (emergency recognition and escalation, medication caution, no definitive diagnosis, privacy) | safety-set pass rate; calibrated refusals |
| cyber | secpatch ground truth (verdict, CWE, Bandit re-run on patches, repository tests in an isolated runner) | secpatch held-out repositories (37 fixes, never trained), CTI-Bench, CyberMetric | detection false-positive rate, vulnerability recall (the existing promotion guard) |
| speech | WER against human references | LibriSpeech test-clean/other subsets, FLEURS en, an owner-recorded household command set (private, never in Git) | latency and real-time factor on owner hardware |

## Bounded self-improvement loop

Round k: the current model samples several answers per training prompt -> an external verifier keeps only answers
that pass ground truth, tests or rubric -> train round k+1 -> evaluate once on the frozen held-out sets -> keep the
round only if the primary metric improves with no gate regression. Stop after three rounds or when a round gains
less than 1 point. The model never edits its verifier, held-out sets, gates, prompts for its own grading, or
promotion decision. Deployment into Haven is an owner decision, as AGENTS.md requires.

## Compute plan

| resource | use | status |
|---|---|---|
| cloud session container (4 vCPU, 15 GB, no GPU) | pipeline code, data building, small-model and STT baselines | available |
| Slink (8 GB GPU) | serve small models; QLoRA up to ~8B; MoE 20B with expert offload | needs Remote Control connection from the Mac |
| MacBook | MLX serving/training sized to its unified memory (unknown) | needs Remote Control connection |
| rented GPU (1x 80 GB, or 2x for gpt-oss-120b RL) | large-model SFT/RL/DPO and distillation data generation | needs an owner account, a spending cap and an API key as an environment secret |
| Hugging Face ZeroGPU | short large-model evaluations within the daily quota (free: 5 GPU-min/day) | available to host up to 2 Spaces; quota too small for training |
| Cloudflare Workers AI (relay, PR #87) | large-model inference lane | needs the owner token on Slink |

No paid compute starts without an owner-approved budget. Every run writes a receipt (data hashes, revisions,
hyperparameters, wall time, cost) and private transcripts stay out of Git.
