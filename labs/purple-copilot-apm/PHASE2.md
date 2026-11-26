# Evidence-driven membership path reviews

The path catalog follows directed AD `MemberOf` and Entra `AZMemberOf` edges into designated groups. The unit of review is an ordered sequence of source ID, relationship type and target ID triples. A changed intermediate group creates a different path even when the principal and target stay the same.

## Run a review

Complete the [sample lab setup](README.md#start-the-sample-lab), then run these commands from this directory.

```sh
python3 -m apm.path_history
python3 -m apm.path_history --show RUN
python3 -m apm.dashboard
```

Open **Path history** on the dashboard. A path expands to its finding ID, component scores, prior-route references and any removal evidence. The CLI emits one JSON summary per asset. A quality warning yields exit 2 after the snapshots have been committed. The existing scheduler runs both direct membership and path jobs. Repeated scheduled reads retain the archive’s original source identity.

The registry defaults to `assets.json`. Select a private replacement with `APM_ASSETS` when needed. Declare a unique key, platform, exact synthetic target ID, sensitivity and privilege designation. The CE adapter verifies membership inventory coverage for the target in the pinned archive before querying. Only the platform’s fixed directed membership template is available. Four hops and 128 distinct simple paths bound a review. An over-budget result yields an unavailable observation. The templates adapt the SpecterOps group-nesting hygiene queries by anchoring the target, bounding depth and including direct members. [AD template upstream](https://github.com/SpecterOps/BloodHoundQueryLibrary/blob/ca4924e007ed8094850f980239a1f2ba2bf23b95/queries/AD%20Groups%20nested%20more%20than%203%20levels.yml) · [Entra template upstream](https://github.com/SpecterOps/BloodHoundQueryLibrary/blob/ca4924e007ed8094850f980239a1f2ba2bf23b95/queries/Azure%20groups%20nested%20more%20than%203%20levels.yml)

## Evidence contract

CE returns a graph of nodes and edges. The adapter resolves graph-local IDs to stable object IDs, reconstructs directed simple paths from observed edges, and independently enumerates the archive membership lists. The private SQLite history records the query, raw graph, archive digest, relevant source filenames, upload job, observation time, findings and quality issues. CE ingestion time supplies no original collection time or independent collector identity.

The synthetic directory adapter demonstrates fresh acquisition from a changing local source. Each read opens a read-only SQLite transaction, checks the expected dataset ID, enumerates group and membership partitions and reads a separate deletion journal. It issues a unique collector-run ID and records start, completion and observation times. A journal entry identifies a concrete event, directed edge and event timestamp. The synthetic source and its journal are trusted fixtures under the local account. The lab does not implement attestation for external collectors.

A path stream is scoped by source, collector, dataset, platform, target and query. A changed score designation can follow the same underlying paths. Reusing a collector-run ID with a conflicting inventory, replaying an older source after a newer one, or submitting conflicting observations fails. Path snapshots and their findings commit atomically. The two evidence sources have distinct origins in storage.

| Observation | Result |
| --- | --- |
| First path, or return after absence | New |
| Same complete directed sequence | Persistent |
| New sequence replaces a previously observed route between the same endpoints | Changed, with superseded path IDs |
| Previous path absent | Missing, evidence insufficient for removal |
| Query, collector or required partition unavailable | Carry prior state, mark observation unavailable |
| Fresh complete enumeration plus an independent deletion event on the missing path | Removed, with event ID and edge |

The positive removal rule checks the collector identity, exact partitions, target enumeration, matching inventory-derived paths, UTC times within 24 hours, a distinct source run and an absent journaled edge. The deletion must postdate the last path observation and precede collection completion. A different hash or a second read of absent data is insufficient. Removed describes a particular route. Another route can still reach the target.

The deterministic review priority is the sum of target sensitivity (50 critical or 30 high), privilege designation (30 or 0) and verified collection (20 or 0). These are transparent lab review weights. Confidence and each component remain available independently of the total. The model has no scoring or state-transition role.

## Investigate one finding

With the local Haven gateway running and a local member key in `HAVEN_GATEWAY_KEY`, select a run and finding ID from the dashboard. Run the investigator with the pinned MCP virtual environment.

```sh
"$APM_STATE/community/.venv/bin/python" -m apm.investigator RUN FINDING_ID triage
```

The choices are `path`, `quality` and `triage`. The MCP process is bound to the selected observed CE finding. Its path read checks the operator registry and revalidates every directed edge through the community BloodHound MCP. The quality read returns that finding’s historical collector evidence. For combined triage the model chooses the first tool and requests the remaining source before writing its assessment. The dispatcher enforces a two-read maximum, fixed tool names, empty arguments and the selected finding outside the model.

Private investigation receipts retain every returned model message, tool selection, citation, stable object ID mapping, timing and conclusion status. The model sees compact aliases for long IDs. Reports attach full IDs to the evidence references. Incomplete responses remain available for inspection. The validator checks citations, the numeric path length and collection qualifications. General interpretation still requires human review.

## Reproduce validation

```sh
python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 tests/path_scenario.py
PYTHONPATH=. python3 tests/live_paths.py
PYTHONPATH=. "$APM_STATE/community/.venv/bin/python" tests/live_finding_policy.py
PYTHONPATH=. "$APM_STATE/community/.venv/bin/python" tests/bench_investigator.py
```

The scenario creates a disposable synthetic directory, changes its records and retains the sidecar’s before/after evidence. To acquire another observation from that schema, use `python3 -m apm.synthetic_collector FILE DATASET_ID`. The model benchmark needs the sample CPU runner on 8135 and port 8877 free for an isolated, authenticated Haven gateway. The deterministic tests and scheduled jobs run without inference.

## Future EntraOps contract

The official exporter consumes preclassified EAM results per RBAC system and emits OpenGraph nodes, directed edges and assignment context. Its edge properties include `admintierlevel`, `admintierlevelname`, `service`, `taggedby` and `taggedbyrolesystem`. Classification can be absent on referenced stubs. The proposed offline adapter would retain exporter revision, dataset scope, upstream collection-run ID, timestamps, artifact digest, original source/target IDs and assignment relationship. It would preserve the original tier value and its role system, join within the same dataset and surface unmatched IDs or unknown tiers as uncertain. Assignment-specific classification belongs on the assignment. Any effect on priority needs a separately reviewed deterministic rule. No exporter, tenant client or extension installation is invoked here. [Exporter implementation](https://github.com/Cloud-Architekt/EntraOps/blob/5bdaebd1f8c4d8a037025b312e9a05405649e378/EntraOps/Public/PrivilegedAccess/Export-EntraOpsPrivilegedEAMBloodHound.ps1) · [OpenGraph schema](https://github.com/Cloud-Architekt/EntraOps/blob/5bdaebd1f8c4d8a037025b312e9a05405649e378/Integrations/BloodHound/OpenGraph_EntraOps_Extension_Schema.json)

## Executed evidence — 2026-11-21 UTC

The Phase 2 review branch starts at milestone-one commit `cca49be`. The unchanged milestone-one tests and the path regression tests passed together (19 tests). Both real stdio MCP suites passed, including five Phase 2 denial cases. The path history dashboard displayed 21 expandable findings at desktop and mobile widths.

| Live CE query on official synthetic archive | One hop | Two hops | Three hops | Wall time including verification and persistence |
| --- | ---: | ---: | ---: | ---: |
| Phantom Administrators | 8 | 12 | 1 | 0.032 s |
| Resource Group Admins | 1 | 0 | 0 | 1.051 s |
| Consent review | 4 | 1 | 0 | 0.018 s |

These timings are one local scan. The two Entra reviews share one decoded inventory. AD retained the previously observed archive count discrepancy. All three groups have limited collection confidence because the historical source cannot attest to a fresh acquisition.

**Independently changing synthetic source.** Four paths were new at baseline and persistent on repeat acquisition. The longest was USER → A → B → C → COUNCIL. Replacing A → B with A → C produced two changed routes, two persistent routes and two missing routes. Making the journal unavailable preserved those states and marked the observation unavailable. When the journal returned, its deletion event corroborated removal of the two prior routes. A subsequent journaled deletion of C → COUNCIL left zero observed routes and six historical routes marked removed.

**Model evaluation.** On the final Qwen3-8B CPU run through the authenticated Haven gateway, path review selected the path tool in 21.220 s, quality review selected the collection tool in 17.645 s, and combined triage selected both in 46.875 s. All three produced completed cited responses. The combined response identified the three-hop nesting and qualified it with the AD collection warning. The exact IDs, edges and collector receipts are supplied by the tools and retained separately from the interpretation. Earlier prompt versions produced a truncated response, a missing citation and an unsupported topology claim. A regression check rejects that topology claim when only collection evidence is available. Three benchmark tasks on one finding establish integration behavior, with general investigation reliability still unmeasured.

**Review boundary.** This milestone covers group membership within each platform. Cross-platform trust paths, production collector freshness, automated remediation and live EntraOps/Maester ingestion remain future work.
