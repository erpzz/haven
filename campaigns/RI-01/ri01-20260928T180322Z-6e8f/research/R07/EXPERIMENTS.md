# Proposed R07 experiments and acceptance

Every case below is **PROPOSED_NOT_EXECUTED**. No test result, model accuracy or physical performance is implied. Original requirements/acceptance/experiment IDs are preserved; R07 case labels are local planned fixtures, not replacements for original AT/EX.

## Ownership and scope crosswalk

| Original anchor | Owner retained | R07 use / expectation |
|---|---|---|
| REQ-RF-01/AT-RF-01 | H08 | Retain geometry and semantic ambition beyond heatmaps, with staged evidence |
| REQ-RF-02/AT-RF-02; REQ-RF-03/AT-RF-03 | H08 | Presence/localization consume actual apparatus evidence; missing/no-motion is not absence or exact position |
| REQ-RF-04/AT-RF-04; EX14 | H08 | Controlled geometry, held-out reference and false-edge accounting; future empirical path |
| REQ-RF-05/AT-RF-05; EX31 | H08 requirement, H01 EX31 | Separate measured structure and semantics; accessibility/comprehension retained |
| REQ-RF-06/AT-RF-06 | H08 | Fixed/phone-accessory/handheld/fixture/rover/drone comparison |
| REQ-RF-07/AT-RF-07; EX09 | H08 | Source/path/history separation and exact transforms |
| REQ-RF-08/AT-RF-08; EX17 | H08 requirement, H10 EX17 | Multimodal degradation; clocks/calibration/uncertainty explicit |
| REQ-RF-09/AT-RF-09; EX15 | H08 | Bounded additional permitted measurement; fixed comparator/equal budgets |
| REQ-RF-10/AT-RF-10 | H08 | Participant/area/radio equipment authorization before physical sensing |
| REQ-ENG-08/AT-ENG-08; EX16 | H09 | Separate enclosure sensor-effect experiment and invalidation |
| REQ-DRONE-04/05/06 and matching AT | H05 | Read-only evidence first; deterministic mission boundary; ACK/observation/unknown distinct |
| REQ-ROBOT-01/03/04 and matching AT | H10 | Ground carrier, independent stop, embodiment-specific qualification |
| REQ-AI-07 and AT-AI-07 | H02 | Grounded supported answer/abstention, not generic confidence |

## E07-A: replay semantics, no model

First implement 24 small synthetic traces below, split12 development/12 protected evaluation before coding. Evaluator/expected records frozen by H06; author cannot inspect protected truth at selection time or alter it. All24 must preserve authority/evidence invariants; positive cases additionally return a useful correctly supported view/answer. Record each input/output and actual reason, elapsed/resource use, not just aggregate pass. Mutation controls: swap parent/child transform; remove tombstone check; duplicate correlated source as independent; reset per-selection deadline. A meaningful test suite must catch all four separately injected faults. These are proposed controls, not mutations performed now.

| Case | Setup / expected oracle |
|---|---|
| C01 supported positive view | Synthetic calibrated static cell and matching frame: exact supported cell/locator/time returned, unknown remainder preserved |
| C02 old depth plus fresh RF | Historical geometry stays old; fresh motion region separately labeled, no chair/body invention |
| C03 missing transform | FRAME_UNRESOLVED; no fabricated origin or alignment |
| C04 reversed transform / wxyz | Known asymmetric point rejects mismatched convention; versioned conversion produces exact expected point |
| C05 unknown learned scale | Relative view permitted with label; metric layer denied SCALE_UNKNOWN |
| C06 non-PSD or nonfinite covariance | Reject invalid matrix; unknown cannot be numeric zero |
| C07 caption/crop/original | Common capture closure deduplicated; no three-witness confidence gain |
| C08 shared calibration drift | Related estimates stay correlated; no averaging systematic bias away |
| C09 disjoint clock intervals | CLOCK_UNKNOWN/degraded conflict according to exact frozen tolerance; receipt time cannot repair capture |
| C10 boot reset/rollover | New source boot/mapping required; old calibration not silently reused |
| C11 map jump | New immutable revision; no interpolation through relocalization discontinuity |
| C12 missing/occluded return | Cell remains UNOBSERVED/OCCLUDED, not observed free |
| C13 repeated objects / track gap | Ambiguous association retained; no identity or cross-user health join |
| C14 low light / small object | Input quality marks degradation; missing detection not absence; no image recognition run implied |
| C15 stale image / visual text error | Evidence date and uncertainty prevent false current metric claim; text does not mint authority |
| C16 false thermal appearance | Ordinary RGB palette cannot become calibrated temperature observation |
| C17 missed between-frame event | Uncovered interval stays unknown, no continuous-video claim |
| C18 audio-video desync/outage | Separate sample intervals; missing stream explicitly degraded, no fabricated agreement |
| C19 revoked joint source | Current query/replay/context/tile/summary denied through complete influence closure |
| C20 correction/rematerialization | Whole affected compressed view denied if inverse lineage unavailable; successor recomputation uses eligible refs only |
| C21 restore + historical permit | New restore epoch, review-only; old replay/permit cannot release again |
| C22 generated scene branch | Scenario never becomes observed map or motion permission, even if visually plausible |
| C23 budget/stop/unknown outcome | Total60s/eightattempts respected including slow/denied views; ACK not STOP_CONFIRMED; unknown no auto acquisition retry |
| C24 positive bounded next-view | Eligible finite candidate resolves known ambiguity under remaining budget; returns proposal only, no command |

