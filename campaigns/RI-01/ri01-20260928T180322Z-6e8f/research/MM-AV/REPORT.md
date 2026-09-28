# Specialist handback — MM-AV v1

Thread / owner / task ID: `/root/ri01_mmav`, actual native child using the exact `haven_audio_video` role text; MM-AV, cross-cutting H01/H02/H07 with H04/H08 boundaries. Supervisor owns publication and task state. CUSTOM_PROFILE_FALLBACK: TOML sandbox intent is not effective isolation; actual filesystem permission is unrestricted and only the assigned writer prefix is authorized.

Input repository version and hashes: campaign base `376031e182c57495912baf6727093b0b188da568`, read from root's run record, not independently queried with Git. Exact working-tree inputs are hashed in INPUT_USE.json. Hard acceptance anchors verified: CORE MANIFEST.sha256 `7c0349a42c4345f68cd2e2abec6e3827a475177ff0d757509114fec05d1515e2`; R04 HASHES.json `90c2d832f126b0111d0726f75f1d8eb5f36bb040fbd82ce154a5b5e016a0eef0`; independent R04 review `4995a764b93eac91844bf1e0de8ccd1eec47c6fac64a5a58375d3fcf62db0956`.

Requirements covered: original REQ/AT identifiers retained in REQUIREMENT_MAP.json. EX03 economics, EX06 voice uncertainty/interruption and EX17 degradation replay remain PROPOSED_NOT_EXECUTED. R03 is H04, R04 is H07, R07 is H08/H05; cross-cutting MM-AV does not replace owners. All original requirements remain targets; none is declared satisfied.

Actual work performed versus proposed: public primary-source research on 2026-09-28; read/hash checks; one DIRECT_IMAGE inspection of an existing synthetic fixture; actual root-routed consultation with MM-VISION; research documents only. No application/model/SDK/device execution, package/weight download, listening, video playback, recording, private data, account, paid call, child spawning or Git. No audio/video asset was decoded. Metadata/JSON operations below are coordination checks, not application tests. Publication classification PUBLIC_SAFE; commit/PR NOT_UPLOADED by this child. Owned paths: this report directory only. Review disposition requested: independent review for synthesis, no self-approval.

## Decisions

### D1 Useful selected-media path

Preserve the accepted selected image + typed question + current authorized evidence + grounded private answer milestone. Add a deliberately selected short speech file as the next input, with an editable, source-linked transcript and explicit confirmation of task-critical names/numbers. A separately approved short clip then adds exact sampled frames, bounded acoustic-event estimates, and a timeline showing unknown gaps. Full simultaneous audio/video/sensor understanding remains the ambitious path, not a claimed consequence of the first screen.

The preferred comparison baseline is deterministic decoding/quality checks -> optional DSP -> VAD -> local ASR -> typed evidence -> scoped late fusion -> bounded reasoning -> short text answer -> optional separately synthesized whole-output speech. Lightweight models are first-class perception components. ASR text alone cannot answer prosody or acoustic-event questions. A general omni model may preserve useful acoustic/video cues, but is an escalation candidate to compare under the same evidence, rights and budget rules, not a replacement for clocks, signal processing or authority.

### D2 Speech pipeline and turn-taking

Keep an eligible original asset reference and raw digest under explicit retention; derive task-specific PCM with sample rate, channel map, gain/resample/trim offsets and decoder identity. Never overwrite original stereo with a mono derivative or drop evidence silently when denoising. Inspect clipping, silence, duration, channel polarity and incomplete decoding as quality facts; they do not establish spoken meaning. Measure ASR on raw and enhanced arms because suppression can remove consonants or non-speech events.

Push-to-talk or selected-file boundaries supply explicit turn scope first. A VAD score is speech-likelihood for a window, not end-of-thought, command intent, consent, or user identity. Proposed endpoint state: IDLE -> INPUT_ACTIVE -> POSSIBLE_END -> INPUT_CLOSED -> PROCESSING -> OUTPUT_READY, with cancellation and uncertainty orthogonal. Initial candidate settings (not measured): minimum 250 ms voiced run, 600 ms trailing silence, 300 ms pre-roll only within an already authorized session, and 30 s hard utterance cap. Tune on held-out accents, hesitation, assistive speech and double-talk; allow manual Finish and typed correction. Never silently clip the last word at a time limit; mark TRUNCATED and ask for continuation.

