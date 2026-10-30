"""COT-EFF-2: real-world time to a correct answer, thinking vs fast paths, on questions no arm was tuned on.

  sets    build the calibration and confirmation sets (secpatch items + adjudicated tool-use episodes)
  run     run preregistered arms over sets; one loopback llama-server per arm, production sampling
  policy  simulate routing policies offline from the per-item rows; pick on calibration, confirm on confirmation

Correctness comes from the existing deterministic graders only: secpatch evaluate.grade and the
adjudicated benchmark's adjudicator. Cost is measured wall time with the model resident (no load time).
Raw rows hold model outputs; keep them in a private directory outside Git.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import random
import re
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'distillation' / 'secpatch'))
import bench  # noqa: E402  (Server, ENGINE)
import evaluate  # noqa: E402  (secpatch grade, parse_json, MAX_NEW)


def _load_adjudicated():
    spec = importlib.util.spec_from_file_location('adj_bench', ROOT / 'adjudicated' / 'bench.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_jsonl(path):
    return [json.loads(x) for x in pathlib.Path(path).read_text().splitlines() if x.strip()]


def write_jsonl(path, rows, mode='w'):
    with pathlib.Path(path).open(mode, encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


# ---------- sets ----------

def pick_secpatch(items, per_task: dict, exclude: set, rng: random.Random) -> list[dict]:
    by = collections.defaultdict(list)
    for it in items:
        if it['id'] not in exclude:
            by[it['task']].append(it)
    out = []
    for task, n in per_task.items():
        pool = sorted(by[task], key=lambda i: i['id'])
        rng.shuffle(pool)
        out += pool[:n] if n >= 0 else pool
    return out


def cmd_sets(args):
    adj = _load_adjudicated()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    exclude = {json.loads(x)['id'] for x in pathlib.Path(args.screen_prompts).read_text().splitlines() if x.strip()} \
        if args.screen_prompts else set()
    rng = random.Random(args.seed)
    cal_sec = pick_secpatch(read_jsonl(args.dev), json.loads(args.cal_per_task), exclude, rng)
    conf_sec = pick_secpatch(read_jsonl(args.heldout), json.loads(args.conf_per_task), set(), rng)
    for f in args.fresh or []:
        conf_sec += read_jsonl(f)
    manifest = {}
    for name, sec, seed, per_family in (('calibration', cal_sec, args.cal_adj_seed, args.cal_per_family),
                                        ('confirmation', conf_sec, args.conf_adj_seed, args.conf_per_family)):
        epi_path = out / f'{name}-episodes.jsonl'
        if not epi_path.exists():
            adj.cmd_fresh(argparse.Namespace(seed=seed, per_family=per_family, out=str(epi_path)))
        rows = [{'kind': 'secpatch', 'id': 's:' + it['id'], 'task': it['task'], 'item': it} for it in sec]
        rows += [{'kind': 'adjudicated', 'id': 'a:' + e['id'], 'task': e['family'], 'episode': e}
                 for e in read_jsonl(epi_path)]
        path = out / f'{name}.jsonl'
        if path.exists():
            raise SystemExit(f'Refusing to overwrite {path}.')
        write_jsonl(path, rows)
        manifest[name] = {'file': path.name, 'sha256': sha(path), 'n': len(rows),
                          'by_kind': dict(collections.Counter(r['kind'] for r in rows)),
                          'secpatch_tasks': dict(collections.Counter(r['task'] for r in rows if r['kind'] == 'secpatch')),
                          'adjudicated_seed': seed}
    manifest.update(written_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    excluded_screen_prompts=len(exclude), selection_seed=args.seed)
    (out / 'sets-manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print(json.dumps(manifest, indent=1))


# ---------- run ----------

def chat(srv, messages, max_tokens, thinking, sampling) -> dict:
    body = {'model': 'bench', 'messages': messages, 'max_tokens': max_tokens, 'cache_prompt': True,
            'chat_template_kwargs': {'enable_thinking': thinking}, **sampling}
    r = srv.call('/v1/chat/completions', body, timeout=1800)
    choice = r['choices'][0]
    return {'content': choice['message'].get('content') or '', 'reasoning': choice['message'].get('reasoning_content') or '',
            'finish': choice.get('finish_reason'), 'tokens': (r.get('usage') or {}).get('completion_tokens')}


def answer_key_secpatch(task: str, text: str):
    """What the answer says, for agreement checks between arms; None when it cannot be compared."""
    if task == 'remediate':
        return None
    obj = evaluate.parse_json(text)
    if obj is None:
        return None
    if task == 'detect':
        return obj.get('verdict')
    if task == 'finding_support':
        return obj.get('supported')
    if task == 'root_cause':
        return tuple(sorted(evaluate.cwe_ids(obj.get('cwe')))) or None
    return None


def answer_key_adjudicated(record: dict):
    """The final claims (value, status) plus the tool names called, read from the model's own output."""
    if not record.get('ok_transport'):
        return None
    text = record.get('answer') or ''
    starts = [m.start() for m in re.finditer(r'\{\s*"claims"', text)]
    start = starts[-1] if starts else -1
    claims = None
    if start >= 0:
        try:
            claims = json.loads(text[start:text.rindex('}') + 1]).get('claims')
        except (ValueError, AttributeError):
            claims = None
    if not isinstance(claims, list):
        return None
    norm = sorted(json.dumps([c.get('value'), c.get('status')], sort_keys=True, default=str)
                  for c in claims if isinstance(c, dict))
    return json.dumps([norm, sorted({t['name'] for t in record.get('trace') or []})])


