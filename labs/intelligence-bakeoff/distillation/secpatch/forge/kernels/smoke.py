"""Kaggle feasibility smoke for the secpatch forge (free 2x T4 lane).

Measures, and records in /kaggle/working/smoke.json:
  1. Qwen3.5-4B QLoRA optimizer steps in fp16 on a T4 (hybrid Gated DeltaNet architecture), s/step, peak memory.
  2. llama.cpp CUDA build time (sm75).
  3. GLM-4.7-Flash Q4_K_M teacher throughput on both T4s with parallel slots.
Each stage is independent; a failure is recorded, never hidden.
"""
import json, os, pathlib, subprocess, sys, time, traceback, urllib.request

OUT = pathlib.Path('/kaggle/working'); OUT.mkdir(exist_ok=True)
WORK = pathlib.Path('/tmp/forge'); WORK.mkdir(exist_ok=True)
R = {'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def save():
    (OUT / 'smoke.json').write_text(json.dumps(R, indent=1, default=str))


def sh(cmd, log, **kw):
    with open(OUT / log, 'a') as f:
        return subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, **kw)


R['nvidia_smi'] = subprocess.run('nvidia-smi --query-gpu=name,memory.total --format=csv,noheader', shell=True,
                                 capture_output=True, text=True).stdout.strip().splitlines()
save()

# llama.cpp build runs in the background while the training probe uses the GPU.
build_t0 = time.monotonic()
build = subprocess.Popen(
    'cd /tmp/forge && git clone -q --depth 1 https://github.com/ggml-org/llama.cpp && cd llama.cpp && '
    'export LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LIBRARY_PATH && '
    '(cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release '
    '-DCMAKE_LIBRARY_PATH=/usr/local/cuda/lib64/stubs || (rm -rf build && cmake -B build -DGGML_CUDA=ON '
    '-DGGML_CUDA_NO_VMM=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release)) && '
    'cmake --build build -j4 --target llama-server llama-quantize',
    shell=True, stdout=open(OUT / 'llama-build.log', 'w'), stderr=subprocess.STDOUT)

# 1. Qwen3.5-4B QLoRA probe
try:
    t0 = time.monotonic()
    sh(f'{sys.executable} -m pip install -q -U "transformers>=5.0" peft accelerate bitsandbytes', 'pip.log', check=True)
    fla = sh(f'{sys.executable} -m pip install -q flash-linear-attention', 'pip.log').returncode == 0
    R['pip_seconds'] = round(time.monotonic() - t0, 1)
    probe = r'''
import json, math, time, torch, transformers, peft
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
name = "Qwen/Qwen3.5-4B"
tok = AutoTokenizer.from_pretrained(name)
q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True)
t0 = time.monotonic()
model = AutoModelForCausalLM.from_pretrained(name, quantization_config=q, device_map={"": 0}, dtype=torch.float16)
load_s = time.monotonic() - t0
model.config.use_cache = False
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})
model.train()
model = get_peft_model(model, LoraConfig(r=32, lora_alpha=64, lora_dropout=0.05, task_type="CAUSAL_LM",
                                         target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]))
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
scaler = torch.amp.GradScaler("cuda")
text = "def handler(request):\n    path = request.args.get('p')\n    return open(path).read()\n" * 300
ids = tok(text, return_tensors="pt").input_ids[:, :2048].cuda()
losses, times = [], []
torch.cuda.reset_peak_memory_stats()
for step in range(8):
    t = time.monotonic()
    with torch.autocast("cuda", dtype=torch.float16):
        loss = model(input_ids=ids, labels=ids).loss
    scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); opt.zero_grad()
    torch.cuda.synchronize(); times.append(time.monotonic() - t); losses.append(float(loss))
print("PROBE" + json.dumps({"transformers": transformers.__version__, "peft": peft.__version__, "torch": torch.__version__,
    "load_s": round(load_s,1), "seq": int(ids.shape[1]), "s_per_step_2048": round(sum(times[2:])/len(times[2:]),2),
    "losses": [round(x,3) for x in losses], "finite": all(math.isfinite(x) for x in losses),
    "peak_gib": round(torch.cuda.max_memory_allocated()/2**30,2),
    "arch": type(model.base_model.model).__name__}))
'''
    (WORK / 'probe.py').write_text(probe)
    p = subprocess.run([sys.executable, str(WORK / 'probe.py')], capture_output=True, text=True, timeout=3600,
                       env={**os.environ, 'CUDA_VISIBLE_DEVICES': '0'})
    (OUT / 'probe.log').write_text(p.stdout[-20000:] + '\n--- stderr ---\n' + p.stderr[-20000:])
    line = [x for x in p.stdout.splitlines() if x.startswith('PROBE')]
    R['qwen35_4b_qlora'] = json.loads(line[-1][5:]) if line else {'error': p.stderr[-1500:]}
    R['qwen35_4b_qlora']['fla_installed'] = fla
