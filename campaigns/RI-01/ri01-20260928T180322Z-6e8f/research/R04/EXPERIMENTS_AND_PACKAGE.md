# R04 finite experiments and future packages

Every case below is **PROPOSED_NOT_EXECUTED**. There is no application/native/physical acceptance evidence in this handback. Thresholds are proposed engineering acceptance criteria, not clinical thresholds or measured reliability. A failed privacy/identity/order case cannot be averaged away by answer quality.

## Original requirement preservation

| Original IDs | R04 treatment | Required eventual evidence |
|---|---|---|
| REQ-WEAR-01 / AT-WEAR-01 | CAPABILITIES native per-person route; W01/W02 | Exact A and B tuples, native enrollment/permission route, independently reviewed unknowns |
| REQ-WEAR-02 / AT-WEAR-02 | Measurement matrix and case C01–C06 | Unavailable/region-limited types do not fabricate readings or continuous medical capability |
| REQ-WEAR-03 / AT-WEAR-03 / EX07 | W02 chronology and C01–C08 | Original time/unit/source survives stale/out-of-order/missing/denied visibility |
| REQ-WEAR-04 / AT-WEAR-04 | Original M6 request-only Watch path; C20 | Tested server receipt through exact path; approval/execute denied to request credential |
| REQ-WEAR-05 / AT-WEAR-05 | Independent camera/audio/display/cue capabilities; C09–C11 | Absent/preview feature uses explicit supported fallback |
| REQ-WEAR-06 / AT-WEAR-06 / EX08 | W03; C12–C15 | Pause/swap/revoke fences collection and disclosure; hardware cessation separately observed |
| REQ-WEAR-07 / AT-WEAR-07 | Independent A/B grants; C07,C16,C17,C26 | Subject private summary allowed with authority; unauthorized partner receives no private payload |
| REQ-WEAR-08 / AT-WEAR-08 | Per-capability D0–D6 ladder; C25 | Mock remains mock, native PENDING_OPERATOR until actual operator evidence |
| REQ-DAILY-08 | R01 continuity and W04/W05; C18–C24 | Correct source age, destination, cancellation and unknown-delivery semantics across surfaces |

## EX07/EX08 extension: 26 frozen cases

Use two fictitious principals, invented measurements and benign synthetic images. No public human biosignal dataset substitutes for synthetic fixtures. Protect expected results from the code under evaluation; preserve all cases, failures and exact revisions.

| Case | Input / fault | Expected observable result |
|---|---|---|
| C01 | Sample collected yesterday arrives now | Historical interval remains; arrival never becomes measurement time |
| C02 | HR value absent; API request completes successfully | UNKNOWN/unavailable, never zero/normal/live; no `read_granted=true` inference |
| C03 | Restricted history window, older records absent | Window/uncertainty shown; no claim no older events occurred |
| C04 | SDNN versus RMSSD, oxygen fraction versus percentage, temperature absolute versus baseline | Preserve estimator/unit/representation; only explicit versioned conversion; no merged medical score |
| C05 | ECG record and source algorithm classification | Clearly historical/provider-derived; no live ECG/Haven diagnosis |
| C06 | Unsupported model/country/type or malformed future timestamp | Type unavailable or clock uncertainty; no guessed measurement/current claim |
| C07 | A observation mislabeled B; wrong subject/store cursor | Reject association; no private content in errors or partner UI |
| C08 | Duplicate, deleted and corrected sample plus stale cursor | Idempotent ingestion; tombstone/correction invalidates derived history; cursor cannot skip committed effects |
| C09 | Camera-only glasses asked to display text | Explicit no-display result and newly admitted phone fallback if authorized |
| C10 | Experimental SDK feature requested in publishable profile | Reject unsupported release profile; retain supported capture/status route |
| C11 | SDK callback arrives before session STARTED or after stop | No capture/publication based on unstarted/stopped session |
| C12 | Pause/revoke while capture request is pending | Future acquisition/output fenced; stop report separate from cessation proof |
| C13 | Device removed, swapped or binding epoch changes | Session invalidated; late data quarantined; explicit rebind required |
| C14 | App backgrounded, OS suspends, Bluetooth link lost | Native availability UNKNOWN/unavailable as appropriate; no invented continuous coverage |
| C15 | Captured text/audio tries to instruct permission escalation | Treat content as evidence only; no scope/recipient/action change |
| C16 | A private history requested by B without sharing grant | Denial without sensitive metadata; A's eligible private view still useful |
| C17 | Joint-source summary; uncited B parent revoked/corrected | Full closure denies stale release/replay and invalidates derivative caches |
| C18 | max_uses=1: release, charge, then consume; competing second release | First valid existing claim consumes once without recharge; second new release denied; duplicate does not remint |
| C19 | Lost release/consume ACK, later revoke, reconnect | Unknown/history retained; read-only reconciliation; no blind replay or refund |
| C20 | Watch request credential tries approve/execute; phone relay/server unavailable | Broader operations denied; receipt states honest; reachability not server delivery |
| C21 | Headphones disconnect or destination becomes shared/locked | Pause/mask future private output; no speaker/lock-screen fallback; residual prior exposure recorded |
| C22 | User asks handoff to another device while parent finite grant exhausted | New destination admission required and denied if no quota; no silent reuse of old permit |
| C23 | Offline cached private answer with no fresh verification | No new private/shared release/replay; show content-minimal connectivity state where authorized |
| C24 | Cancel after historical display report; cue/audio ACK absent | Preserve past display; future eligibility denied; human perception remains unproved |
| C25 | Mock succeeds while physical tuple/indicator/stop untested | Native status remains PENDING_OPERATOR; no maturity promotion |
| C26 | A stops own sharing while B's independent eligible phone request runs | A-dependent work fenced; B's unrelated work survives; no shared-server kill used as privacy mechanism |

