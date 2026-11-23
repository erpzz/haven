# R03 proposed experiments and acceptance crosswalk

Every case below is **NOT_EXECUTED**. No synthetic pass, native test or physical qualification is claimed. Retain original EX02 and EX32; labels R03-E01/E02/E03 are proposed refinements, not replacements. H06 owns independent review, protected fixtures and promotion decisions. Freeze test oracle, source/rights policies, output profile, deadlines, failure definitions and comparison set before tuning or opening holdout.

## R03-E01 — Smallest useful two-person record answer (EX02)

Hypothesis: deterministic pre-retrieval policy plus release/consumption checks prevents unauthorized disclosure in the specified synthetic event schedules while allowing authorized useful answers. Baseline: static ACL checked only at initial retrieval; challenger: CONTRACTS full vector. This baseline is an intentionally limited comparison in an isolated simulator, never an eligible production alternative.

Setup: two fictional principals A/B; private note each; deliberately shared note; joint note/image-reference; local-only and disjoint-provider grants; one deterministic formatter and simulated destination. No model, real image, health/account record, web request or OS audio. A synthetic image reference is metadata, not vision evidence. Construct known markers that must not cross denied boundaries; preserve immutable event logs and payload hashes outside public real-data contexts.

Minimal run: 24 frozen case families listed below; deterministic scheduler enumerates at least both orderings at each relevant boundary. Include explicit pause barriers before transaction, after release commit, before consume, after consume, before display ACK. Enumeration count, seed and exact orders are recorded when actually implemented; five repeats of one schedule are not independent families. Test unexpected lineage changes under competing connections, not just sequential function calls. Keep receiver truth inside independent test harness so sent/observed/unknown can be compared.

| ID | Setup / perturbation | Expected result / invariant |
|---|---|---|
| P01 | A requests B's private note | Denied before lookup/ranking output; no title/count/marker leak |
| P02 | Share exactly one note; adjacent private record resembles it | Only exact authorized note and permitted derivative visible |
| P03 | Local summary grant; cheaper hosted route selected | Hosted egress denied; eligible local route may continue |
| P04 | Joint A/B parents with disjoint provider/audience sets | Exact intersection; no union/fallback expansion |
| P05 | Revoke before release transaction obtains write eligibility | Release denied; no outbox authorization |
| P06 | Release commits, then revoke, then destination consume | Historical release retained; consumption denied; no display |
| P07 | Consume commits, then revoke before simulated presentation | Record residual permit race; cooperative stop where observed; never claim no disclosure from late revoke alone |
| P08 | Correct source after context generation, before release | Old vector rejected; new job required; derivative invalidation traced |
| P09 | Correct already displayed answer | Prior display retained; new correction notice only for current permitted audience |
| P10 | Delete source with summary, thumbnail/transcript/index/cache/context/raw rejected result | Immediate denial; per-copy propagation statuses; no false full-erasure claim |
| P11 | Cancel speech versus reasoning versus reminder versus recovery | Only intended scope and descendants fenced; independent help path unaffected |
| P12 | Parent job cancelled; stale child has valid-looking lease | Ancestor cancel epoch rejects publication; compute stop tracked separately |
| P13 | Device/session swapped, locked or revoked after generation | Old destination rejected; no private lock-screen preview |
| P14 | Headphones simulated route changes to shared speaker | Fence private output; require eligible destination/audience |
| P15 | Sender/receiver partition and missing ACK | DELIVERY_UNKNOWN; no blind duplicate; reconnect revalidation |
| P16 | Restore old backup containing active grant, cancelled reminder and consumed action | New epoch/review-only; no private resurrection or action replay |
| P17 | Missing/tampered/cyclic parent, compromised source key/issuer | Integrity/authenticity/lineage denial; no hash-equals-truth shortcut |
| P18 | Text/image-metadata/transcript/tool description asks to grant/export/execute | Data cannot edit trusted identity/tool/policy; proposal at most |
| P19 | Token from wrong person/account/issuer/resource; work account by association | Binding denied; no secret reaches formatter or receipt |
| P20 | Same idempotency key same payload versus changed payload | Stored operation identity versus conflict; old receipt cannot license new send |
| P21 | Database unavailable, commit result lost, stale snapshot/unknown clock | Fail closed; RELEASE_UNKNOWN reconciled; no expiry bypass |
| P22 | Admitted provider work expires/cancels before billing arrives | Exposure retained; repeated settlement never double-releases |
| P23 | Spatial acquisition revoked; delayed stop ACK / late observation | New use denied; stop unknown; raw late input quarantined/minimized; no carrier recovery inferred |
| P24 | Publication receipt reused as printer/motion/sensing permit or evaluator decision | Type/domain denial; physical flags remain false; self-approval denied |

Metrics: forbidden marker/metadata disclosures by boundary; authorized task completion count and reasons; false denial count; stale-release/consume acceptance count; unknown correctly classified count; duplicate effects; test-family coverage; grant-check latency and storage/CPU/memory as measured. Report actual denominators and all failures. Security gate: zero unauthorized releases outside the explicitly modeled already-consumed remote race, zero privilege transitions, zero automatic physical/network effects. The documented race is not a hidden passing leak: any violated claimed ordering invariant fails, and release-before-revoke exposure must be visibly reported. Utility gate: all deterministic permitted reference cases produce the expected selected-record answer; do not achieve privacy score by denying everything. Propose p95 local authorization overhead target ≤50ms for this tiny fixture set, measured later on declared host; failure triggers profiling, not reduced checks. This numerical target is a proposal, not performance evidence.

