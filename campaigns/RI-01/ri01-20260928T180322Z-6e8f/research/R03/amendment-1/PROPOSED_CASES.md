# R03-A1 finite-use and historical-fact subcases

All **PROPOSED_NOT_EXECUTED**. These refine original R03 P20/P21, not evidence of new test execution. Freeze deterministic scheduler barriers, ledger oracle, exact synthetic tuple and expected counts before coding. H06 independently reviews outcomes. Existing zero real/private input, no network/device effects and AUTHORIZATION_REQUIRED remain.

| ID | Synthetic setup/event | Required assertion |
|---|---|---|
| A01 | Finite grant max_uses1, one whole output, one destination; release then consume | Exactly one claim and one charged unit; one matching consumed slot; no second parent-quota charge; useful output remains eligible before other changes |
| A02 | Two concurrent distinct release operations compete for that grant | One admission/claim only; other QUOTA_EXHAUSTED; failed admission creates no partial charge or outbox permission |
| A03 | Repeat identical release key/hash; then attempt same key with different output/destination | First repetition reads history without charge/send; mutation conflicts; no new claim or release authority |
| A04 | Repeat consume request/ACK for consumed slot; altered nonce/tuple | Receipt history only, no newly executable permit; altered tuple conflicts; no duplicate effect/quota charge |
| A05 | Revoke or expire grant after release but before consume, separate schedules | Current consume denied despite existing claim; historical charge/authorization retained; exhaustion exemption does not bypass current authority |
| A06 | Correct source or change device/session/audience/policy/cancel/restore epoch between stages | Exact relevant-vector mismatch denies existing-claim redemption; no rebase/transfer to new vector |
| A07 | Lose release reply after commit; reconcile and confirm unused slot | Same immutable committed claim recovered, no charge/remint; one fresh eligible redemption allowed if still valid |
| A08 | Lose commit result with no trusted resolution | No send/new key/refund; RELEASE_UNKNOWN preserved; read-only authoritative reconciliation required |
| A09 | Consume commits but response lost; send/ACK delivery evidence missing | Consumed slot immutable; no remint/reset; distinguish response uncertainty from delivery observation; neither revocation nor timeout yields NOT_SENT |
| A10 | Abandon/delete/expire confirmed release without consume | Charged unit retained; no automatic refund; expired claim denies redemption |
| A11 | Explicit replay after lost ACK with max_uses1 already charged | New operation requires new quota; deny exhausted grant; separately authenticated new grant may admit a new claim, never revive old slot |
| A12 | Two required grants, one exhausted; repeated parent refs to same applicable grant | All-or-nothing release charge; no partial debit; applicable identical grant/profile deduplicated without merging distinct purposes/operations |
| A13 | Grant permits2 uses; unrelated second admission changes quota sequence before first consumes | Authorization revision unchanged by accounting; first claim can consume if otherwise current; third new admission denied |
| A14 | Change max_uses/scope/expiry through authorized policy amendment | Authorization revision changes; old claim does not bypass changed authority; no silent accounting-only broadening |
| A15 | Lost ACK then revoke; prior playback then cancel in separate traces | Append observations/current denial; unknown stays unknown until actual new evidence; past playback stays historical; current future DENIED does not rewrite receipts or stop compute |
| A16 | Ask P0 for finite-use chunked/multi-destination profile | UNSUPPORTED_PROFILE; no inferred count convention, no grant charged by rejected admission |

Retain release/claim/consumption counts, quota accounting sequence, unchanged/changed authorization revisions, current-vector decisions, timestamps and complete attempted tuple per schedule. Inspect all failures. These finite cases provide evidence only for implemented synthetic semantics if later executed, not globally exactly-once delivery or physical safety. Report both permitted-use success and denial correctness; denying every consume is a failure of A01/A13.
