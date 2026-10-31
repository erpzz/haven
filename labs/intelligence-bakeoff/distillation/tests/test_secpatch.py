"""secpatch pipeline tests. Local git repositories and test doubles only: no network, no model."""
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'secpatch'))
sys.path.insert(0, str(HERE.parent))
import build  # noqa: E402
import fresh  # noqa: E402
from secpatch import evaluate  # noqa: E402 (avoid legacy distillation/evaluate.py)
import harvest  # noqa: E402
import osv  # noqa: E402
import registry  # noqa: E402
import repo_eval  # noqa: E402
import train  # noqa: E402

MIT = 'Permission is hereby granted, free of charge, to any person obtaining a copy ... The above copyright notice and this permission notice shall be included'
VULN = '''import subprocess


def other():
    return 1


def run_tool(name):
    """Run a tool."""
    return subprocess.call("tool " + name, shell=True)
'''
FIXED = '''import subprocess


def other():
    return 1


def run_tool(name):
    """Run a tool."""
    return subprocess.call(["tool", name])
'''
TEST = '''from app import run_tool


def test_no_shell():
    assert run_tool is not None
'''


def git(cwd, *args):
    env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.invalid',
           'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.invalid'}
    return subprocess.run(['git', *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


def make_repo(root: pathlib.Path, license_text=MIT, cosmetic=False):
    root.mkdir(parents=True)
    git(root, 'init', '-q')
    git(root, 'config', 'uploadpack.allowReachableSHA1InWant', 'true')
    git(root, 'config', 'uploadpack.allowFilter', 'true')
    (root / 'LICENSE').write_text(license_text)
    (root / 'app.py').write_text(VULN)
    git(root, 'add', '.'); git(root, 'commit', '-qm', 'initial')
    (root / 'app.py').write_text(VULN.replace('return 1', 'return  1') if cosmetic else FIXED)
    (root / 'tests').mkdir(); (root / 'tests' / 'test_app.py').write_text(TEST)
    git(root, 'add', '.'); git(root, 'commit', '-qm', 'Avoid shell=True in run_tool')
    return git(root, 'rev-parse', 'HEAD')


class LicenseTests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(harvest.classify_license(MIT), 'MIT')
        self.assertEqual(harvest.classify_license('Apache License Version 2.0, January 2004'), 'Apache-2.0')
        self.assertEqual(harvest.classify_license('Redistribution and use in source and binary forms ... Neither the name'), 'BSD-3-Clause')
        self.assertEqual(harvest.classify_license('GNU General Public License version 3'), 'GPL')
        self.assertIsNone(harvest.classify_license('All rights reserved.'))
        self.assertNotIn('GPL', harvest.PERMISSIVE)


class OsvTests(unittest.TestCase):
    def test_alias_grouping_fix_preference_and_malware_skip(self):
        with tempfile.TemporaryDirectory() as t:
            z = pathlib.Path(t) / 'all.zip'
            with zipfile.ZipFile(z, 'w') as f:
                f.writestr('a.json', json.dumps({'id': 'GHSA-aaaa', 'aliases': ['CVE-1'], 'published': '2025-08-01T00:00:00Z',
                    'summary': 'Command injection in run_tool', 'database_specific': {'cwe_ids': ['CWE-78']},
                    'references': [{'type': 'WEB', 'url': 'https://github.com/o/r/commit/' + 'b' * 40},
                                   {'type': 'FIX', 'url': 'https://github.com/o/r/commit/' + 'a' * 40}]}))
                f.writestr('b.json', json.dumps({'id': 'PYSEC-1', 'aliases': ['CVE-1'], 'published': '2025-07-30T00:00:00Z',
                    'references': [{'type': 'FIX', 'url': 'https://github.com/o/r/commit/' + 'a' * 40}]}))
                f.writestr('c.json', json.dumps({'id': 'MAL-1', 'references': [{'type': 'FIX', 'url': 'https://github.com/x/y/commit/' + 'c' * 40}]}))
            rows = osv.candidates(z)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['repo'], rows[0]['commit']), ('o/r', 'a' * 40))
        self.assertEqual(rows[0]['published'], '2025-07-30T00:00:00Z')
        self.assertEqual(rows[0]['cwes'], ['CWE-78'])
        self.assertEqual({a['license'] for a in rows[0]['advisories']}, {'CC-BY-4.0'})


