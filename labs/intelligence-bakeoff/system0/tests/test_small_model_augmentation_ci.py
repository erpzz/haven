"""Synthetic CI bridge for #126/#141; not intended for merge."""
from __future__ import annotations
import subprocess, sys, unittest
from pathlib import Path

class SmallModelAugmentationCombinedCI(unittest.TestCase):
    def test_combined_augmentation_suite(self):
        root = Path(__file__).resolve().parents[4]
        aug = root / "labs" / "small-model-augmentation"
        compile_run = subprocess.run([sys.executable, "-m", "compileall", "-q", str(aug)], text=True, capture_output=True)
        self.assertEqual(compile_run.returncode, 0, compile_run.stdout + "\n" + compile_run.stderr)
        suite_run = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"],
            cwd=aug, text=True, capture_output=True,
        )
        print(suite_run.stdout)
        print(suite_run.stderr)
        self.assertEqual(suite_run.returncode, 0, suite_run.stdout + "\n" + suite_run.stderr)

if __name__ == "__main__":
    unittest.main()