DRAFT_NOTE = ('\n\nA faster assistant wrote the draft analysis below. It may be wrong. Check every claim against the '
              'code above and give your own answer in the required format.\n<draft>\n{draft}\n</draft>')


def with_draft(messages: list[dict], draft: str) -> list[dict]:
    """Append another model's reasoning to the last user turn, marked as unverified."""
    out = [dict(m) for m in messages]
    last = max(i for i, m in enumerate(out) if m['role'] == 'user')
    out[last]['content'] = out[last]['content'] + DRAFT_NOTE.format(draft=draft.strip())
    return out


def run_secpatch(srv, row, arm, bandit, draft=None):
    """draft: the upstream arm's row for this item when the arm answers from another model's reasoning;
    its wall time is charged to this row, so policy cost stays end-to-end."""
    item = row['item']
    budget = evaluate.MAX_NEW[item['task']] + (arm.get('think_tokens', 0) if arm['thinking'] else 0)
    messages = with_draft(item['messages'], draft.get('reasoning') or '') if draft else item['messages']
    started = time.monotonic()
    try:
        r = chat(srv, messages, budget, arm['thinking'], arm['sampling'])
        err = None
    except Exception as exc:  # recorded, scored wrong, never retried
        r, err = {'content': '', 'reasoning': '', 'finish': None, 'tokens': 0}, f'{type(exc).__name__}: {str(exc)[:200]}'
    wall = time.monotonic() - started
    g = evaluate.grade(item, r['content'], bandit)
    res = {'correct': int(g['score']), 'wall_s': round(wall + (draft['wall_s'] if draft else 0), 3), 'tokens': r['tokens'],
           'finish': r['finish'], 'reasoning_chars': len(r['reasoning']), 'error': err,
           'key': answer_key_secpatch(item['task'], r['content']),
           'output': r['content'][:16000], 'grade': {k: v for k, v in g.items() if k != 'score'}}
    if draft:
        res.update(own_wall_s=round(wall, 3), draft_chars=len(draft.get('reasoning') or ''))
    if arm.get('keep_reasoning'):
        res['reasoning'] = r['reasoning'][:64000]
    return res


