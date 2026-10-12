"""Opt-in, local LoRA SFT for success/foresight datasets.

No training, network or model download occurs without --execute.
This script trains Hugging Face weights/adapters; GGUF inference files cannot
be fine-tuned directly. Start with a 0.6B-class model on 8 GB Turing hardware.
"""
from __future__ import annotations
import argparse
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def load_examples(path):
    rows = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            if not isinstance(obj, dict) or not all(
                isinstance(obj.get(k), str) and obj[k].strip()
                for k in ("prompt", "completion")
            ):
                raise ValueError("Each training example requires prompt and completion.")
            if len(obj["prompt"]) > 16000 or len(obj["completion"]) > 16000:
                raise ValueError("Refusing oversize example.")
            rows.append(obj)
    if not rows:
        raise ValueError("No approved nonempty training examples.")
    return rows


def tokenize_examples(rows, tokenizer, max_length):
    converted = []
    for row in rows:
        prefix = tokenizer.apply_chat_template(
            [{"role": "user", "content": row["prompt"]}],
            tokenize=True, add_generation_prompt=True)
        answer = tokenizer.encode(row["completion"], add_special_tokens=False)
        end = [tokenizer.eos_token_id]
        if len(prefix) + len(answer) + len(end) > max_length:
            raise ValueError("Example too long; do not silently truncate target.")
        ids = prefix + answer + end
        converted.append({"input_ids": ids, "attention_mask": [1] * len(ids),
                          "labels": [-100] * len(prefix) + answer + end})
    return converted


class LocalDataset:
    def __init__(self, rows):
        self.rows = rows
    def __len__(self):
        return len(self.rows)
    def __getitem__(self, index):
        return self.rows[index]


def collator(tokenizer):
    import torch
    def collate(batch):
        width = max(len(item["input_ids"]) for item in batch)
        pad = tokenizer.pad_token_id
        if pad is None:
            pad = tokenizer.eos_token_id
        def padded(name, fill):
            return torch.tensor([item[name] + [fill] * (width - len(item[name]))
                                 for item in batch], dtype=torch.long)
        return {
            "input_ids": padded("input_ids", pad),
            "attention_mask": padded("attention_mask", 0),
            "labels": padded("labels", -100),
        }
    return collate


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=pathlib.Path, required=True)
    ap.add_argument("--model", default="Qwen/Qwen3-0.6B")
    ap.add_argument("--output", type=pathlib.Path, default=HERE / "adapters" / "sft")
    ap.add_argument("--max-length", type=int, default=1024)
    ap.add_argument("--max-steps", type=int, default=40)
    ap.add_argument("--learning-rate", type=float, default=0.0002)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--allow-download", action="store_true",
                    help="Explicitly allow Hugging Face model files to be downloaded.")
    args = ap.parse_args(argv)
    if not 64 <= args.max_length <= 4096 or not 1 <= args.max_steps <= 10000:
        ap.error("Invalid maximum length or steps.")
    rows = load_examples(args.data)
    print(json.dumps({"recipe": "completion_masked_lora_sft",
                      "examples": len(rows), "model": args.model,
                      "steps": args.max_steps,
                      "execute": args.execute, "download": args.allow_download}))
    if not args.execute:
        print("DRY RUN: no model loaded and no training performed.")
        return
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError("Output directory not empty; refusing to overwrite adapter.")
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required. This recipe is not a CPU fallback.")
    from peft import LoraConfig, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoTokenizer, Trainer,
                              TrainingArguments)
    print("CUDA:", torch.cuda.get_device_name(0),
          "total_gb:", round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2))
    tok = AutoTokenizer.from_pretrained(
        args.model, local_files_only=not args.allow_download, trust_remote_code=False)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, local_files_only=not args.allow_download, trust_remote_code=False)
    if hasattr(model.config, "use_cache"):
        model.config.use_cache = False
    model.gradient_checkpointing_enable()
    model = get_peft_model(model, LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.05, bias="none",
        target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM"))
    encoded = tokenize_examples(rows, tok, args.max_length)
    config = TrainingArguments(
        output_dir=str(args.output), max_steps=args.max_steps,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        learning_rate=args.learning_rate, fp16=True, bf16=False,
        logging_steps=5, save_strategy="no", report_to=[],
        dataloader_num_workers=0, remove_unused_columns=False)
    trainer = Trainer(model=model, args=config, train_dataset=LocalDataset(encoded),
                      data_collator=collator(tok))
    trainer.train()
    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(args.output), safe_serialization=True)
    tok.save_pretrained(str(args.output))
    print("Adapter saved locally. Evaluate against frozen tasks before promotion.")


if __name__ == "__main__":
    main()
