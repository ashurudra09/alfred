"""`alfred-ui`: the minimal local web UI (FR24) over the same `run_turn` events as the CLI.

Chat-history sidebar, streamed answers, a live timer, tool-call cards, Confirm/Cancel for writes, Undo with recent
actions, a Memory tab and a timing footer. Bound to 127.0.0.1; no analytics, no web fonts, no share link.
The UI only consumes `run_turn` events and calls the chats / journal / memory functions.
"""

import os

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")  # offline: no telemetry calls

import time  # noqa: E402
from pathlib import Path  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import gradio as gr  # noqa: E402

from alfred.agent import chats  # noqa: E402
from alfred.agent.cli import current_model, list_models, listener_pid, restart_model  # noqa: E402
from alfred.agent.loop import MAX_CALLS, drive, run_turn  # noqa: E402
from alfred.agent.timing import format_timing  # noqa: E402
from alfred.contracts.export import load as load_contracts  # noqa: E402
from alfred.tools import files, journal, memory  # noqa: E402
from alfred.tools.guards import config, home, save_config  # noqa: E402

THEME = gr.themes.Default(font=["system-ui", "sans-serif"], font_mono=["Consolas", "monospace"])  # no Google Fonts
# ponytail: repo-root assets, so this needs the editable install `uv sync` gives; move under src/ if alfred is ever packaged
ICONS = Path(__file__).resolve().parents[3] / "assets" / "icons"


# What each tool can't do, for the Tools tab (UI text only: the frozen contracts stay as they are).
# {max_results} / {max_scan} / {max_read} / {min_score} come from the Settings tab.
LIMITS = {
    "search_files": "allowed folders only; shows {max_results} results, scans up to {max_scan} files",
    "search_file_contents": "txt, md, pdf, code; allowed folders; scans up to {max_scan} files, reads {max_read} bytes each",
    "list_directory": "allowed folders; first 200 entries; hidden files left out",
    "read_file": "txt, md, pdf, docx; up to 20,000 characters; reads {max_read} bytes of a text file",
    "disk_usage": "any drive; stops after 20 s, so big folders may be estimates",
    "move_file": "allowed folders; never overwrites; main folders refused",
    "rename_file": "allowed folders; never overwrites; name only",
    "copy_file": "files only; never overwrites",
    "zip_folder": "never overwrites",
    "organize_folder": "by type or month; shows the whole plan first; shortcuts and temp files skipped",
    "move_to_recycle_bin": "never permanent; main folders refused",
    "open_path": "refuses programs and scripts",
    "open_app": "installed Start Menu apps and a few built-ins",
    "system_info": "this laptop only",
    "top_processes": "a snapshot, not a monitor",
    "network_status": "checks 1.1.1.1; no speed test",
    "port_in_use": "TCP listeners only",
    "git_status": "read-only; no commit or push",
    "create_note": "saved in Alfred's own notes folder",
    "search_notes": "only notes made with create_note",
    "set_reminder": "only fires while Alfred is running",
    "list_reminders": "upcoming only",
    "remember": "only what you ask it to remember",
    "recall": "top 3 above similarity {min_score}; needs the Ollama embedder, else keyword match",
    "calculate": "arithmetic only; + - * / % ** and sqrt, round, abs",
}


def tool_label(t: dict, cfg: dict) -> str:
    vals = {"max_results": cfg.get("max_results", files.MAX_RESULTS), "max_scan": cfg.get("max_scan", files.MAX_SCAN),
            "max_read": cfg.get("max_read", files.MAX_READ), "min_score": cfg.get("min_score", memory.MIN_SCORE)}
    kind = "read-only" if t["annotations"].get("readOnlyHint") else \
        "asks first, undoable" if t["_meta"]["alfred/needs_confirmation"] else "changes things"
    return f"{t['name']} ({kind}): {t['description']} Limits: {LIMITS.get(t['name'], '-').format(**vals)}."


def tool_groups(tools) -> dict[str, list[dict]]:
    """Connected tools (what the MCP server reports) by group, with the contract's description and flags."""
    out: dict[str, list[dict]] = {}
    for t in load_contracts()["tools"]:
        if t["name"] in tools.specs:
            out.setdefault(t["_meta"]["alfred/group"], []).append(t)
    return out


def card_title(name: str, args: dict, mark: str = "🔧") -> str:
    return f"{mark} {name}(" + ", ".join(f"{k}={v!r}" for k, v in args.items()) + ")"


