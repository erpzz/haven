"""Opt-in generalized on-policy distillation through TRL's GKDTrainer.

GKD samples student continuations and obtains teacher token-distribution guidance.
Requires teacher and student model weights concurrently (not an HTTP chat API).
The 8-GB Haven workstation is NOT a qualified target for this run.
"""
from __future__ import annotations
import argparse
import json
import pathlib


def load_prompts(path):
    prompts = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("prompt"), str):
            raise ValueError("Expected JSONL objects containing prompt.")
        if not row["prompt"].strip() or len(row["prompt"]) > 16000:
            raise ValueError("Bad prompt.")
        prompts.append({"prompt": row["prompt"]})
    if not prompts:
        raise ValueError("Empty on-policy prompt set.")
    return prompts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prompts", type=pathlib.Path, required=True)
    ap.add_argument("--student", default="Qwen/Qwen3-0.6B")
    ap.add_argument("--teacher", default="Qwen/Qwen3-1.7B")
    ap.add_argument("--output", type=pathlib.Path, default=pathlib.Path(__file__).parent / "adapters" / "opd")
    ap.add_argument("--beta", type=float, choices=[0.0, 1.0], default=1.0,
                    help="0=forward-KL limit, 1=reverse-KL limit")
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--max-length", type=int, default=1024)
    ap.add_argument("--min-vram-gb", type=float, default=16.0)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--allow-download", action="store_true")
    ap.add_argument("--override-memory-gate", action="store_true",
                    help="Advanced: allow attempted co-resident training below VRAM gate.")
    args = ap.parse_args(argv)
    prompts = load_prompts(args.prompts)
    if args.teacher == args.student:
        ap.error("Teacher and student must be distinct model IDs.")
    if not 1 <= args.max_steps <= 10000 or not 128 <= args.max_length <= 4096:
        ap.error("Invalid steps or maximum length.")
    print(json.dumps({"method": "TRL_GKD_on_policy", "prompts": len(prompts),
                      "student": args.student, "teacher": args.teacher,
                      "beta": args.beta, "on_policy_fraction": 1.0,
                      "steps": args.max_steps, "execute": args.execute}))
    if not args.execute:
        print("DRY RUN. No training, downloads or model initialization.")
        return
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError("Output is not empty; refusing overwrite.")
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required. No silent CPU or cloud fallback.")
    available_gb = torch.cuda.get_device_properties(0).total_memory / 2**30
    if available_gb < args.min_vram_gb and not args.override_memory_gate:
        raise RuntimeError(
            f"Only {available_gb:.1f} GiB VRAM; default gate is {args.min_vram_gb:.1f}. "
            "For 8-GB Haven, use success/foresight SFT first; OPD is unqualified.")
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl.experimental.gkd import GKDConfig, GKDTrainer

    offline = not args.allow_download
    tokenizer = AutoTokenizer.from_pretrained(
        args.student, local_files_only=offline, trust_remote_code=False)
    teacher_tokenizer = AutoTokenizer.from_pretrained(
        args.teacher, local_files_only=offline, trust_remote_code=False)
    if tokenizer.get_vocab() != teacher_tokenizer.get_vocab():
        raise RuntimeError("GKD teacher/student token vocabularies differ.")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    student = AutoModelForCausalLM.from_pretrained(
        args.student, local_files_only=offline, trust_remote_code=False)
    teacher = AutoModelForCausalLM.from_pretrained(
        args.teacher, local_files_only=offline, trust_remote_code=False)
    if hasattr(student.config, "use_cache"):
        student.config.use_cache = False
    config = GKDConfig(
        output_dir=str(args.output), max_steps=args.max_steps,
        per_device_train_batch_size=1, gradient_accumulation_steps=4,
        learning_rate=0.0001, fp16=True, bf16=False, report_to=[],
        save_strategy="no", logging_steps=5, max_length=args.max_length,
        max_new_tokens=128, lmbda=1.0, beta=args.beta, seq_kd=False,
    )
    trainer = GKDTrainer(
        model=student, teacher_model=teacher, args=config,
        processing_class=tokenizer, train_dataset=Dataset.from_list(prompts),
        peft_config=LoraConfig(
            r=8, lora_alpha=16, lora_dropout=0.05, bias="none",
            target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM"),
    )
    trainer.train()
    args.output.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(args.output), safe_serialization=True)
    tokenizer.save_pretrained(str(args.output))
    print("On-policy GKD adapter saved. Run frozen holdouts before use.")


if __name__ == "__main__":
    main()
