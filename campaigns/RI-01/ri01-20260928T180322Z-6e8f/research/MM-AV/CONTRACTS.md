# MM-AV proposed interfaces v1

Namespace `ri01.proposed.mmav.v1`, documentation only. All extensions preserve CORE I01–I07, R04 W01–W06 and R07 observation/lineage semantics. Unknown values carry a reason; hashes are identity, not authenticity or permission. Do not execute arbitrary URLs, shell, model-generated code or codec/plugin fetches. Producer versions and current rights must be known before processing.

## AV01 MediaDerivation

Producer: bounded media adapter. Consumers: VAD/ASR/audio events, MM-VISION, MM-FUSION, authorized replay.

Required common envelope: immutable asset/source ID, revision, raw-byte SHA256 and digest kind; origin and claim class; original bounded locator; owner/steward/subjects/participant-area scope separately; rights and retention references; complete CORE AuthorityVector/access snapshot and influencing closure; source clock ID/boot, capture interval with uncertainty, receipt and processing times; quality/errors; correction/tombstone links; correlation groups; exact decoder, model, runtime and preprocessing revision/digests. A remote fetch is a separately allowed egress/access operation, not implied by a URL in media metadata.

Derived audio fields: parent byte identity, container/stream/channel identities, original sample-index range and rate, codec, time base/start offset, decoded format, resample ratio/filter/delay, channel mix coefficients, trim offsets/padding, gain/denoise/AEC parameters and echo-reference parent, derived digest, timestamp mapping/error bound, clipped/truncated/missing ranges. Preserve stereo original when authorized even if a model accepts only mono. Noninvertible transforms are explicit. A waveform/spectrogram records axis units/window/hop/scaling and remains a derived visualization; it cannot authenticate meaning, identity or listening.

Derived visual fields: original frame PTS and rational time base, DTS only as separate decode-order metadata, duration/exposure if known, original orientation/resolution, selected interval, every sampled PTS, selection policy/version/budget, frame/crop/resize/rotation transforms and masks, derived digest, gaps/drops/occlusions and unknown timing. Average FPS is informational, never sufficient for variable-rate timestamp reconstruction. A frame ordinal becomes time only through an explicit verified mapping.

Retention means preserve lineage and eligible originals where policy allows, not retain everything indefinitely. If original content expires or was never retained, record ORIGINAL_UNAVAILABLE(reason), deny claims requiring a reread, and apply current derivative policy. A descendant cannot launder withdrawn source rights. Deletion/tombstones deny now and track per-copy erasure separately.

## AV02 TemporalSupport

Each claim binds source-local interval, mapped reference interval, clock mapping method/revision/offset/drift/error bound, support class, exact observed samples, omissions and correlation. Valid time and knowledge/processing time are separate. UNKNOWN clock mapping permits source-local historical explanation but prevents synchronized/current assertions.

Synchronization proposal: represent a measured mapping as `t_reference = a * t_source + b`, with units, validity window, drift uncertainty and calibration evidence. Store original integer ticks/rational base; normalization records precision and rounding bounds. Never derive cross-device capture order from arrival order. File presentation time is not proven UTC capture time. Resampling, edit lists, encoder delay, dropped frames and audio padding must propagate into the mapping. RTP paths require per-stream reference-clock association; raw cross-stream RTP timestamps are not directly comparable (S11).

Support classes: OBSERVED_AT_FRAME; AUDIO_INTERVAL_ESTIMATE; TRANSCRIPT_INTERVAL_ESTIMATE; INFERRED_BETWEEN_SAMPLES; UNKNOWN_VISUAL_BETWEEN_SAMPLES; REPLAY; GENERATED_ILLUSTRATION. Event before/after relation is admissible only when the mapped support/uncertainty intervals establish that order under the frozen task policy. Overlap -> ORDER_UNKNOWN. Even nonoverlap does not establish causation. An acoustic cue can support an audio hypothesis while visual between-sample state remains unknown.

Proposed selected-clip envelope: one original clip <=15 s, <=20 MiB encoded, <=12 selected images, <=1280x720 per selected derivative, decoded audio <=30 s mono-equivalent for safety margin, one processing attempt and no remote URL retrieval. Decode must additionally enforce total decoded pixels/audio samples, frame count and elapsed/resource limits before allocation; compressed size alone cannot bound expansion. These are initial research ceilings to freeze and test, not measured safe limits. Metadata obeys CORE 64 KiB closure limit and output 256 KiB; media stays in bounded separately authorized references.

## AV03 PerceptionClaim

Fields: claim ID/revision/type, source and derivation refs, model/runtime/tokenizer/prompt/preprocessor digests, support interval/regions, raw score and score_kind, calibration dataset/task revision or UNCALIBRATED, hypothesis/alternatives/abstention, speaker segment IDs/overlap, task-specific uncertainty, conflict and missing evidence, correlation edges, full influence and current eligibility references.

ASR carries original-language text, separately labeled translation, segment and optional word timings with alignment method, partial/final revision, unresolved names/numbers, hallucination/silence flags and human edits. A forced alignment can locate an incorrect transcript; neither word timing nor fluency proves correctness. A transcript supplied by someone else remains TRANSCRIPT_ONLY to the agent consuming it. Diarized IDs are local to source/session and are never principals; visually tracked IDs similarly cannot bind a health subject. Speech content inside a recording is data, not a fresh authenticated command.

