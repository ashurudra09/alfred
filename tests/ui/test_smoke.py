"""Phase 8 smoke test: the real Gradio app over a fake model, driven through gradio_client."""

import pytest
from gradio_client import Client

from alfred.agent import loop, timing
from alfred.agent.mcp_client import LocalTools
from alfred.tools import journal
from alfred.ui.app import build
from tests.agent.test_loop import FakeBackend, call, say


def text_of(msg) -> str:
    c = msg["content"]
    return c if isinstance(c, str) else " ".join(p.get("text", "") for p in c if isinstance(p, dict))


@pytest.fixture
def ui(sandbox, monkeypatch, tmp_path):
    monkeypatch.setattr(loop, "log_turn", lambda rec: timing.log_turn(rec, tmp_path / "logs"))
    backend = FakeBackend()
    app = build(backend, LocalTools())
    app.launch(server_name="127.0.0.1", prevent_thread_lock=True, quiet=True, ssr_mode=False)
    yield Client(app.local_url, verbose=False), backend, sandbox
    app.close()


def test_message_gets_reply_and_timing(ui):
    client, backend, _ = ui
    backend.script += [call("list_directory", path="Downloads"), say("You have 5 files.")]
    bot, status, *_ = client.predict("what's in downloads?", api_name="/send")
    assert text_of(bot[0]) == "what's in downloads?"
    assert "list_directory" in bot[1]["metadata"]["title"] and "notes.txt" in text_of(bot[1])
    assert text_of(bot[-1]) == "You have 5 files."
    assert "total" in status and "list_directory" in status


def test_cancel_changes_nothing_confirm_moves_and_undo(ui):
    client, backend, sb = ui
    move = call("move_file", source="Downloads\\notes.txt", destination="Documents")
    backend.script += [move, say("Okay, nothing moved."), move, say("Moved.")]
    out = client.predict("move notes to documents", api_name="/send")
    assert "Move" in str(out) and "notes.txt" in str(out)  # the preview shown next to Confirm/Cancel
    client.predict(api_name="/cancel")
    assert (sb["Downloads"] / "notes.txt").exists() and journal.recent() == []

    client.predict("move notes to documents", api_name="/send")
    bot, *_ = client.predict(api_name="/confirm")
    assert (sb["Documents"] / "notes.txt").exists() and text_of(bot[-1]) == "Moved."
    msg, _ = client.predict(None, api_name="/undo")
    assert (sb["Downloads"] / "notes.txt").exists(), msg
