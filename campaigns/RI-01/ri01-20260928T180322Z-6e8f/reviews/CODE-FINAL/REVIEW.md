# CODE-FINAL — independent final candidate review

**PASS — research candidate only.** No blocking code/contract/configuration finding was identified in the exact frozen synthesis below. This does not pass an application, authorize a package, close current M0/R1 work, or establish runtime isolation, scientific validity or physical qualification. All implementation remains AUTHORIZATION_REQUIRED. One low-severity activation clarification is retained below.

Reviewer: `/root/ri01_code_review`, `haven_code_reviewer`, 2026-09-29 UTC. Integration author: `/root/night01_review`; reviewer and author are distinct. The supervisor explicitly allowed review artifacts only under reviews/CODE-FINAL. No candidate/source/config/test edits, Git commands, application execution, installations, devices/accounts, model runs or children were used.

## Exact candidate and read scope

Campaign prefix: campaigns/RI-01/ri01-20260928T180322Z-6e8f. Candidate paths below are relative to integration/final-v1 unless otherwise stated.

| Identity | SHA256 or commit |
|---|---|
| Root-reported local candidate commit; not independently inspected using Git | c087bf9c00cb9213dc3225852fb7385ba0eb9aef |
| MANIFEST.json | c5ec562b5ea5390962ab8334b39f397e959a071a4314c3b17898ec991b3ede1b |
| ARCHITECTURE.md | edac2e9196037dfbea43396dc2d692679c5c86499dbae8194a1d09172c1616ee |
| CONTRACTS.md | cb6cea47fb00aba89da234da620b3fb3bd240c2a10e314bcc81cbfa647cc4be7 |
| WORK_PACKAGES.json | d7b46b4f14165d7634fa1931c772c026a2b14d49cd607faee27fa91d3a9e6500 |
| INPUT_USE.json | 7c67866d5658526ff86533d8b56c1e2174f345b4c6a5ac4b870d465b39ea3a25 |
| state/CANDIDATE_DIFF_SCOPE.json, campaign-relative | ff88984dee09c50ea7c3f384111bc7c4e0007512ec9ae3e54e8f7cf534541716 |

All23 manifest payloads matched exact bytes/SHA256, totaling1129108 bytes. All448 package input rows (202 unique paths),311 INPUT_USE members,76 accepted-disposition pins and39 SOURCE_USE records matched their supplied hashes; supplied member byte counts also matched. The4 immutable coordination snapshots are manifest-covered; live append-only ledgers need not retain their historical snapshot hash. Original102 requirement,102 acceptance and32 experiment records compare structurally equal. These are document validations, not tests of an implementation.

Read full ARCHITECTURE, CONTRACTS, CONTRACT_CROSSWALK, DECISIONS, EVALUATION_PLAN, MULTIMODAL, MODALITY_MATRIX, IMPLEMENTATION_QUEUE, RISKS_AND_DISSENT and manager handback/state; full/targeted VISION_COVERAGE. Read all14 package substantive fields and ready prompts, all39 source-use finding/effect records, all36 crossmodal case inputs/outcomes and MF-L01 addenda, dependency gates/refinements, and structural canonical records. Input member identities were checked in full; this is not a fresh semantic reading of every311 upstream file. Coordination snapshots were hashed and relevant assertions traced, not freshly reviewed line-by-line. No new external-source, image/audio/video or private original archive inspection was performed for CODE-FINAL.

Earlier actual reviews are explicitly reused: CODE-0 REVIEW.md066bbc38273320895dbd5cf1fc3fde31c209253103fa2e170dbf905ff8d4abc8; REVIEW-R15 REVIEW.md45d197fccf4ebe67f00a0ac4dfe11d5d6ef85fb932fe8aa9d67d3c6dd5ec11c6; R15 SOURCE_CHECKS.json4815425b7ce8c7342fbebb1f80e71efa8d2e02f1243dccf0dd40f4cfd9196f45. These hashes were rechecked. Selected historical backend/coordinator/store/context/validation and both test-file hashes still match CODE-0. Earlier R15 selected source reading and241-file identity verification are reused, not presented as another source audit or executed tests.

## Findings and invariant assessment

