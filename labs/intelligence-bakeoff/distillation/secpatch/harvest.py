"""Fetch fix commits and extract verified vulnerable/fixed Python function pairs.

For each candidate the harvester does a shallow, blobless fetch of exactly the
fix commit and its parent from GitHub, then:
  * classifies the repository license *at the fix commit* and keeps only
    permissive licenses (code is redistributed in training rows, with attribution);
  * extracts every non-test Python function whose source changed, with its
    qualified name and line span before and after;
  * records test functions the commit added or changed (regression-test targets);
  * marks each step as a verification result rather than assuming it.
Nothing is executed from the fetched repository here.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import warnings

# Fetched code is only parsed, never run; old escape sequences there are not our warnings.
warnings.filterwarnings('ignore', category=SyntaxWarning)

PERMISSIVE = ('MIT', 'BSD-2-Clause', 'BSD-3-Clause', 'Apache-2.0', 'ISC', 'PSF-2.0', '0BSD', 'Unlicense')
LICENSE_FILES = re.compile(r'^(LICEN[CS]E|COPYING)(\.(md|txt|rst))?$', re.I)
MAX_FUNC_LINES = 150
MAX_CHANGED_FUNCS = 4


def classify_license(text: str) -> str | None:
    """Conservative SPDX classification of a license file; None when unsure."""
    t = ' '.join(text.split()).lower()
    if 'apache license' in t and 'version 2.0' in t:
        return 'Apache-2.0'
    if 'permission is hereby granted, free of charge' in t and 'the above copyright notice' in t:
        return 'MIT'
    if 'redistribution and use in source and binary forms' in t:
        if 'neither the name' in t or 'names of its contributors' in t or 'name of the copyright holder' in t:
            return 'BSD-3-Clause'
        return 'BSD-2-Clause'
    if 'permission to use, copy, modify, and/or distribute this software' in t:
        return 'ISC' if 'the above copyright notice and this permission notice appear' in t else '0BSD'
    if 'python software foundation license' in t or 'psf license agreement' in t:
        return 'PSF-2.0'
    if 'this is free and unencumbered software released into the public domain' in t:
        return 'Unlicense'
    for marker, spdx in (('gnu affero general public license', 'AGPL'), ('gnu lesser general public license', 'LGPL'),
                         ('gnu library general public license', 'LGPL'), ('gnu general public license', 'GPL'),
                         ('mozilla public license', 'MPL-2.0'), ('eclipse public license', 'EPL')):
        if marker in t:
            return spdx  # recognized, but not permissive: excluded from training rows
    return None


def git(repo_dir: pathlib.Path, *args, timeout=120, check=True) -> str:
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_LFS_SKIP_SMUDGE': '1'}
    r = subprocess.run(['git', '-C', str(repo_dir), *args], capture_output=True, text=True,
                       timeout=timeout, env=env, errors='replace')
    if check and r.returncode:
        raise RuntimeError(f'git {args[0]} failed: {r.stderr.strip()[:200]}')
    return r.stdout


def github(repo: str) -> str:
    return f'https://github.com/{repo}.git'


def fetch(repo: str, sha: str, work: pathlib.Path, remote=github) -> pathlib.Path:
    d = work / re.sub(r'[^a-z0-9]+', '_', repo)
    if not d.exists():
        d.mkdir(parents=True)
        git(d, 'init', '-q')
        git(d, 'remote', 'add', 'origin', remote(repo))
    git(d, 'fetch', '-q', '--depth=2', '--filter=blob:none', 'origin', sha, timeout=300)
    return d


def is_test_path(path: str) -> bool:
    p = path.lower()
    return bool(re.search(r'(^|/)(tests?|testing)/', p) or re.search(r'(^|/)test_[^/]*\.py$', p) or p.endswith('_test.py'))


def functions(source: str) -> dict[str, dict]:
    """Qualified name -> {source, start, end} for every function and method."""
    tree = ast.parse(source)
    lines = source.splitlines()
    out = {}
    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name
                if not isinstance(child, ast.ClassDef):
                    start = min([d.lineno for d in child.decorator_list] + [child.lineno])
                    out[name] = {'source': '\n'.join(lines[start - 1:child.end_lineno]), 'start': start, 'end': child.end_lineno}
                walk(child, name + '.')
    walk(tree, '')
    return out


def normalize(code: str) -> str:
    """Whitespace/comment-insensitive form used to ignore cosmetic-only changes and for dedup."""
    try:
        return ast.dump(ast.parse(code.strip() if not code.startswith((' ', '\t')) else 'if 1:\n' + code))
    except SyntaxError:
        return re.sub(r'\s+', ' ', re.sub(r'#.*', '', code)).strip()


def module_shape(source: str) -> str:
    """AST of a module with every function body blanked: differs only when imports, constants,
    class attributes, decorators or signatures change."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.body = [ast.Pass()]
    return ast.dump(tree)


