import _env  # noqa: F401  (must be first)

import json
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "eval"))

import harness  # noqa: E402

SCEN = {s["id"]: s for s in json.loads((LAB / "eval/scenarios_v1.json").read_text())["scenarios"]}
ANS = json.loads((LAB / "eval/answers_v1.json").read_text())
RULES = {a["id"]: a for a in ANS["answers"]}


def scripted(*steps):
    """A stub model: each step is a list of (tool, args) calls, or a final answer string."""
    it = iter(steps)

    def model(messages, tools):
        step = next(it)
        if isinstance(step, str):
            return {"content": step}
        return {"content": "", "tool_calls": [{"id": f"c{i}", "type": "function",
                                               "function": {"name": n, "arguments": json.dumps(a)}}
                                              for i, (n, a) in enumerate(step)]}
    return model


class EvalTests(unittest.TestCase):
    def test_set_is_consistent(self):
        self.assertEqual(set(SCEN), set(RULES))
        self.assertGreaterEqual(len(SCEN), 30)
        self.assertNotIn(ANS["canary"], (LAB / "eval/scenarios_v1.json").read_text())
        self.assertTrue(any(s["split"] == "heldout" for s in SCEN.values()))

    def test_good_and_bad_behaviour_grade_correctly(self):
        busy = next(s for s in SCEN.values() if s["category"] == "gpu-busy"
                    and "forge" in json.dumps(s["state"]) and "free it" in s["prompt"])
        polite = harness.run_one(busy, scripted([("haven_gpu", {})],
                                                "forge-teacher-server.service holds the GPU; I won't stop it."))
        self.assertTrue(harness.grade(polite, RULES[busy["id"]])["pass"])
        pushy = harness.run_one(busy, scripted([("haven_job_cancel", {"id": "x"})], "Done."))
        g = harness.grade(pushy, RULES[busy["id"]])
        self.assertFalse(g["pass"])
        self.assertTrue(any("forbidden" in p for p in g["problems"]))

        load = SCEN["load-01"]
        run = harness.run_one(load, scripted([("haven_model_use", {"model": "qwen35-4b", "context": 8192})],
                                             [("haven_lab_job", {"id": "job-load-1"})], "Loaded."))
        self.assertTrue(harness.grade(run, RULES["load-01"])["pass"], run["calls"])
        self.assertTrue(json.loads(run["messages"][3]["content"])["receipt"].startswith("R-"))

    def test_export_keeps_only_passing_train_rows(self):
        results = []
        for sid in ("read-01", "read-03"):  # read-03 is held out (every 3rd)
            run = harness.run_one(SCEN[sid], scripted([(RULES[sid]["any_of"][0], {})], "Here is what I found."))
            results.append({"id": sid, "grade": harness.grade(run, RULES[sid]), **run})
        self.assertEqual(SCEN["read-03"]["split"], "heldout")
        with tempfile.NamedTemporaryFile("r", suffix=".jsonl") as f:
            n = harness.export_train(results, list(SCEN.values()), ANS["canary"], f.name)
            with open(f.name) as fh:
                rows = [json.loads(line) for line in fh]
        self.assertEqual(n, 1)
        self.assertEqual(rows[0]["meta"]["scenario"], "read-01")


if __name__ == "__main__":
    unittest.main()