Acceptance for the synthetic subset: all specified invariants hold, no unauthorized output or fabricated current/medical state, and at least four positive flows remain useful (selected-image answer with a source link, A-only chronology, B-only independent request and a valid one-use release/consume). Record uncertainty rather than forcing every fault into denial. An independent reviewer checks positive utility and failure semantics, not just a pass count.

## Smallest useful package P-R04-01 — AUTHORIZATION_REQUIRED

Owner H07 with H02 application owner; review H06 plus H04 for privacy. Why useful: a phone-sized selected-image answer/status view and honest synthetic health chronology expose a real daily interaction before optional hardware. Maximum **6 engineering hours**, **$0 paid services/hardware**, **26 fixed cases**, **32 synthetic observations**, **2 fictitious principals**, **10 benign images**, **10 MiB fixture budget**. Keep CORE's smaller authority/lineage/output bounds wherever they apply; output <=256 KiB. No benchmark expansion after fixed results without a new reason/review.

Exact design inputs: this packet's final HASHES.json; CORE architecture `abf33854c793fc58c6e6679348a34d546abe5051bdfd6d91978e24b75449eb82`; CORE contracts `df19f37926b33851236aca230859adfef332a85120380ea04c24294237c2e6d0`; R01 closure `96687ff8643ea960aa275855160a4124d0925e933ebdefdd9c4e8031f4ac9032` and referenced composite; original REQ/AT/EX pins in INPUT_USE. Implementation repository revision/path manifest must be frozen after reading the actual application and its AGENTS rules; it is not invented by this research task. CORE's retained stack is Python 3.12/FastAPI/Pydantic 2/Jinja/Uvicorn/SQLite; retain original M4 `qwen2.5vl:3b` baseline. No framework, queue service or database replacement.

Proposed allowed new package paths, subject to supervisor resolution against the real tree: `design/H07/R04/P01/`, `tests/h07_r04/`, and one explicitly enumerated existing application route/view/schema path set in the future authorization. **No application path is currently authorized.** If the actual implementation is unavailable or differs, return CODE_NOT_AVAILABLE/path conflict instead of silently widening scope. New isolated design/fixture paths are proposals, not instructions to create them now.

Path evidence: this worktree's targeted file inventory exposes recovered historical lab/test snapshots, not a verified active personal-interface application. CORE likewise records active R1/M0 unavailable. Therefore exact application edits are **CODE_NOT_AVAILABLE / PACKAGE_PATH_FREEZE_REQUIRED**; the UI coding assignment is conditional, not falsely ready for execution. A supervisor can first authorize only the named isolated fixture/design paths, or supply the actual application revision and exact route/view/schema files before UI implementation. Do not implement into recovered frozen inputs or treat the historical laboratory as production Haven.

