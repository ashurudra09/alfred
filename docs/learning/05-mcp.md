# MCP: tools as a server

## What it is
The **Model Context Protocol** is an open protocol (from Anthropic, now supported by many clients) for giving a model
access to tools and data. A **server** exposes tools; a **client** (the app that talks to the model) discovers them
and calls them. Messages are JSON-RPC 2.0 over a transport: **stdio** (the client starts the server as a child process
and talks over its stdin/stdout) or HTTP.

The two calls that matter here:
- `tools/list` → each tool's name, description, JSON Schema for its arguments, annotations
  (`readOnlyHint`, `destructiveHint`, …) and a free-form `_meta` field;
- `tools/call(name, arguments)` → a result with text content and an `isError` flag.

The point: tools are written once and any MCP client can use them, whether that's Alfred's own agent, Claude Desktop
or the MCP Inspector.

## How Alfred uses it
- **Frozen contracts → server.** `contracts/tools.py` holds the 25 signatures and docstrings (tag `contracts-v1.0`).
  `tools/server.py` registers each implementation *under its contract* with `functools.wraps`, so the server's
  `tools/list` is byte-for-byte `contracts/tools.json`, the same schemas the model was trained on. A test checks it.
- **Confirmation is metadata, not prose.** Write tools carry `_meta: {"alfred/needs_confirmation": true}`. The agent
  reads that flag from `tools/list`; the model can't talk its way past it.
- **Errors are results.** A guard failure raises `ToolError`, which MCP returns as `isError: true` with a clear
  message ("Refused: … is a sensitive location"); the model sees it and can explain or ask.
- **Instructions on connect.** The server sends known folders, today's date and path conventions in the MCP
  `instructions` field, because clients like Claude Desktop never see Alfred's system prompt (the first Claude
  Desktop test guessed `C:\Users\<someone>` paths without it).
- **Two clients, one server.** `agent/mcp_client.py` runs the server over stdio on a background event loop for the
  CLI and UI; `scripts/add_to_claude_desktop.py` registers the same command with Claude Desktop.

## What happened here
- **The stdin bug:** with stdio, the server's stdin *is* the protocol pipe. Tool subprocesses (git, PowerShell,
  netsh) inherited it: `git status` hung for 20 s and a toast's output could have corrupted the protocol. Every
  subprocess now gets `stdin=DEVNULL`.
- Claude Desktop rewrites its config while running and keeps it in an unexpected folder
  (`%LOCALAPPDATA%\Claude-Data\<id>`); the registration script finds it and edits it only when the app is closed.
- A robustness pass driven by Claude as the client (it phrases arguments differently from our model) found 15
  classes of input the tools mishandled (`"C drive"`, `"My Documents"`, wildcards, extension-less renames, …); all
  fixed with tests.

## Check your understanding
- *Why MCP instead of calling Python functions directly?* One implementation for every client, a standard schema
  format, process isolation (a tool crash doesn't kill the agent), and the server can be tested and inspected alone.
- *stdio vs HTTP?* stdio: local, no port, no auth needed, lifetime tied to the client. HTTP: remote or shared servers,
  needs auth.
- *Where does the confirmation rule live, and why there?* In tool metadata read by the client, not in the prompt: a
  prompt can be ignored or injected, a flag checked in code can't.
- *How do you know the model sees the same tools it was trained on?* `tools/list` is generated from the frozen
  contracts and compared with `tools.json` in a test.

## Where in the code
- `src/alfred/contracts/tools.py`, `export.py`, `tools.json`: the contracts and their JSON export.
- `src/alfred/tools/server.py`: FastMCP server, `bound()` (contract signature), `instructions()`.
- `src/alfred/agent/mcp_client.py`: `McpTools` (stdio client) and `LocalTools` (in-process, for tests).
- `tests/tools/test_server.py`: the stdio round-trip test (`tools/list` = `tools.json`).
