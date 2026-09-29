# CODE-FINAL-CLOSURE addendum received before original report recovery

Root received this actual native addendum from `01a0ef1f-a53c-7f11-896d-a2a6fb2cbdb6` (assignment22). The full original CF-F01–03 handback was absent from the root's delivered context and is being retransmitted in the same assignment. Do not treat this addendum alone as the full code review.

**CODE-FINAL-CLOSURE addendum — CHANGES_REQUIRED remains the code/runtime verdict. The bounded PARTIAL handoff remains acceptable with the open findings and operating restrictions retained.**

I agree with VISION-FINAL’s new **P2 UI finding**. This is **CF-F04** in assignment22, cross-referencing the vision finding at `campaigns/IP-01/ip01-v2-20260929/reviews/VISION-FINAL-CLOSURE/REVIEW.md:108`. It does not replace or weaken my earlier findings.

I independently reread and hashed the unchanged template and JavaScript against candidate `0b59551f36990cfb8a723f97da6d367358a8ceb5`. This addendum involved read-only source, hash and peer-report inspection; no application, browser, tests or model execution. The direct B1 pixel observation remains attributed to VISION-FINAL.

| Finding | Verified source evidence | Required disposition |
|---|---|---|
| **CF-F04 — P2 / MEDIUM: route and progress labels remain misleading after successful model output** | `labs/ip01/haven/templates/index.html:20` hardcodes **“Deterministic excerpts.”** `labs/ip01/haven/static/app.js:63` posts **“Question queued”** after submission and refresh. The successful payload branch at `:65` renders the answer and records the display observation without clearing or replacing that notice. | Retain as an open UI defect. It is nonblocking for this explicitly partial handoff but blocks an unqualified claim that the general image flow reliably presents its route and progress truthfully. No source change is requested in this closure. |

The finding needs a precise boundary: `static/app.js:64` renders actual job disposition and compute state, and `:65` labels the displayed payload using its label or **“Local model proposal.”** Therefore, this is contradictory surrounding UI, not evidence that the backend remained queued, that B1’s successful answer was invalid, or that consumption authorization failed. The stale notice can also affect deterministic completions.

A later authorized repair should distinguish the **displayed answer’s route** from the **route selected for the next request**, and associate progress notices with the relevant operation. Completion of an older operation must not erase a newer operation’s notice. Preserve the repaired CE-F02 session-generation protection. Completed, failed, denied and reload views require a later recheck; none was executed here.

**B2 remains a separate P2 usefulness defect:** an incidental exhausted-context ancestor prevented release after actual model work, producing no observable answer or abstention. CF-F04 neither explains nor closes B2. Neither finding reopens the repaired **CE-F05 G1/G2 grant-shadowing counterexample**.

VISION-FINAL’s limited PASS and EVIDENCE-FINAL’s packet-integrity PASS are compatible with this review. They do not resolve my retained cleanup, concurrent-launcher and unbounded-drain findings **CF-F01–CF-F03**. The acceptable handoff remains bounded PARTIAL, with the single-launch restriction, disabled model gate/HALT and other stated limitations preserved; this review authorizes no restart or additional execution.

The correct QA-handoff SHA-256, already used in my original handback, is:

`733b1d373c42c01ef5a94b5b5b0a971bd6c002952fae9c3a0cdf93ee8041649d`

Root should carry CF-F04 into the changing closure drafts alongside B2 and the original code findings. This addendum does not certify those drafts as frozen final bytes.

**Signed native-role handback:** Lorentz — `01a0ef1f-a53c-7f11-896d-a2a6fb2cbdb6`  
Assignment22 · CODE-FINAL-CLOSURE · `haven_code_reviewer` · CUSTOM_PROFILE_FALLBACK  
Inherited model/cost: UNKNOWN · no model override  
Returned 2026-09-29 21:58 UTC · same assignment · root publication pending.
