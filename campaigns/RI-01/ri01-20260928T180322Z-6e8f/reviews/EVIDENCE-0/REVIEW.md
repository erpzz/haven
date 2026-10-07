# EVIDENCE-0 independent early source and test-equivalence review

## Metadata

Role/task: haven_evidence_auditor / EVIDENCE-0; actual native agent `/root/ri01_evidence`; research R13 / owner H06. Repository https://github.com/erpzz/haven; observed checkout HEAD376031e182c57495912baf6727093b0b188da568. Reviewed recovered PROVENANCE, SUPPLEMENT1–3 and INTAKE revision1. Root persisted the returned report and round1 closure amendment. Reviewer made no writes or Git mutations. No local archive paths published. New application tests: ZERO. No imported application/installer/model executed; no child spawning.

## Decisions / integration summary

Disposition CHANGES_REQUIRED for unrestricted synthesis claims; PASS for exact recovered-byte identity and scoped preservation. Historical source/evidence may be used with the limits below. This is not final campaign review, current-workspace verification, R1 closure, M0 acceptance or Haven qualification. Retain all102 original REQ/AT mappings,32EX,Gen0T01–T35 plus research-testR01 (distinct from research laneR01).

## Evidence / input fidelity

Independently matched both designated archive hashes: HAVEN_Tonight.zip=0e3c76550e63f65669fa0b6f6bc76516f89c43835377b16dc60a1088e7ffddfe; HAVEN_NIGHT_01_Review.zip=4bea43265cbc4f7cbe45c31fb76ad2368aa7bc1802bf3f4bdb95a1e7ec5cb67b. Every132 original manifest member matched recovered size/hash and named ZIP member hash:98starter+34NIGHT01,132unique paths/members,0mismatches. Supplements add2finalsuite logs,9finalN2replay files,1redactionmanifest: total144 independently verified recovered source/evidence files. Original archives contain153/242entries; selected recovery is not complete publication. Starter MANIFEST has145entries:97recovered match,48absent; manifest itself is98threcoveredfile. Missing is not corrupted.

Catalogs:102uniqueREQ,102uniqueAT,32uniqueEX,22cases,39sources,12draftcontracts,13Hownerrecords. No broken REQ→AT,AT→REQ,EX→REQ links. REQUIREMENT_COVERAGE has identical102IDs and unchanged original fields, adding18N1synthetic-subset,11N2synthetic-orchestration-subset and73retained-future-target rows. All102 original AT remain NOT_EXECUTED; all32EX PROPOSED_NOT_EXECUTED. Presence does not verify external scientific claims.

Final N1 log has33unique IDs exactly matching recovered test methods; N2has11. Both exit0,zero failures/errors/skips,all EXECUTED_PASS. All17 source hashes in each log match recovered lab; all12 N1_GATE source hashes match. Historical synthetic execution is source-backed, not rerun here. Saved commands use /usr/bin/python3 -B run_checks.py n1/n2; runner requires Python3.12, but this reviewer did not independently inspect a current interpreter. Missing-final-log finding closed by SUPPLEMENT1; retain correction history.

## Severity-ranked findings and corrections

### E0-H1 HIGH — R1 lifecycle remains unqualified (OPEN)

backend.py bounded_call starts a fork child and performs join/terminate/kill cleanup only in coordinator finally. Abrupt parent death can bypass cleanup. test_real_timeout_is_bounded_and_never_success checks sleeping child while parent survives. test_incomplete_job_returns_unknown_without_resume manually rewrites completed ledger row to RUNNING. Neither is coordinator-kill/worker-survival regression. Preserve WORK-R1 unresolved; require separately authorized Python3.12 reproduction, bounded lifetime repair and independent regression before closure. No reproduction executed. Withheld/unknown output is not stopped computation.

### E0-H2 HIGH — N2 gate lineage (CLOSED FOR HISTORICAL PUBLICATION LINEAGE)

Initial selected5127run results SHAca15ce03f22b7752bf11ebcedb13f06692b88ef001dbd372062e683daf3ef097 executed2026-09-28T03:10:47.930549+00:00 referenced gate361ad36232e73cbd0cf8ba738cad1358d25b705c51245cba4ede1480b7c4a0e6, unlike final recovered N1_GATE d1e330280582a181a5a7750b24ff56b12ad9740b12a09d47e3adc1d9749da66c. Initial finding correctly required lineage rather than inferred final closure. PowerShell display converted the timestamp; literal UTC above supersedes the earlier displayed offset.

SUPPLEMENT2 recovered finalfe154 replay results SHA580cc97ba33a1f4c4a6ec3b1a0a0942e713b9175bc46771ca0a248d2846b6aa0, executed2026-09-28T03:21:02.310054+00:00, gatef2b62ee7cdb926032b6d846c6adb91f990179e94c06b71782ffe8c7113a63019. notebook.py line65 hashes raw gate_path.read_bytes and line148 stores identifier; canonical JSON was not the definition. Recovery alone did not close the mismatch.

