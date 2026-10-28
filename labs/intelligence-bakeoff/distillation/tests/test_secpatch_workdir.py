"""Path validation tests for secpatch's disposable repository evaluator."""
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from secpatch import repo_eval


class RepoEvalWorkdirTests(unittest.TestCase):
    def test_osv_advisory_ids_stay_in_sandbox(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            for key in ('GHSA-aaaa-bbbb-cccc', 'PYSEC-2026-123', 'CVE-2026-10001'):
                self.assertEqual(repo_eval.workdir_for(base, key), base / key)

    def test_rejects_traversal_and_nested_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            for key in ('..', '../outside', 'GHSA/child', '/tmp/outside',
                        '..\\outside', '', '.hidden', 'bad name', 'x' * 129):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    repo_eval.workdir_for(base, key)

    def test_rejects_symlink_in_sandbox(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            other = base / 'other'
            other.mkdir()
            (base / 'GHSA-link').symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError):
                repo_eval.workdir_for(base, 'GHSA-link')


if __name__ == '__main__':
    unittest.main()
