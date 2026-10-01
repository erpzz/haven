# CODE-FINAL-CLOSURE — native independent handback

Native reviewer `01a0ef1f-a53c-7f11-896d-a2a6fb2cbdb6`; assignment 22; role `haven_code_reviewer`. Root received this actual final message at 2026-09-29 22:04:26 UTC. Root transcribed the independent text below; repository path normalization only, no verdict or finding edits. Original native message retained privately. This is read-only review, not new executable QA.

---

**CHANGES_REQUIRED — CODE-FINAL-CLOSURE, assignment22.** This consolidated handback preserves **CF-F01–CF-F04**, the original CE dispositions, inspection scope, evidence boundaries and operating restrictions. It replaces the fragmented delivery of my original report and addendum. **All four CF findings remain unresolved.** No new research or execution was performed for this return.

The existing **bounded PARTIAL handoff is acceptable as an honestly limited evidence and implementation handoff**. This is not unrestricted runtime acceptance. A later, separately authorized deterministic visit must retain the single-launch restriction and disabled model gate. This closure authorizes no restart, new suite or model call.

**Reviewer and independence**

- Native reviewer: **Lorentz — `01a0ef1f-a53c-7f11-896d-a2a6fb2cbdb6`**.
- Assignment22: **CODE-FINAL-CLOSURE**, using `.codex/agents/haven_code_reviewer.toml`.
- **CUSTOM_PROFILE_FALLBACK**; inherited model/cost **UNKNOWN**; no model override.
- Independent from root implementation/support/admin, H00 synthesis and empirical QA17.
- Native review return only; root is responsible for publication and final closure accounting.

For compact references below, **C** means `campaigns/IP-01/ip01-v2-20260929`, and **Q** means `campaigns/IP-01/ip01-v2-20260929/reviews/FINAL-QA`. All paths refer to repository artifacts.

**Exact scope and actual inspection**

| Binding | Reviewed identity |
|---|---|
| Exact executable candidate | `0b59551f36990cfb8a723f97da6d367358a8ceb5` |
| Historical evaluated revision | `487c67299445a29e0fbbdede04259565f741f587`, together with the original 37 worktree hashes |
| Exact sealed QA publication | `e567c3dc541084044e6142ae236a5d71bf64e23f` |
| Published H00 closure | `01d0c746da73546478ed4882a484f3099fa110b9` |

I read the governing instructions, specified role profile and applicable coordination/runtime protocols; the exact-candidate and QA reconciliation records; H00’s accepted contract references, EGRESS amendment, closure/carry-forward records and needed final-v1 mappings; CODE-EARLY findings and owner repairs; actual application, authority, store, supervisor, launcher, model-adapter and JavaScript source; locked configuration, relevant tests and independent public QA evidence.

I independently verified:

- **37 source files:** current worktree hashes, exact-candidate raw Git blobs and correspondence with the original freeze hashes.
- **107 public QA files:** worktree hashes and raw Git blobs at the exact QA publication.
- **94 H00 manifest inputs and four outputs:** matching recorded hashes.
- A final recheck of the 37 source hashes and key binding artifacts before my original return.

These were read-only file, hash, JSON and Git inspections. **I executed no application, tests, model, diagnostic workload or browser flow.** I read no protected private oracle or expected answers. Reported test and runtime outcomes remain attributed to QA. I did not independently reproduce the archive verification subsequently reported by EVIDENCE-FINAL.

Key verified SHA-256 bindings:

| Artifact | SHA-256 |
|---|---|
| `C/integration/closure-v1/MANIFEST.json` | `054eacd33074cb360fd195af6df6cc40e4a2277c92401532573c9b8c5b124121` |
| `C/integration/closure-v1/INTEGRATION_HANDOFF.md` | `b458b7c6942612196e82b4e529937ac6ab17cb4199be71fef07ab8d87a41abd3` |
| `Q/FINAL_QA_HANDOFF.md` | `733b1d373c42c01ef5a94b5b5b0a971bd6c002952fae9c3a0cdf93ee8041649d` |
| `Q/FINAL_QA_REPORT.json` | `09bea0b3deea2e9535ed805a6db960475c9a36b7f556ba1a7058f3e608059629` |
| `Q/FINAL_PUBLIC_MANIFEST.json` | `887f05ea92d0d1d51387415a54dd1d433bc476abcfeacd2f4fa9e26ec47bc72e` |

The correct QA-handoff digest includes **`ef5a94b5b5b0`**. The initial assignment’s shorter transcription was incorrect; the artifact was not defective.

