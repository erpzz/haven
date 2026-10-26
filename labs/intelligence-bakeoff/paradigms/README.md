# Cross-paradigm inference bake-off

Which architecture family gives the most capability on owner hardware: an RTX
2070 Super with 8 GB, a 12-core Ryzen and 64 GB of RAM? This lab runs one
model per family through the frozen tool benchmark in
[`../distillation/tool_sft`](../distillation/tool_sft). Each model runs under
the same llama.cpp build and server settings. The lab also measures the
long-context costs where state-space and linear-attention designs should
differ from attention: decode speed after 1K, 8K and 32K prompt tokens, and the
KV or recurrent-state memory.

- [`PREREGISTRATION.json`](PREREGISTRATION.json) is committed before any
  inference. It fixes:
  - the models, each with repo, revision, file, SHA-256, license, parameters
    and architecture;
  - the server command and the eval command;
  - the metrics and the decision rules.
- `fetch.py` downloads each model at its pinned revision. Downloads resume.
  The SHA-256 is checked while streaming, and a file is renamed into place only
  after its digest matches. It drops written pages from the page cache as it
  goes, so a running model's weights are not evicted.
- `session.py` runs one bounded GPU session:
  1. wait for an idle Lab, disconnect it from Strata, stop Strata and take the
     Lab's cooperative GPU lease;
  2. for each model, start a llama-server on its own loopback port with a
     private key, then run the probes and the benchmark;
  3. always restore: start Strata, then reconnect the Lab with
     `labctl.py strata`.
- `report.py` re-verifies every record with verifier v3 and emits sanitized
  aggregates only: Wilson intervals, paired sign tests against the reference,
  probe timings and buffer sizes.

Raw records, logs and keys stay in a private directory on the host. Tests:
`python3 -m unittest discover -s paradigms/tests -v`, run from
`labs/intelligence-bakeoff`.

Results: [`RESULTS.md`](RESULTS.md).
