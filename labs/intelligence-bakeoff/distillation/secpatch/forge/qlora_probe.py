"""Can a Qwen3.5-9B-class model (e.g. Qwythos-9B-v2) be QLoRA-fine-tuned on Slink's 8 GB RTX 2070 SUPER?

Runs a handful of real optimizer steps on secpatch training rows and records peak VRAM, seconds per step and loss,
for a few (max_length, LoRA rank) settings, using the forge trainer's tricks: NF4 weights, gradient checkpointing,
logits only at answer tokens (248k vocab), sequences padded to multiples of 256 (bounded Triton shape cache).
Feasibility only: no adapter is saved. Output: one JSON line per setting.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import time


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', required=True, help='local HF checkpoint directory')
    ap.add_argument('--rows', type=pathlib.Path, required=True, help='forge sft.jsonl')
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--settings', default='768:16,1024:16,1536:16,1024:64')
    ap.add_argument('--steps', type=int, default=6)
    args = ap.parse_args(argv)
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
    tok = AutoTokenizer.from_pretrained(args.model)
    rows = [json.loads(x) for x in args.rows.read_text().splitlines() if x.strip()]
    cfg, DEV = {'lowvram': True}, 0
    if cfg.get("lowvram"):
        # 8 GB cards: Qwen3.5-9B's untied 248k-vocab embedding and lm_head are ~1B params each, and a 4-bit lm_head is
        # dequantized whole (1.9 GiB) on every training matmul. Keep both on CPU (logits are only computed at answer
        # positions, ~10% of tokens), the unused vision tower too, and skip PEFT's fp32 upcast.
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16,
                               bnb_4bit_use_double_quant=True, llm_int8_skip_modules=["visual", "lm_head"],
                               llm_int8_enable_fp32_cpu_offload=True)
        dmap = {"model.visual": "cpu", "model.language_model.embed_tokens": "cpu", "model.language_model.layers": DEV,
                "model.language_model.norm": DEV, "model.language_model.rotary_emb": DEV, "lm_head": "cpu"}
    else:
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
        dmap = {"": DEV}
    model = AutoModelForImageTextToText.from_pretrained(args.model, quantization_config=q, device_map=dmap,
                                                        dtype=torch.float16)
    model.config.use_cache = False
    if cfg.get("lowvram"):
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    else:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})
    base_gib = torch.cuda.memory_allocated() / 2**30
    with args.out.open('a') as f:
        f.write(json.dumps({'event': 'loaded', 'weights_gib': round(base_gib, 2),
                            'gpu': torch.cuda.get_device_name(0)}) + '\n')
    for setting in args.settings.split(','):
        max_len, rank = map(int, setting.split(':'))
        rec = {'max_length': max_len, 'rank': rank}
        try:
            pm = get_peft_model(model, LoraConfig(r=rank, lora_alpha=2 * rank, lora_dropout=0.05, task_type='CAUSAL_LM',
                target_modules=r'.*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj|in_proj_\w+|out_proj)'))
            pm.train()  # gradient checkpointing only applies in training mode (from_pretrained returns eval mode)
            opt = torch.optim.AdamW([p for p in pm.parameters() if p.requires_grad], lr=1e-4)
            scaler = torch.amp.GradScaler('cuda')
            enc = []
            for r in rows:  # longest rows that fit, so peak memory is measured at the limit
                msgs = r['messages']
                prefix = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
                full = tok.apply_chat_template(msgs, tokenize=False, enable_thinking=False)
                p = tok(prefix, add_special_tokens=False)['input_ids']
                t = tok(full[len(prefix):].rstrip('\n'), add_special_tokens=False)['input_ids']
                if len(p) + len(t) <= max_len:
                    enc.append((p, t))
            enc.sort(key=lambda x: -(len(x[0]) + len(x[1])))
            enc = enc[:args.steps]
            torch.cuda.reset_peak_memory_stats()
            times, losses = [], []
            for p, t in enc:
                n = -(-(len(p) + len(t)) // 256) * 256
                ids = torch.full((1, n), tok.pad_token_id or 0, device='cuda')
                ids[0, :len(p) + len(t)] = torch.tensor(p + t)
                labels = torch.full((1, n), -100, device='cuda')
                labels[0, len(p):len(p) + len(t)] = torch.tensor(t)
                mask = torch.zeros((1, n), dtype=torch.long, device='cuda'); mask[0, :len(p) + len(t)] = 1
                keep = (labels[0, 1:] != -100).nonzero().squeeze(-1)
                t0 = time.monotonic()
                with torch.autocast('cuda', dtype=torch.float16):
                    out = pm(input_ids=ids, attention_mask=mask, logits_to_keep=keep)
                    loss = torch.nn.functional.cross_entropy(out.logits[0].float(), labels[0, keep + 1])
                scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True)
                torch.cuda.synchronize()
                times.append(time.monotonic() - t0); losses.append(float(loss))
            rec.update(ok=True, steps=len(times), longest_tokens=len(enc[0][0]) + len(enc[0][1]) if enc else 0,
                       s_per_step=round(sum(times[1:]) / max(1, len(times) - 1), 2),
                       peak_gib=round(torch.cuda.max_memory_allocated() / 2**30, 2),
                       losses=[round(x, 3) for x in losses], finite=all(math.isfinite(x) for x in losses))
            model = pm.unload()
            del pm, opt
        except torch.cuda.OutOfMemoryError as exc:
            rec.update(ok=False, error='CUDA OOM: ' + str(exc)[:200])
            try:
                model = pm.unload()
            except Exception:
                pass
        torch.cuda.empty_cache()
        with args.out.open('a') as f:
            f.write(json.dumps(rec) + '\n')
        print(json.dumps(rec), flush=True)


if __name__ == '__main__':
    main()