Round1 closure independently verified exact REDACTION_MANIFEST.json,3211bytes,SHAa662d067ee7723b123ceb617bf6e529726787fd3bbd42e66747be5722e94aca0. Producer receipt explicitly maps privatef2b62ee7cdb926032b6d846c6adb91f990179e94c06b71782ffe8c7113a63019 to reviewd1e330280582a181a5a7750b24ff56b12ad9740b12a09d47e3adc1d9749da66c for local path/host redaction. Final replay reference matches private hash, recovered bytes match review hash. Mismatch therefore has documented provenance. This verifies consistency with a producer-authored transformation receipt, not independent reproduction from private original bytes. Private bytes were not inspected or republished. Earlier gate has a receipt mapping too; its public historical gate was not separately recovered by auditor. Original findings and immutable source files are preserved.

### E0-M1 MEDIUM — Complete-import/N0 claims exceed selected evidence (OPEN LIMIT)

ACCEPTANCE_MAP references absent package-validator/unit-test logs and PRESERVATION_FINAL. Original manifests refer to omitted docs/nested archives. Say selected exact recovery; N0 complete-import claims remain unverified unless exact evidence separately recovered/reviewed. Active M0/NIGHT01/R1 trees were not inspected and are not this snapshot.

### E0-M2 MEDIUM — Explicit later-scope mapping (REQUIRED IN SYNTHESIS)

Real consultation Q001: Gen0 retains S1→T32,S2→T33–T35,R0→research-testR01; coreT01–T29,WatchT30–T31 separately. M0–M6 roadmap abbreviation T01–T31 does not establish deletion because later S track remains. Publish all mappings, preserve independent gates and NOT_EXECUTED state.

### E0-L1 LOW — Scoped rights/privacy (ONGOING PUBLICATION LIMIT)

Selected text/code/JSON and targeted scans found no credentials, real health records, household media, runtime DBs or measured host inventory; fixtures use TEST_USER_A/B. Originals retain project owner attribution including full name in historical architecture, and N1_GATE contains redacted /home/<operator>/. Do not call originals fully anonymized. LICENSE_NOTE imposes no new OSS license; links retain third-party terms. Current scoped user authorization supports publication, not invented redistribution/commercial rights. Preserve license note and review new imports separately. No third-party media/model weights imported.

## Interface changes / test equivalence

No application/schema change. CONTRACT_MAPPING explicitly states local NIGHT01 mapping, not wire-compatible production adoption. N1 supports deterministic fixture quotation, test-principal isolation, purpose/revocation checks, inert proposals, bounded normal timeout and synthetic ledger behavior. It does not establish authentication, live-model quality, OS egress isolation, whole-PC durability or abrupt-parent lifecycle guarantees. N2 supports fixed arithmetic, retained negative candidates and rejected physical promotion; writer-authored checker is not independent physical metrology. No CAD/sensor/robot qualification. Inspected modalities: text/code/JSON only; no direct image/audio/video/sensor inspection or Haven runtime test.

## Source verification limits and exact identities

INTAKE INVENTORY.md SHA9aa57516443d56e969ddadaacf160dd7714989c3d4f01e638bb7a7012f15c6e4 read in closure. GitHub inventory is attributed to intake, not independently re-queried by auditor. R02/R06/R08 substantive recommendations not assessed in this assignment. Missing original H00/R1 reviews/prompts/archives and currentM0/R1 limitations apply. Agreement is not physical validation; source-fidelity assignment did not re-research volatile external catalog claims.

PROVENANCE.json SHA1d60bb74ab3e6de17274009a66d157b4a5edf59654f6e7ee6ea2dba0db3beb7d; SUPPLEMENT1 64856c4902836ef94e7f13235abd75c164f741f3b27f9e1988dc1f63a77e6811; SUPPLEMENT2 7e5f84fab9a6ef137e60db1ffa4f3fbe0e5c06686a90bd8cc1036812f5987a09; SUPPLEMENT3 abc7ccb96dd3e64d97f10263b44a3bf3e6b3febb363d71a51b9e233861f8d80e. Their rows preserve individual exact identities. SOURCE_SNAPSHOT SHA1bc2d6af12b9b4a502015934528f45e9560b77b7f059377bc7b070bfe2b67435.

Canonical requirements SHA b904206fefcd553003129bfc30ede87785ff3325a13657f162125b3868492f56; ATcatalog d41660b25a5b105024083cf4c3c0e914c92dc4b68afef60be4649153ab06b478; EX 8d58513cc21daec045b14a0f4f3f0c371241ab9cdac02e303f6bd19debb4411c. Gen0 b599da50679bedb9612cc4613e46ecfe616f448884b5ad4731748ca5aed68771 sections/milestone234–243,test308–312,acceptance343; COVERAGE a9d3dd7171220ee2a29ca99f969edeaa2ba9f15af5dde82045314180677cb5a2.

## Acceptance and next package

144recovered identity checks PASS; catalog links PASS; saved historical33/11suite support verified without rerun; finalN2 lineage CLOSED with transformation-receipt limitation. R1/currentM0/N0complete-import/physical qualification NOT_ESTABLISHED; original AT/EX NOT_EXECUTED. Affected dependents VISION0,CODE0,R13,R02-P01,R08-P00 and synthesis. Scoped evidence use supported; any synthesis claiming R1 or completeimport qualification requires changes. Preserve findings for final independent review. Zero repairs or runtime tests authorized by this review.

Signed `/root/ri01_evidence` — haven_evidence_auditor — EVIDENCE-0 and closure round1 —2026-09-28. Child NOT_UPLOADED; root persistence only.
