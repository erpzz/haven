from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(HERE))

import mac_qualification as qual


class DefenseMacQualificationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "requires POSIX process groups")
    def test_fixture_proves_hook_suppression_timeout_cleanup_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "qualification"
            result = qual.run_qualification(out_dir=out, require_apfs=False)

            self.assertEqual(result["status"], "pass", result)
            self.assertTrue(result["post_checkout_hook_control_fired"])
            self.assertTrue(result["git_hook_suppressed"])
            self.assertTrue(result["delayed_descendant_killed"])
            self.assertTrue(result["worktree_cleanup_verified"])
            self.assertTrue(result["timeout_observed"])
            self.assertFalse(result["model_patch_proposal_tested"])
            self.assertFalse(result["os_sandbox_claimed"])
            self.assertEqual(result["passing_touched_paths"], ["src/app.py"])
            self.assertRegex(result["receipt_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(
                result["implementation"]["implementation_sha256"],
                r"^[0-9a-f]{64}$",
            )

            receipt_path = out / "defense-mac-qualification.json"
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(stat.S_IMODE(receipt_path.stat().st_mode), 0o600)
            written = json.loads(receipt_path.read_text())
            self.assertEqual(written["receipt_sha256"], result["receipt_sha256"])
            self.assertFalse((out / "git-hook-marker").exists())
            self.assertFalse((out / "delayed-descendant-marker").exists())

    def test_existing_output_dir_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "existing"
            out.mkdir()
            marker = out / "keep"
            marker.write_text("keep")
            with self.assertRaisesRegex(
                qual.MacDefenseQualificationError, "OUTPUT_DIR_EXISTS"
            ):
                qual.run_qualification(out_dir=out, require_apfs=False)
            self.assertEqual(marker.read_text(), "keep")

    def test_candidate_commit_is_bound_in_source_identity(self):
        identity = qual._source_identity()
        self.assertEqual(identity["candidate_commit"], qual.CANDIDATE_COMMIT)
        self.assertEqual(
            set(identity["source_sha256"]), set(qual.SOURCE_FILES)
        )
        self.assertRegex(identity["implementation_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
