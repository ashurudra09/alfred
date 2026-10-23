from alfred.agent import chats, cli
from alfred.contracts.schemas import Message
from alfred.tools import files, memory


def test_slash_commands(sandbox, monkeypatch, capsys):
    monkeypatch.setattr(memory, "embed", lambda t: None)
    a = chats.new_chat()
    chats.append(a, [Message(role="user", content="hello there"), Message(role="assistant", content="Hi!")])
    b = cli.command("/new", a)
    assert b != a and chats.exists(b)
    assert cli.command("/open " + str(a), b) == a
    cli.command("/chats", a)
    files.move_file("Downloads\\notes.txt", "Documents")
    cli.command("/actions", a)
    cli.command("/undo", a)
    assert (sandbox["Downloads"] / "notes.txt").exists()
    memory.remember("Resume folder is D:\\docs\\resume")
    cli.command("/memories", a)
    cli.command("/forget 1", a)
    assert memory.all_memories() == []
    monkeypatch.setattr(cli.console, "input", lambda prompt: "y")
    assert cli.command(f"/delete {a}", a) != a and not chats.exists(a)
    assert cli.command("/quit", b) is None
    out = capsys.readouterr().out
    assert "hello there" in out and "move_file" in out and "Moved" in out and "Resume folder" in out
