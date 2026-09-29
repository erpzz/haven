# REVIEW-R04 — independent wearable research review

**ACCEPT_FOR_SYNTHESIS — bounded documentation, contract and experiment-design subset.** No mandatory source amendment was identified. The promotion conditions below remain mandatory before the affected implementation or native claim; this is not operator authorization, executed acceptance or clinical/device qualification.

Reviewer `/root/ri01_evidence`, acting `haven_research_reviewer`, 2026-09-28. Author `/root/ri01_privacy` is distinct. I reread the exact role profile and applied the RI-01 scope already read in this session. The supervisor explicitly assigned this review-output path; only this review was written. No source artifact, Git state, application code, package, account or device was changed. No children were used. **Zero application, native, SDK, simulator or physical tests executed.**

## Exact scope and integrity

Read all eleven files in `research/R04`, relevant CORE I01/I02/I06/I07 and architecture, R01 amendment and independent closure, original wearable acceptance/experiment records, and the prior REVIEW-R10 transcription. All ten HASHES-listed content files match their bytes/SHA256; HASHES.json itself matches the supplied digest. All eighteen INPUT_USE local hashes independently match. The base commit is reported context; the working-tree artifact hashes identify the actual reviewed content, as INPUT_USE explicitly states.

Hard inputs were used faithfully: CORE architecture `abf33854c793fc58c6e6679348a34d546abe5051bdfd6d91978e24b75449eb82`, contracts `df19f37926b33851236aca230859adfef332a85120380ea04c24294237c2e6d0`; R01 report `e515ada3259cfe6a56a9c8b9ac7e09ff2c00a1b90a5f4ca8fa7455328cb66283`, amendment `0f1acb6fb6dbcd9d1a39a39d083275a82eb57e56175f71c235ab99e385c56535`, closure `96687ff8643ea960aa275855160a4124d0925e933ebdefdd9c4e8031f4ac9032`. I independently checked VISION-ARCH's actual acceptance and VA-01 distinction; its review hash is `64615521c1e27c0bbc1f7e82eb919341f8493be60f2b568b08e785661f978e51`. Downstream research is accepted, but P03 inference lifecycle/containment closure remains a later prerequisite.

The two author consultations are accurately qualified: no verified owned tuple was supplied; finite-profile advice is the supervisor's interpretation, not a newly invented CORE-author answer. R12 O09 remains a limited research input, not consumer EMG support.

## Independently checked primary claims

Checks used public text and official indexed excerpts on 2026-09-28. Sparse Apple JavaScript pages required official search extracts. Mutable response bytes were not archived or hashed; editions, sections and URLs are reproducibility anchors, not immutable web snapshots.

