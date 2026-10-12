"""Deterministic, no-model/no-network distillation regression checks."""
import json
import pathlib
import sys
import tempfile
import unittest

DIST = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIST))
import pipeline
import evaluate
import train_sft
import train_opd


class DistillationTests(unittest.TestCase):
    def setUp(self):
        self.tasks = pipeline.load_fixtures()
        self.seed = next(str(n) for n in range(100)
                         if "T06-no-tool" in pipeline.split_ids(self.tasks, seed=str(n))[0])

    def row(self, answer="42"):
        return {"task": "T06-no-tool", "principal": "user-a", "answer": answer,
                "ok_transport": True, "tool_trace": [], "model": "synthetic-test",
                "runtime": "thin-openai-compatible", "repetition": 1}

    def test_success_only_when_scorer_passes(self):
        datasets, manifest = pipeline.build([self.row()], seed=self.seed)
        self.assertEqual(len(datasets["success.jsonl"]), 1)
        self.assertEqual(datasets["success.jsonl"][0]["completion"], "42")
        self.assertEqual(len(datasets["review_queue.jsonl"]), 0)
        self.assertEqual(manifest["counts"]["verified_success"], 1)

    def test_unverified_failure_never_becomes_training_target(self):
        datasets, manifest = pipeline.build([self.row("wrong")], seed=self.seed)
        self.assertEqual(datasets["success.jsonl"], [])
        self.assertEqual(datasets["foresight.jsonl"], [])
        self.assertEqual(len(datasets["review_queue.jsonl"]), 1)
        self.assertFalse(datasets["review_queue.jsonl"][0]["reviewed"])
        self.assertEqual(manifest["counts"]["failure_to_review"], 1)

    def test_hindsight_only_if_reviewed_and_trajectory_blind(self):
        row = self.row("wrong")
        note = {"task": row["task"], "source_digest": pipeline.digest(row),
                "reviewed": True, "evidence": "synthetic score_row failed required 42",
                "foresight": "Check the arithmetic before submitting."}
        datasets, _ = pipeline.build([row], [note], seed=self.seed)
        target = datasets["foresight.jsonl"][0]
        self.assertIn("Check the arithmetic", target["completion"])
        self.assertNotIn("wrong", target["prompt"])
        self.assertNotIn("synthetic score_row", target["prompt"])
        self.assertEqual(len(datasets["success.jsonl"]), 0)

    def test_annotations_need_review_evidence(self):
        row = self.row("wrong")
        note = {"task": row["task"], "source_digest": pipeline.digest(row),
                "reviewed": True, "foresight": "Check arithmetic", "evidence": ""}
        with self.assertRaises(ValueError):
            pipeline.build([row], [note], seed=self.seed)

    def test_cross_principal_is_refused(self):
        row = self.row()
        row["principal"] = "user-b"
        with self.assertRaisesRegex(ValueError, "Principal mismatch"):
            pipeline.build([row], seed=self.seed)

    def test_holdout_never_enters_training(self):
        train, holdout = pipeline.split_ids(self.tasks, seed=self.seed)
        task_id = next(iter(holdout))
        task = self.tasks[task_id]
        row = {"task": task_id, "principal": task["principal"],
               "answer": "synthetic", "ok_transport": True, "tool_trace": []}
        datasets, manifest = pipeline.build([row], seed=self.seed)
        self.assertFalse(datasets["success.jsonl"])
        self.assertFalse(datasets["review_queue.jsonl"])
        self.assertEqual(manifest["counts"]["held_out_rows"], 1)
        self.assertFalse(train & holdout)

    def test_refuse_arbitrary_task_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "tasks.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "synthetic"):
                pipeline.load_fixtures(path)

    def test_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "run.jsonl"
            pipeline.write_jsonl(path, [self.row()])
            self.assertEqual(pipeline.read_jsonl(path), [self.row()])

    def test_masked_labels_do_not_train_on_prompt(self):
        class DummyTokenizer:
            eos_token_id = 99
            def apply_chat_template(self, *args, **kwargs):
                return [10, 11]
            def encode(self, *args, **kwargs):
                return [20, 21]
        rows = train_sft.tokenize_examples([{"prompt": "A", "completion": "B"}],
                                           DummyTokenizer(), 100)
        self.assertEqual(rows[0]["labels"], [-100, -100, 20, 21, 99])
        with self.assertRaises(ValueError):
            train_sft.tokenize_examples([{"prompt": "A", "completion": "B"}],
                                       DummyTokenizer(), 3)

    def test_training_scripts_are_dry_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            file = pathlib.Path(folder) / "synthetic.jsonl"
            file.write_text(json.dumps({"prompt": "hello", "completion": "world"})+"\n",
                            encoding="utf-8")
            train_sft.main(["--data", str(file)])
            train_opd.main(["--prompts", str(file)])

    def test_separate_skill_and_fact_reporting(self):
        probes = evaluate.load_probes()
        self.assertEqual({p["group"] for p in probes},
                         {"compositional_skill", "learned_fact_transfer",
                          "unseen_fact_control", "retrieval_grounded"})
        rows = [{"id": p["id"], "answer": p["expected"],
                 "ok_transport": True} for p in probes]
        report = evaluate.summarize(probes, rows)
        self.assertTrue(all(group["pass_rate"] == 1 for group in report.values()))
        with self.assertRaisesRegex(ValueError, "Missing probes"):
            evaluate.summarize(probes, rows[:-1])
        self.assertTrue(evaluate.score({"expected": "SAPPHIRE"}, "sapphire."))


if __name__ == "__main__":
    unittest.main()