**CF-L01 LOW / activation clarification; nonblocking for research.** WORK_PACKAGES.json:484–498 proposes writes only under future/R02-P02-A while also requiring actual current R1 source to repair the lifecycle. Before activation, the operator/root must pin the supplied source and map it into the isolated approved copy, or issue a separately versioned exact path grant. The current prompt explicitly prohibits active M0/R1/NIGHT-01 edits, so it cannot authorize patching those workspaces or treating a toy substitute as a real repair. Suggested preflight: reject absent source identity, mismatched source-to-copy mapping, or any target outside the activated allowlist before commands run. NOT_EXECUTED. No candidate rewrite is required because current-source supply, isolated checkout and path activation are already hard gates.

**Authority and derivation closure — PASS as design, implementation unproven.** CONTRACTS.md:7–19 preserves operation-specific joint intersection over every influencing source and uncited derivative, full AuthorityVector equality, source/lineage/authenticity and grant revisions, purpose/rights, identities, area/subject scope, cancellation, lease, route/destination/audience and provider policy. Oversized/incomplete closure rejects rather than truncates. Permission filtering precedes ranking/counts/context in MULTIMODAL. Correction is expected-revision CAS; reverse-lineage consistency is part of the security boundary. Typed identifiers and fields are never represented as implemented enforcement.

Raw context, rejected backend output, request/attempt/backend metadata, indexes, exports/providers/backups and personalized derivatives remain in retention/tombstone scope (CONTRACTS:19,85). Denial, linkable audit retention and verified erasure remain distinct. This retains CODE-M1 rather than falsely closing it through output suppression.

**Durable output/accounting/concurrency — PASS as contract.** CONTRACTS:39–58 preserves immutable release and consumed-slot receipts, append-only attributed delivery observations and separately computed current eligibility. A short authoritative transaction compares complete current dependencies and commits claim/outbox/receipt together; network/model/device operations stay outside it. Unknown commit permits no send. Missing ACK cannot prove NOT_SENT. Positive no-dispatch evidence in the R01 reconciliation is stronger than an absent row or local save.

The first profile is ONE_RELEASE_ONE_DESTINATION_WHOLE_OUTPUT. Deduplicated GrantUseClaims charge all applicable grants atomically once at release. Authorization revision and quota accounting sequence are distinct, avoiding self-invalidation. A valid already charged max_uses=1 claim consumes its existing slot after fresh checks without a second debit or requiring unused parent quota. Duplicate/unknown/lost replies return or reconcile history without refund, remint or resend. Explicit replay is new admission. The contract admits the consume-to-display residual race instead of promising recall. Required concurrency, duplicate, crash/unknown-commit, wrong-destination, revocation/expiry and epoch traces are still proposed.

SQLite BEGIN IMMEDIATE is a candidate ordering mechanism, not proven whole-machine durability, a deployed schema or a migration. Current-code continuity and crash/restore/migration testing remain open under CODE-M3 and EVALUATION_PLAN:33. CONTRACTS:19,77,94 correctly separates ordinary view import into an intact current store from authoritative/evidence persistence rollback or lost continuity: only the latter uses new epochs, review-only reconciliation/quarantine and no resumed jobs/permits. Successful DB open alone does not prove intactness.

**Cancellation and containment — PASS as retained gate.** CONTRACTS:23–31 separates STOP_REQUESTED, independently observed STOP_CONFIRMED and UNKNOWN from fenced publication and accounting. Parent-backed worst-case reservation and conservative admitted unknown usage are separate from finite grant quota. ARCHITECTURE:51–55, EVALUATION_PLAN:12,33 and packages R02-P02-A/B/P03 retain CODE-H1's parent-finally gap, startup cuts, exact ownership/boot/fence, independent observer and VA-01/exact adapter containment before actual inference. Static role text, PID, wrapper exit, mock result and zero-spend fields cannot establish OS containment or remote termination. No current R1 repair was inspected.

**Evidence, protected evaluation and multimodal semantics — PASS as proposed design.** Exact quotation/citation remains separate from semantic relevance/entailment. Useful positive answers, abstention and clarification have explicit strata; blanket refusal cannot pass. H06 protected fixtures are outside candidate write access, but actual evaluator separation and OS enforcement remain future checks. Every repeat must meet its family disposition; failed/partial/retry work remains inside inclusive caps. Protocol identities are kept separate: R06 E0 versus R07 E07-B, R02 baseline versus MV-P1, amended ASR48 versus MF-P0's76. MF-P1/MF-P2 are aliases, not extra attempt pools.

