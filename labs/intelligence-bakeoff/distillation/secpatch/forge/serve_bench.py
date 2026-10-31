"""Serving benchmark on Slink: accuracy and speed of one model under different llama.cpp serving configurations.

Built for Qwythos-9B-v2 (a Qwen3.5-9B fine-tune whose MTP head is intact). It fits entirely on the 2070's 8 GB, so
the questions are low-level:
  * how it scores on the secpatch held-out set (thinking off; root_cause with thinking),
  * what each decode trick buys: MTP self-speculation, a same-vocabulary Qwen3.5-0.8B drafter, n-gram drafting, and
    q8_0 KV cache. Greedy speculative decoding must not change answers, so output agreement is checked against the
    plain configuration.
Every arm restarts the server with its own flags. GPU gating, crash restart and resume come from relay_bench.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import relay_bench as rb  # noqa: E402

HOME = pathlib.Path.home()
Q = HOME / '.local/state/haven-forge/models/qwythos'
MODEL = Q / 'gguf/Qwythos-9B-v2-MTP-Q4_K_M.gguf'
DRAFT = Q / 'draft/Qwen3.5-0.8B-Q8_0.gguf'
BASE = ['--n-gpu-layers', '999', '--device', 'CUDA0', '--ctx-size', '16384', '--parallel', '1', '--threads', '12',
        '--threads-batch', '12', '--flash-attn', 'auto', '--jinja', '--batch-size', '2048', '--ubatch-size', '2048']
KV16 = ['--cache-type-k', 'f16', '--cache-type-v', 'f16']
ARMS = [  # name, rows key, extra server flags, evalrun flags
    ('Q_heldout', 'heldout', KV16, []),
    ('Q_think_rc', 'heldout', KV16, ['--think', '7680', '--tasks', 'root_cause']),
    ('S_none', 'subset', KV16, []),
    ('S_mtp', 'subset', KV16 + ['--spec-type', 'draft-mtp'], []),
    ('S_draft08', 'subset', KV16 + ['--spec-type', 'draft-simple', '--model-draft', str(DRAFT), '--n-gpu-layers-draft', '999'], []),
    ('S_ngram', 'subset', KV16 + ['--spec-type', 'ngram-simple'], []),
    ('S_kvq8', 'subset', ['--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0'], []),
    ('T_mtp_rc', 'heldout', KV16 + ['--spec-type', 'draft-mtp'], ['--think', '7680', '--tasks', 'root_cause']),
]


def start(out: pathlib.Path, flags: list[str]):
    env = {**__import__('os').environ, 'LD_LIBRARY_PATH': str(rb.ENGINE)}
    cmd = [str(rb.ENGINE / 'llama-server'), '-m', str(MODEL), '--host', '127.0.0.1', '--port', str(rb.PORT),
           '--alias', 'qwythos', *BASE, *flags]
    proc = subprocess.Popen(cmd, stdout=open(out / 'server.log', 'a'), stderr=subprocess.STDOUT, env=env)
    for _ in range(600):
        if rb.healthy():
            return proc
        if proc.poll() is not None:
            raise RuntimeError(f'server exited {proc.returncode}: {" ".join(flags)}')
        time.sleep(2)
    raise RuntimeError('server not healthy')


def stop(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--heldout', type=pathlib.Path, required=True)
    ap.add_argument('--subset', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--arms', default=','.join(a[0] for a in ARMS))
    ap.add_argument('--wait-units', default='')
    ap.add_argument('--wait-gpu-hours', type=float, default=10)
    ap.add_argument('--bandit', default=str(HOME / '.local/share/haven-forge-venv/bin/bandit'))
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    rows = {'heldout': args.heldout, 'subset': args.subset}
    wanted = set(args.arms.split(','))
    # Same gating as relay_bench: other sessions' units finish first, then this session's own teacher is stopped.
    units = [u for u in args.wait_units.split(',') if u]
    teacher = lambda: subprocess.run(['systemctl', '--user', 'show', '-p', 'MainPID', '--value', 'forge-teacher-server'],
                                     capture_output=True, text=True).stdout.strip()
    busy = lambda: [u for u in units if subprocess.run(['systemctl', '--user', 'is-active', u], capture_output=True,
                                                       text=True).stdout.strip() in ('active', 'activating')]
    deadline = time.time() + args.wait_gpu_hours * 3600
    while busy() or rb.gpu_pids() - {teacher(), '0', ''}:
        if time.time() > deadline:
            rb.log(args.out, 'gpu_busy_gave_up', units=busy(), pids=sorted(rb.gpu_pids()))
            return 1
        time.sleep(60)
    subprocess.run(['systemctl', '--user', 'stop', 'forge-teacher-server'])
    rb.log(args.out, 'stopped_own_teacher', unit='forge-teacher-server')
    time.sleep(5)
    try:
        for name, key, sflags, eflags in ARMS:
            if name not in wanted:
                continue
            dest = args.out / name
            for attempt in range(4):
                proc = None
                try:
                    proc = start(args.out, sflags)
                    rb.log(args.out, 'server_up', arm=name, flags=sflags, attempt=attempt)
                    t0 = time.monotonic()
                    r = subprocess.run([sys.executable, str(HERE / 'evalrun.py'), 'eval', '--rows', str(rows[key]),
                                        '--out', str(dest), '--base-url', f'http://127.0.0.1:{rb.PORT}/v1',
                                        '--model', 'qwythos', '--workers', '1', '--label', name, '--bandit', args.bandit,
                                        '--resume', *eflags], capture_output=True, text=True)
                    errs = rb.errors_in(dest / 'items.jsonl')
                    rb.log(args.out, 'arm_pass', arm=name, attempt=attempt, rc=r.returncode, errors=errs,
                           seconds=round(time.monotonic() - t0, 1), stderr=r.stderr[-400:] if r.returncode else '')
                    if r.returncode == 0 and errs == 0:
                        break
                except Exception as exc:  # a configuration the engine rejects is recorded, not fatal
                    rb.log(args.out, 'arm_error', arm=name, attempt=attempt, error=str(exc)[:400])
                    if 'exited' in str(exc):
                        break
                finally:
                    stop(proc)
        table, ref = {}, {}
        ref_path = args.out / 'S_none' / 'items.jsonl'
        if ref_path.exists():
            ref = {json.loads(x)['id']: json.loads(x)['output'] for x in ref_path.read_text().splitlines() if x.strip()}
        for name, *_ in ARMS:
            sp = args.out / name / 'summary.json'
            if not sp.exists():
                continue
            sm = json.loads(sp.read_text())
            items = [json.loads(x) for x in (args.out / name / 'items.jsonl').read_text().splitlines() if x.strip()]
            tok = sum(r.get('completion_tokens') or 0 for r in items)
            secs = sum(r['latency_s'] for r in items)
            same = sum(1 for r in items if r['id'] in ref and ref[r['id']] == r['output']) if name.startswith('S_') else None
            table[name] = {'n': sm['n'], 'score': sm['score'], 'by_task': {t: f"{v['correct']}/{v['n']}" for t, v in sm['by_task'].items()},
                           'paired_detection': sm.get('paired_detection'), 'fpr': sm.get('false_positive_rate'),
                           'tokens': tok, 'seconds': round(secs, 1), 'tok_per_s_end_to_end': round(tok / max(secs, 1e-9), 1),
                           's_per_item': round(secs / max(1, len(items)), 2), 'cut_off': sm.get('finish_length'),
                           'outputs_identical_to_S_none': same}
        table['_conditions'] = {'model': MODEL.name, 'engine': 'llama.cpp b11146', 'threads': 12, 'batch_ubatch': 2048,
                                'note': 'tok/s is end-to-end per request (prefill + decode), single slot, 2070 SUPER'}
        (args.out / 'table.json').write_text(json.dumps(table, indent=1))
        rb.log(args.out, 'bench_done', arms=[a for a in table if not a.startswith('_')])
    finally:
        subprocess.run(['systemctl', '--user', 'start', 'forge-teacher-server'])
        rb.log(args.out, 'restarted_own_teacher', unit='forge-teacher-server')
    return 0


if __name__ == '__main__':
    sys.exit(main())