class HarvestTests(unittest.TestCase):
    def harvest(self, **kw):
        with tempfile.TemporaryDirectory() as t:
            sha = make_repo(pathlib.Path(t) / 'origin', **kw)
            remote = lambda repo: str(pathlib.Path(t) / 'origin')
            return harvest.harvest_one({'key': 'K', 'repo': 'o/r', 'commit': sha}, pathlib.Path(t) / 'work', remote)

    def test_extracts_single_changed_function_and_test(self):
        rec = self.harvest()
        self.assertTrue(rec['checks']['permissive_license'] and rec['checks']['focused_fix'])
        self.assertEqual([p['name'] for p in rec['pairs']], ['run_tool'])
        self.assertIn('shell=True', rec['pairs'][0]['vulnerable'])
        self.assertEqual([t['name'] for t in rec['tests']], ['test_no_shell'])
        self.assertEqual(rec['commit_message'], 'Avoid shell=True in run_tool')

    def test_cosmetic_change_is_not_a_pair(self):
        self.assertEqual(self.harvest(cosmetic=True)['pairs'], [])

    def test_scope_flags_helpers_and_imports_outside_the_function(self):
        before = 'def f(p):\n    return open(p)\n'
        helper = 'def _inside(p):\n    return True\n\n\ndef f(p):\n    assert _inside(p)\n    return open(p)\n'
        imported = 'import os\n\n\ndef f(p):\n    return open(os.path.basename(p))\n'
        local = 'def f(p):\n    if ".." in p:\n        raise ValueError(p)\n    return open(p)\n'
        fn = harvest.functions
        self.assertEqual(harvest.fix_scope(before, helper, fn(before), fn(helper))['added_functions'], ['_inside'])
        self.assertTrue(harvest.fix_scope(before, imported, fn(before), fn(imported))['module_level_changed'])
        scope = harvest.fix_scope(before, local, fn(before), fn(local))
        self.assertEqual((scope['added_functions'], scope['module_level_changed']), ([], False))
        rec = {'changed_files': ['pkg/a.py', 'tests/test_a.py', 'CHANGES.md'], 'pairs': [{'path': 'pkg/a.py'}]}
        self.assertTrue(harvest.scope_checks(rec, scope)['self_contained'])
        rec['changed_files'].append('pkg/b.py')
        self.assertFalse(harvest.scope_checks(rec, scope)['self_contained'])

    def test_harvest_records_scope(self):
        self.assertTrue(self.harvest()['scope']['self_contained'])

    def test_non_permissive_repo_excluded(self):
        rec = self.harvest(license_text='GNU General Public License v3')
        self.assertFalse(rec['checks']['permissive_license']); self.assertEqual(rec['pairs'], [])


