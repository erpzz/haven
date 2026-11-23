import ast
from dataclasses import replace
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from uuid import uuid4

from haven_lab import LABEL
from haven_lab.types import Budget, TestPrincipal, Denied, Conflict, Unavailable
from haven_lab.store import Ledger, LAB_ROOT
from haven_lab.coordinator import Coordinator
from haven_lab.backend import FixtureQuoteBackend
from haven_lab.render import html_transcript

A=TestPrincipal("TEST_USER_A")
B=TestPrincipal("TEST_USER_B")

def request(actor="TEST_USER_A",**changes):
    return {"schema_version":1,"request_id":str(uuid4()),"actor_id":actor,
            "topic":"PROJECT_RED","question":"What did we decide about the synthetic fixture?",
            "kind":"PROJECT_RECALL",**changes}

class MutatedBackend(FixtureQuoteBackend):
    name="negative-output-fixture"
    def __init__(self,mutation): self.mutation=mutation
    def generate(self,context,req):
        output=super().generate(context,req)
        self.mutation(output)
        return output

class SlowBackend(FixtureQuoteBackend):
    name="sleeping-timeout-fixture"
    def generate(self,context,req):
        time.sleep(0.3)
        return super().generate(context,req)

class ErrorBackend(FixtureQuoteBackend):
    name="exception-fixture"
    def generate(self,context,req): raise RuntimeError("synthetic failure")

class OnceSlowBackend(FixtureQuoteBackend):
    name="first-call-timeout-fixture"
    def __init__(self): self.calls=multiprocessing.Value("i",0)
    def generate(self,context,req):
        with self.calls.get_lock(): self.calls.value+=1; number=self.calls.value
        if number==1: time.sleep(0.3)
        return super().generate(context,req)

class RevokingBackend(FixtureQuoteBackend):
    name="revocation-during-job-fixture"
    def __init__(self,run): self.run=run
    def generate(self,context,req):
        Ledger(self.run).revoke(B,"SHARED_DECISION",A.actor)
        return super().generate(context,req)

