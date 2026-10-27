"""Deterministic, no-model/no-network checks for the paradigm bake-off harness."""
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

PARADIGMS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARADIGMS))
import fetch
import report
import session


def model_for(data, **extra):
    return {"id": "m", "repo": "org/repo", "revision": "a" * 40, "file": "m.gguf",
            "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), **extra}


class FakeResponse(io.BytesIO):
    def __init__(self, data, status=200):
        super().__init__(data)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class FakeOpener:
    def __init__(self, data, status=200):
        self.data, self.status, self.requests = data, status, []

    def open(self, request, timeout=None):
        self.requests.append(request)
        start = 0
        if request.get_header("Range"):
            start = int(request.get_header("Range").split("=")[1].rstrip("-"))
        return FakeResponse(self.data[start:], self.status)


class FetchTests(unittest.TestCase):
    def test_preregistered_models_are_pinned(self):
        for m in fetch.load_models():
            self.assertTrue(fetch.resolve_url(m).startswith("https://huggingface.co/"))
            self.assertEqual(len(m["sha256"]), 64)
            self.assertIn("license", m)

    def test_refuses_branch_revisions_and_unsafe_names(self):
        with self.assertRaises(ValueError):
            fetch.resolve_url(model_for(b"x", revision="main"))
        with self.assertRaises(ValueError):
            fetch.resolve_url(model_for(b"x", file="../escape.gguf"))

    def test_download_verifies_and_renames(self):
        data = b"gguf" * 1000
        with tempfile.TemporaryDirectory() as tmp:
            r = fetch.fetch(model_for(data), tmp, opener=FakeOpener(data), log=lambda *_: None)
            self.assertEqual(r["status"], "DOWNLOADED_VERIFIED")
            self.assertEqual((pathlib.Path(tmp) / "m.gguf").read_bytes(), data)
            again = fetch.fetch(model_for(data), tmp, opener=FakeOpener(b""), log=lambda *_: None)
            self.assertEqual(again["status"], "PRESENT_VERIFIED")

    def test_digest_mismatch_is_quarantined(self):
        data = b"gguf" * 1000
        with tempfile.TemporaryDirectory() as tmp:
            bad = model_for(data, sha256="0" * 64)
            with self.assertRaises(ValueError):
                fetch.fetch(bad, tmp, opener=FakeOpener(data), log=lambda *_: None)
            self.assertFalse((pathlib.Path(tmp) / "m.gguf").exists())
            self.assertTrue((pathlib.Path(tmp) / "m.gguf.part.bad").exists())

    def test_resume_appends_after_range_and_hashes_prefix(self):
        data = bytes(range(256)) * 64
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "m.gguf.part").write_bytes(data[:1000])
            opener = FakeOpener(data, status=206)
            fetch.fetch(model_for(data), tmp, opener=opener, log=lambda *_: None)
            self.assertEqual(opener.requests[0].get_header("Range"), "bytes=1000-")
            self.assertEqual((pathlib.Path(tmp) / "m.gguf").read_bytes(), data)

    def test_resume_refused_when_range_ignored(self):
        data = b"z" * 5000
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "m.gguf.part").write_bytes(data[:10])
            with self.assertRaises(ValueError):
                fetch.fetch(model_for(data), tmp, opener=FakeOpener(data, status=200), log=lambda *_: None)

    def test_truncated_stream_keeps_part_and_resumes(self):
        data = bytes(range(256)) * 64

        class Flaky(FakeOpener):
            def open(self, request, timeout=None):
                response = super().open(request, timeout)
                if len(self.requests) == 1:  # the first stream ends early without an error
                    return FakeResponse(response.read()[:3000], self.status)
                return response

        with tempfile.TemporaryDirectory() as tmp:
            opener = Flaky(data, status=206)
            r = fetch.fetch_with_resume(model_for(data), tmp, opener=opener, log=lambda *_: None, wait=0)
            self.assertEqual(r["status"], "DOWNLOADED_VERIFIED")
            self.assertEqual(opener.requests[1].get_header("Range"), "bytes=3000-")
            self.assertEqual((pathlib.Path(tmp) / "m.gguf").read_bytes(), data)
            self.assertFalse((pathlib.Path(tmp) / "m.gguf.part.bad").exists())

    def test_oversized_download_is_refused(self):
        data = b"y" * 100
        with tempfile.TemporaryDirectory() as tmp:
            m = model_for(data)
            m["size_bytes"] = 50
            with self.assertRaises(ValueError):
                fetch.fetch(m, tmp, opener=FakeOpener(data), log=lambda *_: None)