class BuildTests(unittest.TestCase):
    def test_split_isolates_repository_and_time(self):
        repos = [f'org/repo{i}' for i in range(200)]
        held = [r for r in repos if build.repo_bucket(r) == 'heldout']
        self.assertTrue(20 < len(held) < 80)
        self.assertIsNone(build.split_for(held[0], '2024-01-01', '2025-07-01'))
        self.assertEqual(build.split_for(held[0], '2025-08-01', '2025-07-01'), 'heldout')
        trainer = next(r for r in repos if r not in held)
        self.assertEqual(build.split_for(trainer, '2024-01-01', '2025-07-01'), 'train')
        self.assertEqual(build.split_for(trainer, '2025-08-01', '2025-07-01'), 'dev')

    def test_changed_lines_point_into_vulnerable_function(self):
        pair = {'vulnerable': 'def f(x):\n    a = 1\n    return eval(x)\n', 'fixed': 'def f(x):\n    a = 1\n    return int(x)\n',
                'vulnerable_span': [10, 12]}
        self.assertEqual(build.changed_lines(pair), [12])

    def end_to_end(self, published):
        with tempfile.TemporaryDirectory() as t:
            t = pathlib.Path(t)
            sha = make_repo(t / 'origin')
            rec = harvest.harvest_one({'key': 'K1', 'repo': 'o/r', 'commit': sha}, t / 'work', lambda r: str(t / 'origin'))
            cand = {'key': 'K1', 'repo': 'o/r', 'commit': sha, 'published': published, 'summary': 'Shell injection in run_tool',
                    'details': 'run_tool passes a name to a shell.', 'cwes': ['CWE-78'],
                    'advisories': [{'id': 'GHSA-x', 'source_db': 'GHSA', 'license': 'CC-BY-4.0'}], 'osv_archive_sha256': '0' * 64}
            (t / 'c.jsonl').write_text(json.dumps(cand) + '\n')
            (t / 'h.jsonl').write_text(json.dumps(rec) + '\n')
            fake = t / 'bandit'  # TEST DOUBLE: reports B602 on files containing shell=True
            fake.write_text('#!/usr/bin/env python3\nimport json,pathlib,sys\nif "--version" in sys.argv: print("fake-bandit"); sys.exit()\n'
                            'root=pathlib.Path(sys.argv[-1]); res=[]\nfor f in root.glob("*.py"):\n'
                            '    if "shell=True" in f.read_text(): res.append({"filename":str(f),"test_id":"B602","test_name":"subprocess_popen_with_shell_equals_true",'
                            '"issue_text":"subprocess call with shell=True identified","issue_severity":"HIGH","issue_confidence":"HIGH"})\n'
                            'print(json.dumps({"results":res,"errors":[]}))\n')
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            build.main(['--candidates', str(t / 'c.jsonl'), '--harvest', str(t / 'h.jsonl'), '--out', str(t / 'out'),
                        '--bandit', str(fake)])
            files = {f.name: [json.loads(x) for x in f.read_text().splitlines()] for f in (t / 'out').glob('*.jsonl')}
            return files.__getitem__, json.loads((t / 'out' / 'manifest.json').read_text())

    def test_build_rows_attribution_and_verification(self):
        read, manifest = self.end_to_end('2024-01-01T00:00:00Z')
        split = build.split_for('o/r', '2024-01-01T00:00:00Z', '2025-07-01')
        if split is None:
            self.skipTest('o/r hashes to the held-out bucket')
        rows = read(f'{split}.jsonl')
        tasks = {r['task'] for r in rows}
        self.assertEqual(tasks, {'detect', 'root_cause', 'remediate', 'regression_test', 'tool_select', 'finding_support'})
        for r in rows:
            self.assertEqual(r['source']['code_license'], 'MIT')
            self.assertEqual(r['source']['advisory_ids'], ['GHSA-x'])
            self.assertEqual(r['messages'][-1]['role'], 'assistant')
        tool = next(r for r in rows if r['task'] == 'tool_select')
        self.assertIn('B602', tool['messages'][-1]['content'])
        self.assertTrue(tool['verification']['tool_verified'])
        self.assertEqual(manifest['filters']['tool_verified'], 1)

    def test_multi_function_rows_show_every_function_and_stay_out_of_eval(self):
        pairs = [{'path': 'a.py', 'name': 'run_tool', 'vulnerable': 'def run_tool(n):\n    return call(n, shell=True)',
                  'fixed': 'def run_tool(n):\n    return call([n])', 'vulnerable_span': [10, 11], 'fixed_span': [10, 11]},
                 {'path': 'b.py', 'name': 'helper', 'vulnerable': 'def helper(x):\n    return x',
                  'fixed': 'def helper(x):\n    return quote(x)', 'vulnerable_span': [3, 4], 'fixed_span': [3, 4]}]
        item = {'key': 'K', 'repo': 'o/r', 'split': 'train', 'pair': pairs[0], 'pairs': pairs, 'cwes': ['CWE-78'],
                'changed_lines': build.changed_lines(pairs[0]), 'summary': 'Shell injection', 'details': '',
                'commit_message': 'fix shell injection', 'license': 'MIT', 'tests': [],
                'advisories': [{'id': 'GHSA-x', 'license': 'CC-BY-4.0'}]}
        rows = build.multi_tasks_for(item, 'decoy_fn')
        self.assertEqual({r['task'] for r in rows}, {'detect', 'root_cause', 'finding_support'})
        detect = next(r for r in rows if r['task'] == 'detect' and r['label'] == 'vulnerable')
        self.assertIn('shell=True', detect['messages'][1]['content'])
        self.assertIn('File: b.py (function `helper`)', detect['messages'][1]['content'])
        self.assertEqual(json.loads(detect['messages'][-1]['content'])['evidence_lines'], [11])
        self.assertTrue(all(r['verification']['multi_function_fix'] == 2 for r in rows))

    def test_eval_items_hide_reference(self):
        read, _ = self.end_to_end('2026-01-01T00:00:00Z')
        split = build.split_for('o/r', '2026-01-01T00:00:00Z', '2025-07-01')
        items = read(f'eval-{split}.jsonl')
        self.assertTrue(items)
        for item in items:
            self.assertNotEqual(item['messages'][-1]['role'], 'assistant')
            if item['task'] == 'remediate':
                self.assertNotIn('["tool", name]', item['messages'][-1]['content'])


