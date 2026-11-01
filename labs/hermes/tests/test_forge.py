import _env  # noqa: F401  (must be first)

import json
import tempfile
import unittest
from pathlib import Path

from fakes import FakeSlink
from haven_hermes import server
from haven_hermes.tools import forge

import sandbox
import skills

CODE = """import json, sys
a = json.loads(sys.argv[1])
print(json.dumps({"sum": a["a"] + a["b"]}))
"""
PARAMS = {"properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}


def _cases(root, rows):
    for i, (args, result) in enumerate(rows):
        c = root / f"h{i}"
        (c / "repo").mkdir(parents=True)
        (c / "expect.json").write_text(json.dumps({"args": args, "result": result}))


@unittest.skipUnless(sandbox.describe()["available"], "needs the OS sandbox (seatbelt or landlock)")
class ForgeTests(unittest.TestCase):
    def test_propose_admit_call_and_tamper(self):
        reg = server.build("operate", slink=FakeSlink(), settings={}, state=Path(tempfile.mkdtemp()))
        bad = reg.invoke("haven_tool_propose", {"name": "add_two", "description": "Add two integers a and b.",
                                                "parameters": PARAMS, "code": CODE.replace("+", "-"),
                                                "dev_cases": [{"args": {"a": 2, "b": 3}, "result": {"sum": 5}}]})
        self.assertTrue(bad["ok"], bad)
        self.assertEqual(bad["dev_pass"], 0)
        self.assertEqual(reg.invoke("haven_tool_request_admission", {"name": "add_two"})["error"]["code"],
                         "dev_cases_failing")

        good = reg.invoke("haven_tool_propose", {"name": "add_two", "description": "Add two integers a and b.",
                                                 "parameters": PARAMS, "code": CODE,
                                                 "dev_cases": [{"args": {"a": 2, "b": 3}, "result": {"sum": 5}}]})
        self.assertEqual((good["dev_pass"], good["dev_total"]), (1, 1))
        req = reg.invoke("haven_tool_request_admission", {"name": "add_two"})
        self.assertTrue(req["requested"], req)
        self.assertIn("skills.py admit", req["owner_steps"][1])
        self.assertNotIn("skill_add_two", reg.tools)  # proposed is not callable

        held = forge.heldout_dir("add_two")
        _cases(held, [({"a": 10, "b": -4}, {"sum": 6}), ({"a": 0, "b": 0}, {"sum": 0})])
        rec = skills.admit(forge.candidates_dir() / "add_two", held, "hermes", dev=forge.candidates_dir() / "add_two" / "dev")
        self.assertEqual(rec["status"], "admitted", rec["validation"])

        listed = reg.invoke("haven_tools")
        self.assertIn("skill_add_two", listed["callable_now"])
        spec = reg.tools["skill_add_two"]
        self.assertEqual(spec.effect, "change")
        out = reg.invoke("skill_add_two", {"a": 40, "b": 2})
        self.assertEqual(out["result"], {"sum": 42}, out)
        self.assertEqual(out["status"], "succeeded")

        admitted = skills.verified("add_two")[0]
        (admitted / "skill.py").write_text(CODE.replace("+", "*"))
        self.assertIsNone(skills.verified("add_two"))
        self.assertTrue(reg.refresh())
        self.assertNotIn("skill_add_two", reg.tools)


class CheckCaseTests(unittest.TestCase):
    def test_generic_result_containment(self):
        self.assertTrue(skills.check_case({"sum": 5, "extra": 1}, {"result": {"sum": 5}})[0])
        self.assertFalse(skills.check_case({"sum": 5.0}, {"result": {"sum": 5}})[0])
        self.assertFalse(skills.check_case({"xs": [1, 2]}, {"result": {"xs": [1]}})[0])
        # The original run_tests contract still applies when no "result" is expected.
        self.assertTrue(skills.check_case({"framework": "unittest", "failing": [], "passed": 3},
                                          {"framework": "unittest", "failing": [], "passed": 3})[0])


if __name__ == "__main__":
    unittest.main()
