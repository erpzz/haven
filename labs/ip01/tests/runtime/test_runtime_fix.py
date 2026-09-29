"""Assignment14 development barriers. Mocked authority/model transport; no inference."""
import asyncio
import io
import time
import uuid
import json

import pytest

from haven import supervisor as rt
from haven.model_adapter import ModelAdapter, ModelLease, check_handoff
from test_runtime import job, factory, wait_done, fixture_process
from test_model_gate import setup_gate


def authorized(j, context, vector, gate=None):
    now = time.time()
    return dict(decision="AUTHORIZED", reason="OK", job_id=j["job_id"], attempt_id=j["attempt_id"],
                lease_fence=j["lease_fence"], cancel_epoch=j["cancel_epoch"], context_digest=rt.context_digest(context),
                decision_id=uuid.uuid4().hex, checked_at=now, valid_until=now+1,
                authority_vector_digest=rt.digest(vector), model_gate_sha256=gate)


@pytest.mark.parametrize("mode", ["positive", "denied", "unknown", "exception", "timeout", "job_id", "attempt_id",
    "lease_fence", "cancel_epoch", "context_digest", "authority_vector_digest", "model_gate_sha256", "malformed",
    "expired", "cancel", "deadline"])
def test_actual_idle_owned_worker_fresh_barrier(tmp_path, monkeypatch, mode):
    fixture_process(monkeypatch,"mock-model-transport")
    async def fake_prepare(self,owned,admitted,deadline,cancel):
        return {"mocked_no_network":True}
    monkeypatch.setattr(ModelAdapter,"start_for_attempt",fake_prepare)
    async def run():
        s,c=factory(tmp_path)
        original_admit=c.admit
        async def admission(*args):
            admitted=await original_admit(*args)
            admitted["limits"]["model_gate_sha256"]="a"*64
            return admitted
        s.admit_attempt=admission
        calls=[]
        async def egress(jid, aid, fence, ctx):
            calls.append((jid, aid, fence, ctx))
            assert c.events[-1]["kind"] == "PROCESS_STARTED"
            assert s.jobs[jid]["process"].poll() is None
            admitted=await c.admit(jid,aid,fence)
            response=authorized(j,admitted["context"],admitted["authority_vector"],"a"*64)
            if mode in ("denied", "unknown"): response["decision"]=mode.upper()
            if mode == "exception": raise RuntimeError("mock transaction unavailable")
            if mode == "timeout": await asyncio.sleep(3)
            if mode == "malformed": return {}
            if mode == "expired": response["valid_until"]=time.time()-1
            if mode == "cancel": await s.cancel(jid,2,"mock barrier cancel")
            if mode == "deadline": s.jobs[jid]["deadline"]=time.monotonic()-1
            if mode in ("job_id", "attempt_id", "context_digest", "authority_vector_digest", "model_gate_sha256"):
                response[mode]="wrong"
            if mode in ("lease_fence", "cancel_epoch"):response[mode]=99
            return response
        s.authorize_egress=egress
        await s.start(); j=job(route="model"); c.jobs[j["job_id"]]=j
        await s.submit(j);status=await wait_done(s,j)
        state=s.jobs[j["job_id"]]
        assert status["compute_state"] == "STOP_CONFIRMED" and not status["capacity_held"]
        assert len(calls)==1
        terminals=[e for e in c.events if e["kind"]=="ATTEMPT_TERMINAL"]
        assert len(terminals)==1
        assert terminals[0]["evidence"]["admission_decision"]=="ADMITTED"
        if mode=="positive":
            assert state["dispatch_bytes"]>0 and len(c.results)==1
            assert terminals[0]["evidence"]["result_disposition"]=="FENCED"
        else:
            assert not state.get("dispatch_started") and not c.results
            assert status["disposition"] == ("CANCELLED" if mode=="cancel" else "FAILED" if mode=="denied" else "INCONCLUSIVE")
        await s.close(time.monotonic()+3)
    asyncio.run(run())


def test_model_callback_absent_zero_frame_keeps_claim_mocked_backend(tmp_path,monkeypatch):
    leases=[]
    async def fake_prepare(self,owned,admitted,deadline,cancel):
        _,data=setup_gate(tmp_path)
        data["job"]=admitted["job"]
        lease=ModelLease(tmp_path,data);owned.model_lease=lease;leases.append(lease)
        return {"mocked_no_network":True}
    monkeypatch.setattr(ModelAdapter,"start_for_attempt",fake_prepare)
    async def run():
        s,c=factory(tmp_path);await s.start();j=job(route="model");c.jobs[j["job_id"]]=j
        await s.submit(j);status=await wait_done(s,j)
        assert status["compute_state"]=="STOP_CONFIRMED" and status["disposition"]=="INCONCLUSIVE"
        assert not s.jobs[j["job_id"]].get("dispatch_started") and not c.results
        rows=[json.loads(x) for x in (tmp_path/"model/model-calls.jsonl").read_text().splitlines()]
        assert [r["kind"] for r in rows]==["CLAIM","SETTLE","RESULT_DISPOSITION"]
        assert rows[1]["phase"]=="RESOURCE_SETTLED" and rows[2]["usage"] is None
        await s.close(time.monotonic()+3)
    asyncio.run(run())