except Exception:
    R['qwen35_4b_qlora'] = {'error': traceback.format_exc()[-1500:]}
save()

# 2. llama.cpp build
build.wait()
R['llama_build'] = {'rc': build.returncode, 'seconds': round(time.monotonic() - build_t0, 1)}
save()

# 3. GLM-4.7-Flash teacher throughput on 2x T4
try:
    from huggingface_hub import hf_hub_download
    t0 = time.monotonic()
    gguf = hf_hub_download('unsloth/GLM-4.7-Flash-GGUF', 'GLM-4.7-Flash-Q4_K_M.gguf', local_dir=str(WORK))
    R['glm_download_s'] = round(time.monotonic() - t0, 1)
    srv = subprocess.Popen([str(WORK / 'llama.cpp/build/bin/llama-server'), '-m', gguf, '--host', '127.0.0.1',
                            '--port', '8090', '-ngl', '999', '-np', '8', '-c', '65536', '--jinja', '-fa', 'on'],
                           stdout=open(OUT / 'glm-server.log', 'w'), stderr=subprocess.STDOUT)
    for _ in range(600):
        try:
            urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2); break
        except Exception:
            time.sleep(2)
    R['glm_load_s'] = round(time.monotonic() - t0, 1)
    from concurrent.futures import ThreadPoolExecutor
    code = '\n'.join(f'{i:5d} |     value = request.args.get("p{i}")  # handler line' for i in range(120))
    msg = ('Review this function for security vulnerabilities, reason briefly, then give JSON '
           '{"verdict": "vulnerable"|"not_vulnerable", "cwe": [str]}.\n```python\n' + code + '\n```')

    def one(i):
        body = {'model': 'glm', 'messages': [{'role': 'user', 'content': msg + f'\n(case {i})'}], 'max_tokens': 400,
                'temperature': 0.6, 'chat_template_kwargs': {'enable_thinking': False}}
        req = urllib.request.Request('http://127.0.0.1:8090/v1/chat/completions', json.dumps(body).encode(),
                                     {'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(req, timeout=900).read())
    t0 = time.monotonic()
    with ThreadPoolExecutor(16) as ex:
        res = list(ex.map(one, range(16)))
    wall = time.monotonic() - t0
    usage = [r.get('usage', {}) for r in res]
    R['glm_throughput'] = {'requests': 16, 'wall_s': round(wall, 1),
                           'prompt_tokens': sum(u.get('prompt_tokens', 0) for u in usage),
                           'completion_tokens': sum(u.get('completion_tokens', 0) for u in usage),
                           'sample': res[0]['choices'][0]['message'].get('content', '')[:800]}
    R['glm_throughput']['completion_tok_per_s'] = round(R['glm_throughput']['completion_tokens'] / wall, 1)
    srv.terminate()
except Exception:
    R['glm_throughput'] = {'error': traceback.format_exc()[-1500:]}
R['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
save()
print(json.dumps(R, indent=1, default=str))
