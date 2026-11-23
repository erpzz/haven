# REVIEW-MM-VISION — independent research review

**ACCEPT_FOR_SYNTHESIS — exact v1 documentary design, shortlist and proposed evaluation subset.** No mandatory source amendment was identified. The promotion gates below remain attached to affected future packages; this is not implementation authorization, executed perception acceptance or native/physical qualification. Model-free public research remains unblocked.

Reviewer: `/root/ri01_review_p01`, actual `haven_research_reviewer`, 2026-09-28. Author `/root/ri01_mmvision` is distinct. The reviewer previously authored R12; its O02 reuse is checked here against current primary SAM 2 evidence, not self-certified from the earlier card. The separately labeled R12 peer check-in below is an author reflection, not independent review of R12.

Read the exact reviewer role, RI-01 authority/protocol/vision, all fourteen MM-VISION files, the relevant accepted CORE/R07/R04 and lifecycle review anchors, original selected requirement/acceptance/experiment rows, and actual consultation records. Only this assigned review file is written under the supervisor's explicit review-output permission. No author file, source code, shared registry, Git state, package, account or device is changed. No application, model, simulator or scientific test was run; no children spawned.

## Exact revision and input integrity

Reviewed `research/MM-VISION/HANDOFF_MANIFEST.json` SHA256 `8e9cdac5e012c2fa76cd27b29204158719cee95b2cc7d0663382d003d5b80703`. All thirteen listed payload SHA256 values and byte counts independently matched. All thirty-six immutable INPUT_USE records independently matched their local hashes. The mutable accepted-input index is navigation, not an immutable content pin.

The six REQ rows, six AT rows and three EX rows in REQUIREMENT_MAP.json are structurally identical to the recovered originals, including owners, expected outcomes, reviewer and unexecuted status. EX08 remains H07, EX17 H10 and EX31 H01; H08 owns the four RF requirements and H02 owns AI-07. This is a selected subset, not a replacement for CORE's full102/102/32 register. Exactly28 MV01–MV28 case rows occur in EVALUATION.md.

Important input pins independently matched:

- CORE MANIFEST.sha256 `7c0349a42c4345f68cd2e2abec6e3827a475177ff0d757509114fec05d1515e2`; CONTRACTS.md `df19f37926b33851236aca230859adfef332a85120380ea04c24294237c2e6d0`.
- R07 manifest `2db5745bfc5626f38542b1b4608e63b00458b21f4a38c1b05f2437414cf9bfc8`; contracts `9185653cdd0f24f73c7312710aae20f53d848a3fa622bcd68c17fc4489011ac3`; independent review `21b43e0196bd62144cd284c618954c3260482e0bbd111f30ed15fa76d4582815`.
- R04 contracts `985b53bab11cc9b581e3242429f73be87d41b8d4b55de2069fe64b4317d0b7a2`; independent review `4995a764b93eac91844bf1e0de8ccd1eec47c6fac64a5a58375d3fcf62db0956`.
- VISION-ARCH review `64615521c1e27c0bbc1f7e82eb919341f8493be60f2b568b08e785661f978e51` accepts CORE for downstream research while retaining VA-01 before inference.
- R12 OPPORTUNITIES.json `62c8da5aa77c78cb39af57d19cf31698033cf0e9b85a58d04b56579c7c082781`: only O02 is claimed as the routed frontier update; this use is faithful.

These hashes identify working-tree bytes. The inherited main commit is historical intake context, not a newly inspected Git ref.

## Source checks and source-fidelity conclusions

I independently consulted current primary text/license pages on2026-09-28. No model weights, executable package or third-party media was acquired. Author benchmark numbers remain reported results with their original device/task conditions.

1. **SAM2.1:** the official README supports the tiny checkpoint's38.9M parameters,91.2FPS and76.5SA-V J&F, and labels the speed environment A100/torch2.5.1/CUDA12.4. Apache2 checkpoint/code declarations and separate optional/font notices support the scoped license wording. The source has a September30 announcement and a September29 checkpoint-table date; SOURCES.md explicitly says announcement, so no chronology repair is needed. Promptable masks and streaming state do not establish personal identity or unseen temporal continuity. [SAM2 README](https://raw.githubusercontent.com/facebookresearch/sam2/main/README.md)

