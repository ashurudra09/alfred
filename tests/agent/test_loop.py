import json

import pytest

from alfred.agent import chats, loop, timing
from alfred.agent.backends import RawCall, Result
from alfred.agent.loop import DECLINED, drive, run_turn
from alfred.agent.mcp_client import LocalTools
from alfred.tools import journal, memory
from tests.conftest import snapshot


class FakeBackend:
    """Replays scripted results; records the messages each model call received."""
    model = "fake"

    def __init__(self, *script):
        self.script, self.seen = list(script), []

    def stream(self, messages, tools=None, temperature=0.0):
        self.seen.append(messages)
        res = self.script.pop(0)
        if res.content:
            yield "token", res.content
        yield "done", res


def call(name, **args):
    return Result(tool_calls=[RawCall(name, args, json.dumps(args))], ttft=0.1, total=0.2, completion_tokens=10)


def say(text):
    return Result(content=text, ttft=0.1, total=0.3, completion_tokens=8)


@pytest.fixture
def env(sandbox, monkeypatch, tmp_path):
    monkeypatch.setattr(timing, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(loop, "log_turn", lambda rec: timing.log_turn(rec, tmp_path / "logs"))
    return {**sandbox, "tools": LocalTools(), "chat": chats.new_chat(), "logs": tmp_path / "logs"}


def kinds(events):
    return [e.kind for e in events]


def test_read_tool_turn(env):
    b = FakeBackend(call("list_directory", path="Downloads"), say("You have 5 files and a photos folder."))
    events = drive(run_turn(env["chat"], "what's in downloads?", b, env["tools"]))
    assert kinds(events) == ["tool_call_proposed", "tool_result", "token", "timing", "done"]
    assert events[-1].data["text"] == "You have 5 files and a photos folder."
    tool_msg = b.seen[1][-1]
    assert tool_msg["role"] == "tool" and tool_msg["content"].startswith('<tool_output untrusted="true">')
    assert "notes.txt" in tool_msg["content"]
    t = events[-2].data
    assert t["total"] > 0 and t["tools"][0]["tool"] == "list_directory" and t["tok_per_s"]
    log = (env["logs"] / next(env["logs"].iterdir()).name).read_text(encoding="utf-8")
    assert '"request": "what\'s in downloads?"' in log


def test_denied_write_changes_nothing(env):
    before = snapshot(env["Documents"], env["Downloads"])
    b = FakeBackend(call("move_file", source="Downloads\\notes.txt", destination="Documents"), say("OK, nothing moved."))
    events = drive(run_turn(env["chat"], "move notes to documents", b, env["tools"]), confirm=lambda d: False)
    confirm = next(e for e in events if e.kind == "confirm_required")
    assert "Move" in confirm.data["preview"] and "notes.txt" in confirm.data["preview"]
    result = next(e for e in events if e.kind == "tool_result")
    assert result.data["declined"] and result.data["text"] == DECLINED
    assert snapshot(env["Documents"], env["Downloads"]) == before and journal.recent() == []


def test_plain_iteration_denies(env):
    before = snapshot(env["Downloads"])
    b = FakeBackend(call("move_to_recycle_bin", path="Downloads\\notes.txt"), say("Not deleted."))
    list(run_turn(env["chat"], "delete notes.txt", b, env["tools"]))  # never sends True
    assert snapshot(env["Downloads"]) == before


def test_approved_write_runs_and_is_journaled(env):
    b = FakeBackend(call("move_file", source="Downloads\\notes.txt", destination="Documents"), say("Moved."))
    drive(run_turn(env["chat"], "move notes", b, env["tools"]), confirm=lambda d: True)
    assert (env["Documents"] / "notes.txt").exists() and journal.recent()[0]["op"] == "move"


def test_preview_error_skips_confirmation(env):
    (env["Documents"] / "notes.txt").write_text("keep")
    b = FakeBackend(call("move_file", source="Downloads\\notes.txt", destination="Documents"), say("It exists."))
    events = drive(run_turn(env["chat"], "move notes", b, env["tools"]), confirm=lambda d: pytest.fail("asked"))
    result = next(e for e in events if e.kind == "tool_result")
    assert result.data["is_error"] and "already exists" in result.data["text"]


def test_invalid_call_gets_one_retry(env):
    b = FakeBackend(call("port_in_use", port=70000), call("port_in_use", port=3000), say("Nothing on 3000."))
    events = drive(run_turn(env["chat"], "port 3000?", b, env["tools"]))
    assert kinds(events)[:3] == ["retry", "tool_call_proposed", "tool_result"]
    assert "Invalid arguments" in b.seen[1][-1]["content"]  # the model saw why


def test_second_invalid_call_gives_up(env):
    b = FakeBackend(call("nope"), call("still_nope"))
    events = drive(run_turn(env["chat"], "x", b, env["tools"]))
    assert "error" in kinds(events) and "couldn't make a valid tool call" in events[-1].data["text"]
    assert not any(e.kind == "tool_result" for e in events)


def test_three_call_cap(env):
    b = FakeBackend(*[call("system_info") for _ in range(4)], say("unused"))
    events = drive(run_turn(env["chat"], "loop forever", b, env["tools"]))
    assert sum(e.kind == "tool_result" for e in events) == 3
    assert "stopped after 3 tool calls" in events[-1].data["text"]


def test_backend_error_is_reported(env):
    b = FakeBackend(Result(error="APIConnectionError: connection refused"))
    events = drive(run_turn(env["chat"], "hi", b, env["tools"]))
    assert events[0].kind == "error" and "llama-server" in events[-1].data["text"]


def test_chat_continue_and_delete_keep_memories(env, monkeypatch):
    monkeypatch.setattr(memory, "embed", lambda t: None)
    drive(run_turn(env["chat"], "remember my resume is in D:\\docs\\resume",
                   FakeBackend(call("remember", fact="Resume folder is D:\\docs\\resume"), say("Saved.")), env["tools"]))
    b = FakeBackend(say("It's in D:\\docs\\resume."))
    drive(run_turn(env["chat"], "where's my resume?", b, env["tools"]))
    sent = [m["content"] for m in b.seen[0] if m["role"] == "user"]
    assert sent == ["remember my resume is in D:\\docs\\resume", "where's my resume?"]  # history continued
    assert chats.list_chats()[0]["title"].startswith("remember my resume")
    assert chats.delete_chat(env["chat"]) and not chats.exists(env["chat"])
    assert memory.all_memories()[0]["text"] == "Resume folder is D:\\docs\\resume"  # FR19


def test_context_budget_keeps_whole_recent_turns(env):
    from alfred.contracts.schemas import Message
    for i in range(30):
        chats.append(env["chat"], [Message(role="user", content=f"q{i} " + "x" * 900),
                                   Message(role="assistant", content="a" * 900)])
    ctx = chats.context(env["chat"])
    assert ctx[0].role == "user" and ctx[-1].role == "assistant"
    assert 2 <= len(ctx) < 60 and ctx[-2].content.startswith("q29")
    assert len(chats.history(env["chat"])) == 60  # older turns stay in storage
