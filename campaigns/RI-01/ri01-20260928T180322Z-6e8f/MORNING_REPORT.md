# RI-01 operator review handoff

Status: RESEARCH_COMPLETE; OPERATOR_DECISION_REQUIRED for any proposed implementation. All three final reviews passed for the unchanged frozen candidate. The completed files were published and read back successfully. Final PR metadata remains PARTIAL: automatic approval review blocked the description update and ready transition; user confirmation is pending. See state/PUBLICATION_RECEIPT.json. Research acceptance is documentary; it is neither implementation authorization nor demonstrated application, model, device or physical capability.

## Run and publication

The campaign began 2026-09-28 at 18:03:22 UTC on the actual Windows desktop, using a separate designated Haven checkout. An account interruption occurred and the operator explicitly resumed work after restoring the session allowance. The original eight-hour wall-clock ceiling remains in force: stop new work at 2026-09-29 01:48:22 UTC and stop by 02:03:22 UTC. No extension is assumed. Research and final reviews completed at 2026-09-29 01:35:41 UTC, 7 hours 32 minutes 19 seconds after launch. Publication status was recorded at 2026-09-29T01:49:22.029918+00:00; this metadata checkpoint precedes its own final push and readback.

The frozen research candidate is published at commit `c087bf9c00cb9213dc3225852fb7385ba0eb9aef` on `campaign/ri01-20260928T180322Z-6e8f`. Fetch, ancestor check, push and exact remote-ref readback succeeded. [Consolidated PR #19](https://github.com/erpzz/haven/pull/19) contains the completed review handoff at `b530d1a8ce127ccb868b59d5e62e0d2556f21305`, verified by exact remote-ref and seven public-file byte comparisons. It remains a draft and its older description still says reviews are running; that description is stale. The blocked metadata update is recorded in the publication receipt. Main remains based on `376031e182c57495912baf6727093b0b188da568`; the wave-07 refresh found no changed upstream research heads or new substantive handbacks.

Start with [the architecture](integration/final-v1/ARCHITECTURE.md), [full multimodal design](integration/final-v1/MULTIMODAL.md), [implementation queue](integration/final-v1/IMPLEMENTATION_QUEUE.md), and [retained scope](integration/final-v1/RETAINED_SCOPE.json). The candidate manifest is `integration/final-v1/MANIFEST.json`, SHA256 `c5ec562b5ea5390962ab8334b39f397e959a071a4314c3b17898ec991b3ede1b`.

## Actual delegation and completed research

Twelve native agent handles participated across 63 conservatively counted assignments, including reruns and bounded supplementary reviews. At most three children plus root were active concurrently. Actual dispatches, identities, completions and failures are in [the agent ledger](state/agents.jsonl) and [task state](state/tasks.json). Custom role instructions were supplied explicitly; automatic profile loading and exact model identity were not exposed. Completed native turns are quiescent; no explicit close tool is exposed. Per-agent token attribution and session cost are unknown, not zero. The goal service reported 11,259,919 cumulative tokens and 15,766 usage seconds at 2026-09-29 01:33:54 UTC; these counters are not independently reconstructed billing or elapsed wall-clock time. Later root publication adds usage. See [the usage receipt](state/USAGE_RECEIPT.json). No additional paid-provider calls were made.

The campaign reviewed the existing exact R02 publication-v2, R06 and R08 handbacks from their incoming PR heads. It completed R02-P01 and R08-P00 reconciliation, R01/R03/R04/R05/R07/R09/R10/R11/R12/R14/R15 research, and the MM-VISION, MM-AV and MM-FUSION lanes. CORE and final synthesis were authored by a separate integration manager. Each substantive research handoff has an independent disposition and exact predecessor-use records. Original R01-R13 prompt material and some historical owner reports remained unavailable where recorded; new RI-01 briefs were not represented as recovered originals.

[Accepted inputs](state/ACCEPTED_INPUTS.json), [the source-use index](integration/final-v1/SOURCE_USE_INDEX.json) and [actual consultations](consultations.jsonl) show the exact reuse and changes. The final candidate contains 23 payloads; all 15 original hard inputs were accepted before freeze. Preliminary independent work did not weaken completion gates.

## Preserved scope and useful design

The candidate preserves all 102 original requirements, 102 acceptance records and 32 experiments without structural differences, plus 36 original Generation-0 rows (T01-T35 and the distinct research-test R01), 16 vision anchors and five user journeys. Scope retention is not a claim those tests passed. It adds 36 proposed cross-modal case families, 39 finding-to-section mappings and 14 bounded future packages with exact inputs, allowed-path proposals, prerequisites, tests, resource limits, stop rules, independent reviewers and ready coding prompts.

Seven common interfaces retain the existing foundation and domain ownership. The first useful perception target is an original selected image, a typed question, currently permitted supporting evidence and a grounded response. A deterministic composition slice is explicitly synthetic; actual perception requires its separate model and lifecycle gates. Speech, clips, spatial/RF/telemetry, wearables, new senses, robotics, aircraft, communications, engineering and the Observatory remain retained branches with concrete next work.

The Observatory recommendation is conditional composition of the pinned frontend after a bounded lifecycle, rights and zero-egress proof, with an accessible thin map/table fallback. Its recorded scenes and simulations do not become current measurements or physical authority. No framework migration, model installation or application deployment occurred.

## Material corrections and retained limits

- P01, R03 and R01 material amendments preserve full influencing authority, four separate output records, once-only grant charging and fresh consumption checks. Unknown outcomes never justify automatic resend, remint or refund.
- MM-AV's independently accepted material amendment defines an ASR-only 48-attempt comparison, with explicit positive and protected-negative strata. It supersedes the earlier positive threshold; no video, omni or TTS allocation is implied.
- R06 E0 and R07 E07-B remain different protocols. R08's conditional statistical and metrology gates remain open. R14 checkpoint exposure, person/session grouping and idle-data feasibility must be resolved before its proposed study.
- R05 AT-DAILY-08 remains partial. Account switching is not an accepted enrolled-device handoff test; the proposed C09 refinement remains explicitly unaccepted as a protocol amendment.
- MM-FUSION's MF-L01 requires explicit sidecar corruption, essential metadata loss and changed-authority reimport assertions before execution, within the declared allocation or a separately versioned one.
- The R15 source audit's A02 shutdown-order error is corrected only through [the immutable correction](research/R15/AUDIT_CORRECTIONS.md) and [independent composite review](reviews/REVIEW-R15/REVIEW.md). The original audit alone is not accepted as accurate on that point.
- An inherited 'Uvicorn 1' shorthand is clarified as one Uvicorn worker, with no new dependency version pin. Earlier frozen files are preserved.

## Independent final reviews

| Review | Current disposition |
|---|---|
| [R13 evidence](reviews/R13/REVIEW.md) | PASS: documentary synthesis; no blocking findings |
| [Vision](reviews/VISION-FINAL/REVIEW.md) | PASS: full retained vision and useful capability path |
| [Code](reviews/CODE-FINAL/REVIEW.md) | PASS: research candidate only; NO_APPLICATION_CODE_CHANGED |

These reviewers are distinct from the integration manager. Review agreement is not independent physical evidence. Final acceptance applies only to the exact candidate and its already accepted composites. No corrective research round was required and no candidate byte changed after freeze. [The final review receipt](state/FINAL_REVIEW_RECEIPT.json) pins all three dispositions. All owned children completed; [the lifecycle receipt](state/CHILD_STOP_RECEIPT.json) records the actual observable state.

Low-severity findings remain pre-coding gates, not research blockers: CF-L01 requires an exact current R1 source-to-isolated-copy mapping; R13-L01 requires binding upstream package aliases to the exact queue version, subset and paths. MF-L01/R13-G01 export/import assertions and R13-G02 device-handoff coverage remain unresolved before execution. See [the complete promotion gates](reviews/R13/PROMOTION_GATES.md). No proposed package is authorized by these PASS dispositions.

## Checks actually performed

Actual work includes public primary-source research, static inspection of supplied code, exact SHA256/Git-blob checks, JSON parsing, original-record structural comparisons, source-use review and bounded public-content scans. Root verified all 23 frozen candidate payloads against their hashes and lengths. Reviewer checks independently covered the accepted research composites; their full versus targeted read scopes are recorded. Source cache identity does not mean every cached file was read semantically.

Direct development image inspection and selected locally rendered PDF pages were exercised and recorded with source identities and transformations. Direct audio/video inspection was unavailable in this run. Browser/media decoder availability did not become a claim of playback or browser testing. Generation was not used. Manager synthesis did not claim new media observation from attributed specialist records.

No application, model, native-device, physical or human-study acceptance tests were executed by RI-01. Historical N1 33/N2 11 results were not rerun. Current M0/R1 source was not supplied for this campaign audit; no conclusion about its present PC state or current iPhone/HTTPS acceptance follows from these reports.

## Privacy, protected work and next decision

The public R11 packet is `research/R11-public-v1`, independently reviewed after removal of local provenance paths. Original `research/R11` remains unchanged, private and ignored; root verified it was absent from tracked files and available Git history. Publish tracked or explicit reviewed files only, never the raw working tree. Private caches, credentials, runtime databases, session material, private keys and household data are not part of this delivery.

Changes are confined to this campaign directory. Main, source branches, original source records, active M0 and NIGHT-01/R1 workspaces, package/host configuration, networking, accounts, equipment, workflows and deployments were not changed by this campaign. No background job or automatic continuation was scheduled.

The smallest operator decision is whether to authorize CORE-P0 for one useful synthetic two-person authority/evidence answer. MF-P0 composition, actual-model preparation or the public Observatory proof are separate bounded choices in the queue. If actual inference is the priority, first obtain the current designated source and authorize the independent lifecycle/adapter containment package. Reviewing this PR does not start any package. Do not merge into main or begin implementation automatically.

See [RESUME.md](RESUME.md) for the stopped review gate. [DELIVERY_MANIFEST.json](DELIVERY_MANIFEST.json) inventories the exact public campaign bytes, excluding itself; [the delivery validation](state/DELIVERY_VALIDATION.json) records its bounded checks. The final observed remote checkpoint, PR state, issue receipt and completion time are in [the publication receipt](state/PUBLICATION_RECEIPT.json). Those metadata observations do not revise the frozen research candidate.
