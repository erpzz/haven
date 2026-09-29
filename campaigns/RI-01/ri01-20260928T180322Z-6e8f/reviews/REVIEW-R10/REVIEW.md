# REVIEW-R10

**ACCEPT_FOR_SYNTHESIS — bounded documentary and design subset only.**

Actual reviewer `/root/ri01_evidence`, acting `haven_research_reviewer`, 2026-09-28. Author `/root/ri01_privacy` is distinct. The reviewer read the exact profile, RI authorization/protocol/vision, all 12 R10 deliverables, relevant recovered acceptance/experiment/Gen0 records and consumed REV-R06. No files, Git state, accounts or devices were changed by the reviewer. Zero application, SDK, simulator or aircraft tests executed. Root persisted the actual returned review in this structured form.

R10 supports a candidate comparison, proposed capability/evidence contracts, preserved qualification boundaries and a proposed offline package. It establishes neither a selected affordable aircraft nor an accepted operational schema, physical readiness, completed original acceptance tests or Haven runtime qualification.

## Integrity and input use

All eleven manifest-listed files match their SHA256 and byte counts. The manifest itself matches the root-supplied digest. INPUT_USE contains seventeen records: fifteen referenced local hashes match; two unreceived/provisional inputs correctly retain null hashes. The base commit is supervisor-reported metadata, not proof the new campaign files existed in that commit. The reviewed revision is the exact file set below.

Q-R10-02 correctly attributes advice to `/root/night01_review` through root and calls it provisional. Later CORE existence/review does not retroactively establish author consumption or close R10 schema dependencies.

## Primary-source checks