@pytest.mark.parametrize("fault", ["expiry", "cancel", "fence", "deadline", "duplicate"])
def test_actual_writer_guard_rechecks_after_executor_delay(tmp_path,fault):
    s,_=factory(tmp_path);identity={"lease_fence":1}
    state={"identity":dict(identity),"deadline":time.monotonic()+2,"cancel":asyncio.Event()}
    expiry=time.time()+1
    if fault=="expiry":expiry=time.time()-1
    if fault=="cancel":state["cancel"].set()
    if fault=="fence":state["identity"]["lease_fence"]=2
    if fault=="deadline":state["deadline"]=time.monotonic()-1
    if fault=="duplicate":state["dispatch_started"]=True
    stream=io.BytesIO()
    with pytest.raises(rt.DispatchDenied):s._write_sealed(state,stream,b"sealed",identity,expiry)
    assert stream.getvalue()==b""


def test_context_mutation_after_seal_rejected(tmp_path):
    async def run():
        s,c=factory(tmp_path);j=job(route="model");c.jobs[j["job_id"]]=j
        admitted=await c.admit(j["job_id"],j["attempt_id"],1)
        admitted["limits"]["model_gate_sha256"]="a"*64
        request={"job":j,"identity":{"lease_fence":1},"context":admitted["context"],"context_digest":rt.context_digest(admitted["context"])}
        state={"job":j,"deadline":time.monotonic()+10,"cancel":asyncio.Event(),"identity":request["identity"]}
        async def egress(*args):
            response=authorized(j,admitted["context"],admitted["authority_vector"],"a"*64)
            request["context"]["question"]="mutated after seal"
            return response
        s.authorize_egress=egress
        with pytest.raises(rt.DispatchDenied,match="SEALED_CONTEXT_CHANGED"):
            await s._prepare_dispatch(state,request,admitted)
    asyncio.run(run())


@pytest.mark.parametrize("mode",["unknown_admission","denied_admission","expired","malformed","result_unknown","accepted"])
def test_all_path_terminal_and_pending_same_id(tmp_path,monkeypatch,mode):
    if mode=="malformed":fixture_process(monkeypatch,"malformed")
    async def run():
        s,c=factory(tmp_path);deliveries=[];fail=True
        async def event(e):
            await c.event(e)
            if e["kind"]=="ATTEMPT_TERMINAL":
                deliveries.append(e)
                if fail:raise RuntimeError("mock lost callback reply")
        async def result(r):
            c.results.append(r)
            if mode=="result_unknown":raise RuntimeError("mock lost release reply")
            return {"disposition":"RELEASE_ADMITTED"}
        s.on_event=event;s.on_result=result
        if mode=="unknown_admission":c.decision="UNKNOWN"
        if mode=="denied_admission":c.decision="DENIED"
        await s.start();j=job();c.jobs[j["job_id"]]=j
        if mode=="expired":j["deadline_utc"]="2026-09-29T00:00:00+00:00"
        await s.submit(j);status=await wait_done(s,j)
        assert status["disposition"]==("SUCCEEDED" if mode=="accepted" else "FAILED" if mode=="denied_admission" else "INCONCLUSIVE")
        assert len(deliveries)==1 and len(s.pending_events)==1
        first=rt.canonical(deliveries[0]);result_count=len(c.results)
        fail=False
        assert await s.redeliver_pending()==0
        assert rt.canonical(deliveries[1])==first and len(c.results)==result_count
        assert (await s.submit(j))["disposition"]==status["disposition"]
        await s.close(time.monotonic()+3)
    asyncio.run(run())


@pytest.mark.parametrize("key,value",[("prompt_tokens",-1),("output_tokens",769),("output_tokens",True),
    ("duration_ns",float("nan")),("duration_ns",120_000_000_001),("certainty","OBSERVED")])
def test_usage_invalid_not_stored_as_zero(key,value):
    usage={"model_calls":1,"certainty":"BACKEND_REPORTED","prompt_tokens":10,"output_tokens":4,"duration_ns":100}
    usage[key]=value
    with pytest.raises(ValueError):rt.validated_usage(usage,"model")


