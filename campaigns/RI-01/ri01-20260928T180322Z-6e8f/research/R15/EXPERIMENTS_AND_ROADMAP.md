# Experiments and bounded roadmap

Every experiment here is PROPOSED_NOT_EXECUTED and every package is AUTHORIZATION_REQUIRED. Actual R15 work was documentation/source inspection, primary-source research and artifact validation. Existing N1/N2 scores remain historical synthetic evidence; this task neither reran nor repaired NIGHT-01/R1/M0/M1/M4. A UI pass cannot qualify sensor accuracy, model grounding, authority implementation or physical safety.

## First useful demonstration: a regional evidence scene

Use one public regional area such as Long Island, selected without a private home point. Freeze12authored event fixtures, three explicitly SIMULATED resources, one synthetic correction/gap timeline, a source inspector, linked event table and deterministic answer to “What changed since yesterday?” Retain exact expected answers and unknowns. The default starts RECORDED FIXTURE, never LIVE. A later authorized manual D01NWS refresh is a separate stage using a rights-reviewed exact source snapshot; no actual feed was fetched in this research.

Compare against opening the same pinned GEV and a plain event table separately, with identical events/source detail and no disadvantage imposed on the baseline. The Observatory adds integrated source selection, two-clock history and explicit uncertainty. Any cinematic effect is optional and disabled in correctness tasks.

Positive outcome: a user finds the newly received versus corrected event, sees the actual source footprint, identifies why a simulated rover is unavailable and obtains a correct source-linked explanation. Negative outcome: missing yesterday data is reported as unknown, not no change. A question requiring model semantics is not silently answered by a template pretending to be inference. Later model qualification remains separate.

## Frozen evaluation design

H06 independently freezes fixture IDs, source hashes, expected outcomes, forbidden inferences and scoring before implementation tuning. Author may not edit its evaluator after seeing held-out failures. Keep every failed trial, timeout, retry and exclusion with its original identity. Repeated runs are not new independent case families.

Utility study: two independently consenting intended users; eight matched task families under each of two UI conditions, counterbalanced A/B order with equivalent unseen variants.32total task trials (2users×2conditions×8). Families: identify source/time; locate changed event; distinguish correction; identify gap; inspect support geometry; explain resource unavailability; select exact replay cutoff; draft a public-only share. Freeze four answerable, two abstention and two clarification outcomes, with denominators4/2/2 and overall8 for each user/condition. Correct content and correct outcome class both required. Proposed success: Observatory≥7/8 and no lower correctness than baseline for each user; median completed-task time≥20%lower per user; report individual paired differences and failures. Small-n within-person comparison is formative, not a population effect estimate. No significance or confidence guarantee is claimed.

Mode-comprehension study:14vignettes/person (two variants each of current observation, historical/replay, inference, simulation, stylization, reference and unobserved).28total, separate from32utility trials. Text/pattern/screen-reader/table versions avoid colour memorization. Proposed threshold≥13/14overall for each user, with zero consequential confusion on simulation/stylized-versus-sensing, unknown-versus-free and replay-versus-current. A single consequential error fails that gate despite the total. These are proposed targets, not validated psychometrics. Evaluator-only checks do not count as user testing.

Performance qualification: exact host/browser/build/network profile documented in future package; original target p95local selection-to-inspector≤500ms and first fixture view≤3s over20fixed interactions/session, three separate sessions. Record cold/warm conditions, all failures, frame-time stalls, frontend/process memory and actual request count. Initial memory target≤2GiB and fixture footprint≤200MiB; these are resource goals, not promises. On mobile, background suspension must stop automatic animation/refresh and show age on return; test exact device later, no assumed iPhone result.

Provenance/trust gates are absolute: every released claim has resolvable exact source/locator/class/time, zero unauthorized disclosure/dispatch, no lost essential sidecar, no reconstructed deleted geometry, no source-dependent unsupported precision. They are separate from utility and performance. Passing a mocked receipt vignette proves presentation only; runtime ordering needs independent implementation tests.

## Thirty concrete case families

Each row is a future test specification. Evidence retained is subject to the same privacy/retention policy; use synthetic/public fixtures. “Owner” identifies existing domain expertise plus H06 independent evaluation, not a new runtime service.

