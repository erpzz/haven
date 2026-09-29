import json
from . import LABEL
from .types import Budget, Conflict, Denied, check_request, canonical, digest, now
from .context import build_context
from .backend import FixtureQuoteBackend, bounded_call
from .validation import validate_output
from .store import context_still_permitted

class Coordinator:
    def __init__(self, ledger, backend=None, budget=None):
        self.ledger = ledger
        self.backend = backend if backend is not None else FixtureQuoteBackend()
        self.budget = budget if budget is not None else Budget()
        self.budget.check()

    def submit(self, principal, request):
        request = check_request(principal, request)
        key = (principal.actor, request["request_id"])
        hashed = digest(request)
        existing = False
        with self.ledger.connect(write=True) as c:
            row = c.execute("SELECT payload_hash FROM requests WHERE actor=? AND request_id=?",key).fetchone()
            if row:
                if row[0] != hashed:
                    raise Conflict("CONFLICTING_REQUEST_REUSE")
                existing = True
            else:
                context = build_context(c, principal, request, self.budget, now())
                context["backend"] = {"name":self.backend.name,"version":self.backend.version}
                from dataclasses import asdict
                context["budget"] = asdict(self.budget)
                if len(canonical(context).encode()) > self.budget.max_context_bytes:
                    raise Denied("CONTEXT_BUDGET_EXCEEDED")
                c.execute("INSERT INTO requests VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (*key,hashed,canonical(request),canonical(context),now(),"RUNNING","PENDING",None,None))
        if existing:
            # No retry/resubmit on replay, including an interrupted RUNNING record.
            return self.read(principal, key[1])
        if not context["records"]:
            self._finish(key,"UNAVAILABLE","NO_PERMITTED_EVIDENCE",None)
            return self.read(principal,key[1])
        for number in range(1,self.budget.max_attempts+1):
            with self.ledger.connect(write=True) as c:
                if not context_still_permitted(c, context, now()):
                    self._finish_in(c,key,"REJECTED","CONTEXT_REVOKED_OR_CHANGED",None)
                    break
                c.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?)",(*key,number,now(),None,"STARTED",None))
            state, output = bounded_call(self.backend, context, request, self.budget)
            reason = state
            terminal = state not in ("TIMEOUT","BACKEND_FAILED") or number == self.budget.max_attempts
            status = "UNAVAILABLE"
            if state == "RETURNED":
                try:
                    validate_output(output, context, request, self.budget)
                    status = "ANSWER_READY" if output["kind"] == "ANSWER" else "PROPOSAL_READY"
                    reason = "VALIDATED_GROUNDED_QUOTES"
                except Denied as exc:
                    status, reason = "REJECTED", str(exc)
            with self.ledger.connect(write=True) as c:
                # Revocation between selection, model execution and commit blocks delivery.
                if not context_still_permitted(c,context,now()):
                    terminal,status,reason = True,"REJECTED","CONTEXT_REVOKED_OR_CHANGED"
                c.execute("UPDATE attempts SET ended_at=?,state=?,output_json=? WHERE actor=? AND request_id=? AND attempt=?",
                          (now(),reason,canonical(output) if output is not None else None,*key,number))
                if terminal:
                    self._finish_in(c,key,status,reason,output if status in ("ANSWER_READY","PROPOSAL_READY") else None)
            if terminal:
                break
        return self.read(principal,key[1])

    def _finish_in(self,c,key,status,reason,result):
        c.execute("UPDATE requests SET status=?,reason=?,result_json=?,completed_at=? WHERE actor=? AND request_id=?",
                  (status,reason,canonical(result) if result is not None else None,now(),*key))

    def _finish(self,key,status,reason,result):
        with self.ledger.connect(write=True) as c:
            self._finish_in(c,key,status,reason,result)

    def read(self, principal, request_id):
        principal.check()
        with self.ledger.connect() as c:
            row = c.execute("SELECT * FROM requests WHERE actor=? AND request_id=?",(principal.actor,request_id)).fetchone()
            if row is None:
                raise Denied("REQUEST_NOT_ACCESSIBLE")
            context = json.loads(row["context_json"])
            permitted = context_still_permitted(c,context,now())
            # Suppress the entire derived answer after any contributing grant revocation.
            status = row["status"] if permitted else "WITHHELD"
            reason = row["reason"] if permitted else "CONTEXT_REVOKED_OR_CHANGED"
            if status == "RUNNING":
                status,reason = "OUTCOME_UNKNOWN","INCOMPLETE_JOB_NO_AUTOMATIC_REPLAY"
            result = json.loads(row["result_json"]) if permitted and row["result_json"] else None
            attempts = [dict(a) for a in c.execute("SELECT attempt,started_at,ended_at,state FROM attempts WHERE actor=? AND request_id=? ORDER BY attempt",
                                                  (principal.actor,request_id))]
            return {"label":LABEL,"synthetic":True,"mapping_version":1,
                    "test_identity_only":True,"actor":principal.actor,"request_id":request_id,
                    "status":status,"reason":reason,"request":json.loads(row["request_json"]),
                    "created_at":row["created_at"],"completed_at":row["completed_at"],
                    "context":context if permitted else None,"result":result,"attempts":attempts,
                    "backend":context["backend"],
                    "provider_spend_usd":0,"external_actions":0}
