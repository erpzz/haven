# Upstream contribution plan

No upstream issue or pull request has been filed yet. Nothing below is claimed as fixed. Each item names the evidence that would justify filing it.

| Project | Candidate | Evidence so far | Next step | Status |
|---|---|---|---|---|
| Maester | Document `TestResults.json` as a stable machine-readable contract (field list, Result enum, ResultDetail keys) so importers don't read `ConvertTo-MtMaesterResult.ps1` | Haven's normalizer had to derive the schema from source | check the docs site for an existing schema page; if none, open a docs issue with the field table from `normalize/maester.py` | planned |
| Maester / Prowler | Mark checks as "existence" or "coverage" in metadata, so consumers know whether a PASS means "a policy exists" or "every principal is covered" | Haven's verifier needed a hand crosswalk; on the weak fixture, MT.1006 and `entra_legacy_authentication_blocked` pass while a non-emergency exclusion leaves a Global Administrator uncovered | run both tools on a lab tenant with the same exclusion to reproduce for real (synthetic fixtures are not evidence of upstream behaviour) before filing | planned; needs a lab tenant |
| Prowler | OCSF output: include the evaluated policy ids in `resources[]`/`unmapped` for Entra CA checks (currently a single "Conditional Access Policies" resource) | from `ocsf.py` and check metadata: resource uid is per check, not per policy | confirm on a real scan, then propose a focused PR with a regression test | planned; needs a real scan |
| Hermes Agent | `hermes mcp add` prompts interactively ("Enable all N tools? [Y/n/select]") even when stdin is not a TTY, and cancels; scripted setup needs `echo Y \|` | observed while registering `haven-cyber` on v0.22.5 | check for an existing `--yes` flag or issue; if none, propose `--yes` / `--tools all` with a test | planned |
| MCP Python SDK | none needed: 2.3.0 worked as documented (migration message for the FastMCP rename is clear) | `scripts/mcp_smoke.py` passes | - | no action |
| SigmaHQ / ATT&CK | none yet | - | revisit after the detection-mapping milestone | deferred |

Rules: follow each project's CONTRIBUTING guide, keep changes focused, include a regression test, keep licence headers, and link the Haven evidence (commands and outputs) in the issue. Track status in this file.
