"""Forge train+evaluate kernel (free Kaggle 2x T4 lane; also runs on any 2-GPU CUDA box).

Input: a private dataset holding a forge cycle (`sft.jsonl`, `gate.jsonl`, `eval-heldout.jsonl`, `config.json`,
`code/` with forge + secpatch evaluator) and optionally `haven-llama-engine` (prebuilt llama.cpp CUDA build).
Steps, each recorded in /kaggle/working/receipt.json:
  1. QLoRA SFT of the student on both GPUs (completion-only loss, chat template exactly as at inference,
     time-guarded so evaluation always fits in the session).
  2. Merge into the original checkpoint layout, convert to GGUF and quantize (the format Haven serves).
  3. The base model goes through the identical convert/quantize/serve path.
  4. Both GGUFs are served by llama-server and graded on the gate and held-out sets by secpatch's
     deterministic graders. Optional: student self-play on training rows (credit-free self-teaching data).
"""
import json, os, pathlib, shutil, subprocess, sys, time, traceback, urllib.request

T0 = time.monotonic()
OUT = pathlib.Path('/kaggle/working'); OUT.mkdir(exist_ok=True)
W = pathlib.Path('/tmp/forge'); W.mkdir(exist_ok=True)
def find_input(marker, sibling=None, wait_s=900):
    """Locate the attached dataset. A just-uploaded dataset version can mount minutes after the session starts,
    so poll instead of failing (cycle 0's first training kernel died here with StopIteration)."""
    deadline = time.monotonic() + wait_s
    while True:
        for p in pathlib.Path('/kaggle/input').rglob(marker):
            if sibling is None or (p.parent / sibling).exists():
                return p.parent
        if time.monotonic() > deadline:
            raise SystemExit(f'input dataset with {marker} (+{sibling}) not mounted after {wait_s}s')
        time.sleep(15)


CYCLE = find_input('config.json', 'sft.jsonl')
CFG = json.loads((CYCLE / 'config.json').read_text())
R = {'cycle': CFG.get('cycle'), 'config': CFG, 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'stages': {}}


def save():
    (OUT / 'receipt.json').write_text(json.dumps(R, indent=1, default=str))


def stage(name):
    def deco(fn):
        def run(*a, **k):
            t = time.monotonic()
            try:
                res = fn(*a, **k)
                R['stages'][name] = {'ok': True, 'seconds': round(time.monotonic() - t, 1), **(res or {})}
            except Exception:
                R['stages'][name] = {'ok': False, 'seconds': round(time.monotonic() - t, 1),
                                     'error': traceback.format_exc()[-3000:]}
            save()
            return R['stages'][name]
        return run
    return deco


def sh(cmd, log, check=True, **kw):
    with open(OUT / 'logs' / log, 'a') as f:
        f.write(f'$ {cmd}\n'); f.flush()
        r = subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, **kw)
    if check and r.returncode:
        raise RuntimeError(f'{cmd[:200]} -> exit {r.returncode}; see logs/{log}')
    return r


(OUT / 'logs').mkdir(exist_ok=True)
R['gpus'] = subprocess.run('nvidia-smi --query-gpu=name,memory.total --format=csv,noheader', shell=True,
                           capture_output=True, text=True).stdout.strip().splitlines()
save()
LLAMA_TAG = CFG.get('llama_tag', 'b11146')
ENGINE = None


