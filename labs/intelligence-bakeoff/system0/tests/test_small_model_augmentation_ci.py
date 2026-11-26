"""CI bridge: run the combined small-model augmentation suite from the existing #115 workflow.

This file exists only on the synthetic #143 validation branch and is not intended
for merge into #115 or main.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class SmallModelAugmentationCombinedCI(unittest.TestCase):
    def test_combined_augmentation_suite(self):
        root = Path(__file__).resolve().parents[4]
        aug = root / "labs" / "small-model-augmentation"

        compile_run = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", str(aug)],
            text=True, capture_output=True,
        )
        self.assertEqual(
            compile_run.returncode, 0,
            f"augmentation compile failed\nstdout:\n{compile_run.stdout}\nstderr:\n{compile_run.stderr}",
        )

        suite_run = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"],
            cwd=aug, text=True, capture_output=True,
        )
        self.assertEqual(
            suite_run.returncode, 0,
            f"combined augmentation tests failed\nstdout:\n{suite_run.stdout}\nstderr:\n{suite_run.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
