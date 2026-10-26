"""Run the existing frozen probes on a local HF base or PEFT adapter.

Default is a metadata-only dry run. Explicit execution requires CUDA and never
uses a remote inference service. Raw answers and receipts belong outside Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from evaluate import DEFAULT_PROBES, load_probes, score, summarize, write_results

SYSTEM = ("You are taking a synthetic diagnostic. Reply with exactly the requested "
          "token, nothing else. If a catalog code was not provided or learned, "
          "reply UNKNOWN; never guess.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='Qwen/Qwen3-0.6B')
    parser.add_argument('--revision', required=True)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--probes', type=Path, default=DEFAULT_PROBES)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-new-tokens', type=int, default=80)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--allow-download', action='store_true')
    args = parser.parse_args(argv)
    probes = load_probes(args.probes)
    if not 1 <= args.max_new_tokens <= 256:
        parser.error('Use a finite generation limit between 1 and 256 tokens.')
    if args.output.exists() or args.output.with_suffix('.summary.json').exists():
        parser.error('Refusing to overwrite an evaluation receipt.')
    if args.adapter and not (args.adapter / 'adapter_config.json').is_file():
        parser.error('The adapter directory has no adapter_config.json.')
    print(json.dumps({'model': args.model, 'revision': args.revision,
                      'adapter': bool(args.adapter), 'probes': len(probes),
                      'execute': args.execute, 'download': args.allow_download}))
    if not args.execute:
        print('DRY RUN: no model loaded, no downloads, no inference.')
        return
    os.umask(0o077)
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    if not torch.cuda.is_available():
        raise RuntimeError('A CUDA GPU is required; no CPU fallback.')
    set_seed(42)
    options = {'revision': args.revision, 'trust_remote_code': False,
               'local_files_only': not args.allow_download}
    tokenizer = AutoTokenizer.from_pretrained(args.model, **options)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.float16, use_safetensors=True, **options)
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(args.adapter), is_trainable=False)
    model.to('cuda').eval()
    torch.cuda.reset_peak_memory_stats()
    results = []
    for probe in probes:
        messages = [{'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': probe['prompt']}]
        inputs = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            enable_thinking=False, return_tensors='pt', return_dict=True).to('cuda')
        torch.cuda.synchronize()
        started = time.monotonic()
        with torch.inference_mode():
            output = model.generate(
                **inputs, do_sample=False, max_new_tokens=args.max_new_tokens,
                max_time=30, temperature=None, top_p=None, top_k=None,
                pad_token_id=tokenizer.eos_token_id)
        torch.cuda.synchronize()
        answer = tokenizer.decode(output[0, inputs['input_ids'].shape[1]:],
                                  skip_special_tokens=True).strip()
        result = {'id': probe['id'], 'answer': answer, 'ok_transport': True,
                  'elapsed_seconds': round(time.monotonic() - started, 3)}
        results.append(result)
        print(probe['id'], 'PASS' if score(probe, answer) else 'FAIL', flush=True)
    report = {
        'schema': 'haven-frozen-hf-eval-1', 'model': args.model,
        'revision': args.revision, 'adapter': bool(args.adapter),
        'probes_sha256': hashlib.sha256(args.probes.read_bytes()).hexdigest(),
        'precision': 'fp16', 'enable_thinking': False, 'seed': 42,
        'max_new_tokens': args.max_new_tokens,
        'torch': torch.__version__, 'transformers': transformers.__version__,
        'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
        'peak_reserved_bytes': torch.cuda.max_memory_reserved(),
        'groups': summarize(probes, results),
        'qualification': 'SYNTHETIC_DIAGNOSTIC_ONLY_NOT_PROMOTED',
    }
    write_results(args.output, results)
    args.output.with_suffix('.summary.json').write_text(
        json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
