"""Review aid for one forge cycle's teacher traces (and, when present, its training/eval outputs).

Prints what a reviewer needs to judge a pass: acceptance by task and label under the CURRENT rules, rejection
reasons, red flags the automatic checks cannot see (wrong CWE family in the prose, hedging, generic text,
near-duplicate analyses), and a stratified sample of kept traces to read in full. The reviewer's decision goes
in cycles/cNNN/review-teach.json: {"approved": true, "reviewer": "...", "drop_ids": ["<id>:<hash12>", ...],
"notes": "..."}. Ids are printed by this tool.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import teach  # noqa: E402
from mix import trace_key  # noqa: E402

HEDGE = re.compile(r'\b(may|might|could potentially|possibly|potentially|if .{0,40} not properly)\b', re.I)
GENERIC = re.compile(r'\b(lack of (proper )?(input )?validation|without (proper )?sanitization|security risk|best practice)\b', re.I)
CWE_WORDS = {
    'CWE-22': r'travers|\.\.|path', 'CWE-79': r'xss|script|html|escap', 'CWE-89': r'sql',
    'CWE-78': r'shell|command', 'CWE-88': r'option|argument|--', 'CWE-502': r'pickle|yaml|deserial|load',
    'CWE-918': r'ssrf|url|request|host', 'CWE-601': r'redirect', 'CWE-1333': r'regex|regular expression|backtrack',
    'CWE-400': r'exhaust|unbounded|large|memory|dos|denial', 'CWE-208': r'timing|constant-time|compare',
    'CWE-347': r'signature|verif', 'CWE-295': r'certificate|tls|ssl|verif|trust', 'CWE-352': r'csrf|token',
    'CWE-611': r'xml|entit', 'CWE-94': r'eval|exec|code|template',
}


def jl(path):
    return [json.loads(x) for x in pathlib.Path(path).read_text().splitlines() if x.strip()]


def analysis_of(text: str) -> str:
    return teach.split_answer(text)[0] if '{' in text else re.split(r'```', text)[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cycle', type=pathlib.Path, required=True, help='cycles/cNNN directory')
    ap.add_argument('--samples', type=int, default=2, help='kept traces to print per task/label')
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args(argv)
    pool = {r['id']: r for r in jl(args.cycle / 'data' / 'pool.jsonl')}
    teach.VERSIONS.clear()
    teach.index_versions(list(pool.values()))
    latest = {}
    for path in sorted((args.cycle / 'teach').glob('traces*.jsonl')):
        for rec in jl(path):
            if rec['id'] in pool:
                prev = latest.get(rec['id'])
                if rec.get('sft') or prev is None or not prev.get('sft'):
                    latest[rec['id']] = {**rec, 'file': path.name}
    dropped = set()
    for f in [*args.cycle.glob('review-drops*.json'), args.cycle / 'review-teach.json']:
        if f.exists():
            dropped |= set(json.loads(f.read_text()).get('drop_ids', []))
    stats = collections.defaultdict(collections.Counter)
    kept, flags, seen_text = [], collections.defaultdict(list), {}
    for rid, rec in latest.items():
        row = pool[rid]
        key = (row['task'], row['label'] if row['task'] != 'root_cause' else '*')
        stats[key]['records'] += 1
        if not rec.get('sft'):
            stats[key]['no_trace:' + (rec['verdicts'][-1] if rec['verdicts'] else '?')] += 1
            continue
        text = rec['sft']['messages'][-1]['content']
        ok, why = teach.verify(row, text)
        if not ok:
            stats[key]['fails_current:' + why] += 1
            continue
        if trace_key(rec) in dropped:
            stats[key]['reviewer_dropped'] += 1
            continue
        stats[key]['kept'] += 1
        a = analysis_of(text)
        kept.append((trace_key(rec), key, a, text, rec['file']))
        rid = trace_key(rec)
        if len(HEDGE.findall(a)) >= 2:
            flags['hedging'].append(rid)
        if GENERIC.search(a) and len(a.split()) < 45:
            flags['generic'].append(rid)
        gold_cwe = (row['messages'][-1]['content'])
        for cwe, pat in CWE_WORDS.items():
            if row['task'] in ('detect', 'root_cause') and f'"{cwe}"' in gold_cwe and not re.search(pat, a, re.I):
                flags['cwe_mechanism_not_named:' + cwe].append(rid)
        sig = ' '.join(sorted(set(re.findall(r'[a-z]{5,}', a.lower())))[:200])
        if sig in seen_text:
            flags['near_duplicate'].append(rid)
        seen_text[sig] = rid
    print('== acceptance under current rules (latest record per row)')
    tot = collections.Counter()
    for key in sorted(stats):
        c = stats[key]
        tot.update(c)
        print(f'{key[0]:16s} {key[1]:16s} kept {c["kept"]:4d}/{c["records"]:<4d} ' +
              ' '.join(f'{k}={v}' for k, v in sorted(c.items()) if k not in ('kept', 'records')))
    print(f'TOTAL kept {tot["kept"]}/{tot["records"]}')
    print('\n== red flags (ids)')
    for k, ids in sorted(flags.items()):
        print(f'{k}: {len(ids)}  {ids[:8]}')
    print('\n== stratified sample of kept traces')
    rng = random.Random(args.seed)
    by = collections.defaultdict(list)
    for item in kept:
        by[item[1]].append(item)
    for key in sorted(by):
        for tk, _, a, text, f in rng.sample(by[key], min(args.samples, len(by[key]))):
            rid = tk.split(':')[0]
            row = pool[rid]
            gold = row['messages'][-1]['content'][:160].replace('\n', ' ')
            print(f'\n--- {tk} {key} [{f}] {row["source"]["repo"]} {row["source"].get("function")}')
            print('gold:', gold)
            print('trace:', text[:900])


if __name__ == '__main__':
    main()