| ID / setup | Expected result | Retained evidence | Owner |
|---|---|---|---|
| R15-T01 stale snapshot beyond frozen freshness threshold | Age/stale label; current claim withheld; retained history still correctly labeled if eligible | Source times, policy ref, query/projection, rendered/text status | H08/H06 |
| R15-T02 provider timeout/503 with old snapshot | OUTAGE distinct from empty result; no automatic unbounded retry; old source remains dated | Request identity, timeout/status, retry count, before/after projection | H02/H08 |
| R15-T03 quota429 or unknown remaining allowance | QUOTA_LIMITED/UNKNOWN; no fallback paid provider; budget retained conservatively | Rate revision, reservation, observed status, denied retry | H02/H04 |
| R15-T04 replay selected while animated camera/tour plays | Persistent REPLAY/recorded time in map/table/answer/export; never LIVE | Mode transitions, output digest and captures under future authorization | H01/H08 |
| R15-T05 moving traffic actors with live aggregate flow metadata | Actors explicitly SIMULATED; aggregate data and actor hypotheses separate | Entity classes, lineage, comprehension response | H08/H01 |
| R15-T06 thermal shader over RGB source | STYLIZED display; no measured Celsius claim or sensor qualification | Shader/profile identity, labels, expected rejection of temperature question | H08/H06 |
| R15-T07 contradictory capture/publication/receive times and overlapping clock uncertainty | Preserve all times; order indeterminate where warranted; no invented causality | Native values, mapping uncertainty, query trace | H08/MM-FUSION |
| R15-T08 coarse/null polygon/detection footprint | Footprint/unknown location, no guessed building or centre as observation | Native geometry, support, projection refusal/limited view | H08 |
| R15-T09 swapped axes, local frame, unknown altitude datum, antimeridian extent | Reject or safe source-local/table profile; no precise global height; correct wrap handling | Transform/profile refs, invalid cases and derived render geometry | H08/H05 |
| R15-T10 partial sensor mask and inferred completion over gap | Unknown/conflict mask retained; completion cannot become observed/free | Mask lineage, separate class overlay, participant answer | H08/MM-FUSION |
| R15-T11 revoke after preparation before release/consume | Current admission denies future release/consume; old receipts remain if already committed | Full dependency snapshot, ordering trace, four output records | H04/H02 |
| R15-T12 private pin/label/count in scene link or export | Minimal exact public projection only; no hidden URL/referrer/sidecar leakage; deny unsafe export | Synthetic canary scan, network/export manifest and source closure | H04/H00 |
| R15-T13 HTML/script/URL instructions in annotation or imported document; excessive nesting/size | Render inert text or reject; no script/fetch/command; bounded parser failure | Malicious fixture digest, rejection reason, zero-egress observation | H04/H00 |
| R15-T14 cancel during ingestion or analysis | No fenced late publication; compute STOP_REQUESTED/UNKNOWN unless independently confirmed; no false refund | Attempt/lease/cancel, transport/compute observations, usage | H02/H04 |
| R15-T15 browser background, low memory or WebGL loss | Stop animation/unsolicited refresh, retain exact selection if safe, accessible table fallback and updated age | Lifecycle/request log, memory record, restoration state | H01/H00 |
| R15-T16 scenario injects a live resource, URL or adapter capability | Reject and retain SCENARIO; no network/device path | Capability graph, attempted escape, denied operation | H00/H08/H10 |
| R15-T17 unavailable/stale/unqualified resource icon | UNKNOWN/UNAVAILABLE with allowed explanation; no READY inferred from ownership | Exact config/qualification/age refs, proposal refusal | H05/H10 |
| R15-T18 two users revise shared annotation or compete for resource | Expected-revision conflict; privateA/B remains separate; domain lease arbitrates | Concurrent revision/admission traces and minimized UI outputs | H04/H02/H01 |
| R15-T19 eight matched spatial/provenance tasks versus separate tools | Frozen useful outcome/time targets; report each user/stratum, no fabricated speed gain | Task sheet, condition order, answer key, timings/errors | H01/H06 |
| R15-T20 remove a simulated relay from declared topology | Only modeled connectivity changes; no real network alteration or internet guarantee | Frozen graph/model/branch diff, assumption labels | H11/H08 |
| R15-T21 local relay available but backhaul/destination unknown | Show each layer separately; not “online/delivered/help received” | Layer-specific receipt vignettes and interpretation | H11/H01 |
| R15-T22 delayed correction plus tombstoned parent | Known-then/corrected-now differ; current deny propagates; no deleted geometry leak | Revision graph, query cutoff, invalidation and per-copy states | H04/H08 |
| R15-T23 physical proposal pending/ACK/unknown and stop requested | Proposal not execution; ACK not observed stop; unknown reservation/exclusion retained | Exact domain tuple and outcome state projection | H05/H10/H11 |
| R15-T24 fixture changed, scalar uncertainty/calibration unknown, failed candidate retained | No metric/pose/RF-neutrality promotion; historical failure visible; evaluator unchanged | R08profile/calibration/fixture/protocol/decision refs | H09/H08/H06 |
| R15-T25 release authorized→consumed→lostACK→revoke, plus displayed→cancel | Historical receipts retained; delivery unknown/reported separate from current denial; no refund/resend/remint | Exact output/destination/sequences/vector plus UI wording | H04/H01 |
| R15-T26 offline pack requests OSM standard raster bulk download or ineligible asset | Refuse forbidden acquisition/export; eligible original pack still useful | Rights/source-version decision and allowed pack manifest | H00/H04 |
| R15-T27 capability tree labels accepted research as qualified hardware | Reject promotion; show next gate/owner and NOT_EXECUTED evidence | Source status/review refs, before/after projection | H00/H12/H06 |
| R15-T28 Directorv5 prose/v6 actual parser; missing sidecar, mismatched sidecar digest, stripped essential metadata, changed-authority reimport | Exact supported profile validates; each named corrupt/lossy/unauthorized variant rejects or yields only independently eligible limited table; no grants resume | Four explicit mutation assertions frozen before execution, input version/digests, current authority and semantic conservation diff | H00/H08 |
| R15-T29 no colour/WebGL/audio and screen-reader/keyboard use | Same evidence/mode/selection/task completion via text/table; no private speaker fallback | Accessibility task sheet, exact platform tuple, errors | H01/H07 |
| R15-T30 follow simulated rover vs request real observation | Camera change only for follow; inert separately admitted proposal for real request; no actuation | Typed intent split, synthetic/real IDs, capability allowlist | H10/H05/H08 |

