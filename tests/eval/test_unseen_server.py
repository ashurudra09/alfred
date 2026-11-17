"""Track 4F: the held-out tools as a second MCP server next to Alfred's own (F1, F2)."""
import sys

from alfred.agent.loop import other_tools
from alfred.agent.mcp_client import McpTools
from alfred.contracts.export import load, openai_tools
from eval.unseen import server as unseen
from eval.unseen.specs import HELD_OUT
from eval.unseen.specs import openai_tools as held_out_tools

UNSEEN = {"unseen": {"command": sys.executable, "args": ["-m", "eval.unseen.server"]}}


def test_two_servers(sandbox):
    env = {"ALFRED_HOME": str(sandbox["home"])}
    tools = McpTools(env, servers=UNSEEN | {"broken": {"command": sys.executable, "args": ["-c", "pass"]}})
    try:
        own = {n: s for n, s in tools.specs.items() if not s.get("server")}
        assert list(own) == [t["name"] for t in load()["tools"]]  # Alfred's own tools unchanged and first
        assert openai_tools({"tools": [{"name": n, "description": s["description"], "inputSchema": s["schema"]}
                                       for n, s in own.items()]}) == openai_tools(load())
        assert other_tools(tools.specs) == held_out_tools()  # listed with exactly the frozen schemas
        confirm = {n for n, s in tools.specs.items() if s.get("server") and s["needs_confirmation"]}
        assert confirm == {t["function"]["name"] for t in HELD_OUT if not t["read_only"]}
        assert "broken" in tools.skipped and "unseen" not in tools.skipped
        assert tools.call("convertUnits", {"value": 10, "from_unit": "mi", "to_unit": "km"}) == ("10 mi = 16.0934 km", False)
        assert tools.call("calculate", {"expression": "2 + 3"}) == ("5", False)  # Alfred's own server still answers
        text, err = tools.call("todo_done", {"number": 4})
        assert err and "no to-do item 4" in text
    finally:
        tools.close()


def test_held_out_implementations(sandbox, monkeypatch):
    monkeypatch.setenv("ALFRED_HOME", str(sandbox["home"]))
    assert unseen.convertUnits(212, "F", "C") == "212 F = 100 C"
    assert unseen.colorConvert("#1e90ff", "rgb") == "rgb(30, 144, 255)"
    assert unseen.colorConvert("rgb(30, 144, 255)", "hsl") == "hsl(210, 100%, 56%)"
    assert unseen.clipboard_get() == "The clipboard is empty." and "5 characters" in unseen.clipboard_set("hello")
    assert unseen.clipboard_get() == "hello"
    unseen.todo_add("call the bank", "high")
    unseen.todo_add("water plants")
    unseen.todo_done(1)
    assert unseen.todo_list() == "2. [ ] water plants (normal)" and "1. [x]" in unseen.todo_list("all")
    note = sandbox["Downloads"] / "notes.txt"
    assert unseen.countWords("Downloads/notes.txt").endswith(f"{len(note.read_text(encoding='utf-8'))} characters")
    assert unseen.hashFile("Downloads/notes.txt", "md5").startswith("md5 ")
    assert unseen.files_differ("Downloads/notes.txt", "Downloads/notes.txt") == "The files are identical."
