# REVIEW-R03 — Independent privacy and authority review

Thread R03 / H04 / issue #17. Reviewer /root/ri01_review_privacy, haven_research_reviewer; 2026-09-28; exact model NOT_EXPOSED. Repository https://github.com/erpzz/haven. Root-reported base 376031e182c57495912baf6727093b0b188da568. Campaign prefix campaigns/RI-01/ri01-20260928T180322Z-6e8f/. Paths below are relative to that prefix unless stated otherwise. Read-only inspection; owned paths changed NONE; child NOT_UPLOADED. Root owns persistence/publication. No Git, application/test execution, installations, accounts/devices, private-data collection or children.

## Decisions

Overall AMEND, with the substantial architecture and bounded research conclusions ACCEPT_FOR_SYNTHESIS. One MEDIUM contract clarification is required before finite-use release semantics are frozen for R03-P0. It does not hold unrelated public research, source reconciliation, CORE synthesis or the existing R03 identity/lineage/deletion design. No HIGH defect or unsupported deployed-capability claim was found in this pinned handback. Research acceptance is not operator implementation permission, executed acceptance or physical qualification.

R03 usefully resolves R02 F01's vague immediately-before release rule: one authoritative short write transaction, complete revision/epoch dependency vector, an immutable release receipt, a separate destination consumption operation and attributed delivery observations. It explicitly admits the consume-before-remote-display race, offline withholding, already disclosed bytes and DELIVERY_UNKNOWN. R03's own ReleaseReceipt, ConsumptionPermitReceipt and DeliveryReceipt do not conflate authorization with delivery (CONTRACTS.md:56–73). No assumption about the parallel P01 amendment is needed for this finding.

Accept the distinctions among actor, subject, resource steward, rights holder, audience, device/service/job and sponsor; joint-source intersection including uncited influencing context; independent A/B enrollment; provider/endpoint restrictions; separate egress, digital-write, sensing and physical-dispatch operations; scoped cancellation observations; retained admitted unknown budget exposure; corrections, content-minimal deletion receipts and review-only restoration. Preserve the shared-host administrator limit and native-endpoint uncertainty.

### Required finding

REVIEW-R03-F01 — MEDIUM — Finite grant use versus release/consumption is under-specified. Anchors research/R03/CONTRACTS.md:17–19,62–69 and research/R03/EXPERIMENTS.md P20/P21. A count-limited grant updates its use count at authorize_release, while consume_output subsequently performs fresh validation and one-time consumption. For max_uses=1, the first release exhausts the grant: the contract does not say whether that admitted operation can consume its reserved right, how use-count updates relate to grant revision/vector equality, or how a new replay after a lost permit is charged. Straightforward interpretations can reject the one permitted answer, consume twice, or exempt later releases from the limit. This is a specification ambiguity, not a reproduced failure.

Required closure: name the counted operation and a durable exact-operation grant-use/claim binding; separate eligibility for admitting a new use from fresh revocation/expiry/source/device checks on an already charged use; state whether accounting updates affect authorization revisions; specify lost-reply, abandoned-release and explicit replay charging without automatic refunds or reminting. An alternative minimal P0 may explicitly exclude finite-use grants and reject that unsupported profile; it must not silently claim max_uses support. Add a finite synthetic case family/subcase: max_uses=1 permits at most one admitted release and its one matching consumption without double-charge; concurrent second release denied; duplicate keys do not consume again; revoke/expire between release/consume still denies; lost permit stays uncertain; explicit replay needs fresh eligible quota. These are proposed checks, NOT_EXECUTED. Q-R03-USE-01 was actually routed to root; no author response was received and no agreement is inferred.

### Nonblocking integration follow-up

REVIEW-R03-L01 — LOW — Preserve the author's dated interim CODE-0 attribution, but attach the now-available final review before downstream package freeze. REPORT.md:81,142; INPUT_USE.json final row; NEXT_PACKAGE.md:7 correctly said final pending at author time. Reviewer read and hashed final reviews/CODE-0/REVIEW.md SHA256 066bbc38273320895dbd5cf1fc3fde31c209253103fa2e170dbf905ff8d4abc8. Its CODE-M1 confirms the attributed retained-context/rejected-output/metadata gap; R03 CONTRACTS F already includes those classes. CODE-H1/H2 and M2–M5 retain termination, release, semantic scoring, durability/evaluator and configuration limitations. No contradiction requiring a research restart was found. Record this reviewer cross-check/addendum rather than rewriting historical evidence as if the author had read the final report.

## Evidence