def history_to_ui(chat_id: int) -> list[dict]:
    """A saved chat as Chatbot messages: text turns, and each tool call as a card holding its result."""
    out, open_cards = [], []
    for m in chats.history(chat_id):
        if m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            if m.content:
                out.append({"role": "assistant", "content": m.content})
            for c in m.tool_calls or []:
                card = {"role": "assistant", "content": "", "metadata": {"title": card_title(c.name, c.arguments, "✓"),
                                                                        "status": "done"}}
                out.append(card)
                open_cards.append(card)
        elif m.role == "tool" and open_cards:
            open_cards.pop(0)["content"] = m.content[:1500]
    return out


def apply(msgs: list[dict], e) -> None:
    """Render one run_turn event into the Chatbot messages."""
    last = msgs[-1] if msgs else None
    plain = last and last["role"] == "assistant" and "metadata" not in last
    if e.kind == "token":
        if plain:
            last["content"] += e.data["text"]
        else:
            msgs.append({"role": "assistant", "content": e.data["text"]})
    elif e.kind == "tool_call_proposed":
        msgs.append({"role": "assistant", "content": "",
                     "metadata": {"title": card_title(e.data["name"], e.data["args"]), "status": "pending"}})
    elif e.kind == "tool_result":
        card = next(m for m in reversed(msgs) if "metadata" in m)
        mark = "✗" if e.data["is_error"] else "–" if e.data["declined"] else "✓"
        card["metadata"] = {"title": card["metadata"]["title"].replace("🔧", mark, 1), "status": "done"}
        card["content"] = e.data["text"][:1500]
    elif e.kind == "retry":
        msgs.append({"role": "assistant", "content": "\n".join(e.data["issues"]),
                     "metadata": {"title": "↻ invalid tool call, retrying", "status": "done"}})
    elif e.kind == "done" and e.data["text"] and not plain:
        msgs.append({"role": "assistant", "content": e.data["text"]})


def action_choices() -> list[tuple[str, int]]:
    return [(f"{a['id']} · {a['ts'][5:16].replace('T', ' ')} · {a['tool']} · {a['dst'] or a['src'] or ''}"
             f"{' (undone)' if a['undone'] else ''}", a["id"]) for a in journal.recent(10)]


def chat_choices() -> list[tuple[str, int]]:
    return [(f"{c['title'][:40] + ('…' if len(c['title']) > 40 else '')} · {c['updated'][5:16].replace('T', ' ')}",
             c["id"]) for c in chats.list_chats()]


def fresh_chat() -> int:
    """The newest chat if it's still empty, else a new one (so restarts don't pile up empty chats)."""
    latest = chats.list_chats()[:1]
    return latest[0]["id"] if latest and latest[0]["messages"] == 0 else chats.new_chat()


def memory_rows() -> list[list]:
    return [[m["id"], m["ts"][:10], m["text"]] for m in memory.all_memories()]


