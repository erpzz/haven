"""SPEC-2 bounded self-improvement: rejection-sampling fine-tuning against recorded ground truth.

One round = sample -> verify -> train -> gate. The verifier is spec_bench.parse_answer against the frozen
answer key; nothing the model writes can change it. The same path distils a large model into a small one:
sample with --model LARGE, then train with --model SMALL on the kept traces.

  sample   N answers per training item from a model (+adapter), via vLLM when present, else transformers
  filter   keep verified answers; one per item, the shortest correct (speed with accuracy)
  train    completion-masked LoRA/QLoRA SFT on kept traces (refuses eval-set rows)
  dev      accuracy on a held-back slice of the training pool (never the frozen eval sets)
  loop     rounds of sample/filter/train/dev, each phase in a fresh process; a round is kept only if dev accuracy improves by >= --min-gain

The frozen eval sets are scored separately, once per kept round, by serving the adapter and running
spec_bench.py. Private outputs only; receipts carry hashes, counts and settings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import random
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spec_bench as sb  # noqa: E402

EVAL_BENCHES = {name for name, s in sb.SOURCES.items() if s[1] == "eval"}


def messages_for(row):
    return [{"role": "system", "content": sb.SYSTEM}, {"role": "user", "content": sb.prompt(row)}]


def load_pool(path, limit=None, seed=0, skip=0):
    rows = sb.read_jsonl(path)
    bad = {r["bench"] for r in rows} & EVAL_BENCHES
    if bad:
        raise SystemExit(f"Refusing a pool that contains frozen eval rows: {sorted(bad)}")
    random.Random(seed).shuffle(rows)
    rows = rows[skip:]
    return rows[:limit] if limit else rows


def split_pool(path, dev_size, seed):
    """Deterministic dev slice of the training pool; the rest is the sampling pool."""
    rows = load_pool(path, seed=seed)
    return rows[dev_size:], rows[:dev_size]


# ------------------------------------------------------------------ generation backends
class HFGenerator:
    def __init__(self, model, revision=None, adapter=None, dtype="auto", device=None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model, revision=revision)
        self.model = AutoModelForCausalLM.from_pretrained(model, revision=revision, dtype=dtype)
        if adapter:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, str(adapter))
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device).eval()

    def generate(self, prompts, n, temperature, max_tokens, seed):
        self.torch.manual_seed(seed)
        outs = []
        for msgs in prompts:
            text = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            ids = self.tok(text, return_tensors="pt", add_special_tokens=False).to(self.device)
            with self.torch.inference_mode():
                gen = self.model.generate(**ids, do_sample=temperature > 0, temperature=temperature or None,
                                          top_p=0.95 if temperature > 0 else None, max_new_tokens=max_tokens,
                                          num_return_sequences=n, pad_token_id=self.tok.eos_token_id)
            outs.append([self.tok.decode(g[ids["input_ids"].shape[1]:], skip_special_tokens=True) for g in gen])
        return outs


class VLLMGenerator:
    def __init__(self, model, revision=None, adapter=None, tensor_parallel=1, max_model_len=4096):
        from vllm import LLM, SamplingParams
        from vllm.lora.request import LoRARequest
        self.SamplingParams = SamplingParams
        self.llm = LLM(model=model, revision=revision, enable_lora=bool(adapter), max_lora_rank=64,
                       tensor_parallel_size=tensor_parallel, max_model_len=max_model_len)
        self.lora = LoRARequest("round", 1, str(adapter)) if adapter else None

    def generate(self, prompts, n, temperature, max_tokens, seed):
        params = self.SamplingParams(n=n, temperature=temperature, top_p=0.95 if temperature > 0 else 1.0,
                                     max_tokens=max_tokens, seed=seed)
        results = self.llm.chat(prompts, params, lora_request=self.lora)
        return [[o.text for o in r.outputs] for r in results]


def make_generator(args, adapter=None):
    if args.backend == "vllm":
        return VLLMGenerator(args.model, args.revision, adapter, args.tensor_parallel)
    return HFGenerator(args.model, args.revision, adapter)


# ------------------------------------------------------------------ commands
def sample(gen, rows, n, temperature, max_tokens, seed, out, batch=64):
    os.umask(0o077)
    with open(out, "w", encoding="utf-8") as handle:
        for start in range(0, len(rows), batch):
            chunk = rows[start:start + batch]
            for row, texts in zip(chunk, gen.generate([messages_for(r) for r in chunk], n, temperature,
                                                      max_tokens, seed + start)):
                for k, text in enumerate(texts):
                    pred = sb.parse_answer(text, row["options"])
                    handle.write(json.dumps({"id": row["id"], "k": k, "row": row, "text": text, "pred": pred,
                                             "correct": pred == row["answer"]}) + "\n")


def filter_samples(path, out):
    """One verified trace per item: the shortest correct answer. Returns counts."""
    best, items = {}, set()
    for s in sb.read_jsonl(path):
        items.add(s["id"])
        if s["correct"] and (s["id"] not in best or len(s["text"]) < len(best[s["id"]]["text"])):
            best[s["id"]] = s
    os.umask(0o077)
    with open(out, "w", encoding="utf-8") as handle:
        for s in best.values():
            handle.write(json.dumps({"id": s["id"], "messages": messages_for(s["row"]) +
                                     [{"role": "assistant", "content": s["text"].strip()}]}) + "\n")
    return {"items_sampled": len(items), "items_kept": len(best)}


def train(args, data, output, init_adapter=None):
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments,
                              set_seed)
    set_seed(args.seed)
    rows = sb.read_jsonl(data)
    if any(r["id"].split("-")[0] in EVAL_BENCHES for r in rows):
        raise SystemExit("Refusing training rows from a frozen eval set.")
    tok = AutoTokenizer.from_pretrained(args.model, revision=args.revision)
    encoded = []
    for r in rows:
        prefix = tok.apply_chat_template(r["messages"][:-1], tokenize=False, add_generation_prompt=True)
        full = tok.apply_chat_template(r["messages"], tokenize=False)
        if not full.startswith(prefix):
            raise ValueError("Chat template prefix mismatch; refusing to guess the target span.")
        p = tok(prefix, add_special_tokens=False)["input_ids"]
        t = tok(full[len(prefix):], add_special_tokens=False)["input_ids"]
        if len(p) + len(t) > args.max_length:
            continue  # recorded below; long traces are dropped, never truncated
        encoded.append({"input_ids": p + t, "labels": [-100] * len(p) + t})
    kwargs = {"revision": args.revision, "dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32}
    if args.qlora:
        from transformers import BitsAndBytesConfig
        kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                           bnb_4bit_compute_dtype=torch.bfloat16,
                                                           bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs)
    if args.qlora:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    if init_adapter:  # continue the previous kept round
        model = PeftModel.from_pretrained(model, str(init_adapter), is_trainable=True)
    else:
        model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05,
                                                 target_modules="all-linear", task_type="CAUSAL_LM"))
    if torch.cuda.is_available() and not args.qlora:
        model.enable_input_require_grads()  # gradient checkpointing with a frozen base

    def collate(batch):
        width = max(len(b["input_ids"]) for b in batch)
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        return {"input_ids": torch.tensor([b["input_ids"] + [pad] * (width - len(b["input_ids"])) for b in batch]),
                "attention_mask": torch.tensor([[1] * len(b["input_ids"]) + [0] * (width - len(b["input_ids"]))
                                                for b in batch]),
                "labels": torch.tensor([b["labels"] + [-100] * (width - len(b["labels"])) for b in batch])}

    config = TrainingArguments(output_dir=str(output), num_train_epochs=args.epochs, per_device_train_batch_size=1,
                               gradient_accumulation_steps=args.batch, learning_rate=args.learning_rate,
                               lr_scheduler_type="cosine", warmup_ratio=0.05, bf16=torch.cuda.is_available(),
                               logging_steps=10, save_strategy="no", report_to=[], seed=args.seed,
                               gradient_checkpointing=torch.cuda.is_available(), remove_unused_columns=False,
                               max_steps=args.max_steps or -1)
    started = time.monotonic()
    result = Trainer(model=model, args=config, train_dataset=encoded, data_collator=collate).train()
    model.save_pretrained(str(output))
    receipt = {"schema": "haven-spec2-rft-train-1", "model": args.model, "revision": args.revision,
               "data_sha256": sb.sha256(data), "rows": len(rows), "rows_used": len(encoded),
               "rows_dropped_too_long": len(rows) - len(encoded), "qlora": args.qlora, "rank": args.rank,
               "learning_rate": args.learning_rate, "epochs": args.epochs, "seed": args.seed,
               "init_adapter": str(init_adapter) if init_adapter else None,
               "elapsed_seconds": round(time.monotonic() - started, 1), "metrics": result.metrics}
    (pathlib.Path(output) / "rft-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def dev_accuracy(gen, rows, max_tokens):
    texts = gen.generate([messages_for(r) for r in rows], 1, 0.0, max_tokens, 0)
    return sum(sb.parse_answer(t[0], r["options"]) == r["answer"] for r, t in zip(rows, texts)) / len(rows)


def _phase(args, command, *extra):
    """Run one phase in a fresh process so accelerator memory is released between phases."""
    base = [sys.executable, str(pathlib.Path(__file__).resolve()), command, "--model", args.model,
            "--backend", args.backend, "--tensor-parallel", str(args.tensor_parallel), "--seed", str(args.seed),
            "--max-tokens", str(args.max_tokens)]
    if args.revision:
        base += ["--revision", args.revision]
    subprocess.run(base + [str(x) for x in extra], check=True)


def _train_flags(args):
    flags = ["--rank", args.rank, "--learning-rate", args.learning_rate, "--epochs", args.epochs,
             "--batch", args.batch, "--max-length", args.max_length]
    flags += ["--qlora"] if args.qlora else []
    flags += ["--max-steps", args.max_steps] if args.max_steps else []
    return flags


def cmd_loop(args):
    work = pathlib.Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    pool, dev = split_pool(args.pool, args.dev_size, args.seed)
    sb_rows = lambda rows, path: pathlib.Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))
    sb_rows(dev, work / "dev.jsonl")
    log = {"schema": "haven-spec2-rft-loop-1", "model": args.model, "revision": args.revision,
           "pool_sha256": sb.sha256(args.pool), "dev_size": len(dev), "settings": vars(args) | {"init_adapter":
           str(args.init_adapter) if args.init_adapter else None}, "rounds": []}
    adapter = args.init_adapter

    def dev_score(tag, adapter):
        out = work / f"dev-{tag}.json"
        _phase(args, "dev", "--pool", work / "dev.jsonl", "--out", out, *(["--adapter", adapter] if adapter else []))
        return json.loads(out.read_text())["accuracy"]

    best = log["dev_start"] = dev_score("start", adapter)
    for k in range(1, args.rounds + 1):
        rd = work / f"round-{k}"
        rd.mkdir(exist_ok=True)
        chunk = pool[(k - 1) * args.per_round: k * args.per_round] or pool[:args.per_round]
        sb_rows(chunk, rd / "pool.jsonl")
        _phase(args, "sample", "--pool", rd / "pool.jsonl", "--samples", args.samples, "--temperature",
               args.temperature, "--out", rd / "samples.jsonl", *(["--adapter", adapter] if adapter else []))
        counts = filter_samples(rd / "samples.jsonl", rd / "sft.jsonl")
        if not counts["items_kept"]:
            log["rounds"].append({"round": k, **counts, "kept": False, "stopped": "NO_VERIFIED_SAMPLES"})
            print(json.dumps(log["rounds"][-1]), flush=True)
            break
        _phase(args, "train", "--data", rd / "sft.jsonl", "--output", rd / "adapter", *_train_flags(args),
               *(["--init-adapter", adapter] if adapter else []))
        acc = dev_score(f"round-{k}", rd / "adapter")
        kept = acc >= best + args.min_gain
        receipt = json.loads((rd / "adapter" / "rft-receipt.json").read_text())
        log["rounds"].append({"round": k, **counts, "dev_accuracy": acc, "kept": kept,
                              "train_rows_used": receipt["rows_used"], "train_seconds": receipt["elapsed_seconds"]})
        (work / "loop-receipt.json").write_text(json.dumps(log, indent=2, default=str) + "\n")
        print(json.dumps(log["rounds"][-1]), flush=True)
        if not kept:
            break  # stop at the first round that does not clear the gate
        adapter, best = rd / "adapter", acc
    log["final_adapter"] = str(adapter) if adapter else None
    (work / "loop-receipt.json").write_text(json.dumps(log, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in log.items() if k not in ("rounds", "settings")}, indent=2, default=str))


def cmd_dev(args):
    rows = sb.read_jsonl(args.pool)
    if {r["bench"] for r in rows} & EVAL_BENCHES:
        raise SystemExit("dev never uses frozen eval rows.")
    acc = dev_accuracy(make_generator(args, args.adapter), rows, args.max_tokens)
    pathlib.Path(args.out).write_text(json.dumps({"accuracy": acc, "items": len(rows)}) + "\n")


def cmd_sample(args):
    sample(make_generator(args, args.adapter), load_pool(args.pool, args.limit, args.seed), args.samples,
           args.temperature, args.max_tokens, args.seed, args.out)


def cmd_filter(args):
    print(json.dumps(filter_samples(args.samples, args.out)))


def cmd_train(args):
    print(json.dumps(train(args, args.data, args.output, args.init_adapter), indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", required=True)
    common.add_argument("--revision")
    common.add_argument("--backend", choices=("hf", "vllm"), default="hf")
    common.add_argument("--tensor-parallel", type=int, default=1)
    common.add_argument("--seed", type=int, default=42)
    common.add_argument("--max-tokens", type=int, default=1024)
    trainer = argparse.ArgumentParser(add_help=False)
    trainer.add_argument("--qlora", action="store_true")
    trainer.add_argument("--rank", type=int, default=16)
    trainer.add_argument("--learning-rate", type=float, default=1e-4)
    trainer.add_argument("--epochs", type=float, default=1.0)
    trainer.add_argument("--batch", type=int, default=16)
    trainer.add_argument("--max-length", type=int, default=4096)
    trainer.add_argument("--max-steps", type=int)
    trainer.add_argument("--init-adapter", type=pathlib.Path)
    p = sub.add_parser("sample", parents=[common])
    p.add_argument("--pool", required=True)
    p.add_argument("--adapter", type=pathlib.Path)
    p.add_argument("--limit", type=int)
    p.add_argument("--samples", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--out", required=True)
    p = sub.add_parser("filter")
    p.add_argument("--samples", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("train", parents=[common, trainer])
    p.add_argument("--data", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("dev", parents=[common])
    p.add_argument("--pool", required=True)
    p.add_argument("--adapter", type=pathlib.Path)
    p.add_argument("--out", required=True)
    p = sub.add_parser("loop", parents=[common, trainer])
    p.add_argument("--pool", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--per-round", type=int, default=2000)
    p.add_argument("--samples", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--dev-size", type=int, default=300)
    p.add_argument("--min-gain", type=float, default=0.01)
    args = parser.parse_args(argv)
    {"sample": cmd_sample, "filter": cmd_filter, "train": cmd_train, "dev": cmd_dev, "loop": cmd_loop}[args.command](args)


if __name__ == "__main__":
    main()
