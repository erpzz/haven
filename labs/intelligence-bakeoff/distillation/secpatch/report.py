"""Compare evaluation arms on the same eval file, plus repository-level results, as Markdown.

Refuses to put arms with different eval digests in one table: a comparison is
only meaningful on identical held-out items.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

TASKS = ('detect', 'finding_support', 'root_cause', 'remediate', 'tool_select')


def arm_table(summaries: list[dict]) -> str:
    digests = {s['eval_sha256'] for s in summaries}
    if len(digests) != 1:
        raise SystemExit(f'Arms were evaluated on different item sets: {sorted(digests)}')
    head = ['arm', 'items', 'score'] + [f'{t}' for t in TASKS] + \
        ['detect recall', 'FPR (fixed code)', 'paired detect', 'unsupported', 'invalid JSON', 'Bandit-cleared fixes',
         's/item', 'peak RSS GiB']
    lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    for s in summaries:
        cells = [f"{s['model']} · {s.get('arm', 'plain')}", str(s['n']), f"{s['score']:.3f}"]
        for t in TASKS:
            b = s['by_task'].get(t)
            cells.append(f"{b['correct']}/{b['n']} ({b['wilson95'][0]:.2f}–{b['wilson95'][1]:.2f})" if b else '—')
        inv = sum(b['invalid_json'] for b in s['by_task'].values())
        cleared = s.get('remediation_bandit_cleared', [0, 0])
        cells += [f"{s['detection_recall']:.2f}", f"{s['false_positive_rate']:.2f}", f"{s['paired_detection']:.2f}",
                  f"{s['unsupported_rate']:.3f}", str(inv), f'{cleared[0]}/{cleared[1]}', f"{s['latency_mean_s']:.1f}",
                  f"{s['peak_rss_gib']:.1f}"]
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def repo_table(path: pathlib.Path) -> str:
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    status = collections.Counter(r['status'] for r in rows)
    lines = ['Validation status of held-out fixes with their own tests: ' +
             ', '.join(f'{k} {v}' for k, v in sorted(status.items())), '',
             '| advisory | repository | regression test | recorded fix | model patches |', '|---|---|---|---|---|']
    for r in rows:
        patches = r.get('patches', {})
        model = ', '.join(f'{k}: {v["status"]}' for k, v in patches.items() if k != 'recorded_fix') or '—'
        lines.append(f"| {r['key']} | {r['repo']} | {r['status']} | {patches.get('recorded_fix', {}).get('status', '—')} | {model} |")
    return '\n'.join(lines)


def majority_baseline(eval_path: pathlib.Path, keep: set | None = None) -> dict:
    """What always answering each task's most common label would score: the floor every arm must beat."""
    rows = [json.loads(x) for x in eval_path.read_text().splitlines() if x.strip()]
    if keep is not None:
        rows = [r for r in rows if r['id'] in keep]
    out = {}
    for task in sorted({r['task'] for r in rows}):
        # finding_support is a yes/no answer: stale and nonexistent findings are both "unsupported".
        answer = (lambda r: 'supported' if r['label'] == 'supported' else 'unsupported') if task == 'finding_support' \
            else (lambda r: r['label'])
        labels = collections.Counter(answer(r) for r in rows if r['task'] == task)
        if task in ('detect', 'finding_support'):
            label, n = labels.most_common(1)[0]
            out[task] = {'label': label, 'correct': n, 'n': sum(labels.values())}
    return out


def regrade(item_files: list[pathlib.Path], eval_path: pathlib.Path, bandit: str) -> None:
    """Re-run the current graders on stored outputs (in place, with a .orig backup)."""
    import shutil
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from evaluate import grade
    items = {r['id']: r for r in map(json.loads, eval_path.read_text().splitlines())}
    for path in item_files:
        if not path.with_suffix('.jsonl.orig').exists():
            shutil.copy(path, path.with_suffix('.jsonl.orig'))
        rows = [json.loads(x) for x in path.with_suffix('.jsonl.orig').read_text().splitlines() if x.strip()]
        for r in rows:
            r.update(grade(items[r['id']], r['output'], bandit))
            # Outputs stored before 2026-10-28 were cut at 4000 characters; flag rather than guess.
            r['output_maybe_truncated'] = 'output_chars' not in r and len(r['output']) >= 4000
        path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))


def resummarize(item_files: list[pathlib.Path], tasks: set | None) -> list[dict]:
    """Re-score arms from their per-item files over the ids every arm answered (optionally a task subset),
    so arms run on different task subsets still compare on identical items."""
    import hashlib
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from evaluate import summarize
    arms = []
    for path in item_files:
        rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        meta = json.loads((path.parent / 'summary.json').read_text()) if (path.parent / 'summary.json').exists() else {}
        arms.append((path, rows, meta))
    common = set.intersection(*({(r['id'], r['seed']) for r in rows if tasks is None or r['task'] in tasks}
                                for _, rows, _ in arms))
    ids = sorted({i for i, _ in common})
    digest = hashlib.sha256(json.dumps(ids).encode()).hexdigest()
    out = []
    for path, rows, meta in arms:
        s = summarize([r for r in rows if (r['id'], r['seed']) in common], digest, meta.get('model', path.parent.name))
        s['arm'] = meta.get('arm', path.parent.name)
        s['peak_rss_gib'] = meta.get('peak_rss_gib', s['peak_rss_gib'])  # the evaluator process's, not report.py's
        out.append(s)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--summaries', type=pathlib.Path, nargs='*', default=[])
    ap.add_argument('--items', type=pathlib.Path, nargs='*', default=[], help='items.jsonl files to re-score on shared ids')
    ap.add_argument('--tasks', help='with --items: comma-separated task subset')
    ap.add_argument('--repo-eval', type=pathlib.Path)
    ap.add_argument('--eval', type=pathlib.Path, help='eval file: majority baseline, and --regrade input')
    ap.add_argument('--regrade', action='store_true', help='re-grade --items outputs with current graders first')
    ap.add_argument('--bandit', default='bandit')
    args = ap.parse_args(argv)
    if args.regrade:
        regrade(args.items, args.eval, args.bandit)
    if args.items:
        arms = resummarize(args.items, set(args.tasks.split(',')) if args.tasks else None)
        print(arm_table(arms))
        if args.eval:
            keep = {r['id'] for r in map(json.loads, args.items[0].read_text().splitlines())
                    if not args.tasks or r['task'] in args.tasks.split(',')}
            base = majority_baseline(args.eval, keep)
            print('\nMajority-label floor on the same items: ' + '; '.join(
                f"{t}: always '{b['label']}' = {b['correct']}/{b['n']}" for t, b in base.items()))
    if args.summaries:
        print(arm_table([json.loads(p.read_text()) for p in args.summaries]))
    if args.repo_eval:
        print('\n' + repo_table(args.repo_eval))


if __name__ == '__main__':
    main()
