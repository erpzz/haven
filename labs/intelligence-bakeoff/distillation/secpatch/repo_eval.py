"""Repository-level remediation check on held-out real fixes.

For each held-out fix that shipped its own tests:
  1. check out the fix commit in a disposable directory and install it into a fresh venv;
  2. run the fix's changed test functions on the fix                  -> must PASS
  3. restore the parent's (vulnerable) source, keep the fixed tests    -> must FAIL
     (only then is the regression test *validated*);
  4. for each candidate patch (recorded fix, model outputs from evaluate.py items.jsonl),
     put the candidate function into the parent source and rerun       -> PASS = remediation validated.
Installation errors and the recovery step that resolved them are logged as
events (the source of `recovery` examples).

Isolation: disposable directory, scrubbed environment, HOME inside the sandbox,
dead HTTP(S) proxy and no package index during test runs, per-run timeouts.
This host does not permit unprivileged network namespaces, so the test
process is not network-isolated at the kernel level.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap
import time

SANDBOX_ENV_KEEP = ('LANG', 'LC_ALL', 'TERM')


def run(cmd, cwd, env, timeout):
    started = time.monotonic()
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, errors='replace')
        code, out = r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired as exc:
        code, out = 'TIMEOUT', str(exc.stdout or '')[-2000:]
    return {'cmd': ' '.join(map(str, cmd))[:300], 'returncode': code, 'seconds': round(time.monotonic() - started, 1),
            'tail': out[-4000:]}


def sandbox_env(root: pathlib.Path, venv: pathlib.Path, offline: bool) -> dict:
    env = {k: os.environ[k] for k in SANDBOX_ENV_KEEP if k in os.environ}
    home = root / 'home'
    home.mkdir(exist_ok=True)
    env.update(HOME=str(home), PATH=f'{venv}/bin:/usr/bin:/bin', VIRTUAL_ENV=str(venv), PYTHONDONTWRITEBYTECODE='1',
               PIP_DISABLE_PIP_VERSION_CHECK='1', GIT_TERMINAL_PROMPT='0')
    if offline:
        env.update(http_proxy='http://127.0.0.1:9', https_proxy='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9',
                   HTTPS_PROXY='http://127.0.0.1:9', PIP_NO_INDEX='1')
    return env


def node_ids(tests: list[dict]) -> list[str]:
    return [f"{t['path']}::{t['name'].replace('.', '::')}" for t in tests]


def replace_function(source: str, qualname: str, new_code: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    target = None
    def walk(node, prefix):
        nonlocal target
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name
                if name == qualname and not isinstance(child, ast.ClassDef):
                    target = child
                walk(child, name + '.')
    walk(tree, '')
    if target is None:
        raise ValueError(f'{qualname} not found in parent source')
    start = min([d.lineno for d in target.decorator_list] + [target.lineno])
    indent = re.match(r'\s*', lines[start - 1]).group(0)
    body = textwrap.indent(textwrap.dedent(new_code).rstrip('\n') + '\n', indent)
    out = ''.join(lines[:start - 1]) + body + ''.join(lines[target.end_lineno:])
    ast.parse(out)
    return out


def install(work: pathlib.Path, venv: pathlib.Path, root: pathlib.Path, events: list) -> bool:
    env = sandbox_env(root, venv, offline=False)
    attempts = [['pip', 'install', '-q', '-e', '.[test]'], ['pip', 'install', '-q', '-e', '.[tests]'],
                ['pip', 'install', '-q', '-e', '.'], ['pip', 'install', '-q', '.']]
    base = run([venv / 'bin' / 'pip', 'install', '-q', 'pytest'], work, env, 600)
    if base['returncode'] != 0:
        events.append({'stage': 'install_pytest', **base}); return False
    last = None
    for cmd in attempts:
        r = run([venv / 'bin' / cmd[0], *cmd[1:]], work, env, 900)
        if r['returncode'] == 0:
            if last:
                events.append({'stage': 'install', 'error': last, 'recovery': r['cmd']})
            for req in ('requirements-test.txt', 'requirements-dev.txt', 'test-requirements.txt', 'requirements/test.txt'):
                if (work / req).exists():
                    events.append({'stage': 'test_requirements', **run([venv / 'bin' / 'pip', 'install', '-q', '-r', req], work, env, 900)})
            return True
        last = {'cmd': r['cmd'], 'tail': r['tail'][-600:]}
    events.append({'stage': 'install', 'error': last, 'recovery': None})
    return False


def failure_kind(output: str) -> str | None:
    """Why a pytest run failed. Only an assertion-style failure shows the test detects the vulnerability."""
    if re.search(r'^E\s+(assert\b|AssertionError|Failed: DID NOT RAISE|.*AssertionError)', output, re.M) or \
            re.search(r'^FAILED .* - (assert|AssertionError|Failed: DID NOT RAISE)', output, re.M):
        return 'assertion'
    if re.search(r'ERROR collecting|ImportError|ModuleNotFoundError|^E\s+NameError', output, re.M):
        return 'collection_or_import'
    return 'other_error'


def pytest(work, venv, root, ids, timeout):
    r = run([venv / 'bin' / 'python', '-m', 'pytest', '-q', '-x', '--tb=short', '-rf', '-p', 'no:cacheprovider',
             '-p', 'no:warnings', *ids], work, sandbox_env(root, venv, offline=True), timeout)
    summary = re.findall(r'^.*\b\d+ (?:passed|failed|error)[^\n]*$', r['tail'], re.M)
    passed = r['returncode'] == 0
    return {**r, 'passed': passed, 'summary': summary[-1].strip('= ') if summary else None,
            'failure_kind': None if passed else failure_kind(r['tail'])}


def workdir_for(sandbox: pathlib.Path, key: str) -> pathlib.Path:
    """Keep external advisory IDs inside the selected evaluation workspace.

    Keys are OSV grouping IDs (such as GHSA-*), not hashes. Refuse traversal,
    nested paths and pre-existing symlinks before cleaning an old workspace.
    """
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', key):
        raise ValueError('Invalid advisory ID for workspace path.')
    base = sandbox.resolve()
    target = base / key
    if target.is_symlink() or target.resolve().parent != base:
        raise ValueError('Evaluation workspace must stay inside the sandbox.')
    return target


def evaluate_fix(cand: dict, patches: dict, sandbox: pathlib.Path, timeout: int) -> dict:
    root = workdir_for(sandbox, cand['key'])
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    work, venv, events = root / 'repo', root / 'venv', []
    rec = {'key': cand['key'], 'repo': cand['repo'], 'commit': cand['commit'], 'tests': node_ids(cand['tests']),
           'events': events}
    clone = run(['git', 'clone', '-q', '--filter=blob:none', '--no-checkout', f"https://github.com/{cand['repo']}.git", str(work)],
                root, {**os.environ, 'GIT_TERMINAL_PROMPT': '0'}, 900)
    if clone['returncode'] != 0:
        return {**rec, 'status': 'CLONE_FAILED', 'detail': clone['tail'][-300:]}
    run(['git', 'checkout', '-q', cand['commit']], work, None, 600)
    subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
    if not install(work, venv, root, events):
        return {**rec, 'status': 'INSTALL_FAILED'}
    fixed = pytest(work, venv, root, rec['tests'], timeout)
    rec['on_fix'] = fixed
    if not fixed['passed']:
        return {**rec, 'status': 'TESTS_FAIL_ON_FIX'}
    changed = subprocess.run(['git', 'diff', '--name-only', cand['parent'], cand['commit']], cwd=work,
                             capture_output=True, text=True).stdout.split()
    sources = [p for p in changed if p.endswith('.py') and p not in {t['path'] for t in cand['tests']}]
    run(['git', 'checkout', '-q', cand['parent'], '--', *sources], work, None, 300)
    vuln = pytest(work, venv, root, rec['tests'], timeout)
    rec['on_parent'] = vuln
    if vuln['passed']:
        return {**rec, 'status': 'TEST_DOES_NOT_DETECT_VULNERABILITY'}
    if vuln['failure_kind'] != 'assertion':
        return {**rec, 'status': 'PARENT_FAILS_FOR_UNRELATED_REASON'}
    rec['status'] = 'REGRESSION_TEST_VALIDATED'
    parent_src = (work / cand['path']).read_text()
    rec['patches'] = {}
    for name, code in patches.items():
        if code is None:
            rec['patches'][name] = {'status': 'NO_CODE'}
            continue
        try:
            (work / cand['path']).write_text(replace_function(parent_src, cand['function'], code))
        except (ValueError, SyntaxError) as exc:
            rec['patches'][name] = {'status': 'DOES_NOT_APPLY', 'detail': str(exc)[:200]}
            continue
        r = pytest(work, venv, root, rec['tests'], timeout)
        rec['patches'][name] = {'status': 'PASS' if r['passed'] else 'FAIL', 'seconds': r['seconds'],
                                'summary': r['summary'], 'failure_kind': r['failure_kind'], 'tail': r['tail'][-400:]}
        (work / cand['path']).write_text(parent_src)
    return rec


def main(argv=None):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from evaluate import code_block
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidates', type=pathlib.Path, required=True)
    ap.add_argument('--sandbox', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--items', type=pathlib.Path, nargs='*', default=[],
                    help='evaluate.py items.jsonl files; their remediate outputs become candidate patches.')
    ap.add_argument('--fixed-source', type=pathlib.Path, help='eval-heldout.jsonl, for the recorded-fix positive control.')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--acknowledge-isolated-runner', action='store_true',
                    help='Required: execute only inside a disposable OS-isolated environment without host secrets.')
    args = ap.parse_args(argv)
    # The evaluator installs and executes third-party package code. A virtualenv,
    # private HOME and dead HTTP proxy are NOT kernel isolation. Refuse accidental
    # host execution; the operator must affirm an independently provisioned VM or
    # container. This flag is an explicit acknowledgment, not proof of isolation.
    if not args.acknowledge_isolated_runner:
        ap.error('Repository evaluation executes third-party Python code. Run inside a disposable, '
                 'OS-isolated VM/container without host secrets or network access, then supply '
                 '--acknowledge-isolated-runner. A virtualenv alone is insufficient.')
    cands = [json.loads(x) for x in args.candidates.read_text().splitlines() if x.strip()]
    if args.limit:
        cands = cands[:args.limit]
    recorded = {}
    if args.fixed_source:
        for line in args.fixed_source.read_text().splitlines():
            row = json.loads(line)
            if row['task'] == 'remediate':
                recorded[row['key']] = row['grader']['fixed']
    model_patches: dict[str, dict] = {}
    for path in args.items:
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row['task'] == 'remediate':
                model_patches.setdefault(row['key'], {})[f'{path.parent.name}:seed{row["seed"]}'] = code_block(row['output'])
    with args.out.open('a', encoding='utf-8') as f:
        for cand in cands:
            patches = {'recorded_fix': recorded.get(cand['key']), **model_patches.get(cand['key'], {})}
            rec = evaluate_fix(cand, patches, args.sandbox, args.timeout)
            rec['finished_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            f.write(json.dumps(rec) + '\n'); f.flush()
            print(json.dumps({'key': rec['key'], 'repo': rec['repo'], 'status': rec['status'],
                              'patches': {k: v['status'] for k, v in rec.get('patches', {}).items()}}), flush=True)
            shutil.rmtree(args.sandbox / cand['key'] / 'venv', ignore_errors=True)


if __name__ == '__main__':
    main()