Implementation boundary: typed synthetic health/capability/capture records, one selected benign image plus typed question, source/time/status presentation and CORE output admission integration. Deterministic fixture-backed answers are acceptable for chronology; the image inference path uses only an already authorized/qualified adapter. If actual inference requires held P03 lifecycle/containment prerequisites, do not start it: first show fixture evidence and keep inference explicitly unexecuted. No native health bridge, microphone, watch/glasses SDK, physical device, private image or account, enrollment, background capture, cloud inference or publication.

Prerequisites: independent R04 review; actual code/baseline revision and allowed files; accepted CORE integration profile; existing approved local toolchain; synthetic fixture rights; independent expected-result set; explicit user authorization. Expected checks: bounded parse/unit/order tests for C01–C26 applicable to the synthetic profile; four positive utility paths; static no-side-effect boundary review; visible UI/source-age/status inspection if app execution is authorized later. Native claims stay pending. Stop on unauthorized disclosure, any fabricated current/clinical status, incomplete dependency closure, ambiguous application ownership, missing runtime authority or exhausted budget. Preserve failed cases; no evaluator changes to force a pass.

Ready-to-paste future assignment:

> Implement only the independently approved P-R04-01 scope against the frozen actual application revision and enumerated file manifest. Consume this R04 hash manifest, accepted CORE and R01 composite. Add a useful selected-image/private-phone view and synthetic health chronology/status using existing contracts and stack. Exercise the fixed positive and failure cases without collecting real signals, introducing native SDKs or broadening permissions. Keep release authorization, one-use consumption, delivery observations and current eligibility separate. Do not mark native acceptance complete. Stop at six hours or any privacy/authority escape, retain evidence, and hand the result to a different reviewer. This assignment takes effect only after explicit authorization and path freeze.

## Later finite packages — each separately AUTHORIZATION_REQUIRED

**P-R04-02 exact-tuple bench, H07/H06:** choose one already-owned compatible phone; then one Watch or glasses capability only. Documentation/inventory supplied deliberately by its owner, SDK/firmware/OS/license/entitlement and indicator review first. Budget proposal: one 2-hour nonhuman fixture session, at most 20 attempts, $0 purchase, no new paid membership without separate approval. Measure capture-to-arrival/display times with uncertainty, foreground/background transition, stop report versus observed cessation, reconnect, power/thermal effects and audience/route loss. Use a printed synthetic target and test tones only if explicitly authorized; no bystanders or health data. If installation/SDK access is missing, stop and report the prerequisite. Do not weaken indicator/stop requirements to fit hardware.

**P-R04-03 one-person native history, H07/H04/H06:** separate owner enrollment and exact per-type purpose/retention; start with one explicitly selected historical interval/type, not continuous monitoring. Proposed ceiling: 60 minutes, 20 approved samples, $0 new paid calls. Owner can pause/delete; compare source versus arrival time, OS visibility ambiguity and Haven withdrawal; no clinical interpretation. A second participant is a separate later enrollment, never inherited consent. Full cost/prerequisite approval precedes collection.

**Original M6:** retain its own accepted-M5 prerequisite, request-only credential and 2–6-hour operator run for T30/T31. Do not replace it with a HealthKit experiment. If TLS/connectivity/receipt qualification fails, keep the phone pathway and propose a separate native route; no expanded Watch authority.

**P-R04-04 deliberate-cue and continuity study, R14 with MM-AV/H07/H06:** only after native tuple qualification and an independently reviewed human protocol. Proposed finite study: two independently consenting participants, at most 30 deliberate trials each over one 45-minute session; exact fatigue/accessibility stop criteria; $0 incremental equipment unless separately approved. Compare button/visible acknowledgement against one optional qualified cue, count missed/false activations and comprehension, route leakage, learning burden and haptic-related sensing gaps. No emergency, driving, physiological challenge, invasive/stimulation procedure or human signal dataset downloads. Trial design and participant privacy require fresh authorization; this document is not that authorization.

**P-R04-05 ambitious multimodal replay, MM-AV/MM-FUSION/R14:** synthetic synchronized selected video/audio/pose/health first; fixed manifests, bounded chunks, separate capture and output permits, clock uncertainty and source correlation. Streaming profile, device buffer limits and source/output retention require new CORE-compatible review. Preserve unavailable intervals and false associations. This is a re-entry condition for richer continuous interfaces, not an indefinite deferral and not a claim P0 already supports streams.