def get_engine(sh, W, LLAMA, log):
    """Prebuilt engine from the attached dataset if it runs on this driver; otherwise compile (sm75)."""
    tars = list(pathlib.Path('/kaggle/input').rglob('llama-b*.tar'))
    # Kaggle unpacks uploaded archives, so the dataset usually holds the extracted engine directory.
    servers = [p for p in pathlib.Path('/kaggle/input').rglob('llama-server') if p.is_file()]
    if servers or tars:
        if servers:
            eng = W / 'engine'
            shutil.copytree(servers[0].parent, eng, symlinks=True, dirs_exist_ok=True)
            for f in eng.iterdir():
                f.chmod(0o755)
            tars = [servers[0]]
        else:
            sh(f'tar -C {W} -xf {tars[0]}', log)
            eng = next(W.glob('llama-b*/llama-server')).parent
        ok = subprocess.run(f'LD_LIBRARY_PATH={eng} {eng}/llama-server --version', shell=True,
                            capture_output=True, text=True)
        if ok.returncode == 0:
            return eng, 'prebuilt:' + tars[0].name
        with open(OUT / 'logs' / log, 'a') as f:
            f.write('prebuilt engine failed: ' + ok.stdout[-500:] + ok.stderr[-1500:] + '\n')
    sh(f'git clone -q --depth 1 --branch {LLAMA} https://github.com/ggml-org/llama.cpp {W}/llama.cpp-src && cd {W}/llama.cpp-src && export LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LIBRARY_PATH && '
           f'cmake -B build -DGGML_CUDA=ON -DGGML_CUDA_NO_VMM=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF '
           f'-DCMAKE_BUILD_TYPE=Release && cmake --build build -j4 --target llama-server llama-quantize', log)
    return W / 'llama.cpp-src/build/bin', 'compiled'


@stage('setup')
def setup():
    global ENGINE
    sh(f'{sys.executable} -m pip install -q -U "transformers>=5.0" peft accelerate bitsandbytes bandit==1.9.4 '
       f'flash-linear-attention sentencepiece', 'pip.log')
    # Kaggle ships torchao 0.10; PEFT refuses to wrap plain Linear layers (the fp16 merge) next to it. Nothing here uses it.
    sh(f'{sys.executable} -m pip uninstall -y -q torchao', 'pip.log', check=False)
    sh(f'git clone -q --depth 1 --branch {LLAMA_TAG} https://github.com/ggml-org/llama.cpp {W}/llama.cpp', 'llama.log')
    sh(f'{sys.executable} -m pip install -q {W}/llama.cpp/gguf-py', 'pip.log')
    ENGINE, how = get_engine(sh, W, LLAMA_TAG, 'llama.log')
    os.environ['LD_LIBRARY_PATH'] = f'{ENGINE}:' + os.environ.get('LD_LIBRARY_PATH', '')
    sh(f'{sys.executable} -m bandit --version', 'pip.log')
    return {'engine': how}


