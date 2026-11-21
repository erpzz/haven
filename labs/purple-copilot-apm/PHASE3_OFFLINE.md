# Phase 3 offline evidence adapters

A reviewer can attach EntraOps assignment context and Maester test results to an observed BloodHound membership path. The CLI stores exact source bytes, normalized records and historical correlations in a separate private SQLite database. The existing graph reader opens path history read-only. The importer and report use the Python standard library and run without a model or tenant credentials.

## Reproduce the combined view

Run from `labs/purple-copilot-apm` with Python 3.11 or newer. The demonstration requires an empty directory. It first replays a captured CE sample observation through the Phase 2 history writer. It then imports and correlates four generated fixtures using the same functions as the CLI.

```bash
export APM_STATE="$(mktemp -d)"
report="$(mktemp)"
python3 -m apm.offline.demo > "$report"
fp=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["path_context"]["fingerprint"])' "$report")
fixtures=tests/offline_fixtures
read -r artifact status < <(python3 -m apm.offline import "$fixtures/entraops_eam.receipt.json" "$fixtures/entraops_eam.json")
echo "$status"
python3 -m apm.offline link 1 "$fp" "$artifact"
python3 -m apm.offline show 1 "$fp" --as-of 2026-11-21T20:00:00Z
```

The second import prints `replayed`. Repeating a link retains one correlation. Use `--section posture_evidence` to read one section. The full JSON includes per-record joins, independent graph and source timestamps, provenance, source coverage and a deterministic recommendation.

In the example, a sample user belongs to the resource administrators group through one directed `AZMemberOf` edge. Two synthetic EntraOps exports describe an eligible role at scope `/`. Two Maester exports each report a failed synthetic test affecting the group. The four privilege rows include two principal classifications. The two posture rows retain separate artifact citations. These counts describe source records. The recommended investigation is to verify current membership and seek a separate activation record.

## What the importer accepts

| Source | Normalized evidence | Restrictions |
| --- | --- | --- |
| EntraOps per-system EAM | Principal native ID and kind, role assignment/instance identity, definition, scope, PIM mode, subtype, transitive reference and per-system classifications | Receipt supplies the RBAC system. Unknown principal kinds and contradictory PIM values fail ingestion. Missing PIM evidence yields unknown. |
| EntraOps OpenGraph | Directed source and target references, declared kinds, assignment context, scope and tier properties | Accepts the pinned graph envelope and ID selectors. Known role relationships require consistent RBAC and target kinds. Unknown overlay edges and dangling targets are retained for inspection. None participate in graph traversal. |
| Maester 2.3.0 | Run execution time, test ID, result, applicability/skip reason, severity and structured object references where present | One tenant, UTC execution time, unique test IDs. Standalone affected-object exports and merged reports are outside this reader. |
| Maester 3.0.0-rc83 | Adds schema 2.1, catalog version, reason code, product and service context | An unsupported schema or catalog fails. Explicit tenant-level tests can yield tenant context. A specific asset requires a supported typed reference. |

The source revisions, upstream file links and construction method for each fixture are recorded in the [fixture index](tests/offline_fixtures/README.md).

## Identity, history and confidence

- The private database stores the receipt, SHA-256 of the exact file, exact bytes, ordered normalized records and joins against a specific Phase 2 run, snapshot digest and path fingerprint. Source, dataset, tenant, run and digest determine the immutable artifact ID. Receipt changes beyond a replay's receive time conflict. Import transactions roll back together.
- The selected dataset and tenant must match the graph namespace. The only enabled historical namespace is the pinned official Entra sample. A native ID must match the kind and an endpoint of the observed path. Other datasets may be imported for inspection. Foreign, ambiguous, incompatible, redacted and unresolvable references cannot provide exact asset context.
- For Maester, native joins require an Entra instance and structured Graph object evidence. The derived UniqueId is retained as a source reference. Aggregates that mix sources require test-local corroboration for that object. Unknown references remain inspectable in the original bytes. A passing test and an absent assignment have no authority over the graph lifecycle.
- A source receipt is verified for coverage when it is complete, includes the required partition, carries no warnings and falls within 24 hours of the report clock. Future collection or receive times limit confidence. Read `origin` alongside confidence: sidecar timestamps, revision, completeness and identity assurance are supplied by the local operator. Hash checking establishes byte identity. Independent collector authentication remains a future requirement.
- The CLI report is private. It can contain native IDs and source classifications. Public evidence here uses only artificial exports and the official synthetic graph. Inputs are bounded to 16 MiB. The SQLite file includes raw bytes and needs the same local access controls as its sources.

## Reproduce verification

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s phase3_contract -v
actual=$(mktemp)
PYTHONPATH=. python3 tests/offline_campaign.py > "$actual"
cmp "$actual" evidence/phase3/actual.jsonl
python3 phase3_contract/evaluator.py --adapter-results "$actual"
```

The independent runner uses each frozen operation and input to derive a decision. Some vectors exercise a pure policy or the synthetic harness, including tier ordering and email redaction. The gateway vocabulary in P3-15 maps to fixed CLI sections. The runner blocks and records attempted outbound socket connections and child processes during import and review. Phase 3 adds no MCP tools. These checks do not measure an AI model or provide a general-purpose exporter for public reports.

For the optional CE integration test, start the existing sample-only deployment and provision the Phase 1 reader per the lab README. In an isolated directory, reference the existing official sample inputs and reader receipt. The test records one new local graph observation, queries the CE sample, correlates the generated exports and compares the graph database hash before and after enrichment.

```bash
sample_state="${APM_STATE:-$HOME/.local/state/purple-copilot-apm}"
export APM_STATE="$(mktemp -d)"
for item in reader.json ingest.json ad_sampledata.zip entra_sampledata.zip community; do
  ln -s "$sample_state/$item" "$APM_STATE/$item"
done
PYTHONPATH=. python3 tests/live_offline.py
PYTHONPATH=. python3 tests/live_paths.py
PYTHONPATH=. "$APM_STATE/community/.venv/bin/python" tests/live_mcp.py
PYTHONPATH=. "$APM_STATE/community/.venv/bin/python" tests/live_finding_policy.py
```

## Review and readiness

The [executed receipts](evidence/phase3/verification.txt) distinguish the CE sample query from the generated exporter inputs. The [20 actual results](evidence/phase3/actual.jsonl) can be compared against the frozen oracle from PR #111. There were no expected-output changes.

The supported shapes are ready for offline fixture review. Before approving live collection, validate independently produced, sanitized exports at the pinned revisions, including multi-system EAM, parameterized Maester tests, merged results and non-ID OpenGraph selectors. Current support rejects or withholds those unsupported shapes. Receipt trust and graph namespace enrollment would also need a collection design. This milestone measured neither live EntraOps/Maester collection nor a model's investigative performance.
