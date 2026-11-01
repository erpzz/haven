"""The evaluation set's own integrity: labels agree with the independent tools, every oracle answer grades as a pass."""
import json
import re
import unittest

from haven_cyber import EVAL
from haven_cyber.eval.grade import extract_json, grade
from haven_cyber.eval.toolenv import normalize_command
from haven_cyber.tools import azure_rbac
from haven_cyber.verifier import recheck

SC = {s["id"]: s for s in json.loads((EVAL / "scenarios" / "v1.json").read_text())["scenarios"]}
ANS = json.loads((EVAL / "answers" / "v1.json").read_text())["answers"]


class EvalSetTests(unittest.TestCase):
    def test_shape(self):
        self.assertGreaterEqual(len(SC), 30)
        self.assertEqual(set(SC), set(ANS))
        self.assertGreaterEqual(sum(s["split"] == "heldout" for s in SC.values()), 15)
        for s in SC.values():
            self.assertNotIn("checks", json.dumps(s))  # answers never ship inside the visible scenario

    def test_oracle_answers_pass(self):
        for sid, t in ANS.items():
            a = {}
            for c in t["checks"]:
                if c["op"] == "equals":
                    a[c["field"]] = c["value"]
                elif c["op"] in ("contains_all", "contains_any"):
                    a.setdefault(c["field"], []).extend(c["value"][:1] if c["op"] == "contains_any" else c["value"])
            self.assertTrue(grade(json.dumps(a), t)["pass"], sid)

    def test_ca_labels_match_independent_verifier(self):
        expect = {"ca-01": ("HCA-001", False), "ca-02": ("HCA-001", False), "ca-03": ("HCA-001", False), "ca-04": ("HCA-001", True),
                  "ca-05": ("HCA-002", False), "ca-06": ("HCA-002", False), "ca-07": ("HCA-002", True), "ca-08": ("HCA-003", False),
                  "ca-09": ("HCA-003", False), "ca-10": ("HCA-005", False), "ca-11": ("HCA-005", True), "ca-12": ("HCA-004", False),
                  "ca-13": ("HCA-007", True), "ca-14": ("HCA-007", False)}
        for sid, (rule, ok) in expect.items():
            exists, covered = recheck(rule, SC[sid]["artifacts"]["tenant_snapshot"])
            self.assertEqual(covered, ok, sid)

    def test_rbac_labels_match_evaluator(self):
        for sid in ("rbac-01", "rbac-02", "rbac-03", "rbac-07"):
            s = SC[sid]
            op = re.search(r"Microsoft\.[A-Za-z./]+(?:delete|write)", s["question"]).group(0)
            prin = re.search(r"principal ([0-9a-f-]{36})", s["question"]).group(1)
            scope = re.search(r"(/subscriptions/[^\s?]+)", s["question"]).group(1).rstrip("?").rstrip(")")
            got = azure_rbac.check(s["artifacts"]["azure_rbac"], prin, op, scope)["allowed"]
            self.assertEqual("allowed" if got else "denied", ANS[sid]["checks"][0]["value"], sid)

    def test_grader_parsing(self):
        self.assertEqual(extract_json('<think>{"x":1}</think> text {"verdict": "no", "ids": []} trailing'), {"verdict": "no", "ids": []})
        t = {"checks": [{"field": "verdict", "op": "equals", "value": "no"}], "false_positive_if": None}
        self.assertTrue(grade('{"verdict": ["No"]}', t)["pass"])
        self.assertFalse(grade("no json here", t)["parsed"])
        self.assertEqual(normalize_command("ss -tlnp"), normalize_command("ss -p -n -l -t"))
        from haven_cyber.eval.grade import extract_json_lenient
        obj, fixed = extract_json_lenient('{"tool_id": "entra.ca.assess", "arguments": {"snapshot_path": "x"}, "why": "because"')
        self.assertTrue(fixed)
        self.assertEqual(obj["tool_id"], "entra.ca.assess")
        self.assertIsNone(extract_json('{"tool_id": "x"'))  # grading stays strict


if __name__ == "__main__":
    unittest.main()
