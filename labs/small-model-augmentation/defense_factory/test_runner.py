import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from defense_factory import validate_unified_diff
from runner import Recipe, run_fix


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(("git", "init", "-q"), cwd=self.repo, check=True)
        subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=self.repo, check=True)
        subprocess.run(("git", "config", "user.name", "Haven Test"), cwd=self.repo, check=True)
        (self.repo / "app.txt").write_text("one\n")
        subprocess.run(("git", "add", "app.txt"), cwd=self.repo, check=True)
        subprocess.run(("git", "commit", "-qm", "base"), cwd=self.repo, check=True)
        self.base = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=self.repo, text=True).strip()
        self.patch = "\n".join([
            "diff --git a/app.txt b/app.txt",
            "--- a/app.txt",
            "+++ b/app.txt",
            "@@ -1 +1 @@",
            "-one",
            "+two",
            "",
        ])
        touched = validate_unified_diff(self.patch, ["app.txt"])
        self.fix = {
            "finding_id": "hdf_" + "a" * 32,
            "packet_sha256": "b" * 64,
            "patch": self.patch,
            "patch_sha256": hashlib.sha256(self.patch.encode()).hexdigest(),
            "touched_paths": list(touched),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_passing_recipe_returns_hashed_receipt_and_cleans_worktree(self):
        recipe = Recipe("content", (sys.executable, "-c", "from pathlib import Path; assert Path('app.txt').read_text() == 'two\\n'"), 5)
        result = run_fix(repo=self.repo, base_commit=self.base, validated_fix=self.fix, recipes=[recipe])
        self.assertTrue(result["passed"])
        self.assertEqual(result["touched_paths"], ["app.txt"])
        self.assertEqual(len(result["receipt_sha256"]), 64)
        self.assertEqual(result["finding_id"], self.fix["finding_id"])
        self.assertEqual(result["fix_packet_sha256"], self.fix["packet_sha256"])
        self.assertEqual(len(result["recipe_policy_sha256"]), 64)
        recipe_receipt = result["recipes"][0]
        self.assertNotIn("stdout", recipe_receipt)
        self.assertNotIn("stderr", recipe_receipt)
        self.assertIn("stdout_sha256", recipe_receipt)
        porcelain = subprocess.check_output(("git", "worktree", "list", "--porcelain"), cwd=self.repo, text=True)
        self.assertEqual(porcelain.count("worktree "), 1)

    def test_failing_recipe_is_not_reported_pass(self):
        recipe = Recipe("fail", (sys.executable, "-c", "raise SystemExit(7)"), 5)
        result = run_fix(repo=self.repo, base_commit=self.base, validated_fix=self.fix, recipes=[recipe])
        self.assertFalse(result["passed"])
        self.assertEqual(result["recipes"][0]["exit_code"], 7)

    def test_patch_hash_tamper_rejected(self):
        bad = dict(self.fix, patch_sha256="0" * 64)
        with self.assertRaises(ValueError):
            run_fix(repo=self.repo, base_commit=self.base, validated_fix=bad, recipes=[Recipe("x", (sys.executable, "-c", "pass"), 5)])

    def test_missing_packet_binding_rejected(self):
        bad = dict(self.fix)
        bad.pop("packet_sha256")
        with self.assertRaises(ValueError):
            run_fix(repo=self.repo, base_commit=self.base, validated_fix=bad, recipes=[Recipe("x", (sys.executable, "-c", "pass"), 5)])

    def test_changed_file_receipt_tamper_rejected(self):
        bad = dict(self.fix, touched_paths=["other.txt"])
        with self.assertRaises(ValueError):
            run_fix(repo=self.repo, base_commit=self.base, validated_fix=bad, recipes=[Recipe("x", (sys.executable, "-c", "pass"), 5)])

    @unittest.skipUnless(os.name == "posix", "POSIX process-group test")
    def test_timeout_kills_descendant_before_late_side_effect(self):
        marker = Path(self.tmp.name) / "late.txt"
        child = (
            "import pathlib,time; time.sleep(0.7); "
            f"pathlib.Path({str(marker)!r}).write_text('late')"
        )
        parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1]]); time.sleep(10)"
        recipe = Recipe("timeout", (sys.executable, "-c", parent, child), 0.15)
        result = run_fix(repo=self.repo, base_commit=self.base, validated_fix=self.fix, recipes=[recipe])
        self.assertFalse(result["passed"])
        self.assertTrue(result["recipes"][0]["timed_out"])
        time.sleep(0.9)
        self.assertFalse(marker.exists())

    def test_symlink_patch_target_rejected(self):
        (self.repo / "target.txt").write_text("one\n")
        (self.repo / "link.txt").symlink_to("target.txt")
        subprocess.run(("git", "add", "target.txt", "link.txt"), cwd=self.repo, check=True)
        subprocess.run(("git", "commit", "-qm", "symlink"), cwd=self.repo, check=True)
        base = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=self.repo, text=True).strip()
        patch = "diff --git a/link.txt b/link.txt\n--- a/link.txt\n+++ b/link.txt\n@@ -1 +1 @@\n-target.txt\n+other.txt\n"
        fix = {"finding_id": self.fix["finding_id"], "packet_sha256": self.fix["packet_sha256"], "patch": patch, "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(), "touched_paths": ["link.txt"]}
        with self.assertRaises(ValueError):
            run_fix(repo=self.repo, base_commit=base, validated_fix=fix, recipes=[Recipe("x", (sys.executable, "-c", "pass"), 5)])

    def test_rejects_nonexact_commit_and_duplicate_recipe_ids(self):
        with self.assertRaises(ValueError):
            run_fix(repo=self.repo, base_commit="HEAD", validated_fix=self.fix, recipes=[Recipe("x", (sys.executable, "-c", "pass"), 5)])
        with self.assertRaises(ValueError):
            run_fix(repo=self.repo, base_commit=self.base, validated_fix=self.fix, recipes=[
                Recipe("x", (sys.executable, "-c", "pass"), 5),
                Recipe("x", (sys.executable, "-c", "pass"), 5),
            ])


if __name__ == "__main__":
    unittest.main()
