# Purple Copilot APM milestone 1

| Field | Record |
| --- | --- |
| Assignment | Operator-requested Purple Copilot APM first milestone, no historical research thread or issue assigned |
| Base | `erpzz/haven` main at `53387e74a0ad90786ac3ea16753c8ad99142e9df` |
| Owned path and branch | `labs/purple-copilot-apm/`, `feat/purple-copilot-apm` |
| Governance inputs at base | `AGENTS.md` SHA-256 `ba1d6d4002cc6cbea88e027c92e1136f382bc5451dc8bb945df18145b38e0eab`, `PRECEDENCE.md` `a27fe82ee432ae40e3cb285ba8b6fa57793a4f9b15ab8ef8fdc1ba713bf5b146`, `START_HERE.md` `35e795fec80918140ac846c448330f0f31d4c5d9d2ac5c5774b04d6d3da66e50` |
| Publication | Public-safe implementation and aggregate synthetic results. Runtime databases, credentials, host inventory and raw conversations stay private. |
| Disposition | Feature PR for independent review. Existing REQ/AT/EX identifiers and shared contracts are preserved. |

## Decisions

Use the official CLI and its PostgreSQL graph backend. The initial three-container deployment exhausted the development host’s Docker storage during container creation. The two-service deployment succeeded. Bind CE and the dashboard to loopback, isolate privileged sample setup, use the existing Haven gateway for reasoning and keep scheduled deterministic analysis independent of inference availability.

## Evidence

Executed on 2026-11-21 UTC. CE 9.10.1 reported the upload job complete with 32 files, zero failures and zero partial failures. Both catalog queries returned source IDs matching the corresponding official sample group record. The AD collector metadata declared 113 groups while its archive member contained 115. AD snapshots retained 12 observed relationships under degraded collection health. Entra snapshots retained one observed relationship. Its collector timestamp is unknown. Checksums for upstream archives, skills, executables and model weights are in the deployment scripts. [Installation and primary sources](README.md#verification)

## Interface changes

The new sidecar consumes the signed CE REST API and the community MCP stdio protocol. Its client-facing MCP tool accepts only a catalog scope. Local versioned observations contain query text, directed edges, source object IDs, timestamps and quality evidence. The read-only dashboard and model prompts refer to immutable snapshot IDs. The inference writer can append hypotheses and cannot update graph or lifecycle rows. The existing Model Lab gateway serves the managed local route without a shared-schema change.

## Acceptance

| Executed check | Expected | Observed |
| --- | --- | --- |
| `python3 -m unittest discover -s tests -v` | Graph comparison, lifecycle and authorization pass | 12 passed, including retry, stale/repeated collection, degraded coverage, reappearance, read-only DB and hypothesis-writer restrictions |
| `python3 -m apm.collect` and an external scheduled scan | Versioned baseline followed by persistence | 12 AD and 1 Entra membership new, then 12 and 1 persistent. AD returned a quality warning. |
| `tests/live_mcp.py` in pinned community environment | Fixed tool catalog, two denied calls, two real graph reads | Passed through stdio with CE Read-Only credentials |
| Desktop and mobile Chromium dashboard | Navigate AD and Entra snapshots, expand evidence, fit viewport | Passed at 1280 and 390 CSS pixels after fixing mobile overflow |
| `PYTHONPATH=. python3 tests/live_sample.py` | Qwen3-8B reports both source-verified counts, stores linked hypotheses | Both passed with completed responses. First prompt revision hit the output limit twice, retained locally as incomplete. |
| `PYTHONPATH=. python3 tests/live_haven.py` | Actual Haven gateway authenticates member, routes to local 8B backend and stores review | Passed on the Entra sample via `haven-slink`. |

## Risks and open questions

The catalog covers two direct group-membership paths. Evidence of membership alone does not establish malicious activity or justify automatic removal. The immutable sources cannot establish real remediation. Confirmed remediation was exercised with independently versioned synthetic test inputs. The two count checks provide limited evidence of model behavior. The observed Entra response reported the count without a substantive investigation hypothesis. This deployment uses the foreground external scheduler. Persistent supervision through the documented systemd user command depends on a running user manager.

## Next package

Review the catalog and lifecycle contract before adding EntraOps and Maester adapters, critical-asset scoring, operator-owned investigation tracking and optional Sentinel export. No production connection is part of this milestone.
