import hashlib
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import checkpoint_journal as c

MANIFEST = hashlib.sha256(b"process-matrix-manifest").hexdigest()
RESULT = hashlib.sha256(b'{"case":"q1","semantic_pass":true}').hexdigest()
MODEL_IN = hashlib.sha256(b"prompt").hexdigest()
MODEL_OUT = hashlib.sha256(b"answer").hexdigest()
TOOL_OUT = hashlib.sha256(b"tool-result").hexdigest()

CHILD = r"""
import sys,time
from pathlib import Path
import checkpoint_journal as c

path=Path(sys.argv[1])
marker=Path(sys.argv[2])
sentinel=Path(sys.argv[3])
boundary=sys.argv[4]
resume=sys.argv[5]=="1"
attempt=int(sys.argv[6])
manifest=sys.argv[7]
model_in=sys.argv[8]
model_out=sys.argv[9]
tool_out=sys.argv[10]
result_hash=sys.argv[11]

j=c.Journal(path,"run-1",manifest,fsync=True)
with j.owned(resume=resume):
    j.append("unit_started","q1",attempt)
    if boundary in ("model_request","model_response","before_tool","tool_dispatch","tool_result","before_complete"):
        j.append("model_request_started","q1",attempt,f"m{attempt}",True,model_in)
    if boundary in ("model_response","before_tool","tool_dispatch","tool_result","before_complete"):
        j.append("model_response_committed","q1",attempt,f"m{attempt}",False,model_out)
    if boundary in ("tool_dispatch","tool_result","before_complete"):
        j.append("tool_dispatch_started","q1",attempt,f"t{attempt}",True)
    if boundary in ("tool_result","before_complete"):
        j.append("tool_result_committed","q1",attempt,f"t{attempt}",False,tool_out)
    if boundary=="nonreplay":
        j.append("tool_dispatch_started","q1",attempt,f"unsafe{attempt}",False)
        with sentinel.open("a") as f:
            f.write("x")
            f.flush()
    if boundary=="completed":
        j.append("unit_completed","q1",attempt,payload_sha256=result_hash)
    marker.write_text("durable")
    time.sleep(60)
"""


@unittest.skipIf(c._fcntl is None, "POSIX flock required")
class ProcessInterruptionMatrix(unittest.TestCase):
    def start_worker(self, root, boundary, *, resume=False, attempt=1):
        root = Path(root)
        marker = root / f"marker-{boundary}-{attempt}"
        sentinel = root / "unsafe-canary"
        proc = subprocess.Popen(
            [
                sys.executable, "-c", CHILD,
                str(root / "run.jsonl"), str(marker), str(sentinel), boundary,
                "1" if resume else "0", str(attempt), MANIFEST,
                MODEL_IN, MODEL_OUT, TOOL_OUT, RESULT,
            ],
            cwd=Path(c.__file__).parent,
        )
        deadline = time.time() + 8
        while time.time() < deadline and not marker.exists() and proc.poll() is None:
            time.sleep(0.02)
        self.assertTrue(marker.exists(), f"worker exited={proc.poll()} before {boundary} marker")
        return proc, sentinel

    def kill(self, proc):
        proc.kill()  # SIGKILL on POSIX: no Python cleanup path.
        proc.wait(timeout=5)
        self.assertNotEqual(proc.returncode, 0)

    def recover_and_complete(self, root):
        path = Path(root) / "run.jsonl"
        j = c.Journal(path, "run-1", MANIFEST, fsync=True)
        with j.owned(resume=True):
            plan = j.state(max_attempts=3)
            self.assertEqual(plan["retryable_units"][0]["unit"], "q1")
            self.assertEqual(plan["retryable_units"][0]["next_attempt"], 2)
            j.append("unit_started", "q1", 2)
            j.append("unit_completed", "q1", 2, payload_sha256=RESULT)
        scan = c.scan(path)
        self.assertTrue(scan.ok, scan.errors)
        completed = [e for e in scan.events if e["event"] == "unit_completed"]
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["payload_sha256"], RESULT)
        return scan

    def test_retryable_sigkill_boundaries_recover_to_same_result_hash(self):
        boundaries = [
            "model_request",
            "model_response",
            "before_tool",
            "tool_dispatch",
            "tool_result",
            "before_complete",
        ]
        for boundary in boundaries:
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as d:
                proc, _ = self.start_worker(d, boundary)
                self.kill(proc)
                pre = c.scan(Path(d) / "run.jsonl")
                self.assertTrue(pre.ok, pre.errors)
                self.assertEqual(c.resume_plan(pre.events)["retryable_units"][0]["unit"], "q1")
                final = self.recover_and_complete(d)
                self.assertEqual(
                    [e["attempt"] for e in final.events if e["event"] == "unit_started"],
                    [1, 2],
                )

    def test_nonreplayable_sigkill_blocks_restart_and_never_replays_canary(self):
        with tempfile.TemporaryDirectory() as d:
            proc, sentinel = self.start_worker(d, "nonreplay")
            self.kill(proc)
            self.assertEqual(sentinel.read_text(), "x")
            path = Path(d) / "run.jsonl"
            plan = c.resume_plan(c.scan(path).events)
            self.assertEqual(
                plan["blocked_units"][0]["reasons"],
                ["NONREPLAYABLE_TOOL_IN_INCOMPLETE_UNIT"],
            )
            j = c.Journal(path, "run-1", MANIFEST, fsync=True)
            with j.owned(resume=True):
                with self.assertRaises(ValueError):
                    j.append("unit_started", "q1", 2)
            self.assertEqual(sentinel.read_text(), "x")

    def test_completed_unit_is_skipped_after_process_death(self):
        with tempfile.TemporaryDirectory() as d:
            proc, _ = self.start_worker(d, "completed")
            self.kill(proc)
            path = Path(d) / "run.jsonl"
            j = c.Journal(path, "run-1", MANIFEST, fsync=True)
            with j.owned(resume=True):
                plan = j.state()
                self.assertEqual(plan["completed_units"], ["q1"])
                self.assertEqual(plan["retryable_units"], [])
            scan = c.scan(path)
            self.assertEqual(
                len([e for e in scan.events if e["event"] == "unit_started"]),
                1,
            )
            self.assertEqual(
                [e["payload_sha256"] for e in scan.events if e["event"] == "unit_completed"],
                [RESULT],
            )

    def test_attempt_cap_stops_repeated_crash_loop(self):
        with tempfile.TemporaryDirectory() as d:
            first, _ = self.start_worker(d, "model_request", attempt=1)
            self.kill(first)
            second, _ = self.start_worker(d, "model_request", resume=True, attempt=2)
            self.kill(second)
            path = Path(d) / "run.jsonl"
            plan = c.resume_plan(c.scan(path).events, max_attempts=2)
            self.assertEqual(plan["retryable_units"], [])
            self.assertEqual(plan["blocked_units"][0]["reasons"], ["ATTEMPT_LIMIT"])

    def test_live_competing_owner_cannot_establish_resume_epoch(self):
        with tempfile.TemporaryDirectory() as d:
            proc, _ = self.start_worker(d, "model_request")
            try:
                path = Path(d) / "run.jsonl"
                j = c.Journal(path, "run-1", MANIFEST, fsync=True)
                with self.assertRaisesRegex(RuntimeError, "live owner"):
                    with j.owned(resume=True):
                        pass
                events = c.scan(path).events
                self.assertEqual([e["event"] for e in events].count("run_resumed"), 0)
            finally:
                self.kill(proc)


if __name__ == "__main__":
    unittest.main()
