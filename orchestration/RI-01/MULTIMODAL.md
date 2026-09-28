# Multimodal suite — required design and honest review capability

The user explicitly requires visual recognition and a full multimodal system, not just language models. Cover BOTH the development agents' ability to inspect evidence and Haven's eventual input/output architecture. These are separate capability matrices.

## A. What the research agents actually inspect
At preflight record, for the root and relevant children: text/code reading; image viewing; PDF pages/figures; browser screenshots; video playback or sampled-frame inspection; audio listening or audio-model access; waveforms/spectrograms; spatial data inspection; available transforms; supported generation/output tools. Record model/tool/version only when actually exposed. An unsupported modality is TOOL_UNAVAILABLE, not an inferred capability from the model name.

Every inspection record contains asset ID, source URL or repository path, version/hash, permission/license, inspection mode, exact page/frame/time/region, original and derived relationship, tool, observations, uncertainty and limitations. Modes include DIRECT_IMAGE, PDF_PAGE_IMAGE, DIRECT_AUDIO, DIRECT_VIDEO, SAMPLED_VIDEO_FRAMES, TRANSCRIPT_ONLY, WAVEFORM_ONLY, METADATA_ONLY and DOCUMENTATION_ONLY. Never silently upgrade one mode into another.

For a paper's diagram or chart, inspect the figure when it supports the claim; parsed text alone is not figure inspection. For video, record sampling cadence and uncovered intervals. A sequence of stills cannot establish events between frames. A transcript cannot establish prosody, non-speech sounds, speaker identity or exact timing. A spectrogram is not equivalent to listening. Rendering a geometry file is not structural validation. Vision/OCR errors need task-specific checks.

Use existing approved tools, small eligible public or synthetic examples and bounded preprocessing. Do not install codecs/models, enable microphones/cameras, collect partner signals or initiate paid calls. If a child's tool cannot render an asset but the parent's can, the parent may provide a derived inspection packet; preserve who inspected it and do not let the child claim direct observation. Images and other rich evidence should be passed through native attachment/tool channels, not hidden as enormous base64 strings in chat context.

Perform a benign image-input smoke check if supported. It tests the development workflow only, not Haven's runtime. Audio/video unavailable in this Codex session does not block literature and interface research, but remains an explicit executed-testing gap. Do not claim a full multimodal runtime was built by adding role descriptions.

## B. Haven input capabilities to design

| Family | Required scope | Useful efficient methods to compare |
|---|---|---|
| Text, code and documents | Conversation, exact lookup, structured extraction, diagram/document context and grounded synthesis | Ordinary code/retrieval, small models, stronger reasoning only when needed |
| Images and visual recognition | Objects/scenes, localization/segmentation, temporary anonymous tracks, visual changes, task-specific labels/text, workshop inspection and accessibility descriptions | Classical CV, detectors/segmenters, geometry tools, selected-frame VLM; compare standalone task models with general VLMs |
| Video and events | Clip summaries, temporal localization, motion/tracking, occlusion, event order and uncertainty in sampled intervals | Event-triggered capture, lightweight tracking, bounded temporal models, VLM interpretation of selected evidence |
| Speech and other audio | Push-to-talk, ASR, turn-taking, diarization without identity claims, acoustic-event cues, non-speech sounds, playback/interrupt behavior | VAD/DSP, local ASR/TTS, qualified audio models, optional native speech-to-speech |
| Spatial and 3D | Depth/pose/SLAM candidates, point clouds, occupancy/support masks, coordinate frames, geospatial layers and uncertainty-aware world-model queries | Geometry/estimation first; learned depth/pose where qualified; scene graphs for explanation |
| RF and telemetry | CSI/RSSI/ranging/radar, clocks, IMU/location/device state, confidence/calibration and events | Signal processing and calibrated estimators; do not feed arbitrary raw signals to a text model as a substitute |
| Health-adjacent and biosignals | Consented timestamped Watch measurements and later muscle/eye/neural-interface research | Platform permission checks, quality/freshness filters and qualified specific models; no diagnostic claim or mind reading |