TRAINER = r'''
import json, math, os, pathlib, sys, time, torch
from transformers import (AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig, Trainer,
                          TrainingArguments, TrainerCallback, set_seed)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
cfg = json.loads(sys.argv[1]); deadline = float(sys.argv[2])
rank = int(os.environ.get("LOCAL_RANK", 0)); torch.cuda.set_device(rank); set_seed(cfg["seed"])
tok = AutoTokenizer.from_pretrained(cfg["student"], revision=cfg["revision"])
rows = [json.loads(x) for x in open(cfg["sft"]) if x.strip()]
if cfg.get("max_rows"):  # dry runs: a small deterministic slice
    rows = rows[:cfg["max_rows"]]
enc, skipped = [], 0
for r in rows:
    msgs = r["messages"]
    prefix = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    full = tok.apply_chat_template(msgs, tokenize=False, enable_thinking=False)
    assert full.startswith(prefix), "chat template prefix mismatch"
    p = tok(prefix, add_special_tokens=False)["input_ids"]; t = tok(full[len(prefix):].rstrip("\n"), add_special_tokens=False)["input_ids"]
    if len(p) + len(t) > cfg["max_length"]:
        skipped += 1; continue
    enc.append({"input_ids": p + t, "labels": [-100] * len(p) + t})
class DS(torch.utils.data.Dataset):
    def __len__(self): return len(enc)
    def __getitem__(self, i): return enc[i]
def collate(b):
    # Pad up to a multiple of 256: the DeltaNet (fla/Triton) kernels compile per sequence shape, and thousands of
    # distinct lengths grew host RAM until cycle 0's first full run was OOM-killed at step 146 of 284.
    n = max(len(x["input_ids"]) for x in b); n = -(-n // 256) * 256; pad = tok.pad_token_id or 0
    return {"input_ids": torch.tensor([x["input_ids"] + [pad] * (n - len(x["input_ids"])) for x in b]),
            "attention_mask": torch.tensor([[1] * len(x["input_ids"]) + [0] * (n - len(x["input_ids"])) for x in b]),
            "labels": torch.tensor([x["labels"] + [-100] * (n - len(x["labels"])) for x in b])}
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
model = AutoModelForImageTextToText.from_pretrained(cfg["student"], revision=cfg["revision"], quantization_config=q,
                                                    device_map={"": rank}, dtype=torch.float16)
model.config.use_cache = False
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})
model = get_peft_model(model, LoraConfig(r=cfg["rank"], lora_alpha=cfg["alpha"], lora_dropout=0.05, task_type="CAUSAL_LM",
    target_modules=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj|in_proj_\w+|out_proj)"))
class Guard(TrainerCallback):
    def on_step_end(self, args, state, control, **kw):
        if time.time() > deadline:
            control.should_training_stop = True; control.should_save = True
import inspect
world = int(os.environ.get("WORLD_SIZE", 1))
total_steps = max(1, math.ceil(len(enc) / (world * cfg["grad_accum"])) * math.ceil(cfg["epochs"]))
kw = dict(output_dir=cfg["ckpt"], num_train_epochs=cfg["epochs"], per_device_train_batch_size=1,
          gradient_accumulation_steps=cfg["grad_accum"], learning_rate=cfg["lr"], lr_scheduler_type="cosine",
          warmup_steps=max(1, int(0.03 * total_steps)), fp16=True, logging_steps=5, save_strategy="epoch",
          save_total_limit=1, report_to=[], seed=cfg["seed"], dataloader_num_workers=0, remove_unused_columns=False,
          ddp_find_unused_parameters=False, group_by_length=True, max_grad_norm=1.0)
accepted = inspect.signature(TrainingArguments.__init__).parameters
if rank == 0 and set(kw) - set(accepted):
    print("TrainingArguments: dropping unsupported", sorted(set(kw) - set(accepted)), flush=True)
args = TrainingArguments(**{k: v for k, v in kw.items() if k in accepted})
class AnswerOnlyTrainer(Trainer):
    # Project hidden states to the 248k vocabulary only where a target token follows (about 10% of positions):
    # same loss, a fraction of the logits memory and time.
    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs["labels"]
        keep = (labels[0, 1:] != -100).nonzero().squeeze(-1)
        out = model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"], logits_to_keep=keep)
        logits = out.logits[0].float()
        loss = torch.nn.functional.cross_entropy(logits, labels[0, keep + 1])
        return (loss, out) if return_outputs else loss
tr = AnswerOnlyTrainer(model=model, args=args, train_dataset=DS(), data_collator=collate, callbacks=[Guard()])
tr.model_accepts_loss_kwargs = False  # per-sequence mean loss; the Trainer averages over accumulation steps
torch.cuda.reset_peak_memory_stats()
res = tr.train()
if rank == 0:
    model.save_pretrained(cfg["adapter"])
    json.dump({"rows": len(rows), "encoded": len(enc), "skipped_too_long": skipped, "train_loss": res.training_loss,
               "steps": tr.state.global_step, "max_steps": tr.state.max_steps, "epochs_done": tr.state.epoch,
               "stopped_by_deadline": time.time() > deadline,
               "loss_log": [x for x in tr.state.log_history if "loss" in x],
               "peak_cuda_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2)}, open(cfg["adapter"] + "/train.json", "w"), default=str)
'''


@stage('train')
def train():
    cfg = {**CFG['train'], 'student': CFG['student'], 'revision': CFG['revision'], 'sft': str(CYCLE / 'sft.jsonl'),
           'ckpt': str(W / 'ckpt'), 'adapter': str(OUT / 'adapter')}
    # Leave the configured evaluation reserve inside Kaggle's session limit.
    deadline = time.time() + max(600, CFG['session_seconds'] - CFG['eval_reserve_seconds'] - (time.monotonic() - T0))
    (W / 'trainer.py').write_text(TRAINER)
    ngpu = len(R['gpus'])
    sh(f'{sys.executable} -m torch.distributed.run --nproc_per_node {ngpu} {W}/trainer.py '
       f"'{json.dumps(cfg)}' {deadline}", 'train.log',
       env={**os.environ, 'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True', 'TOKENIZERS_PARALLELISM': 'false'})
    return json.loads((OUT / 'adapter' / 'train.json').read_text())