**Material findings and required responses**

**CF-F01 — HIGH / P1: a durable-journal failure can bypass owned-process cleanup.**

Verified source: `labs/ip01/haven/supervisor.py:429–451`, `:634–646`, and `:735–760`.

In `_execute`’s cleanup path, the supervisor sets `STOP_REQUESTED` and awaits the corresponding event write at line739 **before entering the protected call to `owned.stop()`**. The event path performs journal I/O without containing an I/O failure at this boundary. A journal write/fsync exception can therefore skip process termination, termination observation and lease finalization. The dispatch loop’s error and terminal logging can itself encounter the same failure.

This is a source-supported failure path, **not an observed escaped workload in the frozen run**. A later explicit cancel/close, or parent exit, can terminate owned work; my finding does not claim otherwise. The defect is that the job’s own cleanup/deadline path does not reliably reach that termination when this journal operation fails. A remaining live workload may lack the intended UNKNOWN/quarantine treatment, and persistent journal failure can also stop dispatch.

The inspected existing broken-lease coverage concerns failure around result disposition after completed work; it does not establish safety when journaling fails **before termination**.

Required response:

- Retain as unresolved and withhold an all-path cancellation, deadline or cleanup guarantee.
- In a future authorized repair, make owned-process termination and lease cleanup exception-safe independently of journal availability. Persist the best available failure state, and quarantine when termination cannot be established.
- A later targeted recheck should inject a `STOP_REQUESTED` journal/fsync failure while a benign owned worker remains alive, then verify termination, settlement and admission behavior. **That recheck was not executed here.**

**CF-F02 — MEDIUM / P2: concurrent launcher starts can overwrite the recorded owner.**

Verified source: `labs/ip01/scripts/run.py:119–161`, `:165–175`, `:184–203`, and `:223–228`; relevant restart consequences at `labs/ip01/haven/store.py:155–168`.

The launch sequence does not hold an interprocess lifecycle lock across owner inspection, port selection, process creation and owner publication. Two simultaneous starts can both observe no owner, choose different ports and start against the same runtime state. The later owner-file write can replace the first process’s record. Because those processes have different instance nonces, a subsequent normal stop can target the recorded process while leaving the other unrecorded.

The readiness check also accepts an HTTP200 without binding that response to the exact newly launched child/instance. Store startup invalidates sessions and fences jobs, making a second live application against the same state consequential beyond a cosmetic duplicate window.

Existing serial duplicate-start or phase checks do not establish correctness for this concurrent interleaving. I did not execute a concurrent-start reproduction.

Required response:

- Retain a **single-launch, serialized lifecycle operating restriction**. Do not claim concurrent launcher safety or complete owner accounting under simultaneous starts.
- A future repair should serialize lifecycle operations per runtime directory and verify readiness against the precise child instance.
- A later synchronized two-process start test should demonstrate exactly one admitted owner and correct stop behavior. **Not executed in this review.**

**CF-F03 — MEDIUM / P2: readiness-failure cleanup can wait indefinitely after unconfirmed termination.**

Verified source: `labs/ip01/haven/model_adapter.py:244–273` and `:291–293`, with the caller at `labs/ip01/haven/supervisor.py:690–705`.

In the readiness-failure exception path, `launch_owned_server` calls `owned.stop()` but does not use its termination-confirmation result to bound the subsequent wait for the output-drain task. If termination remains unconfirmed and the process keeps its output pipe open, the unbounded drain wait can prevent return to the supervisor’s outer cleanup and terminal handling. The job can remain pending beyond its intended deadline.

The independent UNKNOWN-cleanup fixture has an important limit: `Q/RUNTIME_TRACE_SUMMARY_SUITE01.json:653` records that the fixture actually terminated the OS process and then withheld confirmation. That tests missing confirmation after termination; it does not exercise an unconfirmed live process retaining an open pipe.

This is a static failure-path finding, **not a claim that the frozen natural runs exhibited this hang**.

Required response:

- Retain as unresolved; do not claim bounded readiness-failure settlement for every termination-unknown path.
- A future repair should bound output draining, propagate unknown termination and enter the appropriate quarantine/terminal handling without relying on EOF.
- Recheck with an intentionally retained open pipe under a controlled benign fixture in a later authorized package. **Not executed here.**

**CF-F04 — MEDIUM / P2: route and progress labels remain misleading after successful model output.**

Verified source:

