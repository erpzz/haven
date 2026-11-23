# REVIEW-R12 — accepted for synthesis

Actual independent reviewer: `/root/ri01_review_privacy`, `haven_research_reviewer`, 2026-09-28. Author: `/root/ri01_review_p01`. Root persisted this substantive record from the actual review handback; it is a structured transcription, not a new root review or claimed verbatim transcript.

**ACCEPT_FOR_SYNTHESIS. No mandatory author amendment.** This is a bounded public-research opportunity packet, not experimental reproduction, model adoption, licensing clearance or implementation permission.

## Scope and integrity

Reviewed all nine R12 files, eight manifest entries and eleven hash-pinned local inputs. All hashes matched. Original 102 requirement and 32 experiment references were valid. Ten opportunity cards, 24 primary sources and seven areas are represented; routing respects the maximum three updates per downstream task. Full exact output pins are retained in `research/R12/HANDOFF_MANIFEST.json` (SHA256 `fec9c4c223fa2370db6bcbe8fd61980d284d92a31a22b37d707dcd48db0a8d77`). REPORT SHA256 `7f47f9672dd4441bc38c336374958910ff1b2b096381c530a8a3517c20032af5`; INPUT_USE `3c063b11e64f5e64d3f6ca7476c5819fe90c73520de34cc59056dea55c188cf5`.

The routed updates are O01 OpenVLA-OFT to R09; O02 SAM2 to MM-VISION; O03 VGGT, O04 ActiveSplat and O05 RFDT to R07; O05 also to R06; O06 A-Lab correction to R08 and R13; O07 Text2CAD backlog only; O08 BPv7 to R11; O09 neuromotor interfaces to R04 and R14; O10 Qwen Omni 3B to MM-AV and R02. These are research inputs, not a requirement to adopt the candidate.

## Findings

**L01 — source-index completeness, nonblocking.** The structured source mappings omit O01/S21 inherited-weight terms, O07/S22 dataset terms and O08/S23 RFC9713 edition. The sources already exist in the registers. Carry their explicit opportunity-to-source mappings into the final SOURCE_USE_INDEX rather than silently rewriting the immutable R12 packet.

**L02 — preserve exact resource and license conditions.** The Qwen Omni 3B memory table is for Transformers, BF16 and FlashAttention2. Its research license permits noncommercial research/evaluation; commercial use requires a requested license. A generic research-license label or unqualified memory number is insufficient for adoption. Exact future model/artifact selection remains a separate gate.

## Primary-source checks and corrections

- VGGT's current code license changed in July 2025; distinguish the original noncommercial checkpoint and gated commercial checkpoint. Its camera convention is camera-from-world OpenCV. Learned confidence is not covariance or measured metric scale. [Author README](https://raw.githubusercontent.com/facebookresearch/vggt/main/README.md), [license](https://raw.githubusercontent.com/facebookresearch/vggt/main/LICENSE.txt).
- Qwen2.5-Omni-3B uses `qwen-research`. Published theoretical memory for 15/30/60-second video is 18.38/22.43/28.22 GB under the specified configuration; the model card says actual use is typically at least 1.2 times theoretical. These are source claims, not measurements on this PC. [Model card](https://huggingface.co/Qwen/Qwen2.5-Omni-3B), [exact license](https://huggingface.co/Qwen/Qwen2.5-Omni-3B/blob/main/LICENSE).
- A-Lab's 19 January 2026 correction distinguishes new-to-platform from new-to-science. Post-publication review confirmed 36 of 40 reported successes and left four inconclusive; one training-included compound was removed. The publisher PDF/indexed primary text was inspected; direct Nature page opening failed. This closes the earlier REV-R08 source-access limitation for the numerical correction, but is not independent laboratory reproduction. [Publisher correction](https://www.nature.com/articles/s41586-025-09992-y).
- The current neuromotor author repository supplies pretrained checkpoints, an 80/10/10 user split per task and subsampling/seed qualifications. Current README/license state CC BY-NC 4.0; the original paper's training-user release described CC BY-NC-SA. Preserve that edition difference. Exact checkpoint terms remain unresolved. Neither a full paper reproduction, thought reading nor access to owned equipment follows. [README](https://raw.githubusercontent.com/facebookresearch/generic-neuromotor-interface-data/main/README.md), [license](https://raw.githubusercontent.com/facebookresearch/generic-neuromotor-interface-data/main/LICENSE), [paper](https://doi.org/10.1038/s41586-025-09255-w).
- RFDT's author release describes a minimal conceptual demo, with the full simulator forthcoming. Five notebooks use RayD/DrJit and a separate Mitsuba branch, Python 3.10+ and CUDA. This is not a full reproducible release, proof of geometry identifiability or blanket reuse permission. [Author README](https://raw.githubusercontent.com/Asixa/Mini-Differentiable-RF-Digital-Twin/main/README.md).
- BPv7 application-agent delivery is not application processing and does not guarantee delivery. RFC9713 updates the administrative registry; it does not create a human receipt. ION terms require notices, disclaimer and nonendorsement. [RFC9171 section 5.7](https://www.rfc-editor.org/rfc/rfc9171.html#section-5.7), [RFC9713](https://www.rfc-editor.org/rfc/rfc9713.html), [ION license](https://raw.githubusercontent.com/nasa-jpl/ION-DTN/current/license.txt).
- Proportionate checks retained OpenVLA-OFT's MIT code versus inherited Llama2 weight terms and author-reported 16/18 GB figures; SAM2's Apache2 code/checkpoints versus separate component notices and per-object tracking; ActiveSplat's MIT author robot demonstration; and Text2CAD's CC BY-NC-SA repository/dataset with exact weight terms unresolved. No experiment was reproduced.

## Useful next experiment and limits

R12-P01 proposes synthetic geometry/provenance/next-view evaluation: 20 cases plus four separate evaluator mutations, canonical SE3, unknown metrology, source-correlation controls and a total 60-second/eight-attempt bound. No model is required. The owner must freeze the exact adapter before separately authorized coding. The 60-minute documentary entry and 90-minute implementation plus 30-minute review are different proposed stages; none is an observed duration or expenditure.

Checks were document reading, hashing, web-source reading and direct inspection of the already available synthetic image. No application, model, audio/video, sensor or physical experiment ran; no additional media was acquired. Direct image access is a tool smoke observation, not Haven perception qualification. Mutable external pages were not byte-frozen; pin exact selected artifacts before adoption. Current M0/R1 code remains unavailable to this research review and does not block its bounded documentary conclusion.

Reviewer identity and actual conclusion: `/root/ri01_review_privacy`, ACCEPT_FOR_SYNTHESIS, 2026-09-28.
