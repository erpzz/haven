"""The W1 Phase 1 notebook is built (not run) and current; its runner works end to end on CPU
against a fake model server; the regression config is complete. No GPU, no model, no network."""
from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import json
import pathlib
import subprocess
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

    def test_notebook_allocation_timer_wraps_setup_and_public_summary(self):
        code_cells = [(i, c["source"]) for i, c in enumerate(NB["cells"]) if c["cell_type"] == "code"]
        first_i, first_src = code_cells[0]
        self.assertIn("NOTEBOOK_STARTED_MONOTONIC = time.monotonic()", first_src)

        setup_i = next(i for i, src in code_cells if "git clone -q --filter=blob:none" in src)
        engine_i = next(i for i, src in code_cells if 'ENGINE = build_llama("b11146"' in src)
        model_i = next(i for i, src in code_cells if "M4 = fetch(MODEL)" in src)
        run_i = next(i for i, src in code_cells if "kaggle/w1_phase1.py --engine" in src)
        final_i, final_src = code_cells[-1]
        self.assertLess(first_i, setup_i)
        self.assertLess(first_i, engine_i)
        self.assertLess(first_i, model_i)
        self.assertLess(first_i, run_i)
        self.assertGreater(final_i, run_i)
        self.assertIn("NOTEBOOK_ENDED_MONOTONIC = time.monotonic()", final_src)
        self.assertIn("collector_summary_sha256", final_src)
        self.assertIn("notebook_device_hours", BUILD.NOTEBOOK_TIMING_HELPER)
        self.assertIn("public_receipt_schema", final_src)

        ns = {}
        exec(BUILD.NOTEBOOK_TIMING_HELPER, ns)
        receipt = ns["notebook_timing_receipt"](100.0, 7300.0, 2, 1.5)
        self.assertEqual(receipt["notebook_wall_hours"], 2.0)
        self.assertEqual(receipt["notebook_device_hours"], 4.0)
        self.assertEqual(receipt["collector_wall_hours_bound"], 1.5)
        with self.assertRaises(RuntimeError):
            ns["notebook_timing_receipt"](100.0, 3700.0, 2, 1.5)

    def test_engine_cell_is_the_run1_helper(self):
        cell = (HERE / "kaggle" / "llama_build_cell.py").read_text()
        self.assertIn('def build_llama(tag, prefix):', cell)
        self.assertIn('ENGINE = build_llama("b11146"', next(c["source"] for c in NB["cells"] if "def build_llama" in c["source"]))

    def test_notebook_preflight_is_complete_fail_fast_and_before_engine_startup(self):
        self.assertIn("tests/test_phase0.py", BUILD.CODE)
        self.assertNotIn("tests/test_notebook_and_config.py", BUILD.CODE)  # structural self-tests stay build-time
        pre = next(i for i, cell in enumerate(NB["cells"])
                   if cell["cell_type"] == "code" and "python3 -m unittest discover -s tests -p" in cell["source"]
                   and "test_phase0.py" in cell["source"])
        eng = next(i for i, cell in enumerate(NB["cells"])
                   if cell["cell_type"] == "code" and 'ENGINE = build_llama("b11146"' in cell["source"])
        self.assertLess(pre, eng)
        self.assertNotIn("| tail", NB["cells"][pre]["source"])
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "test_harmless_failure.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n"
                "    def test_fail(self): self.fail('intentional preflight failure')\n")
            proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", tmp, "-v"],
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)


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
            self.assertEqual(len(tel["sessions"]), 1)
            sess = tel["sessions"][0]
            self.assertEqual((sess["queued"], sess["started"], sess["model_requested"], sess["terminal"]),
                             (4 * n, 4 * n, 4 * n, 4 * n))
            self.assertEqual((sess["skipped_before_start"], sess["timed_out"]), (0, 0))
            self.assertIn("device_hours", sess)
            self.assertEqual(second["telemetry"]["sessions"], tel["sessions"])
            self.assertEqual(first["receipt_grid"]["complete"], True)
            self.assertEqual(first["receipt_grid"]["terminal_pairs"], 4 * n)
            self.assertTrue(first["summary"]["gate_G1"]["eligible"])
            self.assertTrue(all(abs(v - 1.0) < 1e-9 for v in __import__("sft").episode_weight_totals(rows).values()))
            self.assertEqual(sum(s["coverage_kept_attempts_per_episode"].values()), n)
            self.assertEqual(len(common.read_jsonl(tmp / "out" / "metrics.jsonl")), 4 * n)

    def test_receipt_grid_rejects_missing_duplicate_foreign_and_hash_mismatch(self):
        assigned = {("e", 0)}
        run_id = "run-test"
        record = {"episode": "e", "attempt": 0, "run_id": run_id}
        metric = {"episode": "e", "attempt": 0, "run_id": run_id,
                  "record_sha256": common.sha256_bytes(common.canonical(record))}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            rp, mp = tmp / "r.jsonl", tmp / "m.jsonl"
            common.write_jsonl(rp, [record])
            common.write_jsonl(mp, [metric])
            records, metrics = W1._validate_receipts(rp, mp, assigned, run_id)
            self.assertEqual(set(records), assigned)
            self.assertEqual(set(metrics), assigned)

            common.write_jsonl(mp, [metric, metric])
            with self.assertRaises(SystemExit):
                W1._validate_receipts(rp, mp, assigned, run_id)

            common.write_jsonl(mp, [])
            with self.assertRaises(SystemExit):
                W1._validate_receipts(rp, mp, assigned, run_id)

            foreign = {**record, "episode": "foreign"}
            common.write_jsonl(rp, [foreign])
            common.write_jsonl(mp, [{**metric, "episode": "foreign"}])
            with self.assertRaises(SystemExit):
                W1._validate_receipts(rp, mp, assigned, run_id)

            common.write_jsonl(rp, [record])
            common.write_jsonl(mp, [{**metric, "record_sha256": "0" * 64}])
            with self.assertRaises(SystemExit):
                W1._validate_receipts(rp, mp, assigned, run_id)

    def test_resume_identity_refuses_changed_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "run_identity.json"
            one = {"schema": "x", "settings": {"attempts": 8}}
            W1._freeze_identity(path, one)
            with self.assertRaises(SystemExit):
                W1._freeze_identity(path, {"schema": "x", "settings": {"attempts": 7}})

    def test_deadline_skips_are_counted_but_cannot_make_g1_eligible(self):
        eps, _, _ = gen_hare.make_episodes("deadline-seed", 1)
        eps = eps[:2]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            ep_path, model = tmp / "eps.jsonl", tmp / "fake.gguf"
            common.write_jsonl(ep_path, eps)
            model.write_bytes(b"not a model")
            argv = ["--engine", "none", "--model", str(model), "--model-sha256", common.sha256_file(model),
                    "--episodes", str(ep_path), "--episodes-sha256", common.sha256_file(ep_path),
                    "--out", str(tmp / "out"), "--gpus", "0", "--attempts", "2", "--deadline-minutes", "-1"]
            with mock.patch.object(W1, "start_server", lambda *a: FakeProc()), \
                    mock.patch.object(W1.agent, "OpenAIBackend",
                                      side_effect=AssertionError("deadline-skipped slot reached model backend")):
                W1.main(argv)
            summary = json.loads((tmp / "out" / "summary.json").read_text())
            sess = summary["telemetry"]["sessions"][0]
            self.assertEqual(summary["status"], "PARTIAL")
            self.assertFalse(summary["receipt_grid"]["complete"])
            self.assertFalse(summary["summary"]["gate_G1"]["eligible"])
            self.assertIsNone(summary["summary"]["gate_G1"]["in_band"])
            self.assertEqual(sess["queued"], 4)
            self.assertEqual(sess["started"], 4)
            self.assertEqual(sess["model_requested"], 0)
            self.assertEqual(sess["terminal"], 0)
            self.assertEqual(sess["skipped_before_start"], 4)

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