def build(backend, tools, server=None) -> gr.Blocks:
    """`server` is a one-item list holding the llama-server Popen alfred-ui started (None if it's external)."""
    server = server if server is not None else [None]
    # ponytail: one in-process session (a local single-user app); per-browser state if it ever serves more
    S = SimpleNamespace(chat_id=fresh_chat(), gen=None, msgs=[], t0=None, paused=0.0, label="", footer="")

    def finish_pending():
        """Leaving a chat mid-confirmation counts as Cancel (nothing changes) and saves the turn."""
        if S.gen:
            drive(S.gen)
            S.gen, S.t0, S.paused = None, None, 0.0

    with gr.Blocks(title="Alfred", fill_height=True) as app:
        with gr.Sidebar():
            gr.Markdown("### Alfred")
            new_btn = gr.Button("＋ New chat", variant="primary")
            chat_list = gr.Radio(chat_choices(), value=S.chat_id, label="Chats", container=False)
            del_btn = gr.Button("Delete this chat", size="sm", variant="stop")
            with gr.Group(visible=False) as del_confirm:
                gr.Markdown("Delete this chat permanently? Memories are kept.")
                with gr.Row():
                    del_yes = gr.Button("Delete", variant="stop", size="sm")
                    del_no = gr.Button("Keep", size="sm")
        with gr.Tab("Chat"):
            with gr.Row():
                with gr.Column(scale=3):
                    bot = gr.Chatbot(S.msgs, label="Alfred", height="60vh", feedback_options=None, buttons=["copy"],
                                     avatar_images=(None, str(ICONS / "alfred.png")))
                    status = gr.Markdown("")
                    with gr.Group(visible=False) as confirm_box:
                        preview = gr.Code(label="Alfred wants to make this change", language=None, interactive=False)
                        with gr.Row():
                            yes_btn = gr.Button("Confirm", variant="primary")
                            no_btn = gr.Button("Cancel")
                    box = gr.Textbox(placeholder="Ask Alfred… (write actions always ask first)", show_label=False,
                                     submit_btn=True)
                with gr.Column(scale=1, min_width=260):
                    gr.Markdown("#### Recent actions")
                    actions = gr.Dropdown(action_choices(), label="Action to undo (latest by default)",
                                          value=None)
                    undo_btn = gr.Button("↶ Undo")
                    undo_out = gr.Markdown("")
        with gr.Tab("Memory") as mem_tab:
            mems = gr.Dataframe(memory_rows(), headers=["id", "saved", "memory"], interactive=False, wrap=True)
            with gr.Row():
                mem_id = gr.Number(label="Memory id", precision=0)
                forget_btn = gr.Button("Forget", variant="stop")
            mem_out = gr.Markdown("")
        groups = tool_groups(tools)
        with gr.Tab("Tools") as tools_tab:
            gr.Markdown("Untick a tool to stop Alfred using it (applies from your next message). The model was trained "
                        "with all 25 tools, so turning some off can change which tool it picks.")
            cfg0 = config()  # choices are refreshed on tab select (limits follow Settings); set here so values validate
            tool_boxes = {g: gr.CheckboxGroup([(tool_label(t, cfg0), t["name"]) for t in ts], label=g, container=True,
                                              value=[t["name"] for t in ts
                                                     if t["name"] not in cfg0.get("disabled_tools", [])])
                          for g, ts in groups.items()}
            with gr.Row():
                tools_save = gr.Button("Save", variant="primary")
                tools_out = gr.Markdown("")
        with gr.Tab("Settings") as set_tab:
            gr.Markdown("#### Model server")
            server_info = gr.Markdown("")
            with gr.Row():
                model_dd = gr.Dropdown(label="Model", allow_custom_value=True)
                ctx_n = gr.Number(label="Context size (tokens)", precision=0, minimum=1024)
                threads_n = gr.Number(label="CPU threads", precision=0, minimum=1)
            apply_btn = gr.Button("Apply and restart server", variant="stop")
            with gr.Group(visible=False) as restart_confirm:
                restart_msg = gr.Markdown("")
                with gr.Row():
                    restart_yes = gr.Button("Restart", variant="stop", size="sm")
                    restart_no = gr.Button("Keep", size="sm")
            restart_out = gr.Markdown("")
            gr.Markdown("#### Agent (applies from your next message)")
            with gr.Row():
                max_calls_n = gr.Number(label="Max tool calls per request", precision=0, minimum=1)
                context_n = gr.Number(label="Chat history sent to the model (characters)", precision=0, minimum=1000)
                temp_s = gr.Slider(0, 1, step=0.05, label="Temperature")
            gr.Markdown("#### Tool limits")
            with gr.Row():
                results_n = gr.Number(label="Search results shown", precision=0, minimum=1)
                scan_n = gr.Number(label="Max files scanned per search", precision=0, minimum=100)
                read_n = gr.Number(label="Max bytes read from one file", precision=0, minimum=1000)
                score_n = gr.Number(label="Memory match threshold (0-1)", minimum=0, maximum=1)
            folders_df = gr.Dataframe(headers=["name", "path"], column_count=2, type="array", interactive=True,
                                      label="Extra folders Alfred may use (name, full path)")
            with gr.Row():
                save_btn = gr.Button("Save", variant="primary")
                save_out = gr.Markdown("")
        tick = gr.Timer(0.1, active=False)

        turn_outputs = [bot, status, confirm_box, preview, box, tick, actions, chat_list]

        def elapsed() -> str:  # also the 0.1 s tick, so a late tick can't overwrite the waiting message
            if S.paused:
                return "⏸ waiting for you to confirm or cancel"
            return f"⏳ {S.label}… {time.perf_counter() - S.t0:.1f}s" if S.t0 else S.footer

        def view(confirm: str | None = None, running: bool = True) -> dict:
            return {bot: S.msgs, status: elapsed() if running else S.footer, confirm_box: gr.Group(visible=confirm is not None),
                    preview: confirm or "", box: gr.Textbox(interactive=not running),
                    tick: gr.Timer(active=running and confirm is None)}

        def pump(reply=None):
            while True:
                try:
                    e = S.gen.send(reply)
                except StopIteration:
                    S.gen, S.t0 = None, None
                    yield view(running=False) | {actions: gr.Dropdown(action_choices(), value=None),
                                                 chat_list: gr.Radio(chat_choices(), value=S.chat_id)}
                    return
                reply = None
                apply(S.msgs, e)
                S.label = {"tool_call_proposed": f"running {e.data.get('name')}", "tool_result": "thinking",
                           "token": "writing"}.get(e.kind, S.label)
                if e.kind == "timing":
                    S.footer = f"<sub>{format_timing(e.data)}</sub>"
                if e.kind == "confirm_required":
                    S.paused = time.perf_counter()
                    yield view(confirm=e.data["preview"])
                    return  # paused: Confirm/Cancel resumes S.gen
                yield view()

        def send(text):
            if not text.strip() or S.gen:
                yield {box: gr.Textbox()}
                return
            S.msgs.append({"role": "user", "content": text})
            S.gen, S.t0, S.label, S.footer = run_turn(S.chat_id, text, backend, tools), time.perf_counter(), \
                "thinking", ""
            yield view() | {box: gr.Textbox(value="", interactive=False)}
            yield from pump()

        def answer(yes: bool):
            def handler():
                if not S.gen:
                    yield view(running=False)
                    return
                S.label, S.t0, S.paused = "working", S.t0 + time.perf_counter() - S.paused, 0.0  # skip the wait
                yield from pump(yes)
            return handler

        def open_chat(chat_id):
            finish_pending()
            S.chat_id, S.msgs, S.footer = int(chat_id), history_to_ui(int(chat_id)), ""
            return view(running=False) | {chat_list: gr.Radio(chat_choices(), value=S.chat_id),
                                          actions: gr.Dropdown(action_choices(), value=None)}

        def new_chat():
            finish_pending()
            return open_chat(fresh_chat())

        def delete_chat():
            finish_pending()
            chats.delete_chat(S.chat_id)
            rest = chats.list_chats()
            return open_chat(rest[0]["id"] if rest else fresh_chat()) | {del_confirm: gr.Group(visible=False)}

        def undo(action_id):
            msg = journal.undo(int(action_id) if action_id else None)
            return msg, gr.Dropdown(action_choices(), value=None)

        def forget(mid):
            ok = mid is not None and memory.forget(int(mid))
            return memory_rows(), "Forgotten." if ok else f"No memory {mid}."

        def tool_updates():
            cfg = config()
            off = set(cfg.get("disabled_tools", []))
            return {tool_boxes[g]: gr.CheckboxGroup([(tool_label(t, cfg), t["name"]) for t in ts],
                                                     value=[t["name"] for t in ts if t["name"] not in off])
                    for g, ts in groups.items()}

        def save_tools(*enabled):
            on = {n for chosen in enabled for n in chosen}
            off = sorted(t["name"] for ts in groups.values() for t in ts if t["name"] not in on)
            save_config({"disabled_tools": off})
            return f"Saved. {len(off)} tool(s) off: {', '.join(off) or 'none'}."

        settings_fields = [model_dd, ctx_n, threads_n, max_calls_n, context_n, temp_s, results_n, scan_n, read_n,
                           score_n, folders_df]

        def owner(pid) -> str:
            return "started by alfred-ui" if server[0] and server[0].pid == pid else "started outside alfred-ui"

        def server_status() -> str:
            pid = listener_pid()
            if not pid:
                return f"llama-server: not running on :8080. Alfred home: `{home()}`."
            return f"llama-server: running on :8080 (PID {pid}, {owner(pid)}). Alfred home: `{home()}`."

        def load_settings():
            cfg = config()
            return (server_status(), gr.Dropdown([(Path(m).name, m) for m in list_models()], value=current_model()),
                    cfg.get("ctx", 8192), cfg.get("threads", 4), cfg.get("max_calls", MAX_CALLS),
                    cfg.get("context_chars", chats.CONTEXT_CHARS), cfg.get("temperature", 0.0),
                    cfg.get("max_results", files.MAX_RESULTS), cfg.get("max_scan", files.MAX_SCAN),
                    cfg.get("max_read", files.MAX_READ), cfg.get("min_score", memory.MIN_SCORE),
                    [[n, pth] for n, pth in cfg.get("extra_folders", {}).items()] or [["", ""]])

        def save_settings(max_calls, context_chars, temperature, max_results, max_scan, max_read, min_score, folders):
            rows = [(str(n).strip(), str(pth).strip()) for n, pth in folders if str(n).strip() or str(pth).strip()]
            bad = [pth for n, pth in rows if not n or not Path(pth).is_dir()]
            if bad:
                return f"Not saved: every extra folder needs a name and an existing folder ({bad[0] or 'empty path'})."
            save_config({"max_calls": int(max_calls), "context_chars": int(context_chars), "temperature": temperature,
                         "max_results": int(max_results), "max_scan": int(max_scan), "max_read": int(max_read),
                         "min_score": min_score, "extra_folders": dict(rows)})
            return "Saved. Applies from your next message."

        def ask_restart(model, ctx, threads):
            pid = listener_pid()
            what = f"The llama-server on :8080 (PID {pid}, {owner(pid)}) will be stopped, and any other Alfred " \
                   "window using it loses its model until it is back." if pid else "No llama-server is running."
            return gr.Group(visible=True), (f"**Restart the model server?** {what} A new one starts on "
                                            f"`{Path(model).name}` (context {int(ctx)}, {int(threads)} threads). "
                                            "A request in progress is cancelled. This takes up to a minute.")

        def do_restart(model, ctx, threads):
            finish_pending()
            save_config({"model": model, "ctx": int(ctx), "threads": int(threads)})
            proc = restart_model(model)
            if proc:
                server[0] = proc
            return gr.Group(visible=False), ("Restarted on " + Path(model).name if proc else
                                             "llama-server didn't start. Is llama.cpp installed?"), server_status()

        box.submit(send, box, turn_outputs, api_name="send")
        yes_btn.click(answer(True), None, turn_outputs, api_name="confirm")
        no_btn.click(answer(False), None, turn_outputs, api_name="cancel")
        tick.tick(elapsed, None, status,
                  show_progress="hidden", api_visibility="private")
        chat_list.input(open_chat, chat_list, turn_outputs, api_name="open_chat")
        new_btn.click(new_chat, None, turn_outputs, api_name="new_chat")
        del_btn.click(lambda: gr.Group(visible=True), None, del_confirm)
        del_no.click(lambda: gr.Group(visible=False), None, del_confirm)
        del_yes.click(delete_chat, None, turn_outputs + [del_confirm], api_name="delete_chat")
        undo_btn.click(undo, actions, [undo_out, actions], api_name="undo")
        mem_tab.select(memory_rows, None, mems)
        tools_tab.select(tool_updates, None, list(tool_boxes.values()))
        tools_save.click(save_tools, list(tool_boxes.values()), tools_out, api_name="save_tools")
        set_tab.select(load_settings, None, [server_info] + settings_fields)
        save_btn.click(save_settings, [max_calls_n, context_n, temp_s, results_n, scan_n, read_n, score_n, folders_df],
                       save_out, api_name="save_settings")
        apply_btn.click(ask_restart, [model_dd, ctx_n, threads_n], [restart_confirm, restart_msg])
        restart_no.click(lambda: gr.Group(visible=False), None, restart_confirm)
        restart_yes.click(do_restart, [model_dd, ctx_n, threads_n], [restart_confirm, restart_out, server_info],
                          api_name="restart_server")
        forget_btn.click(forget, mem_id, [mems, mem_out], api_name="forget")
    return app


def main():
    import argparse
    import sys

    from alfred.agent.backends import Backend
    from alfred.agent.cli import ensure_model
    from alfred.agent.mcp_client import McpTools

    ap = argparse.ArgumentParser(prog="alfred-ui")
    ap.add_argument("--model", help="GGUF to serve if llama-server isn't running")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # rich's spinner on a cp1252 console
    proc = ensure_model(a.model)
    tools = McpTools()
    server = [proc]
    try:
        build(Backend("local"), tools, server).launch(server_name="127.0.0.1", server_port=a.port, inbrowser=not a.no_browser,
                                              ssr_mode=False, theme=THEME, favicon_path=str(ICONS / "favicon.ico"))
    finally:
        tools.close()
        if server[0]:
            server[0].terminate()


if __name__ == "__main__":
    main()
