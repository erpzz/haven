# First sensor-fixture measurement proposal
Status: AUTHORIZATION_REQUIRED; NOT_EXECUTED. This is a complete proposed protocol amendment for H06/H08/H09 review, not hardware qualification. R08-P00 itself only reads and authors documents.

## Decision before CAD or fabrication
Determine whether an existing mount or a simple manual datum stop already satisfies the real application's alignment need. If there is no useful measurable deficit, stop with NO_NEED rather than manufacturing more candidates. A first physical trial concerns one scalar displacement of a small sensor/dummy relative to one independent reference. It cannot establish 6DoF calibration, RF transparency, robustness across carriers, or production performance.

Required measured/verified inputs, all currently missing:
- Intended sensor/dummy identity, actual mass/envelope/centre-of-mass where relevant, contact/datum geometry, mounting/load direction, cable routing and force, clearance/keepout and environmental limits. H08/H05 must state which functional alignment error matters and its admissible range; no printer is presumed owned.
- Existing mount and manual-stop baseline with exact material/assembly/contact condition; fixture, enclosure, material lot, build orientation, process and assembly revisions. A physical specimen has a unique label/custody record distinct from design revision.
- Actual gauge/reference identity, resolution, calibration result and valid interval, traceability claim support, reference uncertainty, alignment/Abbe/cosine effects as applicable, contact force, fixed independent zero datum, repeat-reading noise and start/end reference checks. A calibration certificate's presence alone does not establish the experiment's full uncertainty.
- Measurand definition: signed displacement along a named positive axis from a fixed datum; explicit frame/revision and units; capture versus receive timestamps and clock uncertainty; operator/session/environment/cable/contact method. Do not re-zero to each candidate and erase bias.
- Actual acquisition hardware/firmware/profile and enclosure baseline, including modality-specific conditions (for RF, waveform/band/frequency/antenna/phase where applicable). Record fixture/enclosure/frame/map/extrinsic/calibration revisions and invalidation causes.
- Reviewer-selected intended-use tolerance, meaningful minimum measurable baseline variability, instrument adequacy threshold, permissible reference drift, bias uncertainty method and retention/handling failure definition. Freeze these before outcome data. Unknown values stop physical eligibility.
- Household-approved location, ventilation/material/power/noise, supervision, handling/cool-down and emergency stop arrangements before any fabrication. No order or heated task follows from this report.