PREF = r"""
import json, math, random, sys, time, torch
from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel, prepare_model_for_kbit_training
cfg = json.loads(sys.argv[1]); deadline = float(sys.argv[2])
torch.manual_seed(cfg["seed"]); random.seed(cfg["seed"])
tok = AutoTokenizer.from_pretrained(cfg["student"], revision=cfg["revision"])
pairs = [json.loads(x) for x in open(cfg["pairs"]) if x.strip()][:cfg.get("max_pairs") or None]
def encode(prompt, answer):
    prefix = tok.apply_chat_template(prompt, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    p = tok(prefix, add_special_tokens=False)["input_ids"]
    t = tok(answer + tok.eos_token if tok.eos_token else answer, add_special_tokens=False)["input_ids"]
    return p, t
data = []
for x in pairs:
    pc, tc = encode(x["prompt"], x["chosen"]); pr, tr_ = encode(x["prompt"], x["rejected"])
    if len(pc) + max(len(tc), len(tr_)) <= cfg["max_length"] and tc and tr_:
        data.append((pc, tc, tr_))
random.shuffle(data)
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
model = AutoModelForImageTextToText.from_pretrained(cfg["student"], revision=cfg["revision"], quantization_config=q,
                                                    device_map={"": 0}, dtype=torch.float16)
model.config.use_cache = False
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})
model = PeftModel.from_pretrained(model, cfg["adapter"], is_trainable=True)
def seq_logp(p, t):
    ids = torch.tensor([p + t], device="cuda")
    keep = torch.arange(len(p) - 1, len(p) + len(t) - 1, device="cuda")
    logits = model(input_ids=ids, logits_to_keep=keep).logits[0].float()
    lp = torch.log_softmax(logits, -1).gather(-1, torch.tensor(t, device="cuda")[:, None]).squeeze(-1)
    return lp.sum(), lp.mean()
# Reference = the SFT policy itself (frozen log-probs computed once), as in iterative RPO.
model.eval(); ref = []
with torch.no_grad():
    for pc, tc, tr_ in data:
        ref.append((seq_logp(pc, tc)[0].item(), seq_logp(pc, tr_)[0].item()))
model.train()
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=cfg["pref_lr"])
scaler = torch.amp.GradScaler("cuda")
beta, alpha, accum = cfg["pref_beta"], cfg["pref_nll"], cfg["grad_accum"]
log, wins, steps = [], 0, 0
for i, ((pc, tc, tr_), (rc, rr)) in enumerate(zip(data, ref)):
    if time.time() > deadline:
        break
    with torch.autocast("cuda", dtype=torch.float16):
        lc, mc = seq_logp(pc, tc); lr_, _ = seq_logp(pc, tr_)
        margin = beta * ((lc - rc) - (lr_ - rr))
        loss = (-torch.nn.functional.logsigmoid(margin) - alpha * mc) / accum
    scaler.scale(loss).backward()
    wins += int(margin.item() > 0)
    if (i + 1) % accum == 0:
        scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(opt); scaler.update(); opt.zero_grad(); steps += 1
        log.append({"pair": i + 1, "loss": round(loss.item() * accum, 4), "margin": round(margin.item(), 4)})
model.save_pretrained(cfg["adapter"])
json.dump({"pairs": len(pairs), "used": len(data), "optimizer_steps": steps, "reward_accuracy": round(wins / max(1, i + 1), 4),
           "beta": beta, "nll_weight": alpha, "lr": cfg["pref_lr"], "log": log[-50:]},
          open(cfg["adapter"] + "/pref.json", "w"))
"""