def run_adjudicated(srv, row, arm, adj):
    import agent
    backend = agent.OpenAIBackend(f'http://127.0.0.1:{srv.port}/v1', 'bench', srv.key,
                                  temperature=arm['sampling'].get('temperature', 0.0),
                                  max_tokens=arm.get('think_tokens', 512) if arm['thinking'] else arm.get('answer_tokens', 512),
                                  seed=arm['sampling'].get('seed'), thinking=arm['thinking'],
                                  sampling={k: v for k, v in arm['sampling'].items() if k not in ('temperature', 'seed')},
                                  timeout=1800)
    started = time.monotonic()
    record = adj.run(backend, row['episode'])
    wall = time.monotonic() - started
    verdict = adj.adjudicator.adjudicate(row['episode'], record)
    steps = record.get('steps') or []
    return {'correct': int(bool(verdict['pass'])), 'wall_s': round(wall, 3),
            'tokens': sum((s.get('usage') or {}).get('completion_tokens') or 0 for s in steps),
            'finish': [s.get('finish_reason') for s in steps], 'rounds': record.get('rounds'),
            'error': record.get('error'), 'key': answer_key_adjudicated(record),
            'output': (record.get('answer') or '')[:16000], 'trace_names': [t['name'] for t in record.get('trace') or []]}


def cmd_run(args):
    prereg = json.loads(pathlib.Path(args.prereg).read_text())
    unknown = bench.gpu_pids() - set(args.allow_gpu_pid)
    if unknown:
        raise SystemExit(f'Refusing: GPU in use by {sorted(unknown)}. Nothing was stopped.')
    adj = _load_adjudicated()
    sets = {name: read_jsonl(pathlib.Path(args.sets) / f'{name}.jsonl') for name in args.set.split(',')}
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    os.umask(0o077)
    arms = [a for a in prereg['arms'] if a['id'] in args.arms.split(',')]
    for arm in arms:
        arm = {**prereg['defaults'], **arm}
        model = os.path.expanduser(prereg['models'][arm['model']])
        work = out / arm['id']
        work.mkdir(parents=True, exist_ok=True)
        eligible = {n: [r for r in rows if r['kind'] in arm.get('kinds', [r['kind']])] for n, rows in sets.items()}
        drafts = {}
        if arm.get('draft_from'):  # the upstream arm must already have run on the same set
            for name in sets:
                p = out / arm['draft_from'] / f'{name}.jsonl'
                if not p.exists():
                    raise SystemExit(f"Arm {arm['id']} needs {arm['draft_from']} rows for {name} first.")
                drafts[name] = {r['id']: r for r in read_jsonl(p)}
        done = collections.defaultdict(set)
        for name in sets:
            p = work / f'{name}.jsonl'
            if p.exists():
                done[name] = {r['id'] for r in read_jsonl(p)}
        if all(len(done[n]) >= len(eligible[n]) for n in sets):
            continue
        srv = bench.Server(model, prereg['server_args'][arm['server']] + arm.get('extra_args', []), work)
        try:
            load_s = srv.wait_ready(prereg['ready_deadline_s'])
            print(json.dumps({'arm': arm['id'], 'load_s': round(load_s, 1)}), flush=True)
            for name, rows in eligible.items():
                for row in rows:
                    if row['id'] in done[name]:
                        continue
                    if row['kind'] == 'secpatch':
                        draft = drafts[name][row['id']] if drafts else None
                        res = run_secpatch(srv, row, arm, args.bandit, draft)
                    else:
                        res = run_adjudicated(srv, row, arm, adj)
                    res.update(arm=arm['id'], set=name, id=row['id'], kind=row['kind'], task=row['task'])
                    write_jsonl(work / f'{name}.jsonl', [res], mode='a')
                    print(json.dumps({k: res[k] for k in ('arm', 'set', 'id', 'correct', 'wall_s', 'tokens')}), flush=True)
        finally:
            srv.stop()
        (work / 'server.json').write_text(json.dumps({'argv': srv.argv, 'peak_vram_mib': srv.peak_vram}, indent=1))


# ---------- policy ----------

