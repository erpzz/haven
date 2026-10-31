"""End-to-end MCP check: spawn the server over stdio with the official client, list tools, call each one.

    PYTHONPATH=labs/cyber <venv-with-mcp>/bin/python labs/cyber/scripts/mcp_smoke.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def main() -> int:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    params = StdioServerParameters(command=sys.executable, args=["-m", "haven_cyber.mcp_server"], env=env, cwd=str(ROOT))
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = [t.name for t in (await s.list_tools()).tools]
            print("tools:", tools)

            async def call(name, args):
                res = await s.call_tool(name, args)
                return json.loads(res.content[0].text)

            hits = await call("cyber_search", {"query": "block legacy authentication conditional access", "domain": "entra"})
            print("search:", [h["ref"] for h in hits["result"]["hits"]])
            caps = await call("cyber_capabilities", {})
            print("capabilities:", [(c["id"], c["available"]) for c in caps])
            desc = await call("cyber_describe", {"tool_id": "entra.ca.assess"})
            print("describe:", desc["id"], desc["scope"], desc["read_only"])
            out = await call("cyber_call", {"tool_id": "entra.ca.assess", "arguments": {"snapshot_path": "fixtures/tenants/contoso-weak.json"}})
            fails = [f["source_check_id"] for f in out["result"]["findings"] if f["status"] == "fail"]
            print("assess fails:", fails)
            bad = await call("cyber_call", {"tool_id": "entra.ca.assess", "arguments": {"snapshot_path": "/etc/passwd"}})
            print("scope guard:", bad["error"]["code"])
            live = await call("cyber_call", {"tool_id": "entra.graph.collect", "arguments": {"emergency_account_ids": []}})
            print("live gate:", live["error"]["code"])
            ok = (set(tools) == {"cyber_search", "cyber_capabilities", "cyber_describe", "cyber_call"} and hits["ok"]
                  and "HCA-001" in fails and bad["error"]["code"] == "path_out_of_scope" and live["error"]["code"] == "prerequisite_failed")
            print("MCP SMOKE", "PASS" if ok else "FAIL")
            return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
