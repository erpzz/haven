"""Development regression tests; neither independent QA nor final suite starts."""
import asyncio
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import time
import uuid

import pytest

from haven import supervisor as rt
from haven.model_adapter import ModelAdapter, ModelLease

FIXTURE = Path(__file__).with_name("fixture_worker.py").resolve()
ROOT = Path(__file__).resolve().parents[4]


def job(milliseconds=10000, route="deterministic"):
    return {"job_id": uuid.uuid4().hex, "request_id": uuid.uuid4().hex,
            "request_digest": rt.digest({"question": "Synthetic color?"}),
            "attempt_id": uuid.uuid4().hex, "lease_fence": 1, "cancel_epoch": 1,
            "route": route, "deadline_utc": (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
            "max_elapsed_ms": milliseconds, "reservation_id": uuid.uuid4().hex}


class Callbacks:
    def __init__(self):
        self.jobs, self.events, self.results = {}, [], []
        self.decision = "ADMITTED"
        self.hold = None

    async def admit(self, job_id, attempt_id, fence):
        if self.hold:
            await self.hold.wait()
        return {"decision": self.decision,
                "context": {"question": "Synthetic color?", "sources": [{"id": "s1", "revision": 1,
                             "title": "Synthetic card", "text": "The square is blue."}]},
                "authority_vector": {"lease_fence": fence}, "job": self.jobs[job_id],
                "limits": {}, "model_identity": None}

    async def event(self, value):
        self.events.append(value)

    async def result(self, value):
        self.results.append(value)
        return {"disposition": "FENCED"}


async def wait_done(s, j, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if s.queue._unfinished_tasks == 0:
            return await s.snapshot(j["job_id"])
        await asyncio.sleep(0.01)
    raise AssertionError("fixed test completion bound exceeded")


def factory(tmp_path):
    callbacks = Callbacks()
    supervisor = rt.Supervisor(runtime_dir=tmp_path, admit_attempt=callbacks.admit,
                               on_event=callbacks.event, on_result=callbacks.result)
    return supervisor, callbacks


def fixture_process(monkeypatch, mode):
    original = rt.OwnedProcess
    def replacement(owned, argv, **kwargs):
        return original(owned, [sys._base_executable, "-I", "-B", str(FIXTURE), mode], **kwargs)
    monkeypatch.setattr(rt, "OwnedProcess", replacement)


def test_benign_owned_process_and_control(tmp_path):
    async def run():
        workload, control = rt.OwnedJob(), rt.OwnedJob()
        started = time.monotonic()
        worker = rt.OwnedProcess(workload, [sys._base_executable, "-I", "-B", str(FIXTURE), "tree"],
                                 env=rt.private_environment(tmp_path), cwd=tmp_path)
        survivor = rt.OwnedProcess(control, [sys._base_executable, "-I", "-B", str(FIXTURE), "sleeper"],
                                   env=rt.private_environment(tmp_path), cwd=tmp_path)
        child = await asyncio.to_thread(worker.stdout.readline)
        assert json.loads(child)["child_pid"] in workload.observation()["pids"]
        before = workload.observation()
        stop_start = time.monotonic()
        stopped = await workload.stop()
        elapsed = time.monotonic() - stop_start
        assert stopped["confirmed"] and survivor.poll() is None
        probe = {"kind": "BENIGN_PROBE", "before": before, "after": stopped,
                 "stop_elapsed_seconds": elapsed, "control_alive": survivor.poll() is None,
                 "fixed_stop_target_seconds": rt.STOP_TARGET_SECONDS}
        (tmp_path / "probe.json").write_bytes(rt.canonical(probe))
        assert (await control.stop())["confirmed"]
        worker.close(); survivor.close(); workload.close(); control.close()
    asyncio.run(run())


def test_actual_worker_result_and_fenced_release_independent_of_stop(tmp_path):
    async def run():
        s, c = factory(tmp_path)
        await s.start()
        j = job(); c.jobs[j["job_id"]] = j
        await s.submit(j)
        status = await wait_done(s, j)
        assert status["compute_state"] == "STOP_CONFIRMED"
        assert status["disposition"] == "FAILED"
        assert len(c.results) == 1
        result = c.results[0]
        assert result["request_digest"] == j["request_digest"]
        assert result["pid"] and result["process_birth"] and result["boot_id"] and result["nonce"]
        assert result["output_digest"] == rt.digest(result["payload"])
        assert "blue" in result["payload"]["text"]
        assert (await s.submit(j))["identity"] == status["identity"]
        different = {**j, "lease_fence": 2}
        with pytest.raises(ValueError):
            await s.submit(different)
        # A duplicate/delayed result cannot call authority twice.
        candidate = {"identity": status["identity"], **{k: result[k] for k in
                     ("request_digest", "context_digest", "output_digest", "payload", "source_refs", "model_identity",
                      "outcome", "usage", "certainty")}}
        assert (await s._accept_candidate(s.jobs[j["job_id"]], candidate))["disposition"] == "FENCED"
        assert len(c.results) == 1
        broken = {**candidate, "outcome": "UNSUPPORTED"}
        assert (await s._accept_candidate(s.jobs[j["job_id"]], broken))["disposition"] == "REJECTED"
        assert len(c.results) == 1
        assert (await s.snapshot(j["job_id"]))["disposition"] == "FAILED"
        assert (await s.close(time.monotonic()+3))["confirmed"]
    asyncio.run(run())


def test_cancel_during_admission_never_starts(tmp_path):
    async def run():
        s, c = factory(tmp_path); c.hold = asyncio.Event()
        await s.start(); j = job(); c.jobs[j["job_id"]] = j
        await s.submit(j); await asyncio.sleep(0.03)
        await s.cancel(j["job_id"], 2, "synthetic cancel")
        c.hold.set()
        status = await wait_done(s, j)
        assert status["compute_state"] == "NOT_STARTED" and status["identity"]["pid"] is None
        assert not c.results
        assert (await s.close(time.monotonic()+3))["confirmed"]
    asyncio.run(run())


@pytest.mark.parametrize("decision", ["DENIED", "UNKNOWN"])
def test_admission_denial(tmp_path, decision):
    async def run():
        s, c = factory(tmp_path); c.decision = decision
        await s.start(); j=job(); c.jobs[j["job_id"]]=j
        await s.submit(j); state=await wait_done(s,j)
        assert state["compute_state"] == "NOT_STARTED" and not c.results
        await s.close(time.monotonic()+3)
    asyncio.run(run())


@pytest.mark.parametrize("mode", ["crash", "malformed", "stale", "bad_hash", "hang", "delay"])
def test_faults_no_release_stop_and_capacity(tmp_path, monkeypatch, mode):
    fixture_process(monkeypatch, mode)
    async def run():
        s,c=factory(tmp_path); await s.start()
        j=job(100 if mode in ("hang", "delay") else 10000); c.jobs[j["job_id"]]=j
        await s.submit(j); state=await wait_done(s,j)
        assert state["compute_state"] == "STOP_CONFIRMED"
        assert not state["capacity_held"] and not c.results
        assert state["disposition"] in ("FAILED", "INCONCLUSIVE")
        await s.close(time.monotonic()+3)
    asyncio.run(run())


def test_cancel_running_and_stale_cancel(tmp_path, monkeypatch):
    fixture_process(monkeypatch, "hang")
    async def run():
        s,c=factory(tmp_path); await s.start(); j=job(); c.jobs[j["job_id"]]=j
        await s.submit(j)
        for _ in range(300):
            if (await s.snapshot(j["job_id"]))["compute_state"] == "RUNNING": break
            await asyncio.sleep(.01)
        assert (await s.cancel(j["job_id"],0,"stale"))["compute_state"] == "RUNNING"
        await s.cancel(j["job_id"],2,"current")
        state=await wait_done(s,j)
        assert state["compute_state"] == "STOP_CONFIRMED" and not c.results
        assert state["disposition"] == "CANCELLED"
        await s.close(time.monotonic()+3)
    asyncio.run(run())


def test_parent_death_job_cleanup_and_control_survival(tmp_path):
    async def run():
        parent_job, control_job = rt.OwnedJob(), rt.OwnedJob()
        parent = rt.OwnedProcess(parent_job, [sys._base_executable,"-I","-B",str(FIXTURE),"parent",str(tmp_path)],
                                 env=rt.private_environment(tmp_path),cwd=tmp_path)
        control = rt.OwnedProcess(control_job,[sys._base_executable,"-I","-B",str(FIXTURE),"sleeper"],
                                  env=rt.private_environment(tmp_path),cwd=tmp_path)
        ready=tmp_path/"parent-ready.json"
        for _ in range(500):
            if ready.exists(): break
            await asyncio.sleep(.01)
        record=json.loads(ready.read_text())
        assert rt.identity_alive(record["worker"])
        # Kill only the exact parent's retained handle, NOT its containing job.
        terminate=rt._api("TerminateProcess",[rt.W.HANDLE,rt.W.UINT])
        rt._check(terminate(parent.handle, 0xE002))
        deadline=time.monotonic()+rt.STOP_TARGET_SECONDS
        while time.monotonic()<deadline and parent_job.observation()["active_processes"]:
            await asyncio.sleep(.01)
        observed=parent_job.observation()
        assert observed["active_processes"] == 0
        assert not rt.identity_alive(record["worker"])
        assert control.poll() is None
        (tmp_path/"parent-death-observed.json").write_bytes(rt.canonical({"before":record,"after":observed,
                                                                        "control_alive":True}))
        assert (await control_job.stop())["confirmed"]
        parent.close();control.close();parent_job.close();control_job.close()
    asyncio.run(run())


def test_restart_rejects_old_job_and_live_predecessor(tmp_path):
    async def run():
        first,c=factory(tmp_path);await first.start(); j=job();c.jobs[j["job_id"]]=j
        await first.submit(j);await wait_done(first,j)
        second,_=factory(tmp_path);await second.start()
        assert second.quarantined
        await second.close(time.monotonic()+3)
        await first.close(time.monotonic()+3)
        third,_=factory(tmp_path);await third.start()
        # An unconfirmed live predecessor intentionally keeps quarantine.
        with pytest.raises(RuntimeError): await third.submit(j)
        await third.close(time.monotonic()+3)
    asyncio.run(run())


def test_bounded_ipc_and_clean_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_SECRET_CREDENTIAL", "do-not-propagate")
    env=rt.private_environment(tmp_path)
    assert "TEST_SECRET_CREDENTIAL" not in env
    assert "HTTP_PROXY" not in env and "PYTHONPATH" not in env
    assert str(tmp_path) in env["TMP"] and str(tmp_path) in env["USERPROFILE"]
    with pytest.raises(ValueError): rt.read_frame(io.BytesIO(b"\xff\xff\xff\xff"))
    with pytest.raises(ValueError): rt.strict_json(b'{"a":1,"a":2}')
    with pytest.raises(ValueError): rt.canonical({"bad":float("nan")})


def test_model_gate_absent_is_closed(tmp_path):
    c=Callbacks();j=job(route="model");c.jobs[j["job_id"]]=j
    admitted=asyncio.run(c.admit(j["job_id"],j["attempt_id"],1))
    with pytest.raises(FileNotFoundError): ModelLease(tmp_path,admitted)
    assert not (tmp_path/"model"/"model-calls.jsonl").exists()


def test_unknown_observer_retains_capacity(tmp_path, monkeypatch):
    real_stop=rt.OwnedJob.stop
    async def observer_unavailable(self,deadline=None):
        evidence=await real_stop(self,deadline)
        return {**evidence,"confirmed":False,"observer_injected":"UNKNOWN"}
    monkeypatch.setattr(rt.OwnedJob,"stop",observer_unavailable)
    async def run():
        s,c=factory(tmp_path);await s.start();j=job();c.jobs[j["job_id"]]=j
        await s.submit(j);state=await wait_done(s,j)
        assert state["compute_state"]=="UNKNOWN" and state["capacity_held"]
        assert s.quarantined and not c.results
        with pytest.raises(RuntimeError):await s.submit(job())
        assert not (await s.close(time.monotonic()+3))["confirmed"]
        owned=s.jobs[j["job_id"]]["owned_job"]
        assert (await real_stop(owned))["confirmed"]
        for p in owned.processes:p.close()
        owned.close()
    asyncio.run(run())


def test_clean_restart_new_job_and_prior_job_fence(tmp_path):
    async def run():
        first,c=factory(tmp_path);await first.start();old=job();c.jobs[old["job_id"]]=old
        await first.submit(old);await wait_done(first,old)
        assert (await first.close(time.monotonic()+3))["confirmed"]
        second,d=factory(tmp_path);await second.start()
        assert not second.quarantined
        with pytest.raises(RuntimeError):await second.submit(old)
        fresh=job();d.jobs[fresh["job_id"]]=fresh
        await second.submit(fresh)
        state=await wait_done(second,fresh)
        assert state["compute_state"]=="STOP_CONFIRMED" and len(d.results)==1
        assert (await second.close(time.monotonic()+3))["confirmed"]
    asyncio.run(run())