Later full-duplex research adds echo-reference timing, AEC and user barge-in. Preserve a raw local reference only when retain/derive authority permits; some privacy profiles should discard raw content after processing and retain only the permitted derivative with honest original-unavailable provenance. Do not imply unlimited original retention is required. Partial hypotheses are unstable and cannot issue actions or final publication. The first profile buffers a complete final answer before release; no finite-use streaming is smuggled in as a latency optimization.

### D3 Speaker, acoustic and event semantics

Diarization labels temporary speaker segments, overlaps and UNKNOWN; it does not identify a person or authenticate a command. One utterance can contain quoted instructions, a television, multiple people or playback of the assistant. Binding a command to A requires a separate authenticated, intentionally active input session and relevant scope. Ambiguous speaker or recipient results in a clarification through that person's permitted channel, not a voiceprint guess. Mouth motion cannot establish intended private content or consent.

Acoustic models return event hypotheses with intervals, scores and calibration scope. A possible alarm/crash is a cue to an authorized human-facing explanation or next-observation proposal; it is neither a guaranteed alarm nor authority for contact or dispatch. Keep false positive classes (dropped utensil, music, television, synthesized siren) and false negatives. No sound or a missing stream is not absence of danger or proof of incapacity.

Selected clips retain original PTS and time base, actual sample list and uncovered intervals. Scene change or motion scores can allocate a finite sample budget; those scores do not prove event semantics. Tracklets retain anonymous IDs and dependence across frames. A narration can say “a transient is estimated near this interval; the selected frames do not show what happened.” It cannot say “the object fell” solely because an unseen interval coincides with a sound. See CONTRACTS AV02/AV03 and the actual peer exchange.

### D4 Candidate routing, rights and economics

SOURCES.md is the primary-evidence ledger; CANDIDATES.md separates exact candidate scope, code/weight/data rights, prerequisites and cost. Default comparison: Silero VAD v6.2.3 + Whisper base/small via faster-whisper v1.2.1; tiny/base is a latency alternative, larger Whisper a quality escalation after measurement. Optional WebRTC APM, pyannote community-1 diarization, YAMNet/1 acoustic cues and Piper v1.8.0 TTS are independent modules. Availability is not installation permission. On any adopted runtime, freeze binary/weight/tokenizer/config/preprocessing hashes and supported OS/hardware, regress after changes, disable unapproved remote fetch/telemetry.

R12 O10 is accepted exactly: Qwen2.5-Omni-3B is a research/evaluation candidate, with restricted weight terms and author-reported BF16/FlashAttention2 video memory figures; no generic permissive or host-fit conclusion. M4 `qwen2.5vl:3b` remains unchanged. Hosted STT/TTS remains a separately eligible comparator only after cloud-transmit/provider-policy/billing approval; cheaper batch processing has a different latency use case. No new provider spend occurred. Session allowance, research labor and energy are not free or metered here.

Proposed resource routing: one inference job at a time, deterministic status/cancel/receipt lane reserved for both principals; no model may starve the second user. Reserve decode bytes, selected seconds/frames, worst-case model tokens, peak RAM/VRAM and all attempts before admission. Record cold/warm p50/p95, real-time factor (processing/audio duration), joules or explicit UNKNOWN, and cost per independently accepted task including retries and review. Do not compare local wall time to hosted token-only cost. Stop budget consumption conservatively when provider completion/usage is unknown; cancellation is not a refund.

### D5 Wearables, accessibility and deliberate private communication

R04's exact native phone/Watch/glasses tuples remain unknown independently for A and B. Start phone-selected imports; future microphone/camera capture requires separate native permission and participant/area scope. HealthKit read consent is intentionally opaque; Haven's own withdrawal changes eligibility directly, while OS Settings withdrawal can have uncertain observation timing. Do not use audio/face matching to associate health with a speaker.

Private audio route loss pauses playback and fences new release; it never falls back to speaker. Headphones/glasses do not prove privacy: leakage, proximity, borrowed devices and wearer changes require an explicit route/audience policy. Separate current route, historical playback report and actual human comprehension. Watch haptics require R04's foreground/workout qualification and can interrupt heart-rate acquisition. Meta DAT 1.0.0 experimental speech/synchronized audio features remain nonpublishable under the reviewed release boundary; version pin alone is not compatibility or deployment proof.

