# MCP and security tool registry

## Exposure model

The MCP server (`haven_cyber/mcp_server.py`, stdio) exposes **four** tools whatever the registry size. A 9B model sees four short schemas, not one per capability:

| MCP tool | Purpose | Annotation |
|---|---|---|
| `cyber_search(query, domain?, k?)` | cited knowledge retrieval in one call | readOnly |
| `cyber_capabilities(domain?)` | one line per registry tool: id, capability, domain, scope, availability | readOnly |
| `cyber_describe(tool_id)` | full input/output schema, permissions, credential rules, prerequisites | readOnly |
| `cyber_call(tool_id, arguments)` | invoke a registry tool (validated, scoped, timed, rate-limited, audited) | readOnly, openWorld |

Results larger than 60,000 characters are replaced by a pointer telling the model to filter with `findings.lookup`.

## Registry contents (generated from `default_registry()`)

| Tool id | Capability | Scope | Required input | Timeout / rate | Credentials | Available now |
|---|---|---|---|---|---|---|
| `cyber.kb.search` | Search the versioned cyber knowledge base (Entra, Azure, detection); returns cited sections. | local-files | query | 10 s / 60 per min | none | yes |
| `entra.ca.assess` | Assess Entra Conditional Access coverage from a Graph snapshot file (read-only, HCA-001..010). | local-files | snapshot_path | 30 s / 60 per min | none | yes |
| `evidence.normalize` | Convert a Maester TestResults.json or Prowler OCSF file into Haven findings. | local-files | format, path | 30 s / 60 per min | none | yes |
| `evidence.verify` | Independently verify an evidence bundle; optionally re-derive claims from a raw snapshot. | local-files | bundle | 60 s / 60 per min | none | yes |
| `findings.lookup` | Filter findings in a stored evidence bundle by status, check id or domain. | local-files | path | 10 s / 60 per min | none | yes |
| `entra.graph.collect` | Collect a read-only Conditional Access snapshot from an authorized tenant via Microsoft Graph. | tenant-read | emergency_account_ids | 120 s / 2 per min | HAVEN_GRAPH_TOKEN from the environment; never logged or returned | no: live tenant access is disabled (set HAVEN_CYBER_ALLOW_LIVE=1 for an authorized tenant) |

Every tool is `read_only=True`. The registry refuses write tools outright (`write_not_authorized`). Changes to production configuration, privilege, credentials or targets need a separate, explicitly authorized and audited path, which does not exist yet by design.

## Tool contract (`ToolSpec`)

`id`, `capability` (one line), `input_schema` and `output_schema` (JSON Schema; `additionalProperties: false` on inputs), `domain`, `read_only`, `scope` (`local-files` | `synthetic` | `tenant-read` | `lab`), `permissions` (least-privilege API scopes), `credentials` (handling rule), `prerequisites()` (returns available + reason), `timeout_s`, `rate_per_min`.

## Errors

`{"ok": false, "error": {"code", "message", "retryable"}}` with these codes: `unknown_tool`, `invalid_input`, `path_out_of_scope`, `not_found`, `prerequisite_failed`, `write_not_authorized`, `rate_limited` (retryable), `timeout` (retryable), `tool_failed` (an exception inside a tool; the agent loop keeps running).

## Audit

One JSON line per call in `runs/audit.jsonl`: time, tool, caller (`mcp`, `slice`, `local`), sha256 of the canonical arguments, ok, error code, milliseconds. Arguments themselves are not stored, so paths and tokens never land in the log.

## Using it from Hermes (verified 2026-10-31)

```bash
echo Y | hermes mcp add haven-cyber --command ~/.local/share/haven-cyber-venv/bin/python \
  --env PYTHONPATH=<repo>/labs/cyber --args -m haven_cyber.mcp_server
hermes mcp test haven-cyber        # ✓ Connected, ✓ Tools discovered: 4
```

The venv needs only `mcp` (1.x or 2.x). The rest of `haven_cyber` is standard library. `scripts/mcp_smoke.py` drives the server end to end with the official client: it lists tools, searches, assesses the weak fixture, and confirms the path guard and the live-tenant gate.

## Evaluation tool set

The A/B/C harness uses an in-process copy of the same capabilities (`eval/toolenv.py`): `kb_search`, `entra_ca_assess`, `verify_tool_finding`, `azure_rbac_check`, `run_command` (deterministic simulated lab host). All five are offered on every scenario, so tool *selection* is measured:
- a tool that doesn't apply returns `not_applicable` (counted as a bad call);
- an unknown name counts as a hallucinated tool;
- a command that fails followed by a working one counts as recovery.