CONTRACTS:88–96 and MULTIMODAL preserve F08 source class/support, native locators/clock/PTS/frame/calibration, uncertainty/dependence/lineage and current authority. Required digest-bound sidecar, loss rejection/limited table and current reimport checks survive. MF-L01 is explicit in MULTIMODAL_CASES:277,550,602, EVALUATION_PLAN:38 and MF-P0: missing sidecar, mismatched digest, stripped essentials and changed-authority reimport must be frozen within76 invocations or versioned before results. No row is reported as executed. Unknown dependence cannot create independent votes; styling/simulation/illustration cannot become measurement.

**R15 integration and foundation compatibility — PASS, conditional.** ARCHITECTURE's Observatory section and WP-R15-0 preserve fork81eb44340d90feda5b5283438f6e5fdad5cabbdd, corrected tools→controls→data→scene phase stop order and within-phase LIFO. They retain pending/uncooperative startup and page/global ownership as proof obligations, not guaranteed termination. Default keyless network providers, tiles/fonts/voice/broker remain excluded from the first zero-egress proof. Default iframe denial, parser v6 versus prose v5, source/data/media rights, exact import/asset allowlist, original fixtures and the120-minute proof remain explicit. F08/whole-output256KiB is not enlarged by Director bundle or raw ingest limits. Thin2D/table fallback stays bounded and can win the comparison.

ARCHITECTURE:11,56 preserves Python3.12/FastAPI/Pydantic2/Jinja2/one Uvicorn worker/SQLite and unchanged M4 advisory pin. The original baseline/cumulative-v1.0/AGENTS.md:22 and recovered Gen0 plan:37 explicitly say one worker; this is process count, not a new Uvicorn version. No active-foundation rewrite or migration is introduced. Original12 inert contracts and CR identities remain mapped without pretending wire compatibility.

## All14 future packages

All have exact input pins, nonempty ownership/reviewer, approved-path activation, boundaries, prerequisites, tests, finite time/resource ceilings, stop conditions and ready prompts. All statuses are AUTHORIZATION_REQUIRED. Their allowlists are disjoint and target future/ or the Observatory prototype/test directories, not active application paths. Numeric host/native/model ceilings unresolved by the research must freeze before the corresponding grant; these are proposal templates, not immediately executable command approval.

| Package | Reviewed acceptance limit |
|---|---|
| CORE-P0 | No worker/model/provider/device; useful two-person transactional answer plus full-vector, quota, duplicate, unknown, restore and closure tests; three bounded suite runs |
| MF-P0 | Synthetic source-table versus typed composition; no decoder/executor;36 families/76 total invocations, zero extra retries, F08/MF-L01 retained |
| R02-P02-A | Actual source and independent observer first; one owned worker/topology, parent-loss/startup/cancel/containment;5s cleanup is a proposed target, not a guarantee; CF-L01 applies |
| R02-P02-B | CORE-P0 plus lifecycle prerequisite before integrated termination claim; parent reservation/release/correction/unknown/restore traces |
| R02-P03-EVAL | Exact artifact/rights/host/oracle and VA-01/adapter closure;24 families×3≤72, no hidden retries or hosted fallback |
| MV-P1 | Two exact qualified routes×24 groups=48 inclusive; one resident model/worker; MF-P1 alias creates no new pool |
| P-MMAV-02-ASR | Accepted material amendment; small/medium int8 CPU,48 inclusive, no repeats; MF-P2 alias; microphone/video/TTS excluded |
| R08-P00-INERT | Exact scalar/time/correction identity,20 families/160 events; no executable design, machine, metrology or pose promotion |
| R05-AGENDA-LOCAL | Synthetic finite agenda,32 cases; account switch is not device handoff, C09 refinement still awaits H06 amendment; no OAuth/provider writes |
| R07-TYPED-REPLAY |24 typed traces plus4 mutants; unknown support and exact semantics; no sensor/model/motion qualification or R06 protocol pooling |
| R11-PUBLIC-REPLAY | Public variant and G1–G5; separate receipt layers and individually capped experiments; no real help message, radio or private relay |
| R14-STAGE-A | Rights/exposure/person/session/idle-data feasibility dossier only; no inference/human acquisition; STOP/REDESIGN can be correct |
| R09-DOMAIN-REPLAY | Inert skill/recovery/exclusion,24 families plus fixed mutants; no motor/simulator actuation or hardware qualification |
| WP-R15-0 |120min zero-egress/lifecycle/rights proof, then≤24h prototype;12 fixtures/3 simulated resources, protected tests,60min session,200MiB fixtures,2GiB browser target/4GiB test ceiling |