@pytest.mark.parametrize("outcome",["RELEASE_ADMITTED","FENCED","REJECTED","UNKNOWN"])
def test_single_resource_settlement_then_result_usage(tmp_path,outcome):
    _,admitted=setup_gate(tmp_path);lease=ModelLease(tmp_path,admitted)
    lease.finish(confirmed=True,outcome="PENDING_VALIDATION")
    before=(tmp_path/"model/model-calls.jsonl").read_bytes()
    usage=rt.validated_usage({"model_calls":1,"certainty":"BACKEND_REPORTED"},"model")
    lease.result_disposition(result_disposition=outcome,usage=usage,context_digest="f"*64)
    lease.result_disposition(result_disposition="REPLAY",usage=None)
    lease.finish(confirmed=True,outcome="REPLAY")
    after=(tmp_path/"model/model-calls.jsonl").read_bytes()
    assert after.startswith(before)
    rows=[json.loads(x) for x in after.splitlines()]
    assert [r["kind"] for r in rows]==["CLAIM","SETTLE","RESULT_DISPOSITION"]
    assert rows[-1]["usage"]["output_tokens"] is None
    assert rows[1]["outcome"]=="PENDING_VALIDATION" and rows[-1]["claim_id"]==rows[0]["claim_id"]


def test_worker_expired_handoff_has_no_generation():
    j=job(route="model");now=time.time()
    handoff={k:j[k] for k in ("job_id","attempt_id","lease_fence","cancel_epoch")}
    handoff.update(decision_id="mock-only",context_digest="a"*64,checked_at=now-2,valid_until=now-1)
    with pytest.raises(RuntimeError,match="expired"):
        check_handoff(handoff,j,"a"*64)


def test_pending_terminal_survives_restart_without_recomputation(tmp_path):
    async def run():
        s,c=factory(tmp_path);captured=[]
        async def failure(e):
            if e["kind"]=="ATTEMPT_TERMINAL":
                captured.append(e)
                raise RuntimeError("mock unavailable event store")
        s.on_event=failure
        await s.start();j=job();c.jobs[j["job_id"]]=j
        await s.submit(j);await wait_done(s,j)
        assert (await s.close(time.monotonic()+3))["pending_terminal_events"]==1
        second,d=factory(tmp_path);await second.start()
        replay=[e for e in d.events if e["kind"]=="ATTEMPT_TERMINAL"]
        assert replay==captured and not d.results and not second.jobs
        assert not second.pending_events
        await second.close(time.monotonic()+3)
    asyncio.run(run())


def test_post_first_byte_cancel_records_possible_transmission_and_owned_stop(tmp_path,monkeypatch):
    fixture_process(monkeypatch,"hang")
    async def run():
        s,c=factory(tmp_path);await s.start();j=job();c.jobs[j["job_id"]]=j
        await s.submit(j)
        for _ in range(300):
            if s.jobs[j["job_id"]].get("dispatch_bytes",0):break
            await asyncio.sleep(.01)
        assert s.jobs[j["job_id"]]["dispatch_bytes"]>0
        await s.cancel(j["job_id"],2,"after observed write")
        status=await wait_done(s,j)
        assert status["disposition"]=="CANCELLED" and status["compute_state"]=="STOP_CONFIRMED"
        assert not c.results
        event=next(e for e in c.events if e["kind"]=="DISPATCH_OBSERVED")
        assert event["evidence"]["bytes_written"]>0
        await s.close(time.monotonic()+3)
    asyncio.run(run())


def test_deterministic_never_calls_model_egress(tmp_path):
    async def run():
        s,c=factory(tmp_path)
        async def forbidden(*args):raise AssertionError("model-only callback")
        s.authorize_egress=forbidden
        await s.start();j=job();c.jobs[j["job_id"]]=j
        await s.submit(j);state=await wait_done(s,j)
        assert len(c.results)==1 and state["compute_state"]=="STOP_CONFIRMED"
        await s.close(time.monotonic()+3)
    asyncio.run(run())


def test_result_audit_failure_still_delivers_terminal(tmp_path):
    async def run():
        s,c=factory(tmp_path);await s.start();j=job();c.jobs[j["job_id"]]=j
        # Exercise only metadata reconciliation, with no backend/process launch.
        await s.submit(j);await wait_done(s,j)
        state=s.jobs[j["job_id"]]
        class BrokenLease:
            claim_id="mock-unavailable-audit"
            def result_disposition(self,**evidence):raise OSError("mock append unavailable")
        state["owned_job"].model_lease=BrokenLease()
        state["terminal_emitted"]=False
        await s._terminal(state)
        terminal=[e for e in c.events if e["kind"]=="ATTEMPT_TERMINAL"][-1]
        assert terminal["evidence"]["reason"]=="RESULT_AUDIT_UNKNOWN"
        assert terminal["evidence"]["job_disposition"]=="INCONCLUSIVE"
        await s.close(time.monotonic()+3)
    asyncio.run(run())
