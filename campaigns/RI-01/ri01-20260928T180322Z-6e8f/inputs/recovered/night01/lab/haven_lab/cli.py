"""No dynamic backend loading, plugins, network or real account selection."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4
from . import LABEL
from .types import TestPrincipal, USERS, LabError
from .store import Ledger
from .coordinator import Coordinator
from .render import text_transcript, html_transcript

def main(argv=None):
    if sys.version_info[:2] != (3,12):
        print(LABEL+" — Python 3.12 required",file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description=LABEL+". Offline synthetic CLI; no real authentication.")
    sub = parser.add_subparsers(dest="command",required=True)
    sub.add_parser("init",help="Create a NEW isolated synthetic run")
    for command in ("ask","read","export","revoke"):
        p = sub.add_parser(command)
        p.add_argument("--run",required=True,type=Path)
        p.add_argument("--test-principal",choices=sorted(USERS),default="TEST_USER_A")
        if command in ("ask","read","export"):
            p.add_argument("--request-id",required=command != "ask",default=None)
        if command == "ask":
            p.add_argument("--topic",default="PROJECT_RED")
            p.add_argument("--question",default="What did we decide about the synthetic sensor fixture?")
            p.add_argument("--kind",choices=("PROJECT_RECALL","DRAFT_NOTE"),default="PROJECT_RECALL")
        if command == "revoke":
            p.add_argument("--evidence-id",required=True)
            p.add_argument("--recipient",required=True,choices=sorted(USERS))
        if command == "export":
            p.add_argument("--format",choices=("json","html"),default="html")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            ledger = Ledger.create()
            print(json.dumps({"label":LABEL,"run":str(ledger.run_dir),"synthetic":True}))
            return 0
        ledger = Ledger(args.run)
        principal = TestPrincipal(args.test_principal)
        if args.command == "revoke":
            ledger.revoke(principal,args.evidence_id,args.recipient)
            print(LABEL+" — synthetic grant revoked")
            return 0
        coordinator = Coordinator(ledger)
        if args.command == "ask":
            view = coordinator.submit(principal,{"schema_version":1,"request_id":args.request_id or str(uuid4()),
                "actor_id":principal.actor,"topic":args.topic,"question":args.question,"kind":args.kind})
        else:
            view = coordinator.read(principal,args.request_id)
        if args.command == "export":
            print(json.dumps(view,indent=2) if args.format == "json" else html_transcript(view))
        else:
            print(text_transcript(view),end="")
        return 0 if view["status"] in ("ANSWER_READY","PROPOSAL_READY") else 3
    except (LabError,OSError,ValueError) as exc:
        print(json.dumps({"label":LABEL,"status":"ERROR","reason":str(exc),"no_automatic_resubmission":True}),file=sys.stderr)
        return 2