def fix_scope(before: str, after: str, fb: dict, fa: dict) -> dict:
    """What else the fix changed in the pair's file. A self-contained fix changes one function and nothing around it."""
    def shape_ok(code):
        try:
            return module_shape(code)
        except SyntaxError:
            return None
    return {'added_functions': sorted(set(fa) - set(fb)), 'removed_functions': sorted(set(fb) - set(fa)),
            'module_level_changed': shape_ok(before) != shape_ok(after)}


def scope_checks(rec: dict, file_scope: dict) -> dict:
    sources = [p for p in rec.get('changed_files', []) if p.endswith('.py') and not is_test_path(p)]
    non_python = [p for p in rec.get('changed_files', [])
                  if not p.endswith('.py') and not re.search(r'(^|/)(docs?|changelog|changes|news)|\.(md|rst|txt)$', p, re.I)]
    scope = {**file_scope, 'other_source_files': [p for p in sources if p != rec['pairs'][0]['path']],
             'non_python_changes': non_python[:20]}
    scope['self_contained'] = not (scope['added_functions'] or scope['removed_functions'] or scope['module_level_changed']
                                   or scope['other_source_files'])
    return scope


def harvest_one(cand: dict, work: pathlib.Path, remote=github) -> dict:
    repo, sha = cand['repo'], cand['commit']
    rec = {'key': cand['key'], 'repo': repo, 'commit': sha, 'checks': {}, 'pairs': [], 'tests': []}
    d = fetch(repo, sha, work, remote)
    full = git(d, 'rev-parse', sha).strip()
    parents = git(d, 'rev-list', '--parents', '-n', '1', full).split()[1:]
    rec['commit'] = full
    if len(parents) != 1:
        rec['checks']['single_parent'] = False
        return rec
    parent = parents[0]
    rec.update(parent=parent, checks={'single_parent': True})
    meta = git(d, 'show', '-s', '--format=%an%x00%aI%x00%cI%x00%B', full).split('\x00', 3)
    rec.update(commit_author=meta[0], authored_at=meta[1], committed_at=meta[2], commit_message=meta[3].strip()[:4000])
    tree = git(d, 'ls-tree', '--name-only', full).split('\n')
    lic_files = [p for p in tree if LICENSE_FILES.match(p)]
    license_id = None
    for p in lic_files:
        license_id = classify_license(git(d, 'show', f'{full}:{p}', timeout=120))
        if license_id:
            rec['license_file'] = p
            break
    rec['license'] = license_id
    rec['checks']['permissive_license'] = license_id in PERMISSIVE
    if license_id not in PERMISSIVE:
        return rec
    changed = [line.split('\t') for line in git(d, 'diff', '--name-status', '--no-renames', parent, full).splitlines()]
    py = [(s, p) for s, p in changed if p.endswith('.py')]
    rec['changed_files'] = [p for _, p in changed][:200]
    for status, path in py:
        before = git(d, 'show', f'{parent}:{path}', check=False) if status != 'A' else ''
        after = git(d, 'show', f'{full}:{path}', check=False) if status != 'D' else ''
        try:
            fb, fa = (functions(before) if before else {}), (functions(after) if after else {})
        except SyntaxError:
            rec['checks'].setdefault('unparseable', []).append(path)
            continue
        if is_test_path(path):
            for name, f in fa.items():
                short = name.rsplit('.', 1)[-1]
                if short.startswith('test') and (name not in fb or normalize(fb[name]['source']) != normalize(f['source'])):
                    rec['tests'].append({'path': path, 'name': name, 'new': name not in fb, 'source': f['source']})
            continue
        for name in sorted(set(fb) & set(fa)):
            b, a = fb[name], fa[name]
            if normalize(b['source']) == normalize(a['source']):
                continue
            rec['pairs'].append({'path': path, 'name': name, 'vulnerable': b['source'], 'fixed': a['source'],
                                 'vulnerable_span': [b['start'], b['end']], 'fixed_span': [a['start'], a['end']],
                                 'file_before_sha256': hashlib.sha256(before.encode()).hexdigest(),
                                 'file_lines_before': len(before.splitlines()),
                                 'file_scope': fix_scope(before, after, fb, fa)})
    rec['checks']['changed_functions'] = len(rec['pairs'])
    big = any(max(p['vulnerable_span'][1] - p['vulnerable_span'][0], p['fixed_span'][1] - p['fixed_span'][0]) > MAX_FUNC_LINES
              for p in rec['pairs'])
    rec['checks']['focused_fix'] = 1 <= len(rec['pairs']) <= MAX_CHANGED_FUNCS and not big
    if len(rec['pairs']) == 1:
        rec['scope'] = scope_checks(rec, rec['pairs'][0].pop('file_scope'))
    return rec