These are alternatives and ordered prerequisites, not an automatically authorized batch. Later source acquisition, native/device work, physical experiments and human studies remain in their original separately gated packages.

## Configuration, import and privacy

Read current .codex/config.toml and all10 role TOMLs. Config SHA e707b5f47198a83d1ea16d910fe2286daf05066f98d45e067071f96df7bb9fc0 and code-role SHA bef693eb967ddc646271b07cd92980a3acee7a6f1eef13179cc58ed5a44256be match CODE-0. The three-child configuration, no model overrides and no recursive spawning are requested policy, not verified runtime enforcement. state/run.json:9–26 still explicitly records effective broad permissions, CUSTOM_PROFILE_FALLBACK and exact model NOT_EXPOSED. Final synthesis does not turn those settings into OS isolation or proof automatic profile loading occurred.

Campaign .gitattributes:1–2 uses * -text, SHA fa6a58c44027baffd076001100c39c5982264278704933eec2219a6cff2b4de7; root attributes preserve historical directories. The dormant source-import workflow was reread statically and remains hash497eb96b1742b99e502590c393db48587536074365c2430ae7b899195b49cec2. It is main/marker-triggered, privileged for its sealed exact-byte import, and remains outside this campaign's activation authority. .import/RUN_ONCE.json is absent. No workflow ran, and no extraction implementation was newly supplied for audit. Historical recovered producer/redaction lineage remains the narrower CODE-0/EVIDENCE-0 receipt; the redacted gate is not an identical original artifact or a rerun.

Root's CANDIDATE_DIFF_SCOPE lists505 paths, all under this campaign; no workflow/config or quarantined original research/R11 path appears. This is a checked root-supplied diff receipt, not an independently executed Git diff or remote publication check. Immutable archived Python copies do not mean active application code was changed. Public pattern scan of final-v1 found no host absolute-path/user-name or common credential-marker hits; it is not a universal privacy proof. No private R11 original, runtime database or source archive was opened for this final review.

## Tests, proposed reproductions and remaining evidence

**New tests ZERO; application/build/model/native/physical tests executed ZERO. NO_APPLICATION_CODE_CHANGED. Current M0/R1 CODE_NOT_AVAILABLE.** Historical N1=33 and N2=11 saved passes were not rerun. CODE-0's actual static tests support bounded synthetic quote/visibility/persistence/timeout/arithmetic behavior, not semantic intelligence, parent-loss containment, protected metrology or current production safety.

Future separately authorized reproductions: concurrent max_uses=1 admissions and exact duplicate consume; crash at before/after claim/outbox/receipt commits; lost consume reply followed by revoke and reconciliation without resend; uncited-source revoke and tombstone propagation into rejected/raw contexts; stale restored epochs versus ordinary inert scene import; independently observed parent death/startup/cleanup and adapter escape; protected semantic relevance/contradiction cases; the four MF-L01 mutations; zero-egress GEV import and delayed constructor destruction. Every item is NOT_EXECUTED. Retain original failed trials and unknown observations.

No required research correction remains. CF-L01 and all earlier runtime/native/rights/oracle gates must be resolved at activation or qualification, not quietly counted as completed by this PASS.

## Brief peer check-in

Strongest own contribution: directly comparing the integrated authority/accounting/import/lifecycle text and all14 package prompts against exact accepted boundaries, with independent identity checks. Weakest: static documentary review cannot establish host enforcement or user benefit, and most upstream external literature was reused through accepted reviews rather than freshly replicated.

Most useful consumed peer artifact: reviews/REVIEW-MM-FUSION/REVIEW.md, c244ac41c7a443839c66725356db434f4b4da73d36811362654cd067c73ae9dd, particularly F08/MF-L01 conservation through the renderer/export seam. Its independent upstream role and my earlier R15 review remain distinct from this manager-authored final candidate.

Biggest risk: an implementation later treats structured fields, local mock authority or copied receipts as actual isolation/current permission. Highest-value next action: one explicitly granted protected positive-and-negative CORE-P0 slice; obtain actual current R1 source and observed lifetime/adapter proof before the model route. Confidence HIGH in documentary identity and retained invariants; MEDIUM in proposed integration feasibility; runtime/scientific/physical qualification UNKNOWN.

Signed `/root/ri01_code_review` — haven_code_reviewer — CODE-FINAL — 2026-09-29 UTC.