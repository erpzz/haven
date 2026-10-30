"""Thought-relay benchmark on Slink: does one model's chain of thought improve another model's answer?

Arms (same items, secpatch graders):
  L_think    Liquid LFM2.5-8B-A1B reasons and answers                 (stage 1 for L->B)
  B_nothink  Qwen3.6-35B-A3B answers without reasoning
  B_think    Qwen3.6-35B-A3B reasons and answers                     (stage 1 for B->L)
  L2B_think  Liquid's stored reasoning in the 35B's own think slot, the 35B answers
  L2B_notes  Liquid's reasoning as notes in the prompt (COT-EFF-2's arm D), the 35B answers, thinking off
  B2L_think  the 35B's stored reasoning in Liquid's think slot, Liquid answers
  B2L_notes  the 35B's reasoning as notes, Liquid answers
Two-stage by design: a reasoner runs over all items and its reasoning is stored, then the answer model's server
replaces it, so the two never share the 8 GB GPU and each stage's cost is measured on its own. Liquid cannot answer
without reasoning (LFM2.5 thinks even with thinking off), so there is no Liquid no-think arm.
llama.cpp b11146 occasionally dies mid long prompt ("illegal memory access"): a dead server is restarted and the
arm resumes; re-runs are logged. Nothing here stops a GPU job it does not own; it waits for the GPU instead.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path.home()
ENGINE = HOME / '.local/share/haven-model-lab/engines/b11146/llama-b11146'
MODELS = {'L': HOME / '.local/share/haven-paradigms/models/LFM2.5-8B-A1B-Q4_K_M.gguf',
          'B': HOME / '.local/share/haven-model-lab/models/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf'}
COMMON = ['--n-gpu-layers', '999', '--device', 'CUDA0', '--cpu-moe', '--ctx-size', '32768', '--parallel', '1',
          '--threads', '12', '--threads-batch', '12', '--flash-attn', 'auto', '--jinja']
# Large prefill batches: relay arms feed thousands of reasoning tokens to the answer model (PREFILL-1: 5.7-7.5x faster
# prompt reading at 2048, decode unchanged). Every arm on a server uses the same settings.
EXTRA = {'L': ['--batch-size', '2048', '--ubatch-size', '2048'],
         'B': ['--batch-size', '2048', '--ubatch-size', '2048', '--cache-type-k', 'f16', '--cache-type-v', 'f16']}
PORT = 8095
ARMS = [  # (name, server, evalrun flags)
    ('L_think', 'L', ['--think', '8192', '--keep-reasoning', '--sampling', 'liquid']),
    ('B_nothink', 'B', []),
    ('B_think', 'B', ['--think', '7680', '--keep-reasoning']),
    ('L2B_think', 'B', ['--reasoning-from', '{out}/L_think/items.jsonl', '--relay-style', 'think']),
    ('L2B_notes', 'B', ['--reasoning-from', '{out}/L_think/items.jsonl', '--relay-style', 'notes']),
    ('B2L_think', 'L', ['--reasoning-from', '{out}/B_think/items.jsonl', '--relay-style', 'think', '--sampling', 'liquid']),
    ('B2L_notes', 'L', ['--reasoning-from', '{out}/B_think/items.jsonl', '--relay-style', 'notes', '--sampling', 'liquid']),
]


def log(out: pathlib.Path, event: str, **kw):
    rec = {'t': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'event': event, **kw}
    with (out / 'bench.jsonl').open('a') as f:
        f.write(json.dumps(rec) + '\n')
    print(json.dumps(rec), flush=True)


def healthy() -> bool:
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health', timeout=3)
        return True
    except Exception:
        return False


def gpu_pids() -> set[str]:
    r = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], capture_output=True, text=True)
    return {x.strip() for x in r.stdout.split() if x.strip()}


class Server:
    def __init__(self, out: pathlib.Path):
        self.out, self.proc, self.which = out, None, None

    def start(self, which: str):
        self.stop()
        env = {**os.environ, 'LD_LIBRARY_PATH': str(ENGINE)}
        cmd = [str(ENGINE / 'llama-server'), '-m', str(MODELS[which]), '--host', '127.0.0.1', '--port', str(PORT),
               '--alias', which, *COMMON, *EXTRA[which]]
        self.proc = subprocess.Popen(cmd, stdout=open(self.out / f'server-{which}.log', 'a'), stderr=subprocess.STDOUT,
                                     env=env)
        self.which = which
        for _ in range(600):
            if healthy():
                log(self.out, 'server_up', model=which, pid=self.proc.pid)
                return
            if self.proc.poll() is not None:
                raise RuntimeError(f'server {which} exited {self.proc.returncode}')
            time.sleep(2)
        raise RuntimeError(f'server {which} not healthy')

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


def errors_in(path: pathlib.Path) -> int:
    if not path.exists():
        return -1
    return sum(1 for x in path.read_text().splitlines() if x.strip() and json.loads(x).get('error'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rows', type=pathlib.Path, required=True, help='eval-format items (with graders)')
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--arms', default=','.join(a[0] for a in ARMS))
    ap.add_argument('--wait-gpu-hours', type=float, default=6)
    ap.add_argument('--bandit', default=str(HOME / '.local/share/haven-forge-venv/bin/bandit'))
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    wanted = set(args.arms.split(','))
    # Free the GPU of this session's own teacher only; wait for anyone else's job to finish.
    if subprocess.run(['systemctl', '--user', 'is-active', 'forge-teacher-server'], capture_output=True,
                      text=True).stdout.strip() == 'active':
        subprocess.run(['systemctl', '--user', 'stop', 'forge-teacher-server'])
        log(args.out, 'stopped_own_teacher', unit='forge-teacher-server', note='restarted when the bench ends')
    deadline = time.time() + args.wait_gpu_hours * 3600
    while gpu_pids():
        if time.time() > deadline:
            log(args.out, 'gpu_busy_gave_up', pids=sorted(gpu_pids()))
            return 1
        time.sleep(60)
    server = Server(args.out)
    try:
        for name, which, flags in ARMS:
            if name not in wanted:
                continue
            dest = args.out / name
            flags = [f.format(out=args.out) for f in flags]
            for attempt in range(4):
                if server.which != which or not healthy():
                    if server.which == which:
                        log(args.out, 'server_dead_restart', arm=name, attempt=attempt)
                    server.start(which)
                    if '--relay-style' in flags and flags[flags.index('--relay-style') + 1] == 'think':
                        # Record where the reasoning goes: think delimiters differ between model families.
                        req = urllib.request.Request(f'http://127.0.0.1:{PORT}/apply-template', json.dumps(
                            {'messages': [{'role': 'user', 'content': 'Q'}], 'chat_template_kwargs': {'enable_thinking': True}}
                        ).encode(), {'Content-Type': 'application/json'})
                        tail = json.loads(urllib.request.urlopen(req, timeout=30).read())['prompt'][-60:]
                        log(args.out, 'template_tail', model=which, tail=tail)
                t0 = time.monotonic()
                cmd = [sys.executable, str(HERE / 'evalrun.py'), 'eval', '--rows', str(args.rows), '--out', str(dest),
                       '--base-url', f'http://127.0.0.1:{PORT}/v1', '--model', which, '--workers', '1',
                       '--label', name, '--bandit', args.bandit, '--resume', *flags]
                r = subprocess.run(cmd, capture_output=True, text=True)
                errs = errors_in(dest / 'items.jsonl')
                log(args.out, 'arm_pass', arm=name, attempt=attempt, rc=r.returncode, errors=errs,
                    seconds=round(time.monotonic() - t0, 1), stderr=r.stderr[-400:] if r.returncode else '')
                if r.returncode == 0 and errs == 0:
                    break
        table = {}
        for name, _, _ in ARMS:
            sp = args.out / name / 'summary.json'
            if sp.exists():
                sm = json.loads(sp.read_text())
                rows = [json.loads(x) for x in (args.out / name / 'items.jsonl').read_text().splitlines() if x.strip()]
                reason_s = sum(r.get('reason_s') or 0 for r in rows)
                table[name] = {'n': sm['n'], 'score': sm['score'],
                               'by_task': {t: f"{v['correct']}/{v['n']}" for t, v in sm['by_task'].items()},
                               'paired_detection': sm.get('paired_detection'), 'fpr': sm.get('false_positive_rate'),
                               'answer_tokens': sm.get('completion_tokens'), 'relay': sm.get('relay'),
                               'seconds_per_item': round((sum(r['latency_s'] for r in rows) + reason_s) / max(1, len(rows)), 1),
                               'reruns': sum(r.get('retries') or 0 for r in rows), 'cut_off': sm.get('finish_length')}
        (args.out / 'table.json').write_text(json.dumps(table, indent=1))
        log(args.out, 'bench_done', arms=list(table))
    finally:
        server.stop()
        subprocess.run(['systemctl', '--user', 'start', 'forge-teacher-server'])
        log(args.out, 'restarted_own_teacher', unit='forge-teacher-server')
    return 0


if __name__ == '__main__':
    sys.exit(main())