def rescan(harvest_files: list[pathlib.Path], work_dirs: list[pathlib.Path], out: pathlib.Path) -> dict:
    """Add fix scope to records harvested before scope analysis existed, from the cached fetches (no network)."""
    stats = {'rescanned': 0, 'missing_cache': 0, 'self_contained': 0}
    with out.open('w', encoding='utf-8') as f:
        for path in harvest_files:
            for line in path.read_text().splitlines():
                rec = json.loads(line)
                if len(rec.get('pairs', [])) != 1 or 'scope' in rec:
                    continue
                d = next((w / re.sub(r'[^a-z0-9]+', '_', rec['repo']) for w in work_dirs
                          if (w / re.sub(r'[^a-z0-9]+', '_', rec['repo'])).exists()), None)
                pair = rec['pairs'][0]
                try:
                    before = git(d, 'show', f"{rec['parent']}:{pair['path']}")
                    after = git(d, 'show', f"{rec['commit']}:{pair['path']}")
                except (RuntimeError, TypeError, subprocess.TimeoutExpired):
                    stats['missing_cache'] += 1
                    continue
                scope = scope_checks(rec, fix_scope(before, after, functions(before), functions(after)))
                stats['rescanned'] += 1; stats['self_contained'] += scope['self_contained']
                f.write(json.dumps({'key': rec['key'], 'scope': scope}) + '\n')
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidates', type=pathlib.Path)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--work', type=pathlib.Path, help='Scratch directory for blobless fetches.')
    ap.add_argument('--per-repo', type=int, default=12,
                    help='Cap advisories per repository *per period* (before/after --cutoff) to limit skew.')
    ap.add_argument('--cutoff', default='2025-07-01', help='Held-out time boundary; see build.py.')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--exclude-repo', action='append', default=[])
    ap.add_argument('--shard', default='0/1', help='k/n: process candidates whose key hashes to k (parallel fetchers).')
    ap.add_argument('--rescan', type=pathlib.Path, nargs='+', help='Harvest files to add fix scope to (uses --work-dirs).')
    ap.add_argument('--work-dirs', type=pathlib.Path, nargs='*', default=[])
    args = ap.parse_args(argv)
    if args.rescan:
        print(json.dumps(rescan(args.rescan, args.work_dirs or [args.work], args.out)))
        return
    if not args.candidates or not args.work:
        ap.error('--candidates and --work are required unless --rescan is given.')
    k, n = map(int, args.shard.split('/'))
    done = set()
    for prior in args.out.parent.glob('harvest*.jsonl'):  # resume across shards and earlier runs
        done |= {json.loads(x)['key'] for x in prior.read_text().splitlines() if x.strip()}
    rows = [json.loads(x) for x in args.candidates.read_text().splitlines() if x.strip()]
    per_repo: dict[tuple, int] = {}
    selected = []
    for row in rows:
        if row['repo'] in args.exclude_repo:
            continue
        # Cap each period separately: a date-sorted global cap would keep only a repository's oldest fixes.
        bucket = (row['repo'], row['published'] >= args.cutoff)
        per_repo[bucket] = per_repo.get(bucket, 0) + 1
        if per_repo[bucket] <= args.per_repo:
            selected.append(row)
    selected = [c for c in selected if int(hashlib.sha256(c['key'].encode()).hexdigest()[:8], 16) % n == k]
    if args.limit:
        selected = selected[:args.limit]
    stats = {'selected': len(selected), 'skipped_done': 0, 'ok': 0, 'error': 0}
    with args.out.open('a', encoding='utf-8') as f:
        for i, cand in enumerate(selected):
            if cand['key'] in done:
                stats['skipped_done'] += 1
                continue
            started = time.monotonic()
            try:
                rec = harvest_one(cand, args.work)
                stats['ok'] += 1
            except (RuntimeError, subprocess.TimeoutExpired, UnicodeError) as exc:
                rec = {'key': cand['key'], 'repo': cand['repo'], 'commit': cand['commit'], 'error': str(exc)[:300]}
                stats['error'] += 1
            rec['harvest_seconds'] = round(time.monotonic() - started, 2)
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            f.flush()
            if i % 25 == 0:
                print(json.dumps({'progress': i, **stats}), flush=True)
    print(json.dumps({'done': True, **stats}))


if __name__ == '__main__':
    main()
