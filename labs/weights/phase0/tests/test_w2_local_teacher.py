import copy
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("w2_local_teacher", HERE / "w2_local_teacher.py")
w2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w2)


def synthetic_population():
    rows, hard = [], set()
    hard_target = {"conflict_rule": 3, "distractor_resolve": 4,
                   "injection_output": 3, "stale_premise": 1}
    for family, count in w2.EXPECTED_FAMILIES.items():
        for i in range(count):
            eid = f"ep-{family}-{i:02d}"
            rows.append({"id": eid, "family": family, "semantic_secret": f"secret-{i}"})
            if family not in w2.TARGET_FAMILIES or i < hard_target.get(family, 0):
                hard.add(eid)
    rows.extend({"id": f"irrelevant-{i}", "family": "missing_admit", "semantic_secret": "ignored"}
                for i in range(7))
    assert len(hard) == 55
    return rows, hard


def dummy_identity(batch="b", token="one"):
    return {"schema": "identity", "batch": batch, "token": token}


class W2LocalTeacherTests(unittest.TestCase):
    def test_exact_99_membership_histogram_and_deterministic_order(self):
        rows, hard = synthetic_population()
        a, histogram = w2.select_population(rows, hard, "run-identity")
        b, histogram2 = w2.select_population(list(reversed(rows)), hard, "run-identity")
        self.assertEqual(len(a), 99)
        self.assertEqual(histogram, w2.EXPECTED_FAMILIES)
        self.assertEqual(histogram2, w2.EXPECTED_FAMILIES)
        self.assertEqual(a, b)
        self.assertEqual(a, sorted(a, key=lambda eid: (w2.order_digest("run-identity", eid), eid)))

    def test_membership_selection_and_commitment_ignore_semantic_content(self):
        rows, hard = synthetic_population()
        altered = copy.deepcopy(rows)
        for row in altered:
            row["semantic_secret"] = {"oracle": "different", "gold": [1, 2, 3]}
            row["world"] = "different"
        ids1, hist1 = w2.select_population(rows, hard, "run")
        ids2, hist2 = w2.select_population(altered, hard, "run")
        kwargs = dict(label="b", run_id="run", hard_set_sha256="h", episodes_sha256="e",
                      hard_membership_sha256=["x", "y"])
        p1 = w2.membership_payload(**kwargs, episode_ids=ids1, family_counts=hist1)
        p2 = w2.membership_payload(**kwargs, episode_ids=ids2, family_counts=hist2)
        salt = "11" * 32
        self.assertEqual(p1, p2)
        self.assertEqual(w2.common.commit(salt, p1), w2.common.commit(salt, p2))

    def test_frozen_sampling_thinking_and_teacher_identity(self):
        self.assertEqual(w2.TEACHER, "qwen3.6-35b-a3b-q4")
        self.assertEqual(w2.SAMPLING, {"temperature": 0.3, "top_p": 0.95, "seed": 0,
                                      "max_tokens": 700, "thinking": False})
        backend, captured = w2.frozen_backend("http://127.0.0.1:8096/v1"), {}

        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()

        class Opener:
            def open(self, request, timeout):
                captured.update(json.loads(request.data))
                return Response(json.dumps({"choices": [{"message": {"content": "ok"},
                                                           "finish_reason": "stop"}]}).encode())

        backend.opener = Opener()
        backend.step([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], [])
        self.assertEqual(captured["model"], w2.TEACHER)
        self.assertEqual((captured["temperature"], captured["top_p"], captured["seed"],
                          captured["max_tokens"]), (0.3, 0.95, 0, 700))
        self.assertEqual(captured["chat_template_kwargs"], {"enable_thinking": False})

    def test_model_visible_request_excludes_hidden_episode_fields(self):
        sent = []

        class Capture:
            def step(self, messages, tools):
                sent.append({"messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools)})
                return {"content": "I cannot determine that.\n{\"claims\":[]}", "tool_calls": []}

        sentinel = "HIDDEN-SENTINEL-UNIQUE"
        episode = {"id": "ep", "family": "no_tool", "principal": "alice", "prompt": "Say hello.",
                   "world": {"devices": [], "notes": []},
                   "oracle": {"answer": sentinel, "calls": []},
                   "contract": {"expect_claims": [{"value": sentinel}],
                                "forbidden_values": [sentinel]},
                   "audit_material": sentinel, "reserve_material": sentinel}
        w2.common.run_harness(Capture(), episode, w2.common.REPLAY)
        body = json.dumps(sent)
        self.assertNotIn(sentinel, body)
        for field in ("expect_claims", "forbidden_values", "oracle", "audit_material", "reserve_material"):
            self.assertNotIn(field, body)

    def test_terminal_grid_executes_each_slot_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            membership = {"commitment": "c", "payload": {"episode_ids": ["e0", "e1"]}}
            identity = dummy_identity()
            episodes = {eid: {"id": eid, "family": "f"} for eid in membership["payload"]["episode_ids"]}
            calls = []

            def trajectory(ep):
                calls.append(ep["id"])
                return {"episode": ep["id"], "family": "f", "ok_transport": True,
                        "messages": [], "trace": [], "attempts": [], "answer": "x"}

            grid = w2.run_grid(root, membership, identity, episodes, trajectory=trajectory)
            self.assertEqual(calls, ["e0", "e1"])
            self.assertTrue(all(s["status"] == "terminal" for s in grid["slots"]))
            w2.run_grid(root, membership, identity, episodes, trajectory=trajectory)
            self.assertEqual(calls, ["e0", "e1"])

    def test_resume_never_retries_a_started_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            membership = {"commitment": "c", "payload": {"episode_ids": ["e0"]}}
            identity = dummy_identity()
            grid = w2.initial_grid(membership, identity)
            grid["slots"][0]["status"] = "started"
            w2.atomic_write(root / "execution-identity.json", w2.json_blob(identity))
            w2.atomic_write(root / "grid.json", w2.json_blob(grid))
            called = []
            result = w2.run_grid(root, membership, identity, {"e0": {"id": "e0", "family": "f"}},
                                 trajectory=lambda ep: called.append(ep))
            self.assertEqual(called, [])
            receipt = w2.load_json(w2.slot_path(root, 0))
            self.assertEqual(receipt["raw_attempt"]["error"], "INTERRUPTED_AFTER_SLOT_START")
            self.assertEqual(result["slots"][0]["status"], "terminal")

    def test_changed_runtime_identity_cannot_resume(self):
        membership = {"commitment": "c", "payload": {"episode_ids": ["e0"]}}
        grid = w2.initial_grid(membership, dummy_identity(token="one"))
        with self.assertRaisesRegex(w2.LocalTeacherError, "changed runtime"):
            w2.validate_grid(grid, membership, dummy_identity(token="two"))

    def test_foreign_malformed_and_changed_receipts_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            membership = {"commitment": "c", "payload": {"episode_ids": ["e0"]}}
            identity = dummy_identity()
            grid = w2.initial_grid(membership, identity)
            (root / "receipts").mkdir()
            (root / "receipts" / "slot-999.json").write_text("{}")
            with self.assertRaisesRegex(w2.LocalTeacherError, "foreign receipt"):
                w2.reconcile_receipts(root, grid, identity)
            (root / "receipts" / "slot-999.json").unlink()
            (root / "receipts" / "slot-000.json").write_text("{}")
            with self.assertRaisesRegex(w2.LocalTeacherError, "malformed/foreign"):
                w2.reconcile_receipts(root, grid, identity)

    def test_correction_fallback_and_duplicates_cannot_enter_kept_data(self):
        base = {"ok_transport": True, "attempts": [], "outcome": "accepted"}
        metrics = {"keep": True, "views": {"model_clean": True}}
        self.assertTrue(w2.model_clean(base, metrics))
        self.assertFalse(w2.model_clean(dict(base, outcome="corrected", corrections_used=1), metrics))
        self.assertFalse(w2.model_clean(dict(base, fallback_used=True), metrics))
        self.assertFalse(w2.model_clean(dict(base, escalated=True), metrics))
        blocked = dict(base, attempts=[{"executed": False, "policy": "P3_duplicate_call"}])
        self.assertFalse(w2.model_clean(blocked, metrics))

    def test_shared_sft_projection_keeps_causal_prefixes_exact_tag_and_weight(self):
        record = {"episode": "e", "family": "f", "outcome": "accepted", "messages": [
            {"role": "system", "content": "s"}, {"role": "user", "content": "u"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "name": "n", "arguments": {}}]},
            {"role": "tool", "content": "o", "name": "n", "tool_call_id": "1"},
            {"role": "assistant", "content": "final"},
            {"role": "user", "content": "correction"}, {"role": "assistant", "content": "revised"}]}
        rows = w2.sft.rows_from_record(record, source="teacher", arm="B", teacher=w2.TEACHER)
        self.assertEqual([r["messages"][-1]["content"] for r in rows], ["", "final"])
        self.assertTrue(all((r["source"], r["arm"], r["teacher"]) ==
                            ("teacher", "B", "qwen3.6-35b-a3b-q4") for r in rows))
        w2.sft.apply_episode_weights(rows)
        self.assertEqual(w2.sft.episode_weight_totals(rows), {"e": 1.0})

    def test_filter_applies_weights_and_rejects_unclean(self):
        episodes = {"e0": {"id": "e0", "family": "f"}, "e1": {"id": "e1", "family": "f"}}
        rec0 = {"episode": "e0", "family": "f", "ok_transport": True, "attempts": [],
                "outcome": "accepted", "messages": [{"role": "system", "content": "s"},
                {"role": "user", "content": "u"}, {"role": "assistant", "content": "a"}]}
        rec1 = dict(rec0, episode="e1", fallback_used=True)
        receipts = [{"episode_id": "e0", "raw_attempt": rec0, "raw_attempt_sha256": "0"},
                    {"episode_id": "e1", "raw_attempt": rec1, "raw_attempt_sha256": "1"}]
        with mock.patch.object(w2.common, "judge", return_value={"keep": True,
                                                                 "views": {"model_clean": True}}):
            rows, results, summary = w2.filter_records(receipts, episodes)
        self.assertEqual((summary["offered"], summary["accepted"], summary["zero_pass"]), (2, 1, 1))
        self.assertEqual({r["episode"] for r in rows}, {"e0"})
        self.assertEqual(w2.sft.episode_weight_totals(rows), {"e0": 1.0})
        self.assertEqual([r["status"] for r in results], ["accepted", "zero_pass"])

    def test_audit_sample_is_deterministic_from_kept_row_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "kept.jsonl"
            rows = [{"episode": f"e{i}", "teacher": w2.TEACHER, "trace": f"t{i}",
                     "messages": [{"role": "assistant", "content": str(i)}]} for i in range(60)]
            w2.common.write_jsonl(path, rows)
            a, b = w2.astra_batch.audit_sample(path, 50), w2.astra_batch.audit_sample(path, 50)
            self.assertEqual(a, b)
            self.assertEqual((a["sampled"], a["traces"]), (50, 60))

    def test_execution_identity_binds_measured_model_and_engine_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            model, engine = root / w2.MODEL_FILE, root / "llama-server"
            model.write_bytes(b"model")
            engine.write_bytes(b"engine")
            runtime = {"batch": "b", "model": {"repo": w2.MODEL_REPO, "file": w2.MODEL_FILE,
                       "revision": w2.MODEL_REVISION, "sha256": None},
                       "engine": {"tag": w2.ENGINE_TAG, "binary_sha256": None},
                       "sampling": w2.SAMPLING, "server": w2.SERVER, "harness": {},
                       "runner_code_sha256": {}}
            version = mock.Mock(returncode=0, stdout="llama.cpp build 11146 (frozen)\n")
            with mock.patch.object(w2.subprocess, "run", return_value=version):
                identity = w2.execution_identity(runtime, {"commitment": "c"}, model, engine)
            self.assertEqual(identity["model"]["sha256"], w2.sha256_file(model))
            self.assertEqual(identity["engine"]["binary_sha256"], w2.sha256_file(engine))
            self.assertEqual(identity["engine"]["reported_version"], "llama.cpp build 11146 (frozen)")


if __name__ == "__main__":
    unittest.main()
