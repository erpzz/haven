import copy
import importlib.util
import io
import json
import pathlib
import tempfile
import types
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


def valid_hardware(token="0"):
    return {"provider": "nvidia-smi", "gpu_count": 2,
            "gpu_models": ["NVIDIA T4", "NVIDIA T4"],
            "gpu_uuids": [f"GPU-{token}-a", f"GPU-{token}-b"],
            "query_sha256": f"hardware-{token}"}


def full_membership(ids=None):
    ids = list(ids or ["e0"])
    return {"commitment": "c", "payload": {"selected_count": len(ids),
            "family_counts": {"f": len(ids)}, "episode_ids": ids}}


def full_runtime():
    return {"batch": "b", "membership_file_sha256": "membership-sha",
            "episodes_sha256": "episodes-sha", "teacher": w2.TEACHER,
            "model": {"repo": w2.MODEL_REPO, "file": w2.MODEL_FILE,
                      "revision": w2.MODEL_REVISION, "sha256": None,
                      "sha256_status": "bind-before-inference"},
            "engine": {"tag": w2.ENGINE_TAG, "binary_sha256": None,
                       "binary_sha256_status": "bind-before-inference"},
            "sampling": dict(w2.SAMPLING), "server": dict(w2.SERVER),
            "harness": {"correction": False}, "runner_code_sha256": {"runner": "sha"}}


