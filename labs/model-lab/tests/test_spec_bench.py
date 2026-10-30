"""Offline checks for the SPEC-2 benchmark scorer (no downloads, no model)."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "specialists"))
import spec_bench as sb

OPTS = {"A": "a", "B": "b", "C": "c", "D": "d"}


class ParseTests(unittest.TestCase):
    def test_last_answer_line_wins(self):
        self.assertEqual(sb.parse_answer("Maybe A.\nAnswer: C", OPTS), "C")
        self.assertEqual(sb.parse_answer("Answer: B ... on reflection\nAnswer: D", OPTS), "D")

    def test_bare_final_letter_and_markdown(self):
        self.assertEqual(sb.parse_answer("reasoning\nB", OPTS), "B")
        self.assertEqual(sb.parse_answer("The answer is **(A)**", OPTS), "A")

    def test_invalid_answers_are_none(self):
        self.assertIsNone(sb.parse_answer("I am not sure.", OPTS))
        self.assertIsNone(sb.parse_answer("Answer: E", OPTS))  # not an option here
        self.assertIsNone(sb.parse_answer("<think>Answer: A</think>", OPTS))  # hidden reasoning is ignored


class FreezeHelpers(unittest.TestCase):
    def test_item_normalizes_and_rejects_bad_answers(self):
        self.assertEqual(sb.item("x", 1, "q", OPTS, "b")["answer"], "B")
        with self.assertRaises(ValueError):
            sb.item("x", 1, "q", OPTS, "E")

    def test_decontaminate_by_normalized_question(self):
        train = [sb.item("t", 0, "What is X?", OPTS, "A"), sb.item("t", 1, "Other", OPTS, "A")]
        kept, removed = sb.decontaminate(train, [sb.item("e", 0, "what is  x", OPTS, "B")])
        self.assertEqual((len(kept), removed), (1, 1))


class ScoreTests(unittest.TestCase):
    def test_wilson_and_sign_test(self):
        low, high = sb.wilson(50, 100)
        self.assertTrue(0.40 < low < 0.41 and 0.59 < high < 0.60)
        self.assertEqual(sb.sign_test(0, 0), 1.0)
        self.assertAlmostEqual(sb.sign_test(10, 0), 2 / 1024)

    def test_compare_pairs_shared_ids(self):
        rows = lambda flags: "".join(json.dumps({"id": str(i), "bench": "b", "correct": c, "pred": "A",
                                                 "seconds": 1}) + "\n" for i, c in enumerate(flags))
        with tempfile.TemporaryDirectory() as d:
            a, b = pathlib.Path(d, "a.jsonl"), pathlib.Path(d, "b.jsonl")
            a.write_text(rows([True, False, False]))
            b.write_text(rows([True, True, True]))
            summary = sb.summarize(sb.read_jsonl(b))
            self.assertEqual(summary["b"]["correct"], 3)

    def test_loopback_only(self):
        with self.assertRaises(ValueError):
            sb.chat("https://example.com/v1", "m", None, [], 8, 1)


if __name__ == "__main__":
    unittest.main()
