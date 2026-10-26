"""Opt-in local LoRA SFT on verified multi-turn tool trajectories.

Each row's last message is the assistant target. The prefix is rendered with
add_generation_prompt=True, exactly as the student sees it at inference, and
only the target tokens are labeled. No model is loaded without --execute.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import world  # noqa: E402
from agent import to_hf  # noqa: E402
from train_sft import LocalDataset, collator  # noqa: E402


def load_rows(path):
    rows = [json.loads(x) for x in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    if not rows:
        raise ValueError("No training rows.")
    for row in rows:
        if not row["episode"].startswith("train-") or row["messages"][-1]["role"] != "assistant":
            raise ValueError("Only training-split assistant targets are accepted.")
    return rows


def render(row, tokenizer):
    """Return (prefix_text, target_text) for one assistant turn."""
    messages = to_hf(row["messages"])
    prefix = tokenizer.apply_chat_template(messages[:-1], tools=world.TOOL_SCHEMAS, tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)
    full = tokenizer.apply_chat_template(messages, tools=world.TOOL_SCHEMAS, tokenize=False,
                                         enable_thinking=False)
    if not full.startswith(prefix):
        raise ValueError("Chat template prefix mismatch; refusing to guess the target span.")
    target = full[len(prefix):]
    if target.endswith("\n"):
        target = target[:-1]
    if not target.endswith("<|im_end|>"):
        raise ValueError("Target does not end at the assistant turn boundary.")
    return prefix, target


def encode(rows, tokenizer, max_length):
    encoded = []
    for row in rows:
        prefix, target = render(row, tokenizer)
        p = tokenizer(prefix, add_special_tokens=False)["input_ids"]
        t = tokenizer(target, add_special_tokens=False)["input_ids"]
        if len(p) + len(t) > max_length:
            raise ValueError("Example too long; do not silently truncate a target.")
        encoded.append({"input_ids": p + t, "attention_mask": [1] * (len(p) + len(t)),
                        "labels": [-100] * len(p) + t})
    return encoded


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=pathlib.Path, required=True)
    ap.add_argument("--model", default="Qwen/Qwen3-0.6B")
    ap.add_argument("--revision", required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--max-length", type=int, default=2048)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--max-steps", type=int, help="Override epochs with an exact step count.")
    ap.add_argument("--learning-rate", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args(argv)
    rows = load_rows(args.data)
    batch = 8
    steps = args.max_steps or math.ceil(len(rows) * args.epochs / batch)
    print(json.dumps({"recipe": "per_turn_completion_masked_lora_sft", "rows": len(rows),
                      "steps": steps, "effective_batch": batch, "execute": args.execute}))
    if not args.execute:
        print("DRY RUN: no model loaded and no training performed.")
        return
    os.umask(0o077)
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError("Output directory not empty; refusing to overwrite an adapter.")
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required. This recipe is not a CPU fallback.")
    from peft import LoraConfig, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoTokenizer, Trainer,
                              TrainingArguments, set_seed)
    set_seed(args.seed)
    options = {"revision": args.revision, "local_files_only": True, "trust_remote_code": False}
    tok = AutoTokenizer.from_pretrained(args.model, **options)
    encoded = encode(rows, tok, args.max_length)
    model = AutoModelForCausalLM.from_pretrained(args.model, use_safetensors=True, **options)
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model = get_peft_model(model, LoraConfig(
        r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    model.enable_input_require_grads()
    config = TrainingArguments(
        output_dir=str(args.output), max_steps=steps, per_device_train_batch_size=1,
        gradient_accumulation_steps=batch, learning_rate=args.learning_rate,
        lr_scheduler_type="cosine", warmup_ratio=0.05, fp16=True, bf16=False,
        logging_steps=10, save_strategy="no", report_to=[], seed=args.seed, data_seed=args.seed,
        dataloader_num_workers=0, remove_unused_columns=False)
    trainer = Trainer(model=model, args=config, train_dataset=LocalDataset(encoded),
                      data_collator=collator(tok))
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    result = trainer.train()
    torch.cuda.synchronize()
    elapsed = time.monotonic() - started
    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(args.output), safe_serialization=True)
    receipt = {
        "schema": "haven-tool-sft-train-1", "status": "COMPLETED",
        "recipe": "per_turn_completion_masked_lora_sft", "model": args.model,
        "revision": args.revision, "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "rows": len(rows), "target_tokens": sum(sum(x != -100 for x in e["labels"]) for e in encoded),
        "max_steps": steps, "completed_steps": trainer.state.global_step, "seed": args.seed,
        "learning_rate": args.learning_rate, "lora_rank": args.rank, "lora_targets": "all_linear",
        "precision": "fp32_base_fp16_autocast", "elapsed_seconds": round(elapsed, 3),
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
        "metrics": result.metrics, "log_history": trainer.state.log_history,
        "promotion": "NOT_EVALUATED_NOT_PROMOTED",
    }
    (args.output / "training-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "log_history"}, indent=2))


if __name__ == "__main__":
    main()
