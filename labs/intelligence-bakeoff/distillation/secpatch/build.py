"""Build the R02 security-specialist SFT and evaluation sets from harvested fixes.

Every row is derived from a real advisory and its fix commit; targets are the
recorded fix, the advisory text, the commit's own tests or an executed Bandit
result. No model writes a target. Splits are isolated by repository *and* time:

  repo bucket = sha256(repo) mod 5 == 0 -> held-out repositories, else training repositories
  train     : training repositories, advisory published before --cutoff
  dev       : training repositories, published on/after --cutoff (time-only held out)
  heldout   : held-out repositories, published on/after --cutoff (repository and time held out)
  (held-out repositories before the cutoff are never used, so no held-out repo code is trained on)

Near-duplicate vulnerable functions across splits are removed from training.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import json
import pathlib
import random
import re
import subprocess
import sys
import tempfile
import textwrap
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from harvest import normalize  # noqa: E402

SYSTEM = ("You are Haven's security engineering assistant for authorized defensive work on code the user owns "
          "or is permitted to audit. Base every claim on the code and evidence provided, cite the lines you rely on, "
          "and say when the evidence is insufficient. Answer in the JSON format requested.")
MAX_FUNC_CHARS = 5000
MAX_TEST_LINES = 60
ATTRIBUTION_KEYS = ('repo', 'commit', 'parent', 'path', 'license', 'advisories', 'published')


def repo_bucket(repo: str) -> str:
    return 'heldout' if int(hashlib.sha256(repo.encode()).hexdigest()[:8], 16) % 5 == 0 else 'train'


def split_for(repo: str, published: str, cutoff: str) -> str | None:
    late = published >= cutoff
    if repo_bucket(repo) == 'heldout':
        return 'heldout' if late else None
    return 'dev' if late else 'train'


def shingles(code: str, n: int = 5) -> set:
    toks = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|\S', re.sub(r'#.*', '', code))
    return {tuple(toks[i:i + n]) for i in range(max(1, len(toks) - n + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def changed_lines(pair: dict) -> list[int]:
    """Absolute line numbers in the vulnerable function that the fix removed or replaced."""
    start = pair['vulnerable_span'][0]
    sm = difflib.SequenceMatcher(a=pair['vulnerable'].splitlines(), b=pair['fixed'].splitlines(), autojunk=False)
    out = []
    for tag, i1, i2, _, _ in sm.get_opcodes():
        if tag in ('replace', 'delete'):
            out.extend(range(start + i1, start + i2))
        elif tag == 'insert':
            out.append(start + max(i1 - 1, 0))  # the fix added code after this line
    return sorted(set(out))


def numbered(code: str, start: int) -> str:
    return '\n'.join(f'{start + i:>5} | {line}' for i, line in enumerate(code.splitlines()))


def run_bandit(bandit: str, pairs: list[dict]) -> dict:
    """Run Bandit once over every vulnerable/fixed function; return issue sets keyed by (index, side)."""
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for i, p in enumerate(pairs):
            for side in ('vulnerable', 'fixed'):
                (root / f'{i}_{side}.py').write_text(textwrap.dedent(p[side]) + '\n', encoding='utf-8')
        r = subprocess.run([bandit, '-q', '-r', '-f', 'json', str(root)], capture_output=True, text=True, timeout=1800)
        report = json.loads(r.stdout or '{}')
        for issue in report.get('results', []):
            idx, side = pathlib.Path(issue['filename']).stem.split('_', 1)
            out.setdefault((int(idx), side), []).append(
                {'test_id': issue['test_id'], 'test_name': issue['test_name'], 'text': issue['issue_text'],
                 'severity': issue['issue_severity'], 'confidence': issue['issue_confidence']})
        errors = {pathlib.Path(e['filename']).stem for e in report.get('errors', [])}
    for i in range(len(pairs)):
        for side in ('vulnerable', 'fixed'):
            out.setdefault((i, side), [])
            if f'{i}_{side}' in errors:
                out[(i, side)] = None
    return out


def advisory_text(rec: dict, limit: int = 900) -> str:
    details = re.sub(r'\s+', ' ', rec.get('details') or '').strip()
    summary = (rec.get('summary') or '').strip()
    text = summary if not details else (summary + ' — ' + details if summary and summary not in details else details)
    return text[:limit].rsplit(' ', 1)[0] + ('…' if len(text) > limit else '')


def chat(user: str, answer) -> list[dict]:
    content = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user},
            {'role': 'assistant', 'content': content}]


def code_block(item: dict, side: str) -> str:
    start = item['pair']['vulnerable_span' if side == 'vulnerable' else 'fixed_span'][0]
    return f"Repository: {item['repo']}\nFile: {item['pair']['path']}\n```python\n{numbered(item['pair'][side], start)}\n```"


def tasks_for(item: dict, decoy_name: str, rng: random.Random) -> list[dict]:
    """All task rows for one verified single-function fix. Each row keeps attribution and its verification."""
    p, rec = item['pair'], item
    name, lines = p['name'], item['changed_lines']
    cwe = rec['cwes']
    vuln_finding = {'verdict': 'vulnerable', 'function': name, 'cwe': cwe, 'evidence_lines': lines,
                    'issue': rec['summary'] or advisory_text(rec, 300)}
    rows = []
    ask_detect = ('Review the function below for security vulnerabilities. Respond with JSON: '
                  '{"verdict": "vulnerable" | "not_vulnerable", "function": str, "cwe": [str], '
                  '"evidence_lines": [int], "issue": str}. Use "not_vulnerable" when the code shows no exploitable weakness.')
    rows.append({'task': 'detect', 'label': 'vulnerable',
                 'messages': chat(f"{ask_detect}\n\n{code_block(item, 'vulnerable')}", vuln_finding)})
    rows.append({'task': 'detect', 'label': 'not_vulnerable',
                 'messages': chat(f"{ask_detect}\n\n{code_block(item, 'fixed')}",
                                  {'verdict': 'not_vulnerable', 'function': name, 'cwe': [], 'evidence_lines': [],
                                   'issue': 'No exploitable weakness of the reported kind is visible in this code.'})})
    if cwe:
        rows.append({'task': 'root_cause', 'label': ','.join(cwe), 'messages': chat(
            'This function was patched for a security issue. Using the vulnerable and fixed versions, explain the root '
            'cause. Respond with JSON: {"cwe": [str], "root_cause": str, "fix": str}.\n\nVulnerable:\n'
            f"{code_block(item, 'vulnerable')}\n\nFixed:\n{code_block(item, 'fixed')}",
            {'cwe': cwe, 'root_cause': advisory_text(rec), 'fix': rec['commit_message'].splitlines()[0][:200]})})
    rows.append({'task': 'remediate', 'label': 'fix', 'messages': chat(
        f"Reported issue: {rec['summary'] or advisory_text(rec, 300)}\n\nRewrite the function below to fix the issue "
        'without changing its interface or unrelated behavior. Return only the corrected function in one ```python block.'
        f"\n\n{code_block(item, 'vulnerable')}", f"```python\n{p['fixed']}\n```")})
    tests = [t for t in rec['tests'] if len(t['source'].splitlines()) <= MAX_TEST_LINES]
    if tests:
        test = tests[0]
        rows.append({'task': 'regression_test', 'label': test['name'], 'messages': chat(
            f"Reported issue: {rec['summary'] or advisory_text(rec, 300)}\n\nWrite a regression test (pytest or unittest, "
            f"matching {test['path']}) that fails on the vulnerable version and passes on the fixed one. Return one "
            f"```python block.\n\nVulnerable:\n{code_block(item, 'vulnerable')}\n\nFixed:\n{code_block(item, 'fixed')}",
            f"```python\n{test['source']}\n```")})
    if item.get('tool_verified'):
        hit = item['tool_verified']
        rows.append({'task': 'tool_select', 'label': hit['test_id'], 'messages': chat(
            'Which automated check should an analyst run to confirm the weakness in this function, and which rule should '
            'fire? Respond with JSON: {"tool": str, "rule": str, "command": str, "expected": str}.\n\n'
            f"{code_block(item, 'vulnerable')}",
            {'tool': 'bandit', 'rule': hit['test_id'], 'command': f"bandit -t {hit['test_id']} {p['path']}",
             'expected': hit['text']})})
    claim = (f"Finding: `{name}` in {p['path']} is vulnerable ({', '.join(cwe) or 'unclassified'}): "
             f"{rec['summary'] or advisory_text(rec, 200)} Evidence lines: {lines}.")
    ask = 'Is the finding supported by the code shown? Respond with JSON: {"supported": bool, "reason": str}.'
    rows.append({'task': 'finding_support', 'label': 'supported', 'messages': chat(
        f"{claim}\n\n{ask}\n\n{code_block(item, 'vulnerable')}",
        {'supported': True, 'reason': f'Lines {lines} of `{name}` contain the code the fix later changed.'})})
    rows.append({'task': 'finding_support', 'label': 'stale', 'messages': chat(
        f"{claim}\n\n{ask}\n\n{code_block(item, 'fixed')}",
        {'supported': False, 'reason': 'The code shown already contains the fix; the cited lines no longer hold the weakness.'})})
    decoy = claim.replace(f'`{name}`', f'`{decoy_name}`', 1)
    rows.append({'task': 'finding_support', 'label': 'nonexistent', 'messages': chat(
        f"{decoy}\n\n{ask}\n\n{code_block(item, 'vulnerable')}",
        {'supported': False, 'reason': f'`{decoy_name}` does not appear in the code shown; the finding cites code that is not there.'})})
    attribution = {k: rec.get(k) for k in ATTRIBUTION_KEYS if k in rec}
    attribution.update(path=p['path'], function=name, code_license=rec['license'],
                       advisory_ids=[a['id'] for a in rec['advisories']],
                       advisory_licenses=sorted({a['license'] for a in rec['advisories']}))
    for row in rows:
        row.update(id=hashlib.sha256((item['key'] + row['task'] + row['label']).encode()).hexdigest()[:16],
                   key=item['key'], split=item['split'], source=attribution,
                   verification={'fix_commit_fetched': True, 'single_parent': True, 'permissive_license': True,
                                 'single_function_fix': True, 'parsed': True,
                                 'tool_verified': bool(item.get('tool_verified')),
                                 'tests_in_fix_commit': len(rec['tests'])})
    return rows


def eval_items(item: dict) -> list[dict]:
    """Held-out probes with grader metadata. Prompts never carry the answer."""
    rows = [r for r in tasks_for(item, 'not_a_real_function', random.Random(0)) if r['task'] != 'regression_test']
    for r in rows:
        r['grader'] = {'task': r['task'], 'label': r['label'], 'function': item['pair']['name'],
                       'cwe': item['cwes'], 'changed_lines': item['changed_lines'],
                       'bandit': item.get('tool_verified'), 'vulnerable': item['pair']['vulnerable'],
                       'fixed': item['pair']['fixed']}
        r['reference'] = r['messages'][-1]['content']
        r['messages'] = r['messages'][:-1]
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidates', type=pathlib.Path, required=True)
    ap.add_argument('--harvest', type=pathlib.Path, nargs='+', required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--bandit', default='bandit')
    ap.add_argument('--cutoff', default='2025-07-01')
    ap.add_argument('--near-dup', type=float, default=0.8)
    args = ap.parse_args(argv)
    cands = {c['key']: c for c in map(json.loads, args.candidates.read_text().splitlines())}
    stats = collections.Counter()
    items, seen_exact = [], {}
    harvested = {}
    for line in (x for path in args.harvest for x in path.read_text().splitlines() if x.strip()):
        h = json.loads(line)
        harvested[h['key']] = h  # resumed or sharded runs may repeat a key; the latest record wins
    for h in harvested.values():
        stats['harvested'] += 1
        if h.get('error'):
            stats['fetch_error'] += 1; continue
        c = h.get('checks', {})
        if not c.get('permissive_license'):
            stats['license_excluded'] += 1; continue
        if len(h.get('pairs', [])) != 1 or not c.get('focused_fix'):
            stats['not_single_function'] += 1; continue
        pair = h['pairs'][0]
        if max(len(pair['vulnerable']), len(pair['fixed'])) > MAX_FUNC_CHARS:
            stats['too_long'] += 1; continue
        cand = cands[h['key']]
        split = split_for(h['repo'], cand['published'], args.cutoff)
        if split is None:
            stats['heldout_repo_before_cutoff_unused'] += 1; continue
        digest = hashlib.sha256(normalize(pair['vulnerable']).encode()).hexdigest()
        if digest in seen_exact:
            stats['exact_duplicate'] += 1; continue
        seen_exact[digest] = h['key']
        items.append({**cand, **h, 'pair': pair, 'split': split, 'digest': digest,
                      'changed_lines': changed_lines(pair)})
    # Leakage: a training function that nearly matches any dev/held-out function is dropped from training.
    sh = {it['key']: shingles(it['pair']['vulnerable']) for it in items}
    protected = [it for it in items if it['split'] != 'train']
    kept = []
    for it in items:
        if it['split'] == 'train' and any(jaccard(sh[it['key']], sh[o['key']]) >= args.near_dup for o in protected):
            stats['train_near_duplicate_of_eval_dropped'] += 1; continue
        kept.append(it)
    items = kept
    assert not ({i['repo'] for i in items if i['split'] == 'train'} & {i['repo'] for i in items if i['split'] == 'heldout'})
    bandit = run_bandit(args.bandit, [it['pair'] for it in items])
    for i, it in enumerate(items):
        vuln, fixed = bandit[(i, 'vulnerable')], bandit[(i, 'fixed')]
        it['bandit'] = {'vulnerable': vuln, 'fixed': fixed}
        if vuln is not None and fixed is not None:
            gone = {x['test_id'] for x in vuln} - {x['test_id'] for x in fixed}
            hit = next((x for x in vuln if x['test_id'] in gone), None)
            if hit:
                it['tool_verified'] = hit
                stats['tool_verified'] += 1
    rng = random.Random(20261027)
    names = [it['pair']['name'].rsplit('.', 1)[-1] for it in items]
    args.out.mkdir(parents=True, exist_ok=True)
    counts = collections.Counter()
    files = {s: (args.out / f'{s}.jsonl').open('w', encoding='utf-8') for s in ('train', 'dev', 'heldout')}
    evals = {s: (args.out / f'eval-{s}.jsonl').open('w', encoding='utf-8') for s in ('dev', 'heldout')}
    for it in items:
        decoy = rng.choice([n for n in names if n not in it['pair']['vulnerable']] or ['missing_helper'])
        for row in tasks_for(it, decoy, rng):
            files[it['split']].write(json.dumps(row, ensure_ascii=False) + '\n')
            counts[(it['split'], row['task'])] += 1
        if it['split'] in evals:
            for row in eval_items(it):
                evals[it['split']].write(json.dumps(row, ensure_ascii=False) + '\n')
    for f in [*files.values(), *evals.values()]:
        f.close()
    # Repository-level verification candidates: held-out fixes that shipped their own tests.
    with (args.out / 'repo-eval-candidates.jsonl').open('w', encoding='utf-8') as f:
        for it in items:
            if it['split'] == 'heldout' and it['tests']:
                f.write(json.dumps({k: it[k] for k in ('key', 'repo', 'commit', 'parent', 'published', 'summary', 'cwes')}
                                   | {'path': it['pair']['path'], 'function': it['pair']['name'],
                                      'tests': [{'path': t['path'], 'name': t['name']} for t in it['tests']]}) + '\n')
    manifest = {
        'built_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'cutoff': args.cutoff,
        'osv_archive_sha256': next(iter(cands.values()))['osv_archive_sha256'],
        'partition': 'sha256(repo)[:8] mod 5 == 0 -> held-out repositories',
        'filters': stats, 'items_by_split': collections.Counter(it['split'] for it in items),
        'rows': {f'{s}/{t}': n for (s, t), n in sorted(counts.items())},
        'repos_by_split': {s: len({i['repo'] for i in items if i['split'] == s}) for s in ('train', 'dev', 'heldout')},
        'code_licenses': collections.Counter(i['license'] for i in items),
        'advisory_sources': collections.Counter(a['source_db'] for i in items for a in i['advisories']),
        'cwe_top': collections.Counter(c for i in items for c in i['cwes']).most_common(15),
        'bandit_version': subprocess.run([args.bandit, '--version'], capture_output=True, text=True).stdout.split('\n')[0],
        'note': 'Targets are recorded fixes, advisory text (CC-BY-4.0), commit tests or executed Bandit results. No model output.'}
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=1, default=dict) + '\n')
    print(json.dumps(manifest, default=dict)[:3000])


if __name__ == '__main__':
    main()
