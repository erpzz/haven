"""Resource-ledger unit tests in isolated temporary trees; no model/backend calls."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import pytest

from haven.model_adapter import ModelLease, ModelAdapter, GATE_VERSION, ALLOCATIONS
from haven.supervisor import canonical, digest


def setup_gate(tmp_path, allocation="readiness"):
    directory=tmp_path/"model";directory.mkdir(exist_ok=True)
    pin={k:'a'*64 for k in ("manifest_sha256","runtime_sha256","template_sha256","preprocessor_sha256")}
    gate={"version":GATE_VERSION,"enabled":True,"root_thread_id":"01a0eb51-c8b3-7923-94ed-ea1874de843e",
          "authorizing_task":"MODEL-READY","independent_benign_receipt_sha256":"b"*64,
          "scope":"SYNTHETIC_LOCAL_TEXT_IMAGE_ONLY","expires_utc":"2026-09-29T10:10:16Z",
          "identity":pin,"slots":{"unit-only-slot":{"allocation":allocation}}}
    (directory/"model-gate.json").write_bytes(canonical(gate))
    admitted={"job":{"job_id":"unit-job","attempt_id":"unit-attempt","lease_fence":1,"cancel_epoch":1,
                     "request_digest":"c"*64,"route":"model"},
              "limits":{"model_attempt_token":"unit-only-slot","model_allocation":allocation,
                        "model_binding_id":"unit-binding","model_gate_sha256":digest(gate)},
              "model_identity":pin}
    return gate,admitted


def write_gate(tmp_path,gate,admitted):
    (tmp_path/"model/model-gate.json").write_bytes(canonical(gate))
    admitted["limits"]["model_gate_sha256"]=digest(gate)


def seed_ledger(tmp_path,allocation,count,seconds=1,unknown=False):
    path=tmp_path/"model/model-calls.jsonl"
    with path.open('ab') as f:
        for i in range(count):
            f.write(canonical({"kind":"CLAIM","claim_id":str(i),"token":"seed-"+str(i),"allocation":allocation})+b'\n')
            if not unknown:
                f.write(canonical({"kind":"SETTLE","claim_id":str(i),"charged_seconds":seconds,
                                   "cleanup_confirmed":True})+b'\n')


def test_unit_pool_claim_lock_once_and_binding(tmp_path):
    gate,admitted=setup_gate(tmp_path)
    lease=ModelLease(tmp_path,admitted)
    records=[json.loads(x) for x in (tmp_path/"model/model-calls.jsonl").read_text().splitlines()]
    assert records[0]["job"]==admitted["job"] and records[0]["binding_id"]=="unit-binding"
    with pytest.raises(RuntimeError,match="capacity busy"):ModelLease(tmp_path,admitted)
    lease.finish(confirmed=True,outcome="UNIT_NO_NETWORK")
    with pytest.raises(RuntimeError,match="already consumed"):ModelLease(tmp_path,admitted)


@pytest.mark.parametrize("allocation",list(ALLOCATIONS))
def test_unit_fixed_allocation_caps(tmp_path,allocation):
    gate,admitted=setup_gate(tmp_path,allocation)
    seed_ledger(tmp_path,allocation,ALLOCATIONS[allocation])
    with pytest.raises(RuntimeError,match="exhausted"):ModelLease(tmp_path,admitted)


def test_unit_unknown_cleanup_blocks_new_work(tmp_path):
    gate,admitted=setup_gate(tmp_path)
    seed_ledger(tmp_path,"readiness",1,unknown=True)
    with pytest.raises(RuntimeError,match="cleanup unknown"):ModelLease(tmp_path,admitted)


def test_unit_time_budget(tmp_path):
    gate,admitted=setup_gate(tmp_path)
    seed_ledger(tmp_path,"final",45,seconds=120)
    with pytest.raises(RuntimeError,match="wall budget"):ModelLease(tmp_path,admitted)


@pytest.mark.parametrize("change",["disabled","expired","wrong_scope","changed_gate","wrong_identity"])
def test_unit_gate_fail_closed(tmp_path,change):
    gate,admitted=setup_gate(tmp_path)
    if change=="disabled":gate["enabled"]=False
    if change=="expired":gate["expires_utc"]="2026-09-29T00:00:00Z"
    if change=="wrong_scope":gate["scope"]="wrong"
    if change=="wrong_identity":admitted["model_identity"]=deepcopy(admitted["model_identity"]);admitted["model_identity"]["manifest_sha256"]="wrong"
    write_gate(tmp_path,gate,admitted)
    if change=="changed_gate":admitted["limits"]["model_gate_sha256"]="wrong"
    with pytest.raises(RuntimeError):ModelLease(tmp_path,admitted)
    assert not (tmp_path/"model/model-calls.jsonl").exists()


def test_unit_corrupt_ledger_fails_closed(tmp_path):
    gate,admitted=setup_gate(tmp_path)
    (tmp_path/"model/model-calls.jsonl").write_bytes(b'{"kind":"CLAIM"')
    with pytest.raises(ValueError):ModelLease(tmp_path,admitted)


def test_runtime_pin_works_without_localappdata(tmp_path,monkeypatch):
    import hashlib
    binary=tmp_path/"fake-runtime-no-execution.exe";binary.write_bytes(b"never executed")
    adapter=ModelAdapter(tmp_path)
    (adapter.directory/"runtime-pin.json").write_text(json.dumps({"path":str(binary),"sha256":hashlib.sha256(binary.read_bytes()).hexdigest()}))
    monkeypatch.delenv("LOCALAPPDATA",raising=False)
    assert adapter.installed_binary()==binary
    assert adapter.gate_snapshot()["enabled"] is False
