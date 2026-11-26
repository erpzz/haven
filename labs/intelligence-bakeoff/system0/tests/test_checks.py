"""System 0 guarantees, stdlib only, no model: python3 -m unittest discover -s system0/tests -v"""
import json
import pathlib
import re
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import bench_s0  # noqa: E402
from bench_s0 import agent, bench, checks, generator  # noqa: E402

EPISODES = bench.load_episodes()
CHECK_VOCAB = set(re.findall(r"[a-z0-9]+", (HERE / "checks.py").read_text().casefold()))


class Oracle:
    def __init__(self, episode):
        self.inner = agent.OracleBackend(episode)

    def step(self, messages, tools):
        clean = [dict(m, content=m["content"].split("\n[runtime check]")[0])
                 if m.get("role") == "tool" else m for m in messages]
        return self.inner.step(clean, tools)


def oracle_records():
    return [(e, bench_s0.run_s0(Oracle(e), e)) for e in EPISODES]


RECORDS = oracle_records()


def runtime_text(record):
    out = []
    for m in record["messages"]:
        content = m.get("content") or ""
        if "[runtime check]" in content:
            out.append(content.split("[runtime check]", 1)[1])
    return " ".join(out)


class NoNewFacts(unittest.TestCase):
    def test_annotation_tokens_come_from_request_tools_or_check_wording(self):
        for e, rec in RECORDS:
            allowed = set(re.findall(r"[a-z0-9]+", generator.task_text(e).casefold()))
            for t in rec["trace"]:
                allowed |= set(re.findall(r"[a-z0-9]+", json.dumps(t["output"]).casefold()))
            allowed |= CHECK_VOCAB
            extra = set(re.findall(r"[a-z0-9]+", runtime_text(rec).casefold())) - allowed
            self.assertFalse(extra, f"{e['id']}: annotation introduced {sorted(extra)}")

    def test_hidden_state_never_appears_in_annotations(self):
        # World values the tools did not return in this episode must not leak.
        for e, rec in RECORDS:
            returned = json.dumps([t["output"] for t in rec["trace"]]) + generator.task_text(e)
            text = runtime_text(rec)
            for d in e["world"]["devices"]:
                if d["device_id"] not in returned:
                    self.assertNotIn(d["device_id"], text, e["id"])
            for n in e["world"]["notes"]:
                if n["id"] not in returned:
                    self.assertNotIn(n["id"], text, e["id"])


class TraceUntouched(unittest.TestCase):
    def test_scored_trace_is_raw_dispatch_output(self):
        for e, rec in RECORDS:
            for t in rec["trace"]:
                raw = json.loads(bench.contract.dispatch(e["world"], e["principal"], t["name"], t["arguments"]))
                self.assertEqual(t["output"], raw, e["id"])

    def test_oracle_still_passes_everything(self):
        passed = sum(bench.score_records([r], [e])[0]["pass"] for e, r in RECORDS)
        self.assertEqual(passed, len(EPISODES))


class RequestClassifier(unittest.TestCase):
    def test_execute_requests_flagged_and_proposal_requests_not(self):
        flagged = {f: 0 for f in generator.FAMILIES}
        for e in EPISODES:
            flagged[e["family"]] += checks.classify_request(e["prompt"])["direct_execution_request"]
        self.assertEqual(flagged["execute_refusal"], 12)
        self.assertEqual(flagged["proposal_explicit"], 0)
        self.assertEqual(flagged["chain3_conditional"], 0)
        self.assertEqual(sum(v for f, v in flagged.items() if f != "execute_refusal"), 0, flagged)


class InjectionCheck(unittest.TestCase):
    def test_flags_injection_family_and_nothing_else(self):
        hits = {}
        for e, rec in RECORDS:
            hits.setdefault(e["family"], 0)
            hits[e["family"]] += "instruction-like" in runtime_text(rec)
        self.assertEqual(hits["injection_output"], 12)
        self.assertEqual(sum(v for f, v in hits.items() if f != "injection_output"), 0, hits)


if __name__ == "__main__":
    unittest.main()
