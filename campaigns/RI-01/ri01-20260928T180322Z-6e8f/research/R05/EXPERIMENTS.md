# R05 proposed qualification protocol

All cases below: **NOT_EXECUTED**. This is design, not generated results. Keep canonical EX05 (owner H03, REQ-DAILY-02), AT-DAILY-02/03/04/05/07/08/10 and original requirement IDs. R01 UI vignettes cannot stand in for these runtime tests. No runtime was started during research.

## Hypothesis and apparatus

A deterministic reader and durable synthetic scheduler can provide correct agenda/reminder state through ordinary restart, ambiguity and bounded outages without inference, while preserving explicit unknown external outcomes. Proposed R05-P0 apparatus: isolated existing approved runtime, temporary synthetic current store plus deliberately stale backup, fake monotonic/wall clocks, A/B test principals, fake provider/native destination, explicit complete authority fixture, append-only receipts, no network/credentials/model. Retain exact fixture/protocol/build/config hashes and every eligible case event log, expected and actual values, exclusions and failure reasons. Independent reviewer H06 or root-assigned distinct agent checks all safety cases and sampled positive output.

Baseline: manual exact fixture agenda plus deterministic EX05 scheduler oracle prepared independently of implementation. Human usability comparison is a later separately authorized study, not a current runtime requirement. In the fake destination “accepted”, “display reported” and “human received” are separate fields; human received remains UNKNOWN.

## Frozen denominator: 32 cases

Each row is one case; subconditions are mandatory assertions, not extra denominator opportunities. Do not drop cases after observing failure. Repeat runs are reliability repeats, not new independent cases. Strata A=8 useful projections/drafts, B=12 schedule state cases, C=12 authority/reconciliation cases. All 32 must run for complete evaluation; report completed/32 if interrupted, with no promotion from a subset.

| ID | Setup / expected result | Anchor |
|---|---|---|
| A01 | Single owned calendar, two timed events and 30-minute open slot: exact source-linked agenda and correct candidate gap, no write. | AT-DAILY-02 |
| A02 | All-day event plus timed item in explicit zone: dates and times displayed correctly, no midnight alarm invented. | AT-DAILY-02 |
| A03 | Two calendars share a meeting title: identify ambiguity and request exact calendar/resource before proposal. | AT-DAILY-05 |
| A04 | Empty first page with next-page token and populated second page: include second-page event; never declare whole interval free early. | AT-DAILY-05 |
| A05 | Page/event budget reached: useful partial agenda with exact coverage/truncation; no comprehensive availability claim. | AT-DAILY-10 |
| A06 | Selected file supports decision and contains injected send instruction: cite decision evidence, create no effect. | AT-DAILY-03 |
| A07 | Dictated message draft with recipient change: local reviewed body remains useful; new recipient invalidates former approval; no send. | AT-DAILY-04 |
| A08 | A/B separately grant minimal availability sharing: correct intersection without private meeting titles; revoke B and shared projection becomes ineligible. | AT-DAILY-08 |
| B01 | One-shot schedule local commit: durable receipt and next due time; no “delivered” label. | EX05 |
| B02 | Intact-current-database process restart before due: one new occurrence admitted with fresh authority, no model needed. | EX05 |
| B03 | Restart after synthetic destination received but reply lost: outcome remains unknown; no second send. | EX05 |
| B04 | Cancel before due then restart: cancelled state persists and no destination effect. | EX05 |
| B05 | Sleep then wake within approved catch-up window: one eligible catch-up cue only. | EX05 |
| B06 | Wake outside window: missed occurrence recorded; no storm of stale notifications. | EX05 |
| B07 | Spring gap with explicit human reminder skip policy: preview and occurrence accounting agree; RFC recurrence mode separately respects RFC skip. | AT-DAILY-02 |
| B08 | Autumn fold with explicit first/second choice: exactly selected intended occurrence key, no duplicate from ambiguous local clock. | AT-DAILY-02 |
| B09 | User travels while schedule says home zone: intended zone stable; explicit zone edit creates revised future schedule. | AT-DAILY-02 |
| B10 | Series edit/cancel one occurrence: exact cutover, old worker fence denied, unrelated occurrences preserved. | EX05 |
| B11 | Restore stale backup/import: new epochs, review-only schedules, no tokens/timers/permits revived. Indeterminate rollback provenance quarantines. | EX05 |
| B12 | Model unavailable and routine quiet hours active: due/missed/cancelled arithmetic works; independent alarm policy untouched; private release still requires current authority. | AT-DAILY-07 |
| C01 | Complete release claim consumes final parent quota slot: existing admitted claim can consume once without second quota debit or positive remaining quota requirement. | CORE I06 |
| C02 | Same release key repeated returns historical result, never a fresh permit; changed payload/destination conflicts. | CORE I06 |
| C03 | Provider commit followed by lost ACK: UI may show unknown or exact later observed match, never “not sent”; cancellation preserves uncertainty/history. | R01 amendment |
| C04 | Exact provider ID occupied by different payload/account marker: conflict; no overwrite/reuse/new automatic ID. | R05 D4 |
| C05 | Authenticated exact lookup matches sealed resource: record provider-resource-observed; human receipt still unknown; no redispatch. | R05 D4 |
| C06 | Complete successful search yields no current match: record absence-of-current-match only; no historical noncommit assertion or auto-retry. | R05 D4 |
| C07 | Lookup 401 and 403 variants: authentication/authorization failure distinct; no empty-success result or silent scope broadening. | R05 D4 |
| C08 | Lookup 404 versus 429 versus 5xx versus network timeout variants: retain distinct uncertainty/error categories; bound read retries and never resend. | R05 D4 |
| C09 | Account switched or A token presented for B job: binding epoch/principal failure, no read/write or shared output. | AT-DAILY-08 |
| C10 | Parent source corrected/revoked after draft/release but before consumption: full vector fences current output; historical authorized record retained; derived content unavailable offline. | AT-DAILY-10 |
| C11 | Provider send acceptance vs synthetic display report: show different statuses; UI cannot label human-received. Positive local-only/no-dispatch state alone permits “not sent.” | AT-DAILY-04 |
| C12 | Google task time requested, unsupported recurrence translation or unknown provider idempotency profile: useful local proposal/clarification, no silent precision loss or live mutation. | AT-DAILY-02/05 |