- DJI's tagged MSDK 5.18.0 README lists Mini3, Mini3Pro and Mini4Pro. Official release-page text independently reproduces historical 5.13.0 firmware/controller tuples. Joining those older tuples to 5.18.0 remains unsupported; R10 avoids that inference. [Tagged README](https://raw.githubusercontent.com/dji-sdk/Mobile-SDK-Android-V5/V5.18.0/README.md), [release notes](https://developer.dji.com/doc/mobile-sdk-tutorial/en/).
- `enableVirtualStick`, advanced-mode control and a recommended 5–25 Hz send rate are documented. The API limits virtual-stick obstacle avoidance to named aircraft/modes; consumer marketing cannot establish it. Camera/frame/stream listeners exist since5.8.0, but callbacks do not establish trusted capture time. [Virtual-stick API](https://developer.dji.com/api-reference-v5/android-api/Components/IVirtualStickManager/IVirtualStickManager.html), [camera API](https://developer.dji.com/api-reference-v5/android-api/Components/IMediaDataCenter/ICameraStreamManager.html).
- Tello SDK2.0 documents automatic landing after15 seconds without commands. Vendor-described behavior is not evidence of a safe landing location, authenticated Haven authority or tested recovery. [Ryze guide, November2018](https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf).
- PX4v1.16 distinguishes continued offboard signaling, supported frames and configured loss handling. MAVLink distinguishes acceptance from completion and specifies transport retries; R10 requires reconciliation above those semantics. [PX4](https://docs.px4.io/v1.16/en/flight_modes/offboard), [MAVLink](https://mavlink.io/en/services/command.html).
- Standard CoDrone EDU has no camera; its API exposes pairing/battery queries. This supports bounded programming/sensor use, not camera perception or fleet qualification. [Manufacturer camera clarification](https://help.robolink.com/article/yameybd0n6-does-co-drone-edu-have-a-camera), [Python API](https://docs.robolink.com/docs/CoDroneEDU/Python/Drone-Function-Documentation/).
- Crazyflie logging uses a24-bit boot-relative millisecond timestamp, making boot identity and rollover material. Dock3 accommodates one aircraft; charging figures are conditional manufacturer measurements, not battery swapping or generic fleet readiness. [CRTP logging](https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/crtp/crtp_log/), [Dock3](https://enterprise.dji.com/dock-3/specs).

These were selected documentation/text checks dated2026-09-28. Mutable web-response hashes were not captured; editions/tags and URLs are anchors. Not every promotional specification or platform combination was independently checked.

## Findings and retained gates

1. **High consequence, acknowledged: operational promotion remains blocked.** REPORT CR-R10-01–04 separates documented capability, qualified configuration, evidence, authority, dispatch and observed outcome. No actual identity, complete current firmware/bridge tuple, recovery behavior, calibrated camera timing or physical reservation enforcement was tested. Unknown-aircraft exclusions and reservations survive lease loss; admission timeout cannot prove an aircraft disappeared.
2. **Medium: shared-contract closure before P0.** Source time, receipt time, boot, clock uncertainty, altitude datum, home origin, calibration and correlation are suitable synthesis requirements. Exact schema versions, covariance convention, numeric types, authority ordering and reservation identities remain owner decisions. The package already requires accepted CORE/R07/R03; preserve that dependency, not satisfaction by this review.
3. **Medium: component licensing/startup before SDK adoption.** Public docs and exclusion of third-party media do not establish rights for a complete future SDK application. DJI distinguishes MIT sample code from SDK-linked LGPL FFmpeg. Exact SDK/library/codec licenses, notices, account registration and offline-startup evidence remain required before an SDK-bearing package. This does not block standard-library-only P0. [DJI licensing](https://raw.githubusercontent.com/dji-sdk/Mobile-SDK-Android-V5/V5.18.0/README.md).
4. **Medium: affordability unresolved.** Reviewer independently confirmed CoDrone kit$249, Crazyflie Brushless$480, Holybro6C$609/6X$769, Mini3RC-N1USD419 and Mini4ProRC-N2USD759. Both inspected DJI configurations were out of stock. No unlike currencies are added and component prices are not full totals; delivered system costs remain UNKNOWN. Future totals must avoid double-counting included batteries/guards/cables and price missing infrastructure. Holybro6X has an additional power-module firmware condition beyond the M10 minimum; do not generalize the6C row. [CoDrone](https://www.robolink.com/products/codrone-edu), [Crazyflie](https://store.bitcraze.io/products/crazyflie-2-1-brushless), [Holybro](https://holybro.com/products/px4-development-kit-x500-v2), [Mini3](https://store.dji.com/product/dji-mini-3), [Mini4Pro](https://store.dji.com/product/dji-mini-4-pro).
5. **Medium: legal research is scenario-specific.** US Part107 is an explicit research scenario; actual jurisdiction, registration, site, operation and permission remain unknown. FAA sources support VLOS/multiple-aircraft waiver distinctions and registration-related RemoteID applicability. Neither S2 nor a dock confers permission; no actual legal clearance is established. [FAA waivers](https://www.faa.gov/uas/commercial_operators/part_107_waivers), [RemoteID](https://www.faa.gov/uas/getting_started/remote_id).

None requires rejection of bounded research or fabricated hardware execution.

## Coverage and experiments

REQ-DRONE-01–12 and AT-DRONE-01–12 remain recognizable, NOT_EXECUTED. The crosswalk preserves complete cost, EC120 uncertainty, exact configuration, freshness, deterministic authority, replay/outcome, recovery, fleet separation, handoff energy, payload, base readiness and simulator containment.

EX18–20, related EX16/21/22/24, Gen0M0–M6, independentR0/R01, S1/T32 and independentS2/T33–35 remain retained. S2's15-second interval is synthetic; mock help remains independent of model/drone availability. T01–T35 are not reduced to a shorter roadmap core. EC120 identity/manual remains UNKNOWN, not proof of unsupported hardware or completion of the original four-hour dossier.

R10-E0–E8 are proposed. P0's four-hour/32-case/five-minute bounds are planning limits. Synthetic images/admission fixtures cannot establish camera freshness, payload benefit, RF neutrality, airworthiness or physical stop behavior. Next is exact contract reconciliation, then separately authorized offlineP0 with independent implementation/review. Historical N1/N2 evidence remains historical synthetic evidence, not a new run or independentR1 closure.

## Actual modality and consultation

Reviewer directly inspected `modality-smoke.png`: white background, red square left, blue circle centrally, thin black descending diagonal at right; declared240×120. This establishes static-image inspection only. No audio, video, real telemetry, sensor data or PDF page image was inspected in this review. The author's failed PDF screenshot attempt is disclosed.

Q-CORE-04 was actually sent to root during this task, citing R08 contractSHA `01ed60d55591b3d4a2a03cafaf4c299d24c1c9f47d406d68bd3dd2bac6d02f03`. Seconds→integer milliseconds requires exact representability/range checking, rejecting sub-ms fractions, overflow and UNKNOWN rather than rounding authority. Durations, UTC instants and clock uncertainty are distinct. Length conversion scales uncertainty/covariance dimensionally, not frames/datums. Allocations preserve authoritative parent reservation/lease identity. Exact P00 owner closure remains deferred.

## Actual peer assessment

R10's strength is distinguishing vendor documentation from qualification; REV-R06 uncertainty/cessation findings improve it. Both are documentary, and this review checks selected primary sources and bytes, not installed SDK/physical recovery. Synthesis risks converting model-list membership, a fresh receipt or a revision vector into a physical-state guarantee. Next: reconcile exact CORE/R07/R03 and retain denial fixtures beforeP0 authorization. Confidence high for integrity/bounded coverage, medium for comparison, no confidence claim for unperformed hardware qualification. Conclusions do not outrun code/test evidence while these limits remain attached.

## Exact SHA256 register

```text
COMPATIBILITY.md fe4b60387975e7b919bbea84b90bc365e4323420b7d4205c65fc7a604a0f74f6
CONSULTATIONS_AND_CHECKIN.md 0f4b9a4d9e80b4452d22252728e8ba34c1373be79197b9a534fe7f91fffa06fe
COSTS.md e1a25c3947feed2728a44421098ad9457592a663a3225d7c0d3497b8fc3be6d3
EXPERIMENTS_AND_PACKAGE.md e3a0ea372287ab6d9b43c57310b3bb3ff92e82d99fcc38dd20c623edd823a01c
INPUT_RECEIPT.md 4a0366decb919b0a6a910bc121482ae4bd6ab7f1af01e4a8497fd4b0dfb5f4d3
INPUT_USE.json fce32febcb869f705d4e3333016ab3c88b8e7248dfc39563671fb614969c7250
MANIFEST.json a880c3eea7584036651c280a8d4a71f28a0d5645471a4e064c8df6ff27e541c1
modality-smoke.png 10468285615819f3e0946a12b149e2c67699da89002d15747856487fbd54e86f
MODALITY.md c2e70b2403390a05c244ceb64de4d04f02bf738dcd85835bdead20a304f0e097
REPORT.md 0ff3035427b78dd71594b38b152904d67bf2771829b9ceece12cd51c3f1e0c90
SOURCES.md 1080c49714a48b8a8298787b701f479aaa2eabe576362bc5b48b3e7a85eaf3f4
VALIDATION.md db26144c599139c4ef45d064a8d149e59268cd709f766d0aea64b38b24c3e285
```

Actual reviewer: `/root/ri01_evidence`, REVIEW-R10, 2026-09-28.
