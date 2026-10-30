"""LoRA / QLoRA SFT of a small open-weight student on the secpatch training split.

The loss covers only the assistant answer; the prompt is rendered exactly as
at inference (chat template, add_generation_prompt, thinking off). Nothing is
loaded without --execute. `--device cpu` is a pipeline/config check, not a
training run: it refuses more than --cpu-max-steps steps.

Every run writes `receipt.json` next to the adapter: data digest, row counts by
task, base model revision, hyperparameters, loss log, wall time and peak memory.
Register and promote adapters with registry.py; nothing here promotes.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import pathlib
import platform
import resource
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from train_sft import LocalDataset, collator  # noqa: E402  (shared with the R02 pilot)

TARGET_MODULES = ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']


def lora_targets(model_id: str, choice: str = 'auto'):
    if choice != 'auto':
        return choice if choice == 'all-linear' else choice.split(',')
    return TARGET_MODULES if 'qwen' in model_id.lower() else 'all-linear'


def load_rows(path: pathlib.Path, tasks: set | None) -> list[dict]:
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get('split') != 'train':
            raise ValueError(f"Row {row.get('id')} is from split {row.get('split')!r}; only training rows are accepted.")
        if row['messages'][-1]['role'] != 'assistant':
            raise ValueError('Every row must end with its assistant target.')
        if tasks is None or row['task'] in tasks:
            rows.append(row)
    if not rows:
        raise ValueError('No training rows selected.')
    return rows


def render(row: dict, tokenizer) -> tuple[str, str]:
    msgs = row['messages']
    prefix = tokenizer.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    full = tokenizer.apply_chat_template(msgs, tokenize=False, enable_thinking=False)
    if not full.startswith(prefix):
        raise ValueError('Chat template prefix mismatch; refusing to guess the target span.')
    return prefix, full[len(prefix):].rstrip('\n')


def encode(rows: list[dict], tokenizer, max_length: int) -> tuple[list[dict], int]:
    encoded, skipped = [], 0
    for row in rows:
        prefix, target = render(row, tokenizer)
        p = tokenizer(prefix, add_special_tokens=False)['input_ids']
        t = tokenizer(target, add_special_tokens=False)['input_ids']
        if len(p) + len(t) > max_length:
            skipped += 1  # counted in the receipt; a target is never truncated
            continue
        encoded.append({'input_ids': p + t, 'attention_mask': [1] * (len(p) + len(t)), 'labels': [-100] * len(p) + t})
    return encoded, skipped


def target_only_loss(model, inputs):
    """Next-token loss computed from logits at answer positions only.

    The default causal-LM loss materializes vocab-sized logits for every position (Qwen3: 151,936 per token),
    including the prompt that is never learned from. On an 8 GiB card shared with another model, that is what
    ran out of memory. Hidden states for prompt positions are dropped before the LM head, so memory scales
    with the answer length. The value equals the default loss (mean over answer tokens)."""
    import torch
    base = model.get_base_model() if hasattr(model, 'get_base_model') else model
    labels = inputs['labels']
    hidden = base.model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask']).last_hidden_state
    target = labels[:, 1:]
    keep = target != -100
    logits = base.lm_head(hidden[:, :-1][keep]).float()
    return torch.nn.functional.cross_entropy(logits, target[keep])


def peak_rss_gib() -> float:
    scale = 1 if platform.system() == 'Darwin' else 1024
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * scale / 2**30, 3)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', type=pathlib.Path, required=True)
    ap.add_argument('--tasks', help='Comma-separated task filter (default: all).')
    ap.add_argument('--model', default='Qwen/Qwen3-0.6B')
    ap.add_argument('--revision', required=True, help='Exact base model revision; recorded in the receipt.')
    ap.add_argument('--output', type=pathlib.Path, required=True)
    ap.add_argument('--device', choices=('cuda', 'cpu'), default='cuda')
    ap.add_argument('--qlora', action='store_true', help='4-bit base weights (CUDA + bitsandbytes), for 1.5B-4B students.')
    ap.add_argument('--max-length', type=int, default=2048)
    ap.add_argument('--epochs', type=float, default=2.0)
    ap.add_argument('--max-steps', type=int)
    ap.add_argument('--batch', type=int, default=8, help='Effective batch via gradient accumulation.')
    ap.add_argument('--learning-rate', type=float, default=1e-4)
    ap.add_argument('--rank', type=int, default=16)
    ap.add_argument('--target-modules', default='auto',
                    help="'auto': Qwen projection names for Qwen students, every linear layer otherwise (e.g. Liquid LFM)")
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--save-steps', type=int, default=50, help='Checkpoint interval (resumable).')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--cpu-max-steps', type=int, default=3)
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args(argv)
    tasks = set(args.tasks.split(',')) if args.tasks else None
    rows = load_rows(args.data, tasks)
    data_sha = hashlib.sha256(args.data.read_bytes()).hexdigest()
    steps = args.max_steps or math.ceil(len(rows) * args.epochs / args.batch)
    plan = {'recipe': 'completion_masked_lora_sft_target_logits' + ('_qlora4' if args.qlora else ''), 'rows': len(rows),
            'by_task': collections.Counter(r['task'] for r in rows), 'steps': steps, 'effective_batch': args.batch,
            'device': args.device, 'data_sha256': data_sha, 'execute': args.execute}
    print(json.dumps(plan))
    if not args.execute:
        print('DRY RUN: no model loaded and no training performed.')
        return plan
    if args.device == 'cpu' and steps > args.cpu_max_steps:
        raise SystemExit(f'CPU mode is a pipeline check capped at {args.cpu_max_steps} steps; use a GPU window for training.')
    if args.qlora and args.device != 'cuda':
        raise SystemExit('QLoRA needs CUDA.')
    os.umask(0o077)
    if args.output.exists() and any(args.output.iterdir()) and not args.resume:
        raise SystemExit('Output directory not empty; refusing to overwrite an adapter (use --resume to continue).')
    import torch
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise SystemExit('CUDA requested but unavailable; nothing was trained.')
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, set_seed
    set_seed(args.seed)
    opts = {'revision': args.revision, 'local_files_only': True, 'trust_remote_code': False}
    tok = AutoTokenizer.from_pretrained(args.model, **opts)
    encoded, skipped = encode(rows, tok, args.max_length)
    load = {'use_safetensors': True, **opts}
    if args.qlora:
        from transformers import BitsAndBytesConfig
        load['quantization_config'] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                                         bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
        load['device_map'] = {'': 0}
    elif args.device == 'cpu':
        load['torch_dtype'] = torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model, **load)
    model.config.use_cache = False
    if args.qlora:
        model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()
    model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, bias='none',
                                             task_type='CAUSAL_LM', target_modules=lora_targets(args.model, args.target_modules)))
    model.enable_input_require_grads()
    cfg = TrainingArguments(
        output_dir=str(args.output / 'checkpoints'), max_steps=steps, per_device_train_batch_size=1,
        gradient_accumulation_steps=args.batch, learning_rate=args.learning_rate, lr_scheduler_type='cosine',
        warmup_ratio=0.05, fp16=args.device == 'cuda', bf16=False, use_cpu=args.device == 'cpu',
        logging_steps=1 if args.device == 'cpu' else 10, save_strategy='steps', save_steps=args.save_steps,
        save_total_limit=2, report_to=[], seed=args.seed, data_seed=args.seed, dataloader_num_workers=0,
        remove_unused_columns=False)
    class TargetOnlyTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            return target_only_loss(model, inputs)

    trainer = TargetOnlyTrainer(model=model, args=cfg, train_dataset=LocalDataset(encoded), data_collator=collator(tok))
    trainer.model_accepts_loss_kwargs = False  # per-micro-batch mean; Trainer divides by accumulation steps
    if args.device == 'cuda':
        torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    resume = args.resume and any((args.output / 'checkpoints').glob('checkpoint-*'))
    result = trainer.train(resume_from_checkpoint=True if resume else None)
    elapsed = time.monotonic() - started
    model.save_pretrained(str(args.output / 'adapter'))
    receipt = {**plan, 'classification': 'CPU_PIPELINE_CHECK' if args.device == 'cpu' else 'GPU_TRAINING_RUN',
               'base_model': args.model, 'base_revision': args.revision, 'rows_encoded': len(encoded),
               'rows_skipped_too_long': skipped, 'max_length': args.max_length, 'learning_rate': args.learning_rate,
               'rank': args.rank, 'seed': args.seed, 'train_loss': result.training_loss,
               'loss_log': [x for x in trainer.state.log_history if 'loss' in x],
               'wall_seconds': round(elapsed, 1), 'peak_rss_gib': peak_rss_gib(),
               'peak_cuda_gib': round(torch.cuda.max_memory_allocated() / 2**30, 3) if args.device == 'cuda' else None,
               'versions': {'torch': torch.__version__, 'python': platform.python_version()},
               'finished_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=1, default=dict) + '\n')
    print(json.dumps({k: receipt[k] for k in ('classification', 'rows_encoded', 'train_loss', 'wall_seconds', 'peak_rss_gib')}))
    return receipt


if __name__ == '__main__':
    main()