- **HealthKit:** Apple explicitly withholds whether read access was granted or denied. `authorizationStatus(for:)` concerns saving/sharing, not a reliable read-grant bit. Restricted-window visibility does not distinguish full access from denial. W02 accurately preserves this uncertainty and leaves the new window API's minimum OS unresolved. [Authorization](https://developer.apple.com/documentation/healthkit/authorizing-access-to-health-data), [authorization status](https://developer.apple.com/documentation/healthkit/hkauthorizationstatus).
- **Background and haptics:** background delivery is scheduled with maximum update frequency and requires the entitlement from iOS 15/watchOS 8. It is not guaranteed continuous sampling. Watch haptics normally do not run in inactive/background states, except the documented workout case, and interrupt HealthKit heart-rate gathering. These limits support R04's separated sensing/cue qualification. [Background delivery](https://developer.apple.com/documentation/healthkit/hkhealthstore/enablebackgrounddelivery(for:frequency:withcompletion:)), [haptic playback](https://developer.apple.com/documentation/watchkit/wkinterfacedevice/play(_:)).
- **Meta DAT:** both official changelogs show 1.0.0 dated 2026-09-24 and explicitly restrict publication of apps using experimental features. The iOS 0.9.0 section raises deployment minimum to 17.2 and changes camera lifecycle; 1.0's standalone photos, motion, speech, inputs and camera audio additions are experimental. A release number or mock preview cannot qualify production hardware, background behavior or distribution. R04 records this correctly. [iOS changelog](https://raw.githubusercontent.com/facebook/meta-wearables-dat-ios/main/CHANGELOG.md), [Android changelog](https://raw.githubusercontent.com/facebook/meta-wearables-dat-android/main/CHANGELOG.md).
- **Android:** Health Connect's default historical window and extra history permission, Wear OS target-API permission differences, and separate glasses hardware permissions are documented. Phone permission does not automatically authorize glasses capture. [Health Connect](https://developer.android.com/health-and-fitness/health-connect/read-data), [Health Services permissions](https://developer.android.com/health-and-fitness/health-services/permissions), [XR hardware permissions](https://developer.android.com/develop/xr/jetpack-xr-sdk/request-hardware-permissions).
- **Frame and neuromotor research:** Frame documents capture/readiness/read primitives; this does not establish reliable streaming or a speaker path. The neuromotor repository advertises pretrained artifacts and an 80/10/10 participant split; code/data are CC BY-NC 4.0. Checkpoint-specific terms and consumer raw-EMG access remain unestablished. No dataset or checkpoint was downloaded. [Frame API](https://docs.brilliant.xyz/frame/frame-sdk-lua/), [research README](https://raw.githubusercontent.com/facebookresearch/generic-neuromotor-interface-data/main/README.md), [license](https://raw.githubusercontent.com/facebookresearch/generic-neuromotor-interface-data/main/LICENSE).

## Findings and mandatory promotion conditions

**R04-G1 — HIGH consequence, acknowledged native-evidence gate.** Exact phone/Watch/glasses model, OS, firmware, companion topology, country and entitlements remain UNKNOWN separately for A and B. No platform list proves an owned configuration. W01 and C25 correctly prevent mock success becoming native acceptance. Before a native package, freeze the actual tuple, distribution eligibility, lifecycle/indicator/route behavior and measured stop evidence. No emergency, medical or wearer-identity inference follows from sensor absence, device ownership, voice/face matching or don/doff state.

**R04-G2 — MEDIUM, access ambiguity and withdrawal must remain distinct.** W02 correctly makes Haven's own withdrawal an authoritative scope/epoch change while acknowledging that OS Settings read withdrawal may not be immediately observable. Native API enforcement, Haven retention/deletion and historical imported data have different semantics. Preserve this distinction in C02/C03/C08/C12/C26 and later P-R04-03 checks. An empty query, a successful authorization request or a deleted-sample callback cannot supply a global permission truth bit. A stopped capture session also must not erase historical evidence; lawful later historical use requires its own current authority.

**R04-G3 — MEDIUM, preserve exact output accounting and delivery uncertainty.** W04/W05 match CORE's four records and R01's accepted correction. One whole output has one destination and one charged release claim; redemption does not recharge the parent. New destination/replay requires new admission, and exhausted quota cannot be silently refunded or reminted. C18–C24 preserve unknown commits, absent ACKs, historical delivery, current eligibility and no automatic resend. Hardware buffering leaves a residual race after consume; masking/stop requests are not proof of recall. Future chunked, streaming or multi-destination profiles remain deferred and separately reviewed.

**R04-G4 — MEDIUM, coding path and inference prerequisite remain unresolved.** P-R04-01 explicitly reports CODE_NOT_AVAILABLE / PACKAGE_PATH_FREEZE_REQUIRED for the actual application. Its proposed paths and six-hour ceiling are not current code authorization. Supply a frozen real application revision and exact route/view/schema allowlist before UI edits; never implement into recovered immutable inputs. Preserve VA-01 lifecycle/containment closure before any affected inference pilot. A fixture-backed status view can be evaluated separately, but cannot claim image-model runtime qualification.

**R04-G5 — MEDIUM, native release rights and total costs remain unclosed.** Experimental API visibility is not publishability. Later SDK adoption must pin release artifacts, terms, telemetry settings, signing/entitlement and companion requirements. The new HealthKit history-window API needs actual availability qualification rather than an assumed minimum OS. Apple's published USD99/year membership is supported, but it is not a complete native-development cost. Mac/toolchain, compatible devices, distribution and support costs remain UNKNOWN. No purchase is recommended or authorized. [Apple enrollment](https://developer.apple.com/programs/enroll/), [Meta repository](https://github.com/facebook/meta-wearables-dat-ios).

These conditions are already substantially represented in R04 and do not block documentation synthesis. They block the corresponding unsupported deployment/qualification claim.

## Utility, coverage and experiment assessment

The first slice is useful and appropriately narrow: one deliberately selected benign phone image, typed question, source-linked private answer/status, plus synthetic history. It does not need native health enrollment, glasses, microphone access or a new framework. The four required positive flows prevent a denial-only demonstration: image answer, A-only history, B's independent request, and valid one-use release/consume. Future real image inference remains subject to its separate adapter qualification.

I counted exactly 26 distinct C01–C26 cases. C01–C08 cover chronology, absent/restricted access, estimator/unit differences and corrections; C09–C15 cover capability, session/lifecycle and malicious input; C16–C26 cover two-person lineage, quota, uncertainty, route change and independent usefulness. They are proposed cases, not executed native acceptance or a statistical reliability study. Implementers must freeze which cases are symbolic versus actual software assertions before execution; simulated OS events cannot qualify hardware.

All eight original REQ-WEAR/AT-WEAR pairs, EX07 stale-data semantics, EX08 glasses lifecycle and REQ-DAILY-08 survive. Original M6 remains request-only, after accepted M5, with T30/T31 and its 2–6-hour qualification boundary. Mock success leaves AT-WEAR native status NOT_EXECUTED/PENDING_OPERATOR. P-R04-02–05 preserve concrete re-entry paths for native testing, independent enrollment, deliberate cues and richer multimodal replay. No physiological challenge, diagnosis, emergency contact or physical dispatch is introduced.

## Actual modality and R10 transcription addendum

I directly viewed the entire existing 240x120 `research/R10/modality-smoke.png`, SHA256 `10468285615819f3e0946a12b149e2c67699da89002d15747856487fbd54e86f`: red square left, blue circle centrally, thin black descending diagonal right on white. No transforms were applied. This is a synthetic static-image development observation only. No audio/video playback, PDF figure, real health signal, waveform or wearable sensor was inspected. R04's transcript-only and documentation-only labels remain appropriate.

Spot-checked the complete root transcription `reviews/REVIEW-R10/REVIEW.md`, SHA256 `227e775267b79b38326ffbd064db61fa3836a7e83468e21672e6e470f57880d8`, against my returned review. It retains bounded acceptance, all five gates, exact hashes, EC120 uncertainty, historical-only N1/N2, unqualified R1, no new tests, source/modality limits and Q-CORE-04. **No substantive correction required.** Later CORE acceptance does not retroactively change R10 author consumption.

## PEER-CHECKIN-01

Observed strength: the author distinguishes platform visibility, Haven authority, delivery evidence and physical behavior while retaining positive utility. CORE/R01's exact accepted records prevent contradictory handoff accounting. Weakness: neither these documents nor my review demonstrates executing native access, user comprehension or background/route behavior. Major risk: an adapter simplifies these distinctions into permission/live/delivered Booleans. Next: preserve the gates in synthesis, then freeze actual application paths and protected positive/failure cases before authorization. Confidence high in hashes, source-preservation and contract consistency; medium in practical deployment prospects; no native performance confidence established. Accepted conclusions do not outrun code/test evidence while these limits remain attached.

## Reviewed content hashes

```text
CAPABILITIES.md c3663b8e72513feb50be22063a3da5964f20def7c34b3bf31a25e12fdb8489eb
CONSULTATIONS.md c6a82b71c80301ecec9d5ce598fbb184b1dec671b7dded36684f2624880d4a01
CONTRACTS.md 985b53bab11cc9b581e3242429f73be87d41b8d4b55de2069fe64b4317d0b7a2
EXPERIMENTS_AND_PACKAGE.md c12167d3efd91ee3eb7df8819ab4dec40ab069eaf918b64da20b08d0ee76be3c
HASHES.json 90c2d832f126b0111d0726f75f1d8eb5f36bb040fbd82ce154a5b5e016a0eef0
INPUT_RECEIPT.md 67628fd1c9a0e41ac641df0bafb2b41b56d908aacc6c573a61b55ea08c5f3713
INPUT_USE.json 3d89c8c8f5b149b673a525ad38874ab99534d1b6ebe218f40f2548b89f39f5de
MODALITY.json c16536e2ed52a9dca2736429fc25b4d8fac23e86b7f8f3559e5be8bff8dd7396
REPORT.md b519b2189c711c8edbf2458d6e18cf9d3273705a1b84722eae4cbc6a178c9479
SOURCES.md 2ba4219a1f9cc88fef34ecd031cd8d00dc7e80b3021e68f400a55bcf9123a15b
VALIDATION.md ef8369186b4e0b0a6c2ba77e73fcdb25158f8fc7e191d974287c1a187ecf0c7c
```

Signed `/root/ri01_evidence` — REVIEW-R04 — 2026-09-28.
