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
    # Kaggle packages evaluate.py beside forge/; the repo and Slink keep it in secpatch/.
    path = next(p for p in (HERE.parent / 'evaluate.py', HERE.parent / 'secpatch' / 'evaluate.py') if p.exists())
    spec = importlib.util.spec_from_file_location('secpatch_evaluate', path)
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


def _post(url: str, body: dict, timeout: int = 1800) -> dict:
    import urllib.request
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


THINK = re.compile(r'<think>(.*?)(?:</think>|$)', re.S)


def relay_generator(args):
    """Thought relay: the reasoner thinks (its answer is discarded), the answer model writes the final answer.

    style=think: the reasoning is placed in the answer model's own reasoning slot, built from its chat template
    (/apply-template with thinking on), so it continues as if it had thought it. style=notes: the reasoning is
    appended to the prompt as a colleague's notes and the answer model answers with thinking off.
    """
    abase = args.base_url.rstrip('/')
    aroot = re.sub(r'/v1$', '', abase)
    stored = {}
    if args.reasoning_from:  # two-stage relay: no co-hosting, clean per-stage timings
        for line in args.reasoning_from.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if not r.get('error'):
                    stored[r['id']] = r

    def gen(item, max_new, temperature, seed):
        messages = item['messages']
        t0 = time.monotonic()
        if stored:
            r = stored.get(item['id'])
            if r is None:
                raise KeyError(f'no stored reasoning for {item["id"]}')
            reasoning, rtok, rfin = r.get('reasoning') or '', r.get('completion_tokens'), r.get('finish')
            rs = r.get('latency_s') or 0
        else:
            d = _post(args.reason_url.rstrip('/') + '/chat/completions',
                      {'model': args.reason_model, 'messages': messages, 'temperature': temperature,
                       'max_tokens': args.reason_budget + max_new, 'seed': seed,
                       'chat_template_kwargs': {'enable_thinking': True}})
            m, rfin = d['choices'][0]['message'], d['choices'][0].get('finish_reason')
            reasoning = (m.get('reasoning_content') or '').strip()
            if not reasoning:
                hit = THINK.search(m.get('content') or '')
                reasoning = hit.group(1).strip() if hit else ''
            rtok, rs = (d.get('usage') or {}).get('completion_tokens'), time.monotonic() - t0
        t1 = time.monotonic()
        if args.relay_style == 'think':
            prompt = _post(aroot + '/apply-template', {'messages': messages,
                                                       'chat_template_kwargs': {'enable_thinking': True}})['prompt']
            if not prompt.rstrip().endswith('<think>'):
                prompt += '<think>'
            prompt += '\n' + reasoning + '\n</think>\n\n'
            c = _post(aroot + '/completion', {'prompt': prompt, 'n_predict': max_new, 'temperature': temperature,
                                              'seed': seed, 'cache_prompt': True, **sampling(args)})
            text, atok = c.get('content') or '', c.get('tokens_predicted')
            afin = 'length' if c.get('stop_type') == 'limit' or c.get('truncated') else 'stop'
        else:
            msgs = [dict(x) for x in messages]
            msgs[-1]['content'] += '\n\nAnalysis notes from a colleague (may be wrong; check them against the code):\n' + reasoning
            a = _post(abase + '/chat/completions', {'model': args.model, 'messages': msgs, 'temperature': temperature,
                                                    'max_tokens': max_new, 'seed': seed,
                                                    'chat_template_kwargs': {'enable_thinking': False}, **sampling(args)})
            text, atok = a['choices'][0]['message'].get('content') or '', (a.get('usage') or {}).get('completion_tokens')
            afin = a['choices'][0].get('finish_reason')
        return text, atok, afin, {'reason_tokens': rtok, 'reason_s': round(rs, 3), 'answer_s': round(time.monotonic() - t1, 3),
                                  'reason_finish': rfin, 'reason_chars': len(reasoning)}
    gen.wants_item = True
    return gen


