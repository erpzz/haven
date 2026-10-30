"""CACHE-1: can a new chat reuse the shared system+tools prefix of the previous chat on the hybrid 35B?

Qwen3.6-35B-A3B has recurrent (linear-attention) layers, so llama-server cannot cut its cache back to an arbitrary
prefix; it resumes only from a saved context checkpoint at or below the common prefix. On Slink the engine log shows
checkpoints only near the end of each prompt (`min spacing = 8192`), so a new chat sharing 539 tokens with the last
one re-read all 5476 (engine.log task 157). This test sends two chats with an identical ~3k-token system+tools prefix
and different first messages, per server configuration, and records how many prompt tokens chat B had to process.
Prompts are synthetic stand-ins (no user data).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench  # noqa: E402
from prefill import with_ubatch  # noqa: E402

TOOL_NAMES = ['read_file', 'list_dir', 'grep', 'run_tests', 'web_search', 'fetch_url', 'haven_status', 'haven_read_note',
              'haven_write_note', 'calendar_list', 'calendar_add', 'shell_readonly', 'bandit_scan', 'osv_lookup',
              'git_log', 'git_diff', 'sysinfo', 'disk_usage', 'net_listeners', 'journal_tail']


def tools() -> list[dict]:
    return [{'type': 'function', 'function': {
        'name': n, 'description': f'{n.replace("_", " ").capitalize()} on the Haven host. Returns structured JSON; '
                                  'never modifies state unless the name says so. ' * 3,
        'parameters': {'type': 'object', 'properties': {
            'path': {'type': 'string', 'description': 'Absolute path or identifier the tool acts on.'},
            'limit': {'type': 'integer', 'description': 'Maximum number of results to return.'},
            'query': {'type': 'string', 'description': 'Free-text query, pattern or filter expression.'}},
            'required': ['path']}}} for n in TOOL_NAMES]


SYSTEM = ('You are Haven, a private household assistant running on the family\'s own hardware. ' * 40 +
          'Follow the household rules, cite tool results, and say when you are unsure.')


def chat(srv, first_message: str) -> dict:
    body = {'model': 'bench', 'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': first_message}],
            'tools': tools(), 'max_tokens': 16, 'temperature': 0, 'cache_prompt': True,
            'chat_template_kwargs': {'enable_thinking': False}}
    t0 = time.monotonic()
    r = srv.call('/v1/chat/completions', body, timeout=900)
    tm = r.get('timings') or {}
    return {'prompt_processed': tm.get('prompt_n'), 'prompt_cached': tm.get('cache_n'),
            'prompt_s': round((tm.get('prompt_ms') or 0) / 1000, 3), 'wall_s': round(time.monotonic() - t0, 3)}


def checkpoint_positions(log: pathlib.Path) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(r'created context checkpoint \d+ of \d+ \(pos_min = (\d+)', log.read_text())]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prereg', required=True)
    ap.add_argument('--configs', default='default,cms512,cms0', help='default | cmsN (--checkpoint-min-step N)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--allow-gpu-pid', type=int, action='append', default=[])
    args = ap.parse_args(argv)
    prereg = json.loads(pathlib.Path(args.prereg).read_text())
    unknown = bench.gpu_pids() - set(args.allow_gpu_pid)
    if unknown:
        raise SystemExit(f'Refusing: GPU in use by {sorted(unknown)}. Nothing was stopped.')
    model = str(pathlib.Path(prereg['models']['q35']).expanduser())
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for cfg in args.configs.split(','):
        extra = [] if cfg == 'default' else ['--checkpoint-min-step', cfg.removeprefix('cms')]
        work = out / cfg
        work.mkdir(exist_ok=True)
        srv = bench.Server(model, with_ubatch(prereg['server_args']['moe'], 2048, 2048) + extra, work)
        row = {'config': cfg, 'extra_args': extra}
        try:
            srv.wait_ready(prereg['ready_deadline_s'])
            row['chat_a'] = chat(srv, 'What is listening on the network right now, and is any of it exposed beyond loopback?')
            row['chat_b'] = chat(srv, 'Summarize yesterday\'s journal warnings for the Open WebUI service.')
            row['chat_b_followup_shape'] = 'new chat: same system+tools, different first message'
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {str(exc)[:300]}'
        finally:
            srv.stop()
        log = next(work.glob('*.log'), None)
        row['checkpoint_positions'] = checkpoint_positions(log) if log else None
        row['peak_vram_mib'] = srv.peak_vram
        print(json.dumps(row), flush=True)
        results.append(row)
    (out / 'cache.json').write_text(json.dumps(results, indent=1) + '\n')


if __name__ == '__main__':
    main()
