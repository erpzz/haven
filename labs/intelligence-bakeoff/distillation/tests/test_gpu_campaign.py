"""Offline unit tests for data admission and execution receipts, NOT GPU training.

These fixture rows verify preflight rejects accidental leakage and unverified
samples; no fake CUDA device, model weights or training receipt is created.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "secpatch"))
import gpu_campaign


def make_dataset(root: pathlib.Path, train_fixes=3, held_fixes=2):
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({
        "osv_archive_sha256": "a" * 64,
        "note": "Targets are recorded fixes from public open-source repositories."}) + "\n")
    for split, count, filename in [
            ("train", train_fixes, "train.jsonl"),
            ("heldout", held_fixes, "eval-heldout.jsonl")]:
        with (root / filename).open("w") as stream:
            for i in range(count):
                row = {
                    "id": split + str(i), "key": split + "-GHSA-" + str(i), "split": split,
                    "task": "detect",
                    "messages": [{"role": "user", "content": "example"}] +
                                ([{"role": "assistant", "content": "answer"}] if split == "train" else []),
                    "source": {
                        "repo": f"{split}/repo-{i}", "commit": "a" * 40, "parent": "b" * 40,
                        "advisory_ids": ["GHSA-example"], "code_license": "MIT"},
                    "verification": dict.fromkeys((
                        "fix_commit_fetched", "single_parent", "permissive_license",
                        "single_function_fix", "parsed"), True)}
                if split == "heldout":
                    row["grader"] = {"task": "detect", "label": "not_vulnerable"}
                stream.write(json.dumps(row) + "\n")


class CampaignPreflightTests(unittest.TestCase):
    def test_check_license_provenance_and_repository_split(self):
        with tempfile.TemporaryDirectory() as t:
            data = pathlib.Path(t)
            make_dataset(data)
            q = gpu_campaign.qualify_data(data, min_train=3, min_heldout=2)
            self.assertEqual(q["train_fix_count"], 3)
            self.assertEqual(q["heldout_fix_count"], 2)
            self.assertEqual(q["tasks"], gpu_campaign.TRAIN_TASKS)
            self.assertEqual(q["train_sha256"], hashlib.sha256(
                (data / "train.jsonl").read_bytes()).hexdigest())

    def test_refuse_small_data_even_if_json_well_formed(self):
        with tempfile.TemporaryDirectory() as t:
            data = pathlib.Path(t)
            make_dataset(data)
            with self.assertRaises(gpu_campaign.QualificationError):
                gpu_campaign.qualify_data(data)

    def test_reject_train_heldout_repository_overlap(self):
        with tempfile.TemporaryDirectory() as t:
            data = pathlib.Path(t)
            make_dataset(data)
            path = data / "eval-heldout.jsonl"
            lines = [json.loads(x) for x in path.read_text().splitlines()]
            lines[0]["source"]["repo"] = "train/repo-0"
            path.write_text("".join(json.dumps(r) + "\n" for r in lines))
            with self.assertRaisesRegex(gpu_campaign.QualificationError, "overlap"):
                gpu_campaign.qualify_data(data, min_train=3, min_heldout=2)

    def test_reject_unverified_or_unlicensed_training_row(self):
        with tempfile.TemporaryDirectory() as t:
            data = pathlib.Path(t)
            make_dataset(data)
            path = data / "train.jsonl"
            lines = [json.loads(x) for x in path.read_text().splitlines()]
            lines[1]["source"]["code_license"] = "GPL-3.0"
            path.write_text("".join(json.dumps(r) + "\n" for r in lines))
            with self.assertRaisesRegex(gpu_campaign.QualificationError, "licensed"):
                gpu_campaign.qualify_data(data, min_train=3, min_heldout=2)

    def test_refuse_eval_with_assistant_answer(self):
        with tempfile.TemporaryDirectory() as t:
            data = pathlib.Path(t)
            make_dataset(data)
            path = data / "eval-heldout.jsonl"
            lines = [json.loads(x) for x in path.read_text().splitlines()]
            lines[0]["messages"].append({"role": "assistant", "content": "LEAK"})
            path.write_text("".join(json.dumps(r) + "\n" for r in lines))
            with self.assertRaisesRegex(gpu_campaign.QualificationError, "leaks"):
                gpu_campaign.qualify_data(data, min_train=3, min_heldout=2)

    def test_refuse_non_pinned_model_revision(self):
        with tempfile.TemporaryDirectory() as t:
            data = pathlib.Path(t)
            make_dataset(data)
            with self.assertRaises(SystemExit):
                gpu_campaign.campaign(["--data", str(data), "--output", str(data / "unused"),
                                       "--revision", "main"])
            self.assertFalse((data / "unused").exists())


if __name__ == "__main__":
    unittest.main()
