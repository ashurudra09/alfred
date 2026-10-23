import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from alfred.contracts.export import load


async def session_calls(env):
    params = StdioServerParameters(command=sys.executable, args=["-m", "alfred.tools.server"], env=env)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as s:
        await s.initialize()
        tools = (await s.list_tools()).tools
        ok = await s.call_tool("calculate", {"expression": "34999 * 18 / 100"})
        listing = await s.call_tool("list_directory", {"path": "Downloads"})
        refused = await s.call_tool("read_file", {"path": "Documents\\.env"})
        bad_args = await s.call_tool("port_in_use", {"port": 70000})
        return tools, ok, listing, refused, bad_args


def test_server_over_stdio(sandbox):
    env = {**os.environ, "ALFRED_HOME": str(sandbox["home"])}
    tools, ok, listing, refused, bad_args = asyncio.run(session_calls(env))
    ref = {t["name"]: t for t in load()["tools"]}
    assert [t.name for t in tools] == list(ref)
    for t in tools:
        assert t.inputSchema == ref[t.name]["inputSchema"] and t.description == ref[t.name]["description"]
        assert t.meta == ref[t.name]["_meta"]
        assert t.annotations.model_dump(exclude_none=True) == ref[t.name]["annotations"]
    assert not ok.isError and ok.content[0].text == "6299.82"
    assert "notes.txt" in listing.content[0].text
    assert refused.isError and "sensitive" in refused.content[0].text
    assert bad_args.isError
