# R04 — Wearables, health and glasses

## Metadata and one-page summary

Author: `/root/ri01_privacy`, `haven_researcher`; H07 / RI-01 R04. Research date: 2026-09-28. Base recorded by supervisor: `376031e182c57495912baf6727093b0b188da568`. Status: **REVIEW_READY, documentation research only; no author acceptance claim**. Start 19:38:30 UTC; maximum 30 minutes. Exact inputs and their effects are in INPUT_USE.json. CORE core-v1 and R01 composite govern this proposal. Supervisor reports CORE independently passed for downstream research; the VA01 hold concerns prerequisites before a future P03 package freeze, not this research. No owned SKU, OS, firmware, country, pairing or entitlement tuple is verified.

The useful first wearable-adjacent slice is an explicitly selected phone image, a typed question, and one grounded response shown on the same authenticated private phone. A status view shows source age, connectivity, queued/unknown delivery and pause. It can work before native health collection or glasses integration. Keep the original M4 image-model baseline and application stack. Follow with synthetic health chronology and glasses lifecycle cases, then separately authorized native qualification. These stages retain the two-person wearable, multimodal and deliberate communication ambitions without treating mock success as physical evidence.

Three distinctions change the design. HealthKit history is not a continuous Watch feed, and successful authorization does not reveal read permission. A glasses product's camera, audio, display and gesture interfaces are independent capabilities. A platform callback or transfer acknowledgement is not proof that a human saw an answer, felt a cue or received help. The exact current Meta DAT release is materially different from older preview descriptions: version 1.0.0 lists new experimental interfaces that cannot yet be used in published apps. Record version, release channel and publishability separately from documentation existence.

This packet supplies concrete contracts, a device and measurement matrix, 26 finite proposed cases, staged budgets and a ready-to-paste future coding assignment. All native, application, health, audio and wearable experiments are **NOT_EXECUTED**. A benign existing synthetic image was directly viewed through the development tool; that is not Haven runtime qualification.

## Decisions

1. **Phone first.** Use a system selected-photo interface or explicit foreground still capture. An imported image has an upload time, not an inferred current capture time. Do not request microphone or full-library access for a still-image task. Private response stays in the admitted destination; switching to a Watch, glasses or shared screen requires fresh destination admission.
2. **Enroll A and B independently.** Platform health authorization, Haven identity/session, subject binding, retention, derivation, cloud processing and sharing are separate decisions. Owning a phone or paying for a household service cannot enroll the other person. A sensed wearer, paired account, voice match or nearby face cannot establish health-record subject identity.
3. **Preserve missingness.** Historical measurement, current qualified observation, manual statement, provider classification and model interpretation are separate fields. No sample is not zero, normal, sleeping, safe or incapacitated. A current arrival of an old sample remains historical.
4. **Native authority remains explicit.** HealthKit is a native Apple route with per-type access; the original Safari/PC path does not gain HealthKit by adding a server endpoint. A legitimate workout API may support timely measurements during that workout, but a fake workout must not be used as an always-on background exemption. The original M6 Watch request-only milestone remains separate.
5. **Intentional cues are optional convenience.** Start with a deliberate button and visible acknowledgement, later a qualified haptic cue or compatible glasses display. A cue does not approve a physical action, prove perception or authenticate a wearer. Apple documents that Watch haptic playback can interrupt heart-rate acquisition; a combined sensing/cue experiment must retain that interference.
6. **Reuse CORE ordering.** Acquisition, inference, release authorization, consumption eligibility, delivery evidence and physical dispatch remain different boundaries. For the first finite profile, one immutable output goes to one destination under one durable use claim. No new wearable-specific central authorization service is proposed.

## Evidence and practical pathways

The source-linked platform/API and measurement facts are centralized in CAPABILITIES.md and SOURCES.md to keep versions reviewable. These are public vendor/API claims, not measured latency, battery, reliability or native compatibility.

**Daily image help:** A selects a photo of a connector, asks which label is legible, and receives a source-linked answer with ambiguity preserved. The source record retains the original image and any crop relationship. If the image also contains B's private information, A's upload permission alone is insufficient for sharing or cloud processing; minimize or use an independently permitted source. Text visible in the image is untrusted task data, never a new instruction. A follow-up on another device must revalidate lineage and audience.

**Private health chronology:** after future enrollment, A asks what measurements were recorded last night. The system displays the actual interval, source, units and gaps, without converting nightly measurements into a current condition. B cannot request A's summary without an applicable sharing grant. A deliberately shared excerpt retains source dependence by default; revoking a parent blocks new release and replay. No independently declassified health lineage is created here.

**Watch continuity:** the original M6 request-only Shortcut can propose a request and inspect an honest receipt after its own operator qualification. WatchConnectivity reachability is a local app-path observation, not internet or server-delivery proof. A queued request and an unanswered request remain distinguishable from a rejected or positively fenced unsent request. No automatic retry after an ambiguous external dispatch.

