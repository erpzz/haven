"""Expose two catalog reads through the pinned private community MCP subprocess."""
import json
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP

from .graph import now, verify_reader
from .policy import authorize
from .samples import ROOT, read, save

server = FastMCP("Purple Copilot read-only reviews")


@server.tool()
async def review_memberships(scope: str) -> dict:
    """Read synthetic group memberships for one approved scope, ad or entra."""
    review = authorize(scope)
    return await community_graph(scope, review.query)


async def community_graph(scope, cypher):
    verify_reader()
    token = read("reader.json")
    upstream = ROOT / "community"
    params = StdioServerParameters(command=str(upstream / ".venv/bin/python"),
                                   args=[str(upstream / "main.py")], cwd=str(upstream),
                                   env={"BLOODHOUND_DOMAIN": "127.0.0.1", "BLOODHOUND_PORT": "8080",
                                        "BLOODHOUND_SCHEME": "http", "BLOODHOUND_TOKEN_ID": token["id"],
                                        "BLOODHOUND_TOKEN_KEY": token["key"], "NO_PROXY": "127.0.0.1"})
    stamp = now()
    audit = {"query": cypher, "scope": scope, "observed": stamp, "status": "started"}
    filename = f"mcp-{stamp}.json"
    save(filename, audit)
    async with stdio_client(params) as (rx, tx), ClientSession(rx, tx, read_timeout_seconds=timedelta(seconds=90)) as client:
        await client.initialize()
        reply = await client.call_tool("cypher_query", {"info_type": "run", "query": cypher,
                                                        "include_properties": False})
        result = json.loads(reply.content[0].text)
        save(filename, dict(audit, status="returned", response=result))
        if reply.isError or result.get("success") is not True or not result.get("has_results"):
            raise RuntimeError("MCP query failed or returned no verifiable graph")
        return result["data"]


if __name__ == "__main__":
    server.run()
