#!/usr/bin/env python3
"""Smoke test for the Haven operator MCP server.

  python3 scripts/smoke.py          offline: the operate surface over MCP framing against a fake Slink
  python3 scripts/smoke.py --live   spawns the real server in observe mode and makes read-only calls only

Prints MCP SMOKE PASS or FAIL and exits 0 or 1.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))


def frames(*msgs):
    return "\n".join(json.dumps(m) for m in msgs) + "\n"


def call(i, name, args=None):
    return {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args or {}}}


def parse(text):
    out = {}
    for line in text.splitlines():
        m = json.loads(line)
        if "id" in m:
            r = m.get("result") or {}
            out[m["id"]] = json.loads(r["content"][0]["text"]) if "content" in r else r or m.get("error")
    return out


def offline():
    tmp = Path(tempfile.mkdtemp(prefix="haven-hermes-smoke-"))
    os.environ.update(HAVEN_ENGINEER_STATE=str(tmp / "state"), HAVEN_ENGINEER_CONFIG=str(tmp / "cfg"))
    from haven_hermes.simulated import FakeSlink, gpu
    from haven_hermes import server
    from haven_hermes.mcp_stdio import Server
    results = []
    for label, fake in (("free", FakeSlink()), ("busy", FakeSlink(gpu_state=gpu(peers=["peer.service"])))):
        reg = server.build("operate", slink=fake, settings={}, state=tmp / label)
        out = io.StringIO()
        Server(reg, name="haven", version="smoke", instructions="", out=out).serve(io.StringIO(frames(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            call(3, "haven_status"), call(4, "haven_model_use", {"model": "qwen35-4b"}), call(5, "haven_receipts"))))
        results.append(parse(out.getvalue()))
    free, busy = results
    names = {t["name"]: t for t in free[2]["tools"]}
    checks = {
        "operate exposes change tools with readOnlyHint false": names["haven_model_use"]["annotations"]["readOnlyHint"] is False,
        "reads are marked read-only": names["haven_status"]["annotations"]["readOnlyHint"] is True,
        "status answers": free[3]["ok"] and free[3]["slink"]["host"] == "slink",
        "load succeeds with a receipt": free[4]["status"] == "succeeded" and free[4]["receipt"].startswith("R-"),
        "ledger verifies": free[5]["verified"] is True,
        "busy GPU is refused, not interrupted": busy[4]["status"] == "refused" and busy[4]["error"]["code"] == "gpu_busy",
    }
    return checks


def live():
    env = {**os.environ, "PYTHONPATH": str(LAB)}
    p = subprocess.run([sys.executable, "-m", "haven_hermes.server", "--mode", "observe"], cwd=LAB, env=env,
                       input=frames({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                                    call(3, "haven_status"), call(4, "haven_gpu"), call(5, "haven_models"),
                                    call(6, "haven_model_use", {"model": "qwen35-4b"})),
                       capture_output=True, text=True, timeout=180)
    r = parse(p.stdout)
    names = [t["name"] for t in r[2]["tools"]]
    return {
        "observe mode lists no change tools": "haven_model_use" not in names and "haven_status" in names,
        "status reached Slink": r[3].get("ok") and r[3]["slink"].get("host") is not None,
        "gpu holders reported": r[4].get("ok") and "compute_apps" in r[4]["gpu"],
        "models listed": r[5].get("ok") and len(r[5].get("models", [])) > 0,
        "change tool unreachable in observe mode": isinstance(r[6], dict) and r[6].get("code") == -32602,
    }


def main():
    checks = live() if "--live" in sys.argv else offline()
    for name, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + name)
    ok = all(checks.values())
    print("MCP SMOKE " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