T01–18 cover every original required category;T19–30 add usefulness, communications, lineage and honest state cases. Each family requires positive useful examples as well as rejection examples where applicable. No proposed table row is reported as an original AT pass or rewritten original requirement.

## Roadmap and coding packages

Each package owns only the proposed new directory after root checks it is unused. Existing application, source inputs, canonical contracts, baseline lab and shared index are outside child ownership. No GitHub actions, deployment, user enrollment or automatic next package is implied.

### WP-R15-0 — one-page public fixture proof
Owner H00 implementation; independent H06/code and H04boundary reviewer. Inputs: accepted R15+MMF composites, exact GEV pin/audit/lock/license allowlist, CORE/R07/R01 and frozen test oracle. Prerequisites: explicit operator authorization for exact dependencies/build/test commands and no-egress environment; no source install happens in research.

Scope:120minute composition feasibility gate; then up to24engineering hours for12event/3simresource original fixtures, deterministic query, inspector/time/table/mode labels. Proposed paths `prototypes/observatory-p0/` and `tests/observatory-p0/`; no main app/database migration. First profile makes0network/feed/model/device calls, including fonts/tiles/geocoding/telemetry. New build dependencies are explicitly enumerated before approval; no “npm install everything” allowance.

Tests:T04–10,T12–18,T20,T22–30 using fixtures, plus complete applicable original mapping from REQUIREMENT_MAP. Resource budget:0paid calls,200MiB authored/eligible fixtures,2GiB browser target,4GiB implementation test-process ceiling,60minute test session. Stop on unwanted egress, unowned globals that cannot be bounded in the120minute gate, license uncertainty, authority escape or budget exceedance. Fall back to an original thin2D/table prototype, not a rewrite. H06 retains failed proof and reviewer decides promotion; do not self-accept.

### WP-R15-1 — one manual public provider
Owner H08 adapter with H00; independent H04/H06. Inputs: acceptedWP0, D01current terms/schema, exact allowlisted URL/headers, valid source/correction fixtures and rate/error oracle. Prerequisites: explicit network/source acquisition authorization and current provider check.

