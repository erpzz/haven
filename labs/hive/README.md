# HIVE — Heterogeneous Internet Volunteer Execution (research pilot)

**Status: experimental real CPU transformer layer-sharding, not trained AI or production WAN inference.**

HIVE is a new, isolated experimental module for Haven's [HS01 federation](../../ops/haven-core/FEDERATION.md). Unlike HS01's *complete-request* worker routing, HIVE performs real sequential transformer layer forward passes in independent worker processes. The coordinator holds **only embeddings and the final projection**. Each worker loads **only its assigned contiguous transformer blocks**, not the other blocks or embeddings. A token traverses all workers, in order. End-to-end integration tests compare the emitted bytes with an identical monolithic transformer.

The initial checkpoint is **deterministic, randomly initialized, byte-level**, with real causal self-attention and feed-forward layers implemented in PyTorch. Its tokens are arbitrary bytes; it cannot write useful natural language. This is a transport, topology, correctness, latency, and node-failure prototype. **It does not yet shard Qwen, Strata, GGUF or a trained model.** It is not meant to be merged into the production Lab backend without a separate security and performance review.

## Scope and safety boundary

- CPU-first, separate `torch` dependency; optional `--device cuda` if a GPU-capable PyTorch install and compatible GPU exist. No installation, downloads, model replacement, service restart, or GPU execution occurs by opening this repository.
- All listeners bind **only `127.0.0.1`**. Clients accept literal loopback IPs only. For a second physical machine use an owner-approved **SSH local forward** to that machine's loopback HIVE worker. Do not expose the worker to a public listener or use unauthenticated TCP relays.
- Requests require a high-entropy private file-based bearer token (mode 0600 on POSIX), limited tensor dimensions, finite FP32 values, verified model identity, and an exact contiguous layer partition. No redirects, DNS endpoints or environment proxy use. This is a private trusted-worker prototype, **not hostile-peer isolation or confidentiality**: a worker receiving hidden activations may infer information about the prompt, and a compromised worker can lie about computed outputs.
- One generation is synchronous with no retry or silent fallback on failure. No speculative decoding, KV caching, efficient token-stream transport, P2P discovery, training or scheduling is claimed. Forward passes recompute the full context, intentionally simplifying correctness at the cost of speed.
- No non-stdlib dependency is introduced into `labs/model-lab`. Nothing changes existing Haven ports, workers, routing policies or Slink engine. The model lab remains the production path.

## Local two-worker run (in two or three terminals)

From `labs/hive`, create and activate an isolated environment that has PyTorch (`requirements.txt`). Do not install PyTorch into the existing Model Lab environment just for this test. Then:

```bash
python -m hive secret --output .hive-secret
python -m hive worker --secret-file .hive-secret --port 9171 --start 0 --stop 2
# another terminal
python -m hive worker --secret-file .hive-secret --port 9172 --start 2 --stop 4
# coordinator terminal
python -m hive run --secret-file .hive-secret --peer 127.0.0.1:9171 --peer 127.0.0.1:9172 --prompt Hive --new-tokens 4
python -m hive baseline --prompt Hive --new-tokens 4
```

Compare `tokens` and `output_hex`. The distributed JSON includes per-hop RTT, self-reported worker compute milliseconds, application-layer byte counts (not actual wire/network overhead), and end-to-end token rate. Performance is usually **worse** than monolithic inference on one host because this model is tiny and JSON/base64/full-context transport is inefficient. That negative result is useful.

## Safe physical two-host setup

1. On Slink (or another authorized host), start only one HIVE worker on its **loopback** address, using the same private test-spec and a privately provisioned secret. Never place the secret in chat, GitHub, command-line arguments or public receipts.
2. On the coordinator host, create an approved SSH forward like `ssh -N -L 127.0.0.1:9172:127.0.0.1:9172 haven` (the name `haven` is an example of an existing verified SSH alias, not a new address). The worker must be started on the remote host with `--port 9172` and `--start 2 --stop 4`.
3. Start the first worker locally on `127.0.0.1:9171` with `--start 0 --stop 2`. Run the coordinator as above.
4. Compare to local `baseline`, record real worker process ownership, CPU/GPU residency, RTT, bytes and energy if available. If no SSH access is established, the run is **NOT_EXECUTED**, not successful.

**Do not reuse Haven's existing Mac-worker tunnel or secret:** this is a distinct experiment and its independently authenticated worker port needs its own explicitly approved tunnel. Shut down the two HIVE worker processes and the owned test tunnel after the experiment. Never restart Slink's Model Lab or Strata for this pilot.

## Reproducible verification

```bash
python -m unittest discover -s tests -v
```

This suite launches **two independent OS worker processes** and makes actual HTTP requests over loopback. It verifies distributed byte-token equality with the full monolith, the worker forward counts, exact layer coverage, authentication denial, incompatible model fingerprints, peer loss without fallback, tensor bounds, private credentials and loopback endpoint policy. These are genuine CPU calculations; no model output is scripted or mocked. A successful run establishes local proof of *real cross-process execution*, **not** cross-host WAN, trained LLM quality, end-user privacy against untrusted peers, or GPU acceleration.

## Next engineering gates

1. Port a small **trained permissively licensed** decoder checkpoint to the same partition API; verify exact tensor/batch compatibility and compare held-out next-token logits to a nonsharded baseline (tolerance required for mixed-device arithmetic).
2. Switch full-context requests to an authenticated streamed binary activation protocol with bounded frames and optional KV caching; instrument network and CPU/GPU cost.
3. Perform a real two-host SSH-tunneled trial during an explicitly approved idle compute window. Require process-level verification that layers actually execute on both machines.
4. Only then explore pipeline concurrency, speculative verification, topology-aware scheduler and dynamic node admission. Treat Internet-scale arbitrary peers as a separate trust, attestation and privacy research problem.

Owner: HIVE experiment; base branch and exact measured receipts are to be included in its PR. No automatic merges, deployments, paid compute, or host changes.
