# R10 document integrity receipt

2026-09-28, Windows PowerShell host; author `/root/ri01_privacy`, haven_researcher. Start recorded19:11UTC; document checks19:31UTC, final manifest generated afterward within25-minute task. Source/instruction reads, public web primary research and document operations only. No Git, external publication, SDK/package installation, application source execution, test runner, device operation or subagent used.

Actual checks:

- `Get-Content INPUT_USE.json -Raw | ConvertFrom-Json`: parsed17 records.
- Recomputed SHA256 for all15 referenced local input files using `Get-FileHash`: zero mismatches. Two unresolved soft-input/consultation records intentionally have null artifact hashes.
- Read exact original requirements and tests/experiments; retained REQ-DRONE-01–12, AT-DRONE-01–12, EX18–20 and related16/21/22/24; original Gen0 M0–M6, R0/R01, S1/T32 and S2/T33–T35 remain proposed/not executed.
- Required report sections and files present; no placeholder PASS or measured aircraft capability is asserted. Exact function/firmware/support unknowns and incomplete system costs remain visible.
- Original synthetic240x120PNG created using existing System.Drawing and directly opened through `view_image`; observed red square/blue circle/black diagonal. This is only a development image-input smoke.
- Attempted vendor-PDF page image failed; parsed text remains DOCUMENTATION_ONLY. No hidden upgrade to figure/video/audio inspection.

A PowerShell `foreach` pipeline form initially produced a parser error during read-only input hashing; it was corrected by collecting records before conversion. An initially attempted old PX4 offboard URL lacked operative content; the correct versioned official path was retrieved. These are document-tool retrieval corrections, not application failures or tests.

MANIFEST.json lists byte counts/SHA256 for final deliverables other than the manifest itself. Hash identity and JSON parsing do not establish scientific correctness, schema acceptance or physical qualification. Independent review remains requested. CORE/R07 exact artifact closure and EC120 identity remain pending; no further work is promised without the campaign supervisor's dispatch.
