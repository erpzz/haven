"""Trust gate (TSZ approvals -> Haven), node worker, and the durable scheduler.

Runs the real worker.py under this host's sandbox; no network, no SSH, no model.
"""
import json
import os
import pathlib
import shutil
import signal
import sys
import tempfile
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
TMP = tempfile.mkdtemp(prefix="haven-sched-test-")
os.environ["HAVEN_ENGINEER_STATE"] = os.path.join(TMP, "state")
os.environ["HAVEN_ENGINEER_CONFIG"] = os.path.join(TMP, "config")
os.environ["HAVEN_WORKER_STATE"] = os.path.join(TMP, "worker")
os.environ["HAVEN_WORKER_CACHE"] = os.path.join(TMP, "wcache")
sys.path.insert(0, str(HERE))

import scheduler  # noqa: E402
import trust  # noqa: E402
import worker  # noqa: E402

tsz = trust._tsz()
NOW = 1_800_000_000
SLINK = {"name": "slink", "kind": "ssh", "ssh": "haven", "roles": ["tools", "inference-gpu"],
         "host_fingerprint": "SHA256:abc", "address": "192.168.1.20", "tsz_node_id": "slink-node"}
LOCAL = {"name": "local", "kind": "local", "roles": ["tools", "inference"], "trust": "LOCAL_HOST"}


def tsz_state(roles=("engineering",), expires=NOW + 3600, address="192.168.1.20"):
    """Build TSZ state exactly as `fleet.py discover` + `sync-approved` would."""
    state = tsz.empty_state()
    obs = tsz.observation(address, "aa:bb:cc:dd:ee:ff", "en0", "test")
    tsz.update_candidates(state, [obs], NOW - 10)
    export = {"schema": tsz.DECISION_SCHEMA, "expires_at": expires,
              "nodes": [{"node_id": "slink-node", "candidate_id": obs["candidate_id"], "roles": list(roles)}]}
    tsz.reconcile_approved(state, export, NOW)
    return state


class TrustGateTest(unittest.TestCase):
    def gate(self, state, now=NOW):
        return trust.Gate({"source": "tsz"}, tsz_state=state, now=now)

    def test_approved_bound_node_is_eligible(self):
        d = self.gate(tsz_state()).decide(SLINK, "tools")
        self.assertTrue(d["ok"], d)
        self.assertEqual(d["tsz_node_id"], "slink-node")

    def test_denials(self):
        st = tsz_state()
        cases = {
            "unbound": ({**SLINK, "tsz_node_id": None}, "tools", st, NOW),
            "role not in approval": (SLINK, "inference-gpu", st, NOW),
            "role not enrolled": (SLINK, "inference-cpu", st, NOW),
            "expired": (SLINK, "tools", st, NOW + 7200),
            "no pinned key": ({**SLINK, "host_fingerprint": None}, "tools", st, NOW),
            "binding contradicts address": ({**SLINK, "address": "192.168.1.99"}, "tools", st, NOW),
        }
        for label, (node, role, state, now) in cases.items():
            self.assertFalse(self.gate(state, now).decide(node, role)["ok"], label)

    def test_revocation_is_snapshot_replacement(self):
        state = tsz_state()
        tsz.reconcile_approved(state, {"schema": tsz.DECISION_SCHEMA, "expires_at": NOW + 60, "nodes": []}, NOW)
        d = self.gate(state).decide(SLINK, "tools")
        self.assertFalse(d["ok"])
        self.assertIn("absent or revoked", d["reason"])

    def test_unreadable_state_fails_closed(self):
        d = trust.Gate({"source": "tsz", "tsz_state_dir": os.path.join(TMP, "nope", "x")}).decide(SLINK, "tools")
        bad = pathlib.Path(TMP, "badtsz")
        bad.mkdir(mode=0o700)
        (bad / "inventory.json").write_text("{}")
        os.chmod(bad / "inventory.json", 0o600)
        d2 = trust.Gate({"source": "tsz", "tsz_state_dir": str(bad)}).decide(SLINK, "tools")
        self.assertFalse(d2["ok"])
        self.assertIn("unreadable", d2["reason"])
        # An absent state dir is an empty (no approvals) state, which also denies.
        self.assertFalse(d["ok"])

    def test_enrollment_only_source_is_labelled(self):
        d = trust.Gate({"source": "enrollment"}).decide(SLINK, "tools")
        self.assertTrue(d["ok"])
        self.assertEqual(d["source"], "enrollment")


class FixedGate:
    def __init__(self, ok=True):
        self.ok = ok

    def decide(self, node, role):
        return {"ok": self.ok, "source": "test", "reason": "test approval" if self.ok else "revoked by test"}


