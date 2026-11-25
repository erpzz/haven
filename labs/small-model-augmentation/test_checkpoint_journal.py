import hashlib, json, tempfile, threading, unittest
from pathlib import Path
import checkpoint_journal as c

MANIFEST = hashlib.sha256(b"manifest").hexdigest()


class JournalTests(unittest.TestCase):
    def make(self, d):
        return c.Journal(Path(d, "run.jsonl"), "run-1", MANIFEST, fsync=False).open()

    def test_new_journal_and_complete_unit(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            j.append("model_request_started", "q1", 1, "m1", True,
                     hashlib.sha256(b"prompt-artifact").hexdigest())
            j.append("model_response_committed", "q1", 1, "m1", False,
                     hashlib.sha256(b"response-artifact").hexdigest())
            j.append("tool_dispatch_started", "q1", 1, "t1", True)
            j.append("tool_result_committed", "q1", 1, "t1", False,
                     hashlib.sha256(b"tool-result-artifact").hexdigest())
            j.append("unit_completed", "q1", 1,
                     payload_sha256=hashlib.sha256(b"result-row").hexdigest())
            self.assertEqual(j.state()["completed_units"], ["q1"])
            raw = Path(d, "run.jsonl").read_text()
            self.assertNotIn("prompt-artifact", raw)
            self.assertNotIn("tool-result-artifact", raw)

    def test_torn_tail_is_ignored_and_repaired_on_append(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            p = Path(d, "run.jsonl")
            with p.open("ab") as f:
                f.write(b'{"partial":')
            s = c.scan(p)
            self.assertTrue(s.torn_tail)
            self.assertTrue(s.ok)
            j.append("model_request_started", "q1", 1, "m1", True)
            self.assertFalse(c.scan(p).torn_tail)
            self.assertEqual(len(c.scan(p).events), 3)

    def test_committed_corruption_blocks_not_repairs(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            p = Path(d, "run.jsonl")
            with p.open("ab") as f:
                f.write(b'not-json\n')
            s = c.scan(p)
            self.assertFalse(s.ok)
            self.assertIn("CORRUPT_COMMITTED_LINE", s.errors)
            with self.assertRaises(ValueError):
                j.append("unit_started", "q1", 1)

    def test_hash_chain_detects_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            p = Path(d, "run.jsonl")
            rows = p.read_text().splitlines()
            e = json.loads(rows[1])
            e["unit"] = "q2"
            rows[1] = json.dumps(e, separators=(",", ":"), sort_keys=True)
            p.write_text("\n".join(rows) + "\n")
            self.assertIn("EVENT_HASH_MISMATCH", c.scan(p).errors)

    def test_manifest_must_be_bound_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                c.Journal(Path(d, "run.jsonl"), "run-1", c.ZERO, fsync=False)

    def test_append_accepts_hash_not_raw_payload(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            with self.assertRaises(TypeError):
                j.append("model_request_started", "q1", 1, "m1", True,
                         payload={"private": "target"})
            with self.assertRaises(ValueError):
                j.append("model_request_started", "q1", 1, "m1", True, "not-a-hash")

    def test_manifest_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.make(d)
            other = c.Journal(Path(d, "run.jsonl"), "run-1",
                              hashlib.sha256(b"other").hexdigest(), fsync=False)
            with self.assertRaises(ValueError):
                other.open()

    def test_incomplete_model_request_is_retryable(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            j.append("model_request_started", "q1", 1, "m1", True)
            st = j.state()
            self.assertEqual(st["retryable_units"][0]["unit"], "q1")
            self.assertEqual(st["retryable_units"][0]["pending_model_requests"], 1)

    def test_uncertain_read_only_tool_is_retryable(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            j.append("tool_dispatch_started", "q1", 1, "t1", True)
            st = j.state()
            self.assertEqual(st["retryable_units"][0]["uncertain_replay_safe_tools"], 1)

    def test_any_nonreplayable_tool_blocks_incomplete_unit_restart(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            j.append("tool_dispatch_started", "q1", 1, "t1", False)
            j.append("tool_result_committed", "q1", 1, "t1")
            st = j.state()
            self.assertEqual(st["blocked_units"][0]["reasons"],
                             ["NONREPLAYABLE_TOOL_IN_INCOMPLETE_UNIT"])

    def test_journal_refuses_restart_after_nonreplayable_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            j.append("tool_dispatch_started", "q1", 1, "t1", False)
            j = c.Journal(Path(d, "run.jsonl"), "run-1", MANIFEST, fsync=False).open()
            with self.assertRaises(ValueError):
                j.append("unit_started", "q1", 2)

    def test_attempt_limit_blocks_crash_loop(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            j = c.Journal(Path(d, "run.jsonl"), "run-1", MANIFEST, fsync=False).open()
            j.append("unit_started", "q1", 2)
            st = j.state(max_attempts=2)
            self.assertEqual(st["blocked_units"][0]["reasons"], ["ATTEMPT_LIMIT"])

    def test_overlapping_attempt_without_resume_epoch_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            with self.assertRaises(ValueError):
                j.append("unit_started", "q1", 2)

    def test_run_complete_rejects_active_unit(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            with self.assertRaises(ValueError):
                j.append("run_completed")

    def test_duplicate_json_keys_are_committed_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            p = Path(d, "run.jsonl")
            with p.open("ab") as f:
                f.write(b'{"schema":"x","schema":"y"}\n')
            self.assertIn("CORRUPT_COMMITTED_LINE", c.scan(p).errors)

    def test_operation_commit_pairing(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("unit_started", "q1", 1)
            with self.assertRaises(ValueError):
                j.append("tool_result_committed", "q1", 1, "missing")
            j.append("tool_dispatch_started", "q1", 1, "t1", True)
            j.append("tool_result_committed", "q1", 1, "t1")
            with self.assertRaises(ValueError):
                j.append("tool_result_committed", "q1", 1, "t1")

    def test_run_complete_must_be_last(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            j.append("run_completed")
            with self.assertRaises(ValueError):
                j.append("unit_started", "q1", 1)

    def test_concurrent_appends_preserve_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            j = self.make(d)
            errors = []

            def worker(i):
                try:
                    j.append("unit_started", f"u{i}", 1)
                except Exception as exc:
                    errors.append(str(exc))

            ts = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(errors, [])
            s = c.scan(Path(d, "run.jsonl"))
            self.assertTrue(s.ok, s.errors)
            self.assertEqual([e["seq"] for e in s.events], list(range(1, 22)))


if __name__ == "__main__":
    unittest.main()
