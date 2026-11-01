import _env  # noqa: F401  (must be first)

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from haven_hermes.simulated import FakeSlink, gpu
from haven_hermes import server
from haven_hermes.registry import ToolError


def build(slink=None, mode="operate", **kw):
    # A fresh surface state per build: rate limits persist across sessions by design.
    return server.build(mode, slink=slink or FakeSlink(), settings=kw.pop("settings", {}),
                        state=Path(tempfile.mkdtemp()), **kw)


class ModelTests(unittest.TestCase):
    def test_load_receipted_and_verified(self):
        fake = FakeSlink()
        reg = build(fake)
        out = reg.invoke("haven_model_use", {"model": "qwen35-4b", "context": 8192})
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["status"], "succeeded")
        self.assertRegex(out["receipt"], r"^R-[0-9a-f]{10}$")
        self.assertEqual(out["lab"]["job_id"], "job-load-1")
        self.assertIn("load", fake.actions())
        led = reg.invoke("haven_receipts")
        self.assertTrue(led["verified"])
        self.assertEqual(led["receipts"][-1]["status"], "succeeded")

    def test_peer_on_gpu_refuses_before_touching_the_lab(self):
        fake = FakeSlink(gpu_state=gpu(peers=["haven-cyber-qwythos.service"]))
        reg = build(fake)
        out = reg.invoke("haven_model_use", {"model": "qwen35-4b"})
        self.assertEqual((out["status"], out["error"]["code"]), ("refused", "gpu_busy"))
        self.assertEqual(out["error"]["detail"]["holders"], ["haven-cyber-qwythos.service"])
        self.assertNotIn("load", fake.actions())
        self.assertEqual(reg.receipts.ledger.get(out["receipt"])["status"], "refused")

    def test_busy_engine_needs_switch(self):
        fake = FakeSlink(gpu_state=gpu(lab=True), engine={"state": "READY", "ownership": "OWNED", "label": "old"})
        reg = build(fake)
        out = reg.invoke("haven_model_use", {"model": "qwen35-9b"})
        self.assertEqual(out["error"]["code"], "engine_busy")
        out = reg.invoke("haven_model_use", {"model": "qwen35-9b", "switch": True})
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["replaced"], "old")
        self.assertEqual(fake.actions()[-2:], ["unload", "load"])

    def test_bad_model_id_never_reaches_slink(self):
        fake = FakeSlink()
        out = build(fake).invoke("haven_model_use", {"model": "x; reboot"})
        self.assertEqual(out["error"]["code"], "invalid_input")
        self.assertEqual(fake.calls, [])

    def test_unload_disconnects_external_backend(self):
        fake = FakeSlink(connection={"ownership": "EXTERNAL", "model": "strata"})
        out = build(fake).invoke("haven_model_unload")
        self.assertEqual(out["action"], "disconnect")

    def test_timeout_is_unknown_not_retryable(self):
        fake = FakeSlink(fail={"unload": ToolError("timeout", "Slink did not answer")},
                         engine={"state": "READY", "ownership": "OWNED"})
        reg = build(fake)
        out = reg.invoke("haven_model_unload")
        self.assertEqual(out["status"], "unknown")
        self.assertNotIn("retryable", json.dumps(out))
        self.assertEqual(reg.receipts.ledger.get(out["receipt"])["status"], "unknown")

    def test_idempotent_replay_and_conflict(self):
        fake = FakeSlink()
        reg = build(fake)
        a = reg.invoke("haven_model_use", {"model": "qwen35-4b", "idempotency_key": "k-1"})
        fake.engine = {"state": "STOPPED", "ownership": "NONE"}
        b = reg.invoke("haven_model_use", {"model": "qwen35-4b", "idempotency_key": "k-1"})
        self.assertEqual(a["receipt"], b["receipt"])
        self.assertTrue(b["idempotent_replay"])
        self.assertEqual(fake.actions().count("load"), 1)
        c = reg.invoke("haven_model_use", {"model": "qwen35-9b", "idempotency_key": "k-1"})
        self.assertEqual(c["error"]["code"], "idempotency_conflict")


