"""Bounded offline commands. Output goes to stdout except private extraction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .entra import assess, fixture, select_policy
from .forensics import extract, write_private_jsonl
from .knowledge import search
from .router import route_synthetic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("entra", help="Assess a shipped synthetic Entra fixture")
    demo.add_argument("--fixture", choices=("entra-demo", "entra-heldout"), default="entra-demo")
    demo.add_argument("--question", default="Do these Entra Conditional Access policies require MFA?")
    routed = commands.add_parser("route", help="Route one declared synthetic policy question without a model")
    routed.add_argument("--fixture", choices=("entra-demo", "entra-heldout"), default="entra-demo")
    routed.add_argument("--policy-id", required=True)
    routed.add_argument("--question", default="Does this Entra policy require MFA?")
    retrieve = commands.add_parser("search", help="Search reviewed Markdown cards with FTS5/BM25")
    retrieve.add_argument("query")
    forensic = commands.add_parser("extract", help="Extract private session events without model calls")
    forensic.add_argument("session", type=Path)
    forensic.add_argument("--output", type=Path, required=True)
    forensic.add_argument("--trace", type=Path)
    args = parser.parse_args()
    if args.command == "entra":
        result = assess(fixture(args.fixture), args.question)
    elif args.command == "route":
        def execute(values):
            snapshot = select_policy(fixture(values["fixture"]), values["policy_id"])
            return json.dumps(assess(snapshot, values["question"]))
        result = route_synthetic(args.question, args.fixture, args.policy_id, execute)
    elif args.command == "search":
        result = search(args.query)
    else:
        events = extract(args.session, args.trace)
        write_private_jsonl(args.output, events)
        result = {"events": len(events), "results": sum(x["result_index"] is not None for x in events),
                  "training_admitted": 0, "private_output_created": True}
    print(json.dumps(result, indent=2, ensure_ascii=False))
