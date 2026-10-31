"""Qwythos-9B-v2 shard layout planner; planning ONLY (no model download/execute)."""
from __future__ import annotations
import argparse
import json

MODEL = 'empero-ai/Qwythos-9B-v2'
LAYERS = 32
# Published GGUF weight file sizes. NOT per-layer weight sizes or VRAM admission.
QUANTS = {'Q4_K_M': 5.34, 'Q5_K_M': 6.08, 'Q6_K': 6.95, 'Q8_0': 8.87, 'BF16': 16.69}

def plan(nodes: int, quant: str = 'Q4_K_M') -> dict:
    if type(nodes) is not int or not (1 <= nodes <= 32):
        raise ValueError('Expected 1-32 authorized workers')
    if quant not in QUANTS:
        raise ValueError('Unsupported published trunk GGUF quantization')
    whole, rem = divmod(LAYERS, nodes)
    start = 0
    shards = []
    for i in range(nodes):
        stop = start + whole + (i < rem)
        shards.append({'worker': i + 1, 'layer_range': [start, stop], 'layers': stop - start})
        start = stop
    return {'model': MODEL, 'weights_repo': MODEL + '-GGUF', 'trunk_layers': LAYERS,
            'format': quant, 'published_total_file_gib': QUANTS[quant],
            'shards': shards, 'runtime': 'NOT_IMPLEMENTED_FOR_QWYTHOS',
            'weights_loaded': False, 'cross_host_tested': False, 'gpu_admission_checked': False,
            'notes': ['Hybrid Gated-DeltaNet recurrent state and attention KV must remain consistent per layer.',
                      'Layer weights are NOT uniform; logical partitions are not actual memory balancing.',
                      'Embedding/output head, tokenizer, caches, MTP and vision projector are not assigned.',
                      'HIVE cannot load this GGUF; use a separate approved llama.cpp RPC experiment or port a model-native sharded runtime.']}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--nodes', type=int, default=2)
    ap.add_argument('--quant', choices=sorted(QUANTS), default='Q4_K_M')
    a = ap.parse_args()
    print(json.dumps(plan(a.nodes, a.quant), indent=2))

if __name__ == '__main__': main()
