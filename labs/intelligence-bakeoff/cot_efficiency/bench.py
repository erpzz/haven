"""Chain-of-thought cost on Slink: lossless runtime levers for the CPU-MoE 35B, measured.

Each arm starts its own loopback llama-server, sends the same reasoning-on prompts at
temperature 0, records server timings and draft acceptance, and stops the server.
Speed is the only thing an arm may change: every output is compared token-for-token
(text identity) with the baseline arm A0. Arms and thresholds are fixed in
PREREGISTRATION.json before any run.

Usage (on Slink, in an approved GPU window; refuses unknown GPU processes):
  python3 bench.py --prereg PREREGISTRATION.json --prompts prompts.jsonl --out <dir> \
      --allow-gpu-pid <pid> ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import secrets
import socket
import subprocess
import threading
import time
import urllib.request

ENGINE = pathlib.Path.home() / '.local/share/haven-model-lab/engines/b11146/llama-b11146'


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def gpu_pids() -> set[int]:
    out = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'],
                         capture_output=True, text=True, timeout=10).stdout
    return {int(x) for x in out.split() if x.strip().isdigit()}


def gpu_used_mib() -> int | None:
    out = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                         capture_output=True, text=True, timeout=10).stdout.strip()
    return int(out.split()[0]) if out else None


class Server:
    def __init__(self, model: str, args: list[str], workdir: pathlib.Path):
        self.port, self.key = free_port(), secrets.token_urlsafe(24)
        keyfile = workdir / 'key'
        keyfile.write_text(self.key)
        keyfile.chmod(0o600)
        self.log = (workdir / 'server.log').open('w')
        argv = [str(ENGINE / 'llama-server'), '--model', model, '--host', '127.0.0.1', '--port', str(self.port),
                '--api-key-file', str(keyfile), '--alias', 'bench', '--jinja', '--metrics', '--no-webui', *args]
        env = {**os.environ, 'LD_LIBRARY_PATH': str(ENGINE)}
        self.argv = argv
        self.proc = subprocess.Popen(argv, stdout=self.log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        self.peak_vram = 0
        self._stop = threading.Event()
        threading.Thread(target=self._sample, daemon=True).start()

    def _sample(self):
        while not self._stop.wait(1.0):
            used = gpu_used_mib()
            if used:
                self.peak_vram = max(self.peak_vram, used)

    def call(self, path: str, body: dict | None = None, timeout: float = 900):
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=json.dumps(body).encode() if body else None,
                                     headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def wait_ready(self, deadline_s: float) -> float:
        start = time.monotonic()
        while time.monotonic() - start < deadline_s:
            if self.proc.poll() is not None:
                raise RuntimeError(f'llama-server exited with {self.proc.returncode}; see server.log')
            try:
                if self.call('/v1/models', timeout=2).get('data'):
                    return time.monotonic() - start
            except OSError:
                pass
            time.sleep(1)
        raise TimeoutError('server not ready')

    def rss_mib(self) -> int | None:
        try:
            return int(next(l for l in pathlib.Path(f'/proc/{self.proc.pid}/status').read_text().splitlines()
                            if l.startswith('VmRSS')).split()[1]) // 1024
        except (OSError, StopIteration):
            return None

    def stop(self):
        self._stop.set()
        if self.proc.poll() is None:
            os.killpg(self.proc.pid, 15)
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, 9)
        self.log.close()


def run_arm(arm: dict, prompts: list[dict], out: pathlib.Path, params: dict) -> dict:
    work = out / arm['id']
    work.mkdir(parents=True, exist_ok=True)
    srv = Server(arm['model'], arm['args'], work)
    rows = []
    try:
        load_s = srv.wait_ready(params['ready_deadline_s'])
        thinking = arm.get('thinking', True)
        for p in prompts:
            started = time.monotonic()
            body = {'model': 'bench', 'messages': p['messages'], 'temperature': 0, 'seed': 7, 'top_k': 1,
                    'max_tokens': arm.get('max_tokens', params['max_tokens']),
                    'chat_template_kwargs': {'enable_thinking': thinking}, 'cache_prompt': True}
            r = srv.call('/v1/chat/completions', body)
            msg = r['choices'][0]['message']
            reasoning, answer = msg.get('reasoning_content') or '', msg.get('content') or ''
            text = reasoning + '\n<<answer>>\n' + answer
            t = r.get('timings') or {}
            row = {'arm': arm['id'], 'prompt': p['id'], 'wall_s': round(time.monotonic() - started, 3),
                   'predicted_n': t.get('predicted_n'), 'decode_tps': t.get('predicted_per_second'),
                   'prompt_n': t.get('prompt_n'), 'prefill_tps': t.get('prompt_per_second'),
                   'draft_n': t.get('draft_n'), 'draft_accepted': t.get('draft_n_accepted'),
                   'finish': r['choices'][0].get('finish_reason'), 'reasoning_chars': len(reasoning),
                   'answer': answer[:16000], 'sha256': hashlib.sha256(text.encode()).hexdigest(), 'chars': len(text)}
            # Turn 2: a short follow-up in the same conversation. With prompt caching the server should
            # re-read only the new tokens; prompt_n shows how much it actually processed.
            follow = {**body, 'max_tokens': 64, 'messages': p['messages'] + [
                {'role': 'assistant', 'content': answer}, {'role': 'user', 'content': params['followup']}]}
            t2 = time.monotonic()
            r2 = srv.call('/v1/chat/completions', follow)
            tt = r2.get('timings') or {}
            row.update(followup_wall_s=round(time.monotonic() - t2, 3), followup_prompt_n=tt.get('prompt_n'),
                       followup_prefill_ms=tt.get('prompt_ms'), followup_cache_n=tt.get('cache_n'))
            rows.append(row)
        summary = {'arm': arm['id'], 'status': 'OK', 'load_s': round(load_s, 1), 'peak_vram_mib': srv.peak_vram,
                   'rss_mib': srv.rss_mib()}
    except Exception as exc:  # recorded, never hidden; the next arm still runs
        summary = {'arm': arm['id'], 'status': 'FAILED', 'error': f'{type(exc).__name__}: {str(exc)[:300]}',
                   'peak_vram_mib': srv.peak_vram}
    finally:
        srv.stop()
    summary['argv'] = srv.argv
    with (work / 'rows.jsonl').open('w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    (work / 'summary.json').write_text(json.dumps(summary, indent=1))
    return {**summary, 'rows': rows}


def compare(results: list[dict], baseline: str) -> list[dict]:
    base = {r['prompt']: r for res in results if res['arm'] == baseline for r in res['rows']}
    table = []
    for res in results:
        rows = res['rows']
        tokens = sum(r['predicted_n'] or 0 for r in rows)
        wall = sum(r['wall_s'] for r in rows)
        drafted = sum(r['draft_n'] or 0 for r in rows)
        accepted = sum(r['draft_accepted'] or 0 for r in rows)
        same = sum(1 for r in rows if base.get(r['prompt'], {}).get('sha256') == r['sha256'])
        decode = sorted(r['decode_tps'] for r in rows if r['decode_tps'])
        table.append({'arm': res['arm'], 'status': res['status'], 'prompts': len(rows), 'tokens': tokens,
                      'wall_s': round(wall, 1), 'tokens_per_wall_s': round(tokens / wall, 2) if wall else None,
                      'median_decode_tps': decode[len(decode) // 2] if decode else None,
                      'draft_acceptance': round(accepted / drafted, 3) if drafted else None,
                      'identical_to_baseline': f'{same}/{len(rows)}', 'load_s': res.get('load_s'),
                      'peak_vram_mib': res.get('peak_vram_mib'), 'rss_mib': res.get('rss_mib'),
                      'error': res.get('error')})
    b = next((t for t in table if t['arm'] == baseline), None)
    for t in table:
        t['speedup_vs_baseline'] = round(t['tokens_per_wall_s'] / b['tokens_per_wall_s'], 3) \
            if b and b.get('tokens_per_wall_s') and t.get('tokens_per_wall_s') else None
    return table


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prereg', type=pathlib.Path, required=True)
    ap.add_argument('--prompts', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--allow-gpu-pid', type=int, action='append', default=[])
    ap.add_argument('--arms', help='Comma-separated subset of preregistered arm ids.')
    args = ap.parse_args(argv)
    prereg = json.loads(args.prereg.read_text())
    unknown = gpu_pids() - set(args.allow_gpu_pid)
    if unknown:
        raise SystemExit(f'Refusing: GPU in use by {sorted(unknown)}. Nothing was stopped.')
    prompts = [json.loads(x) for x in args.prompts.read_text().splitlines() if x.strip()]
    arms = [a for a in prereg['arms'] if not args.arms or a['id'] in args.arms.split(',')]
    models = prereg['models']
    for a in arms:
        a['model'] = os.path.expanduser(models[a['model']])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'run.json').write_text(json.dumps({'started_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                                   'prereg_sha256': hashlib.sha256(args.prereg.read_bytes()).hexdigest(),
                                                   'prompts_sha256': hashlib.sha256(args.prompts.read_bytes()).hexdigest(),
                                                   'allowed_gpu_pids': args.allow_gpu_pid}, indent=1))
    results = []
    for arm in arms:
        if not pathlib.Path(arm['model']).exists():
            results.append({'arm': arm['id'], 'status': 'SKIPPED_MODEL_MISSING', 'rows': []})
            continue
        results.append(run_arm(arm, prompts, args.out, prereg['params']))
        print(json.dumps({k: v for k, v in results[-1].items() if k not in ('rows', 'argv')}), flush=True)
    table = compare(results, prereg['baseline'])
    (args.out / 'table.json').write_text(json.dumps(table, indent=1))
    for t in table:
        print(json.dumps(t))


if __name__ == '__main__':
    main()
