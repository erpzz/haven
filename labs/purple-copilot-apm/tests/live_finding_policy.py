"""Check actual stdio capabilities and authorization before model dispatch."""
import asyncio
import os
import sys
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from apm.finding_mcp import path_evidence
from apm.investigator import check_report, permitted
from apm.path_history import get_run, record_paths
from apm.paths import registry, sample_scan
from apm.samples import ROOT


async def check():
    run = record_paths(sample_scan(registry()["phantom-admins"]))
    _, findings = get_run(run)
    key = next(iter(findings))
    env = {"APM_STATE": str(ROOT), "APM_FINDING_RUN": str(run), "APM_FINDING_ID": key}
    params = StdioServerParameters(command=sys.executable, args=["-m", "apm.finding_mcp"], env=env)
    async with stdio_client(params) as (rx, tx), ClientSession(rx, tx) as session:
        await session.initialize()
        assert {t.name for t in (await session.list_tools()).tools} == {"path_evidence", "collection_quality"}
        for name in ("file_upload", "cypher_query"):
            assert (await session.call_tool(name, {})).isError
    with patch.dict(os.environ, dict(env, APM_FINDING_ID="unknown")), patch("apm.finding_mcp.community_graph") as live:
        try:
            await path_evidence()
        except PermissionError:
            pass
        else:
            raise AssertionError("Cross-finding request accepted")
        live.assert_not_called()
    for name, args in [("path_evidence", '{"run":0}'), ("file_upload", "{}")]:
        try:
            permitted({"tool_calls": [{"type": "function", "id": "test",
                                       "function": {"name": name, "arguments": args}}]})
        except PermissionError:
            pass
        else:
            raise AssertionError("Unauthorized model action accepted")
    try:
        check_report("collection_quality", "[E1] Confidence is limited with a hop count of 2.", {"confidence": "limited"})
    except ValueError:
        pass
    else:
        raise AssertionError("Quality report included unsupported topology")
    print("Two-tool inventory and five authorization denials passed")


if __name__ == "__main__":
    asyncio.run(check())