def wait_for(pred, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.1)
    return False


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        # Worker workspaces must sit inside $HOME. Inside a sandbox, only its temp dir is writable.
        home, tmp = pathlib.Path.home().resolve(), pathlib.Path(tempfile.gettempdir()).resolve()
        base = tmp if home in tmp.parents else home / ".cache" / "haven-engineer"
        base.mkdir(parents=True, exist_ok=True)
        self.ws = pathlib.Path(tempfile.mkdtemp(prefix="sched-test-", dir=base))
        self.addCleanup(shutil.rmtree, self.ws, True)
        self.gate = FixedGate()
        self.obs = {"local": {"status": "ONLINE", "observed_at": time.time(), "cores": 8, "load": [1.0],
                              "mem_avail": 8 * 1024 ** 3}}
        root = pathlib.Path(TMP) / f"sched-{id(self)}"
        self.sch = scheduler.Scheduler(scheduler.Store(root), nodes=lambda: [LOCAL],
                                       observe=lambda: {k: {**v, "observed_at": time.time()} for k, v in self.obs.items()},
                                       gate=lambda: self.gate)

    def submit(self, command, **kw):
        return self.sch.submit({"command": command, "workspace": str(self.ws), "cpu": 1, "mem_mib": 64,
                                "timeout_s": 30, **kw})

    def settle(self, jid, states):
        return wait_for(lambda: (self.sch.tick(), self.sch.store.load(jid)["state"])[1] in states, 15)

    def test_lifecycle_and_receipt(self):
        job = self.submit("echo built > artifact.txt && echo ok")
        self.assertTrue(self.settle(job["id"], {"SUCCEEDED"}), self.sch.store.load(job["id"]))
        done = self.sch.store.load(job["id"])
        self.assertEqual((self.ws / "artifact.txt").read_text().strip(), "built")
        self.assertIn("ok", done["output_tail"])
        rec = self.sch.store.ledger.get(done["receipt"])
        self.assertEqual(rec["status"], "succeeded")
        self.assertEqual(rec["exit_code"], 0)
        self.assertTrue(self.sch.store.ledger.verify())
        events = [h["event"] for h in done["history"]]
        self.assertEqual(events[:3], ["submitted", "placed", "running"])

    def test_failure_is_failed(self):
        job = self.submit("exit 3")
        self.assertTrue(self.settle(job["id"], {"FAILED"}))
        self.assertEqual(self.sch.store.ledger.get(job["receipt"])["exit_code"], 3)

    def test_cancel_running(self):
        job = self.submit("sleep 30")
        self.assertTrue(self.settle(job["id"], {"RUNNING"}))
        self.sch.cancel(job["id"])
        self.assertTrue(self.settle(job["id"], {"CANCELLED"}))
        self.assertEqual(self.sch.store.ledger.get(job["receipt"])["status"], "failed")

    def test_trust_revocation_cancels_running_and_blocks_new(self):
        job = self.submit("sleep 30")
        self.assertTrue(self.settle(job["id"], {"RUNNING"}))
        self.gate = FixedGate(ok=False)
        self.assertTrue(self.settle(job["id"], {"CANCELLED"}))
        self.assertIn("revoked", self.sch.store.load(job["id"])["revoked"])
        second = self.submit("echo never")
        self.sch.tick()
        held = self.sch.store.load(second["id"])
        self.assertEqual(held["state"], "QUEUED")
        self.assertEqual(held["waiting"], {"local": "revoked by test"})
        self.assertEqual(self.sch.store.ledger.get(second["receipt"])["status"], "proposed")

    def test_headroom_and_stale_telemetry(self):
        self.obs["local"]["cores"] = 1  # load 1.0 leaves no core free
        job = self.submit("echo x")
        self.sch.tick()
        self.assertIn("no headroom", self.sch.store.load(job["id"])["waiting"]["local"])
        self.obs["local"]["status"] = "OFFLINE"
        self.sch.tick()
        self.assertEqual(self.sch.store.load(job["id"])["state"], "QUEUED")

    def test_crash_before_start_requeues_and_lost_runner_is_unknown(self):
        job = self.submit("echo hi")
        # Simulate a controller crash after "placed" was persisted but before the worker got the job.
        j = self.sch.store.load(job["id"])
        j.update(state="STARTING", node="local", node_workspace=str(self.ws))
        self.sch.store.ledger.transition(j["receipt"], "authorized", decided_by="trust:test")
        self.sch.store.save(j)
        self.sch.tick()  # worker says ABSENT -> requeued; then placed and started on the same tick
        self.assertTrue(self.settle(job["id"], {"SUCCEEDED"}))
        self.assertIn("requeued", [h["event"] for h in self.sch.store.load(job["id"])["history"]])
        # A runner killed with no exit record is LOST and its receipt unknown, never success.
        job2 = self.submit("sleep 30")
        self.assertTrue(self.settle(job2["id"], {"RUNNING"}))
        rpath = pathlib.Path(os.environ["HAVEN_WORKER_STATE"]) / "jobs" / job2["id"] / "runner.json"
        self.assertTrue(wait_for(lambda: "child_pid" in json.loads(rpath.read_text())))
        runner = json.loads(rpath.read_text())
        os.killpg(runner["child_pid"], signal.SIGKILL)
        os.kill(runner["pid"], signal.SIGKILL)
        self.assertTrue(self.settle(job2["id"], {"LOST"}))
        self.assertEqual(self.sch.store.ledger.get(job2["receipt"])["status"], "unknown")

    def test_worker_start_is_at_most_once(self):
        spec = {"command": "echo once >> count.txt", "workspace": str(self.ws), "timeout_s": 10}
        worker.start("once-1", spec)
        again = worker.start("once-1", spec)
        self.assertTrue(again["already_started"])
        self.assertTrue(wait_for(lambda: worker.status("once-1")["state"] == "SUCCEEDED"))
        self.assertEqual((self.ws / "count.txt").read_text(), "once\n")

    def test_rejects_gpu_and_bad_specs(self):
        for bad in ({"gpu": True}, {"cpu": 0}, {"workspace": None}, {"role": "training"}):
            with self.assertRaises(scheduler.SchedError, msg=str(bad)):
                self.sch.submit({"command": "x", "workspace": str(self.ws), "cpu": 1, "mem_mib": 64,
                                 "timeout_s": 5, **bad})


if __name__ == "__main__":
    unittest.main()
