# Efficient and specialist models for Haven — compatibility and decisions (2026-10-30)

Scope: Liquid LFM3/LFM2.5, decision ("System One") models, and the hybrid/state-space families
relevant to Slink (RTX 2070 Super 8 GB, 64 GB RAM, llama.cpp **b11146** pinned) and the Mac.
Every volatile fact below was read on 2026-10-28/30 from the linked model card, from the GGUF
header bytes of the pinned file, or from the llama.cpp release that merged support.
"Vendor" means a claim by the model's publisher that nobody has reproduced on Haven.

## What the runtime actually supports

| Support added to llama.cpp | First release | In Slink's b11146? |
|---|---|---|
| `lfm2`, `lfm2moe` (LFM2/2.5 incl. 8B-A1B, 24B-A2B) | before b11146 | yes |
| `qwen35moe` multi-token prediction (`--spec-type draft-mtp`) | before b11146 | yes, but the deployed 35B file has **no** MTP tensors (header: 40 blocks, no `nextn.*`) |
| `/v1/systemone` decision endpoint ([#29818](https://github.com/ggml-org/llama.cpp/pull/29818)) | b11361 | no |
| `--moe-cache-mib` GPU hot-expert cache | after b11146 | no |
| LFM3-1.7B / LFM3-VL-2B ([#31252](https://github.com/ggml-org/llama.cpp/pull/31252)) | b11938 | no |
| LFM3-Audio / LFM3-Omni ([#31257](https://github.com/ggml-org/llama.cpp/pull/31257)) | b11941 | no |
| d1-2B / d1-Omni-2B ([#31275](https://github.com/ggml-org/llama.cpp/pull/31275)) | b11945 | no |

Releases mapped from the llama.cpp tag list against commit history (b11146 = `7fe450e`,
b11946 = `8ca4060`). Consequence: **every LFM3-generation model needs a newer engine than
Slink runs.** The Lab now says so instead of attempting a load (see PR).

## Architectures, stated precisely

- **LFM2 / LFM2.5 / LFM3 (Liquid):** gated short-convolution blocks interleaved with grouped-query
  attention. LFM3 adds sliding-window attention (24 layers: 13 conv, 5 SWA, 6 global; header
  `lfm3.attention.sliding_window = 256`). These are **not** selective state-space (Mamba) models.
- **d1 decision models:** an LFM3 backbone run **non-causally** (`lfm3.attention.causal = false`)
  with a decision head (`lfm3.decision.type = lfm3-d1`); one forward pass, zero output tokens.
- **Qwen3.5 / Qwen3.6 (already deployed):** hybrid linear-attention (Gated DeltaNet-style
  recurrent layers, `ssm.*` keys) with full attention every 4th layer (`full_attention_interval = 4`).
- **Nemotron 3 Nano (already measured, PR #61):** Mamba-2 + attention hybrid MoE. It scored 49/110,
  so state-space layers did not by themselves buy tool competence here.
- **RWKV-7:** loadable (`rwkv7` arch in b11146), but no current small checkpoint offers a Haven role
  the families above lack. Not pursued.

## Decision matrix (top candidates only)

| Candidate | Architecture | Backend / min build | Slink / Mac fit | Role | License & training rights | Missing proof |
|---|---|---|---|---|---|---|
| **[d1-2B](https://huggingface.co/LiquidAI/d1-2B)** Q8_0, 1.85 GB | LFM3 non-causal + decision head, 1.92B | llama.cpp `/v1/systemone`, **b11945+**; Transformers (remote code) | CPU-capable: 1.9 GB RSS, 4.4 s/decision on 2 CPU threads (off-host). Fits beside the 35B without the GPU | routing, triage, guardrail, yes/no checks with confidence | LFM Open v1.0 (Apache-2.0 based; free commercial use only below $10M revenue; derivatives allowed, may stay private) | Slink run; decisions on Haven safety/tool questions; any fine-tuning path |
| **[LFM3-1.7B](https://huggingface.co/LiquidAI/LFM3-1.7B)** Q4_K_M, 1.10 GB | LFM3 tri-hybrid, 1.73B, 256K ctx | llama.cpp **b11938+** | ~2 GB RSS; 11 tok/s decode on 2 CPU threads (off-host); GPU unmeasured | fast tool-calling / extraction lane, Mac worker | LFM Open v1.0 | Haven tool suite and adjudicated suite; vendor table claims 9B-class agent scores, but PR #61 showed vendor speed and tool-task completion diverge |
| **[LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B)** Q4_K_M, 14.5 GB | LFM2 MoE, 64 experts / 4 active, ~2.45B active | `lfm2moe`, **works on b11146**; DSpark draft sidecar (664 MB) | experts in RAM like the 35B (~15 GB RAM); competes with the 35B and Strata for RAM | possible second "smart lane" | LFM Open v1.0 | everything on Haven; vendor-only comparison against Qwen3.6-35B-A3B |
| [Qwen3.6-35B-A3B **MTP** GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF) 22.7 GB | same model + 1 MTP block | `draft-mtp`, b11146 | replaces the deployed file; speed only | faster decode of the existing smart lane | Apache-2.0 | accepted-token rate with CPU-resident experts; output parity |
| [Clef / Clef-flash](https://huggingface.co/Cloudflare/clef-flash) | decision heads on Qwen3.8-27B / Qwen3.5-9B (HF card `base_model`) | Workers AI; local runtime unverified | Clef-flash 9B ≈ the 9B's footprint | decision lane alternative | Apache-2.0 (HF card) | any local runtime path |
| TypeSafe Jev | undisclosed | hosted API only | — | architectural reference for typed decisions | closed | not usable locally |

LFM3-VL/Audio/Omni-2B and d1-Omni-2B are skipped. Haven has no accepted camera or audio input path
yet ([START_HERE](../../../START_HERE.md): "not multimodal"), and video is not served by llama.cpp.

## Decisions

1. **d1-2B — trial in isolation (chosen; cataloged in this PR).** A new role, not a weaker
   generalist. Zero-shot on Haven's 36 real PR titles it tied the hand-written rules (28/36 vs
   29/36; chronological test 7/8 vs 7/8, where #83's trained head got 6/8). At #83's 0.55
   threshold its 4 abstentions were all real errors: 4 wrong answers committed plus 4 escalated,
   against 7 committed silently by rules. n = 36, sign test p = 1.0: this is a mechanism worth
   trialing, not a measured improvement. Receipt:
   `specialists/results/d1-2b-route-acceptance-20261030.json`.
2. **LFM3-1.7B — trial in isolation after the engine question is settled; not cataloged.** It loads
   on b11946 and produced a correctly parsed tool call in a single smoke prompt
   (`specialists/results/lfm3-1.7b-toolcall-smoke-20261030.json`). That is compatibility, not
   capability. It must pass the existing frozen suites before taking any role.
3. **LFM2.5-24B-A2B — defer.** It runs on the pinned engine. But it would be a third RAM-resident
   generalist competing with the deployed 35B and Strata, and its only quality evidence is the
   vendor's. Revisit only with an approved model-ownership window.

## Training suitability (does not duplicate #90)

LFM Open v1.0 permits private fine-tunes; Haven's use falls below the revenue threshold.
LFM3-1.7B is published as a single-GPU fine-tuning target (TRL notebooks on its card). The d1-2B card
offers fine-tuning only via Liquid's sales contact (no public recipe), so d1 training is
**unverified** and not proposed. A useful
d1 study needs labels Haven does not yet have: independently verified routing and escalation
outcomes from real gateway or executor receipts (#83's conclusion), never Claude or GPT outputs.
Utility hypothesis to test first: does d1's confidence predict errors on unseen Haven tasks
well enough to cut silent wrong routes? That needs **no training**, only receipts.
