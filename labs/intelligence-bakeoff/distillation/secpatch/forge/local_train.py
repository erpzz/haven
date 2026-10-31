"""Fine-tune a Qwen3.5-family student on Slink's own GPU with the forge's Kaggle trainer, unchanged.

The SFT trainer and the preference (DPO+NLL) stage are the self-contained scripts embedded in kernels/train.py; they
are extracted (not re-implemented) and run on one GPU. Then the adapter is merged into the original checkpoint
layout (dropped tensors such as Qwen3.5's MTP head restored), converted to GGUF and quantized, ready for
serve_bench/evalrun grading on the same held-out items as the stock model.

Example (Qwythos-9B-v2 on the 8 GB RTX 2070 SUPER, settings from qlora_probe.py):
  local_train.py --model ~/.local/state/haven-forge/models/qwythos/hf --cycle-data cycles/c001/data \
      --out runs/qwythos-c001 --max-length 1536 --rank 16 --epochs 1
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path.home()
ENGINE = HOME / '.local/share/haven-model-lab/engines/b11146/llama-b11146'
LLAMA_SRC = pathlib.Path('/tmp/llama.cpp-b11146')


def kernel_script(name: str) -> str:
    """The TRAINER/PREF source strings from kernels/train.py, read without executing the kernel."""
    tree = ast.parse((HERE / 'kernels' / 'train.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def run(cmd, log: pathlib.Path, env=None):
    with log.open('a') as f:
        f.write('$ ' + ' '.join(map(str, cmd))[:400] + '\n'); f.flush()
        r = subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT, env=env)
    if r.returncode:
        raise RuntimeError(f'{cmd[1] if len(cmd) > 1 else cmd[0]} exited {r.returncode}; see {log}')


PREEMPT_REQUEST = HOME / '.local/state/haven/gpu-preempt-request'


def note(log: pathlib.Path, msg: str):
    with log.open('a') as f:
        f.write(time.strftime('%FT%TZ ', time.gmtime()) + msg + '\n')


def fresh_request(max_age_s: int = 1800) -> bool:
    """Model Lab writes this when a load would fit an empty card but our VRAM blocks it (and deletes it once loaded)."""
    try:
        return time.time() - PREEMPT_REQUEST.stat().st_mtime < max_age_s
    except FileNotFoundError:
        return False


class ChatWatcher:
    """The owner wants this GPU for interactive inference: Model Lab's explicit preemption request.

    Chat traffic alone is not a signal: Model Lab never auto-loads on chat, and cloud-routed chats need no GPU, so
    pausing on every gateway request would stall training for no one.
    """
    def chat_wanted(self) -> str | None:
        return 'Model Lab gpu-preempt-request' if fresh_request() else None


def wait_for_quiet_gpu(out: pathlib.Path, log: pathlib.Path):
    """Start or resume only when no other process holds the GPU and no fresh preemption request is pending."""
    while True:
        teacher = subprocess.run(['systemctl', '--user', 'show', '-p', 'MainPID', '--value', 'forge-teacher-server'],
                                 capture_output=True, text=True).stdout.strip()
        pids = set(subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'],
                                  capture_output=True, text=True).stdout.split()) - {teacher, '0', ''}
        if not pids and not fresh_request():
            subprocess.run(['systemctl', '--user', 'stop', 'forge-teacher-server'])  # this session's own teacher
            note(log, 'GPU free and no pending preemption request; (re)starting training')
            return
        time.sleep(60)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', type=pathlib.Path, required=True, help='local HF checkpoint (student base)')
    ap.add_argument('--cycle-data', type=pathlib.Path, required=True, help='forge cycle data dir (sft.jsonl, pairs.jsonl)')
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--max-length', type=int, default=1536)
    ap.add_argument('--rank', type=int, default=16)
    ap.add_argument('--epochs', type=float, default=1.0)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--grad-accum', type=int, default=16)
    ap.add_argument('--hours', type=float, default=20, help='training deadline; the adapter is saved when it hits')
    ap.add_argument('--pref', action='store_true', help='run the DPO+NLL stage on pairs.jsonl after SFT')
    ap.add_argument('--quant', default='Q4_K_M')
    ap.add_argument('--lowvram', action='store_true', help='9B on 8 GB: 4-bit lm_head, embedding and vision on CPU')
    ap.add_argument('--save-steps', type=int, default=10, help='checkpoint interval (optimizer steps); bounds lost work')
    ap.add_argument('--python', default=str(HOME / '.local/share/forge-train-venv/bin/python'))
    args = ap.parse_args(argv)
    out = args.out; out.mkdir(parents=True, exist_ok=True)
    log = out / 'local_train.log'
    receipt = {'model': str(args.model), 'cycle_data': str(args.cycle_data), 'started': time.strftime('%FT%TZ', time.gmtime()),
               'settings': {k: getattr(args, k) for k in ('max_length', 'rank', 'epochs', 'lr', 'grad_accum', 'pref', 'quant')}}
    save = lambda: (out / 'receipt.json').write_text(json.dumps(receipt, indent=1, default=str))
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '0', 'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True',
           'TOKENIZERS_PARALLELISM': 'false'}
    cfg = {'rank': args.rank, 'alpha': 2 * args.rank, 'lr': args.lr, 'epochs': args.epochs, 'grad_accum': args.grad_accum,
           'max_length': args.max_length, 'seed': 42, 'student': str(args.model), 'revision': None,
           'sft': str(args.cycle_data / 'sft.jsonl'), 'ckpt': str(out / 'ckpt'), 'adapter': str(out / 'adapter'),
           'lowvram': args.lowvram}
    t0 = time.monotonic()
    (out / 'trainer.py').write_text(kernel_script('TRAINER'))
    flag = out / 'PREEMPT'
    cfg.update(preempt_flag=str(flag), save_steps=args.save_steps, resume=True)
    deadline = time.time() + args.hours * 3600
    receipt['preemptions'] = []
    while True:  # interactive inference takes precedence: yield the GPU, then resume from the checkpoint
        flag.unlink(missing_ok=True)
        wait_for_quiet_gpu(out, log)
        proc = subprocess.Popen([args.python, str(out / 'trainer.py'), json.dumps(cfg), str(deadline)],
                                stdout=log.open('a'), stderr=subprocess.STDOUT, env=env)
        watcher = ChatWatcher()
        while proc.poll() is None:
            time.sleep(15)
            why = watcher.chat_wanted()
            if why and not flag.exists():
                flag.write_text(why)
                receipt['preemptions'].append({'at': time.strftime('%FT%TZ', time.gmtime()), 'why': why}); save()
                note(log, f'preempting training: {why}')
        if proc.returncode:
            raise RuntimeError(f'trainer exited {proc.returncode}; see {log}')
        train = json.loads((out / 'adapter' / 'train.json').read_text())
        if not train.get('preempted'):
            break
        note(log, 'training paused for interactive use; will resume when the GPU is quiet')
    receipt['train'] = train; save()
    if args.pref and (args.cycle_data / 'pairs.jsonl').exists():
        pcfg = {**cfg, 'pairs': str(args.cycle_data / 'pairs.jsonl'), 'pref_lr': 2e-5, 'pref_beta': 0.1, 'pref_nll': 1.0}
        (out / 'pref.py').write_text(kernel_script('PREF'))
        run([args.python, out / 'pref.py', json.dumps(pcfg), time.time() + 6 * 3600], log, env)
        receipt['pref'] = json.loads((out / 'adapter' / 'pref.json').read_text()); save()
    # Merge on CPU into the original layout, restore tensors transformers drops (MTP), convert and quantize.
    merge = f'''
import json, pathlib, shutil, sys, torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText
sys.path.insert(0, {str(HERE / 'kernels')!r})
base, adapter, merged = pathlib.Path({str(args.model)!r}), {str(out / 'adapter')!r}, pathlib.Path({str(out / 'merged')!r})
m = AutoModelForImageTextToText.from_pretrained(base, dtype=torch.float16, device_map={{"": "cpu"}})
m = PeftModel.from_pretrained(m, adapter).merge_and_unload()
m.save_pretrained(merged, safe_serialization=True)
for f in base.iterdir():
    if not f.name.endswith(".safetensors") and not f.name.endswith(".index.json") and f.name != "config.json" and f.is_file():
        shutil.copy(f, merged / f.name)
'''
    (out / 'merge.py').write_text(merge)
    run([args.python, out / 'merge.py'], log, {**env, 'CUDA_VISIBLE_DEVICES': ''})
    restore_src = (HERE / 'kernels' / 'train.py').read_text()
    a = restore_src.index('def restore_untouched_tensors'); b = restore_src.index("@stage('merge_convert')")
    ns: dict = {'json': json, 'pathlib': pathlib}
    exec(compile(restore_src[a:b], 'restore', 'exec'), ns)
    receipt['restored_tensors'] = ns['restore_untouched_tensors'](args.model, out / 'merged'); save()
    if not LLAMA_SRC.exists():
        run(['git', 'clone', '-q', '--depth', '1', '--branch', 'b11146', 'https://github.com/ggml-org/llama.cpp', LLAMA_SRC], log)
    run([args.python, '-m', 'pip', 'install', '-q', LLAMA_SRC / 'gguf-py'], log)
    f16 = out / 'student-f16.gguf'
    run([args.python, LLAMA_SRC / 'convert_hf_to_gguf.py', out / 'merged', '--outtype', 'f16', '--outfile', f16], log)
    gguf = out / f'student-{args.quant}.gguf'
    run([ENGINE / 'llama-quantize', f16, gguf, args.quant], log, {**env, 'LD_LIBRARY_PATH': str(ENGINE)})
    f16.unlink(); shutil.rmtree(out / 'merged')
    receipt.update(gguf=str(gguf), gguf_bytes=gguf.stat().st_size, wall_s=round(time.monotonic() - t0, 1),
                   finished=time.strftime('%FT%TZ', time.gmtime()))
    save()
    print(json.dumps({k: receipt[k] for k in ('gguf', 'wall_s')}))


if __name__ == '__main__':
    try:
        main()
    finally:  # this session's own teacher was stopped for training
        subprocess.run(['systemctl', '--user', 'start', 'forge-teacher-server'])
