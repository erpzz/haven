# Trusted Slink Zone — offline model-sharding feasibility probe

**Status:** synthetic planning utility only. It performs **no inference, network scanning, SSH, installation, device enrollment, or agent propagation**. It does not modify Slink or the Mac's running workspaces.

This additive TSZ module helps reason about the first pipeline-parallel experiment without assuming that network sharding beats the current Slink-only MoE/llama.cpp baseline.

## Inputs

Create a private JSON file containing a model's approximate aggregate accelerator weight/KV footprint and a set of **control-plane-verified** node capabilities. Example using entirely fictional devices:

```json
{
  "model": {
    "weights_mib": 4000,
    "kv_mib": 400,
    "layers": 20,
    "boundary_activation_kib": 256
  },
  "nodes": [
    {"id":"node-a","enrolled":true,"online":true,"inference_grant":true,
     "accelerator_free_mib":2600,"fabric_mbps":1000,"backend":"cuda"},
    {"id":"node-b","enrolled":true,"online":true,"inference_grant":true,
     "accelerator_free_mib":2600,"fabric_mbps":1000,"backend":"metal"},
    {"id":"unowned-candidate","enrolled":false,"online":true,"inference_grant":false,
     "accelerator_free_mib":9000,"fabric_mbps":1000,"backend":"unknown"}
  ]
}
```

```bash
python3 labs/tsz/placement.py /path/to/private-manifest.json
python3 -m unittest discover -s labs/tsz/tests -v
```

The planner prefers a single device when its modeled free accelerator memory fits the model; otherwise, it estimates a contiguous pipeline split over eligible nodes. The output reports assignments, exclusions, and a lower bound for **one-way activation transfer bytes / declared bandwidth**.

**This is not authorization.** The boolean flags in a manifest are merely inputs, not cryptographic verification; real execution must consume grants and resource measurements from a trusted Haven control plane. Keep real host inventories and credentials out of Git.

## What has not been implemented

- No physical model splitting or real inference speed results.
- No verification that the model's actual layer sizes, backend version, shared tensors or KV-cache layout permit the proposed partition.
- No actual network bandwidth or latency measurements; the planner's estimate excludes protocol, synchronization, return traffic, computation and memory fragmentation.
- No tensor parallelism, MoE expert sharding, RAM spill, model training or network discovery.

## Next live acceptance

1. Verify the existing Haven browser/Computer auth and active workload owners.
2. Collect resource/transport capabilities from **already enrolled** Slink and Mac workers, without storing private inventory in Git.
3. Benchmark *the same small GGUF* on one device, then an explicitly authorized two-node test via a suitable distributed runtime. Treat [llama.cpp RPC](https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md) as experimental and never expose it as an unauthenticated LAN service.
4. Compare real tokens/sec, first output, VRAM/RAM, network bytes, cold-load times and behavior under node loss. If two-node sharding is slower or less reliable, prefer independent task workers and RAM-resident MoE experts.
5. Only then integrate a runtime-backed TSZ node/shard dashboard. The existing Open WebUI Computer is the workspace, not itself a distributed model scheduler.

Research anchor: [Anthropic, Oct 12, 2026](https://www.anthropic.com/research/self-replicating-ai), which demonstrated pipeline-model splitting across constrained IoT hardware, and separately investigated self-replication. TSZ deliberately implements *neither* autonomous spreading nor unauthorized device access.
