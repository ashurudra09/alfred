"""Alfred's MCP server over stdio: the 25 tools, each registered under its frozen contract (signature, docstring,
annotations, meta), so `list_tools` equals contracts/tools.json.

Run: uv run python -m alfred.tools.server     (Claude Desktop / MCP Inspector: the same command)
"""

import functools
import threading

from mcp.server.fastmcp import FastMCP

from alfred.contracts.export import tool_options
from alfred.contracts.tools import REGISTRY
from alfred.tools import calc, dev, files, memory, productivity, system

IMPLS = {name: getattr(mod, name) for mod in (files, system, dev, productivity, memory, calc)
         for name in REGISTRY if hasattr(mod, name)}
assert set(IMPLS) == set(REGISTRY), f"missing implementations: {set(REGISTRY) - set(IMPLS)}"


def bound(name: str):
    """The implementation, presented with the contract's signature and annotations (functools.wraps)."""
    @functools.wraps(REGISTRY[name]["fn"])
    def tool(**kwargs):
        return IMPLS[name](**kwargs)
    return tool


def build() -> FastMCP:
    mcp = FastMCP("alfred")
    for name in REGISTRY:
        mcp.add_tool(bound(name), **tool_options(name))
    return mcp


def main():
    threading.Thread(target=productivity.reminder_loop, daemon=True).start()
    build().run("stdio")


if __name__ == "__main__":
    main()
