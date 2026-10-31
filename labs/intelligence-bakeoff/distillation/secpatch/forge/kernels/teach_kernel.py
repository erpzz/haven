"""Forge teacher kernel: GLM-4.7-Flash (MIT) on a free Kaggle 2x T4 pair, verified traces for training rows.

Input dataset: a forge cycle (`pool.jsonl` recorded targets, `config.json`, `code/`) and optionally `haven-llama-engine`.
Output: /kaggle/working/traces.jsonl (teach.py format; resumable: a previous version's traces in the input are
carried forward and skipped) and receipt.json.
"""
import json, os, pathlib, shutil, subprocess, sys, time, traceback, urllib.request

T0 = time.monotonic()
OUT = pathlib.Path('/kaggle/working'); (OUT / 'logs').mkdir(parents=True, exist_ok=True)
W = pathlib.Path('/tmp/forge'); W.mkdir(exist_ok=True)
def find_input(marker, sibling=None, wait_s=2700):
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


CYCLE = find_input('config.json', 'pool.jsonl')
CFG = json.loads((CYCLE / 'config.json').read_text())
T = CFG['teacher']
R = {'cycle': CFG.get('cycle'), 'teacher': T, 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def save():
    (OUT / 'receipt.json').write_text(json.dumps(R, indent=1, default=str))


def sh(cmd, log):
    with open(OUT / 'logs' / log, 'a') as f:
        r = subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(f'{cmd[:200]} -> exit {r.returncode}')


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


try:
    R['gpus'] = subprocess.run('nvidia-smi --query-gpu=name,memory.total --format=csv,noheader', shell=True,
                               capture_output=True, text=True).stdout.strip().splitlines()
    engine, R['engine'] = get_engine(sh, W, CFG.get('llama_tag', 'b11146'), 'setup.log')
    os.environ['LD_LIBRARY_PATH'] = f'{engine}:' + os.environ.get('LD_LIBRARY_PATH', '')
    sh(f'{sys.executable} -m pip install -q -U huggingface_hub', 'setup.log')
    from huggingface_hub import hf_hub_download
    gguf = hf_hub_download(T['repo'], T['file'], revision=T.get('revision'), local_dir=str(W))
    R['setup_seconds'] = round(time.monotonic() - T0, 1); save()
    ctx = T['parallel'] * T['ctx_per_slot']
    srv = subprocess.Popen([str(engine / 'llama-server'), '-m', gguf, '--host', '127.0.0.1', '--port', '8090',
                            '-ngl', '999', '-np', str(T['parallel']), '-c', str(ctx), '--jinja', '-fa', 'on',
                            '--alias', 'teacher'], stdout=open(OUT / 'logs' / 'teacher-server.log', 'w'),
                           stderr=subprocess.STDOUT, env=os.environ)
    for _ in range(600):
        try:
            urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2); break
        except Exception:
            if srv.poll() is not None:
                raise RuntimeError(f'teacher server exited {srv.returncode}')
            time.sleep(2)
    R['server_ready_seconds'] = round(time.monotonic() - T0, 1); save()
    traces = OUT / 'traces.jsonl'
    for prev in pathlib.Path('/kaggle/input').rglob('traces*.jsonl'):  # carry forward earlier sessions' work
        with traces.open('a') as f:
            f.write(prev.read_text())
    deadline = CFG['session_seconds'] - 900 - (time.monotonic() - T0)
    rows = [str(CYCLE / 'pool.jsonl')] + [str(p) for p in CYCLE.glob('teach-extra*.jsonl')]
    sh(f'{sys.executable} {CYCLE}/code/forge/teach.py --rows {" ".join(rows)} --out {traces} '
       f'--base-url http://127.0.0.1:8090/v1 --model teacher --workers {T["parallel"]} '
       f'--attempts {T["attempts"]} --deadline {int(deadline)} --shard {T.get("shard", "0-0/1")} '
       f'--think-retries {T.get("think_retries", 1)}', 'teach.log')
    if T.get('critic', True):  # blind second read of every trace this cycle has (carried forward + new)
        prior = [str(p) for p in pathlib.Path('/kaggle/input').rglob('traces*.jsonl')]
        left = CFG['session_seconds'] - 600 - (time.monotonic() - T0)
        if left > 600:
            sh(f'{sys.executable} {CYCLE}/code/forge/critic.py --pool {CYCLE}/pool.jsonl --traces {traces} '
               f'{" ".join(prior)} --out {OUT}/critic.jsonl --base-url http://127.0.0.1:8090/v1 '
               f'--workers {T["parallel"]} --deadline {int(left)}', 'critic.log')
            cr = [json.loads(x) for x in (OUT / 'critic.jsonl').read_text().splitlines() if x.strip()] \
                if (OUT / 'critic.jsonl').exists() else []
            R['critic'] = {'judged': len(cr), 'unsound': sum(1 for c in cr if not c['sound'])}
    srv.terminate()
    recs = [json.loads(x) for x in traces.read_text().splitlines() if x.strip()]
    by = {}
    for r in recs:
        k = r['task']; by.setdefault(k, [0, 0]); by[k][0] += 1; by[k][1] += bool(r['sft'])
    R['traces'] = {'records': len(recs), 'kept_by_task': by,
                   'completion_tokens': sum(r['usage']['completion_tokens'] for r in recs)}
    R['ok'] = True
except Exception:
    R['ok'] = False
    R['error'] = traceback.format_exc()[-3000:]
R['wall_seconds'] = round(time.monotonic() - T0, 1)
save()
print(json.dumps(R, indent=1, default=str))
if not R['ok']:
    sys.exit(1)
