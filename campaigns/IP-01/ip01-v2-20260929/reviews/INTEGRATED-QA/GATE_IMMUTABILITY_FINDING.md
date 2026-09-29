Q-GATE-IMMUTABILITY-01 — actual attributed answer from task15 independent QA, recorded 2026-09-29T06:23:44Z.

**Yes. I briefly rewrote `DETERMINISTIC_GATE_READY.json`, then restored its exact original bytes.** The writer was my evaluator report-builder `<evaluator>/integrated_qa/finalize_reports.py`, not an APP/RUNTIME author, model worker, root policy decision or external process. This was a QA publication/control-artifact immutability error. I did not know the receipt had become task16's frozen control input until root's subsequent freeze instruction arrived. That explains the sequence; it does not make the rewrite appropriate.

The original/frozen SHA256 is `1113841e537784edf6416b66cb5661fbc5cc074a7881a142c20d6da8ef345d88` (6582 bytes). The briefly substituted closure edition SHA256 is `a14427221fd400f291589a30d248da13dc747ebed603585a543367d53d9d8515` (6787 bytes). The restored current gate SHA256 is exactly the original `1113841e537784edf6416b66cb5661fbc5cc074a7881a142c20d6da8ef345d88`.

Observed timeline, UTC:

| Time | Actual observation/provenance |
|---|---|
|06:08:24.8592949|Evaluator original gate file timestamp; original private bytes remain at `<evaluator>/integrated_qa/DETERMINISTIC_GATE_READY.json`.|
|06:19:20.3797805|Creation timestamp of `finalize_reports.py`, the report-builder I executed with candidate-provisioned Python `-B`.|
|06:19:23.0163602|Before rewriting, the builder preserved the original public gate as `<evaluator>/integrated_qa/public_originals/1113841e537784edf6416b66cb5661fbc5cc074a7881a142c20d6da8ef345d88-DETERMINISTIC_GATE_READY.json`. Its bytes and hash still match the original.|
|06:19:23.0173658|Write timestamp of the closure edition, now preserved unchanged as `DETERMINISTIC_GATE_CLOSURE_ADDENDUM.json`. The builder wrote this edition to the original gate pathname at this point.|
|06:19:23.0307769|`<evaluator>/integrated_qa/FINALIZE_PARTIAL.json` completion marker. The builder command completed successfully, exit0.|
|After builder completion, before restoration|Root's freeze instruction arrived in this native conversation, stating that root had verified/frozen SHA1113841e and task16 control was pinned to it. I immediately disclosed that the builder had just changed the gate. Exact message-arrival subsecond time is not independently logged in these artifacts.|
|06:19:40.823765|Creation timestamp of the new addendum pathname when my corrective command copied the substituted gate there. `Copy-Item` retained the substituted edition's06:19:23.0173658write timestamp.|
|Within06:19:40UTC, after that addendum copy|The same sequential command copied the retained evaluator original back to the gate pathname, then computed SHA256 of both public gate and addendum. Tool output confirmed original1113841e and addendum a1442722. The immediately following clock tool returned `2026-09-29 06:19:40 UTC`. Exact restoration write subsecond is not recoverable from LastWriteTime because `Copy-Item` preserved the original file's timestamp; I do not present that preserved06:08timestamp as the restoration time.|
|06:20:38.9636119|I changed the evaluator builder so its closure-writing branch targets only the new addendum and first asserts the frozen gate's original SHA. I did not rerun that builder.|
|06:23:44UTC|Fresh read-only hashes again confirmed public gate=private original=1113841e, addendum=a1442722. No further gate write is being made for this finding.|

The temporary edition added closure-result references, the latest38-case result, operator smoke/image-crash outcomes and lifecycle-checker resolution; it removed the then-obsolete pending-supplement limitation. It did not alter candidate source hashes, stop targets, candidate code, a model gate, an allocation or a ledger. Its altered bytes nonetheless invalidate an exact hash preflight while substituted, and the gate pathname was not immutable during the approximately18-second interval above. The builder used ordinary text writing rather than atomic publication, so a concurrent reader could also encounter an incomplete write; I have no observation proving that happened.

The restoration command, with public-safe path aliases, was sequential:

```powershell
Copy-Item -LiteralPath <campaign>/reviews/INTEGRATED-QA/DETERMINISTIC_GATE_READY.json -Destination <campaign>/reviews/INTEGRATED-QA/DETERMINISTIC_GATE_CLOSURE_ADDENDUM.json
Copy-Item -LiteralPath <evaluator>/integrated_qa/DETERMINISTIC_GATE_READY.json -Destination <campaign>/reviews/INTEGRATED-QA/DETERMINISTIC_GATE_READY.json -Force
Get-FileHash -Algorithm SHA256 <campaign>/reviews/INTEGRATED-QA/DETERMINISTIC_GATE_READY.json
Get-FileHash -Algorithm SHA256 <campaign>/reviews/INTEGRATED-QA/DETERMINISTIC_GATE_CLOSURE_ADDENDUM.json
```

Both the builder and corrective command returned exit0. The bad action was successful mutation of an artifact that should have remained immutable, not a failed shell command. Its substituted bytes are preserved in the addendum and its original bytes in two evaluator locations. `GATE_EDITION_NOTICE.json` is the earlier disclosure; this finding provides the fuller timeline requested. All task15 failed pytest/checker commands and originals remain retained in `ATTEMPTS.json` and private run directories. The task16 failed preflight is root/task16 evidence and has not been modified by task15.

Root reports L2's preflight failure timestamp06:19:57, before any submission. That timestamp is later than my tool-observed restoration/hash verification in the06:19:40UTCsecond. Therefore I can confirm the transient mutation, but cannot establish from my evidence alone when task16 actually read the changed/incomplete gate or whether its06:19:57timestamp records read time versus later failure reporting. Root should correlate the retained task16 trace. I will not assert an exact causal read timestamp I did not observe.

Root's reported L1cancel PASS, L2zero submissions and5claims/5confirmed settlements are attributed to root, not independently re-audited by task15 here. This finding does not clear task16's HALT, authorize a retry, spend a slot, refund a count or transform uncertainty into a PASS. Root owns that reconciliation. Task15 has made0realmodel calls and has not touched root8765, its model gate or its ledger. The gate file remains at its original hash; later reporting uses new filenames only.