- `labs/ip01/haven/templates/index.html:20` hardcodes **“Deterministic excerpts.”**
- `labs/ip01/haven/static/app.js:63` posts **“Question queued”** after submission and refresh.
- `labs/ip01/haven/static/app.js:65` renders a successfully consumed answer and records the display observation without clearing or replacing that notice.

I independently confirmed this source behavior and the unchanged hashes:

- JavaScript: `3ca857311c75771d7ab972575d5afb1b067005a5bb9c8190deca939d8f9ef2fa`
- Template: `b5d485d711e392d8c50ba63fd596db7cc5f66494ddb81b28a0413c5a3748f57c`

This agrees with VISION-FINAL’s finding at `C/reviews/VISION-FINAL-CLOSURE/REVIEW.md:108`. Its direct B1 pixel observation remains attributed to that reviewer.

The boundary matters: `static/app.js:64` renders actual job disposition and compute state, and `:65` labels the displayed payload using its supplied label or **“Local model proposal.”** The defect is contradictory surrounding UI. It does not establish that the backend remained queued, invalidate B1’s successful answer, or demonstrate failed consumption authorization. The stale notice can also affect deterministic completions.

Required response:

- Retain as an open UI defect, nonblocking for the explicitly partial handoff but blocking an unqualified claim that the general image flow reliably presents its route and progress truthfully.
- In a later repair, distinguish the displayed result’s route from the route selected for a future request. Bind progress notices to the relevant operation so an older completion cannot erase a newer notice.
- Preserve CE-F02’s session-generation protection. Recheck completed, failed, denied and reload views later. **No source alteration or new execution is requested in this closure.**

**Original CODE-EARLY findings**

These are dispositions of the original counterexamples, not a blanket runtime approval.

| Original finding | Disposition and inspected basis |
|---|---|
| **CE-F01** | **Original counterexample closed within the accepted bounded EGRESS contract.** Permission propagation and the relevant prelaunch/release checks are present in `labs/ip01/haven/app.py:144–218`, `labs/ip01/haven/supervisor.py:486–565` and `:690–707`, and `labs/ip01/haven/model_adapter.py:299–346`. The interval after a final authority check remains a stated boundary; this is not instantaneous revocation or physical recall. |
| **CE-F02** | **Original delayed-refresh/consume counterexample closed.** Session-generation checks and reset behavior are present in `labs/ip01/haven/static/app.js:5–20`, `:26–44` and `:46–56`. The independent final recheck reports two passes against the final JavaScript hash in `Q/executions/suite-01/CE-F02_RECHECK.json:2–25`. CF-F04 is a separate progress-label defect. |
| **CE-F03** | **Original deadline, malformed-input and UNKNOWN-admission repairs accepted for their demonstrated cases.** Relevant source is `labs/ip01/haven/app.py:256–297` and `labs/ip01/haven/supervisor.py:459–484`, `:667–675` and `:773–806`. All-path lifecycle acceptance remains withheld because of CF-F01 and CF-F03. |
| **CE-F04** | **Original ancestry-depth/memoization counterexample closed.** The height-aware handling is present in `labs/ip01/haven/authority.py:59–92`; the inspected independent test covers the depth16/17 boundary in both traversal orders. This is a static review plus attributed test evidence, not a rerun. |
| **CE-F05** | **Original exhausted-G1 shadowing usable-G2 counterexample closed.** Grant selection at `labs/ip01/haven/authority.py:38–56` and its use at `:187` address the original selection defect; consumption still enforces quota at `:339–346`. Inspected independent coverage checks consumption and final exhaustion. **B2 remains separate**, as explained below. |
| **CE-F06 / R8-F01** | **Original premature-settlement-label counterexample closed.** Settlement/disposition handling at `labs/ip01/haven/model_adapter.py:116–137` and `labs/ip01/haven/supervisor.py:758–765` and `:459–484` supports the repaired distinction. Historical entries remain historical evidence. This does not cure CF-F01’s earlier cleanup interruption. |

**B2 is an unresolved usefulness defect, not a recurrence of CE-F05.**

The default context-selection path can include matching notes and then the selected image: `labs/ip01/haven/authority.py:171–187`. An incidental exhausted-context ancestor can consequently influence the sealed operation, after which fresh release enforcement denies at `:260–265`.

QA records an actual B2 model submission followed by `GRANT_QUOTA_EXHAUSTED`, with no observable answer or abstention: `Q/READINESS_RESULTS.json:58–82` and `:97–103`. The closure handoff retains that limitation at `C/integration/closure-v1/INTEGRATION_HANDOFF.md:49–55`.