class GraderTests(unittest.TestCase):
    def item(self, task, label, content='  10 | def run_tool(name):\n  11 |     return subprocess.call("tool " + name, shell=True)'):
        return {'messages': [{'role': 'user', 'content': content}],
                'grader': {'task': task, 'label': label, 'function': 'run_tool', 'cwe': ['CWE-78'], 'changed_lines': [11],
                           'bandit': {'test_id': 'B602'}, 'vulnerable': VULN.split('\n\n\n')[-1], 'fixed': FIXED.split('\n\n\n')[-1]}}

    def test_detect_true_positive_and_false_positive(self):
        g = evaluate.grade(self.item('detect', 'vulnerable'),
                           '<think>x</think>{"verdict":"vulnerable","function":"run_tool","cwe":["CWE-78"],"evidence_lines":[11]}', 'bandit')
        self.assertEqual((g['score'], g['cwe_match'], g['evidence_hit'], g['unsupported']), (1, True, True, False))
        g = evaluate.grade(self.item('detect', 'not_vulnerable'), '{"verdict":"vulnerable","function":"run_tool","evidence_lines":[11]}', 'bandit')
        self.assertEqual((g['score'], g['false_positive']), (0, True))

    def test_unsupported_assertions(self):
        g = evaluate.grade(self.item('detect', 'vulnerable'), '{"verdict":"vulnerable","function":"exec_payload","evidence_lines":[99]}', 'bandit')
        self.assertTrue(g['unsupported'])
        self.assertTrue(evaluate.grade(self.item('detect', 'vulnerable'), 'not json', 'bandit')['invalid_json'])

    def test_finding_tool_and_root_cause(self):
        self.assertEqual(evaluate.grade(self.item('finding_support', 'stale'), '{"supported": false}', 'b')['score'], 1)
        self.assertTrue(evaluate.grade(self.item('finding_support', 'nonexistent'), '{"supported": true}', 'b')['false_positive'])
        self.assertEqual(evaluate.grade(self.item('tool_select', 'B602'), '{"tool":"Bandit","rule":"B602"}', 'b')['score'], 1)
        self.assertEqual(evaluate.grade(self.item('root_cause', 'CWE-78'), '{"cwe":["CWE-79"]}', 'b')['score'], 0)
        named = '{"cwe":["CWE-78: Improper Neutralization of Special Elements used in an OS Command"]}'
        self.assertEqual(evaluate.grade(self.item('root_cause', 'CWE-78'), named, 'b')['score'], 1)
        self.assertFalse(evaluate.cwe_ids(['CWE-78: OS command injection']) & evaluate.cwe_ids(['CWE-7']))
        self.assertEqual(evaluate.cwe_ids(['cwe-79', 'CWE 20', 'none']), {'CWE-79', 'CWE-20'})

    def test_remediation_requires_signature_and_change(self):
        fixed = '```python\n' + FIXED.split('\n\n\n')[-1] + '\n```'
        with unittest.mock.patch.object(evaluate, 'bandit_rules', return_value=set()):
            g = evaluate.grade(self.item('remediate', 'fix'), fixed, 'bandit')
        self.assertEqual((g['score'], g['matches_recorded_fix'], g['bandit_cleared']), (1, True, True))
        renamed = '```python\ndef other_name(name):\n    return 1\n```'
        self.assertEqual(evaluate.grade(self.item('remediate', 'fix'), renamed, 'bandit')['score'], 0)
        same = '```python\n' + VULN.split('\n\n\n')[-1] + '\n```'
        self.assertEqual(evaluate.grade(self.item('remediate', 'fix'), same, 'bandit')['score'], 0)

    def test_tool_evidence_uses_absolute_lines(self):
        issue = [{'test_id': 'B602', 'test_name': 'subprocess_popen_with_shell_equals_true', 'line_number': 2,
                  'issue_text': 'shell=True', 'issue_severity': 'HIGH', 'issue_confidence': 'HIGH'}]
        item = self.item('detect', 'vulnerable', 'Review\n```python\n   10 | def run_tool(name):\n   11 |     return call(name, shell=True)\n```')
        with unittest.mock.patch.object(evaluate, 'bandit_issues', return_value=issue) as run:
            msgs = evaluate.with_tool_evidence(item, 'bandit')
        self.assertEqual(run.call_args[0][1], 'def run_tool(name):\n    return call(name, shell=True)')
        self.assertIn('B602 subprocess_popen_with_shell_equals_true at line 11', msgs[-1]['content'])
        self.assertNotIn('Tool evidence', item['messages'][-1]['content'])

    def test_copied_line_number_gutter_is_stripped_and_counted(self):
        fixed = FIXED.split('\n\n\n')[-1]
        gutter = '```python\n' + '\n'.join(f'{10 + i:>5} | {l}' for i, l in enumerate(fixed.splitlines())) + '\n```'
        with unittest.mock.patch.object(evaluate, 'bandit_rules', return_value=set()):
            g = evaluate.grade(self.item('remediate', 'fix'), gutter, 'bandit')
        self.assertEqual((g['score'], g['gutter_stripped'], g['matches_recorded_fix']), (1, True, True))
        mixed = '```python\n   10 | def run_tool(name):\nreturn 1\n```'
        self.assertFalse(evaluate.strip_gutter(mixed.split('\n', 1)[1].rsplit('```', 1)[0])[1])

    def test_summary_paired_and_wilson(self):
        rows = [{'key': 'a', 'task': 'detect', 'label': 'vulnerable', 'score': 1, 'false_positive': False, 'unsupported': False,
                 'invalid_json': False, 'latency_s': 1, 'completion_tokens': 5, 'seed': 0},
                {'key': 'a', 'task': 'detect', 'label': 'not_vulnerable', 'score': 0, 'false_positive': True, 'unsupported': False,
                 'invalid_json': False, 'latency_s': 1, 'completion_tokens': 5, 'seed': 0}]
        s = evaluate.summarize(rows, 'x', 'm')
        self.assertEqual((s['paired_detection'], s['false_positive_rate'], s['detection_recall']), (0.0, 1.0, 1.0))
        self.assertEqual((s['detection_positive_n'], s['detection_negative_n']), (1, 1))
        self.assertEqual(evaluate.wilson(0, 0), [0.0, 0.0])