def exact_mcnemar(b: int, c: int) -> float:
    """Two-sided exact p for discordant pairs b (policy right, baseline wrong) vs c (the reverse)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def simulate(policy: dict, rows: dict, ids: list[str]) -> dict:
    """rows[arm][id] -> row. Returns per-item (correct, cost) for the policy, sequential execution."""
    out = {}
    for i in ids:
        kind = policy['kind']
        if kind == 'single':
            r = rows[policy['arm']][i]
            out[i] = (r['correct'], r['wall_s'], False)
        elif kind == 'agree':  # run first..., accept the first arm's answer if every key matches, else escalate
            first = [rows[a][i] for a in policy['first']]
            cost = sum(r['wall_s'] for r in first)
            keys = [r['key'] for r in first]
            agree = keys[0] is not None and all(k == keys[0] for k in keys)
            if agree:
                out[i] = (first[0]['correct'], cost, False)
            else:
                esc = rows[policy['escalate']][i]
                out[i] = (esc['correct'], cost + esc['wall_s'], True)
        elif kind == 'valid':  # accept the fast answer when it is parseable/comparable, else escalate
            r = rows[policy['arm']][i]
            if r['key'] is not None:
                out[i] = (r['correct'], r['wall_s'], False)
            else:
                esc = rows[policy['escalate']][i]
                out[i] = (esc['correct'], r['wall_s'] + esc['wall_s'], True)
        elif kind == 'route':  # the item kind is known when the request arrives; each kind has its own sub-policy
            out[i] = simulate(route_for(policy, next(r[i] for r in rows.values() if i in r)), rows, [i])[i]
        else:
            raise ValueError(kind)
    return out


def route_for(policy: dict, row: dict):
    """The sub-policy for an item: by task when the route names it (secpatch tasks are known from the request), else by kind."""
    return policy['route'].get(row.get('task')) or policy['route'].get(row['kind'])


def resolve(policy: dict, policies: dict) -> dict:
    """Replace route targets given by policy name with the policy itself."""
    if policy['kind'] != 'route':
        return policy
    return {**policy, 'route': {k: resolve(policies[v], policies) if isinstance(v, str) else v
                                for k, v in policy['route'].items()}}


def arms_of(policy: dict) -> set:
    if policy['kind'] == 'route':
        return set().union(*(arms_of(p) for p in policy['route'].values()))
    return {a for a in [policy.get('arm'), policy.get('escalate'), *policy.get('first', [])] if a}


def score_policy(name, policy, rows, ids, baseline):
    res = simulate(policy, rows, ids)
    base = simulate({'kind': 'single', 'arm': baseline}, rows, ids)
    k = sum(c for c, _, _ in res.values())
    cost = sum(t for _, t, _ in res.values())
    kb = sum(c for c, _, _ in base.values())
    cb = sum(t for _, t, _ in base.values())
    b = sum(1 for i in ids if res[i][0] and not base[i][0])
    c = sum(1 for i in ids if base[i][0] and not res[i][0])
    return {'policy': name, 'n': len(ids), 'correct': k, 'baseline_correct': kb, 'wall_s': round(cost, 1),
            'baseline_wall_s': round(cb, 1), 'speedup': round(cb / cost, 2) if cost else None,
            'seconds_per_correct': round(cost / k, 2) if k else None,
            'baseline_seconds_per_correct': round(cb / kb, 2) if kb else None,
            'escalated': sum(1 for _, _, e in res.values() if e), 'wins': b, 'losses': c,
            'mcnemar_p': round(exact_mcnemar(b, c), 4), 'non_inferior': k >= kb}


def load_rows(run_dir: pathlib.Path, set_name: str) -> dict:
    rows = {}
    for p in sorted(run_dir.glob(f'*/{set_name}.jsonl')):
        rows[p.parent.name] = {r['id']: r for r in read_jsonl(p)}
    return rows


def cmd_policy(args):
    prereg = json.loads(pathlib.Path(args.prereg).read_text())
    rows = load_rows(pathlib.Path(args.run), args.set)
    report = {'set': args.set, 'baseline': prereg['baseline'], 'arms_present': sorted(rows), 'groups': {}}
    for group in ('all', 'secpatch', 'adjudicated'):
        tables = []
        for name, pol in prereg['policies'].items():
            pol = resolve(pol, prereg['policies'])
            if pol['kind'] == 'route':  # each item only needs the arms of its own kind's sub-policy
                ids = [i for i, r in rows.get(prereg['baseline'], {}).items()
                       if route_for(pol, r) and all(i in rows.get(a, {}) for a in arms_of(route_for(pol, r)))]
            else:
                needed = arms_of(pol) | {prereg['baseline']}
                if any(a not in rows for a in needed):
                    continue
                ids = set.intersection(*(set(rows[a]) for a in needed))
            ids = sorted(i for i in ids if group == 'all' or rows[prereg['baseline']][i]['kind'] == group)
            if ids:
                tables.append(score_policy(name, pol, rows, ids, prereg['baseline']))
        report['groups'][group] = sorted(tables, key=lambda t: -(t['speedup'] or 0))
    print(json.dumps(report, indent=1))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(report, indent=1) + '\n')


def cmd_regrade(args):
    """Re-grade stored secpatch answers with the current grader (every arm alike). Remediation is skipped:
    its grade runs Bandit and did not change. The first grade is kept as correct_v1 on rows that change."""
    items = {r['id']: r for r in read_jsonl(pathlib.Path(args.sets) / f'{args.set}.jsonl')}
    for p in sorted(pathlib.Path(args.run).glob(f'*/{args.set}.jsonl')):
        rows, changed = read_jsonl(p), 0
        for r in rows:
            if r['kind'] != 'secpatch' or r['task'] == 'remediate':
                continue
            item = items[r['id']]['item']
            g = evaluate.grade(item, r['output'], 'unused')
            key = answer_key_secpatch(r['task'], r['output'])
            key = list(key) if isinstance(key, tuple) else key  # as stored in JSON
            if int(g['score']) != r['correct'] or key != r['key']:
                changed += int(g['score']) != r['correct']
                r.setdefault('correct_v1', r['correct'])
                r.update(correct=int(g['score']), key=key, grade={k: v for k, v in g.items() if k != 'score'})
        if changed or not args.dry_run:
            print(json.dumps({'arm': p.parent.name, 'score_changes': changed}))
        if not args.dry_run:
            backup = p.with_suffix('.jsonl.bak-v1')
            if not backup.exists():
                backup.write_bytes(p.read_bytes())
            write_jsonl(p, rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('sets')
    p.add_argument('--dev', required=True, help='secpatch eval-dev.jsonl (calibration source)')
    p.add_argument('--heldout', required=True, help='secpatch eval-heldout.jsonl (confirmation source)')
    p.add_argument('--fresh', nargs='*', help='secpatch eval-fresh-*.jsonl files, added to confirmation')
    p.add_argument('--screen-prompts', help='COT-EFF-1 prompts.jsonl: excluded from calibration')
    p.add_argument('--cal-per-task', default='{"detect": 8, "finding_support": 8, "root_cause": 6, "remediate": 6}')
    p.add_argument('--conf-per-task', default='{"detect": 20, "finding_support": 20, "root_cause": 16, "remediate": 16}')
    p.add_argument('--cal-adj-seed', required=True)
    p.add_argument('--conf-adj-seed', required=True)
    p.add_argument('--cal-per-family', type=int, default=2)
    p.add_argument('--conf-per-family', type=int, default=3)
    p.add_argument('--seed', type=int, default=20261030)
    p.add_argument('--out', required=True)
    p = sub.add_parser('run')
    p.add_argument('--prereg', required=True)
    p.add_argument('--sets', required=True)
    p.add_argument('--set', default='calibration')
    p.add_argument('--arms', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--bandit', default='bandit')
    p.add_argument('--allow-gpu-pid', type=int, action='append', default=[])
    p = sub.add_parser('policy')
    p.add_argument('--prereg', required=True)
    p.add_argument('--run', required=True)
    p.add_argument('--set', default='calibration')
    p.add_argument('--out')
    p = sub.add_parser('regrade')
    p.add_argument('--sets', required=True)
    p.add_argument('--run', required=True)
    p.add_argument('--set', default='calibration')
    p.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    {'sets': cmd_sets, 'run': cmd_run, 'policy': cmd_policy, 'regrade': cmd_regrade}[args.cmd](args)


if __name__ == '__main__':
    main()
