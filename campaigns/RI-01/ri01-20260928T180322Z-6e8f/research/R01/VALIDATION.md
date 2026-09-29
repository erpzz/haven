# R01 documentation verification

Author `/root/ri01_daily`; 2026-09-28; Windows PowerShell shell. These checks verify document structure/source identity only. They do not qualify product behavior. No application/runtime/user/media-processing/AT/EX test was run.

Executed read-only/document checks using `Get-Content -Raw | ConvertFrom-Json`, `Get-FileHash -Algorithm SHA256`, PowerShell record comparisons and regex heading counts:

| Check | Expected | Actual |
|---|---|---|
| INPUT_USE JSON parse | Valid array | 17 records parsed |
| Upstream bytes versus recorded input hashes | Zero mismatches at final check | 0 |
| Original requirement/map counts | 102/102 | 102/102 |
| Requirement ID/owner/AT link match | Zero mismatches | 0 |
| Original experiment/map counts | 32/32 | 32/32 |
| Experiment ID/owner/REQ link match | Zero mismatches | 0 |
| Priority scenario headings | Five | 5 |
| Ordinary daily variant rows | At least twelve | 12 |
| Physical/health boundary rows | At least four | 4 |

Readback confirmed the five reviewed integrated journeys map to S1, S4, S5a, S5b and S2. Numerical usability/latency/setup thresholds are labeled proposals. Every experiment has NOT_EXECUTED/AUTHORIZATION_REQUIRED status and limits. Original AT/EX statuses are unchanged. Future code location is explicitly unassigned rather than a hidden implementation grant.

Current primary web documentation and a development image smoke inspection are actual research activities; they are not runtime/media benchmark executions. Exact source/hash/mode is in SOURCES.md. An initial oversized shell write was rejected by Windows process creation before writing REPORT.md; the report was then created with the file patch tool. This was a document-transport limitation, not application execution or a product test failure.

No independent handback review has occurred within this author task. Root must freeze artifacts and dispatch a different reviewer. INPUT_USE records R03 advice as provisional; it does not assert reviewed CORE. SHA256SUMS.json excludes itself and is an identity manifest only, not scientific acceptance.
