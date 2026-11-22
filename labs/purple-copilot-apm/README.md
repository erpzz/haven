# Purple Copilot APM

Haven’s local identity review lab monitors direct membership of two designated critical assets in SpecterOps’ synthetic AD and Entra samples. Each membership is a one-edge identity access path. A signed REST read records the actual graph, an independent archive read checks collection coverage, and SQLite retains the evidence behind every change. The dashboard opens at [localhost:8134](http://127.0.0.1:8134/).

For configurable critical assets, directed multi-hop comparisons and finding-scoped investigation, see the [Phase 2 runbook](PHASE2.md).

To correlate offline EntraOps and Maester evidence with a historical sample path, see the [Phase 3 runbook](PHASE3_OFFLINE.md).

For every attack edge into BloodHound's Tier Zero (permissions, sessions, delegation, certificate abuse and Entra application rights), ranked by the identities able to gain it, see [Tier Zero control](TIER_ZERO.md). To review those findings conversationally in Hermes Agent with an evidence gateway and answer verifier, see [Hermes](HERMES.md).

## Start the sample lab

Use a Linux x86-64 host with Python 3.11+, Docker Engine with Compose v2, curl, tar, sha256sum, uv and free loopback ports 8080 and 8134. The CPU model runner also uses 8135. Allow space for the database, Docker layers and a 3.05 GB GGUF. Run the commands below from this directory. Private state defaults to `~/.local/state/purple-copilot-apm`. Set `APM_STATE` consistently to use another private directory.

```sh
export APM_STATE="${APM_STATE:-$HOME/.local/state/purple-copilot-apm}"
./ops/fetch.sh
./ops/ce.sh install
```

The installer runs the official BloodHound CLI with a digest-pinned Compose file and the PostgreSQL graph driver. Save the generated local administrator password privately. The first launch can take longer than the CLI readiness message. Wait for the local login page, then run the two operator-only actions below. Each prompts for the password. Only the pinned, project-owned loopback container is eligible for bootstrap. The archive hashes are checked before upload.

```sh
python3 -m apm.setup ingest
python3 -m apm.setup reader
python3 -m apm.collect
python3 -m apm.dashboard
```

The official AD archive has a count discrepancy. The collector **saves both snapshots and exits 2** to report the quality warning. The dashboard remains usable. From a second terminal, run the external scheduler. It takes a snapshot immediately and repeats hourly. A file lock serializes concurrent collection jobs. SIGTERM or Ctrl-C stops the scheduler after its current scan. The schedule rereads the local CE graph and collector evidence. Upstream collection times remain those of the archived samples.

```sh
python3 -u -m apm.schedule --seconds 3600
```

For a persistent Linux user service on hosts with a running systemd user manager, the same entry point works under supervision.

```sh
systemd-run --user --unit=purple-apm-scans --property=Restart=on-failure \
  --working-directory="$PWD" --setenv="APM_STATE=$APM_STATE" \
  "$(command -v python3)" -u -m apm.schedule
```

Use `./ops/ce.sh down` to stop CE and retain its named PostgreSQL volume. Use `./ops/ce.sh up` to restart it. Stop a supervised scheduler with `systemctl --user stop purple-apm-scans`. A failed or interrupted upload retains its job receipt locally. A repeat of the ingest command checks the job and preserves a record of any uncertain upload before retrying. A terminal partial or failed job needs operator inspection in CE. Keep its receipt when starting a fresh sample lab.

## Evidence and lifecycle

The catalog selects the Phantom Domain Admins group and the Entra Resource Group Admins group by immutable sample object ID. Both assets are designated for review. Group names alone do not establish effective permissions. The versioned `runs.evidence` JSON contains the exact query, archive digest and member filename, expected members, graph-local node/edge references, stable source/target object IDs, CE timestamps, ingest job ID, observation time and quality issues. The AD collector filename encodes local time without a timezone. The Entra member file supplies no trustworthy collection time. Ingestion and observation times are tracked independently.

| Event | Finding lifecycle |
| --- | --- |
| First observation or reappearance | New, open |
| Present on successive observations | Persistent, open |
| Absent with missing coverage, stale input or unknown collection time | Missing, coverage required |
| First independently enumerated absence on a fresh, complete inventory | Missing, awaiting corroboration |
| Second corroborating complete inventory, distinct source digest, later UTC collection time | Confirmed-remediated, closed |
| Request or parse failure | Prior state retained, collection unavailable |

The confirmation policy requires an exact match to the authoritative membership inventory and a UTC collection time within 24 hours of observation. Unavailable or degraded coverage breaks corroboration. Immutable sample replays can never confirm remediation. Synthetic transition tests exercise the two-collection confirmation contract. The sidecar does not remove edges from CE, run tenant collectors or act on a model response.

## Read-only MCP and analyst

Configure a local stdio MCP client with the command `$APM_STATE/community/.venv/bin/python`, arguments `-m apm.mcp_reader`, this directory as its working directory and the absolute `APM_STATE`. The only advertised tool is `review_memberships(scope)`, where scope is `ad` or `entra`. The adapter checks the CE identity and sole role, invokes the pinned community server over private stdio and supplies a fixed query. Register only the adapter with clients. Local MCP receipts preserve each approved query and response. Upstream resources and unrestricted tool dispatch stay private to the subprocess.

The default analyst uses the existing Haven Model Lab gateway, a direct gateway key in `HAVEN_GATEWAY_KEY`, and its managed `haven-slink` route with egress `NONE`. With that local backend already running on port 8877, use `python3 -m apm.analyst SNAPSHOT_ID`. The prompt takes a bounded excerpt from the corresponding pinned SpecterOps AD or AzureHound skill. The model receives an observation and has no tools. SQLite stores its request, model metadata and complete response as a hypothesis referencing that observation.

On a separate test host, the pinned CPU runner provides the same chat-completions contract. Start it in another terminal with `./ops/model.sh`, then run `python3 -m apm.analyst SNAPSHOT_ID --sample-runner`. This uses Qwen3-8B IQ2_M with llama.cpp b12608. The runner supports `APM_MODEL_FILE` for a predownloaded GGUF and verifies its digest. All listeners are loopback-only. The trust boundary assumes a private local OS account. Raw source graphs, tokens, SQLite files and model responses belong in its private state directory.

## Verification

```sh
python3 -m unittest discover -s tests -v
"$APM_STATE/community/.venv/bin/python" tests/live_mcp.py
PYTHONPATH=. python3 tests/live_sample.py
```

The first suite uses temporary databases. The second exercises the actual MCP tool inventory, denials and both graph reads. The third requires CE, the seeded samples and the local model runner. It checks graph counts against source IDs, AD quality evidence, model output and linkage to the stored hypothesis. A matching count tests a narrow behavior. It does not qualify general model accuracy.

The install scripts pin the CLI, service images, upstream MCP revision and its frozen uv lock, both sample archives, skill documents, inference binary and GGUF. The collection, store and dashboard use the Python standard library. [CE installation](https://bloodhound.specterops.io/get-started/quickstart/community-edition-quickstart) · [REST contract and samples](https://github.com/SpecterOps/BloodHound-Docs/tree/61d0859a461ccc0aad8b06fefabd6b4df0c079bc/docs) · [Community MCP](https://github.com/mwnickerson/bloodhound_mcp/tree/cdb17097e761c8a8622cb93bc3ba49a9e150bb6e) · [SpecterOps skills](https://github.com/SpecterOps/skills/tree/f5dbbb23059c1186c695c832eedf88c8f3a0fcb4/plugins/bloodhound) · [Haven Model Lab](../model-lab/)

To test the Haven integration on an isolated development host with port 8877 free, run `PYTHONPATH=. python3 tests/live_haven.py`. It creates a temporary Model Lab, issues a local member key, attaches the sample inference server, exercises the authenticated gateway and closes the temporary Lab. See the [milestone handback](HANDBACK.md) for executed results.
