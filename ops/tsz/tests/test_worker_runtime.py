"""Synthetic local-node tests. Never probes any real network or model."""
import importlib.util
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "worker_runtime.py"
spec = importlib.util.spec_from_file_location("worker_runtime", MODULE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
NOW = 1_800_000_000
CID = "neighbor-" + "a" * 24


def fleet(nodes=None):
    return {"nodes": nodes or {"laptop": {"candidate_id": CID, "roles": ["inventory", "engineering", "inference"], "approved_until": NOW+1800}}}


def heartbeat(node_id="laptop", *, age=0, roles=None, cores=4, memory=8192, inference=True):
    return {"schema": w.SCHEMA, "node_id": node_id, "candidate_id": CID,
            "recorded_at": NOW-age, "roles": roles or ["inventory", "engineering", "inference"],
            "cpu_cores": cores, "ram_available_mib": memory,
            "inference_runtime_ready": inference}


class WorkerTests(unittest.TestCase):
    def test_macos_vm_stat_memory_estimate(self):
        fixture = ("Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
                   "Pages free:                              65536.\n"
                   "Pages speculative:                        4096.\n"
                   "Pages inactive:                          300000.\n")
        self.assertEqual(w.parse_vm_stat(fixture), 1088)
        self.assertIsNone(w.parse_vm_stat("invalid"))
        from subprocess import CompletedProcess
        with patch.object(w.platform, "system", return_value="Darwin"), \
             patch.object(w.subprocess, "run", return_value=CompletedProcess(
                 args=["vm_stat"], returncode=0, stdout=fixture, stderr="")) as run:
            self.assertEqual(w.available_memory_mib(), 1088)
            self.assertEqual(run.call_args.args[0], ["vm_stat"])

    def test_worker_can_be_staged_and_heartbeat(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "worker"
            config = w.stage_local_worker(fleet(), "laptop", path, NOW)
            self.assertEqual(config["node_id"], "laptop")
            with patch.object(w, "available_memory_mib", return_value=1024):
                hb = w.emit_heartbeat(path, NOW)
            self.assertTrue(w.usable_heartbeat(fleet(), "laptop", hb, NOW))
            self.assertEqual((path/"heartbeat.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            self.assertFalse(hb["inference_runtime_ready"])

    def test_unapproved_stage_denied(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(w.WorkerError):
            w.stage_local_worker({"nodes": {}}, "new-device", Path(temp)/"new", NOW)

    def test_expired_stage_denied(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(w.WorkerError):
            w.stage_local_worker(fleet(), "laptop", Path(temp), NOW+3600)

    def test_binding_change_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"worker"
            w.stage_local_worker(fleet(), "laptop", path, NOW)
            changed = fleet({"laptop":{"candidate_id":"neighbor-"+"b"*24,
                       "roles":["inventory"], "approved_until":NOW+1800}})
            with self.assertRaises(w.WorkerError):
                w.stage_local_worker(changed, "laptop", path, NOW)

    def test_unknown_or_expired_heartbeat_denied(self):
        self.assertFalse(w.usable_heartbeat(fleet(), "another", heartbeat(), NOW))
        self.assertFalse(w.usable_heartbeat(fleet(), "laptop", heartbeat(age=91), NOW))
        self.assertFalse(w.usable_heartbeat(fleet(), "laptop", heartbeat(age=-1), NOW))
        self.assertFalse(w.usable_heartbeat(fleet(), "laptop", heartbeat(), NOW+3600))

    def test_unauthorized_roles_denied(self):
        self.assertFalse(w.usable_heartbeat(fleet(), "laptop", heartbeat(roles=["training"]), NOW))

    def test_place_job_is_plan_not_execution(self):
        jobs=[{"id":"job1","role":"engineering","cpu_cores":1,"memory_mib":128}]
        result = w.place_jobs(fleet(), {"laptop":heartbeat()}, jobs, NOW)
        self.assertEqual(result, [{"job_id":"job1","status":"PLANNED_ONLY","node_id":"laptop"}])

    def test_no_gpu_claim_without_proven_runtime(self):
        jobs=[{"id":"inference1","role":"inference","cpu_cores":1,"memory_mib":512}]
        result = w.place_jobs(fleet(), {"laptop":heartbeat(inference=False)}, jobs, NOW)
        self.assertEqual(result[0]["status"], "NO_ELIGIBLE_CAPACITY")

    def test_capacity_enforced(self):
        jobs=[{"id":f"j{i}","role":"engineering","cpu_cores":1,"memory_mib":1000} for i in range(5)]
        results = w.place_jobs(fleet(), {"laptop":heartbeat(cores=4,memory=2000)}, jobs, NOW)
        self.assertEqual([r["status"] for r in results].count("PLANNED_ONLY"),2)

    def test_revoke_removes_future_plans(self):
        result = w.place_jobs({"nodes":{}},{"laptop":heartbeat()},
                 [{"id":"j","role":"engineering","cpu_cores":1,"memory_mib":128}], NOW)
        self.assertEqual(result[0]["status"],"NO_ELIGIBLE_CAPACITY")

    def test_reject_invalid_job(self):
        for job in ({"id":"\t","role":"inventory","cpu_cores":1,"memory_mib":1},
                    {"id":"ok","role":"root","cpu_cores":1,"memory_mib":1},
                    {"id":"ok","role":"inventory","cpu_cores":0,"memory_mib":1},
                    {"id":"ok","role":"inventory","cpu_cores":1,"memory_mib":-1}):
            with self.subTest(job=job),self.assertRaises(w.WorkerError):
                w.place_jobs(fleet(), {"laptop":heartbeat()}, [job],NOW)

    def test_plan_jobs_cli_with_private_files(self):
        with tempfile.TemporaryDirectory() as temp:
            import json
            import sys
            path = Path(temp)
            fleet_path, job_path, observation_dir = path/"fleet.json",path/"jobs.json",path/"telemetry"
            observation_dir.mkdir(mode=0o700)
            fleet_path.write_text(json.dumps(fleet()))
            job_path.write_text(json.dumps({"jobs":[{"id":"i","role":"engineering", "cpu_cores":1, "memory_mib":128}]}))
            (observation_dir/"laptop.json").write_text(json.dumps(heartbeat()))
            for file in (fleet_path, job_path, observation_dir/"laptop.json"):
                file.chmod(0o600)
            with patch.object(w.time, "time", return_value=NOW), \
                 patch.object(sys, "argv", ["worker_runtime", "plan-jobs", "--fleet", str(fleet_path),
                      "--jobs", str(job_path), "--heartbeats-dir", str(observation_dir)]), \
                 patch("builtins.print") as output:
                w.main()
            self.assertIn("PLANNED_ONLY", output.call_args.args[0])

    def test_fairness_of_two_nodes(self):
        other={"candidate_id":"neighbor-"+"b"*24,"roles":["engineering"],"approved_until":NOW+1800}
        fl=fleet({"laptop":fleet()["nodes"]["laptop"],"other":other})
        hb2=heartbeat("other",roles=["engineering"], memory=8192)
        hb2["candidate_id"]=other["candidate_id"]
        jobs=[{"id":f"j{i}","role":"engineering","cpu_cores":1,"memory_mib":1} for i in range(2)]
        result=w.place_jobs(fl,{"laptop":heartbeat(),"other":hb2},jobs,NOW)
        self.assertEqual({r["node_id"] for r in result},{"laptop","other"})


if __name__ == "__main__":
    unittest.main()
