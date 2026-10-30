"""Assemble one forge cycle's SFT pool and its evaluation gate from a built secpatch data directory.

Splits (all by repository, so no repository's code is ever both trained on and used to judge):
  * gate  = dev-split repositories with sha256(repo) odd                 (eval rows; promotion decisions)
  * pool  = train + dev rows from every other repository                 (training rows; a gate repository's
            pre-cutoff fixes are dropped too)
  * heldout = the held-out split, untouched                              (eval rows; reported, also gated)
Targets: a verified teacher trace replaces the recorded target when one exists; verified self-play samples
(student outputs that the deterministic grader accepted) are added; otherwise the recorded target is used.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import teach  # noqa: E402


def jl(path: pathlib.Path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def repo_half(repo: str) -> int:
    return int(hashlib.sha256(repo.encode()).hexdigest()[:8], 16) % 2


def trace_key(rec: dict) -> str:
    """Identity of one trace: row id + content hash, so a dropped trace does not block a later good one."""
    text = rec['sft']['messages'][-1]['content']
    return rec['id'] + ':' + hashlib.sha256(text.encode()).hexdigest()[:12]


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', type=pathlib.Path, required=True, help='built data dir (train/dev/eval-dev/eval-heldout)')
    ap.add_argument('--traces', type=pathlib.Path, nargs='*', default=[], help='teach.py outputs')
    ap.add_argument('--selfplay', type=pathlib.Path, nargs='*', default=[], help='selfplay.py outputs')
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--selfplay-per-row', type=int, default=1)
    ap.add_argument('--no-reverify', dest='reverify', action='store_false')
    ap.add_argument('--reviews', type=pathlib.Path, nargs='*', default=[], help='review-teach.json decisions')
    ap.add_argument('--critic', type=pathlib.Path, nargs='*', default=[], help='critic.py verdicts')
    ap.add_argument('--critic-max-reject', type=float, default=0.35)
    ap.add_argument('--pairs', type=pathlib.Path, nargs='*', default=[], help='self-play chosen/rejected pairs')
    args = ap.parse_args(argv)
    train, dev = jl(args.data / 'train.jsonl'), jl(args.data / 'dev.jsonl')
    eval_dev, heldout = jl(args.data / 'eval-dev.jsonl'), jl(args.data / 'eval-heldout.jsonl')
    # dev repositories also have pre-cutoff fixes in train; a gate repository contributes nothing to the pool.
    gate_repos = {r['source']['repo'] for r in dev if repo_half(r['source']['repo']) == 1}
    pool = [r for r in train + dev if r['source']['repo'] not in gate_repos]
    gate = [r for r in eval_dev if r['source']['repo'] in gate_repos]
    pool_repos = {r['source']['repo'] for r in pool}
    judge_repos = {r['source']['repo'] for r in gate} | {r['source']['repo'] for r in heldout}
    if pool_repos & judge_repos:
        raise SystemExit(f'Repository leak between pool and gate/heldout: {sorted(pool_repos & judge_repos)[:5]}')
    pool_ids = {r['id'] for r in pool}
    by_id = {r['id']: r for r in pool}
    teach.VERSIONS.clear()
    teach.index_versions(train + dev)
    taught, rejected = {}, collections.Counter()
    dropped = set()
    for path in args.reviews:  # traces (id:hash) a reviewer rejected never train
        dropped |= set(json.loads(path.read_text()).get('drop_ids', []))
    critic_ignored = {}
    for path in args.critic:  # the automated critic's rejections count like a reviewer's drops
        verdicts = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        unsound = {v['key'] for v in verdicts if v.get('sound') is False}
        # Circuit breaker: a critic that rejects a large share is miscalibrated (its first version rejected 65%
        # of traces, mostly by disputing correct labels); ignore the whole file rather than gut the data.
        if verdicts and len(unsound) / len(verdicts) > args.critic_max_reject:
            critic_ignored[path.name] = round(len(unsound) / len(verdicts), 3)
            continue
        dropped |= unsound
    for path in args.traces:
        for rec in jl(path):
            if rec.get('sft') and rec['id'] in pool_ids and trace_key(rec) in dropped:
                rejected['reviewer_dropped'] += 1
            elif rec.get('sft') and rec['id'] in pool_ids:
                # Re-check every stored trace against the CURRENT rules, so tightening the teacher's checks
                # also removes traces accepted under older, looser ones.
                kept, why = teach.verify(by_id[rec['id']], rec['sft']['messages'][-1]['content'])
                if kept or not args.reverify:
                    taught[rec['id']] = rec['sft']
                else:
                    rejected[why] += 1
    extra = collections.defaultdict(list)
    for path in args.selfplay:
        for rec in jl(path):
            if rec.get('id') in pool_ids and len(extra[rec['id']]) < args.selfplay_per_row:
                extra[rec['id']].append(rec)
    rows, origin = [], collections.Counter()
    for r in pool:
        row = taught.get(r['id'])
        if row is None:
            row = {**r, 'origin': 'recorded'}
        rows.append({**row, 'split': 'train'})
        origin[row['origin']] += 1
        for s in extra[r['id']]:
            rows.append({**s, 'split': 'train'})
            origin['selfplay_verified'] += 1
    pairs = {}
    for path in args.pairs:  # later cycles overwrite earlier ones: pairs from the newest policy win
        for rec in jl(path):
            if rec.get('id') in pool_ids:
                pairs[rec['id']] = rec
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / 'pairs.jsonl').open('w', encoding='utf-8') as f:
        for rec in pairs.values():
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    recorded = [{**r, 'split': 'train'} for r in pool]  # ground-truth targets: teacher input and self-play graders
    for name, data in (('sft.jsonl', rows), ('pool.jsonl', recorded), ('gate.jsonl', gate),
                       ('eval-heldout.jsonl', heldout)):
        with (args.out / name).open('w', encoding='utf-8') as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    manifest = {
        'source_manifest': json.loads((args.data / 'manifest.json').read_text()),
        'pool_rows': len(rows), 'pool_fixes': len({r['key'] for r in pool}), 'pool_repos': len(pool_repos),
        'by_task': collections.Counter(r['task'] for r in rows), 'by_origin': origin,
        'traces_rejected_on_reverify': rejected,
        'critic_files_ignored_as_miscalibrated': critic_ignored,
        'preference_pairs': len(pairs),
        'gate_rows': len(gate), 'gate_fixes': len({r['key'] for r in gate}),
        'heldout_rows': len(heldout), 'heldout_fixes': len({r['key'] for r in heldout}),
        'sha256': {n: digest(args.out / n) for n in ('sft.jsonl', 'pool.jsonl', 'gate.jsonl', 'eval-heldout.jsonl')},
        'split_rule': 'dev repos with sha256(repo)[:8] odd -> gate (all their rows leave the pool)',
    }
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print(json.dumps({k: manifest[k] for k in manifest if k != 'source_manifest'}, indent=1))
    return manifest


if __name__ == '__main__':
    main()
