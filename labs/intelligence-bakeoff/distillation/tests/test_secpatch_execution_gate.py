"""Secpatch repo evaluator refuses execution absent deliberate isolated-runner acknowledgment."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
EVALUATOR = HERE.parent / 'secpatch' / 'repo_eval.py'


class RepoEvalExecutionGateTests(unittest.TestCase):
    def test_unacknowledged_host_execution_refused_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            out = root / 'results.jsonl'
            cmd = [sys.executable, str(EVALUATOR),
                   '--candidates', str(root / 'does-not-exist.jsonl'),
                   '--sandbox', str(root / 'sandbox'), '--out', str(out)]
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn('--acknowledge-isolated-runner', done.stderr)
            self.assertFalse(out.exists())
            self.assertFalse((root / 'sandbox').exists())


if __name__ == '__main__':
    unittest.main()