Distinguish a tool's software license, a model's weight license, training-data access, dataset reuse and hosted-service billing. Compare task-specific local models with multimodal general models using exact task, artifact, quantization, runtime and preprocessing. Do not download model candidates in this campaign. R02's existing M4 image baseline stays unchanged unless a later explicit package revises it.

## C. Output and action channels
Cover text, structured data and source-linked answers; low-latency speech; explanatory plots/diagrams; scene overlays and AR; maps/3D/time-series displays; deliberate private haptic cues; and typed digital/physical proposals. Generated imagery/video is an illustration or design hypothesis, never substituted for camera evidence. Anonymous tracking within a qualified task is not personal identification. Audio matching is not authentication. A haptic warning is not a clinically validated or guaranteed safety alert.

Output devices have an audience: headphones/glasses, shared wall display, phone lock screen and exported link have different disclosure risks. Review before publication and cancel stale output. 'Stop talking', 'cancel reasoning', 'cancel queued reminder' and 'request physical recovery' remain different commands with different observed outcomes.

## D. Cross-modal architecture
Design: acquisition/permission -> source/time/frame/quality normalization -> specialized perception -> typed evidence and uncertainty -> scoped retrieval/fusion -> reasoning/proposal -> publication/domain authority -> observed outcome. Retain the original artifact and typed derived claims; do not collapse everything into untraceable prose. Long videos, raw RF and every telemetry sample need not enter a frontier-model context.

Specify original capture, receipt and processing times; clock uncertainty; coordinate frame and altitude datum; calibration; unit conventions; missing/stale/ambiguous state; modality-specific confidence and validated meaning; source dependencies; correction/revocation lineage; budgets and cancellation. Related modalities may share the same source, so combining them must not double-count independent evidence. A caption and its original frame are not two independent witnesses.

Compare early versus late fusion where relevant, with a small late-fusion typed baseline first. Missing modalities should degrade explicitly, not force fabricated agreement. Correlation does not prove causality. A wrong visual object association must not attach another person's health readings or authorize a robot. Surface contradictions and ask for a permitted additional observation where useful.

Multimodal memory retrieves only authorized current source revisions. Store raw assets in appropriate storage and references/indices in the existing application where sufficient; no mandatory vector database or broker. Plan future embedding search only after evaluating lexical/metadata/geometry alternatives and permission filtering. Corrections invalidate derived embeddings/summaries/caches as well as text answers.

## E. Required research outputs
MM-VISION: visual perception architecture, detection/segmentation/tracking/geometry shortlist, current primary evidence, latency/resource/quality measures, failure set and R07/R15 integration.
MM-AV: speech/audio/video architecture, task-specific model/runtime options, synchronization/interrupt protocol, actual tool availability, noise/ambiguity/temporal tests and wearable integration.
MM-FUSION: joint modality registry, minimal evidence contracts, input/output architecture, correlated/conflicting evidence handling, retention/privacy, cost routing and cross-modal evaluation plan. Consume MM-VISION, MM-AV and actual R02/R03/R04/R07 results.

Each includes low-cost/local paths and stronger escalation candidates, explicit claims the system must not make, runtime/installation prerequisites and one bounded next implementation proposal. No universal claim that one VLM replaces signal processing, geometry, recognition and clinical evidence.

## F. Minimum evaluation coverage
Propose at least 24 cases spanning low light, small/occluded objects, visual text errors, repeated objects, instruction injection in images/audio, stale images, false thermal appearance, missed between-frame events, audio/video desynchronization, noise/accents/names/numbers, ambiguous speaker/recipient, cancelled playback, false acoustic alarms, wrong coordinate frame, missing calibration, RF silence, sensor drift, modality outage, cross-user association, revoked shared source, derived-cache invalidation, generated-as-observed confusion, and per-user resource contention.

Use synthetic/licensed inputs and frozen ground truth where possible, with modality-qualified human evaluation when appropriate. Distinguish source-derived expectations from actually executed results. No aggregate answer score overrides an unauthorized disclosure, physical-command escape or false claim of measured evidence. Report the smallest useful next milestone: selected image + typed question + current authorized evidence + grounded answer, then speech/clip/telemetry additions under separate approval. Include a richer simultaneous scene/video/audio/sensor research scenario without pretending the first milestone implements it.
