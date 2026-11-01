"""Teacher bake-off kernel: identical rows, one attempt each, for every candidate teacher on a Kaggle 2x T4 pair.

The decisive metric for a teacher is the share of rows where its trace passes forge/teach.py's checks on the first
attempt (no retries, no reasoning mode), plus the reviewer's read of the traces. Output: traces-<name>.jsonl and
receipt.json in /kaggle/working.
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


CYCLE = find_input('bakeoff.json')
CFG = json.loads((CYCLE / 'bakeoff.json').read_text())
R = {'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'candidates': {}}


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


engine, R['engine'] = get_engine(sh, W, CFG.get('llama_tag', 'b11146'), 'setup.log')
os.environ['LD_LIBRARY_PATH'] = f'{engine}:' + os.environ.get('LD_LIBRARY_PATH', '')
sh(f'{sys.executable} -m pip install -q -U huggingface_hub', 'setup.log')
from huggingface_hub import hf_hub_download
for cand in CFG['candidates']:
    name, t = cand['name'], time.monotonic()
    try:
        gguf = hf_hub_download(cand['repo'], cand['file'], revision=cand.get('revision'), local_dir=str(W))
        srv = subprocess.Popen([str(engine / 'llama-server'), '-m', gguf, '--host', '127.0.0.1', '--port', '8090',
                                '-ngl', '999', '-np', '8', '-c', str(8 * 8192), '--jinja', '-fa', 'on', '--alias', 'teacher'],
                               stdout=open(OUT / 'logs' / f'server-{name}.log', 'w'), stderr=subprocess.STDOUT, env=os.environ)
        for _ in range(600):
            try:
                urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2); break
            except Exception:
                if srv.poll() is not None:
                    raise RuntimeError(f'server exited {srv.returncode}')
                time.sleep(2)
        out = OUT / f'traces-{name}.jsonl'
        sh(f'{sys.executable} {CYCLE}/code/forge/teach.py --rows {CYCLE}/rows.jsonl --out {out} '
           f'--base-url http://127.0.0.1:8090/v1 --model teacher --workers 8 --attempts 1 --think-retries 0', f'teach-{name}.log')
        srv.terminate(); srv.wait(timeout=60)
        recs = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
        by = {}
        for r in recs:
            by.setdefault(r['task'], [0, 0]); by[r['task']][0] += 1; by[r['task']][1] += bool(r['sft'])
        R['candidates'][name] = {'ok': True, 'rows': len(recs), 'first_try_pass': sum(1 for r in recs if r['sft']),
                                 'by_task': by, 'completion_tokens': sum(r['usage']['completion_tokens'] for r in recs),
                                 'seconds': round(time.monotonic() - t, 1)}
        os.remove(gguf)
    except Exception:
        R['candidates'][name] = {'ok': False, 'error': traceback.format_exc()[-1500:]}
    save()
R['wall_seconds'] = round(time.monotonic() - T0, 1)
save()
print(json.dumps(R, indent=1))
