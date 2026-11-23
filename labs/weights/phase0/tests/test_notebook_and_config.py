"""The W1 Phase 1 notebook is built (not run) and current; its runner works end to end on CPU
against a fake model server; the regression config is complete. No GPU, no model, no network."""
from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import gen_hare  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUILD = load("kaggle/build_w1_phase1.py", "build_w1_phase1")
W1 = load("kaggle/w1_phase1.py", "w1_phase1")
NB = json.loads((HERE / "kaggle" / "w1_phase1_kaggle.ipynb").read_text())


class Notebook(unittest.TestCase):
    def test_built_not_run(self):
        for cell in NB["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell["outputs"], [])
                self.assertIsNone(cell["execution_count"])
                ast.parse(cell["source"])

    def test_embedded_bundle_is_current(self):
        src = next(c["source"] for c in NB["cells"] if 'BLOB = "' in c["source"])
        blob = src.split('BLOB = "')[1].split('"')[0]
        embedded = hashlib.sha256(base64.b64decode(blob)).hexdigest()
        self.assertEqual(embedded, hashlib.sha256(BUILD.bundle()).hexdigest(),
                         "rebuild with: python3 kaggle/build_w1_phase1.py")
        self.assertIn(embedded, src)

    def test_refuses_to_run_without_the_posted_episode_hash(self):
        cfg = NB["cells"][1]["source"]
        self.assertIn('EPISODES_SHA256 = ""', cfg)
        self.assertIn("assert len(EPISODES_SHA256) == 64", cfg)
        self.assertIn("Do not run until the gates on #123 are met", NB["cells"][0]["source"])
        self.assertIn("AMENDMENT_1.md", NB["cells"][0]["source"])

    def test_engine_cell_is_the_run1_helper(self):
        cell = (HERE / "kaggle" / "llama_build_cell.py").read_text()
        self.assertIn('def build_llama(tag, prefix):', cell)
        self.assertIn('ENGINE = build_llama("b11146"', next(c["source"] for c in NB["cells"] if "def build_llama" in c["source"]))


class FakeProc:
    def terminate(self):
        pass


class Phase1DryRun(unittest.TestCase):
    """The runner on CPU: a fake server whose answers depend on the attempt seed."""

    def test_keep_rule_hard_episodes_gate_and_resume(self):
        eps, _, _ = gen_hare.make_episodes("dry-run-seed", 2)
        prompts = {}
        for e in eps:
            prompts.setdefault(common.agent.user_message(e["principal"], common.generator.task_text(e)), []).append(e)
        eps = [v[0] for v in prompts.values() if len(v) == 1]
        by_user = {common.agent.user_message(e["principal"], common.generator.task_text(e)): e for e in eps}

        class Fake:
            def __init__(self, url, model, key, temperature, max_tokens, seed):
                self.seed, self.inner = seed, None

            def step(self, messages, tools):
                e = by_user[messages[1]["content"].split("\n\n[runtime check]")[0]]
                if e["family"] == "no_tool" or self.seed % 2:      # odd seeds and no_tool always wrong
                    return {"content": "No idea.\n" + json.dumps({"claims": [{"value": "x", "evidence_id": None,
                                                                              "status": "direct"}]}), "tool_calls": []}
                self.inner = self.inner or common.Oracle(e)
                return self.inner.step(messages, tools)

        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            ep_path, model = tmp / "eps.jsonl", tmp / "fake.gguf"
            common.write_jsonl(ep_path, eps)
            model.write_bytes(b"not a model")
            argv = ["--engine", "none", "--model", str(model), "--model-sha256", common.sha256_file(model),
                    "--episodes", str(ep_path), "--episodes-sha256", common.sha256_file(ep_path),
                    "--out", str(tmp / "out"), "--gpus", "0,1", "--attempts", "4"]
            with mock.patch.object(W1, "start_server", lambda *a: FakeProc()), \
                    mock.patch.object(W1.agent, "OpenAIBackend", Fake):
                W1.main(argv)
                first = json.loads((tmp / "out" / "summary.json").read_text())
                W1.main(argv)                                     # resume: nothing left to do
                second = json.loads((tmp / "out" / "summary.json").read_text())
            s = first["summary"]
            n = len(eps)
            no_tool = [e["id"] for e in eps if e["family"] == "no_tool"]
            self.assertEqual(first["status"], "EXECUTED")
            self.assertEqual(s["attempts"], 4 * n)
            self.assertEqual(s["passing_attempts"], 2 * (n - len(no_tool)))   # seeds 0 and 2 pass
            self.assertEqual(s["hard_episodes"], len(no_tool))
            hard = (tmp / "out" / "hard-episodes.txt").read_text().split()
            self.assertEqual(sorted(hard), sorted(no_tool))
            rows = common.read_jsonl(tmp / "out" / "kept-rows.jsonl")
            per_ep = {}
            for r in rows:
                per_ep.setdefault(r["episode"], set()).add(r["turn"])
                self.assertEqual((r["arm"], r["teacher"]), ("A", W1.TEACHER))
            self.assertEqual(set(per_ep), {e["id"] for e in eps} - set(no_tool))
            self.assertEqual(second["summary"], s)
            self.assertEqual(set(s["views_over_attempts"]), {"model_clean", "corrected_model", "final_system"})
            self.assertEqual(s["views_over_attempts"]["final_system"], s["passing_attempts"])
            tel = first["telemetry"]
            self.assertEqual(tel["accelerators"], 2)
            self.assertEqual(tel["attempts_this_session"], 4 * n)
            self.assertIn("device_hours_this_session", tel)
            self.assertEqual(second["telemetry"]["attempts_this_session"], 0)
            self.assertTrue(all(abs(v - 1.0) < 1e-9 for v in __import__("sft").episode_weight_totals(rows).values()))
            self.assertEqual(sum(s["coverage_kept_attempts_per_episode"].values()), n)
            self.assertEqual(len(common.read_jsonl(tmp / "out" / "metrics.jsonl")), 4 * n)

    def test_refuses_a_mismatched_episode_file(self):
        eps, _, _ = gen_hare.make_episodes("dry-run-seed", 1)
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "e.jsonl"
            common.write_jsonl(p, eps)
            with self.assertRaises(SystemExit):
                W1.main(["--engine", "x", "--model", str(p), "--episodes", str(p), "--episodes-sha256", "0" * 64,
                         "--out", tmp])


class RegressionConfig(unittest.TestCase):
    CFG = json.loads((HERE / "regression" / "config.json").read_text())
    SUB = json.loads((HERE / "regression" / "mmlu_pro_subset.json").read_text())

    def test_three_benchmarks_pinned_with_metrics_and_no_results(self):
        self.assertEqual(set(self.CFG["benchmarks"]), {"ifeval", "bfcl", "mmlu_pro"})
        self.assertIn("NOT_EXECUTED", self.CFG["status"])
        for name, b in self.CFG["benchmarks"].items():
            self.assertEqual(len(b["dataset"]["revision"]), 40, name)
            self.assertTrue(b["primary_metric"], name)
            hashes = b["dataset"].get("files") or {b["dataset"]["file"]: b["dataset"]["sha256"]}
            self.assertTrue(all(len(h) == 64 for h in hashes.values()), name)
        self.assertEqual(self.CFG["rule_4"]["threshold_points"], 2.0)
        self.assertNotIn("results", json.dumps(self.CFG).lower().replace("no results", ""))

    def test_mmlu_pro_subset_is_100_per_category_and_reproducible(self):
        cats = self.SUB["categories"]
        self.assertEqual(len(cats), 14)
        self.assertTrue(all(len(v) == 100 for v in cats.values()))
        self.assertEqual(len({q for v in cats.values() for q in v}), 1400)
        self.assertEqual(self.CFG["benchmarks"]["bfcl"]["slice"]["total"], 1240)


class Manifest(unittest.TestCase):
    def test_manifest_is_current_and_tied_to_the_preregistered_plan(self):
        import manifest
        self.assertTrue(manifest.plan_check()["commit_matches"])
        self.assertEqual(json.loads(manifest.OUT.read_text()), manifest.build(),
                         "rerun: python3 manifest.py")


if __name__ == "__main__":
    unittest.main()
