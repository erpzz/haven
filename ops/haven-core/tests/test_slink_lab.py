"""slink-lab decisions over a scripted Lab state; no SSH is run."""
import importlib.util
import pathlib
import types
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("slink_lab", pathlib.Path(__file__).resolve().parents[1] / "slink-lab.py")
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)

MODELS = [{"id": "qwen35-4b", "filename": "Qwen3.5-4B-Q4_K_M.gguf", "downloaded": True},
          {"id": "qwen36-35b-a3b", "filename": "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf", "downloaded": True}]


def engine(model, state):
    return {"state": state, "ownership": "OWNED", "started_at": 100.0, "label": model,
            "argv": ["llama-server", "--model", "/m/" + next(m["filename"] for m in MODELS if m["id"] == model)]}


class FakeLab:
    def __init__(self, states):
        self.states, self.calls = list(states), []

    def __call__(self, *args, check=True):
        self.calls.append(args)
        if args[0] == "state":
            return {"models": MODELS, **(self.states.pop(0) if len(self.states) > 1 else self.states[0])}
        if args[0] == "load":
            return {"job_id": "j1"}
        return {}


def run(fake, *argv):
    args = types.SimpleNamespace(model=argv[0], switch="--switch" in argv, context=4096, timeout=60)
    with mock.patch.object(lab, "labctl", fake), mock.patch.object(lab.time, "sleep"):
        lab.use(args)
    return [c[0] for c in fake.calls]


class UseTests(unittest.TestCase):
    def test_ready_same_model_is_a_no_op(self):
        fake = FakeLab([{"engine": engine("qwen36-35b-a3b", "READY")}])
        self.assertEqual(run(fake, "qwen36-35b-a3b"), ["state"])

    def test_starting_same_model_is_followed_not_requested_again(self):
        fake = FakeLab([{"engine": engine("qwen36-35b-a3b", "STARTING")}, {"engine": engine("qwen36-35b-a3b", "STARTING")},
                        {"engine": engine("qwen36-35b-a3b", "READY")}])
        calls = run(fake, "qwen36-35b-a3b")
        self.assertNotIn("load", calls)
        self.assertNotIn("unload", calls)

    def test_other_model_needs_switch(self):
        fake = FakeLab([{"engine": engine("qwen36-35b-a3b", "READY")}])
        with self.assertRaises(lab.LabError):
            run(fake, "qwen35-4b")
        self.assertEqual([c[0] for c in fake.calls], ["state"])

    def test_switch_unloads_then_loads_and_waits(self):
        fake = FakeLab([{"engine": engine("qwen36-35b-a3b", "READY")}, {"engine": engine("qwen35-4b", "STARTING")},
                        {"engine": engine("qwen35-4b", "READY")}])
        self.assertEqual(run(fake, "qwen35-4b", "--switch"), ["state", "unload", "load", "state", "state"])

    def test_external_backend_is_disconnected_only_with_switch(self):
        ext = {"engine": {"state": "STOPPED", "ownership": "NONE"},
               "connection": {"ownership": "EXTERNAL", "kind": "strata", "model": "x"}}
        with self.assertRaises(lab.LabError):
            run(FakeLab([ext]), "qwen35-4b")
        fake = FakeLab([ext, {"engine": engine("qwen35-4b", "READY")}])
        self.assertEqual(run(fake, "qwen35-4b", "--switch"), ["state", "disconnect", "load", "state"])

    def test_failed_load_is_reported_as_failure(self):
        fake = FakeLab([{"engine": {"state": "STOPPED", "ownership": "NONE"}},
                        {"engine": {"state": "STOPPED", "ownership": "NONE"},
                         "jobs": [{"id": "j1", "kind": "engine-start", "state": "FAILED", "error": "Engine exited.",
                                   "created_at": 200.0}]}])
        with self.assertRaises(lab.LabError) as err:
            run(fake, "qwen35-4b")
        self.assertIn("FAILED", str(err.exception))

    def test_unknown_model_is_refused_before_anything_changes(self):
        fake = FakeLab([{"engine": engine("qwen36-35b-a3b", "READY")}])
        with self.assertRaises(lab.LabError):
            run(fake, "nope", "--switch")
        self.assertEqual([c[0] for c in fake.calls], ["state"])


if __name__ == "__main__":
    unittest.main()