2. **Detection:** the v2-S640/48.1AP/217FPS T4-FP16 table and the v4-S49.8AP/3.66ms T4 table match the shortlist. The v4 release notice is2025-11-17. Apache2 repository licenses were directly checked. The author correctly avoids an end-to-end speed-ranking inference across pipelines and keeps exact checkpoints/dependencies/data open. [v2 source](https://raw.githubusercontent.com/lyuwenyu/RT-DETR/main/README.md), [v4 source](https://raw.githubusercontent.com/RT-DETRs/RT-DETRv4/main/README.md), [v4 license](https://raw.githubusercontent.com/RT-DETRs/RT-DETRv4/main/LICENSE)

3. **OCR:** the official June11,2026 PaddleOCR3.7.0 announcement explicitly includes PP-OCRv6. Keeping PP-OCRv5 as an earlier comparator is accurate. The software license is Apache2; this does not settle every model/data/backend chain. No headline improvement is claimed as Haven performance. [PaddleOCR README](https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/README.md), [license](https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/LICENSE)

4. **Grounding/tracking/retrieval:** GroundingDINO documents the Swin-T grounding candidate and Apache2 code. ByteTrack's80.3MOTA/77.3IDF1/63.1HOTA and approximately30FPS on V100 match its MOT17 reporting; MIT applies to its tracker code. OpenCLIP documents separate model/preprocessing/pretrained identities and has MIT-style code terms. These support comparator choices, not household-task validity or blanket data/weight licensing. [GroundingDINO](https://raw.githubusercontent.com/IDEA-Research/GroundingDINO/main/README.md), [ByteTrack](https://raw.githubusercontent.com/FoundationVision/ByteTrack/main/README.md), [OpenCLIP](https://raw.githubusercontent.com/mlfoundations/open_clip/main/README.md)

5. **Geometry/change:** OpenCV4.13 documentation supports camera calibration/projection and MOG2/KNN operations; the official license page confirms Apache2 for4.5+. Depth Anything V2 explicitly distinguishes Apache2 Small from noncommercial Base/Large/Giant models. Relative depth and pipeline-specific upsampling do not supply scale or calibrated covariance. [OpenCV geometry](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html), [background subtraction](https://docs.opencv.org/4.13.0/d1/dc5/tutorial_background_subtraction.html), [license](https://opencv.org/license/), [Depth Anything V2](https://raw.githubusercontent.com/DepthAnything/Depth-Anything-V2/main/README.md)

6. **Exact VLM rights:** the original Qwen2.5-VL-3B card/license is the Qwen Research License, agreement dated2024-09-19, with the defined research/evaluation restriction. Qwen3-VL-4B-Instruct's card declares Apache2. The handback correctly preserves `qwen2.5vl:3b` as the historical M4 baseline while leaving its exact redistributed/quantized artifact and conversion rights unresolved. The4B candidate is not a silent replacement. This is reporting primary terms, not adoption clearance. [Original3B license](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/raw/main/LICENSE), [4B card](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct/raw/main/README.md)

SOURCE_FETCHES.json honestly labels its hashes as UTF8 encodings of decoded responses, with originals not retained. I checked its record/content identity but did not reproduce those eleven HTTP-response hashes. They are neither immutable repository/weight pins nor independently archived source snapshots. Current claim checks above support documentary synthesis; exact artifact freezing remains required before adoption. No chart-pixel or demo-video judgment follows from parsed source text.

## Contract coherence and useful behavior

The additive profiles preserve CORE rather than create a competing authority engine:

- CONTRACTS.md:9–15 keeps original raw identity, decoded limits, pixel convention, transform/inverse mapping, information loss, native PTS, capture uncertainty and the complete transitive AuthorityVector. A selected crop does not reduce parent capture obligations. The captured vector is explicitly a snapshot that must be checked again.
- CONTRACTS.md:19–32 separates raw scores/calibration, support regions, estimator/hypothesis/generated/measurement classes and anonymous track hypotheses. Class score never becomes covariance; RGB styling never becomes thermal measurement. Geometry is only promoted through exact R07 semantics/frame/map/calibration/scale qualification. Ordinary supported appearance answers remain possible.
- CONTRACTS.md:36–42 preserves observed-at-sample versus inferred-between evidence, shared capture/dependence and uncertainty in event ordering. Neither speaker nor track IDs become a principal or health subject. R15 receives eligible overlays, not permission-bypassing geometry/counts; R04 capture/native routing and motion domains retain their own gates.
- CONTRACTS.md:46–52 uses bounded eligible pure retries, whole-output/single-destination accounting and separate historical receipts/current eligibility. Lost ACK and later revoke do not fabricate non-disclosure. Correction/deletion invalidates transitive caches, embeddings and tracks; unknown physical erasure remains unknown.

REPORT.md's MV01 and EVALUATION MV01/MV12/MV28 retain positive utility: supported region answers, real localized change and eligible search. Wrong scale/frame can deny spatial promotion while an authorized image-only answer continues (MV18/MV19). This is not a deny-everything proposal. The image follow-up and richer joint video/audio/RF/IMU scenario survive; no requirement is replaced with a still-image-only end state.

## Actual consultation and modality

CONSULTATIONS.md:9–11 accurately describes real MM-AV exchange. I read campaign consultations.jsonl records33–35: an actual question was relayed, `/root/ri01_mmav` returned native timebase/PTS/sampled-window/audio-range/clock-offset fields, and `/root/ri01_mmvision` returned the explicit between-sample unknown rule. Root independently confirmed this provenance in reply to Q-REV-MMV-01 during this review. Earlier R07/MM-FUSION consistency advice is explicitly root interpretation, not fabricated specialist acceptance. Later MM-AV independent review is not pre-approved here.

I directly viewed the full original240x120 R10 smoke PNG, hash `10468285615819f3e0946a12b149e2c67699da89002d15747856487fbd54e86f`. It shows a red square left, blue circle near the middle, and a thin black descending diagonal on white, without visible text. No crop/transform was requested. This agrees with MODALITY.json and proves only development image-viewing access. I did not inspect scientific figure pixels, audio/video, sampled frames, live cameras, physical calibration or a running Haven model. No runtime source inspection or test rerun is claimed in this review.

## Severity-ranked retained promotion gates

These are claim-specific **adoption/experiment conditions already substantially present**, not demands for another documentary revision.

**MV-G1 — MEDIUM, exact artifact and intended-use rights.** SHORTLIST.md's rights column, SOURCES S11/S12 and NEXT_PACKAGE.md:7,11 leave executable/checkpoint/runtime/preprocessing/quantization and rights chains unpinned. Before MV-P1, resolve the actual M4 artifact and admissible use; do not treat an Apache software wrapper or another Qwen size as changing original weight terms. Apply the same separation to detectors, OCR, tracker dependencies and data. Unknown rights block affected artifact use, not MV-P0 or other research.

**MV-G2 — MEDIUM, lifecycle/decoder/native containment before actual inference.** NEXT_PACKAGE.md:7–11 retains VA-01 and independently evidenced worker ownership/parent-death/lease/cancel containment. Model/delivery suppression is not termination or zero billing. Exact host memory/VRAM/SLO and decoder limits must be frozen before the pilot, rather than borrowing author GPU numbers. A device/camera/output tuple needs separate R04 evidence. This acceptance does not close the historical lifecycle finding.

**MV-G3 — MEDIUM, independent oracle and semantic utility.** EVALUATION.md:5–13 and52 requires independent protected labels, grouped splits, frozen calibration and useful-answer measures. Metadata/quote validation cannot stand in for pixel-supported relevance/entailment; positive utility is separate from zero-tolerance disclosure/measurement failures. The6/8 and3/4 gates are a small feasibility-study proposal with weak generalization, not deployment assurance. H06 must retain evaluator control before candidate execution.

**MV-G4 — LOW, freeze routes, retries and denominators together.** EVALUATION.md:52 describes the candidate family, while NEXT_PACKAGE.md:9 limits the actual next pilot to two routes and48 total attempts. That narrower cap governs MV-P1. Twenty-four groups times two routes consumes all48 first attempts; retries require a pre-results allocation change. Freeze the final split/positive denominators and any changed threshold as one version, preserve paired comparisons and never omit failed trials or count repeats as independent groups. No third route or pooled R06/R07 equivalence is implied. REPORT Acceptance correctly retains the distinct R06 E0 and R07 E07-B protocols.

**MV-G5 — MEDIUM, measured spatial/temporal and human claims stay unqualified.** CONTRACTS.md:13,26–38 and EVALUATION MV14–MV23/E-MV-C require actual support intervals, qualified scale/calibration and anonymous identity limits. Future inferred geometry must not become observed free space, an audio-only event must not become visually seen, and a track must not authorize a subject association. The corresponding metrology/native/human studies remain separate. These are scoped promotion gates, not prerequisites for a supported color/shape/text response.

## Next bounded action and disposition

Root may synthesize this exact documentary revision with MV-G1–G5 attached. The smallest next candidate is MV-P0 fixture/oracle freeze under its explicit authorization boundary; it can proceed independently of model provisioning or physical world-model qualification once authorized. MV-P1 remains a separate contained inference package. No source amendment, framework rewrite or new survey is requested.

Affected dependents: MM-FUSION temporal/support/correlation and authority seam; R15 overlays; R04 selected-media/native distinction; H02 exact model profiles; H06 evaluation; R07 geometry admission. No author or reviewer consensus beyond the actual records above is implied.

## PEER-CHECKIN-01 — R12 author reflection, separately scoped

Strongest R12 work: ten finite opportunities distinguished public evidence, artifact completeness and exact rights from qualified capability. The late neuromotor release check corrected paper-era availability/license assumptions before freezing; Text2CAD stayed backlog and R07 received only three focused updates. Weakest evidence: no candidate execution, exact host economics or physical/human outcome was measured; most external artifacts lacked immutable source-byte pins and cost dimensions remained UNKNOWN.

Useful exact peer artifact: MM-VISION CONTRACTS.md `97a6a0ab83297bbe30905d0b22b4f45bd9caf1fb7092d8f98b4eb25a27268038`, especially lines15,26 and36, makes R12 O02 operationally clearer through complete influence, anonymous-track bounds and real temporal gaps. NEXT_PACKAGE.md `7782c9f7d43a2df2c64682e9b81929cc9e3498715cb44ed5ec6b2f9ca469ece4` separates useful fixture work from model containment/rights. This is documentary reuse, not proof of implementation.

Main risk: downstream readers promote a promising model/paper or synthetic fixture into measured geometry, user identity or operational reliability. Next: retain independent R12 review conditions, freeze exact selected artifacts and approve only a bounded fixture package when desired. Confidence is high in the finite scope, source distinctions and local hash identity; medium in candidate usefulness; unestablished for runtime, cost or physical benefit. I did not inspect application/runtime code for this check-in and cannot claim such evidence.

## Exact reviewed payload hashes

```text
CONSULTATIONS.md 156b37cfc5a752ba9bf09418ce38e6f901f03b54412e5a10da89b6d6f2925ca3
CONTRACTS.md 97a6a0ab83297bbe30905d0b22b4f45bd9caf1fb7092d8f98b4eb25a27268038
EVALUATION.md bbed0c91a9aa52e96b0df7dae4c1646723b6fc6c81f404b235d3d322035d74ed
INPUT_USE.json 9c55f35506176a8fa7c6d3f56e9f48263fda12054e5fd5a522313f612bddbbb0
INTEGRATION_SUMMARY.md e0dbf2c5be66f48402638b650f8b4d916c2930c4f77926522a444e8fbab14acd
MODALITY.json bc5c625e0b6feffe3558cbfc39736b677e1d364d3e4c4ae3dffcec913f24b8a6
NEXT_PACKAGE.md 7782c9f7d43a2df2c64682e9b81929cc9e3498715cb44ed5ec6b2f9ca469ece4
REPORT.md ea6722679f82074ebd022505a3f64149fb45233eff64f6e7ac4a7de7333fbddd
REQUIREMENT_MAP.json fe8c6e6524e18146099bc5999d4d3aaa12f664d166259631cf12f915fa0124aa
SHORTLIST.md 91cdf5de90a2f87bb53a4ccb604b5d2d015db15848be20ffd814833bf30cd13e
SOURCE_FETCHES.json 34ae0c0fd57dc00e7d5a8d9f935e3eae9806c1ff197fcb3e891f83a5f9d991fe
SOURCES.md b21661413cb79b367da4aede824d770641a16337de01000003c3a3e4f7ba209c
VALIDATION.json 5c239733227ce11ef3b551d0ed6db4d076ab46f1d3715a73ab222f54221d3bdc
```

Signed `/root/ri01_review_p01` — REVIEW-MM-VISION — 2026-09-28.