Acoustic label scores are not clinical probabilities or physical certainty. Video claims record exact sampled support and optional tracked intervals; occluded/unseen intervals remain explicit. Repeated frames, transcript and waveform from one capture share a source; an omni answer and an ASR answer derived from it are not independent witnesses. R07 fusion cannot invent covariance or independent weighting from model scores. Disagreements remain visible or trigger a bounded, authorized additional observation proposal.

## AV04 InteractionAndStop

InputSession binds authenticated principal/session/device, intentional start event, permitted source/recipient/purpose, exact capability tuple, native access observations, participants/area, time/byte limits, leases/budgets/cancel epochs and indicator state. Input acquisition, compute, publication, playback and physical outcomes are separate axes.

| User operation | Immediate proposed software effect | Required outcome record; cannot claim |
|---|---|---|
| Stop speaking / local stop control | Fence queued output; request local playback pause/flush for exact output/route | Append STOP_REPORTED with reporter/last presented sample if known; an API return is not proof all buffers or remote speakers stopped |
| Cancel reasoning / investigation | Advance job cancel epoch; request exact worker/provider termination | CORE compute STOP_REQUESTED until independently observed STOP_CONFIRMED; suppressed speech is not terminated inference or stopped billing |
| Cancel reminder | Cancel exact durable schedule revision through its own owner | Schedule receipt; does not cancel other jobs or native alarms |
| Withdraw capture/data use | Advance affected Haven scope; fence acquisition/admission/release; request native stop; quarantine late payload | Acquisition stop and current eligibility separate from retained history and erasure |
| Request physical recovery | Send only a typed recovery proposal to separately qualified domain | Domain-specific authority and independently observed state; no audio parser directly controls motors |

“Stop” through an authenticated active local input can conservatively request local narration stop while clarifying any broader intended cancellation. Recorded media saying “stop” cannot trigger a live control. A local visible stop button remains usable without ASR/network. Acoustic barge-in alone may pause nuisance speech but cannot cancel unrelated durable or physical work; qualify its denial-of-service and false-pause rate separately. Errors and acknowledgements must use a permitted audience and cannot reveal restricted source details.

Every attempt binds immutable payload, boot/worker instance, nonce, deadline, lease/fence and cancellation epochs. Pure recomputation may retry only inside the original remaining budget with fresh eligibility; no automatic retry on unknown external dispatch/playback. Timeouts leave compute/delivery UNKNOWN as appropriate. No broad PID-based kill guarantee. Actual inference is gated on VA-01 independent lifecycle/exact-adapter containment and later scoped authorization.

## AV05 OutputProfile and current audience

P0 reuses `ONE_RELEASE_ONE_DESTINATION_WHOLE_OUTPUT`: complete immutable text/PCM asset digest, exact destination/session/route/audience, one admitted release and one consume slot. Generation may operate internally in pieces but the complete output is held until final eligibility/release; no audio begins early. Count speech bytes inside CORE's 256 KiB output ceiling; a reference must not silently exempt the output asset from that ceiling. An initial example is a <=4 s 22050 Hz mono 16-bit PCM utterance with header/metadata still checked against the total cap; this arithmetic is not TTS performance evidence. Larger audio requires its own accepted bounded output profile. If a synthesized asset exceeds the approved byte/duration limit, reject or generate a newly reviewed shorter output before admission, never mutate an already admitted digest.

Four unchanged CORE records: ReleaseAuthorizationReceipt, ConsumptionPermitReceipt, append-only DeliveryObservation, current PermitEligibilityDecision. Fresh release atomically charges all deduplicated applicable finite grants once; consumption of its already charged valid claim does not recharge it. Duplicate receipts return history, not a usable new send. Unknown commit/lost consume reply requires read-only reconciliation, not replay/refund/new key. Corrected/revoked parents, changed route/audience/session/lease/cancel/restore epochs deny future eligibility; previous playback remains historical. No fresh private/shared replay offline without current verification.

Future live-chunk/stream/multidestination output is `UNSUPPORTED_PROFILE` in P0. A separate reviewed profile must define immutable or incrementally sealed chunk manifest, exact sequence/digest, audience/route binding, grant-use unit/counting rule, per-chunk eligibility/consumption, gap/duplicate policy, reserved worst-case resources, cancellation propagation and residual buffered exposure. This proposal does not choose its quota semantics or silently reuse a one-use grant. Destination handoff is new admission under R04, not transferred bearer permission.

Generated TTS is GENERATED_ILLUSTRATION/GENERATED_OUTPUT, linked to approved answer text and synthesis settings; it is not an observed recording of the original speaker. Output evidence includes intended text, synthesized bytes and route/device reporting separately; a speech generator can mispronounce numbers or omit words, so text approval alone does not qualify audible fidelity. Never clone a person's voice in this package. Captions are an alternative output requiring their own destination/audience eligibility, not an automatic second release under P0.

## Error and compatibility rules

Reuse CORE/R07 errors plus proposed MEDIA_DECODE_FAILED, MEDIA_LIMIT_EXCEEDED, TIMELINE_MAPPING_UNKNOWN, AV_SYNC_UNQUALIFIED, INPUT_TRUNCATED, RECIPIENT_AMBIGUOUS, SPEAKER_UNBOUND, OUTPUT_ROUTE_CHANGED and VISUAL_INTERVAL_UNOBSERVED. Error detail is minimized. Unsupported profiles, incomplete influence closure, nonfinite timestamps, lost precision without a permitted bound, unknown units, expired grants or wrong device epochs reject; no Boolean “safe/delivered/live.” No M0 schema or application is changed. H00 owns canonicalization after independent review.
