"""CPU lane for the tool-SFT recipe: exact shared-prefix LoRA training and cached-prefix evaluation.

train.py and run.py's HF path require CUDA and stay unchanged. This lane runs the same
per-turn completion-masked recipe (LoRA r16/alpha 32/dropout 0.05 on all projections,
AdamW lr 1e-4, cosine with 5% warmup, effective batch 8, 2 epochs, grad-norm clip 1.0,
token-weighted loss over each 8-row step as Trainer does, seed 42) on a CPU.

Every training row begins with the same system prompt and tool block. Within one optimizer
step the adapter weights are fixed, so the shared tokens are run once and each row's suffix
attends to that cache; the gradient of all rows flows back through the one prefix graph. The
loss and gradients equal the per-row computation up to float rounding (checked in
tests/test_cpu_lane.py), except that one LoRA dropout mask is shared by the prefix positions
of a step. Precision is fp32 throughout: on the measured 4-core AMX host, fp32 training was
faster (22 s vs 25 s per step) and smaller (8.6 vs 10.5 GB) than bf16 autocast, and fp32 greedy
decoding 2.5x faster. `--bf16` opts into autocast. Evaluation reuses run.py's loop, verifier
and receipt format with a greedy HF backend that caches the same shared prefix.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import pathlib
import random
import resource
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import agent  # noqa: E402
import run  # noqa: E402
import train as gpu_train  # noqa: E402  (load_rows, render, encode: identical targets)
import world  # noqa: E402

LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def common_prefix(sequences):
    """Length of the longest token prefix shared by every sequence."""
    first, n = sequences[0], min(len(s) for s in sequences)
    for seq in sequences[1:]:
        k = 0
        while k < n and seq[k] == first[k]:
            k += 1
        n = k
    return n


def _cache_from(kv):
    from transformers import DynamicCache
    cache = DynamicCache()
    for layer, (k, v) in enumerate(kv):
        cache.update(k, v, layer)  # update concatenates into new tensors; kv stays intact
    return cache


def _kv(cache):
    if hasattr(cache, "layers"):
        return [(layer.keys, layer.values) for layer in cache.layers]
    return list(zip(cache.key_cache, cache.value_cache))


def step_loss(model, prefix_ids, rows, autocast):
    """Accumulate the token-weighted loss gradient of `rows`, which all start with `prefix_ids`.

    The prefix runs once. Each row's suffix backpropagates into detached copies of the prefix
    keys/values, one row at a time; their summed gradient then flows through the prefix graph
    in a single backward pass. Logits are computed only where a target token is predicted.
    Returns (loss value, target tokens).
    """
    import torch
    from transformers import DynamicCache
    base = model.get_base_model() if hasattr(model, "get_base_model") else model
    decoder, head = base.model, base.lm_head
    n = len(prefix_ids)
    for row in rows:
        if row["input_ids"][:n] != prefix_ids or any(x != -100 for x in row["labels"][:n + 1]):
            raise ValueError("Row does not share the prefix, or a target lies inside it.")
    tokens = sum(sum(x != -100 for x in row["labels"][n + 1:]) for row in rows)
    amp = torch.autocast("cpu", dtype=torch.bfloat16, enabled=autocast)
    with amp:
        cache = DynamicCache()
        decoder(input_ids=torch.tensor([prefix_ids]), past_key_values=cache, use_cache=True)
    kv = [t for pair in _kv(cache) for t in pair]
    leaves = [t.detach().requires_grad_() for t in kv]
    total = 0.0
    for row in rows:
        labels = row["labels"][n:]
        where = [j for j in range(len(labels) - 1) if labels[j + 1] != -100]
        with amp:
            hidden = decoder(input_ids=torch.tensor([row["input_ids"][n:]]),
                             past_key_values=_cache_from(list(zip(leaves[0::2], leaves[1::2]))),
                             use_cache=True).last_hidden_state
            logits = head(hidden[0, where]).float()
        loss = torch.nn.functional.cross_entropy(
            logits, torch.tensor([labels[j + 1] for j in where]), reduction="sum") / tokens
        loss.backward()
        total += float(loss)
    torch.autograd.backward(kv, [leaf.grad for leaf in leaves])
    return total, tokens


def build_model(args, trainable):
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(args.threads)
    options = {"revision": args.revision, "local_files_only": True, "trust_remote_code": False}
    tok = AutoTokenizer.from_pretrained(args.model, **options)
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.float32, use_safetensors=True,
                                                 **options)
    if trainable:
        model = get_peft_model(model, LoraConfig(
            r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, bias="none",
            task_type="CAUSAL_LM", target_modules=LORA_TARGETS))
    elif getattr(args, "adapter", None):
        model = PeftModel.from_pretrained(model, str(args.adapter), is_trainable=False)
    return tok, model


def cmd_train(args):
    rows = gpu_train.load_rows(args.data)
    batch = 8
    steps = args.max_steps or math.ceil(len(rows) * args.epochs / batch)
    print(json.dumps({"recipe": "per_turn_completion_masked_lora_sft", "lane": "cpu_shared_prefix",
                      "rows": len(rows), "steps": steps, "effective_batch": batch,
                      "execute": args.execute}), flush=True)
    if not args.execute:
        print("DRY RUN: no model loaded and no training performed.")
        return
    os.umask(0o077)
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError("Output directory not empty; refusing to overwrite an adapter.")
    import torch
    from transformers import get_cosine_schedule_with_warmup, set_seed
    set_seed(args.seed)
    tok, model = build_model(args, trainable=True)
    encoded = gpu_train.encode(rows, tok, args.max_length)
    n = common_prefix([e["input_ids"] for e in encoded])
    prefix = encoded[0]["input_ids"][:n]
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=args.learning_rate, weight_decay=0.0)
    scheduler = get_cosine_schedule_with_warmup(optimizer, math.ceil(0.05 * steps), steps)
    order, rng = [], random.Random(args.seed)
    while len(order) < steps * batch:  # reshuffle every epoch, as a seeded sampler does
        epoch = list(range(len(encoded)))
        rng.shuffle(epoch)
        order += epoch
    log, started = [], time.monotonic()
    args.output.mkdir(parents=True, exist_ok=True)
    for step in range(steps):
        chunk = [encoded[i] for i in order[step * batch:(step + 1) * batch]]
        loss, tokens = step_loss(model, prefix, chunk, autocast=args.bf16)
        grad_norm = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        entry = {"step": step + 1, "loss": round(loss, 5), "grad_norm": round(grad_norm, 4),
                 "learning_rate": scheduler.get_last_lr()[0], "target_tokens": tokens,
                 "elapsed": round(time.monotonic() - started, 1)}
        log.append(entry)
        if (step + 1) % 10 == 0 or step == 0:
            print(json.dumps(entry), flush=True)
    elapsed = time.monotonic() - started
    model.save_pretrained(str(args.output), safe_serialization=True)
    receipt = {
        "schema": "haven-tool-sft-train-1", "status": "COMPLETED",
        "recipe": "per_turn_completion_masked_lora_sft", "lane": "cpu_shared_prefix",
        "model": args.model, "revision": args.revision,
        "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(), "rows": len(rows),
        "target_tokens": sum(sum(x != -100 for x in e["labels"]) for e in encoded),
        "shared_prefix_tokens": n, "max_steps": steps, "completed_steps": steps, "seed": args.seed,
        "learning_rate": args.learning_rate, "lora_rank": args.rank, "lora_targets": "all_linear",
        "precision": "fp32_base_bf16_autocast_cpu" if args.bf16 else "fp32_cpu",
        "threads": args.threads, "elapsed_seconds": round(elapsed, 3),
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "trainable_parameters": sum(p.numel() for p in params),
        "final_loss": log[-1]["loss"], "log_history": log,
        "promotion": "NOT_EVALUATED_NOT_PROMOTED",
    }
    (args.output / "training-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "log_history"}, indent=2))


class CachedPrefixBackend(agent.HFBackend):
    """agent.HFBackend with the shared system/tool prefix computed once and reused."""

    def __init__(self, model, tokenizer, max_new_tokens=256, autocast=True):
        super().__init__(model, tokenizer, max_new_tokens)
        import torch
        from transformers import DynamicCache
        self.autocast = autocast
        probe = [[{"role": "system", "content": agent.SYSTEM}, {"role": "user", "content": u}]
                 for u in ("Authenticated principal: a\n\nx", "Authenticated principal: b\n\ny")]
        ids = [tokenizer(tokenizer.apply_chat_template(m, tools=world.TOOL_SCHEMAS, tokenize=False,
                                                       add_generation_prompt=True,
                                                       enable_thinking=False),
                         add_special_tokens=False)["input_ids"] for m in probe]
        self.prefix = ids[0][:common_prefix(ids)]
        self.cache = DynamicCache()
        with torch.inference_mode(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=autocast):
            model(input_ids=torch.tensor([self.prefix]), past_key_values=self.cache, use_cache=True)

    def step(self, messages, tools):
        import torch
        text = self.tok.apply_chat_template(agent.to_hf(messages), tools=tools, tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)
        ids = self.tok(text, add_special_tokens=False, return_tensors="pt")
        n = len(self.prefix)
        use = tools is world.TOOL_SCHEMAS and ids["input_ids"][0, :n].tolist() == self.prefix
        extra = {"past_key_values": copy.deepcopy(self.cache)} if use else {}
        with torch.inference_mode(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=self.autocast):
            out = self.model.generate(**ids, do_sample=False, max_new_tokens=self.max_new_tokens,
                                      temperature=None, top_p=None, top_k=None,
                                      eos_token_id=self.stop, pad_token_id=self.stop[-1], **extra)
        new = out[0, ids["input_ids"].shape[1]:]
        raw = self.tok.decode(new, skip_special_tokens=False)
        for marker in ("<|im_end|>", "<|endoftext|>"):
            raw = raw.split(marker)[0]
        content, calls, error = agent.parse_tool_text(raw)
        return {"content": content, "tool_calls": calls, "format_error": error,
                "usage": {"prompt_tokens": int(ids["input_ids"].shape[1]),
                          "completion_tokens": int(new.shape[0]), "prefix_cached": use}}


def cmd_eval(args):
    def make_backend(_):
        tok, model = build_model(args, trainable=False)
        model.eval()
        return CachedPrefixBackend(model, tok, args.max_tokens, autocast=args.bf16)
    run.make_backend = make_backend  # run.py's loop, verifier and receipt; only the backend differs
    args.backend = "hf-cpu-bf16-autocast" if args.bf16 else "hf-cpu-fp32"
    run.cmd_eval(args)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("train", "eval"):
        p = sub.add_parser(name)
        p.add_argument("--model", default="Qwen/Qwen3-0.6B")
        p.add_argument("--revision", required=True)
        p.add_argument("--threads", type=int, default=os.cpu_count() or 1)
        p.add_argument("--bf16", action="store_true", help="bf16 autocast; slower on the measured host.")
    p = sub.choices["train"]
    p.add_argument("--data", type=pathlib.Path, required=True)
    p.add_argument("--output", type=pathlib.Path, required=True)
    p.add_argument("--max-length", type=int, default=2048)
    p.add_argument("--epochs", type=float, default=2.0)
    p.add_argument("--max-steps", type=int)
    p.add_argument("--learning-rate", type=float, default=1e-4)
    p.add_argument("--rank", type=int, default=16)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--execute", action="store_true")
    p = sub.choices["eval"]
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--adapter", type=pathlib.Path)
    p.add_argument("--sets", default="heldout,legacy")
    p.add_argument("--limit", type=int)
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--deadline-minutes", type=float)
    args = parser.parse_args(argv)
    {"train": cmd_train, "eval": cmd_eval}[args.command](args)


if __name__ == "__main__":
    main()