@stage('pref')
def pref():
    pairs = CYCLE / 'pairs.jsonl'
    cfg = {**CFG['train'], **CFG.get('pref', {}), 'student': CFG['student'], 'revision': CFG['revision'],
           'pairs': str(pairs), 'adapter': str(OUT / 'adapter')}
    deadline = time.time() + max(300, CFG['session_seconds'] - CFG['eval_reserve_seconds'] - (time.monotonic() - T0))
    (W / 'pref.py').write_text(PREF)
    sh(f"{sys.executable} {W}/pref.py '{json.dumps(cfg)}' {deadline}", 'pref.log',
       env={**os.environ, 'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True', 'CUDA_VISIBLE_DEVICES': '0'})
    return json.loads((OUT / 'adapter' / 'pref.json').read_text())


def to_gguf(src, name):
    f16 = W / f'{name}-f16.gguf'
    sh(f'{sys.executable} {W}/llama.cpp/convert_hf_to_gguf.py {src} --outtype f16 --outfile {f16}', 'gguf.log')
    q = OUT / f'{name}-{CFG["quant"]}.gguf'
    sh(f'{ENGINE}/llama-quantize {f16} {q} {CFG["quant"]}', 'gguf.log')
    f16.unlink()
    return q


def restore_untouched_tensors(base_dir: pathlib.Path, merged: pathlib.Path) -> int:
    """Copy tensors transformers drops on load (Qwen3.5's multi-token-prediction layer) back from the base.

    The config still declares them, so the GGUF converter expects them; LoRA never touched them, so the base
    tensors are exact. Keeping them also keeps MTP speculative decoding possible when serving.
    """
    from safetensors import safe_open
    from safetensors.torch import save_file
    have = set()
    for f in merged.glob('*.safetensors'):
        with safe_open(str(f), 'pt') as h:
            have |= set(h.keys())
    missing = {}
    for f in base_dir.glob('*.safetensors'):
        with safe_open(str(f), 'pt') as h:
            for k in h.keys():
                if k not in have:
                    missing[k] = h.get_tensor(k)
    if not missing:
        return 0
    extra = 'model-restored-00001.safetensors'
    save_file(missing, str(merged / extra), metadata={'format': 'pt'})
    index = merged / 'model.safetensors.index.json'
    if index.exists():  # sharded save: the converter follows the index, so register the new shard there
        idx = json.loads(index.read_text())
        idx['weight_map'].update({k: extra for k in missing})
        index.write_text(json.dumps(idx, indent=1))
    return len(missing)


@stage('merge_convert')
def merge_convert():
    import torch
    from huggingface_hub import snapshot_download
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText
    base_dir = snapshot_download(CFG['student'], revision=CFG['revision'])
    model = AutoModelForImageTextToText.from_pretrained(base_dir, dtype=torch.float16, device_map={'': 'cpu'})
    model = PeftModel.from_pretrained(model, str(OUT / 'adapter')).merge_and_unload()
    merged = W / 'merged'
    model.save_pretrained(merged, safe_serialization=True)
    del model
    for f in pathlib.Path(base_dir).iterdir():  # tokenizer, processor, chat template: byte-identical to base
        if not f.name.endswith('.safetensors') and not f.name.endswith('.index.json') and f.name != 'config.json':
            shutil.copy(f, merged / f.name)
    restored = restore_untouched_tensors(pathlib.Path(base_dir), merged)
    student = to_gguf(merged, 'student')
    shutil.rmtree(merged)
    out = {'student_gguf': student.name, 'student_bytes': student.stat().st_size, 'restored_tensors': restored}
    if CFG.get('eval_base', True):
        base = to_gguf(base_dir, 'base')
        out.update(base_gguf=base.name)
    return out


def serve(gguf, port):
    ctx = CFG['serve_parallel'] * CFG['serve_ctx_per_slot']
    p = subprocess.Popen([str(ENGINE / 'llama-server'), '-m', str(gguf), '--host', '127.0.0.1', '--port', str(port),
                          '-ngl', '999', '-np', str(CFG['serve_parallel']), '-c', str(ctx), '--jinja', '-fa', 'on',
                          '--alias', 'student'], stdout=open(OUT / 'logs' / f'serve-{gguf.stem}.log', 'w'),
                         stderr=subprocess.STDOUT, env=os.environ)
    for _ in range(300):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2)
            return p
        except Exception:
            if p.poll() is not None:
                raise RuntimeError(f'llama-server exited {p.returncode}')
            time.sleep(2)
    raise RuntimeError('llama-server did not become healthy')