This differs from repaired CE-F05, where one exhausted grant incorrectly shadowed another usable grant for the selection at issue. B2 spent model work on context that ultimately prevented useful release. A future improvement should address source relevance and early quota feedback **without dropping an actually influencing ancestor or substituting grants after sealing**. No refund, retry, weakened release check or readiness PASS follows from this review.

**Retained evidence and execution limitations**

- Deterministic evidence is a **composite** of seven suite1 components plus 221 suite3 producer checks. It is not a newly successful complete suite start. Failed suite1/suite2 setup records remain, and all three starts were consumed. See `Q/FINAL_QA_HANDOFF.md:3` and `Q/FINAL_DETERMINISTIC_RESULTS.json:225–254` and `:272–299`.
- The pilot executed **54/72**, with **45 passes, nine conservative failures and 18 unrun**. Protected evaluation remains **EVALUATION_INCONCLUSIVE**, and separation remains **NOT_ESTABLISHED**. I relied on public evidence only.
- B1’s premodel driver failure remains in the record; the later actual image pass is a useful observed positive. B2 remains the actual-model-call/release-denial case above.
- Reported actual text/image cancellation times were **0.156/0.141 seconds**. Natural model timeout attempts completed early; actual natural model timeout behavior remains **NOT_EXERCISED**. See `Q/FINAL_QA_HANDOFF.md:12–14`.
- Global accounting remains **64 settled calls, 1593.405 seconds**, with no new closure calls or suites. See `Q/FINAL_QA_REPORT.json:216–227`.
- The locked production gate’s historical deadline was **2026-09-29T10:10:16Z**. Positive model-lease producer tests use that historical gate while `labs/ip01/haven/model_adapter.py:59–68` checks actual time and the hard deadline. Their historical passes remain valid evidence; the unchanged positive cases are not a current post-expiry rerun promise. A later test-clock repair must not relax the production gate. The separate exported deterministic harness does not require that model gate.
- Original APP shutdown at **07:53:50** is an attributed recorded event. It does not establish cessation of the later native closure reviewers. The model gate remains disabled and HALT retained.
- H00’s closure overlay corrects older snapshot/preparation prose; it does not upgrade empirical results. See `C/integration/closure-v1/CARRY_FORWARD.md:9–17` and `C/receipts/H00_CLOSURE_FREEZE.json:15`.
- No canonical acceptance, production readiness, real two-person qualification, R1/M0 qualification or physical qualification is established.

**Operating restrictions and honest claim**

The packet supports a claim that an exact candidate has a traceable, independently checked public evidence packet; that specified deterministic components and bounded authority/lifecycle cases were reported as exercised; and that the actual-model evidence includes a useful B1 result, a B2 usefulness failure and limited cancellation observations.

It does **not** support claims of universally bounded cleanup, safe simultaneous launcher starts, comprehensive natural timeout behavior, a generally reliable image flow, successful protected evaluation or completed physical qualification.

The acceptable handoff therefore retains these restrictions:

1. **No new execution in this closure:** no application restart, model calls, suite starts or counter resets.
2. Any later authorized deterministic use must use **one serialized launcher lifecycle per runtime state**, with the model gate disabled.
3. Do not treat reported cancellation successes as proof against CF-F01 or CF-F03.
4. Preserve failed attempts, UNKNOWN/NOT_EXERCISED states, B2, CF-F01–CF-F04 and dissent in public closure artifacts.
5. Root must complete publication, input/output accounting and exact native cessation separately.

Root’s reports, audit material and RESUME were changing drafts during this review. **I do not certify their eventual final bytes.** Required documentary corrections are to publish and disposition all four CF findings, qualify launcher/lifecycle and image-flow claims, retain the historical-test clock caveat, use the correct QA digest, and replace pending-review prose only with actual received native returns. Historical execution records should remain intact.

VISION-FINAL’s PASS for truthful PARTIAL/vision retention and EVIDENCE-FINAL’s PASS for frozen-packet integrity are compatible with this **CHANGES_REQUIRED** code verdict. Neither supersedes it.

**Signed native-role final handback:**  
**Lorentz — `01a0ef1f-a53c-7f11-896d-a2a6fb2cbdb6`**  
Assignment22 · CODE-FINAL-CLOSURE · `haven_code_reviewer`  
CUSTOM_PROFILE_FALLBACK · inherited model/cost UNKNOWN · no override  
Read-only review complete · **CF-F01–CF-F04 unresolved** · bounded PARTIAL handoff acceptable with the restrictions above · root publication and cessation accounting remain downstream.