Scope: one manual NWS regional request at a time, max2MiB/20seconds, no polling, no private coordinates/account/key. Store source bytes plus native metadata under existing approved evidence interface. Proposed paths `prototypes/observatory-p0/adapters/nws/` and its fixtures/tests; runtime acquired records outside public repository. Tests:T01–03,T07–09,T14,T22,T26 plus positive no-alert/supplied-geometry results. Budget:≤10manual requests total for qualification, no paid API,≤20MiBnew raw evidence,4engineer hours+2review. Stop on unknown rights/schema, redirected unexpected host, oversized response, unintended query metadata or quota. Success is one qualified adapter profile, not all regional sources or emergency alerting.

### WP-R15-2 — formative utility and semantics study
Owner H01/H06 independent evaluator. Inputs: frozenWP0and optionallyWP1snapshot,32utility/28mode trials, known answers and separate baseline. Prerequisites: each participant's explicit consent, no private media/location, exact device/browser and anonymized retention policy. Proposed paths `evaluation/observatory-formative-v1/`; results separate from code and no public participant data.

Scope: described two-person comparison, table/keyboard alternative, source lookup and mode distinctions. Budget:≤90minutes/person,6operator hours including scoring, no model/device acquisition/paid service,≤100MiBeligible logs. Stop for fatigue/withdrawal/privacy breach or changed oracle. Report individual errors and uncertainty; failed useful positive cases cannot be replaced with easier examples. Independent reviewer may prefer the plain table; that is a valid result.

### WP-R15-3 — recorded multimodal replay and inert scenarios
Owner H08/MM-FUSION with H00; independent H06/H04. Inputs: acceptedMMFexact profiles, R07/R08lineage, authorized original/suitably licensed recordings and exact tools if proposed. Prerequisites: acceptedP0, independent authority/lifecycle adapter closure; model-bearing work additionally COREVA-01/P01. Proposed paths `prototypes/observatory-replay-v1/` and `evaluation/observatory-replay-v1/`.

Scope: source-linked image/audio/video/telemetry views with full time/frame/support/correlation, one finite graph fork and mandatory export sidecar. Do not add MCAP/Rerun unless existing simple files fail a named task. Budget candidate8engineering hours+4review,≤250MiBnew eligible source assets subject to remaining campaign/host allowance,≤4GiBtest memory,0paid or live device calls,0unqualified model calls. Tests:T07/T09–16/T20–25/T28. Stop if essential provenance is lost, cross-source alignment unknown is hidden, scenario escapes or current eligibility cannot resolve. This is recorded evidence, not sensor/robot qualification.

### WP-R15-4 — later cooperative/embodied continuity
Owners H04/H07/H08/H09/H10/H05/H11 by effect; H00 coordinates and H06independently reviews. Inputs: accepted earlier packages and exact native/device/physical contracts/qualifications, complete system costs and operator permissions. Proposed design path `design/H00/R15/cooperative-v1/`; implementation paths/commands deliberately unresolved until owners select exact hardware/interfaces.

Scope: private pin/output, deliberate cue, resource-readiness and inert mission/engineering proposals. Budget for a further design closure≤4hours,0purchases/devices/paid calls; any operational package needs separately itemized limits. Tests:T11/T18/T21/T23–25/T29–30 plus domain originals. Stop at missing authority/device/clinical/flight/fabrication qualification; no stale offline-grant exception. Actual capture, transport, actuation and physical recovery remain distinct future grants.

## Promotion and retained scope

Document acceptance → authorized offline proof → independently reviewed source adapter → useful human comparison → recorded multimodal/scenario slice → separately qualified private/device/domain paths. Advancement is evidence-based, not automatic. The first meaningful result can be a simple public map/table that beats separate tools. Broader observatory, cooperative senses, active perception and protective machines remain explicit targets with re-entry gates.

All102original requirements,102acceptance expectations,32experiments, Gen0T01–T35, original research-testR01, M0/M1/R1/M4 and qwen2.5vl:3b remain unchanged. R15Txx/WP/OBS labels are local proposal IDs. REQUIREMENT_MAP references the exact original records and ownership; it does not assert full implementation coverage. Missing original upstream research prompts/reviews remain recorded gaps rather than reconstructed authority.
