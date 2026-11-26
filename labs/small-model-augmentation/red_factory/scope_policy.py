#!/usr/bin/env python3
"""Build the host-owned raw-MCP scope policy for guarded Red Factory runs.

The policy is intentionally stable across cases so #206 preflight can bind it
before a suite starts. Per-case fixture state narrows the surface further and
requires the exact current synthetic object before an actual call is logged.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

SMALL = Path(__file__).resolve().parents[1]
if str(SMALL) not in sys.path:
    sys.path.insert(0, str(SMALL))

import tool_scope  # noqa: E402


def build_policy() -> dict:
    policy = {
        "schema": tool_scope.SCHEMA,
        "allowed_tools": ["read_fixture"],
        "max_calls": 1,
        "per_tool_max": {"read_fixture": 1},
        "unique_calls": True,
        "argument_rules": {
            "read_fixture": {
                "allowed_keys": ["object"],
                "required_keys": ["object"],
                # Exact object identity is case state, not suite-global policy.
                # mcp_fixture.py checks fixture["object"] before this gate.
                "exact_values": {},
            }
        },
    }
    errors = tool_scope.validate_policy(policy)
    if errors:
        raise ValueError("invalid Red Factory scope policy: " + ",".join(errors))
    return policy


def write_private(path: Path) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to replace existing policy")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (
        json.dumps(build_policy(), sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Write the guarded Red Factory raw-MCP policy"
    )
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    write_private(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