Read all eleven R03 files: REPORT, CONTRACTS, EXPERIMENTS, INPUT_RECEIPT, INPUT_USE, SOURCES, NEXT_PACKAGE, CONSULTATIONS, ARTIFACT_CHECKS, MODALITY and MANIFEST. Read governing root/coordination/RI-01 documents and exact reviewer profile; exact incoming R02 CONTRACT_DESIGN, R06 CONTRACT_PROPOSALS, R08 INTERFACES_AND_CONTRACTS; REV-R02/06/08 complete reviews and R06/R08 source registers; final CODE-0; baseline privacy prose; recovered canonical privacy requirements, all nine AT-PRIV entries and original EX02/EX32. Inert-schema key restrictions were inspected. This does not claim a fresh whole-laboratory code audit or all upstream literature reproduction.

Independently computed all supplied pins: REPORT 5b2029bb8b292f8ebef3ef89a1a4442c27b6c8545cad3f7820854817a7c2368d; CONTRACTS cfd271d1650e40daa735651ddc2ab28ca4ccdcb17f117c96cc5602975bad5eea; INPUT_USE 42e57e4531e1c2b80e487c17ca7876af8c6b18c263094f749660396926eb060e; MANIFEST e154d038cd1eedf1dcfa7acefc29ddb31c88cd5d36b56573a3dc5e344405a4ac. All match. Independently hashed all ten manifest rows: zero mismatches. INPUT_USE has 25 records; 24 hash-bearing records represent 18 unique files, all matched. The remaining row explicitly attributes an interim message with null hash. Counts independently confirmed: 15 CR rows, 24 proposed P cases, 102 canonical requirements.

Exact upstream contract hashes matched: R02 9cc1ce4ce5d2d240b244513aa7680ba0015d86829216497877f3f90cd51856d7; R06 e4833cb18364235110065b2f702a1e67dfa552de78c0769dde6b32288432bf13; R08 01ed60d55591b3d4a2a03cafaf4c299d24c1c9f47d406d68bd3dd2bac6d02f03. Accepted-review pins matched INPUT_RECEIPT. The 25 input-use records describe actual downstream choices/reasons rather than titles alone. Local bytes are verified; Git reachability/pushed blob identity and original ZIP fidelity were not independently rechecked. Source commit and copied local path should be resolved using INTAKE's source_path/path mapping, not treated as the same path at the source commit.

Current primary-source checks, performed 2026-09-28 through public documentation text:

