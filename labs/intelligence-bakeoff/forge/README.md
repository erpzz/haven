# Operation Forge

This lab turns Hermes session failures into reproducible fixes and small, independently checkable capabilities. It is an **isolated research package**: the native Hermes plugin is not installed into the operator's live profile, and the synthetic Entra analyzer does not connect to a Microsoft tenant.

The current implementation provides:

- A native Hermes `transform_tool_result` hook that appends an observation record to terminal and process results without altering their exit codes or granting authority.
- Local, owner-only extraction of Hermes session exports into call/result records with stable event IDs, source hashes and trace-line references. Missing results stay unknown.
- A small versioned Markdown corpus searched with SQLite FTS5/BM25. Cached indexes and results are per thread, bounded, and invalidated by content hashes on every lookup.
- An offline Entra Conditional Access MFA analyzer for **shipped synthetic fixtures only**, with evidence pointers, a second truth-table reconciliation and per-policy scope. A narrow caller-invoked routing helper can choose this tool for a single known fixture policy and verifies its returned report.
- Four original synthetic correction examples with reproduced results and explicitly hypothetical errors, plus four distinct held-out evaluation examples. This is a seed, not a sufficient training corpus.

The engineering findings, research program and experiment ledger are in [FINDINGS.md](FINDINGS.md), [RESEARCH.md](RESEARCH.md) and [experiments/ledger.jsonl](experiments/ledger.jsonl). [CHECKPOINT.md](CHECKPOINT.md) is the concise resume point.

## Run locally

Run from this directory with Python 3.11+ and SQLite FTS5:

```sh
python3 run.py search 'Conditional Access MFA report-only'
python3 run.py entra
python3 run.py entra --fixture entra-heldout
python3 run.py route --fixture entra-demo --policy-id synthetic-mfa-or-device
python3 -m unittest discover -s tests -v
python3 bench_retrieval.py --iterations 500 --repetitions 9
hermes plugins doctor .hermes/plugins/haven-forge --ci
```

The optional integration probe copies the plugin into a temporary Hermes home, enables only that plugin there, blocks network connections, calls its real Hermes dispatch and terminal hook, and removes the temporary home. Supply a compatible Hermes source checkout and an interpreter with its dependencies:

```sh
python3 verify_hermes.py --source /path/to/hermes-agent
```

To analyze private exports, first create an owner-only directory outside any Git checkout, then pass the existing session and trace exports. The output is exclusively created with mode 0600 and refuses to overwrite an existing file. The export, extracted events and manual classifications can contain private commands or identifiers even when Hermes redaction was enabled; do not commit them.

```sh
FORGE_PRIVATE_DIR="$HOME/.local/state/haven-forge/session-review"
mkdir -p "$FORGE_PRIVATE_DIR"
chmod 700 "$FORGE_PRIVATE_DIR"
python3 run.py extract "$FORGE_PRIVATE_DIR/glasshouse.session.jsonl" \
  --trace "$FORGE_PRIVATE_DIR/glasshouse.trace.jsonl" \
  --output "$FORGE_PRIVATE_DIR/events.private.jsonl"
```

Forensic extraction does not automatically admit training examples. `build_dataset.py --output /new/output/directory` regenerates the original synthetic seed; it executes only three local synthetic shell commands and no model or network calls. Its admission receipt checks schema, provenance, group separation and hash binding, but is not a cryptographic attestation of a reviewer or general-purpose secret scanner.

The optional [CPU benchmark](experiments/bench_qwythos.py) requires an existing model, an existing compatible `llama-server`, an isolated owner-only output directory, AC power, and sufficient free memory. It starts one CPU-only child bound to a verified owned loopback port and stops that child at the end. Its cases and limits are in [v1](experiments/entra-heldout-v1.json), [v2](experiments/entra-heldout-v2.json), and [v3](experiments/entra-heldout-v3.json); it never accesses a live tenant. Do not run it against a model file or machine owned by another active workload.

## Boundaries

An exit code of zero means the command process exited zero. It does not verify the user's goal. Diagnostic pattern matches are advisory because output may contain quoted text. A running or missing result is not a successful result. Retrieved knowledge is reference data, never operational instructions or authorization. Policy findings do not prove sign-in, tenant-wide MFA coverage, licensing, deployment readiness or the safety of enabling a policy. Unsupported controls fail to `indeterminate`.

The original preserved traces and detailed forensic rows stay in private operator storage. The caller must supply a known fixture and policy ID; this is not integrated into the live production request path and does not extract entities from arbitrary requests. No automatic cloud fallback, background agent, live scan, model update, service restart, training job, tenant access or deployment is introduced by this lab.
