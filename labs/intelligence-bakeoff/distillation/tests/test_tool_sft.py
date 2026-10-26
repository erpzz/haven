"""Deterministic, no-model checks for the verified tool-trajectory SFT lab."""
import json
import pathlib
import sys
import tempfile
import unittest

TOOL_SFT = pathlib.Path(__file__).resolve().parents[1] / "tool_sft"
sys.path.insert(0, str(TOOL_SFT))
import agent
import run
import world


class Scripted:
    def __init__(self, *replies):
        self.replies = list(replies)

    def step(self, messages, tools):
        return self.replies.pop(0)


def call(name, **args):
    return {"content": "", "tool_calls": [{"name": name, "arguments": args}]}


def final(text):
    return {"content": text, "tool_calls": []}


class ToolWorldTests(unittest.TestCase):
    def test_frozen_files_match_preregistration(self):
        registered = json.loads((TOOL_SFT / "PREREGISTRATION.json").read_text())["frozen_files_sha256"]
        for name in ("train", "dev", "heldout"):
            self.assertEqual(world.file_sha256(TOOL_SFT / "frozen" / f"{name}.jsonl"),
                             registered[f"frozen/{name}.jsonl"])

    def test_oracle_passes_every_frozen_episode(self):
        for name in ("train", "dev", "heldout"):
            for episode in run.load_split(name):
                record = agent.run_world_episode(agent.OracleBackend(episode), episode)
                self.assertTrue(world.verify(episode, record)["pass"], episode["id"])

    def test_splits_are_disjoint_in_vocabulary_and_composition(self):
        heldout = run.load_split("heldout")
        train_text = (TOOL_SFT / "frozen" / "train.jsonl").read_text()
        for principal in world.VOCAB["heldout"]["principals"]:
            self.assertNotIn(principal, train_text)
        for topic, _ in world.VOCAB["heldout"]["topics"]:
            self.assertNotIn(f'"topic": "{topic}"', train_text)
        self.assertFalse({e["family"] for e in run.load_split("train")} & set(world.COMPOSITION_FAMILIES))
        self.assertEqual({e["family"] for e in heldout if e["track"] == "composition"},
                         set(world.COMPOSITION_FAMILIES))

    def test_runtime_binds_principal_and_denies_cross_user(self):
        episode = world.make_episode("dev", "cross_user_deny", 0)
        other = next(n["owner"] for n in episode["world"]["notes"]
                     if n["owner"] not in (episode["principal"], "shared"))
        topic = episode["check"]["required"][0]["args"]["topic"][1]
        # The model claims to be the other user; the loop overrides it.
        backend = Scripted(call("haven_read_note", principal=other, topic=topic, owner=other),
                           final("Access denied: not authorized."))
        record = agent.run_world_episode(backend, episode)
        self.assertEqual(record["trace"][0]["arguments"]["principal"], episode["principal"])
        self.assertFalse(record["trace"][0]["output"]["ok"])
        self.assertTrue(world.verify(episode, record)["pass"])

    def test_substituted_proposal_and_execution_claim_fail(self):
        episode = world.make_episode("dev", "execute_refusal", 0)
        did = episode["check"]["required"][0]["args"]["device_id"][1]
        state = episode["check"]["must_contain"][0]
        backend = Scripted(call("haven_device_state", device_id=did),
                           call("haven_propose_action", action="do it", target=did),
                           final(f"It was {state}; I cannot do that."))
        verdict = world.verify(episode, agent.run_world_episode(backend, episode))
        self.assertFalse(verdict["pass"])
        self.assertIn("substituted_proposal", verdict["violations"])

    def test_cited_proposal_must_be_the_returned_one(self):
        episode = world.make_episode("dev", "proposal", 0)
        did = episode["check"]["required"][0]["args"]["target"][1]
        backend = Scripted(call("haven_propose_action", action="inspect", target=did),
                           final("Proposal proposal-0000000000 prepared; not executed."))
        self.assertFalse(world.verify(episode, agent.run_world_episode(backend, episode))["pass"])

    def test_parse_tool_text_and_errors(self):
        content, calls, error = agent.parse_tool_text(
            '<tool_call>\n{"name": "haven_device_state", "arguments": {"device_id": "x"}}\n</tool_call>')
        self.assertEqual(calls, [{"name": "haven_device_state", "arguments": {"device_id": "x"}}])
        self.assertIsNone(error)
        self.assertEqual(content, "")
        self.assertEqual(agent.parse_tool_text("<tool_call>{oops</tool_call>")[2], "UNPARSEABLE_TOOL_CALL")
        self.assertEqual(agent.parse_tool_text("<tool_call>{")[2], "UNTERMINATED_TOOL_CALL")

    def test_build_uses_only_verified_training_episodes_and_matches_oracle(self):
        train = run.load_split("train")[:3]
        good = agent.run_world_episode(agent.OracleBackend(train[0]), train[0])
        bad = agent.run_world_episode(Scripted(final("No idea.")), train[1])
        with tempfile.TemporaryDirectory() as tmp:
            teacher = pathlib.Path(tmp) / "teacher.jsonl"
            run.write_jsonl(teacher, [good, bad])
            run.main(["build", "--teacher", str(teacher), "--output", str(pathlib.Path(tmp) / "data")])
            manifest = json.loads((pathlib.Path(tmp) / "data" / "manifest.json").read_text())
            self.assertEqual(manifest["verified_teacher_episodes"], 1)
            rows = run.read_jsonl(pathlib.Path(tmp) / "data" / "teacher_sft.jsonl")
            self.assertTrue(all(r["episode"] == train[0]["id"] for r in rows))
            self.assertTrue(all(r["messages"][-1]["role"] == "assistant" for r in rows))
            heldout = run.load_split("heldout")[0]
            leaked = agent.run_world_episode(agent.OracleBackend(heldout), heldout)
            run.write_jsonl(teacher, [leaked])
            with self.assertRaises(SystemExit):
                run.main(["build", "--teacher", str(teacher), "--output", str(pathlib.Path(tmp) / "x")])

    def test_only_loopback_endpoints(self):
        with self.assertRaises(ValueError):
            agent.OpenAIBackend("http://192.168.1.5:8080/v1", "m")


if __name__ == "__main__":
    unittest.main()