def full_identity(token="0"):
    runtime = full_runtime()
    return {"schema": w2.BOUND_IDENTITY_SCHEMA, "batch": "b",
            "membership_commitment": "c", "membership_file_sha256": "membership-sha",
            "episodes_sha256": "episodes-sha", "teacher": w2.TEACHER,
            "model": {**runtime["model"], "sha256": f"model-{token}", "sha256_status": "bound"},
            "engine": {**runtime["engine"], "binary_sha256": f"engine-{token}",
                       "binary_sha256_status": "bound", "reported_version": "build 11146",
                       "reported_version_sha256": f"version-{token}"},
            "hardware": valid_hardware(token), "sampling": runtime["sampling"],
            "server": runtime["server"], "harness": runtime["harness"],
            "runner_code_sha256": runtime["runner_code_sha256"]}


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
            runtime = full_runtime()
            version = mock.Mock(returncode=0, stdout="llama.cpp build 11146 (frozen)\n")
            with mock.patch.object(w2.subprocess, "run", return_value=version):
                identity = w2.execution_identity(runtime, {"commitment": "c"}, model, engine,
                                                 hardware=valid_hardware())
            self.assertEqual(identity["model"]["sha256"], w2.sha256_file(model))
            self.assertEqual(identity["engine"]["binary_sha256"], w2.sha256_file(engine))
            self.assertEqual(identity["engine"]["reported_version"], "llama.cpp build 11146 (frozen)")

    def test_bind_preflight_writes_receipts_without_model_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            runtime_path = root / "runtime.json"
            runtime_path.write_text("{}")
            identity_path, receipt_path = root / "identity.json", root / "bound.json"
            membership, identity = full_membership(), full_identity()
            args = types.SimpleNamespace(runtime=runtime_path, membership=root / "membership.json",
                                         episodes=root / "episodes.jsonl", model_file=root / w2.MODEL_FILE,
                                         engine_binary=root / "llama-server",
                                         bound_identity=identity_path, bound_receipt=receipt_path)
            with mock.patch.object(w2, "verify_runtime", return_value=membership), \
                    mock.patch.object(w2, "execution_identity", return_value=identity), \
                    mock.patch.object(w2, "frozen_backend") as backend, \
                    mock.patch.object(w2.common, "run_harness") as harness, \
                    mock.patch("sys.stdout", new=io.StringIO()):
                w2.cmd_bind(args)
            backend.assert_not_called()
            harness.assert_not_called()
            self.assertEqual(identity_path.read_bytes(), w2.json_blob(identity))
            self.assertEqual(receipt_path.read_bytes(),
                             w2.pretty_json_blob(w2.bound_public_receipt(identity, membership)))

    def test_run_refuses_without_bound_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            runtime_path = root / "runtime.json"
            runtime_path.write_text("{}")
            args = types.SimpleNamespace(runtime=runtime_path, membership=root / "membership.json",
                                         episodes=root / "episodes.jsonl", model_file="missing-model",
                                         engine_binary="missing-engine", bound_identity=root / "missing-id",
                                         bound_receipt=root / "missing-receipt", run_dir=root / "run",
                                         base_url="http://127.0.0.1:8096/v1")
            with mock.patch.object(w2, "verify_runtime", return_value=full_membership()):
                with self.assertRaisesRegex(w2.LocalTeacherError, "required before run"):
                    w2.cmd_run(args)

    def test_run_refuses_changed_bound_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            runtime_path = root / "runtime.json"
            runtime_path.write_text("{}")
            membership, old, fresh = full_membership(), full_identity("old"), full_identity("new")
            identity_path, receipt_path = root / "identity.json", root / "receipt.json"
            identity_path.write_bytes(w2.json_blob(old))
            receipt_path.write_bytes(w2.pretty_json_blob(w2.bound_public_receipt(old, membership)))
            args = types.SimpleNamespace(runtime=runtime_path, membership=root / "membership.json",
                                         episodes=root / "episodes.jsonl", model_file="model",
                                         engine_binary="engine", bound_identity=identity_path,
                                         bound_receipt=receipt_path, run_dir=root / "run",
                                         base_url="http://127.0.0.1:8096/v1")
            with mock.patch.object(w2, "verify_runtime", return_value=membership), \
                    mock.patch.object(w2, "execution_identity", return_value=fresh):
                with self.assertRaisesRegex(w2.LocalTeacherError, "identity bytes/hash differ"):
                    w2.cmd_run(args)

    def test_model_and_engine_byte_changes_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            model, engine = root / w2.MODEL_FILE, root / "llama-server"
            model.write_bytes(b"model-v1")
            engine.write_bytes(b"engine-v1")
            runtime, membership = full_runtime(), full_membership()
            version = mock.Mock(returncode=0, stdout="llama.cpp build 11146\n")
            with mock.patch.object(w2.subprocess, "run", return_value=version):
                identity = w2.execution_identity(runtime, membership, model, engine,
                                                 hardware=valid_hardware())
            identity_path, receipt_path = root / "identity.json", root / "receipt.json"
            identity_path.write_bytes(w2.json_blob(identity))
            receipt_path.write_bytes(w2.pretty_json_blob(w2.bound_public_receipt(identity, membership)))
            model.write_bytes(b"model-v2")
            with mock.patch.object(w2.subprocess, "run", return_value=version):
                with self.assertRaisesRegex(w2.LocalTeacherError, "identity bytes/hash differ"):
                    w2.verify_bound_artifacts(runtime, membership, model_file=model,
                                              engine_binary=engine, identity_path=identity_path,
                                              receipt_path=receipt_path, hardware=valid_hardware())
            model.write_bytes(b"model-v1")
            engine.write_bytes(b"engine-v2")
            with mock.patch.object(w2.subprocess, "run", return_value=version):
                with self.assertRaisesRegex(w2.LocalTeacherError, "identity bytes/hash differ"):
                    w2.verify_bound_artifacts(runtime, membership, model_file=model,
                                              engine_binary=engine, identity_path=identity_path,
                                              receipt_path=receipt_path, hardware=valid_hardware())

    def test_wrong_engine_version_and_non_2xt4_hardware_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            model, engine = root / w2.MODEL_FILE, root / "llama-server"
            model.write_bytes(b"model")
            engine.write_bytes(b"engine")
            wrong = mock.Mock(returncode=0, stdout="llama.cpp build 11145\n")
            with mock.patch.object(w2.subprocess, "run", return_value=wrong):
                with self.assertRaisesRegex(w2.LocalTeacherError, "b11146"):
                    w2.execution_identity(full_runtime(), full_membership(), model, engine,
                                          hardware=valid_hardware())
            version = mock.Mock(returncode=0, stdout="llama.cpp build 11146\n")
            bad_hardware = {**valid_hardware(), "gpu_count": 1, "gpu_models": ["NVIDIA T4"],
                            "gpu_uuids": ["GPU-one"]}
            with mock.patch.object(w2.subprocess, "run", return_value=version):
                with self.assertRaisesRegex(w2.LocalTeacherError, "exactly 2x NVIDIA T4"):
                    w2.execution_identity(full_runtime(), full_membership(), model, engine,
                                          hardware=bad_hardware)

    def test_bound_public_receipt_has_required_public_safe_identity(self):
        receipt = w2.bound_public_receipt(full_identity(), full_membership())
        required = {"schema", "batch", "offered", "membership_commitment",
                    "execution_identity_sha256", "teacher", "model", "engine", "hardware",
                    "sampling", "server", "harness_sha256", "runner_code_sha256"}
        self.assertTrue(required.issubset(receipt))
        self.assertEqual(receipt["offered"], 1)
        self.assertEqual(receipt["hardware"],
                         {"gpu_count": 2, "gpu_models": ["NVIDIA T4", "NVIDIA T4"]})
        self.assertNotIn("episode_ids", json.dumps(receipt))
        self.assertNotIn("gpu_uuids", receipt["hardware"])

    def test_execution_receipt_fields_and_aggregate_commitment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            membership, identity = full_membership(["e0", "e1"]), full_identity()
            episodes = {eid: {"id": eid, "family": "f"} for eid in membership["payload"]["episode_ids"]}

            def trajectory(ep):
                return {"episode": ep["id"], "family": "f", "ok_transport": ep["id"] == "e0",
                        "messages": [], "trace": [], "attempts": [], "answer": "x",
                        "elapsed_seconds": 2.5, "steps": [{"usage": {"prompt_tokens": 10,
                                                                       "completion_tokens": 4}}]}

            grid = w2.run_grid(root, membership, identity, episodes, trajectory=trajectory)
            bound = root / "bound.json"
            bound.write_bytes(b"bound\n")
            first = w2.build_execution_receipt(root, grid, identity, membership, bound)
            second = w2.build_execution_receipt(root, grid, identity, membership, bound)
            required = {"batch", "membership_commitment", "execution_identity_sha256",
                        "model_sha256", "engine", "hardware", "sampling", "server",
                        "harness_sha256", "runner_code_sha256", "offered_slots",
                        "terminal_slots", "open_slots", "transport_success", "transport_failure",
                        "aggregate_completion_tokens", "aggregate_prompt_tokens",
                        "wall_clock_execution_seconds", "gpu_device_hours", "terminal_grid_sha256",
                        "slot_receipts_aggregate_sha256"}
            self.assertTrue(required.issubset(first))
            self.assertEqual(first, second)
            self.assertEqual((first["offered_slots"], first["terminal_slots"], first["open_slots"]),
                             (2, 2, 0))
            self.assertEqual((first["transport_success"], first["transport_failure"]), (1, 1))
            self.assertEqual((first["aggregate_prompt_tokens"],
                              first["aggregate_completion_tokens"]), (20, 8))
            slot = w2.slot_path(root, 1)
            changed = w2.load_json(slot)
            changed["raw_attempt"]["answer"] = "changed"
            changed["raw_attempt_sha256"] = w2.sha256_bytes(w2.canonical(changed["raw_attempt"]))
            w2.atomic_write(slot, w2.json_blob(changed))
            third = w2.build_execution_receipt(root, grid, identity, membership, bound)
            self.assertNotEqual(first["slot_receipts_aggregate_sha256"],
                                third["slot_receipts_aggregate_sha256"])

    def test_persisted_summary_binds_finalized_audit_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            rows = [{"episode": "e0", "teacher": w2.TEACHER, "messages": []}]
            results = [{"episode": "e0", "status": "accepted"}]
            summary = {"schema": w2.FINALIZATION_SCHEMA, "offered": 1, "accepted": 1,
                       "zero_pass": 0, "by_family": {"f": {"offered": 1, "accepted": 1,
                                                              "zero_pass": 0}},
                       "kept_sft_rows": 1, "execution_identity_sha256": "identity"}
            packet = {"schema": w2.AUDIT_SCHEMA,
                      "audit_sample": {"traces": 1, "sampled": 1}, "records": []}
            final = w2.persist_filter_outputs(out_dir=root, rows=rows, results=results,
                                              summary=summary, packet_builder=lambda kept: packet)
            persisted = w2.load_json(root / "summary.json")
            self.assertEqual(persisted, final)
            self.assertIn("audit_packet_sha256", persisted)
            self.assertEqual(persisted["audit_packet_sha256"],
                             w2.sha256_file(root / "audit-v1.private.json"))


if __name__ == "__main__":
    unittest.main()
