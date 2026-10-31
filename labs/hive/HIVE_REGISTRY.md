# HIVE volunteer registry and Qwythos 9B v2 preflight

**Status: executable LOCAL discovery/consent pilot; no public service, no remote GPUs, no Qwythos inference or GPU training.** No changes to Haven production services. Built to integrate with `labs/hive` via separate review.

## What we are actually trying to build

Sharding is not the same as request routing. The existing HIVE test transformer has four random-initialized layers and can distribute them across loopback workers; it **cannot** consume Qwythos safetensors or GGUF. The `hive.qwythos_plan` module only divides Qwythos's 32 *logical transformer blocks*. It intentionally reports `weights_loaded=false`, `runtime=NOT_IMPLEMENTED_FOR_QWYTHOS`, and no verified VRAM capacity. Hybrid recurrent Gated-DeltaNet states, KV cache, tokenizer, embeddings, tensor formats, MTP and the full image projector must be supported before declaring trained sharded inference.

Run from `labs/hive` (no new dependencies):

```bash
python -m hive.qwythos_plan --nodes 4 --quant Q4_K_M
python -m unittest discover -s tests -p 'test_registry.py' -v
```

Suggested *first actual model trial*: use a separately built/pinned llama.cpp binary with experimental RPC enabled, a Qwythos-9B-v2-Q4_K_M GGUF whose published SHA is checked, and two **authorized** physical nodes connected through separately owned authenticated SSH tunnels. Run local one-node identical model before attempting the two-host trial. Verify that `qwen35` hybrid attention/recurrent operations work correctly over the chosen RPC version; do not infer compatibility from the existence of an RPC switch. Restrict context initially (e.g. 4K), verify exact prompt/logits/output and per-host memory/GPU use. The RPC backend itself warns it is experimental and insecure for direct public network exposure. No commands in this proposal automatically download, install, start or route anything to paid compute.

## Why a public registry rather than Shodan

Hosts should **explicitly volunteer** their compute. Merely finding an exposed GPU API is not permission to use it. A future HIVE registry should index *offers* — verified capability, model-format compatibility, consent, minimum price (including zero), availability and required privacy/trust tier — rather than discover vulnerable machines. Public DHT records from Petals are a useful prior art; Shard's c0mpute rendezvous, libp2p and receipts are even closer to this goal. Do not duplicate a generic GPU-rental marketplace: integrate with provider supply (e.g. Vast.ai / Clore.ai) through user-owned accounts and opt-in terms only.

## Pilot semantics

`registry` provides **owner-issued one-use invitations**, `join` with affirmative consent and an explicit public visibility setting, worker-scoped bearer credentials for heartbeat and revocation, and a read-only sanitized node list. No IP, hostname, public key, endpoint, provider account, secret, user identity, or operator name can enter the registration schema. Worker information is self-declared and gets **no verified badge**. Heartbeat freshness is 90 seconds; heartbeat alone proves neither GPU capability nor permission to execute a task. No arbitrary code execution, job queue, task routing, resource leasing, payment rail, or actual work verification exists.

The server deliberately accepts **loopback only**. To run a temporary registry for private owner evaluation:

```bash
python -m registry init --secret-file .hive-registry-admin
python -m registry serve --secret-file .hive-registry-admin --port 9191
```

Owner token stays in the private 0600 file (not printed). Access is via a separately approved SSH tunnel. The registry is **in-memory**, with no durable persistence or worker advertisements across restarts; this is appropriate for a local prototype only. The owner must opt in and issue invites via authenticated `POST /v1/invites` to enable registration. A would-be public-facing gateway needs TLS, explicit rate limits, abuse controls, peer ID proof, signed expiring adverts, persistence, crash consistency, real GPU challenges, consent/revocation UX, protection against Sybils, traffic accounting, and independently reviewed deployment before it could leave loopback. Do not expose this pilot to the internet.

API (JSON): `POST /v1/invites` with `{'ttl_seconds':600}` and owner bearer; `POST /v1/join` with `{'invite':..., 'declaration':{'consent':true, 'public':true, 'model':'empero-ai/Qwythos-9B-v2','backend':'cuda','vram_gib':8,'roles':['layer_inference']}}`; `POST /v1/nodes/{id}/heartbeat` with `{'available':true}` and node bearer; `POST /v1/nodes/{id}/revoke` with `{}` and node bearer; `GET /v1/nodes` public metadata. Credentials are returned once. `public=false` nodes are never listed. The reported capability is **unverified**.

## Legitimate supply sources (October 2026)

- Petals: public community layer-hosting DHT and https://health.petals.dev/api/v1/state ; model architecture must be implemented; Qwythos is NOT automatically supported.
- Shard / c0mpute: layer-sharding and prospective per-node payouts, with ongoing network/pay integration; custom Qwythos engine and hybrid state compatibility not established.
- AI Horde: free volunteer *whole-request inference*, not arbitrary layer execution; anonymous key lowest priority.
- AIs@home: free capped volunteer Qwen3.8 27B inference, not a arbitrary layer rental pool, explicitly nonconfidential.
- Vast.ai, Clore.ai, SaladCloud: real marketplace/rental capacity, not free indefinite GPUs; opt-in providers can be privately integrated. Salad contributor rewards are not a transferable free SaladCloud balance for the renter.
- Prime Intellect INTELLECT-2: compelling precedent for **asynchronous distributed RL**; not equivalent to all-reduce-style synchronous fine-tuning across high-latency residential machines.

## Success criteria for next PRs

1. Verify model hashes, architectures and exact Qwythos RPC operation support; record a one-host baseline with real weights.
2. Obtain independent owner-authorized compute hosts with pinned versions and independently verifiable resource receipts.
3. Execute a two-machine cross-host sharded forward with per-node GPU compute proof, correctness and throughput; compare against the one-host baseline. No simulated GPU runs accepted.
4. Add genuine challenge-based worker qualification, outbound-only job transport and worker admission; keep privacy-aware choice to retain sensitive inputs locally.
5. Separately prototype asynchronous rollout generation/verification/training with a fixed reward oracle and a reproducible held-out eval; compute the true GPU-hours, electricity and dollars per verified improvement.

References: https://github.com/ggml-org/llama.cpp/tree/master/tools/rpc ; https://github.com/bigscience-workshop/petals ; https://github.com/leyten/shard ; https://github.com/learning-at-home/hivemind ; https://www.primeintellect.ai/blog/intellect-2-release .