class StrataTests(unittest.TestCase):
    def test_needs_launch_flag_confirm_and_free_gpu(self):
        self.assertEqual(build().invoke("haven_strata_connect", {"confirm": "COLD_START_15MIN"})["error"]["code"],
                         "strata_disabled")
        reg = build(allow_strata=True)
        self.assertEqual(reg.invoke("haven_strata_connect", {"confirm": "yes"})["error"]["code"], "confirm_required")
        busy = build(FakeSlink(gpu_state=gpu(peers=["forge-teacher-server.service"])), allow_strata=True)
        self.assertEqual(busy.invoke("haven_strata_connect", {"confirm": "COLD_START_15MIN"})["error"]["code"],
                         "gpu_busy")
        out = reg.invoke("haven_strata_connect", {"confirm": "COLD_START_15MIN"})
        self.assertEqual(out["lab"]["job_id"], "job-strata-1")


class JobAndTaskTests(unittest.TestCase):
    def test_job_guards(self):
        reg = build()
        call = lambda **a: reg.invoke("haven_job_submit", {"command": "make test", "workspace": "demo", **a})
        self.assertEqual(call(node="local")["error"]["code"], "node_disabled")
        self.assertEqual(call(node="nope")["error"]["code"], "unknown_node")
        self.assertEqual(call(workspace="elsewhere")["error"]["code"], "unknown_workspace")
        self.assertEqual(call(network=True)["error"]["code"], "network_not_granted")

    def test_job_submit_and_cancel(self):
        import scheduler
        reg = build()
        with mock.patch.object(scheduler.Scheduler, "tick", lambda self: None):
            out = reg.invoke("haven_job_submit", {"command": "make test", "workspace": "demo"})
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["state"], "QUEUED")
        self.assertTrue(out["job_id"].startswith("hermes-"))
        self.assertEqual(reg.invoke("haven_jobs", {"id": out["job_id"]})["job"]["spec"]["node"], "slink")
        self.assertEqual(reg.invoke("haven_job_cancel", {"id": out["job_id"]})["state"], "CANCELLED")

    def test_task_agent_allowlist_and_cancel(self):
        out = build().invoke("haven_task_start", {"prompt": "fix it", "agent": "qwen35-4b-mac", "workspace": "demo"})
        self.assertEqual(out["error"]["code"], "agent_not_allowed")
        tdir = _env.STATE / "tasks" / "20261031T000000-abcdef"
        tdir.mkdir(parents=True)
        (tdir / "meta.json").write_text(json.dumps({"task_id": tdir.name, "status": "running"}))
        self.assertTrue(build().invoke("haven_task_cancel", {"task_id": tdir.name})["cancel_requested"])
        self.assertTrue((tdir / "cancel").exists())


class ReceiptTests(unittest.TestCase):
    def test_check_answer_and_tamper(self):
        reg = build()
        out = reg.invoke("haven_model_use", {"model": "qwen35-4b"})
        rid = out["receipt"]
        ok = reg.invoke("haven_check_answer", {"text": f"Started loading qwen35-4b ({rid})."})
        self.assertTrue(ok["ok"], ok)
        forged = reg.invoke("haven_check_answer", {"text": "Done, see R-0123456789."})
        self.assertEqual(forged["forged"], ["R-0123456789"])
        path = reg.receipts.ledger.path
        lines = path.read_text().splitlines()
        lines[0] = lines[0].replace('"agent":"hermes"', '"agent":"someone"')
        path.write_text("\n".join(lines) + "\n")
        tid = reg.receipts.task_id
        self.assertFalse(build().invoke("haven_receipts", {"task_id": tid})["verified"])

    def test_read_only_session_leaves_no_task(self):
        before = set((_env.STATE / "tasks").glob("*")) if (_env.STATE / "tasks").exists() else set()
        reg = build(mode="observe")
        reg.invoke("haven_status")
        reg.invoke("haven_gpu")
        after = set((_env.STATE / "tasks").glob("*")) if (_env.STATE / "tasks").exists() else set()
        self.assertEqual(before, after)
        self.assertIsNone(reg.receipts.task_id)


if __name__ == "__main__":
    unittest.main()