class CaseArmTests(unittest.TestCase):
    def row(self, split, code, fixed, repo):
        user = f'Reported issue: shell injection\n\nRewrite...\n\nRepository: {repo}\nFile: a.py\n```python\n' + \
            '\n'.join(f'{10 + i:>5} | {l}' for i, l in enumerate(code.splitlines())) + '\n```'
        return {'split': split, 'task': 'remediate', 'source': {'repo': repo, 'advisory_ids': ['GHSA-x']},
                'messages': [{'role': 'system', 'content': 's'}, {'role': 'user', 'content': user},
                             {'role': 'assistant', 'content': f'```python\n{fixed}\n```'}]}

    def test_retrieves_nearest_training_case_and_refuses_eval_rows(self):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t) / 'train.jsonl'
            near = 'def run(name):\n    return subprocess.call("tool " + name, shell=True)'
            far = 'def parse(x):\n    return yaml.load(x)'
            p.write_text('\n'.join(json.dumps(self.row('train', c, 'def f(): pass', r)) for c, r in ((near, 'a/near'), (far, 'b/far'))))
            idx = evaluate.CaseIndex(p)
            self.assertEqual(idx.nearest('def go(n):\n    return subprocess.call("x " + n, shell=True)', 1)[0]['repo'], 'a/near')
            msgs = evaluate.with_cases([{'role': 'user', 'content': 'review\n```python\n   1 | def go(n): os.system(n)\n```'}], idx, 1)
            self.assertIn('similar past security fixes', msgs[-1]['content'])
            p.write_text(json.dumps(self.row('heldout', near, 'x', 'c/eval')))
            with self.assertRaises(ValueError):
                evaluate.CaseIndex(p)

    def test_lora_targets_are_architecture_aware(self):
        self.assertEqual(train.lora_targets('Qwen/Qwen3-0.6B'), train.TARGET_MODULES)
        self.assertEqual(train.lora_targets('LiquidAI/LFM2.5-8B-A1B'), 'all-linear')


