# R12 source register

Checked 2026-09-28. Primary evidence is documentation and author-reported results, not Haven execution. `SOURCES.json` is the structured register; `OPPORTUNITIES.json` binds each claim to sources, artifact edition and separate software/weights/data rights. Mutable URLs were not byte-frozen; no models or datasets were downloaded. This is a limitation, not a hash pass.

- **S01** [OpenVLA-OFT project, paper and artifact links](https://openvla-oft.github.io/). 2025 / arXiv:2502.19645. O01 architecture/released research lead; author benchmark scope only.

- **S02** [OpenVLA-OFT repository](https://github.com/moojink/openvla-oft). Mutable main README, accessed 2026-09-28. O01 MIT code declaration, inference/training resource profiles; exact checkpoint license still needs its own audit.

- **S03** [SAM 2 official repository](https://github.com/facebookresearch/sam2). SAM 2.1 release 2024-09-30; predictor update 2024-12-11. O02 image/video segmentation, per-object predictor, code/checkpoint Apache-2.0 declaration; optional component terms differ.

- **S04** [VGGT official README](https://raw.githubusercontent.com/facebookresearch/vggt/main/README.md). Current README accessed 2026-09-28; licensing update 2025-07-29. O03 camera convention, prediction outputs, code/checkpoint separation; VGGT-Omega May 2026 mention retained only as backlog.

- **S05** [VGGT exact custom license](https://raw.githubusercontent.com/facebookresearch/vggt/main/LICENSE.txt). VGGT License version July 29, 2025. O03 software terms/use restrictions; not permission for an arbitrary checkpoint or physical deployment.

- **S06** [VGGT original paper](https://arxiv.org/abs/2503.11651). arXiv:2503.11651 / CVPR 2025; exact PDF revision not frozen. O03 learned geometry paper; text/PDF available; figure rendering attempt did not expose image pixels in this tool path.

- **S07** [ActiveSplat author project](https://li-yuetao.github.io/ActiveSplat/). arXiv:2410.21955; RA-L 2025. O04 Gaussian/visibility/topological active exploration; author-described simulation/robot evidence, no video watched.

- **S08** [ActiveSplat exact license](https://raw.githubusercontent.com/Li-Yuetao/ActiveSplat/main/LICENSE). 2025 copyright; mutable main accessed 2026-09-28. O04 MIT code; dataset and dependent model rights not implied.

- **S09** [Mini Differentiable RF Digital Twin author README](https://raw.githubusercontent.com/Asixa/Mini-Differentiable-RF-Digital-Twin/main/README.md). Author citation MobiCom 2026 DOI 10.1145/3795866.3796686; mutable README. O05 minimal conceptual release, full simulator forthcoming, notebooks/backend/CUDA prerequisites; complete published performance not reproduced.

- **S10** [A-Lab original article, corrected edition](https://www.nature.com/articles/s41586-023-06734-w). Original November 29, 2023; corrected 2026. O06 autonomous materials lab and linked component/data artifacts; no assumption all artifacts share article rights.

- **S11** [A-Lab author correction](https://doi.org/10.1038/s41586-025-09992-y). January 19, 2026. O06 novelty correction, 36/40 confirmed and four inconclusive, training-contaminated compound removal; direct Nature cookie/error route supplemented by primary indexed correction text.

- **S12** [Text2CAD author repository](https://github.com/SadilKhan/Text2CAD). NeurIPS 2024 / arXiv:2409.17106; v1 artifact links. O07 sequential sketch/extrusion representation and released code/model/data links.

- **S13** [Text2CAD exact repository license](https://raw.githubusercontent.com/SadilKhan/Text2CAD/main/LICENSE). Community License, accessed 2026-09-28. O07 CC BY-NC-SA 4.0 repository terms; exact model checkpoint terms not separately established.

- **S14** [RFC 9171 Bundle Protocol version 7](https://www.rfc-editor.org/rfc/rfc9171.html). January 2022; sections 4.3.1, 5.5, 5.7 and 6.1. O08 bundle lifetime/expiry and delivery to application agent, not processing; normative source.

- **S15** [NASA/JPL ION-DTN](https://github.com/nasa-jpl/ION-DTN). Current branch inspected 2026-09-28; no immutable release selected. O08 available implementation; module maturity/platform qualification remains deployment-specific.

- **S16** [ION exact license](https://raw.githubusercontent.com/nasa-jpl/ION-DTN/current/license.txt). 2002-2011 copyright; current branch accessed 2026-09-28. O08 redistribution/attribution/non-endorsement conditions; software and RFC text rights separate.

- **S17** [A generic non-invasive neuromotor interface for human-computer interaction](https://www.nature.com/articles/s41586-025-09255-w). July 23, 2025. O09 surface-EMG deliberate motor-interface experiments; data availability distinguishes released training users from evaluation users.

- **S18** [Current generic neuromotor interface README](https://raw.githubusercontent.com/facebookresearch/generic-neuromotor-interface-data/main/README.md). Inspected 2026-09-28. Current release advertises pretrained checkpoints and 80/10/10 train/validation/test participants per task, with a subsampling/seed caveat; code/data declared CC BY-NC 4.0. This differs from earlier paper data-availability text and is preserved as an edition distinction.

- **S19** [Qwen2.5-Omni-3B exact model card](https://huggingface.co/Qwen/Qwen2.5-Omni-3B). 3B card accessed September 28, 2026. O10 qwen-research license declaration, input/output modalities and author BF16 memory table, actual-use multiplier warning.

- **S20** [Qwen2.5-Omni official README](https://raw.githubusercontent.com/QwenLM/Qwen2.5-Omni/main/README.md). arXiv:2503.20215 / 2025; mutable README. O10 architecture/runtime lead; not a rights grant for all code dependencies or guarantee of timing correctness.

- **S21** [Original OpenVLA repository](https://github.com/openvla/openvla). Public README accessed 2026-09-28. O01 inherited Llama 2 weight-license caution; code and weights distinguished.

- **S22** [Text2CAD.v1 dataset card](https://huggingface.co/datasets/SadilKhan/Text2CAD/blob/main/README.md). v1, accessed 2026-09-28. O07 dataset CC BY-NC-SA 4.0; does not resolve every upstream provenance question.

- **S23** [RFC 9713 BPv7 administrative records](https://www.rfc-editor.org/rfc/rfc9713.html). January 2025. O08 update lead identified; no new implementation requirement inferred without profile review.

- **S24** [Current neuromotor exact license](https://raw.githubusercontent.com/facebookresearch/generic-neuromotor-interface-data/main/LICENSE). Inspected 2026-09-28. CC BY-NC 4.0; applicable code/data scope differs from paper-era CC BY-NC-SA description. Exact checkpoint rights remain a separate check.

Negative access evidence: an initial CVPR VGGT PDF route returned 403; arXiv PDF text was available, but the screenshot response in this execution path exposed a reference without viewable pixels. Do not count this as figure inspection. An initial RFDT license route did not yield a license. One Nature correction URL returned a cookie/server error; indexed primary correction text and DOI identity were available. No access failure is evidence that the underlying artifact does not exist.
