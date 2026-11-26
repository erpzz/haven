#!/usr/bin/env python3
"""Run exactly one Local Red Factory case through the already-admitted Hermes child.

This module is intentionally tiny. The parent Mac campaign owns policy discovery,
plugin/runtime preflight, and the #127 owned-llama lease. The child only executes
one deterministic HRF case and writes its full private result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from hermes_runner import run_hermes_case
from local_runner import _validate_new_output_path, _write_private_json
from red_factory import make_case


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hermes", type=Path, required=True)
    p.add_argument("--hermes-home", type=Path, required=True)
    p.add_argument("--toolsets", required=True)
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--family", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--max-turns", type=int, default=8)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    _validate_new_output_path(args.out)
    case = make_case(args.family, args.seed)
    result = run_hermes_case(
        hermes=args.hermes,
        hermes_home=args.hermes_home,
        toolsets=args.toolsets,
        backend_base_url=args.base_url,
        model=args.model,
        case=case,
        timeout_seconds=args.timeout,
        max_turns=args.max_turns,
    )
    _write_private_json(args.out, result)
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "case_id": result["case_id"],
        "family": result["family"],
        "result_sha256": result["result_sha256"],
        "out": str(args.out),
    }, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