class FreshTests(unittest.TestCase):
    def test_select_only_new_unseen_non_training(self):
        c = lambda k, repo, pub: {'key': k, 'repo': repo, 'published': pub}
        cands = [c('old', 'x/a', '2026-09-01'), c('seen', 'x/a', '2026-10-29'), c('train', 't/r', '2026-10-29'),
                 c('ok1', 'x/a', '2026-10-29'), c('ok2', 'x/a', '2026-10-29'), c('ok3', 'x/a', '2026-10-29'),
                 c('cap', 'x/a', '2026-10-30'), c('ok4', 'y/b', '2026-10-30')]
        got = [x['key'] for x in fresh.select(cands, '2026-10-28', {'seen'}, {'t/r'}, 10)]
        self.assertEqual(got, ['ok1', 'ok2', 'ok3', 'ok4'])  # at most 3 per repository


class ReportTests(unittest.TestCase):
    def test_resummarize_uses_only_shared_items(self):
        # Load secpatch/report.py by path: tool_sft/report.py shares the module name in a full test run.
        import importlib.util
        spec = importlib.util.spec_from_file_location('secpatch_report', HERE.parent / 'secpatch' / 'report.py')
        report = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(report)
        def row(i, task, score):
            return {'id': i, 'key': i, 'task': task, 'label': 'vulnerable', 'seed': 0, 'score': score, 'false_positive': False,
                    'unsupported': False, 'invalid_json': False, 'latency_s': 1.0, 'completion_tokens': 3}
        with tempfile.TemporaryDirectory() as t:
            a, b = pathlib.Path(t) / 'a', pathlib.Path(t) / 'b'
            a.mkdir(); b.mkdir()
            (a / 'items.jsonl').write_text('\n'.join(json.dumps(r) for r in [row('1', 'detect', 1), row('2', 'remediate', 1)]))
            (b / 'items.jsonl').write_text(json.dumps(row('1', 'detect', 0)))
            with unittest.mock.patch.dict(sys.modules, {'evaluate': evaluate}):
                sa, sb = report.resummarize([a / 'items.jsonl', b / 'items.jsonl'], None)
        self.assertEqual((sa['n'], sb['n']), (1, 1))
        self.assertEqual(sa['eval_sha256'], sb['eval_sha256'])
        self.assertEqual((sa['score'], sb['score']), (1.0, 0.0))


