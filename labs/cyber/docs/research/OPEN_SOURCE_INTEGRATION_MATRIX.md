# Open-source integration matrix

Repository facts come from the GitHub API on 2026-10-31: stars, last push, SPDX licence, archived flag. Output formats were read from upstream source, not documentation summaries. Each decision is one of: **reuse directly**, **thin adapter**, **improve upstream**, **build complementary**, **reject/defer**.

## Microsoft security

| Project | What it does | Activity / licence | Credentials and risk | Overlap with Haven | Decision and status |
|---|---|---|---|---|---|
| **Maester** (maester365/maester) | Pester-based tests for Entra/M365/Azure (MT.*, EIDSCA, CIS, CISA, ORCA) with HTML/JSON reports | 1.2k★, pushed 2026-10-31, MIT | Graph read scopes via Connect-Maester; needs PowerShell 7 | none | **Thin adapter**, *implemented and tested*. `normalize/maester.py` reads `TestResults.json` with field names taken from `ConvertTo-MtMaesterResult.ps1`. Test ids, severity, HelpUrl and remediation are kept verbatim; Skipped is never treated as a pass. Maester itself was not run: no `pwsh` on any host. |
| **Prowler** (prowler-cloud/prowler) | Multi-cloud CSPM (Azure, M365/Entra checks, AWS, GCP, K8s); OCSF JSON output | 15.1k★, pushed 2026-10-30, Apache-2.0 | read-only cloud credentials | none | **Thin adapter**, *implemented and tested*. `normalize/prowler_ocsf.py` reads the `-M json-ocsf` Detection Finding layout from `prowler/lib/outputs/ocsf/ocsf.py`, keeping CheckID, compliance mappings and remediation. Any OCSF 2004 producer works the same way. Prowler not run: no credentials or install. |
| **ScoutSuite** (nccgroup/ScoutSuite) | Multi-cloud configuration auditing; JS-wrapped JSON report | 7.9k★, **last push 2025-09-23**, GPL-2.0 | read-only credentials | Prowler covers more and is maintained | **Defer.** Activity has slowed and Prowler supersedes it. GPL-2.0 is fine for an importer that only parses its output. |
| **ROADtools / ROADrecon** (dirkjanm/ROADtools) | Entra enumeration into SQLite; token tooling | 2.8k★, pushed 2026-10-22, MIT | uses internal Azure AD Graph endpoints and token tricks; offensive-research oriented | partly overlaps the Graph collector | **Defer.** Haven's least-privilege collector uses official Graph v1.0 only. ROADrecon's database could later be a snapshot source for authorized red-team labs. |
| **Azure MCP Server** (microsoft/mcp, `servers/Azure.Mcp.Server`) | Official MCP server exposing Azure tools (Resource Graph, storage, Key Vault, monitor, etc.) | 3.8k★, pushed 2026-10-30, MIT | uses the caller's Azure identity; includes write-capable tools | would overlap a future Haven Azure collector | **Reuse directly** once a tenant exists, restricted to read-only tools through Hermes `mcp configure` tool selection. Untested: no Azure login. Haven keeps its own evaluators because they work offline on exported data. |
| **Microsoft MCP Server for Enterprise** (microsoft/EnterpriseMCP) | Public preview of a remote Microsoft-hosted MCP endpoint that turns natural-language requests into Graph calls for Entra data; per-tenant provisioning plus `MCP.<scope>` permissions | 62★, pushed 2026-10-28, CC-BY-4.0 (docs repo) | delegated Entra scopes granted to an MCP client app | none | **Defer until a tenant exists.** It is remote, preview and needs tenant provisioning. Evaluate as a read path for condition C on a lab tenant. |
| **Microsoft Graph SDK for Python** (microsoftgraph/msgraph-sdk-python) | Typed Graph client | 634★, pushed 2026-10-31, MIT | as configured | `tools/graph.py` uses plain HTTPS | **Defer.** About 7 GET endpoints did not justify the dependency tree (kiota, azure-identity). Revisit if write paths or batching are ever needed. |
| **Azure Resource Graph** | KQL over ARM resources and role assignments | service | Reader at the target scope | `tools/azure_rbac.py` evaluates exports | **Reuse directly** as the data source (`authorizationresources`, `resources`). Haven's evaluator consumes its export; collector not built (no tenant). |
| **Microsoft security baselines / CIS M365** | configuration baselines | vendor/CIS terms | - | crosswalk ids | **Reference only.** Control ids are carried as `controls` (for example `CIS-4.0_M365:5.2.2.3` from Prowler). Baseline text is not copied. |

