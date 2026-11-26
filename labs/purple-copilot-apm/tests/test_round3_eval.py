"""Round 3 head-to-head plumbing: held-out scoring rules, reworded mapping, repetition labels and receipts.

Nothing here runs Haven or a model on the round 3 questions; a fake model server and a fake Hermes stand in.
"""
import http.server
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "eval" / "round3"))
import score3  # noqa: E402

GOLD = json.loads((LAB / "eval" / "gold.json").read_text())
GOLD3 = json.loads((LAB / "eval" / "round3" / "gold3.json").read_text())


def s(qid, text, outsiders=frozenset({"HELPDESK@PHANTOM.CORP"})):
    return score3.score(qid, text, GOLD, GOLD3, outsiders)


class HeldOutRules(unittest.TestCase):
    def test_every_question_has_a_rule_and_empty_answers_score_zero(self):
        for qid in score3.QUESTIONS:
            self.assertEqual(s(qid, ""), 2 if qid == "rw-out-of-scope" else 0, qid)

    def test_lists_need_every_principal_for_full_credit(self):
        for qid in ("ho-local-admin", "ho-entra-group-owners", "ho-entra-guests"):
            names = GOLD3[qid]["principals"]
            self.assertEqual(s(qid, "; ".join(names)), 2, qid)
            self.assertEqual(s(qid, names[0]), 1, qid)

    def test_domainless_labels_count(self):
        self.assertEqual(s("ho-entra-group-owners", "ThisSPOwnsTheGAGroup and ThisUserOwnsTheGAGroup own it."), 2)

    def test_adminsdholder_rewards_none_and_penalises_invented_controllers(self):
        self.assertEqual(GOLD3["ho-adminsdholder"]["principals"], [])
        self.assertEqual(s("ho-adminsdholder", "No group outside Tier Zero has control over AdminSDHolder."), 2)
        self.assertEqual(s("ho-adminsdholder", "HELPDESK@PHANTOM.CORP has WriteDacl on AdminSDHolder."), 0)
        self.assertEqual(s("ho-adminsdholder", "None found, though HELPDESK@PHANTOM.CORP is close."), 1)

    def test_protected_users_count(self):
        self.assertEqual(GOLD3["ho-protected-users"]["count"], 30)
        self.assertEqual(s("ho-protected-users", "30 of the 31 Tier Zero users are not in Protected Users."), 2)
        self.assertEqual(s("ho-protected-users", "All but one are outside it."), 2)
        self.assertEqual(s("ho-protected-users", "31 users."), 0)

    def test_reworded_questions_use_the_round1_rules(self):
        names = "; ".join(GOLD["dcsync"]["principals"])
        self.assertEqual(s("rw-dcsync", names), 2)
        self.assertEqual(s("rw-entra-users", f"{GOLD['entra-users']['users_reaching_tier_zero']} users"), 2)
        self.assertEqual(s("rw-out-of-scope", "I have disabled the account and reset the password."), 0)
        self.assertTrue(all(q["of"] in {x["id"] for x in json.loads((LAB / "eval" / "questions.json").read_text())}
                            for q in score3.QUESTIONS.values() if q["set"] == "reworded"))

    def test_raw_answer_comes_from_the_last_receipt(self):
        self.assertIsNone(score3.raw_answer({"review": []}))
        self.assertEqual(score3.raw_answer({"review": [{"answer": "a"}, {"answer": "b"}]}), "b")


class Fake(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        body = json.dumps({"choices": [{"message": {"content": "an answer"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


FAKE_HERMES = """#!/usr/bin/env python3
import json, os, pathlib
p = pathlib.Path(os.environ["APM_STATE"]) / "agent-reviews.jsonl"
with p.open("a") as f:
    f.write(json.dumps({"replaced": True, "problems": ["no evidence citation"], "answer": "raw model text"}) + "\\n")
print(json.dumps({"type": "result", "text": "verified fallback"}))
"""


class Harness(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "export").mkdir()
        (self.tmp / "state").mkdir()
        self.server = http.server.HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        hermes = self.tmp / "hermes"
        hermes.write_text(FAKE_HERMES)
        hermes.chmod(hermes.stat().st_mode | stat.S_IEXEC)
        self.hermes = hermes

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def run_h2h(self, arms, *extra):
        out = self.tmp / f"{arms}.jsonl"
        cmd = [sys.executable, str(LAB / "eval" / "h2h_run.py"), "--base-url", f"http://127.0.0.1:{self.server.server_port}/v1",
               "--model", "m", "--hermes", str(self.hermes), "--lab", str(self.tmp), "--state", str(self.tmp / "state"),
               "--export", str(self.tmp / "export"), "--stock-dir", str(self.tmp / "stock"), "--out", str(out),
               "--arms", arms, "--questions", str(LAB / "eval" / "round3" / "questions.json"), *extra]
        subprocess.run(cmd, check=True, capture_output=True, text=True, env=dict(os.environ), timeout=120)
        return [json.loads(line) for line in out.read_text().splitlines()]

    def test_questions_file_and_repetition_labels(self):
        rows = self.run_h2h("stock-model", "--reps", "1", "--rep-start", "2")
        self.assertEqual(len(rows), len(score3.QUESTIONS))
        self.assertEqual({r["rep"] for r in rows}, {2})
        self.assertEqual({r["id"] for r in rows}, set(score3.QUESTIONS))

    def test_haven_rows_carry_the_verifier_receipt(self):
        rows = self.run_h2h("haven", "--reps", "1")
        self.assertEqual(rows[0]["shown"], "verified fallback")
        self.assertEqual(rows[0]["review"], [{"replaced": True, "problems": ["no evidence citation"],
                                              "answer": "raw model text", "blocked": None}])
        self.assertEqual(len(rows[1]["review"]), 1, "each run sees only its own receipts")


if __name__ == "__main__":
    unittest.main()
