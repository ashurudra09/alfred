"""Tools for the agent: the Alfred MCP server over stdio (the real thing), or the same functions in-process (tests).

Both expose `.specs` (tool name -> {schema, needs_confirmation}) and `.call(name, args) -> (text, is_error)`.
"""

import asyncio
import os
import sys
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError


class McpTools:
    """Starts `python -m alfred.tools.server` and talks MCP to it from a background event loop."""

    def __init__(self, env: dict | None = None):
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()
        self._ready, self._stop = threading.Event(), None
        self._session, self._error = None, None
        params = StdioServerParameters(command=sys.executable, args=["-m", "alfred.tools.server"],
                                       env={**os.environ, **(env or {})})
        asyncio.run_coroutine_threadsafe(self._run(params), self._loop)
        if not self._ready.wait(60) or self._error:
            raise RuntimeError(f"tool server didn't start: {self._error}")

    async def _run(self, params):
        try:
            self._stop = asyncio.Event()
            async with stdio_client(params) as (read, write), ClientSession(read, write) as s:
                await s.initialize()
                tools = (await s.list_tools()).tools
                self.specs = {t.name: {"schema": t.inputSchema,
                                       "needs_confirmation": bool((t.meta or {}).get("alfred/needs_confirmation"))}
                              for t in tools}
                self._session = s
                self._ready.set()
                await self._stop.wait()
        except Exception as e:
            self._error = e
            self._ready.set()

    def call(self, name: str, args: dict) -> tuple[str, bool]:
        fut = asyncio.run_coroutine_threadsafe(self._session.call_tool(name, args), self._loop)
        r = fut.result(timeout=120)
        text = "\n".join(c.text for c in r.content if getattr(c, "text", None))
        return text, bool(r.isError)

    def close(self):
        if self._stop:
            self._loop.call_soon_threadsafe(self._stop.set)


class LocalTools:
    """The same tools called in-process (unit tests and quick runs). Same validation as the server: none here,
    the agent validates arguments against the schema before calling."""

    def __init__(self):
        from alfred.contracts.export import load
        from alfred.tools.server import IMPLS
        self._impls = IMPLS
        self.specs = {t["name"]: {"schema": t["inputSchema"],
                                  "needs_confirmation": t["_meta"]["alfred/needs_confirmation"]}
                      for t in load()["tools"]}

    def call(self, name: str, args: dict) -> tuple[str, bool]:
        try:
            return str(self._impls[name](**args)), False
        except ToolError as e:
            return str(e), True
        except Exception as e:
            return f"Error executing tool {name}: {e}", True

    def close(self):
        pass
