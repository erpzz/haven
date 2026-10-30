"""Offline checks for the SPEC-2 STT scorer and the RFT loop's guards (no model, no download)."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "specialists"))
import rft
import spec_bench as sb
import spec_stt

OPTS = {"A": "x", "B": "y", "C": "z", "D": "w"}


class WerTests(unittest.TestCase):
    def test_normalizer_and_wer(self):
        self.assertEqual(spec_stt.normalize("Hello, World! It's fine-tuned."), "hello world it's fine tuned")
        self.assertEqual(spec_stt.corpus_wer([("the cat sat", "the cat sat")]), 0.0)
        self.assertAlmostEqual(spec_stt.corpus_wer([("the cat sat", "the bat sat down")]), 2 / 3)

    def test_loopback_only(self):
        args = type("A", (), {"backend": "openai", "base_url": "https://example.com/v1", "model": "m",
                              "timeout": 1})()
        with self.assertRaises(ValueError):
            spec_stt.make_transcriber(args)


class RftGuardTests(unittest.TestCase):
    def write(self, d, rows):
        path = pathlib.Path(d, "pool.jsonl")
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        return path

    def test_pool_refuses_eval_rows(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.write(d, [sb.item("medqa_test", 0, "q", OPTS, "A")])
            with self.assertRaises(SystemExit):
                rft.load_pool(path)

    def test_filter_keeps_shortest_correct_per_item(self):
        row = sb.item("medqa_train", 0, "q", OPTS, "B")
        samples = [{"id": row["id"], "row": row, "text": t, "correct": c, "k": k}
                   for k, (t, c) in enumerate([("long reasoning\nAnswer: B", True), ("Answer: B", True),
                                               ("Answer: A", False)])]
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d, "s.jsonl")
            src.write_text("".join(json.dumps(s) + "\n" for s in samples))
            counts = rft.filter_samples(src, pathlib.Path(d, "out.jsonl"))
            kept = sb.read_jsonl(pathlib.Path(d, "out.jsonl"))
        self.assertEqual(counts, {"items_sampled": 1, "items_kept": 1})
        self.assertEqual(kept[0]["messages"][-1]["content"], "Answer: B")

    def test_dev_split_is_deterministic_and_disjoint(self):
        rows = [sb.item("medqa_train", i, f"q{i}", OPTS, "A") for i in range(20)]
        with tempfile.TemporaryDirectory() as d:
            path = self.write(d, rows)
            pool1, dev1 = rft.split_pool(path, 5, 7)
            pool2, dev2 = rft.split_pool(path, 5, 7)
        self.assertEqual([r["id"] for r in dev1], [r["id"] for r in dev2])
        self.assertFalse({r["id"] for r in dev1} & {r["id"] for r in pool1})


if __name__ == "__main__":
    unittest.main()
