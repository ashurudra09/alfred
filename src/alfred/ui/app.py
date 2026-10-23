"""`alfred-ui`: the minimal local web UI (FR24) over the same `run_turn` events as the CLI.

Chat-history sidebar, streamed answers, a live timer, tool-call cards, Confirm/Cancel for writes, Undo with recent
actions, a Memory tab and a timing footer. Bound to 127.0.0.1; no analytics, no web fonts, no share link.
The UI only consumes `run_turn` events and calls the chats / journal / memory functions.
"""

import os

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")  # offline: no telemetry calls

import time  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import gradio as gr  # noqa: E402

from alfred.agent import chats  # noqa: E402
from alfred.agent.loop import drive, run_turn  # noqa: E402
from alfred.agent.timing import format_timing  # noqa: E402
from alfred.tools import journal, memory  # noqa: E402

THEME = gr.themes.Default(font=["system-ui", "sans-serif"], font_mono=["Consolas", "monospace"])  # no Google Fonts


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


def build(backend, tools) -> gr.Blocks:
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
                    bot = gr.Chatbot(S.msgs, label="Alfred", height="60vh", feedback_options=None, buttons=["copy"])
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
    try:
        build(Backend("local"), tools).launch(server_name="127.0.0.1", server_port=a.port, inbrowser=not a.no_browser,
                                              ssr_mode=False, theme=THEME)
    finally:
        tools.close()
        if proc:
            proc.terminate()


if __name__ == "__main__":
    main()