| R03 source | Independently verified support and limit |
|---|---|
| S01 | [SQLite isolation](https://www.sqlite.org/isolation.html) supports serialized writers, snapshot distinctions and acquiring write eligibility before subsequent reads. It does not establish a remote-display transaction or tested Haven behavior. |
| S02 | [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html), January 2025, supports redirect matching, PKCE, restricted audiences/privileges and applicable refresh-token protections. Exact client/provider conformance remains untested. |
| S03 | [RFC 7009](https://www.rfc-editor.org/rfc/rfc7009), August 2013, explicitly discusses propagation delay and successful responses for invalid tokens. Local disablement and provider outcome must remain distinct. |
| S04 | [WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/), §§13.4.9/14.2, supports origin validation, RP scoping and credential identifiers not directly identifying people. R03 does not claim native implementation or transaction consent from authentication. |
| S05 | [NIST SP 800-88 Rev. 2](https://csrc.nist.gov/pubs/sp/800/88/r2/final) confirms final publication September 26, 2025, superseding Rev. 1. Its sanitization definition does not establish deletion of every plaintext/key copy. Abstract/metadata inspected. |
| S06 | [ICO erasure guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/right-to-erasure/) supports backup operational exclusion, scheduled replacement and transparent limits. R03 appropriately treats this as UK-specific guidance, without deciding Haven’s legal obligations. |
| S07 | [MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) supports per-client consent, audience validation and prohibition of token passthrough. It does not certify installed connectors. |
| S08 | [SQLite secure_delete](https://www.sqlite.org/pragma.html#pragma_secure_delete) confirms FAST/free-list and virtual/FTS shadow-table limitations. Application inaccessibility remains distinct from forensic erasure. |
| S09 | [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final), August 2020, supports no implicit trust from location/ownership and distinct authentication/authorization. Abstract inspected; no deployment certification. |
| S10 | [Apple Data Protection overview](https://support.apple.com/en-au/guide/security/secf6276da8a/web), December 19, 2024, supports protection classes and key accessibility. It does not establish privacy of Haven’s actual unlocked processing or output routes. |

No material source contradiction found. Mutable response bytes were not archived. No provider accounts, media assets, models or executable tools were acquired. Upstream RF/engineering source observations remain attributed to their exact reviews; this review did not reproduce their experiments or recheck every upstream citation. No new license grant follows from public access or a consent record.

## Interface changes

No files or canonical interfaces changed by reviewer. R03 proposes a separate namespace and retains inert v1 boundaries.

All fifteen dispositions were checked against the exact source contracts and accepted review limitations:

| CR | Review assessment |
|---|---|
| CR-R02-01 | AMEND direction supported: vector and distinct cancellation/containment states; actual worker termination remains open. |
| CR-R02-02 | AMEND direction supported: named release/consume ordering resolves the principal F01 design gap; carry REVIEW-R03-F01 for finite-use accounting. |
| CR-R02-03 | ACCEPT bounded provenance extension supported; subject/lineage/authenticity checks do not establish truth or physical qualification. |
| CR-R02-04 | AMEND supported: authority, budget and execution remain separate; admitted unknown exposure cannot disappear on expiry. |
| CR-R02-05 | AMEND supported: typed domain mapping without generic execution or conversion of proposals into grants. |
| CR-R06-01 | ACCEPT supported: mandatory paired sidecar/version/hash and unknown states; exact adapter remains H08/R07-owned. |
| CR-R06-02 | AMEND supported: multi-subject/rights/session intersection, public-human distinction and acquisition footprint. |
| CR-R06-03 | AMEND supported: fixed acquisition catalog, separate motion permission and distinct stop observations. |
| CR-R06-04 | AMEND supported: 60-second total episode, maximum eight attempted selections; eligibility expiry does not prove hardware stop. |
| CR-R06-05 | ACCEPT bounded immutable qualification successor supported; actual promotion remains deferred. |
| CR-R08-01 | AMEND supported: authenticated protocol review, parent budgets and independently protected evaluation. |
| CR-R08-02 | AMEND supported: template-only first executable profile and material/lot/orientation/assembly invalidation. |
| CR-R08-03 | AMEND supported: authorized recorder plus exact H08 pose convention; measurement accuracy remains unqualified. |
| CR-R08-04 | AMEND supported: exact sealed-job/machine/boot/supervision dispatch attempt, separate from publication; uncertain send forbids automatic replay. |
| CR-R08-05 | AMEND supported: reviewer authority, competence, independence and exact qualification scope. |

Joint-source semantics are conservative and coherent: all influencing parents remain dependencies; provider/audience restrictions intersect; a minimized excerpt does not automatically detach its source grants. The R01 consultation is accurately labeled advice without returned acceptance.

Deletion covers successful and rejected outputs, request/context metadata, derivatives, queues, provider references and backups. Restoration cannot authenticate its own obsolete grants; new epochs and current authority reconciliation are required. Offline cached private/shared output is unavailable for new release without verification, while prior disclosures remain historical facts. These are explicit proposed semantics, not implemented guarantees.

## Acceptance

Actual checks were read-only PowerShell file reading, SHA-256 hashing, JSON parsing and structural counting, plus primary web-document inspection. No application, model, authentication, deletion, native-device, RF or physical tests ran.

All 24 P01–P24 families remain **NOT_EXECUTED**. The proposed scheduler includes useful release/consume/display boundaries, competing connections and unknown outcomes. The utility gate avoids treating universal denial as success. The remote race is visibly reported rather than silently counted as a privacy pass.

REQ-PRIV-01–09 and AT-PRIV-01–09 retain their original identifiers and substantive purposes. Original EX02/EX32 remain proposed. P0 provides finite synthetic evidence only; borrowed devices, independent enrollment, native output behavior and administrative threat acceptance need later evidence. Synthetic image references do not establish visual understanding. R03’s documentation-only modality receipt is accurate.

No observed defect justifies demanding unavailable current M0/R1 source to qualify this research. Current active M0/R1 remain **CODE_NOT_AVAILABLE** within this review; archived code findings are separately attributed to CODE-0. Parent-death containment remains a prerequisite for transferable worker claims, not for documenting or testing an inert authority protocol.

## Risks and open questions

The finite-use clarification is the only identified required contract amendment. The final CODE-0 cross-reference is a nonblocking integration follow-up. Original H00/R1 review and original R03 prompt gaps remain explicit; their contents were not reconstructed.

Production retention schedules, trusted identity recovery, endpoint compromise, real output buffering, provider deletion, hardware stop and storage sanitization remain unqualified. Their absence blocks the corresponding production promotion, not P0 design work. Suggested latency, memory, artifact-size and coding-time ceilings are proposals without measured fit.

## Next package

Retain the bounded R03 architecture for synthesis. Resolve Q-R03-USE-01 through a small versioned amendment and focused reviewer recheck, preserving the pinned draft. Add the final CODE-0 cross-reference. Freeze the relevant CORE/R02-P01/R03 interfaces before separately authorizing R03-P0.

R03-P0 remains useful: deterministic synthetic selected-record answers, transactional authority checks, simulated destinations and review-only restoration. It needs no hardware purchase, hosted inference, real accounts or current M0/R1 implementation. Keep actual implementation authorization separate.

Signed `/root/ri01_review_privacy` — haven_research_reviewer — REVIEW-R03 — 2026-09-28. Overall **AMEND**; substantial bounded subset **ACCEPT_FOR_SYNTHESIS**. No implementation or operational permission granted.