## Defensive security

| Project | Activity / licence | Decision |
|---|---|---|
| **SigmaHQ/sigma** | 11.4k★, pushed 2026-10-21; rules under DRL 1.1 (attribution required) | **Reuse directly, deferred to the next milestone.** Map posture findings to detection rules by ATT&CK tag. Licence noted in the corpus; no rules vendored yet. |
| **pySigma** | 604★, pushed 2026-10-31, LGPL-2.1 | **Reuse directly** for rule conversion when a SIEM backend exists. Not installed. |
| **MITRE ATT&CK STIX data** (mitre-attack/attack-stix-data) | 706★, pushed 2026-10-13; MITRE terms of use (free with attribution) | **Build complementary.** Technique ids are used in the corpus and eval. Next step: an ingestion step that validates ids against the STIX bundle. |
| **osquery** | 23.7k★, pushed 2026-10-31 (Apache-2.0 / GPL-2.0 dual) | **Defer.** A good fit for "local systems" read-only tools; not installed and needs an install decision. |
| **Wazuh** | 17.5k★ (GPL-2.0) | **Defer.** A full SIEM/XDR platform; too heavy for this milestone. |
| **Semgrep** | 17.4k★ (LGPL-2.1 engine) | **Defer** to application security. The forge secpatch lane already covers code review. |
| **Open Policy Agent** | 12.4k★, Apache-2.0 | **Defer.** Rego could express HCA rules declaratively, but the Python predicates are already tested and verified independently. |

## Agent and training infrastructure

| Project | Activity / licence | Decision |
|---|---|---|
| **Hermes Agent** (NousResearch/hermes-agent, v0.22.5 installed) | 259k★, MIT | **Reuse directly.** Its native MCP client loads `haven-cyber` (verified with `hermes mcp test`). |
| **MCP Python SDK** (modelcontextprotocol/python-sdk) | 24.7k★, MIT; 2.3.0 installed | **Reuse directly.** `mcp_server.py` targets `MCPServer` (2.x) with a FastMCP (1.x) fallback. |
| **FastMCP** (PrefectHQ/fastmcp) | 28.3k★, Apache-2.0 | **Not needed.** The official SDK covers the four tools. |
| **SQLite FTS5** | in the standard library (SQLite 3.45 on Slink) | **Reuse directly** for deterministic BM25 retrieval. |
| **Transformers / PEFT / TRL / bitsandbytes** | Apache-2.0 / MIT | **Reuse directly** through the forge trainer (versions in the audit). |
| **Unsloth** | 78.9k★, Apache-2.0 | **Defer.** Qwen3.5 hybrid DeltaNet support would have to be verified first; the forge trainer already runs Qwen3.5 QLoRA on T4s. |
| **MLX-LM** | 7.5k★, MIT | **Reject for now.** The Mac is the only Apple Silicon host and its compute is off. |

## Why adapters, not rewrites

Maester and Prowler already encode hundreds of maintained checks. Haven adds what they lack for an autonomous agent:
- one evidence model for both tools;
- raw-evidence pointers;
- independent re-derivation, which turns a tool verdict into corroborated or refuted;
- a crosswalk that tells whether a check asks "a policy exists" or "every principal is covered".

The cross-check already demonstrates the difference: Prowler's `entra_legacy_authentication_blocked` and Maester's MT.1006 both **pass** on the weak fixture, while Haven's coverage rules show a non-emergency exclusion. The verifier reports that as a criterion gap, not as an error in either tool.
