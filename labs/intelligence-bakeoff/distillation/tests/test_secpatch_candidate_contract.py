"""Fail-closed secpatch input checks. No third-party repository code is executed."""
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'secpatch'))
from candidate_contract import validate_candidate, safe_source_path
import repo_eval

SHA = 'a' * 40
BASE = {'key': 'GHSA-aaaa-bbbb-cccc', 'repo': 'owner/repo', 'commit': SHA,
        'parent': 'b' * 40, 'path': 'src/core.py', 'function': 'Handler.handle',
        'tests': [{'path': 'tests/test_core.py', 'name': 'TestHandler.test_case'}]}


class CandidateContractTests(unittest.TestCase):
    def test_accepts_valid_harvest_record(self):
        validate_candidate(BASE)

    def test_rejects_repo_and_revision_attacks(self):
        for field, values in {'repo': ['-c/foo', '../repo', 'owner/../repo',
                                       'https://evil.example/repo', 'owner/repo\\nfoo'],
                              'commit': ['--help', 'main', '../evil', 'a' * 39],
                              'parent': ['-x', 'b' * 41]}.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_candidate({**BASE, field: value})

    def test_rejects_path_and_pytest_option_attacks(self):
        for field, values in {'path': ['../../outside.py', '/tmp/outside.py',
                                       'src/../outside.py', 'src//core.py',
                                       'src\\\\core.py', 'src/-option.py', 'src/config.toml'],
                              'function': ['-k', 'Handler.__class__/oops', ''],
                              'tests': [[{'path': '../bad.py', 'name': 'test_ok'}],
                                        [{'path': 'tests/test.py', 'name': '--override-ini'}],
                                        [], [{}]]}.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    validate_candidate({**BASE, field: value})

    def test_refuses_symlinked_source_and_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            work = root / 'repo'; work.mkdir()
            (work / 'src').mkdir()
            (work / 'src' / 'core.py').write_text('def f(): pass\\n')
            self.assertEqual(safe_source_path(work, 'src/core.py'), work / 'src' / 'core.py')
            (work / 'src' / 'link.py').symlink_to(root / 'outside.py')
            with self.assertRaises(ValueError):
                safe_source_path(work, 'src/link.py')
            (work / 'linked').symlink_to(work / 'src', target_is_directory=True)
            with self.assertRaises(ValueError):
                safe_source_path(work, 'linked/core.py')

    def test_refuses_missing_source_and_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp); root.joinpath('repo').mkdir()
            for path in ('missing.py', '../outside.py', '/etc/passwd'):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    safe_source_path(root / 'repo', path)

    def test_evaluator_rejects_bad_candidate_before_clone_or_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            wheelhouse = root / 'wheels'; wheelhouse.mkdir()
            sandbox = root / 'sandbox'
            bad = {**BASE, 'path': '../../host.py'}
            with patch.object(repo_eval, 'run', side_effect=AssertionError('subprocess reached')):
                with self.assertRaises(ValueError):
                    repo_eval.evaluate_fix(bad, {}, sandbox, 5, wheelhouse)
            self.assertFalse(sandbox.exists())

    def test_pip_setup_is_offline_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            work = root / 'repo'; work.mkdir()
            venv = root / 'venv'; venv.mkdir()
            wheelhouse = root / 'wheels'; wheelhouse.mkdir()
            with patch.object(repo_eval, 'run', return_value={'returncode': 1, 'cmd': 'pip',
                                                               'tail': 'no wheel'}) as mocked:
                self.assertFalse(repo_eval.install(work, venv, root, [], wheelhouse))
            env = mocked.call_args.args[2]
            self.assertEqual(env['PIP_NO_INDEX'], '1')
            self.assertEqual(env['PIP_FIND_LINKS'], str(wheelhouse))
            self.assertEqual(env['http_proxy'], 'http://127.0.0.1:9')

    def test_clone_does_not_inherit_host_tokens_or_git_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            wheelhouse = root / 'wheels'; wheelhouse.mkdir()
            sandbox = root / 'sandbox'
            with patch.dict(repo_eval.os.environ, {'HF_TOKEN': 'not-for-child',
                                                    'GIT_CONFIG_COUNT': '9'}):
                with patch.object(repo_eval, 'run', return_value={'returncode': 1,
                         'tail': 'clone refused', 'cmd': 'git'}) as mocked:
                    result = repo_eval.evaluate_fix(BASE, {}, sandbox, 5, wheelhouse)
            self.assertEqual(result['status'], 'CLONE_FAILED')
            env = mocked.call_args.args[2]
            self.assertNotIn('HF_TOKEN', env)
            self.assertNotIn('GIT_CONFIG_COUNT', env)
            self.assertEqual(env['GIT_ALLOW_PROTOCOL'], 'https')
            self.assertEqual(env['GIT_CONFIG_NOSYSTEM'], '1')


if __name__ == '__main__':
    unittest.main()