## Measures and thresholds

For positive utility, A01/A02/A04/A06/A07/A08 must produce their correct useful outputs, not blanket refusals. A03/A05 require correct bounded clarification/partial output. Require A=8/8 expected case dispositions; separately report event/time/source-field accuracy with the predeclared eligible facts denominator and omission count. Model output quality is outside this deterministic experiment.

For schedules require B=12/12 state outcomes and zero duplicate destination effects, revived cancellations, unauthorized catch-up or stale-epoch admission. Report expected/actual due, admitted, cancelled, missed and unknown counts per case, not a single “delivery rate.” Clock correctness is against fixture oracle; synthetic latency provides no device latency claim.

For authority/reconciliation require C=12/12; every listed variant in C07/C08/C12 is mandatory. Zero cross-user disclosures, repeated finite debit, unknown-write retries or false received/not-sent claims. No averaging a safety failure into an overall passing score. Any mandatory failure blocks promotion and is retained, with changed build and bounded full affected-case recheck after repair.

Limits for proposed package: <=32 original cases plus explicitly logged repair repeats; one two-hour implementation session and one one-hour evaluation; <=20MiB synthetic artifacts; no installs/network/model/provider spend. If budget expires preserve incomplete state and report completed/32; do not relax thresholds. Capture CPU/wall duration if executed; no energy or cost numbers invented.

## Later real-provider and ambitious studies

P1 finite read-only validation needs explicit account/user scope, OAuth app review, one owned calendar/window, exact projection caps, permitted retention and revocation test; provider read failures remain observations, not synthetic passes. No mutation. Compare returned IDs/times against native calendar for all eligible items with independent inspection. A success qualifies that route/version/account class only.

P2 write qualification needs an endpoint-specific grant and harmless synthetic destination/test resource; inspect SDK retry policy before any operation. Dedicated lost-ACK experiments on real provider writes require a separate duplicate-risk protocol and operator approval; fake-provider results cannot establish provider dedup lifetime.

Ambitious cooperative study: two independent consenting participants, selected calendar/document, source correction, offline transition, device handoff and optional selected speech/image input. Pre-register ten eligible planning facts per participant, two shared availability decisions and two exact cue occurrences. Targets: >=9/10 facts correct per person, both shared decisions correct, zero unauthorized disclosures/duplicates; separately report clarification count, completion time versus native tools, accessibility failures and all missing observations. Native display ACK is not human perception. Device/media/model/account permissions and qualified paths are prerequisites; this entire study remains NOT_EXECUTED.
