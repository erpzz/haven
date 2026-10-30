"""Automated critic: a blind second read of every teacher trace, so review continues when no person is watching.

The rule-based checks in teach.py catch leaks and ungrounded citations, but not analyses that are plausible
and wrong ("a try/except around open() prevents path traversal"). Manual review found that failure; this
script makes it routine. The critic gets exactly the student's view (the task prompt with its code, and no
reference, label or other version) plus the trace's analysis. It judges whether every claim is supported by
the code and the security reasoning is sound. A trace it rejects is dropped by mix.py like a reviewer drop.

The critic is told the established verdict and never re-decides it (a blind critic disputed correct labels on
subtle bugs and rejected 65% of traces in its first calibration); it only checks the explanation.

Output: one JSON line per trace, {"key": "<id>:<hash12>", "sound": bool, "problem": str}; resumable.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import pathlib
import sys
import threading

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import teach  # noqa: E402
from mix import trace_key  # noqa: E402

SYSTEM = ('You are a strict senior application-security reviewer checking a junior reviewer\'s written explanation. '
          'The verdict is already established from the project\'s security history and is correct; never dispute it. '
          'Your only job is to judge whether the explanation is supported by the code shown.')
ASK = ('\n\n---\nEstablished verdict: {verdict}\n{extra}Junior\'s explanation:\n{analysis}\n\n'
       'Answer sound=false ONLY for a clear error: the explanation states something the code shown contradicts '
       '(a wrong identifier, line or control flow), or names a mechanism or guard that plainly does not apply to '
       'this code. Imperfect wording, missing detail or a different emphasis are sound. If unsure, answer sound=true. '
       'Respond with only JSON: {{"sound": true|false, "problem": "<empty if sound, else one sentence>"}}')


def verdict_of(row: dict) -> str:
    task, label = row['task'], row['label']
    gold = teach.target_json(row) or {}
    cwe = ', '.join(gold.get('cwe') or []) or 'unclassified'
    if task == 'detect':
        return (f'the function is VULNERABLE ({cwe}).' if label == 'vulnerable' else
                'the function is NOT vulnerable to the weakness it is reviewed for (it contains the protection).')
    if task == 'finding_support':
        return {'supported': 'the finding IS supported by the code shown.',
                'stale': 'the finding is NOT supported: the code shown already contains the protection.'}.get(
                    label, 'the finding is NOT supported: it cites code that is not shown.')
    if task == 'root_cause':
        return f'the weakness class is {cwe}; both versions are shown above.'
    return 'the original function is vulnerable; the corrected function is shown below.'


def critic_messages(row: dict, analysis: str, target: str = '') -> list[dict]:
    extra = ''
    if row['task'] == 'remediate':  # the explanation describes the fix, so the critic must see the fix
        code = target.split('```python', 1)[-1] if '```python' in target else ''
        extra = 'Corrected function (recorded):\n```python' + code + '\n'
    ask = ASK.format(verdict=verdict_of(row), extra=extra, analysis=analysis)
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': row['messages'][-2]['content'] + ask}]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pool', type=pathlib.Path, required=True, help='recorded pool rows (pool.jsonl)')
    ap.add_argument('--traces', type=pathlib.Path, nargs='+', required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--base-url', required=True)
    ap.add_argument('--model', default='teacher')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--think', action='store_true', help='critic reasons before judging (slower, stronger)')
    ap.add_argument('--deadline', type=float, default=0)
    ap.add_argument('--keys', nargs='*', default=[], help='only these id:hash12 traces (calibration)')
    args = ap.parse_args(argv)
    import time
    started = time.monotonic()
    pool = {json.loads(x)['id']: json.loads(x) for x in args.pool.read_text().splitlines() if x.strip()}
    teach.VERSIONS.clear()
    teach.index_versions(list(pool.values()))
    todo, seen = [], set()
    if args.out.exists():
        seen = {json.loads(x)['key'] for x in args.out.read_text().splitlines() if x.strip()}
    for path in args.traces:
        if not path.exists():
            continue
        for x in path.read_text().splitlines():
            rec = json.loads(x) if x.strip() else {}
            if not rec.get('sft') or rec.get('id') not in pool:
                continue
            key = trace_key(rec)
            text = rec['sft']['messages'][-1]['content']
            if (args.keys and key not in args.keys) or key in seen or not teach.verify(pool[rec['id']], text)[0]:
                continue  # judged already, or already failing the rule checks
            seen.add(key)
            todo.append((key, pool[rec['id']], text))
    ep = teach.Endpoint(args.base_url, args.model)
    lock, counts = threading.Lock(), {'sound': 0, 'unsound': 0, 'error': 0}
    print(json.dumps({'todo': len(todo)}), flush=True)

    def work(item):
        if args.deadline and time.monotonic() - started > args.deadline:
            return
        key, row, text = item
        analysis = text.split('```')[0] if row['task'] == 'remediate' else teach.split_answer(text)[0]
        try:
            out, _ = ep(critic_messages(row, analysis.strip(), text), 4000 if args.think else 300, 0.0, 0, args.think)
            _, obj = teach.split_answer(out)
            if obj is None or not isinstance(obj.get('sound'), bool):
                raise ValueError('critic gave no verdict')
            rec = {'key': key, 'sound': obj['sound'], 'problem': str(obj.get('problem', ''))[:300]}
        except Exception as exc:  # no verdict: the trace keeps its rule-based status
            with lock:
                counts['error'] += 1
            return
        with lock:
            counts['sound' if rec['sound'] else 'unsound'] += 1
            with args.out.open('a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            if sum(counts.values()) % 50 == 0:
                print(json.dumps(counts), flush=True)

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, todo))
    print(json.dumps({'finished': True, **counts}), flush=True)


if __name__ == '__main__':
    main()
