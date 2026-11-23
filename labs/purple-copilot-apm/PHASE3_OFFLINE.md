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
- A source receipt qualifies for coverage and freshness when it is complete, includes the required partition, carries no warnings and falls within 24 hours of the report clock. Future collection or receive times limit confidence. Read `origin` alongside confidence: sidecar timestamps, revision, completeness and identity assurance are supplied by the local operator. Hash checking establishes byte identity. Independent collector authentication remains a future requirement.
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

## Assurance follow-up to review 6008224354

A report clock before the graph observation now raises an availability error. Artifacts received after the clock contribute no joins, counts, classifications or recommendations. Choose a later clock explicitly for a retrospective report. Graph membership is always attributed to its observation. The latest-observation groups use source collection time after filtering by receive time. Groups preserve record citations at each time, simultaneous contradictions and prior disagreement. Role-level projections without a stable assignment identity remain source observations and add zero independently identified entitlements. An assignment node's ID can identify an instance. Integrity, coverage, freshness and producer authentication are reported independently. Producer authentication remains unverified for local sidecars.

### Pinned producer experiment

PowerShell 7.4.13 ran the original EntraOps exporter on one invented EAM input and the Maester 2.3.0 result writer on one synthetic Pester object with mocked session/catalog functions. The Maester routine includes machine metadata, so generated artifacts stay private. The OpenGraph output had three nodes and four directed edges, including an assignment node. Both exact serialized files were accepted by the production importer. These SHA-256 values identify this execution; PowerShell object ordering and local metadata can vary across runs.

| Output | Digest |
| --- | --- |
| OpenGraph | `0a3afb796533a109e59458d6ba25075a6b7e64fe490ffc303826b037fc2fd283` |
| Maester stable | `7d539ece1e958ebe351acd46b12ccc5f7bc30ede0a0164ac967f0b2d1e68d47f` |

```bash
work=$(mktemp -d)
curl -fsSL https://raw.githubusercontent.com/Cloud-Architekt/EntraOps/5bdaebd1f8c4d8a037025b312e9a05405649e378/EntraOps/Public/PrivilegedAccess/Export-EntraOpsPrivilegedEAMBloodHound.ps1 -o "$work/eo.ps1"
curl -fsSL https://raw.githubusercontent.com/maester365/maester/7413c42d3fcc724dfea94d2726e690ddd364d914/powershell/internal/ConvertTo-MtMaesterResult.ps1 -o "$work/stable.ps1"
(cd "$work" && echo '7d789f8304ab59d8879dc642cbc34597ebfb38bdd469bdef8a0efb811ca8214f  eo.ps1
c982c7cb04bacb4ac5205810a8ddd6a72de42894b0ffb3adfff9ea97e64bb0fd  stable.ps1' | sha256sum -c -)
pwsh -NoProfile -File tests/producers/serialize.ps1 -SourceDir "$work" -OutputDir "$work/outputs"
APM_STATE="$work/state" PYTHONPATH=. python3 tests/producers/check.py "$work/outputs"
```

The rc83 native family pipeline and upstream redacted/aggregate-object generation remain unqualified. Duplicate test identities, non-ID selectors, merged results and null classification arrays are rejected. Empty classification arrays preserve absence of classification. Synthetic tests continue to cover mixed-source, derived and redacted references. The P3-15 and P3-17 scores concern the offline harness only.