class N1Tests(unittest.TestCase):
    def setUp(self):
        self.ledger=Ledger.create()
        self.coordinator=Coordinator(self.ledger)

    def test_private_shared_context_and_traceable_answer(self):
        out=self.coordinator.submit(A,request())
        self.assertEqual(out["status"],"ANSWER_READY")
        ids={x["evidence_id"] for x in out["context"]["records"]}
        self.assertIn("A_DECISION",ids); self.assertIn("SHARED_DECISION",ids)
        self.assertNotIn("B_PRIVATE",ids)
        self.assertEqual(len(out["result"]["claims"]),len(ids))
        self.assertEqual(out["provider_spend_usd"],0)
        self.assertEqual(out["external_actions"],0)
        out_b=self.coordinator.submit(B,request(B.actor))
        self.assertEqual({x["evidence_id"] for x in out_b["context"]["records"]},{"B_PRIVATE","SHARED_DECISION"})

    def test_cross_user_read_denied_without_presence_disclosure(self):
        req=request(); self.coordinator.submit(A,req)
        for rid in (req["request_id"],str(uuid4())):
            with self.assertRaisesRegex(Denied,"REQUEST_NOT_ACCESSIBLE"):
                self.coordinator.read(B,rid)

    def test_revoked_grant_rechecked_before_selection(self):
        self.ledger.revoke(B,"SHARED_DECISION",A.actor)
        out=self.coordinator.submit(A,request())
        self.assertNotIn("SHARED_DECISION",{x["evidence_id"] for x in out["context"]["records"]})

    def test_revoked_during_job_cannot_deliver(self):
        out=Coordinator(self.ledger,RevokingBackend(self.ledger.run_dir)).submit(A,request())
        self.assertEqual(out["status"],"WITHHELD")
        self.assertIsNone(out["result"]);self.assertIsNone(out["context"])
        with self.ledger.connect() as c:
            self.assertEqual(c.execute("SELECT status FROM requests").fetchone()[0],"REJECTED")

    def test_revocation_invalidates_cached_read_and_idempotent_replay(self):
        req=request(); self.coordinator.submit(A,req)
        self.ledger.revoke(B,"SHARED_DECISION",A.actor)
        before=self.ledger.path.read_bytes()
        for result in (self.coordinator.read(A,req["request_id"]),self.coordinator.submit(A,req)):
            self.assertEqual(result["status"],"WITHHELD");self.assertIsNone(result["result"])
        self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_grant_owner_and_purpose_are_enforced(self):
        with self.assertRaises(Denied):self.ledger.revoke(A,"SHARED_DECISION",A.actor)
        with self.ledger.connect(write=True) as c:
            c.execute("UPDATE grants SET purpose='cloud.transmit'")
        out=self.coordinator.submit(A,request())
        self.assertNotIn("SHARED_DECISION",{r["evidence_id"] for r in out["context"]["records"]})

    def test_expired_grant_is_not_context(self):
        with self.ledger.connect(write=True) as c:c.execute("UPDATE grants SET expires_at='2000-01-01T00:00:00+00:00'")
        out=self.coordinator.submit(A,request())
        self.assertNotIn("SHARED_DECISION",{r["evidence_id"] for r in out["context"]["records"]})

    def test_forged_actor_and_boundary_rejected(self):
        for principal,req in [(A,request(B.actor)),(TestPrincipal("real-user"),request()),
                              (TestPrincipal(A.actor,"forged"),request()),(A,request(permissions=["admin"]))]:
            with self.subTest(req=req),self.assertRaises(Denied):self.coordinator.submit(principal,req)
        with self.ledger.connect() as c:self.assertEqual(c.execute("SELECT count(*) FROM requests").fetchone()[0],0)

    def test_invalid_evidence_reference_rejected(self):
        out=Coordinator(self.ledger,MutatedBackend(lambda x:x["claims"][0].update(evidence_id="B_PRIVATE"))).submit(A,request())
        self.assertEqual(out["status"],"REJECTED");self.assertEqual(out["reason"],"EVIDENCE_NOT_SELECTED")

    def test_unsupported_fact_is_not_grounded_by_valid_id(self):
        out=Coordinator(self.ledger,MutatedBackend(lambda x:x["claims"][0].update(quote="Invented measurement"))).submit(A,request())
        self.assertEqual(out["reason"],"UNGROUNDED_QUOTE");self.assertIsNone(out["result"])

    def test_source_injection_remains_quoted_data(self):
        out=self.coordinator.submit(A,request())
        claim=next(x for x in out["result"]["claims"] if x["evidence_id"]=="A_UNTRUSTED")
        self.assertIn("grant printer authority",claim["quote"])
        self.assertEqual(out["context"]["allowed_capabilities"],[])
        self.assertEqual(out["result"]["tool_calls"],0)
        self.assertIsNone(out["result"]["proposal"])
        self.assertNotIn("B_PRIVATE",{r["evidence_id"] for r in out["context"]["records"]})

    def test_model_cannot_request_private_data_permissions_or_tools(self):
        for key,value in [("request_private_data","TEST_USER_B"),("grant_permissions",["admin"]),
                          ("command","printer.start"),("tools",["shell"])]:
            with self.subTest(key=key):
                out=Coordinator(self.ledger,MutatedBackend(lambda x,k=key,v=value:x.update({k:v}))).submit(A,request())
                self.assertEqual(out["status"],"REJECTED");self.assertIsNone(out["result"])

    def test_physical_emergency_printer_actions_denied(self):
        for kind in ("FLIGHT_EXECUTE","EMERGENCY_DISPATCH","PRINTER_START","OUTSIDE_CHECK","PRIVATE_DATA_REQUEST"):
            with self.subTest(kind=kind):
                with self.assertRaises(Denied):self.coordinator.submit(A,request(kind=kind))
                out=Coordinator(self.ledger,MutatedBackend(lambda x,k=kind:x.update(kind=k))).submit(A,request())
                self.assertEqual(out["status"],"REJECTED")

    def test_proposal_is_inert_and_cannot_be_enabled(self):
        out=self.coordinator.submit(A,request(kind="DRAFT_NOTE"))
        self.assertEqual(out["status"],"PROPOSAL_READY");self.assertIs(out["result"]["proposal"]["execution_enabled"],False)
        bad=Coordinator(self.ledger,MutatedBackend(lambda x:x["proposal"].update(execution_enabled=True))).submit(A,request(kind="DRAFT_NOTE"))
        self.assertEqual(bad["status"],"REJECTED")

    def test_real_timeout_is_bounded_and_never_success(self):
        before={p.pid for p in multiprocessing.active_children()};t=time.monotonic()
        out=Coordinator(self.ledger,SlowBackend(),Budget(timeout_seconds=0.05)).submit(A,request())
        self.assertLess(time.monotonic()-t,2)
        self.assertEqual(out["status"],"UNAVAILABLE");self.assertEqual(len(out["attempts"]),2)
        self.assertEqual([x["state"] for x in out["attempts"]],["TIMEOUT","TIMEOUT"])
        self.assertIsNone(out["result"])
        self.assertEqual({p.pid for p in multiprocessing.active_children()},before)

    def test_retry_once_then_success_and_replay_does_not_retry(self):
        backend=OnceSlowBackend(); coordinator=Coordinator(self.ledger,backend,Budget(timeout_seconds=0.05))
        req=request();out=coordinator.submit(A,req)
        self.assertEqual(out["status"],"ANSWER_READY");self.assertEqual(backend.calls.value,2)
        coordinator.submit(A,req);self.assertEqual(backend.calls.value,2)

    def test_backend_failure_bounded_and_invalid_output_not_retried(self):
        out=Coordinator(self.ledger,ErrorBackend()).submit(A,request())
        self.assertEqual(out["status"],"UNAVAILABLE");self.assertEqual(len(out["attempts"]),2)
        out=Coordinator(self.ledger,MutatedBackend(lambda x:x.update(label="LIVE AI"))).submit(A,request())
        self.assertEqual(len(out["attempts"]),1);self.assertEqual(out["status"],"REJECTED")

    def test_zero_external_budget_and_hard_caps(self):
        for change in [{"external_provider_usd":1},{"external_provider_usd":float("nan")},{"tool_calls":1},
                       {"max_attempts":3},{"max_attempts":True},{"timeout_seconds":float("inf")}]:
            with self.subTest(change=change),self.assertRaises(Denied):Coordinator(self.ledger,budget=replace(Budget(),**change))
        out=Coordinator(self.ledger,MutatedBackend(lambda x:x.update(external_spend_usd=1))).submit(A,request())
        self.assertEqual(out["status"],"REJECTED")

    def test_output_and_context_size_caps(self):
        out=Coordinator(self.ledger,MutatedBackend(lambda x:x.update(extra="x"*40000))).submit(A,request())
        self.assertEqual(out["status"],"UNAVAILABLE");self.assertEqual(out["reason"],"OUTPUT_BUDGET")
        with self.assertRaises(Denied):Coordinator(self.ledger,budget=Budget(max_context_bytes=256)).submit(A,request())

    def test_restart_and_separate_process_persistence(self):
        req=request();out=self.coordinator.submit(A,req)
        new=Coordinator(Ledger(self.ledger.run_dir)).read(A,req["request_id"])
        self.assertEqual(out,new)
        p=subprocess.run([sys.executable,"-B","-m","haven_lab","export","--run",str(self.ledger.run_dir),
            "--request-id",req["request_id"],"--format","json"],cwd=LAB_ROOT,capture_output=True,text=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),out)

    def test_conflicting_request_reuse_never_changes_history(self):
        req=request();out=self.coordinator.submit(A,req);before=self.ledger.path.read_bytes()
        with self.assertRaises(Conflict):self.coordinator.submit(A,{**req,"question":"different"})
        self.assertEqual(self.ledger.path.read_bytes(),before)
        self.assertEqual(self.coordinator.submit(A,req),out)

    def test_isolated_runs_and_m0_path_cannot_open(self):
        other=Ledger.create();self.assertNotEqual(other.path,self.ledger.path)
        req=request();self.coordinator.submit(A,req)
        with self.assertRaises(Denied):Coordinator(other).read(A,req["request_id"])
        with self.assertRaises(Denied):Ledger(LAB_ROOT.parent.parent/"project-astra")

    def test_read_export_do_not_modify_database(self):
        req=request();self.coordinator.submit(A,req);before=self.ledger.path.read_bytes()
        for _ in range(3):html_transcript(self.coordinator.read(A,req["request_id"]))
        self.assertEqual(self.ledger.path.read_bytes(),before)
        with self.ledger.connect() as c:
            with self.assertRaises(sqlite3.OperationalError):c.execute("DELETE FROM requests")

    def test_connection_settings_version_and_database_errors(self):
        with self.ledger.connect(write=True) as c:
            for pragma,expected in [("journal_mode","delete"),("synchronous",2),("foreign_keys",1),("busy_timeout",500)]:
                self.assertEqual(c.execute("PRAGMA "+pragma).fetchone()[0],expected)
        req=request();self.coordinator.submit(A,req)
        lock=sqlite3.connect(self.ledger.path,isolation_level=None);lock.execute("BEGIN EXCLUSIVE")
        try:
            with self.assertRaises(Unavailable):self.coordinator.read(A,req["request_id"])
        finally:lock.rollback();lock.close()
        c=sqlite3.connect(self.ledger.path);c.execute("PRAGMA user_version=99");c.close()
        before=self.ledger.path.read_bytes()
        with self.assertRaises(Unavailable):self.coordinator.read(A,req["request_id"])
        self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_incomplete_job_returns_unknown_without_resume(self):
        req=request();self.coordinator.submit(A,req)
        with self.ledger.connect(write=True) as c:
            c.execute("UPDATE requests SET status='RUNNING',reason='PENDING',result_json=NULL,completed_at=NULL")
        before=self.ledger.path.read_bytes()
        out=self.coordinator.submit(A,req)
        self.assertEqual(out["status"],"OUTCOME_UNKNOWN");self.assertIsNone(out["result"])
        self.assertEqual(self.ledger.path.read_bytes(),before)

    def test_metadata_classes_and_render_escape_preserved(self):
        fixture=json.loads((LAB_ROOT/"fixtures/context.json").read_text());fixture["records"][0]["text"]='<script>alert("fixture")</script>'
        out=Coordinator(Ledger.create(fixture)).submit(A,request())
        self.assertEqual({r["category"] for r in out["context"]["records"]},
                         {"CURRENT_STATE","HISTORICAL_FACT","USER_STATEMENT","MODEL_INTERPRETATION"})
        html=html_transcript(out)
        self.assertIn(LABEL,html);self.assertNotIn("<script>",html);self.assertIn("&lt;script&gt;",html)
        for r in out["context"]["records"]:
            self.assertTrue(r["synthetic"]);self.assertIn(r["captured_at"],html);self.assertIn(r["evidence_id"],html)

    def test_no_evidence_is_unavailable_and_no_backend_attempt(self):
        out=self.coordinator.submit(A,request(topic="MISSING_TOPIC"))
        self.assertEqual(out["status"],"UNAVAILABLE");self.assertEqual(out["attempts"],[])
        self.assertEqual(out["reason"],"NO_PERMITTED_EVIDENCE")

    def test_runner_has_no_adapter_import_or_provider_selector(self):
        forbidden={"socket","urllib","http","requests","httpx","smtplib","imaplib","serial","webbrowser","ctypes","importlib"}
        for file in (LAB_ROOT/"haven_lab").glob("*.py"):
            tree=ast.parse(file.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):names=[n.name.split('.')[0] for n in node.names]
                elif isinstance(node,ast.ImportFrom):names=[(node.module or '').split('.')[0]]
                else:continue
                self.assertFalse(forbidden.intersection(names),(file,names))
        p=subprocess.run([sys.executable,"-B","-m","haven_lab","ask","--backend","live"],cwd=LAB_ROOT,text=True,capture_output=True,timeout=5)
        self.assertNotEqual(p.returncode,0)

    def test_executed_flow_under_network_and_shell_audit_denial(self):
        code="""
import sys
blocked=[]
def guard(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        blocked.append(event)
        raise RuntimeError('external operation forbidden in this test')
sys.addaudithook(guard)
from haven_lab.store import Ledger
from haven_lab.coordinator import Coordinator
from haven_lab.types import TestPrincipal
from uuid import uuid4
r={'schema_version':1,'request_id':str(uuid4()),'actor_id':'TEST_USER_A','topic':'PROJECT_RED','question':'fixture recall','kind':'PROJECT_RECALL'}
out=Coordinator(Ledger.create()).submit(TestPrincipal('TEST_USER_A'),r)
assert out['status']=='ANSWER_READY'
assert blocked==[]
print('EXECUTED_PASS: no network/shell audit events; not OS-level containment')
"""
        p=subprocess.run([sys.executable,"-B","-c",code],cwd=LAB_ROOT,text=True,capture_output=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn("EXECUTED_PASS",p.stdout)

    def test_fixture_metadata_strictness_regression(self):
        import copy
        from haven_lab.store import validate_fixture
        original=json.loads((LAB_ROOT/"fixtures/context.json").read_text())
        for changes in ({"schema_version":99},{"schema_version":True},{"claim_class":123},
                        {"category":"MODEL_INTERPRETATION","claim_class":"OBSERVED_FACT"},
                        {"evidence_id":"../../bad"},{"version":True},{"topic":[]},
                        {"captured_at":"2030-01-01T00:00:00+00:00"},{"received_at":"bad"}):
            data=copy.deepcopy(original);data["records"][0].update(changes)
            with self.subTest(changes=changes),self.assertRaises(Denied):validate_fixture(data)
        data=copy.deepcopy(original);data["grants"]*=2
        with self.assertRaises(Denied):validate_fixture(data)

    def test_final_context_including_backend_metadata_obeys_budget(self):
        from haven_lab.context import build_context
        from haven_lab.types import canonical,now
        req=request()
        with self.ledger.connect() as c:packet=build_context(c,A,req,Budget(),now())
        narrow=Budget(max_context_bytes=len(canonical(packet).encode())+20)
        with self.assertRaisesRegex(Denied,"CONTEXT_BUDGET_EXCEEDED"):
            Coordinator(self.ledger,budget=narrow).submit(A,req)
        with self.ledger.connect() as c:self.assertEqual(c.execute("SELECT count(*) FROM requests").fetchone()[0],0)

    def test_empty_grounded_claims_cannot_be_success(self):
        for kind in ("PROJECT_RECALL","DRAFT_NOTE"):
            out=Coordinator(self.ledger,MutatedBackend(lambda x:x.update(claims=[]))).submit(A,request(kind=kind))
            self.assertEqual(out["status"],"REJECTED");self.assertIsNone(out["result"])

    def test_initialization_checks_durability_before_schema_transaction(self):
        from unittest.mock import patch
        real_connect=sqlite3.connect
        observed=[]
        class InspectConnection(sqlite3.Connection):
            def executescript(connection,script):
                values={p:connection.execute("PRAGMA "+p).fetchone()[0] for p in
                        ("journal_mode","synchronous","foreign_keys","busy_timeout")}
                observed.append(values)
                self.assertFalse(connection.in_transaction)
                self.assertEqual(values,{"journal_mode":"delete","synchronous":2,"foreign_keys":1,"busy_timeout":500})
                return super().executescript(script)
        def connect(*args,**kwargs):
            c=real_connect(*args,**kwargs,factory=InspectConnection)
            c.execute("PRAGMA synchronous=OFF")
            c.execute("PRAGMA foreign_keys=OFF")
            return c
        with patch("haven_lab.store.sqlite3.connect",side_effect=connect):
            fresh=Ledger.create()
            with fresh.connect() as c:
                self.assertEqual(c.execute("PRAGMA synchronous").fetchone()[0],2)
                self.assertEqual(c.execute("PRAGMA foreign_keys").fetchone()[0],1)
        self.assertEqual(len(observed),1)

if __name__=="__main__":unittest.main()