class RegistryAndTrainTests(unittest.TestCase):
    def run_dir(self, t, classification):
        d = pathlib.Path(t) / 'run'
        (d / 'adapter').mkdir(parents=True)
        (d / 'adapter' / 'adapter_config.json').write_text('{}')
        # Unit fixture only: this does not execute or claim actual GPU training.
        weights = b'unit-fixture-not-a-trained-model'
        (d / 'adapter' / 'adapter_model.safetensors').write_bytes(weights)
        import hashlib
        (d / 'receipt.json').write_text(json.dumps({
            'classification': classification, 'device': 'cuda' if classification == 'GPU_TRAINING_RUN' else 'cpu',
            'execute': True, 'optimizer_steps': 2, 'train_loss': 1.25,
            'cuda_evidence': {'optimizer_steps': 2, 'device_name': 'UNIT_TEST_ONLY',
                              'total_memory_bytes': 1024, 'peak_allocated_bytes': 64,
                              'trainable_cuda_parameters': 2},
            'adapter_weights_sha256': {'adapter_model.safetensors': hashlib.sha256(weights).hexdigest()},
            'base_model': 'Qwen/Qwen3-0.6B', 'base_revision': 'c1899de', 'data_sha256': '0' * 64}))
        return d

    def summary(self, t, name, score, fpr, recall=0.9):
        p = pathlib.Path(t) / f'{name}.json'
        p.write_text(json.dumps({'eval_sha256': 'E', 'score': score, 'false_positive_rate': fpr,
                                 'detection_recall': recall, 'detection_positive_n': 3, 'detection_negative_n': 3,
                                 'by_task': {'detect': {'n': 6}}, 'n': 10, 'model': name}))
        return p

    def test_constant_answer_collapse_is_not_promoted(self):
        # Measured 2026-10-30: the seed-42 adapter raised score 0.382 -> 0.483 by answering "not vulnerable" to everything.
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t) / 'reg'
            registry.register(root, self.run_dir(t, 'GPU_TRAINING_RUN'), 'collapsed')
            registry.attach_eval(root, 'base', self.summary(t, 'base', 0.382, 0.81, recall=0.84))
            registry.attach_eval(root, 'collapsed', self.summary(t, 'collapsed', 0.483, 0.0, recall=0.0))
            with self.assertRaisesRegex(ValueError, 'discrimination'):
                registry.promote(root, 'collapsed', 'E')

    def test_cpu_check_cannot_be_registered(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                registry.register(pathlib.Path(t) / 'reg', self.run_dir(t, 'CPU_PIPELINE_CHECK'), 'v1')

    def test_registration_rejects_missing_gpu_evidence_and_tampered_weights(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t) / 'registry'
            run = self.run_dir(t, 'GPU_TRAINING_RUN')
            receipt_path = run / 'receipt.json'
            original = json.loads(receipt_path.read_text())
            for altered in ({**original, 'execute': False},
                            {**original, 'device': 'cpu'},
                            {**original, 'optimizer_steps': 0},
                            {**original, 'cuda_evidence': {}},
                            {**original, 'adapter_weights_sha256': {}}):
                with self.subTest(changed=list(altered)), self.assertRaises(ValueError):
                    receipt_path.write_text(json.dumps(altered))
                    registry.register(root, run, 'not-a-run')
            receipt_path.write_text(json.dumps(original))
            (run / 'adapter' / 'adapter_model.safetensors').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                registry.register(root, run, 'not-a-run')
            self.assertFalse((root / 'registry.json').exists())

    def test_gated_promotion_and_rollback(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t) / 'reg'
            registry.register(root, self.run_dir(t, 'GPU_TRAINING_RUN'), 'v1')
            registry.attach_eval(root, 'base', self.summary(t, 'base', 0.30, 0.2))
            registry.attach_eval(root, 'v1', self.summary(t, 'v1', 0.28, 0.1))
            with self.assertRaises(ValueError):
                registry.promote(root, 'v1', 'E')
            registry.attach_eval(root, 'v1', self.summary(t, 'v1', 0.40, 0.3))
            with self.assertRaises(ValueError):  # better score, worse false positives
                registry.promote(root, 'v1', 'E')
            registry.attach_eval(root, 'v1', self.summary(t, 'v1', 0.40, 0.2, recall=0.95))
            self.assertEqual(registry.promote(root, 'v1', 'E'), {'promoted': 'v1'})
            self.assertEqual(registry.card(root)['base_revision'], 'c1899de')
            self.assertEqual(registry.rollback(root), {'promoted': None})
            self.assertIsNone(registry.card(root)['promoted'])
            with self.assertRaises(ValueError):
                registry.register(root, self.run_dir(t + '/x', 'GPU_TRAINING_RUN'), 'v1')

    def test_promotion_rejects_recall_collapse_and_unusable_evaluations(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t) / 'reg'
            registry.register(root, self.run_dir(t, 'GPU_TRAINING_RUN'), 'v1')
            registry.attach_eval(root, 'base', self.summary(t, 'base', 33 / 72, 1.0, 10 / 12))
            registry.attach_eval(root, 'v1', self.summary(t, 'v1', 35 / 72, 2 / 12, 1 / 12))
            with self.assertRaisesRegex(ValueError, 'recall'):
                registry.promote(root, 'v1', 'E')
            self.assertIsNone(registry.load(root)['promoted'])

            valid = json.loads(self.summary(t, 'v1', 0.5, 0.1, 0.9).read_text())
            invalid_cases = [
                {k: v for k, v in valid.items() if k != 'detection_recall'},
                {k: v for k, v in valid.items() if k != 'detection_positive_n'},
                {**valid, 'detection_positive_n': 0},
                {**valid, 'detection_recall': float('nan')},
                {**valid, 'detection_negative_n': 2},
                {**valid, 'detection_positive_n': 2, 'detection_negative_n': 4},
                {**valid, 'by_task': None},
            ]
            for summary in invalid_cases:
                with self.subTest(summary=summary):
                    path = pathlib.Path(t) / 'invalid.json'
                    path.write_text(json.dumps(summary))
                    registry.attach_eval(root, 'v1', path)
                    with self.assertRaises(ValueError):
                        registry.promote(root, 'v1', 'E')
                    self.assertIsNone(registry.load(root)['promoted'])

            registry.attach_eval(root, 'v1', self.summary(t, 'v1', 0.5, 0.1, 10 / 12))
            self.assertEqual(registry.promote(root, 'v1', 'E'), {'promoted': 'v1'})

    def test_train_refuses_eval_rows_and_dry_runs(self):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t) / 'd.jsonl'
            row = {'id': '1', 'task': 'detect', 'split': 'heldout', 'messages': [{'role': 'user', 'content': 'x'}, {'role': 'assistant', 'content': 'y'}]}
            p.write_text(json.dumps(row) + '\n')
            with self.assertRaises(ValueError):
                train.load_rows(p, None)
            p.write_text(json.dumps({**row, 'split': 'train'}) + '\n')
            plan = train.main(['--data', str(p), '--revision', 'r', '--output', str(pathlib.Path(t) / 'o')])
            self.assertFalse(plan['execute'])
            with self.assertRaises(SystemExit):  # CPU mode is a capped pipeline check
                train.main(['--data', str(p), '--revision', 'r', '--output', str(pathlib.Path(t) / 'o'),
                            '--device', 'cpu', '--max-steps', '50', '--execute'])


