"""Only the built-in deterministic quote fixture is exposed by the runner.

The Protocol is a replaceable boundary, not permission to enable a real provider.
Trusted unit tests inject other synthetic implementations for negative cases.
"""
import multiprocessing
from typing import Protocol
from . import LABEL
from .types import canonical

class ModelBackend(Protocol):
    name: str
    version: str
    def generate(self, context: dict, request: dict) -> dict: ...

class FixtureQuoteBackend:
    name = "deterministic-fixture-quotes"
    version = "1"
    def generate(self, context, request):
        return {"schema_version":1, "label":LABEL,
                "kind":"ANSWER" if request["kind"] == "PROJECT_RECALL" else "PROPOSAL",
                "claims":[{"evidence_id":r["evidence_id"],"quote":r["text"]} for r in context["records"]],
                "proposal":None if request["kind"] == "PROJECT_RECALL" else
                    {"kind":"DRAFT_NOTE", "state":"PROPOSED", "execution_enabled":False},
                "external_spend_usd":0, "tool_calls":0}

def _child(send, backend, context, request, output_limit):
    try:
        raw = canonical(backend.generate(context, request)).encode()
        if len(raw) > output_limit:
            send.send_bytes(b'{"backend_error":"OUTPUT_BUDGET"}')
        else:
            send.send_bytes(raw)
    except Exception:
        send.send_bytes(b'{"backend_error":"BACKEND_FAILED"}')
    finally:
        send.close()

def bounded_call(backend, context, request, budget):
    """Bound real child execution; terminate only this call's child on timeout.

    This is not an OS network/security sandbox. No external adapter exists here.
    """
    mp = multiprocessing.get_context("fork")
    receive, send = mp.Pipe(duplex=False)
    child = mp.Process(target=_child, args=(send,backend,context,request,budget.max_output_bytes))
    child.start()
    send.close()
    try:
        if not receive.poll(budget.timeout_seconds):
            return "TIMEOUT", None
        try:
            raw = receive.recv_bytes(budget.max_output_bytes)
        except (EOFError, OSError):
            return "BACKEND_FAILED", None
        import json
        output = json.loads(raw)
        if type(output) is dict and "backend_error" in output:
            return output["backend_error"], None
        return "RETURNED", output
    finally:
        receive.close()
        child.join(timeout=0.05)
        if child.is_alive():
            child.terminate()
            child.join(timeout=0.5)
        if child.is_alive():
            child.kill()
            child.join(timeout=0.5)
        child.close()
