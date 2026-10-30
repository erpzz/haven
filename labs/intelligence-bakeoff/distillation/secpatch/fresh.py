"""Build a dated eval set from security fixes published after the last one: novel questions every run.

Takes a current OSV export, keeps advisories published on/after --since that were never harvested
before (any key in --seen files) and whose repository is not a training repository, then harvests
and verifies them exactly like build.py (permissive license at the fix, one self-contained-or-flagged
function change, both versions parse, executed Bandit). Output: eval-fresh-<stamp>.jsonl in the same
item format as eval-heldout.jsonl, plus a manifest. Nothing here is ever used for training.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build  # noqa: E402
import harvest  # noqa: E402
import osv  # noqa: E402


def select(candidates: list[dict], since: str, seen: set, train_repos: set, limit: int) -> list[dict]:
    out, per_repo = [], collections.Counter()
    for c in candidates:
        if c['published'] < since or c['key'] in seen or c['repo'] in train_repos:
            continue
        per_repo[c['repo']] += 1
        if per_repo[c['repo']] <= 3:  # keep one project from dominating a small fresh set
            out.append(c)
    return out[:limit]


def items_from(harvested: list[dict], cands: dict, bandit: str) -> tuple[list[dict], collections.Counter]:
    stats, items = collections.Counter(), []
    for h in harvested:
        c = h.get('checks', {})
        if h.get('error'):
            stats['fetch_error'] += 1; continue
        if not c.get('permissive_license'):
            stats['license_excluded'] += 1; continue
        if len(h.get('pairs', [])) != 1 or not c.get('focused_fix'):
            stats['not_single_function'] += 1; continue
        pair = h['pairs'][0]
        if max(len(pair['vulnerable']), len(pair['fixed'])) > build.MAX_FUNC_CHARS:
            stats['too_long'] += 1; continue
        scope = h.get('scope')
        items.append({**cands[h['key']], **h, 'pair': pair, 'split': 'fresh', 'scope': scope,
                      'self_contained': bool(scope and scope['self_contained']),
                      'changed_lines': build.changed_lines(pair)})
    if items:
        results = build.run_bandit(bandit, [it['pair'] for it in items])
        for i, it in enumerate(items):
            vuln, fixed = results[(i, 'vulnerable')], results[(i, 'fixed')]
            if vuln is not None and fixed is not None:
                gone = {x['test_id'] for x in vuln} - {x['test_id'] for x in fixed}
                hit = next((x for x in vuln if x['test_id'] in gone), None)
                if hit:
                    it['tool_verified'] = hit
                    stats['tool_verified'] += 1
    stats['items'] = len(items)
    return items, stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive', type=pathlib.Path, required=True, help='A current OSV ecosystem export (all.zip).')
    ap.add_argument('--since', required=True, help='ISO date; only advisories published on/after it.')
    ap.add_argument('--seen', type=pathlib.Path, nargs='*', default=[], help='Earlier candidates/harvest files.')
    ap.add_argument('--train', type=pathlib.Path, required=True, help='train.jsonl: its repositories are excluded.')
    ap.add_argument('--work', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True, help='Output directory.')
    ap.add_argument('--bandit', default='bandit')
    ap.add_argument('--limit', type=int, default=150)
    args = ap.parse_args(argv)
    seen = set()
    for path in args.seen:
        seen |= {json.loads(x)['key'] for x in path.read_text().splitlines() if x.strip()}
    train_repos = {json.loads(x)['source']['repo'] for x in args.train.read_text().splitlines() if x.strip()}
    cands = osv.candidates(args.archive)
    picked = select(cands, args.since, seen, train_repos, args.limit)
    harvested = []
    for c in picked:
        try:
            harvested.append(harvest.harvest_one(c, args.work))
        except Exception as exc:  # recorded per advisory; never silently skipped
            harvested.append({'key': c['key'], 'repo': c['repo'], 'error': str(exc)[:300]})
    by_key = {c['key']: c for c in picked}
    items, stats = items_from(harvested, by_key, args.bandit)
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f'eval-fresh-{stamp}.jsonl'
    with out.open('w', encoding='utf-8') as f:
        for it in items:
            for row in build.eval_items(it):
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    (args.out / f'harvest-fresh-{stamp}.jsonl').write_text(''.join(json.dumps(h) + '\n' for h in harvested))
    manifest = {'built_at': stamp, 'since': args.since, 'osv_archive_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
                'candidates_after_since': len(picked), 'filters': stats, 'fixes': len(items),
                'repos': len({i['repo'] for i in items}), 'eval_file': out.name,
                'eval_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
                'note': 'Fresh questions: published after --since, never harvested before, no training repository.'}
    (args.out / f'manifest-fresh-{stamp}.json').write_text(json.dumps(manifest, indent=1, default=dict) + '\n')
    print(json.dumps(manifest, default=dict))


if __name__ == '__main__':
    main()
