"""Concurrent driver around secpatch/evaluate.py's graders, for an OpenAI-compatible server (llama-server).

Two modes, same deterministic graders (no model grades a model):
  eval      eval-format rows (with `grader`); writes items.jsonl + summary.json exactly like evaluate.py
  selfplay  training rows; samples k answers per row, grades them against the recorded target, and writes the
            accepted samples as SFT rows (origin selfplay_verified) plus chosen/rejected pairs for preference
            training. This is the credit-free self-teaching step: the student only learns from its own answers
            that the recorded ground truth confirms.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import pathlib
import re
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent


def _load_evaluator():
    # By path, under its own name: distillation/evaluate.py would shadow a plain `import evaluate`.
    import importlib.util
    spec = importlib.util.spec_from_file_location('secpatch_evaluate', HERE.parent / 'evaluate.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ev = _load_evaluator()  # secpatch/evaluate.py, unchanged


def gold_grader(row: dict) -> dict | None:
    """Grader record for a training row, derived from its recorded target."""
    task, label = row['task'], row['label']
    target = row['messages'][-1]['content']
    g = {'task': task, 'label': label, 'function': row['source'].get('function'), 'cwe': [], 'changed_lines': [],
         'bandit': None}
    if task in ('detect', 'root_cause', 'finding_support'):
        try:
            obj = json.loads(target)
        except ValueError:
            return None
        g['cwe'] = obj.get('cwe') or []
        if task == 'detect' and label == 'vulnerable':
            g['changed_lines'] = obj.get('evidence_lines') or []
        if task == 'finding_support':
            g['cwe'] = []
        return g
    if task == 'remediate':
        m = re.search(r'```python\n(.*?)```', row['messages'][-2]['content'], re.S)
        fixed = ev.code_block(target)
        if not m or not fixed:
            return None
        g['vulnerable'] = '\n'.join(re.sub(r'^\s*\d+ \| ?', '', x) for x in m.group(1).splitlines())
        g['fixed'] = fixed
        return g
    if task == 'tool_select':
        g['bandit'] = {'test_id': label}
        return g
    return None


def as_item(row: dict) -> dict | None:
    if 'grader' in row:
        return row
    g = gold_grader(row)
    if g is None:
        return None
    return {**row, 'messages': row['messages'][:-1], 'grader': g}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=('eval', 'selfplay'))
    ap.add_argument('--rows', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--base-url', required=True)
    ap.add_argument('--model', default='student')
    ap.add_argument('--bandit', default='bandit')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--samples', type=int, default=1)
    ap.add_argument('--temperature', type=float, default=0.0)
    ap.add_argument('--tasks', default='detect,root_cause,finding_support,remediate,tool_select')
    ap.add_argument('--label', default='', help='arm name recorded in the summary')
    ap.add_argument('--limit', type=int, default=0, help='selfplay: rows to sample (deterministic shuffle)')
    ap.add_argument('--deadline', type=float, default=0, help='stop starting new rows after this many seconds')
    ap.add_argument('--think', type=int, default=0, help='reasoning mode on, with this many extra tokens of budget')
    args = ap.parse_args(argv)
    started = time.monotonic()
    tasks = set(args.tasks.split(','))
    rows = [json.loads(x) for x in args.rows.read_text(encoding='utf-8').splitlines() if x.strip()]
    if args.mode == 'selfplay' and any(r.get('split') not in ('train', 'dev') for r in rows):
        raise SystemExit('Self-play samples only training rows.')
    items = [i for i in (as_item(r) for r in rows if r['task'] in tasks) if i is not None]
    if args.limit:  # rotate through the pool across cycles: the order depends on the row ids only
        salt = args.label if args.mode == 'selfplay' else ''  # eval arms must see identical items
        items = sorted(items, key=lambda i: hashlib.sha256((i['id'] + salt).encode()).hexdigest())[:args.limit]
    eval_sha = hashlib.sha256(json.dumps([i['id'] for i in items]).encode()).hexdigest()
    gen = ev.OpenAI(args.base_url, args.model, None)
    if args.think:  # reasoning mode: the answer is graded, reasoning (reasoning_content or <think>) is not
        import urllib.request

        def gen(messages, max_new, temperature, seed, _base=args.base_url.rstrip('/'), _model=args.model):
            body = {'model': _model, 'messages': messages, 'max_tokens': max_new + args.think,
                    'temperature': temperature, 'seed': seed, 'chat_template_kwargs': {'enable_thinking': True}}
            req = urllib.request.Request(_base + '/chat/completions', json.dumps(body).encode(),
                                         {'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=1800) as r:
                data = json.loads(r.read())
            ch = data['choices'][0]
            return (ch['message'].get('content') or '', (data.get('usage') or {}).get('completion_tokens'),
                    ch.get('finish_reason'))
        gen.name = args.model
    args.out.mkdir(parents=True, exist_ok=True)
    lock, results = threading.Lock(), []
    sink = (args.out / 'items.jsonl').open('w', encoding='utf-8')
    accepted = (args.out / 'selfplay-sft.jsonl').open('w', encoding='utf-8') if args.mode == 'selfplay' else None
    pairs = (args.out / 'selfplay-pairs.jsonl').open('w', encoding='utf-8') if args.mode == 'selfplay' else None
    raw = {r['id']: r for r in rows}

    def work(item):
        if args.deadline and time.monotonic() - started > args.deadline:
            return
        outs = []
        for seed in range(args.samples):
            t0 = time.monotonic()
            # Transport failures (timeouts, a restarting server) are retried twice, and the retries are recorded:
            # the promotion gate fails closed on any remaining error, so one network hiccup must not void a cycle.
            retries = 0
            while True:
                try:
                    out = gen(item['messages'], ev.MAX_NEW[item['task']], args.temperature, seed)
                    text, ntok = out[0], out[1]
                    finish = out[2] if len(out) > 2 else None  # 'length' = cut off by the budget, not answered wrong
                    err = None
                    break
                except Exception as exc:
                    if retries < 2:
                        retries += 1
                        time.sleep(10 * retries)
                        continue
                    text, ntok, err, finish = '', 0, f'{type(exc).__name__}: {str(exc)[:200]}', None
                    break
            row = {'id': item['id'], 'key': item['key'], 'task': item['task'], 'label': item['label'], 'seed': seed,
                   'latency_s': round(time.monotonic() - t0, 3), 'completion_tokens': ntok, 'error': err,
                   'finish': finish, 'retries': retries,
                   **ev.grade(item, text, args.bandit), 'output': text[:4000]}
            outs.append(row)
        with lock:
            for row in outs:
                results.append(row)
                sink.write(json.dumps(row, ensure_ascii=False) + '\n')
            if accepted is not None:
                good = [o for o in outs if o['score'] and not o['invalid_json'] and not o.get('unsupported')]
                bad = [o for o in outs if not o['score']]
                src = raw[item['id']]
                for o in good[:1]:
                    sft = {k: src[k] for k in ('id', 'key', 'task', 'label', 'split', 'source')}
                    sft['messages'] = src['messages'][:-1] + [{'role': 'assistant', 'content': o['output']}]
                    sft['origin'] = 'selfplay_verified'
                    accepted.write(json.dumps(sft, ensure_ascii=False) + '\n')
                if good and bad:
                    pairs.write(json.dumps({'id': item['id'], 'task': item['task'], 'prompt': src['messages'][:-1],
                                            'chosen': good[0]['output'], 'rejected': bad[0]['output']},
                                           ensure_ascii=False) + '\n')
            if len(results) % 100 < args.samples:
                print(json.dumps({'graded': len(results), 'of': len(items) * args.samples,
                                  'score_so_far': round(sum(r['score'] for r in results) / len(results), 4)}), flush=True)

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, items))
    sink.close()
    for f in (accepted, pairs):
        if f:
            f.close()
    summary = ev.summarize(results, eval_sha, args.label or args.model)
    summary['think_budget'] = args.think
    summary['finish_length'] = sum(1 for r in results if r.get('finish') == 'length')
    summary.update(eval_file=str(args.rows), seeds=','.join(map(str, range(args.samples))),
                   temperature=args.temperature, backend='openai', arm=args.label, mode=args.mode,
                   classification=('SELFPLAY_ON_TRAIN' if args.mode == 'selfplay' else
                                   'MEASURED_ON_HELD_OUT' if 'heldout' in args.rows.name else 'MEASURED_ON_GATE'))
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps({k: summary[k] for k in ('model', 'n', 'score', 'false_positive_rate', 'detection_recall',
                                              'paired_detection')}))
    return summary


if __name__ == '__main__':
    main()