The metrology rationale is limited: gauge studies distinguish repeated-reading precision from operator/session/configuration effects and bias. Method-defined quantities require a specified procedure and reference uncertainty. These do not supply our application tolerances. [NIST gauge studies](https://www.itl.nist.gov/div898/handbook/mpc/section4/mpc4.htm), [TN1297 D4](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-appendix-d4-measurand-defined-measurement-method).

## Proposed finite design
1. Freeze protocol, raw form, instrument/reference checks and exclusion rules. Take ten stationary repeated readings and ten development baseline removals/remounts; characterize instrument adequacy and repeatability. Separately document the manual datum-stop comparator. Adequacy failure is INCONCLUSIVE/STOP, not a reason to optimize against noise.
2. Permit no more than five candidate revisions, including failed builds/designs. Vary at most three geometry parameters; keep intended material/process/contact/cable method fixed. At most ten development remount readings per candidate, all retained. Count reference/missing/failed events against the overall event budget.
3. Lock one candidate and its exact physical specimen and protocol before access to holdout outcomes. Reviewer controls fresh paired holdout schedule. Twenty pairs total: ten per session, two prespecified sessions. Randomize baseline/candidate order inside each pair with a frozen schedule. Each measurement requires full removal and reseating; repeated stationary readings are not independent remounts.
4. Keep all forty holdout readings, both orderings, timestamps, failures and reference checks. A lost or invalid pair remains in the raw record and makes the confirmatory endpoint INCONCLUSIVE under this first proposal. No retrospective deletion, imputation or extension until success; a new campaign needs its own frozen protocol.
5. Before the holdout, H06 freezes analysis program hash/environment and the exact resampling draw-index artifact. Optimizer cannot inspect or modify protected holdout data, schedule or criterion through its search path. Ordinary source permissions alone do not prove this boundary; it must be separately tested.

Proposed bounds retained from R08: five candidate revisions; two attended print attempts including failed attempts and any coupons; 300g total planned material; 90min per print and three hours total machine time; 160 total measurement/reference/correction events; eight operator hours; seven calendar days. These are planning ceilings, not physical permissions or known cost. Print limits do not authorize the first inert package to print. Actual machine-specific material/time/energy and money caps require measured estimates and an I05 parent reservation. Unknown admitted exposure is retained; no automatic refund or retry.

## Exact proposed analysis, and what it can establish
Define baseline readings b_si and candidate readings c_si in metres, s in {1,2}, i=1..10. Primary variability preserves original R08 E01:
R_z = sqrt(sum over all20 (z_si - mean_all(z))^2 / 19).
Primary ratio Q = R_c/R_b. It includes the observed difference between session means. Do not silently replace it by within-session variability to make an apparent gain larger.

Report separately each session's mean/SD, drift from fixed reference, pair order, and within-session pooled SD sqrt(sum_s sum_i(z_si-mean_s(z))^2/18). The latter is a diagnostic, not an alternative winning primary metric. Absolute bias is abs(mean_all(z)-reference); report per-session bias too. No noise-floor subtraction is allowed by default. Both baseline and candidate must pass reference/uncertainty/handling eligibility.

Bootstrap proposal: independently within each of the two fixed sessions, sample ten paired indices with replacement; each sampled index carries its complete baseline/candidate pair. Combine the twenty sampled pairs and recompute the same overall Q. Use exactly 10,000 draws. The draw-index file (integers0..9, session-specific) is generated and hash-frozen by H06 before opening holdout outcomes; retain generator implementation/version/seed. Analysis consumes that exact file rather than relying on an unspecified library RNG. Sort all10,000 finite ratios ascending; the one-sided percentile upper bound is order statistic9,500 (one-based, ceil(0.95*10000)), without interpolation. Any undefined denominator/nonfinite ratio or invalid resample invalidates confirmation rather than silently dropping replicates. A prespecified deterministic fixture should test order-statistic indexing and pair/stratum preservation.

This is an explicit author proposal, not a statistical guarantee. Two fixed sessions do not support population claims about sessions, operators, specimens or manufacturing lots. Serial dependence, drift, shared reference errors and selection can undermine the paired bootstrap. If H06 finds the exchangeability assumption implausible, mark this proposal insufficient and preregister a different design before collection; do not repair the interval after seeing results. The exact draw schedule, minimum meaningful baseline and full bias uncertainty model are owner-freeze prerequisites, not invented completed artifacts.

Illustrative R08 targets remain Q<=0.70 with upper bound<0.70, candidate R<=0.25mm, and bias plus applicable expanded uncertainty<=0.50mm; the proposed instrument expanded uncertainty<=0.05mm is also illustrative. None becomes approved by conversion into metres. Physical target values need H08/H06 justification. Require baseline variability above the predeclared measurability floor; near-zero baseline, unresolved calibration/reference/clock uncertainty, missing pairs, out-of-domain conditions or failed retention/handling yield INCONCLUSIVE or FAIL with reasons. Bias uncertainty must account for applicable reference, calibration, alignment and correlation terms; do not substitute sample SD or arbitrary k=2 without method support.

A ratio success cannot offset an absolute bias or safety failure. Report baseline and candidate all metrics, counts, exclusions and raw hashes, including a predicted improvement followed by measured regression. The result qualifies at most tested specimens and conditions under an explicit intended-use review.

## Distinct metrics, independent lineage
- R02-E02 suggests at least20% lower held-out alignment error; it is not the same estimand as SD of reseating.
- R08-E01 suggests30% lower variation, plus absolute/bias/uncertainty guards and a ratio confidence bound.
- R06 adaptive sensing suggests20% fewer attempted observations at matched error/false-geometry limits.
- N2's invented arithmetic objective is none of these. Preserve its five original scores.

Record each by exact metric_definition_ref, unit, denominator, population/conditions, protocol hash and reviewer; never a generic improvement_percent used across them.

## Invalidation and later ambition
Material lot, orientation, processing, assembly, sensor firmware, acquisition settings, enclosure geometry/material, extrinsic/frame/map revision, reference/calibration expiry or environmental violations append requalification requirements. Earlier evidence remains visible under its original scope. Sensor quality must have a separate held-out modality-specific result; one-axis reseating benefit cannot claim RF neutrality or actual sensing improvement.

E02 remains a later pilot: independent manufactured specimens, build sessions and separately qualified bench/handheld/rover conditions, then H10 handling of cooled passive specimens only. It needs an independently qualified 6DoF reference where required, exact sensor-performance metrics and additional permission. Repeated readings never become new manufactured specimens. Full adaptive engineering, robotics and field utility remain goals, not consequences of this first scalar notebook.

