# Actual verification and unexecuted tests

Author-side documentary checks only; these are not independent review and not runtime acceptance. Environment: PowerShell in the assigned RI-01 working tree, 2026-09-28. No Git/application/model/simulator/device test was run. All AT-ROBOT, EX and R09-T entries remain NOT_EXECUTED.

## V-DOC-01 — JSON and input identity

Executed `Get-Content -Raw | ConvertFrom-Json` for INPUT_USE.json and REQUIREMENTS.json. For each input row, executed `Get-FileHash -LiteralPath <row.path> -Algorithm SHA256` and compared lowercase digest to its recorded value; checked finding/upstream/downstream/reason fields. Expected38 parseable, complete input rows and zero digest mismatches. Actual38 rows, zero missing fields/mismatches. Two unavailable source entries remain explicitly null and are not counted as hashed inputs. The accepted hard-input hashes also match root-supplied identities listed in INPUT_RECEIPT.md. This proves byte identity at the check, not validity of scientific claims.

## V-DOC-02 — Preserve original IDs, owners and statuses

Parsed original102-row requirement register, original acceptance catalog and experiments. Selected each copied record by original ID; compared its complete `ConvertTo-Json -Depth15 -Compress` representation to the copied record. Expected unchanged9 relevant REQ records,5 AT-ROBOT and 5 EX records. Actual all19 selected records identical in content; zero differences. The report's new experiment proposals do not edit original source files or claim test completion.

## V-DOC-03 — Fixture/source coverage inventory

Executed regex enumeration of EXPERIMENTS table `R09-T01` through `R09-T24` and SOURCES table `S01` through `S23`. Actual24 unique proposed case rows and23 source rows. These are coverage counts, not executed-case scores. Manually checked explicit positive cases, hard failure outcomes, no-model/no-device caps, independent oracle protection, physical UNKNOWN and exact CORE I06 record names. Corrected an initial draft's abbreviated output-record labels to canonical names before freeze; no upstream file changed.

## V-DOC-04 — Static-image smoke

Actual direct whole-image view of existing R10 synthetic asset succeeded; hash/observations/mode in MODALITY.md. No video, audio, PDF figure, spatial render or sensor signal was inspected. This establishes only development static-image access.

## V-DOC-05 — Final artifact identity

HANDOFF_MANIFEST.json records every final payload's relative path, byte length and SHA256; the manifest excludes its own recursive hash. Final tool check reparses the manifest and rehashes all listed payloads. Root receives the manifest's separate digest in the handback. No manifest identity is an operational grant or an independent scientific review.

## Explicit gaps

NO_APPLICATION_CODE_CHANGED; no application code qualification. Native hardware interfaces, stop/recovery, simulator, teleop, model latency, force/payload/retention, training, privacy erasure, original AT/EX and protected evaluator tests NOT_EXECUTED. External current pages are date/URL anchors without web-body hashes or exact adoption commits. Original prompt/document gaps are retained. Root must assign a different actual reviewer; this author does not accept its own packet.

