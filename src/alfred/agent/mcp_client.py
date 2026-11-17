"""Tools for the agent: the Alfred MCP server over stdio (the real thing), or the same functions in-process (tests).

Both expose `.specs` (tool name -> {schema, description, needs_confirmation[, server]}) and
`.call(name, args) -> (text, is_error)`. `server` is set only for tools from another MCP server (config.json
"mcp_servers", track 4F step F1).
"""

import asyncio
import os
import sys
import threading
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError


class McpTools:
    """Starts `python -m alfred.tools.server`, plus the servers in `servers` ({name: {"command", "args"[, "env"]}},
    by default config.json's "mcp_servers"), and talks MCP to them from a background event loop.

    Alfred's own tools come first: a tool of another server with the same name is left out. Another server's tool
    needs confirmation unless it declares itself read-only (readOnlyHint). A server that fails to start is left out
    and named in `.skipped`; Alfred's own server failing is an error."""

    def __init__(self, env: dict | None = None, servers: dict | None = None):
        if servers is None:
            from alfred.tools.guards import config
            servers = config().get("mcp_servers", {})
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()
        self._ready, self._stop = threading.Event(), None
        self._sessions, self._error, self.specs, self.skipped = {}, None, {}, {}
        env = {**os.environ, **(env or {})}
        params = {None: StdioServerParameters(command=sys.executable, args=["-m", "alfred.tools.server"], env=env)}
        params |= {name: StdioServerParameters(command=s["command"], args=s.get("args", []),
                                               env={**env, **s.get("env", {})}) for name, s in servers.items()}
        asyncio.run_coroutine_threadsafe(self._run(params), self._loop)
        if not self._ready.wait(60 + 30 * len(servers)) or self._error:
            raise RuntimeError(f"tool server didn't start: {self._error}")

    async def _connect(self, stack, server, p):
        read, write = await stack.enter_async_context(stdio_client(p))
        s = await stack.enter_async_context(ClientSession(read, write))
        await s.initialize()
        for t in (await s.list_tools()).tools:
            if t.name in self.specs:
                continue
            ro = bool(t.annotations and t.annotations.readOnlyHint)
            confirm = (t.meta or {}).get("alfred/needs_confirmation") if server is None else not ro
            self.specs[t.name] = {"schema": t.inputSchema, "description": t.description or "",
                                  "needs_confirmation": bool(confirm), **({"server": server} if server else {})}
            self._sessions[t.name] = s

    async def _run(self, params):
        try:
            self._stop = asyncio.Event()
            async with AsyncExitStack() as stack:
                for server, p in params.items():
                    if server is None:
                        await self._connect(stack, server, p)
                        continue
                    sub = AsyncExitStack()  # its own stack: a server that fails leaves nothing half-open behind
                    try:
                        async with asyncio.timeout(30):  # same task: the stdio client's scopes must close in it
                            await self._connect(sub, server, p)
                        stack.push_async_callback(sub.aclose)
                    except Exception as e:
                        self.skipped[server] = f"{type(e).__name__}: {e}"
                        await sub.aclose()
                self._ready.set()
                await self._stop.wait()
        except Exception as e:
            self._error = e
            self._ready.set()

    def call(self, name: str, args: dict) -> tuple[str, bool]:
        fut = asyncio.run_coroutine_threadsafe(self._sessions[name].call_tool(name, args), self._loop)
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
        self.specs = {t["name"]: {"schema": t["inputSchema"], "description": t["description"],
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