SAMPLE_LOG = """
load_tensors: offloaded 33/33 layers to GPU
load_tensors:   CPU_Mapped model buffer size =   303.75 MiB
load_tensors:        CUDA0 model buffer size =  2368.21 MiB
llama_context:  CUDA_Host  output buffer size =     0.58 MiB
llama_kv_cache:      CUDA0 KV buffer size =  1040.00 MiB
llama_kv_cache: size = 1040.00 MiB ( 33280 cells,   8 layers,  1/1 seqs), K (f16):  520.00 MiB, V (f16):  520.00 MiB
llama_memory_recurrent:      CUDA0 RS buffer size =    50.25 MiB
llama_memory_recurrent: size =   50.25 MiB (     1 cells,  32 layers,  1 seqs), R (f32):    2.25 MiB, S (f32):   48.00 MiB
sched_reserve:      CUDA0 compute buffer size =   300.75 MiB
"""


class SessionTests(unittest.TestCase):
    def test_server_args_are_loopback_keyed_and_preregistered(self):
        args = session.server_args({"id": "m"}, "/m.gguf", 8192, 18931, "/k", "/l")
        self.assertEqual(args[args.index("--host") + 1], "127.0.0.1")
        self.assertIn("--api-key-file", args)
        for flag in ("--jinja", "--no-webui"):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index("--fit") + 1], "off")
        self.assertEqual(args[args.index("-np") + 1], "1")
        self.assertNotIn("--cpu-moe", args)
        self.assertIn("--cpu-moe", session.server_args({"offload": "cpu-moe"}, "/m", 8192, 18931, "/k", "/l"))

    def test_lab_and_strata_ports_are_refused(self):
        for port in (8877, 8878, 8880, 80):
            with self.assertRaises(ValueError):
                session.server_args({}, "/m", 8192, port, "/k", "/l")

    def test_preregistered_flags_match_harness(self):
        prereg = json.loads(session.PREREG.read_text())
        args = session.server_args({}, "/m", 8192, 18931, "/k", "/l")
        for flag in prereg["condition"]["server_args"]:
            self.assertIn(flag, args)

    def test_parse_buffers(self):
        b = session.parse_buffers(SAMPLE_LOG)
        self.assertEqual(b["load_tensors:CUDA0"], 2368.21)
        self.assertEqual(b["llama_kv_cache:CUDA0"], 1040.0)
        self.assertEqual(b["llama_kv_cache:total"], 1040.0)
        self.assertEqual(b["llama_memory_recurrent:CUDA0"], 50.25)
        self.assertEqual(b["sched_reserve:CUDA0"], 300.75)
        self.assertEqual(session.parse_buffers(""), {})

    def test_probe_tokens_exact_length(self):
        self.assertEqual(len(session.probe_tokens([1, 2, 3], 8192)), 8192)
        self.assertEqual(session.probe_tokens([1, 2, 3], 4), [1, 2, 3, 1])
        with self.assertRaises(ValueError):
            session.probe_tokens([], 10)

    def test_probes_skip_depths_beyond_context(self):
        class Fake:
            class sampler:
                @staticmethod
                def snapshot():
                    return {"peak_gpu_mib": 1, "peak_rss_mib": 1}

            def tokenize(self, text):
                return [5, 6, 7]

            def completion(self, tokens, n):
                return {"timings": {"prompt_n": len(tokens), "prompt_per_second": 1000.0,
                                    "predicted_n": n, "predicted_per_second": 50.0}}
        rows = session.run_probes(Fake(), 8192)
        status = {r["prompt_tokens"]: r["status"] for r in rows}
        self.assertEqual(status, {1024: "OK", 2048: "OK", 8192: "DOES_NOT_FIT_CTX", 32768: "DOES_NOT_FIT_CTX"})
        self.assertEqual(rows[0]["prompt_n"], 1024)

    def test_lab_busy(self):
        idle = {"jobs": [{"kind": "generation", "state": "COMPLETED"}], "engine": {"state": "STOPPED"},
                "prepared_runtime": {"switch_job": None}}
        self.assertIsNone(session.lab_busy(idle))
        self.assertIn("RUNNING", session.lab_busy({**idle, "jobs": [{"kind": "generation", "state": "RUNNING"}]}))
        self.assertIsNotNone(session.lab_busy({**idle, "engine": {"state": "READY"}}))
        self.assertIsNotNone(session.lab_busy({**idle, "engine": {"state": "READY", "compute": "gpu"}}))
        self.assertIsNotNone(session.lab_busy({**idle, "engine": {"state": "STARTING", "compute": "cpu"}}))
        self.assertIsNone(session.lab_busy({**idle, "engine": {"state": "READY", "compute": "cpu"}}))
        self.assertIsNotNone(session.lab_busy({**idle, "prepared_runtime": {"switch_job": "x"}}))

    def test_restore_leaves_lab_connection_when_not_disconnected(self):
        calls = []
        saved = (session.strata_active, session.systemctl, session.http_json, session.STRATA_KEY,
                 session.subprocess.run)
        with tempfile.TemporaryDirectory() as tmp:
            key = pathlib.Path(tmp) / "k"
            key.write_text("secret\n")
            try:
                session.strata_active = lambda: True
                session.systemctl = lambda *a, **k: calls.append(a)
                session.http_json = lambda *a, **k: {"data": [{"id": "strata"}]}
                session.STRATA_KEY = key
                session.subprocess.run = lambda *a, **k: calls.append(("run", a))
                r = session.restore({}, reconnect_lab=False, wait_seconds=5)
            finally:
                (session.strata_active, session.systemctl, session.http_json, session.STRATA_KEY,
                 session.subprocess.run) = saved
        self.assertTrue(r["restored"])
        self.assertEqual(r["lab_connection"], "LEFT_AS_FOUND")
        self.assertEqual(calls, [])  # Strata already active; labctl was not invoked

    def test_eval_command_matches_preregistration(self):
        prereg = json.loads(session.PREREG.read_text())["eval_command"]
        for token in ("--sets heldout,legacy", "--max-tokens 1024", "--temperature 0", "--backend openai"):
            self.assertIn(token, prereg)