class RepoEvalTests(unittest.TestCase):
    def test_replace_function_preserves_rest_and_indent(self):
        src = 'class A:\n    def f(self):\n        return 1\n\n    def g(self):\n        return 2\n'
        out = repo_eval.replace_function(src, 'A.f', 'def f(self):\n    return 3\n')
        self.assertEqual(out, 'class A:\n    def f(self):\n        return 3\n\n    def g(self):\n        return 2\n')
        with self.assertRaises(ValueError):
            repo_eval.replace_function(src, 'A.h', 'def h(self): pass')

    def test_failure_kind_separates_detection_from_breakage(self):
        self.assertEqual(repo_eval.failure_kind('E   assert 302 == 404\nFAILED t.py::x'), 'assertion')
        self.assertEqual(repo_eval.failure_kind('FAILED t.py::x - AssertionError: open redirect'), 'assertion')
        self.assertEqual(repo_eval.failure_kind('ERROR collecting tests/t.py\nImportError: cannot import name'), 'collection_or_import')
        self.assertEqual(repo_eval.failure_kind('E   TypeError: bad'), 'other_error')

    def test_recovery_uses_only_declared_test_dependencies(self):
        with tempfile.TemporaryDirectory() as t:
            w = pathlib.Path(t)
            self.assertEqual(repo_eval.declared_test_installs(w), [])
            (w / 'pyproject.toml').write_text('[dependency-groups]\ndev = ["opentelemetry-sdk"]\n'
                                              '[project]\nname = "x"\n[project.optional-dependencies]\ntest = ["rich"]\n')
            self.assertEqual(repo_eval.declared_test_installs(w), [['pip', 'install', '-q', '--group', 'dev'],
                                                                   ['pip', 'install', '-q', '-e', '.[test]']])
        self.assertEqual(repo_eval.missing_module("E   ModuleNotFoundError: No module named 'opentelemetry.sdk'"), 'opentelemetry.sdk')

    def test_node_ids(self):
        self.assertEqual(repo_eval.node_ids([{'path': 'tests/t.py', 'name': 'TestX.test_y'}]), ['tests/t.py::TestX::test_y'])

    def test_sandbox_env_is_scrubbed(self):
        with tempfile.TemporaryDirectory() as t, unittest.mock.patch.dict(os.environ, {'HF_TOKEN': 'secret', 'SSH_AUTH_SOCK': '/x'}):
            env = repo_eval.sandbox_env(pathlib.Path(t), pathlib.Path(t) / 'venv', offline=True)
        self.assertNotIn('HF_TOKEN', env); self.assertNotIn('SSH_AUTH_SOCK', env)
        self.assertTrue(env['HOME'].startswith(t)); self.assertEqual(env['PIP_NO_INDEX'], '1')


import unittest.mock  # noqa: E402

if __name__ == '__main__':
    unittest.main()
