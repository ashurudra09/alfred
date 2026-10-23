"""`alfred`: the terminal assistant (FR22, FR25).

Commands: /new  /chats  /open <id>  /delete <id>  /undo [id]  /actions  /memories  /forget <id>  /help  /quit
Starts llama-server on the fine-tuned model if it isn't already running (model: --model, ALFRED_MODEL, or the
"model" key in %LOCALAPPDATA%\\Alfred\\config.json).
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from alfred.agent import chats
from alfred.agent.backends import ROOT, Backend, serve
from alfred.agent.loop import run_turn
from alfred.agent.mcp_client import McpTools
from alfred.agent.timing import format_timing
from alfred.tools import journal, memory
from alfred.tools.guards import home

DEFAULT_MODEL = ROOT / "runs" / "sft_2b_v2" / "alfred-2b-v2-q4.gguf"
HELP = ("/new  /chats  /open <id>  /delete <id>  /undo [id]  /actions  /memories  /forget <id>  /help  /quit\n"
        "Write actions (move, rename, copy, zip, organize, delete) always ask you first; /undo reverses them.")
console = Console()


def server_up(url="http://127.0.0.1:8080/health") -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


def ensure_model(model: str | None):
    if server_up():
        return None
    cfg = home() / "config.json"
    model = model or os.environ.get("ALFRED_MODEL") or \
        (json.loads(cfg.read_text()).get("model") if cfg.exists() else None) or str(DEFAULT_MODEL)
    with console.status(f"Starting llama-server on {Path(model).name}..."):
        proc = serve(model)
        for _ in range(240):
            if server_up():
                return proc
            if proc.poll() is not None:
                break
            time.sleep(0.5)
    console.print("[red]llama-server didn't start.[/] Is llama.cpp installed (winget install ggml.llamacpp)?")
    sys.exit(1)


class Spinner:
    """A status line with elapsed seconds that refreshes ~10x/s while Alfred works."""

    def __init__(self, label="thinking"):
        self.label, self.t0, self.status, self._run = label, time.perf_counter(), None, False

    def start(self, label=None):
        self.label = label or self.label
        self.status, self._run = console.status(f"{self.label}..."), True
        self.status.start()
        threading.Thread(target=self._tick, daemon=True).start()

    def _tick(self):
        while self._run:
            self.status.update(f"{self.label}... {time.perf_counter() - self.t0:.1f}s")
            time.sleep(0.1)

    def stop(self):
        if self._run:
            self._run = False
            self.status.stop()


def one_turn(chat_id, text, backend, tools):
    spin, gen, reply, streaming = Spinner(), run_turn(chat_id, text, backend, tools), None, False
    spin.start()
    while True:
        try:
            e = gen.send(reply)
        except StopIteration:
            break
        reply = None
        if e.kind == "token":
            if not streaming:
                spin.stop()
                console.print("[bold cyan]Alfred:[/] ", end="")
                streaming = True
            console.print(e.data["text"], end="", markup=False, highlight=False)
        elif e.kind == "tool_call_proposed":
            spin.stop()
            args = ", ".join(f"{k}={v!r}" for k, v in e.data["args"].items())
            console.print(f"[dim]→ {e.data['name']}({args})[/]", highlight=False)
            spin.start(f"running {e.data['name']}")
        elif e.kind == "confirm_required":
            spin.stop()
            console.print(Panel(e.data["preview"], title="Confirm", border_style="yellow"), highlight=False)
            reply = console.input("Do it? [y/N] ").strip().lower() in ("y", "yes")
            spin.start("working")
        elif e.kind == "tool_result":
            spin.stop()
            first = e.data["text"].splitlines()[0] if e.data["text"] else ""
            style = "red" if e.data["is_error"] else "yellow" if e.data["declined"] else "green"
            console.print(f"[{style}]  {'✗' if e.data['is_error'] else '–' if e.data['declined'] else '✓'} "
                          f"{first[:150]}[/]", highlight=False)
            spin.start("thinking")
        elif e.kind == "retry":
            console.print(f"[dim]  (invalid call, retrying: {e.data['issues'][0][:100]})[/]", highlight=False)
        elif e.kind == "error":
            spin.stop()
            console.print(f"[red]  error: {e.data['message'][:200]}[/]", highlight=False)
        elif e.kind == "timing":
            spin.stop()
            if streaming:
                console.print()
            console.print(f"[dim]  {format_timing(e.data)}[/]")
        elif e.kind == "done" and not streaming and e.data["text"]:
            console.print(f"[bold cyan]Alfred:[/] {e.data['text']}", highlight=False)
    spin.stop()


def command(line: str, chat_id: int) -> int | None:
    """Handle a /command. Returns the (possibly new) chat id, or None to quit."""
    cmd, _, arg = line.partition(" ")
    arg = arg.strip()
    if cmd in ("/quit", "/exit"):
        return None
    if cmd == "/help":
        console.print(HELP, markup=False)
    elif cmd == "/new":
        chat_id = chats.new_chat()
        console.print(f"New chat {chat_id}.")
    elif cmd == "/chats":
        for c in chats.list_chats()[:20]:
            console.print(f"{'*' if c['id'] == chat_id else ' '} {c['id']:>3}  {c['updated'][:16]}  {c['title']}",
                          highlight=False)
    elif cmd == "/open" and arg.isdigit() and chats.exists(int(arg)):
        chat_id = int(arg)
        for m in chats.history(chat_id)[-10:]:
            if m.role in ("user", "assistant") and m.content:
                console.print(f"[bold]{'You' if m.role == 'user' else 'Alfred'}:[/] {m.content}", highlight=False)
        console.print(f"[dim]Continuing chat {chat_id}.[/]")
    elif cmd == "/delete" and arg.isdigit() and chats.exists(int(arg)):
        if console.input(f"Delete chat {arg} permanently? Memories are kept. [y/N] ").strip().lower() == "y":
            chats.delete_chat(int(arg))
            console.print(f"Deleted chat {arg}.")
            if int(arg) == chat_id:
                chat_id = chats.new_chat()
    elif cmd == "/undo":
        console.print(journal.undo(int(arg) if arg.isdigit() else None))
    elif cmd == "/actions":
        for a in journal.recent(10):
            console.print(f"{a['id']:>4}  {a['ts'][:16]}  {a['tool']:<20} {a['dst'] or a['src'] or ''}"
                          f"{'  (undone)' if a['undone'] else ''}", highlight=False)
    elif cmd == "/memories":
        for m in memory.all_memories():
            console.print(f"{m['id']:>4}  {m['ts'][:10]}  {m['text']}", highlight=False)
    elif cmd == "/forget" and arg.isdigit():
        console.print("Forgotten." if memory.forget(int(arg)) else f"No memory {arg}.")
    else:
        console.print(f"Unknown command or missing id. {HELP}", markup=False)
    return chat_id


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="alfred")
    ap.add_argument("--model", help="GGUF to serve if llama-server isn't running")
    ap.add_argument("--chat", type=int, help="continue this chat id")
    a = ap.parse_args()
    proc = ensure_model(a.model)
    with console.status("Starting tools..."):
        tools = McpTools()
    backend = Backend("local")
    chat_id = a.chat if a.chat and chats.exists(a.chat) else chats.new_chat()
    console.print(f"[bold]Alfred[/] (chat {chat_id}).")
    console.print(HELP, markup=False)
    try:
        while True:
            try:
                line = console.input("[bold green]You:[/] ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            if line.startswith("/"):
                chat_id = command(line, chat_id)
                if chat_id is None:
                    break
                continue
            one_turn(chat_id, line, backend, tools)
    finally:
        tools.close()
        if proc:
            proc.terminate()


if __name__ == "__main__":
    main()