**Glasses continuity:** compatible glasses can later offer explicit still acquisition and a short private status display. Removal, a detected session change, app background transition or an uncertain wearer invalidates the bound session and stops future admission. Undetected swapping remains a physical limitation requiring tested controls; a don/doff sensor is not identity assurance. If a private audio route disappears, pause; do not silently play through a phone speaker. A display may be visible to someone else and open-ear audio may be audible nearby: neither is inherently a private audience.

**Ambitious cooperative scene:** independently enrolled A and B intentionally contribute bounded clips, audio, pose and timestamped observations to a shared incident replay; permitted summaries return to selected devices. Specialized audio/vision processing supplies typed evidence; correlated frames, crops and captions are one lineage, not independent witnesses. This requires later streaming/chunk contracts, codec/lifecycle qualification, synchronization, false-activation and audience studies. It is not implemented by the initial still-image slice. Emergency support must retain an independent help pathway; no missing wearable signal or model inference authorizes a drone, robot, emergency contact or clinical diagnosis.

## Interface changes

CONTRACTS.md proposes H07 extensions to CORE I01/I02/I06/I07: exact capability tuple, health observation/access observation, explicit capture session, intentional cue and handoff records. Full source/grant/policy/cancel dependency closure remains canonical. Where HealthKit intentionally withholds read-authorization status, the extension records visibility uncertainty rather than fabricating a reliable revocation callback. OS enforcement and Haven's own withdrawal controls complement each other; neither substitutes for the other.

## Actual versus proposed

| Activity | Actual status | What it establishes |
|---|---|---|
| Read pinned CORE, R01 composite, original wearable goals/REQ/AT/EX | EXECUTED document inspection | Contract and requirement fidelity only |
| Current official Apple, Android, Meta, Brilliant and R12 O09 sources | EXECUTED public text/API research | Dated documentation claims; not hardware performance |
| Existing synthetic PNG direct view | EXECUTED development-tool smoke | This session can inspect that image |
| Audio/video playback, native sensor collection, SDK build, application tests | NOT_EXECUTED | No wearable or Haven modality qualification |
| Proposed cases and packages | PROPOSED_NOT_EXECUTED / AUTHORIZATION_REQUIRED | Reviewable next work only |

## Acceptance and maturity

All original **REQ-WEAR-01–08 / AT-WEAR-01–08**, **EX07**, **EX08** and **REQ-DAILY-08** survive. EXPERIMENTS_AND_PACKAGE.md maps each requirement to evidence and finite cases. Original AT statuses remain NOT_EXECUTED; native acceptance remains PENDING_OPERATOR even after a future mock passes. Original M6 follows accepted M5 and retains its request-only 2–6-hour operator qualification and stop-on-unreliable-receipt boundary. No revision of M4, M5, M6 or a physical/emergency policy is authorized here.

Maturity is per capability: D0 unknown; D1 primary documentation identified; D2 synthetic contract experiment passed independently; D3 exact device bench qualification; D4 one-person narrowly enrolled useful trial; D5 two independently enrolled users and withdrawal/audience qualification; D6 separately reviewed continuous multimodal/human-factors study. This packet reaches D1 for the documented candidates, D0 for exact owned tuples and D0/D1 for preview or unpublished interfaces. No D2–D6 pass is claimed.

## Risks and open questions

HealthKit's privacy-preserving access ambiguity prevents a simple global `read_granted=true` truth bit. Freshness thresholds are task-specific product criteria, not medical normal ranges. Exact sensor provenance, OS availability of newer access-window APIs and country-dependent measurement availability must be qualified on the eventual tuple. Background suspension, reconnection, duplicate events, stale route observations and power loss remain possible. Native SDK telemetry, vendor terms, distribution entitlements and cloud processing require their own review; an open code sample is not permission to redistribute data or weights.

No verified owned tuple is available: supervisor answered Q-R04-01 with UNKNOWN and no inventory access. On Q-R04-02, supervisor confirms that selected still/single destination fits the accepted finite-use profile and later streaming/cross-device output needs reviewed scope and fresh admission. This is explicitly a supervisor interpretation, not a fresh CORE-author answer. R12 O09's updated public dataset/checkpoint release does not imply raw EMG access on consumer glasses or a private silent-input product. The proposed first slice remains useful if every optional wearable is unavailable.

## Next package

Select the bounded synthetic/phone-view package in EXPERIMENTS_AND_PACKAGE.md, independently review this packet and freeze the actual application input revision before authorizing code. Native health enrollment, physical wearable capture, microphone use, paid membership, continuous streams and human studies are separate packages. Downstream **MM-AV** consumes route/interrupt, codec/background and synchronized-source distinctions; **R14** consumes deliberate cues, interference, false activation and O09 licensing limits; **R11** consumes missingness, fall-event limitations, honest receipts and the independent help-path boundary.