class ReportTests(unittest.TestCase):
    def test_wilson_matches_published_reference(self):
        self.assertEqual(report.wilson(76, 110), [59.9, 77.0])  # RESULTS.md, Qwen3.5-4B
        self.assertEqual(report.wilson(14, 110), [7.7, 20.2])
        self.assertIsNone(report.wilson(0, 0))

    def test_sign_test(self):
        self.assertAlmostEqual(report.sign_test(37, 13), 0.000936, places=5)  # RESULTS.md: p≈0.0009
        self.assertGreater(report.sign_test(8, 44), 0)
        self.assertLess(report.sign_test(8, 44), 0.000001)
        self.assertEqual(report.sign_test(0, 0), 1.0)
        self.assertEqual(report.sign_test(3, 3), 1.0)

    def test_truncated_steps(self):
        records = [{"steps": [{"usage": {"completion_tokens": 1024}}, {"usage": {"completion_tokens": 9}}]},
                   {"steps": [{"usage": {}}]}]
        self.assertEqual(report.truncated_steps(records), 1)

    def test_paired_counts_and_unpaired(self):
        a = {"x": {"pass": True}, "y": {"pass": False}, "z": {"pass": True}}
        b = {"x": {"pass": True}, "y": {"pass": True}}
        out = report.paired(a, b, ["x", "y", "z"])
        self.assertEqual((out["both"], out["gained"], out["unpaired"]), (1, 1, 1))

    def test_performance_is_sanitized(self):
        receipt = {"status": "COMPLETED", "attempts": [
            {"ctx": 33280, "ready": False, "seconds": 3.0},
            {"ctx": 8192, "ready": True, "seconds": 20.0, "buffers_mib": {"a": 1},
             "final": {"peak_gpu_mib": 7000, "peak_rss_mib": 900},
             "probes": [{"prompt_tokens": 1024, "status": "OK", "prompt_tok_s": 1.0, "decode_tok_s": 2.0,
                         "after": {"peak_gpu_mib": 1}}],
             "eval": {"seconds": 100.0, "exit_code": 0}}]}
        out = report.performance(receipt)
        self.assertEqual(out["ctx"], 8192)
        self.assertEqual(out["peak_gpu_mib"], 7000)
        self.assertNotIn("after", out["probes"][0])
        self.assertEqual(out["probes"][0]["cumulative_peak_memory_mib"]["peak_gpu_mib"], 1)
        self.assertEqual([a["ready"] for a in out["load_attempts"]], [False, True])

    def test_ready_without_reconnection_is_not_reported_as_connected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp)
            (path / "session.json").write_text(json.dumps({"models": [], "restore": {
                "restored": True, "strata_ready_seconds": 12, "lab_connection": "LEFT_AS_FOUND"}}))
            result = report.build(path)["session"]
        self.assertTrue(result["strata_ready"])
        self.assertTrue(result["lab_connection_left_as_found"])
        self.assertFalse(result["strata_restored_and_connected"])

    def test_markdown_handles_missing_and_complete_models(self):
        result = {"models": {
            "ref": {"performance": {"ctx": 33280, "probes": [
                {"prompt_tokens": 32768, "status": "OK", "decode_tok_s": 40.0}], "buffers_mib": {}},
                "tool_benchmark": {"heldout": {"passed": 76, "total": 110, "wilson95_pct": [59.9, 77.0]},
                                   "by_track": {"paraphrase": {"passed": 34, "total": 60}}}},
            "big": {"performance": {}, "adjudicated": {"pass": 121, "episodes": 180},
                    "paired_vs_reference_adjudicated": {"gained": 73, "lost": 10, "sign_test_p": 5.8e-13},
                    "tool_benchmark": {"heldout": {"passed": 81, "total": 110, "wilson95_pct": [64.7, 81.0]},
                                       "by_track": {}}},
            "gone": {"status": "SKIPPED_BUDGET"}}}
        text = report.markdown(result)
        self.assertIn("| 121/180 (73/10, p=5.8e-13) |", text)
        self.assertIn("| ref | 76/110 | 59.9–77.0 | — | 34/60 |", text)
        self.assertIn("| gone | SKIPPED_BUDGET |", text)
        self.assertIn("40.0 |", text)


if __name__ == "__main__":
    unittest.main()