def evaluate(gguf, arm):
    p = serve(gguf, 8091)
    res = {}
    try:
        for name in ('gate', 'eval-heldout'):
            out = OUT / 'eval' / arm / name
            sh(f'{sys.executable} {CYCLE}/code/forge/evalrun.py eval --rows {CYCLE}/{name}.jsonl --out {out} '
               f'--base-url http://127.0.0.1:8091/v1 --workers {CFG["serve_parallel"]} --label {arm} '
               + (f'--limit {CFG["eval_limit"]} ' if CFG.get('eval_limit') else '') +
               f'--bandit {shutil.which("bandit") or "bandit"}', f'eval-{arm}.log')
            s = json.loads((out / 'summary.json').read_text())
            res[name] = {k: s[k] for k in ('n', 'score', 'by_task', 'false_positive_rate', 'detection_recall',
                                           'paired_detection', 'cwe_match_when_detected', 'unsupported_rate',
                                           'remediation_bandit_cleared')}
    finally:
        p.terminate(); p.wait(timeout=60)
    return res


@stage('selfplay')
def selfplay():
    """Student answers training rows; answers the recorded ground truth accepts become next cycle's data."""
    p = serve(OUT / f'student-{CFG["quant"]}.gguf', 8092)
    try:
        out = OUT / 'selfplay'
        sh(f'{sys.executable} {CYCLE}/code/forge/evalrun.py selfplay --rows {CYCLE}/pool.jsonl --out {out} '
           f'--base-url http://127.0.0.1:8092/v1 --workers {CFG["serve_parallel"]} --label selfplay-c{CFG.get("cycle", 0)} '
           f'--samples {CFG["selfplay_samples"]} --temperature 0.8 --bandit {shutil.which("bandit") or "bandit"} '
           f'--limit {CFG.get("selfplay_rows", 800)} --deadline {max(60, int(CFG["session_seconds"] - 1800 - (time.monotonic() - T0)))}',
           'selfplay.log')
    finally:
        p.terminate(); p.wait(timeout=60)
    n = lambda f: sum(1 for _ in (out / f).open()) if (out / f).exists() else 0
    return {'accepted_rows': n('selfplay-sft.jsonl'), 'pairs': n('selfplay-pairs.jsonl')}


@stage('eval_student')
def eval_student():
    return evaluate(OUT / f'student-{CFG["quant"]}.gguf', 'student')


@stage('eval_base')
def eval_base():
    return evaluate(OUT / f'base-{CFG["quant"]}.gguf', 'base')


@stage('eval_champion')
def eval_champion(path):
    return evaluate(path, 'champion')


if setup()['ok']:
    if CFG.get('skip_train'):
        R['stages']['train'] = {'ok': True, 'skipped': True}
    else:
        train()
    pairs = CYCLE / 'pairs.jsonl'
    if R['stages']['train']['ok'] and CFG.get('pref', {}).get('enabled') and pairs.exists() and pairs.stat().st_size:
        pref()  # a failed preference stage leaves the SFT adapter in place (it saves only at the end)
    if R['stages']['train']['ok']:
        if merge_convert()['ok']:
            eval_student()
            if CFG.get('eval_base', True):
                eval_base()
            champ = list(pathlib.Path('/kaggle/input').rglob('champion-*.gguf'))
            if champ:
                eval_champion(champ[0])
            if CFG.get('selfplay_samples', 0):
                selfplay()
for f in OUT.glob('base-*.gguf'):
    f.unlink()  # reproducible from the pinned base; keep the output small
R['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
R['wall_seconds'] = round(time.monotonic() - T0, 1)
save()
print(json.dumps({k: v for k, v in R.items() if k != 'config'}, indent=1, default=str)[:20000])
if not all(s.get('ok') for s in R['stages'].values()):
    sys.exit(1)
