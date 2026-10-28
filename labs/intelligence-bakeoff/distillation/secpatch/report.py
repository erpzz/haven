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
    args = ap.parse_args(argv)
    if args.items:
        print(arm_table(resummarize(args.items, set(args.tasks.split(',')) if args.tasks else None)))
    if args.summaries:
        print(arm_table([json.loads(p.read_text()) for p in args.summaries]))
    if args.repo_eval:
        print('\n' + repo_table(args.repo_eval))


if __name__ == '__main__':
    main()
