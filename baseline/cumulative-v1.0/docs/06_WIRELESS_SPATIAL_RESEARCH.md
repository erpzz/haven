# Beyond direct sight: wireless sensing and spatial reconstruction

**Retained user requirement:** this is not a WiFi coverage-map project. The desired endpoint includes evidence about spaces or objects beyond direct visual observation, potentially through an obstruction or outside a building. Presence and localization are accepted stepping stones toward geometry and semantic understanding. Keep all four stages in the roadmap.

## Four different outputs

| Stage | Desired output | What would count as progress | What does not count |
|---|---|---|---|
| Sensing presence | Movement/occupancy candidate with quality and coverage | Fewer false triggers on held-out conditions than a stated baseline | A binary demo in one unchanged room presented as universal detection |
| Localization/tracking | Region/trajectory with coordinate frame and uncertainty | Ground-truth error and interval coverage on unseen placements | A precise dot drawn from a weak class probability |
| Geometry reconstruction | Estimated surfaces/edges/occupancy | Comparison with known structures under controlled measurement geometry | Generative room imagery without measured support |
| Semantic understanding | Candidate object/scene interpretation tied to evidence | Grounded object-level outputs with abstention on ambiguous data | A plausible label promoted to an observed fact |

These stages can require different measurement hardware and algorithms. A presence detector is not necessarily a scalable primitive for high-resolution geometry. A successful first stage proves useful acquisition/validation infrastructure, not automatic feasibility of the remaining stages.

## Starting evidence and hardware paths

Use R01–R05 in the research register as distinct precedents: coordinated RSSI tomography, diffraction/edge reconstruction, RF pose estimation, CSI acquisition examples and standardized sensing operations. Do not collapse them into one claim that an ordinary phone already exposes a universal imaging sensor.

Investigate four configurations independently: fixed low-cost nodes at measured positions; an authorized handheld accessory using a phone for display/context; a controlled scanning fixture; and a mobile robot/drone carrying an explicitly qualified sensor. A phone can be central without its native radio being sufficient. The EC120's flight programmability and a sensing accessory's RF access are unrelated questions.

CSI, signal strength, timing/ranging and radar observations have different information content. A link-quality heatmap may support acquisition troubleshooting, but is not completion of the presence or reconstruction objective. Do not collect nearby network traffic/content merely to obtain measurements; use authorized test equipment and data.

## Physics and observability

Every proposed reconstruction must state the measurements it assumes, sensor frequency/bandwidth/antenna geometry, transmitter/receiver positions, synchronization, calibration, sampling path, target/environment assumptions and expected ambiguity. Use exact qualified hardware specifications at acquisition time; no nominal “WiFi capable” label substitutes for measurement access.

A world estimate must represent unobserved space explicitly. Multipath, material differences, nearby movement, interference, device drift and changes in furniture can change interpretation. Test these as confounders rather than using a large model to hide them. Visually convincing generated content is a hypothesis visualization, not independent evidence.

Direct through-obstruction sensing, a device already across the obstruction and a remembered visual map are three separate evidence origins. Combining them is allowed only when the result retains these distinctions. A new radio reading must not make an old map appear newly surveyed.

## Spatial contract

A `SpatialEstimate` identifies its map revision, coordinate frame, time interval, evidence references, calibration revisions, method/version, estimate type, region/geometry and uncertainty representation. Coordinates without a frame/transform are invalid. A classification score is not a spatial covariance. Unknown uncertainty must be recorded as unknown rather than an invented matrix.

A map projection can hold measured geometry, inferred occupancy, change candidates, semantic hypotheses and unknown regions in separate layers. A display may simplify presentation but cannot erase those layers. Region privacy applies to the map and derived estimates, not only raw recordings.

## Active perception

Haven may propose the next observation expected to reduce an ambiguity, subject to consent, time, energy, safe movement and information value. Compare an adaptive strategy to a fixed sequence under identical measurement budgets. Require the proposed next view to refer to known equipment and allowed observation locations. Do not let the model synthesize a new flight route or assume it can access the far side of a wall.

The first active-perception experiment can be a software replay over a prerecorded set of allowable observations. Only after validation should a physical operator move a fixture through an approved sequence. This preserves ambition without requiring immediate aerial autonomy.

## Research sequence

**RF0:** inventory exact candidate measurements, permitted datasets, legal hardware categories and acquisition metadata. **RF1:** reproduce a simple presence baseline on synthetic/authorized data. **RF2:** collect a consented small room dataset with repeatable node fixtures, session/room-level holdouts and ground truth. **RF3:** compare localization models and calibration; test movement/no-movement/multiple-source ambiguity. **RF4:** investigate geometry using controlled targets and known sample positions; do not promise a particular resolution. **RF5:** compare fusion of RF, direct-view/depth and historical maps. **RF6:** evaluate adaptive observation with budgeted human/robot motion. **RF7:** qualify the same technique on a suitable mobile carrier if it adds measured value.

The printer branch supplies repeatable fixtures and scanning supports. The robotics branch supplies measured pose only when qualified. These are contract dependencies, not permission to install every stack into one environment.

## Evaluation and legal boundaries

Pre-register scenarios, ground truth, train/validation/test split, held-out rooms/people/sessions, baselines and stopping criteria. Count false presence alarms per hour, misses under defined conditions, location error, uncertainty coverage, geometric error and latency/energy. Record negative results and calibration drift. Do not split adjacent frames from one recording across train and test and call it generalization.

Use consenting participants and permitted spaces; through-wall collection can affect nonparticipants even without a camera. Review RF equipment authorization and use restrictions separately. R33 is particularly important for certain UWB through-wall systems; it is not a blanket rule for all WiFi sensing. Until exact classification is resolved, keep that hardware path at simulation/dataset/documentation level. No wall penetration claim, covert monitoring or real rescue readiness is asserted by this roadmap.
