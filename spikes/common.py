"""Shared bits for the Phase 1 spikes: 25 dummy tool schemas (shaped like requirements Section 5) and an Ollama client.

Throwaway: Phase 2 replaces these schemas with the frozen contracts.
"""

import json
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen3.5:2b"

S, I = {"type": "string"}, {"type": "integer"}


def tool(fn_name, desc, required=(), **props):
    return {"type": "function", "function": {"name": fn_name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": list(required)}}}


TOOLS = [
    tool("search_files", "Find files by name in a folder.", ["query", "folder"], query=S, folder=S, extension=S, modified_within_days=I),
    tool("search_file_contents", "Find files whose text contains a phrase.", ["text", "folder"], text=S, folder=S, extension=S),
    tool("list_directory", "List a folder's contents.", ["path"], path=S),
    tool("read_file", "Read a txt, md or pdf file's text.", ["path"], path=S, max_chars=I),
    tool("disk_usage", "Show the largest items under a path.", ["path"], path=S, top_n=I),
    tool("move_file", "Move a file. Never overwrites. Needs confirmation.", ["source", "destination"], source=S, destination=S),
    tool("rename_file", "Rename a file. Needs confirmation.", ["path", "new_name"], path=S, new_name=S),
    tool("copy_file", "Copy a file. Never overwrites. Needs confirmation.", ["source", "destination"], source=S, destination=S),
    tool("zip_folder", "Zip a folder. Never overwrites. Needs confirmation.", ["source", "destination"], source=S, destination=S),
    tool("organize_folder", "Sort a folder's files into subfolders. Shows the plan first.", ["path"], path=S,
         strategy={"type": "string", "enum": ["by_type", "by_date"]}),
    tool("move_to_recycle_bin", "Delete a file by moving it to the Recycle Bin. Needs confirmation.", ["path"], path=S),
    tool("open_path", "Open a file or folder in its default app.", ["path"], path=S),
    tool("open_app", "Launch an app from the Start Menu.", ["name"], name=S),
    tool("system_info", "CPU, RAM, battery and OS info."),
    tool("top_processes", "Processes using the most CPU or memory.", ["sort_by"],
         sort_by={"type": "string", "enum": ["cpu", "memory"]}, n=I),
    tool("network_status", "Wi-Fi name, IP and whether online."),
    tool("port_in_use", "Which process is listening on a port.", ["port"], port=I),
    tool("git_status", "Branch, ahead/behind and changed files of a git repo.", ["repo_path"], repo_path=S),
    tool("create_note", "Save a note.", ["title", "content"], title=S, content=S),
    tool("search_notes", "Search saved notes.", ["query"], query=S),
    tool("set_reminder", "Show a Windows notification at a time.", ["text", "time"], text=S, time=S),
    tool("list_reminders", "List pending reminders."),
    tool("remember", "Store a fact about the user for later.", ["fact"], fact=S),
    tool("recall", "Find stored facts relevant to a query.", ["query"], query=S),
    tool("calculate", "Evaluate an arithmetic expression.", ["expression"], expression=S),
]
assert len(TOOLS) == 25

SYSTEM = ("You are Alfred, a helpful assistant on the user's Windows laptop. Use a tool when one fits; "
          "otherwise answer directly. Known folders: Documents=C:\\Users\\asha\\Documents, "
          "Downloads=C:\\Users\\asha\\Downloads, Desktop=C:\\Users\\asha\\Desktop.")


def post(path, body, timeout=600):
    req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def chat(user, tools=TOOLS, model=MODEL):
    """Streamed /api/chat with think=false. Returns (tool_calls, content, stats) with ttft/total in seconds."""
    t0 = time.perf_counter()
    ttft, content, calls, final = None, "", [], {}
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            "tools": tools, "think": False, "stream": True, "options": {"temperature": 0}}
    with post("/api/chat", body) as r:
        for line in r:
            chunk = json.loads(line)
            msg = chunk.get("message", {})
            if ttft is None and (msg.get("content") or msg.get("tool_calls")):
                ttft = time.perf_counter() - t0
            content += msg.get("content", "")
            calls += msg.get("tool_calls", [])
            if chunk.get("done"):
                final = chunk
    stats = {"ttft": ttft, "total": time.perf_counter() - t0, "prompt_tokens": final.get("prompt_eval_count"),
             "load_s": final.get("load_duration", 0) / 1e9, "gen_tokens": final.get("eval_count"),
             "tok_per_s": final.get("eval_count", 0) / max(final.get("eval_duration", 1), 1) * 1e9}
    return calls, content, stats


def unload(model=MODEL):
    post("/api/generate", {"model": model, "keep_alive": 0}).read()