Provide editable captions, text alternatives, large readable controls, optional pace/repeat, keyboard/switch input and visible quiet mode. Do not require hearing, clear speech or color to stop output. Every cue has a plain-language meaning and an accessible equivalent; optional acknowledgement reports an intentional UI action, not comprehension. Deliberate two-user communication starts with explicit recipient choice, typed/preset message and private text/cue. Whispered speech, lip movement and biosignals are not mind reading; no voice cloning is proposed. Haptics and notification timing can disclose sensitive activity and need the same current audience treatment as words.

### D6 Five retained journeys and ambitious scenario

Daily: A selects a spoken project note, corrects a name and receives a short private, cited summary; B's independent request stays responsive. Image follow-up: A selects a workshop still and asks which item was described in a speech note; ambiguous repeated objects get region choices, not fabricated identity. Incident replay: a permitted clip, acoustic cue and delayed synthetic sensor interval appear on one timeline with uncertainty; no current-condition claim from historical evidence. Regional Observatory: licensed public clip/caption and time-stamped regional readings can support a public field summary, with no private household or identified-bystander material. Engineering: replay a failed candidate's authorized selected inspection clip; retain the failed result and require independent dimensional evidence rather than inferring tolerances from sound or pixels.

The richer scenario is an offline, synthetic workshop replay: two independently scoped users, video of a moving object, separate audio with a transient and speech, IMU history and a delayed Watch-like synthetic value. A asks what changed while B receives their own unrelated answer. With calibrated clocks, compare modular late fusion with one qualified omni model, removing streams, adding drift, revoking a parent and interrupting output. Show observations, hypotheses, temporal conflicts and unknowns together. Neither audio/video association nor model agreement attaches B's health to A, proves causation, authorizes motion, or turns a simulated value into a measurement. This preserves V01–V16 without claiming a runtime exists.

## Evidence

Primary URLs, editions, findings and limits are in SOURCES.md; volatile claims checked 2026-09-28. Web responses were not archived as immutable files; URL/tag/card and access date are anchors, not hashes of remote bytes. No figures/charts were visually inspected for numerical claims; reported values come from source text tables. Exact local read/usage hashes are in INPUT_USE.json. All external performance is source-reported, not Haven execution.

I directly viewed whole `inputs/runtime/synthetic-vision-probe.png` using `view_image`: a red filled rectangle on the left, blue filled circle on the right, separated on a pale background. SHA256 `12a1ed92fe078247281f01f05edbde362110a562cd759e2f8f7f7244bd66e837`; original 360x180 campaign-authored fixture, no transforms. It proves this child's static image tool path only. I did not listen to, play or inspect a waveform of audio or view temporal video. MODALITY.json records those limits.

## Interface changes

Propose `ri01.proposed.mmav.v1` AV01 MediaDerivation, AV02 TemporalSupport, AV03 PerceptionClaim, AV04 InteractionAndStop and AV05 OutputProfile extensions. CONTRACTS.md defines fields, errors, retries, bounds, current authority and cancellation without editing CORE. Reuse full I01–I07; retain all influencing parents, including uncited context. Source correction invalidates transcripts, waveforms, frames, event claims, embeddings, cached speech and pending outputs. Old outputs retain historical receipts and cannot become current authority.

## Acceptance

Only the image smoke and input integrity/JSON checks were executed. The 32 evaluation families and positive progression in EVALUATION.md are all proposed. No direct audio/video or native device test passed, and no model was qualified. A reviewer must check usefulness and grounding as well as strict authority boundaries; aggregate accuracy cannot offset a privacy/authority escape. SOURCE_AVAILABLE, fixture consistency, software execution, model task quality and native qualification remain different gates.

## Risks and open questions

Highest risks: silent timestamp shifts after preprocessing; unsupported identity association; VAD treating hesitations as turn ends; hallucinated silence transcripts; false acoustic alarms; stale final speech; mistaken private route; duplicate consumption after lost ACK; and treating a model's streaming capability as an accepted release profile. Device tuples, model host fit, per-voice rights and direct listening/evaluation are unresolved. These block runtime/native promotion, not this documentation package. R07 is a soft accepted contract input; MM-VISION's report was still in progress and only the attributed consultation is consumed. No fictional reviewer agreement is recorded.

## Next package

P-MMAV-01 in NEXT_PACKAGE.md: separately authorized inert temporal/authority fixture adapter, no models or devices, then distinct inference and endpoint qualification gates. Status AUTHORIZATION_REQUIRED. Do not execute merely because this handback exists.
