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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--summaries', type=pathlib.Path, nargs='+', required=True)
    ap.add_argument('--repo-eval', type=pathlib.Path)
    args = ap.parse_args(argv)
    print(arm_table([json.loads(p.read_text()) for p in args.summaries]))
    if args.repo_eval:
        print('\n' + repo_table(args.repo_eval))


if __name__ == '__main__':
    main()
