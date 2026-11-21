"""Run with the pinned community virtualenv after seed, from the lab directory."""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check():
    params = StdioServerParameters(command=sys.executable, args=["-m", "apm.mcp_reader"],
                                   env={"APM_STATE": os.environ["APM_STATE"]})
    async with stdio_client(params) as (rx, tx), ClientSession(rx, tx) as client:
        await client.initialize()
        assert [t.name for t in (await client.list_tools()).tools] == ["review_memberships"]
        for tool, arguments in [("file_upload", {}), ("review_memberships", {"scope": "write"})]:
            assert (await client.call_tool(tool, arguments)).isError
        for scope, count in [("ad", 12), ("entra", 1)]:
            result = await client.call_tool("review_memberships", {"scope": scope})
            assert not result.isError and len(json.loads(result.content[0].text)["edges"]) == count
        print("MCP tool inventory, two denials and both sample graph reads passed")


if __name__ == "__main__":
    asyncio.run(check())