def sampling(args) -> dict:
    if getattr(args, 'sampling', 'greedy') == 'liquid':
        return {'temperature': 0.1, 'top_p': 0.1, 'top_k': 50, 'repeat_penalty': 1.05}
    return {}


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
    ap.add_argument('--reason-url', help='relay: a second model writes the reasoning; --base-url model answers')
    ap.add_argument('--reason-model', default='reasoner')
    ap.add_argument('--reason-budget', type=int, default=4096)
    ap.add_argument('--reasoning-from', type=pathlib.Path,
                    help='relay stage 2: inject reasoning stored by an earlier --think --keep-reasoning run (by row id)')
    ap.add_argument('--keep-reasoning', action='store_true', help='store each row\'s reasoning (relay stage 1)')
    ap.add_argument('--sampling', choices=('greedy', 'liquid'), default='greedy',
                    help='liquid: LFM2.5 recommended sampling (temp 0.1, top_p 0.1, top_k 50, repeat_penalty 1.05)')
    ap.add_argument('--resume', action='store_true', help='keep error-free rows already in --out and run the rest')
    ap.add_argument('--relay-style', choices=('think', 'notes'), default='think',
                    help='think: reasoning goes into the answer model\'s own think slot; notes: into the prompt')
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
    if args.reason_url or args.reasoning_from:
        gen = relay_generator(args)
    elif args.think:  # reasoning mode: the answer is graded, reasoning (reasoning_content or <think>) is not
        import urllib.request

        def gen(messages, max_new, temperature, seed, _base=args.base_url.rstrip('/'), _model=args.model):
            body = {'model': _model, 'messages': messages, 'max_tokens': max_new + args.think,
                    'temperature': temperature, 'seed': seed, 'chat_template_kwargs': {'enable_thinking': True},
                    **sampling(args)}
            req = urllib.request.Request(_base + '/chat/completions', json.dumps(body).encode(),
                                         {'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=1800) as r:
                data = json.loads(r.read())
            ch = data['choices'][0]
            content = ch['message'].get('content') or ''
            reasoning = (ch['message'].get('reasoning_content') or '').strip()
            if not reasoning:
                hit = THINK.search(content)
                reasoning = hit.group(1).strip() if hit else ''
            extra = {'reasoning': reasoning} if args.keep_reasoning else {}
            extra['reasoning_chars'] = len(reasoning)
            return content, (data.get('usage') or {}).get('completion_tokens'), ch.get('finish_reason'), extra
        gen.name = args.model
    args.out.mkdir(parents=True, exist_ok=True)
    lock, results = threading.Lock(), []
    done = {}
    if args.resume and (args.out / 'items.jsonl').exists():  # keep error-free rows; re-run errors and missing rows
        for line in (args.out / 'items.jsonl').read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                if not r.get('error'):
                    done[(r['id'], r.get('seed', 0))] = r
        results.extend(done.values())
    sink = (args.out / 'items.jsonl').open('w', encoding='utf-8')
    for r in done.values():
        sink.write(json.dumps(r, ensure_ascii=False) + '\n')
    accepted = (args.out / 'selfplay-sft.jsonl').open('w', encoding='utf-8') if args.mode == 'selfplay' else None
    pairs = (args.out / 'selfplay-pairs.jsonl').open('w', encoding='utf-8') if args.mode == 'selfplay' else None
    raw = {r['id']: r for r in rows}

    def work(item):
        if args.deadline and time.monotonic() - started > args.deadline:
            return
        outs = []
        for seed in range(args.samples):
            if (item['id'], seed) in done:
                continue
            t0 = time.monotonic()
            # Transport failures (timeouts, a restarting server) are retried twice, and the retries are recorded:
            # the promotion gate fails closed on any remaining error, so one network hiccup must not void a cycle.
            retries = 0
            while True:
                try:
                    out = (gen(item, ev.MAX_NEW[item['task']], args.temperature, seed) if getattr(gen, 'wants_item', False)
                           else gen(item['messages'], ev.MAX_NEW[item['task']], args.temperature, seed))
                    text, ntok = out[0], out[1]
                    finish = out[2] if len(out) > 2 else None  # 'length' = cut off by the budget, not answered wrong
                    extra = out[3] if len(out) > 3 else {}
                    err = None
                    break
                except Exception as exc:
                    if retries < 2:
                        retries += 1
                        time.sleep(10 * retries)
                        continue
                    text, ntok, err, finish, extra = '', 0, f'{type(exc).__name__}: {str(exc)[:200]}', None, {}
                    break
            row = {'id': item['id'], 'key': item['key'], 'task': item['task'], 'label': item['label'], 'seed': seed,
                   'latency_s': round(time.monotonic() - t0, 3), 'completion_tokens': ntok, 'error': err,
                   'finish': finish, 'retries': retries, **extra,
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
    if args.reason_url or args.reasoning_from:
        summary['relay'] = {'reason_url': args.reason_url, 'reasoning_from': str(args.reasoning_from or ''),
                            'reason_model': args.reason_model, 'style': args.relay_style,
                            'reason_budget': args.reason_budget,
                            'reason_tokens': sum(r.get('reason_tokens') or 0 for r in results),
                            'answer_tokens': sum(r.get('completion_tokens') or 0 for r in results),
                            'reason_seconds': round(sum(r.get('reason_s') or 0 for r in results), 1),
                            'answer_seconds': round(sum(r.get('answer_s') or 0 for r in results), 1),
                            'reasoning_cut_off': sum(1 for r in results if r.get('reason_finish') == 'length')}
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
