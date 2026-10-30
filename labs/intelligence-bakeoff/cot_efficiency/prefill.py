"""PREFILL-1: how fast does the production 35B read a long prompt, by batch/microbatch size?

Real Open WebUI requests on Slink spend most of their time reading the prompt (engine.log: 91 s prompt vs 8 s
decode over 5 requests; first message of a chat 26-117 s to first token at ~87 tok/s). With experts in system RAM
(--cpu-moe), llama.cpp can run large prompt batches on the GPU by streaming expert weights over PCIe; the
production microbatch of 128 may be below where that pays. Each configuration gets its own loopback server with
production arguments except --batch-size/--ubatch-size; prompts are real secpatch items concatenated to chat-like
lengths; cache_prompt is off so every request reads its whole prompt; decode is greedy and capped.

Outputs per config: prompt tok/s per length, decode tok/s, peak VRAM, and whether the greedy answer text equals the
production config's (microbatch size changes summation order, so small differences are possible and are reported).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench  # noqa: E402


def with_ubatch(args: list[str], batch: int, ubatch: int) -> list[str]:
    out, skip = [], False
    for i, a in enumerate(args):
        if skip:
            skip = False
            continue
        if a in ('--batch-size', '--ubatch-size'):
            skip = True
            continue
        out.append(a)
    return out + ['--batch-size', str(batch), '--ubatch-size', str(ubatch)]


def build_prompts(items_path: pathlib.Path, targets: list[int]) -> list[dict]:
    """Chat-like prompts of roughly each target length (4 chars/token estimate), from real item text."""
    rows = [json.loads(x) for x in items_path.read_text().splitlines() if x.strip()]
    texts = [r['item']['messages'][-1]['content'] for r in rows if r.get('kind') == 'secpatch']
    prompts = []
    for t in targets:
        body, i = [], 0
        while sum(len(b) for b in body) < t * 4 and i < len(texts):
            body.append(texts[i])
            i += 1
        prompts.append({'target': t, 'messages': [
            {'role': 'system', 'content': 'You are Haven, a careful security engineering assistant.'},
            {'role': 'user', 'content': '\n\n---\n\n'.join(body) + '\n\nIn two sentences, which of the code above is most at risk and why?'}]})
    return prompts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prereg', required=True)
    ap.add_argument('--items', required=True, help='a COT-EFF set file with secpatch items')
    ap.add_argument('--configs', default='256/128,512/512,1024/1024,2048/2048', help='batch/ubatch pairs; the first is the reference')
    ap.add_argument('--lengths', default='2000,5500,7500')
    ap.add_argument('--repeats', type=int, default=2)
    ap.add_argument('--out', required=True)
    ap.add_argument('--allow-gpu-pid', type=int, action='append', default=[])
    args = ap.parse_args(argv)
    prereg = json.loads(pathlib.Path(args.prereg).read_text())
    unknown = bench.gpu_pids() - set(args.allow_gpu_pid)
    if unknown:
        raise SystemExit(f'Refusing: GPU in use by {sorted(unknown)}. Nothing was stopped.')
    model = str(pathlib.Path(prereg['models']['q35']).expanduser())
    prompts = build_prompts(pathlib.Path(args.items), [int(x) for x in args.lengths.split(',')])
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results, reference = [], {}
    for cfg in args.configs.split(','):
        batch, ubatch = map(int, cfg.split('/'))
        work = out / f'b{batch}-u{ubatch}'
        work.mkdir(exist_ok=True)
        srv = bench.Server(model, with_ubatch(prereg['server_args']['moe'], batch, ubatch), work)
        row = {'batch': batch, 'ubatch': ubatch, 'runs': []}
        try:
            row['load_s'] = round(srv.wait_ready(prereg['ready_deadline_s']), 1)
            for p in prompts:
                for rep in range(args.repeats):
                    t0 = time.monotonic()
                    r = srv.call('/v1/chat/completions', {'model': 'bench', 'messages': p['messages'], 'max_tokens': 64,
                                                          'temperature': 0, 'cache_prompt': False,
                                                          'chat_template_kwargs': {'enable_thinking': False}}, timeout=1800)
                    tm = r.get('timings') or {}
                    text = r['choices'][0]['message'].get('content') or ''
                    if cfg == args.configs.split(',')[0] and rep == 0:
                        reference[p['target']] = text
                    row['runs'].append({'target': p['target'], 'rep': rep, 'prompt_n': tm.get('prompt_n'),
                                        'prompt_s': round((tm.get('prompt_ms') or 0) / 1000, 3),
                                        'prompt_tps': round(tm.get('prompt_per_second') or 0, 1),
                                        'decode_tps': round(tm.get('predicted_per_second') or 0, 1),
                                        'wall_s': round(time.monotonic() - t0, 3),
                                        'same_text_as_reference': text == reference.get(p['target'])})
                    print(json.dumps({'cfg': cfg, **row['runs'][-1]}), flush=True)
        except Exception as exc:  # an OOM or crash is a result for this config, not a reason to stop the sweep
            row['error'] = f'{type(exc).__name__}: {str(exc)[:300]}'
            print(json.dumps({'cfg': cfg, 'error': row['error']}), flush=True)
        finally:
            srv.stop()
        row['peak_vram_mib'] = srv.peak_vram
        results.append(row)
    (out / 'prefill.json').write_text(json.dumps({'model': model, 'results': results}, indent=1) + '\n')


if __name__ == '__main__':
    main()