Complementary cross-modal cases remain MM owners' responsibility: acoustic false alarms, names/numbers/accents, ambiguous speaker/recipient, cancelled playback and per-user contention. R07 contributes C13/C17/C18/C19 seams; it does not falsely claim all full-suite24 modality cases tested. Real low-light/small-object/audio cases need modality-qualified data and evaluation later; metadata traces test contracts only.

## E07-B: bounded active observation (EX15, R06 E0 reused)

60 synthetic episodes;20 development,20 validation,20 protected held-out, split by scene/layout rather than adjacent frames. This reconciles R06's60episode design with E07-A's separate24semantic traces; counts are not interchangeable. At most8 immutable candidate views per episode,60seconds total inclusive of selector/inference/retries/admission, fixed/random/adaptive at equal permitted attempts/time/energy assumptions. Freeze seed list, candidate catalog, cost/gain estimator and stopping thresholds before evaluation; selector sees only acquired evidence. Hidden full scene and test forward model stay inaccessible.

Oracle: all safety/privacy/authority invariants; report support coverage, unknown volume, false geometry and task error against independently generated truth versus count/time/energy assumptions. Baseline includes strongest fixed permitted schedule, random with multiple frozen seeds, and best single sensor (EX17). Success is a Pareto improvement or a measured no-benefit/inconclusive result; do not demand universal superiority. Statistical intervals are descriptive of synthetic episodes, not household generalization. Stop on ground-truth leakage, budget mutation, authorization escape, or any observed/inferred relabeling. Retain every failed/inconclusive episode. No live action or simulation package executed now.

## E07-C: measured geometry/calibration comparison, later

Independent H06 reference metrology and explicit licensed selected imagery/depth required. Compare calibrated classical geometry/depth baseline with exactly pinned learned candidate only after rights/hardware/runtime authorization. Freeze unit/scale/frame/camera intrinsics/extrinsics, nuisance variables, holdout room/session/configuration and observed support mask. Measure metric median/tail error, completeness, false geometry, repeatability, interval coverage when calibrated, latency/memory/energy and failures by reflective/texture-poor/occluded/moving condition. Unknown calibration remains unqualified. Synthetic agreement alone cannot promote to measured performance; no package selected for execution here.

## E07-D: interface comprehension (EX31, H01)

First inspect synthetic phone/mock-glasses screens against text baseline: select an old map, conflict and unknown region; ask what was actually observed, when, and what additional evidence is needed. Later separately approved participant study measures correct distinctions, time and unsafe interpretations. Use shape/pattern/text labels in addition to color, accessible text summaries and no route guarantee. Stop/revise when the display implies safe passage from inferred/unknown coverage. Human study NOT_EXECUTED; no participants enrolled.

## E07-E: RF inverse identifiability (R12 O05 / EX14 bridge)

Six proposed paired cases: distinct layouts with indistinguishable measurement response, wrong material prior, shifted calibration, optical-prior dependence, held-out frequency/apparatus, and empty scene false-edge control. Use a different forward model from the inverse model with hidden reference. Retain multiple hypotheses/unknown when nonidentifiable. RFDT full-artifact/license gaps block its run; the conceptual counterexample dossier can proceed without it. No gradient benchmark establishes geometry or material truth.