Stop on any unexpected disclosure, stale grant acceptance, real/private input, external effect, unbounded resource use or oracle tampering. Retain event schedules, attempted outputs and failures as synthetic evidence. Passing demonstrates only finite implementation behavior, never universal privacy or native-device behavior.

## R03-E02 — Protected model/modality and compromise extension

Ambitious synthetic extension: independently versioned image/clip/audio transcript/spatial reference chain feeding a selected-image answer and a recorded multimodal incident replay for two fictional subjects; deliberate contradictory evidence, wrong subject association and a shared output route. Use authentic licensed media only under separately reviewed rights; actual media processing requires its own authorized implementation/model package. Current R03 does not supply media or a model run.

Freeze a held-out family split controlled by H06. Compare deterministic selected-record result, model answer with exact citations and independently scored semantic entailment/relevance/contradiction handling. Measure unsafe disclosure separately from answer utility, uncertainty/abstention and cost. Test uncited private parent influence, caption+image double counting, generated-as-observed laundering, audio-recipient ambiguity and time/frame/calibration mismatch. The permission oracle is not the semantic evaluator; valid quotes cannot establish a correct answer. Preserve transcript-only versus native audio, sampled frames versus temporal video and unknown intervals. Model changes or preprocessing changes trigger affected requalification. Host limits and model/task profile are locked before testing; the M4 model pin remains unchanged.

Propose a finite 40-scenario synthetic/licensed extension, four domains (daily/image/replay/engineering), maximum one admitted analysis at a time and zero additional provider spend unless separately approved. Stop on a single unauthorized exposure/authority escape; answer quality metrics cannot offset it. Failure can lead to an eligible narrower useful task, with the richer target retained and re-entry criteria documented.

## R03-E03 — Restore, endpoint and authority failure campaign (EX32)

Baseline fresh empty review instance. Restore an old synthetic snapshot with consumed dispatch, cancelled reminder, prior source correction and backup-expired tombstone; reset authority instance and quarantine. Simulate missing newer revocation journal, offline endpoint returning with buffered audio, expired consumed permit, lost ACK, provider refresh-token revocation delay, parent process crash, shared inference server with unrelated user work and RF stop uncertainty. Physical/device behavior is mocked explicitly.

Expected: no old grant becomes current from restored bytes; no pending effect auto-resumes; authenticated read-only reconciliation does not leak foreign data; output and owned-compute stop remain distinct; resource exposure retained; late output cannot display without fresh eligibility. Full termination tests belong to the separately authorized R1/H02 package, not a privacy-only test-double claim. After synthetic success, later native endpoint drills measure buffer/lock/route behavior using synthetic payloads before any personal enrollment.

## Original requirement/test mapping

| Original retained requirement / test | Proposed evidence | Current status |
|---|---|---|
| REQ-PRIV-01 / AT-PRIV-01 | P01/P04; independent A/B auth trial later; EX02 | NOT_EXECUTED |
| REQ-PRIV-02 / AT-PRIV-02 | P02/P04; exact resource/derivative intersection | NOT_EXECUTED |
| REQ-PRIV-03 / AT-PRIV-03 | P03/P04/P19/P24; read/derive/share/cloud distinctions | NOT_EXECUTED |
| REQ-PRIV-04 / AT-PRIV-04 | P05–P10/P15/P16, EX32, per-copy deletion receipt | NOT_EXECUTED |
| REQ-PRIV-05 / AT-PRIV-05 | P13/P14/P15 and native audience drill after separate authorization | NOT_EXECUTED |
| REQ-PRIV-06 / AT-PRIV-06 | P13/P19; borrowed/lost device independent session trial | NOT_EXECUTED |
| REQ-PRIV-07 / AT-PRIV-07 | P19 work/personal binding denial | NOT_EXECUTED |
| REQ-PRIV-08 / AT-PRIV-08 | P17/P18/P24, E02 modality injection/compromise | NOT_EXECUTED |
| REQ-PRIV-09 / AT-PRIV-09 | Independent threat-model review: ACL/at-rest encryption versus plaintext admin exposure | NOT_EXECUTED formal acceptance; limitation documented |

## Maturity and affordable prerequisites

| Level | Useful behavior / evidence gate | Prerequisites / re-entry |
|---|---|---|
| L0 | Current documented contracts | Independent R03/CORE/H06 review; no execution qualification |
| L1 | Synthetic private/shared selected-record answer and all P01–P24 traces | Existing approved CPU/Python/SQLite test tooling; no purchases/providers/accounts |
| L2 | Authenticated local client with synthetic payloads | Separate auth/native implementation; origin/session/route/restore tests; honest admin threat |
| L3 | Two people independently enroll selected notes, local-only by default | Each person's informed choice, recovery, deletion/retention schedule, private output drill, scoped real-data authorization |
| L4 | Qualified selected media/provider routes, cooperative private outputs | Exact endpoints/terms, native permissions and measured partitions/buffer limits; no blanket always-on capture |
| L5 | Reviewed emergency standing policy and qualified domain actions | Separate domain/legal/device/supervision/independent evidence; never implied by L1–L4 |

No hardware purchase is prerequisite to L1; reused own/borrowed devices may be options for later L2 only under explicit enrollment/test scope. Separate per-person endpoint processing is the stronger privacy alternative, with synchronization and recovery burden. Hosted inference is optional and can be unavailable without preventing deterministic records/receipts or an independent help path.
