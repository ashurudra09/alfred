import re
import socket
import subprocess
from datetime import datetime, timedelta

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from alfred.tools import calc, dev, files, guards, journal, memory, productivity, system
from tests.conftest import snapshot


# --- guards ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("spelling", ["C:\\", "C:", "C", "c", "C drive", "drive C", "c:/", "/", "C:\\\\"])
def test_drive_spellings(sandbox, spelling):
    assert str(guards.expand(spelling)) == "C:\\"


def test_known_folder_names_expand(sandbox):
    assert guards.resolve_safe("Downloads\\notes.txt") == (sandbox["Downloads"] / "notes.txt").resolve()
    assert guards.resolve_safe("downloads/photos") == (sandbox["Downloads"] / "photos").resolve()


@pytest.mark.parametrize("bad", ["outside", "Documents\\.env", "Documents\\.ssh\\id_rsa", "Documents\\.ssh",
                                 "Documents\\vault.kdbx", "relative\\path.txt"])
def test_guard_refuses(sandbox, bad):
    path = str(sandbox["root"] / bad) if bad == "outside" else bad
    with pytest.raises(ToolError):
        guards.resolve_safe(path, must_exist=False)


def test_junction_escape_is_refused(sandbox):
    link = sandbox["Documents"] / "sneaky"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(sandbox["root"] / "outside")], check=True,
                   capture_output=True)
    assert link.exists()
    with pytest.raises(ToolError, match="outside the allowed"):
        files.read_file("Documents\\sneaky\\x.txt")


def test_sensitive_files_hidden_from_listing_and_search(sandbox):
    out = files.list_directory("Documents")
    assert ".env" not in out and ".ssh" not in out and "resume" in out
    assert "No matching" in files.search_file_contents("API_KEY", "Documents")


def test_hidden_files_left_out(sandbox):
    ini = sandbox["Documents"] / "desktop.ini"
    ini.write_text("[.ShellClassInfo]")
    subprocess.run(["attrib", "+h", "+s", str(ini)], check=True)
    assert "desktop.ini" not in files.list_directory("Documents")
    assert "No matching" in files.search_files("desktop", "Documents")


def test_executables_refused(sandbox, monkeypatch):
    monkeypatch.setattr("os.startfile", lambda p: pytest.fail("must not open"))
    with pytest.raises(ToolError, match="program or script"):
        files.open_path("Downloads\\setup.exe")


def test_open_path_opens_documents(sandbox, monkeypatch):
    opened = []
    monkeypatch.setattr("os.startfile", opened.append)
    assert "Opened" in files.open_path("Downloads\\notes.txt")
    assert opened == [str((sandbox["Downloads"] / "notes.txt").resolve())]


# --- read tools ----------------------------------------------------------------------------------------------------

def test_search_files(sandbox):
    out = files.search_files("transformer", "Downloads", extension="pdf")
    assert out.startswith("1 file:") and "attention_transformer.pdf" in out
    assert "a.jpg" in files.search_files("a", "Downloads", extension="jpg")
    assert "No matching" in files.search_files("transformer", "Downloads", extension="docx")
    assert "attention" in files.search_files("attention", "Downloads", modified_within_days=1)
    with pytest.raises(ToolError):
        files.search_files("x", "C:\\Windows")


def test_search_files_without_folder_searches_all_known_folders(sandbox):
    (sandbox["Documents"] / "attention_summary.txt").write_text("x")
    out = files.search_files("attention")
    assert out.startswith("2 files:") and "Downloads" in out and "Documents" in out
    assert files.search_files("*", extension="jpg").startswith("2 files:")
    assert "No matching" in files.search_files("no_such_name")


def test_search_file_contents(sandbox):
    out = files.search_file_contents("low-rank", "Downloads")
    assert "notes.txt" in out and "low-rank adapters" in out


def test_list_and_read(sandbox):
    out = files.list_directory("Downloads")
    assert out.splitlines()[1] == "photos\\ (folder)" and "notes.txt" in out
    assert "LoRA adds" in files.read_file("Downloads\\notes.txt")
    assert "more chars" in files.read_file("Downloads\\notes.txt", max_chars=5)
    with pytest.raises(ToolError, match="Can't read"):
        files.read_file("Downloads\\budget.xlsx")
    with pytest.raises(ToolError, match="Not found"):
        files.read_file("Downloads\\missing.txt")


def test_disk_usage(sandbox):
    out = files.disk_usage("Downloads", top_n=2)
    assert "free of" in out and len(out.split("Largest:\n")[1].splitlines()) == 2


# --- write tools: no overwrite, and every one undoes back to the same files -----------------------------------------

def roundtrip(sandbox, action, check):
    before = snapshot(sandbox["Documents"], sandbox["Downloads"], sandbox["Desktop"])
    out = action()
    assert "Undo: /undo" in out
    check()
    msg = journal.undo()
    assert "Couldn't" not in msg and "Nothing" not in msg, msg
    assert snapshot(sandbox["Documents"], sandbox["Downloads"], sandbox["Desktop"]) == before


def test_move_undo(sandbox):
    roundtrip(sandbox, lambda: files.move_file("Downloads\\notes.txt", "Documents"),
              lambda: (sandbox["Documents"] / "notes.txt").exists())


def test_rename_undo(sandbox):
    roundtrip(sandbox, lambda: files.rename_file("Downloads\\notes.txt", "lora.txt"),
              lambda: (sandbox["Downloads"] / "lora.txt").exists())


def test_copy_undo(sandbox):
    roundtrip(sandbox, lambda: files.copy_file("Downloads\\photo.jpg", "Desktop"),
              lambda: (sandbox["Desktop"] / "photo.jpg").exists())


def test_zip_undo(sandbox):
    def check():
        assert (sandbox["Documents"] / "resume.zip").exists()
    roundtrip(sandbox, lambda: files.zip_folder("Documents\\resume"), check)


def test_zip_several_files(sandbox):
    import zipfile
    args = {"source": "Downloads\\notes.txt", "extra_files": ["Downloads\\photo.jpg"], "destination": "Desktop\\both"}
    assert "notes.txt, " in files.preview("zip_folder", args)
    assert "(2 files" in files.zip_folder(**args)
    assert sorted(zipfile.ZipFile(sandbox["Desktop"] / "both.zip").namelist()) == ["notes.txt", "photo.jpg"]


def test_not_found_hint_marks_folders(sandbox):
    with pytest.raises(ToolError, match=r"resume\\"):
        files.move_file("Documents\\resume.pdf", "Desktop")


def test_organize_undo(sandbox):
    def check():
        d = sandbox["Downloads"]
        assert (d / "PDFs" / "attention_transformer.pdf").exists() and (d / "Images" / "photo.jpg").exists()
    plan = files.preview("organize_folder", {"path": "Downloads"})
    assert "notes.txt → Documents\\" in plan and "(5 moves)" in plan
    roundtrip(sandbox, lambda: files.organize_folder("Downloads"), check)


def test_recycle_undo_restores(sandbox):
    roundtrip(sandbox, lambda: files.move_to_recycle_bin("Downloads\\budget.xlsx"),
              lambda: not (sandbox["Downloads"] / "budget.xlsx").exists())


def test_never_overwrites(sandbox):
    (sandbox["Documents"] / "notes.txt").write_text("keep me")
    (sandbox["Documents"] / "resume.zip").write_bytes(b"old zip")
    before = snapshot(sandbox["Documents"], sandbox["Downloads"])
    for call in (lambda: files.move_file("Downloads\\notes.txt", "Documents"),
                 lambda: files.copy_file("Downloads\\notes.txt", "Documents"),
                 lambda: files.rename_file("Downloads\\photo.jpg", "notes.txt"),
                 lambda: files.zip_folder("Documents\\resume")):
        with pytest.raises(ToolError, match="already exists|never overwrites"):
            call()
    assert snapshot(sandbox["Documents"], sandbox["Downloads"]) == before


def test_write_guards(sandbox):
    with pytest.raises(ToolError):
        files.move_file("Downloads\\notes.txt", str(sandbox["root"] / "outside"))
    with pytest.raises(ToolError):
        files.rename_file("Downloads\\notes.txt", "..\\x.txt")
    for call in (lambda: files.move_to_recycle_bin("Downloads"), lambda: files.move_file("Downloads", "Documents"),
                 lambda: files.rename_file("Downloads", "old"), lambda: files.preview("move_file",
                 {"source": "Downloads", "destination": "Documents"})):
        with pytest.raises(ToolError, match="main folders"):
            call()
    with pytest.raises(ToolError):
        files.copy_file("Documents\\.env", "Desktop")


def test_undo_nothing_left(sandbox):
    assert journal.undo() == "Nothing to undo."


# --- system / developer --------------------------------------------------------------------------------------------

def test_system_tools():
    assert re.search(r"RAM: [\d.]+ of [\d.]+ GB used", system.system_info())
    out = system.top_processes("memory", 3)
    assert out.startswith("Top 3 by memory:") and len(out.splitlines()) == 4
    assert re.match(r"(Online|Offline)\. (Wi-Fi|Wired): .*Local IP: |(Online|Offline)\. Not connected",
                    system.network_status())


def test_network_wired_and_wifi(monkeypatch):
    monkeypatch.setattr(system.socket, "create_connection", lambda *a, **k: type("C", (), {"close": lambda s: None})())
    monkeypatch.setattr(system, "_wifi", lambda: (None, None))
    monkeypatch.setattr(system, "active_interfaces", lambda: [("Ethernet 4", "10.1.36.221", False)])
    assert system.network_status() == "Online. Wired: Ethernet 4. Local IP: 10.1.36.221."
    monkeypatch.setattr(system, "_wifi", lambda: ("HomeNet_5G", "82%"))
    monkeypatch.setattr(system, "active_interfaces", lambda: [("Wi-Fi", "192.168.1.23", True)])
    assert system.network_status() == "Online. Wi-Fi: HomeNet_5G (signal 82%). Local IP: 192.168.1.23."
    monkeypatch.setattr(system, "active_interfaces", lambda: [])
    assert system.network_status() == "Online. Not connected to any network."


def test_open_app(monkeypatch, tmp_path):
    opened = []
    monkeypatch.setattr("os.startfile", opened.append)
    apps = {"spotify": ("Spotify", str(tmp_path / "Spotify.lnk")), "word": ("Word", "shell:AppsFolder\\Word"),
            "microsoft edge": ("Microsoft Edge", "shell:AppsFolder\\Edge"),
            "visual studio code": ("Visual Studio Code", "code.lnk")}
    monkeypatch.setattr(system, "start_menu_apps", lambda: apps)
    assert system.open_app("spotify") == "Launched Spotify." and opened
    assert system.open_app("Microsoft Word") == "Launched Word."  # not Microsoft Edge
    assert system.open_app("VS Code") == "Launched Visual Studio Code."
    assert system.open_app("edge") == "Launched Microsoft Edge."
    assert system.open_app("calculator") == "Launched Calculator."
    with pytest.raises(ToolError, match="No app"):
        system.open_app("photoshop")
    with pytest.raises(ToolError, match="No app"):
        system.open_app("Microsoft Excel")  # not installed here: must not launch something similar


def test_port_in_use():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    port = s.getsockname()[1]
    try:
        assert f"Port {port}: python" in dev.port_in_use(port).lower().replace("port", "Port", 1)
    finally:
        s.close()
    assert "Nothing is listening" in dev.port_in_use(port)


def test_git_status(sandbox):
    repo = sandbox["Documents"] / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    (repo / "a.txt").write_text("x")
    out = dev.git_status("Documents\\repo")
    assert out.startswith("Branch main, no upstream.") and "?? a.txt" in out
    with pytest.raises(ToolError, match="Not a git"):
        dev.git_status("Documents\\resume")


# --- productivity / memory / calculate -----------------------------------------------------------------------------

def test_notes(sandbox):
    assert productivity.create_note("Groceries", "rice, dal, atta") == "Saved note 'Groceries' (note 1)."
    productivity.create_note("Interview prep", "revise DPO and GRPO")
    out = productivity.search_notes("dpo")
    assert out.startswith("1 note:") and "Interview prep" in out
    assert productivity.search_notes("pizza") == "No matching notes."
    assert "Deleted note" in journal.undo() and "No matching" in productivity.search_notes("dpo")


def test_reminders(sandbox):
    assert "reminder 1" in productivity.set_reminder("drink water", "in 30 minutes")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 09:00")
    assert tomorrow in productivity.set_reminder("call mom", tomorrow)
    assert productivity.list_reminders().startswith("2 upcoming:")
    with pytest.raises(ToolError, match="past"):
        productivity.set_reminder("x", "2020-01-01 10:00")
    with pytest.raises(ToolError, match="Can't read"):
        productivity.set_reminder("x", "tomorrowish")
    shown = []
    fired = productivity.fire_due(datetime.now() + timedelta(hours=1), notify=shown.append)
    assert [r["text"] for r in fired] == ["drink water"] and shown == ["drink water"]
    assert "Cancelled reminder 2" in journal.undo()
    assert productivity.list_reminders() == "No upcoming reminders."


def test_parse_time():
    now = datetime(2026, 10, 22, 10, 0)
    assert productivity.parse_time("in 2 hours", now) == datetime(2026, 10, 22, 12, 0)
    assert productivity.parse_time("in an hour", now) == datetime(2026, 10, 22, 11, 0)
    assert productivity.parse_time("in 3 hours 45 minutes", now) == datetime(2026, 10, 22, 13, 45)
    assert productivity.parse_time("in 1 hour and 30 min", now) == datetime(2026, 10, 22, 11, 30)
    assert productivity.parse_time("2026-10-23 09:00", now) == datetime(2026, 10, 23, 9, 0)
    sat = datetime(2026, 10, 24, 21, 0)  # a Saturday
    assert productivity.parse_time("friday 17:00", sat) == datetime(2026, 10, 30, 17, 0)
    assert productivity.parse_time("next monday at 9am", sat) == datetime(2026, 10, 26, 9, 0)
    assert productivity.parse_time("saturday 22:00", sat) == datetime(2026, 10, 24, 22, 0)  # later today
    assert productivity.parse_time("saturday 8am", sat) == datetime(2026, 10, 31, 8, 0)  # passed: next week
    assert productivity.parse_time("next saturday 22:00", sat) == datetime(2026, 10, 31, 22, 0)


def test_memory_keyword_fallback(sandbox, monkeypatch):
    monkeypatch.setattr(memory, "embed", lambda text: None)
    assert memory.remember(r"Resume folder is D:\docs\resume").startswith("Saved memory 1:")
    memory.remember("Sister's birthday is 14 March")
    out = memory.recall("where is my resume folder")
    assert out.startswith("1. Resume folder is D:\\docs\\resume")
    assert memory.recall("favourite pizza") == "No matching memories."
    assert "Forgot memory 2" in journal.undo() and len(memory.all_memories()) == 1


def test_memory_embeddings(sandbox):
    if memory.embed("ping") is None:
        pytest.skip("Ollama embedder not running")
    memory.remember(r"Resume folder is D:\docs\resume")
    memory.remember("My home Wi-Fi is called Batcave")
    assert memory.recall("where's my CV").startswith("1. Resume folder")


def test_calculate_tool():
    assert calc.calculate("34999 * 18 / 100") == "6299.82"
    assert calc.calculate("2 ** 10") == "1024" and calc.calculate("10 / 4") == "2.5"
    for bad in ["__import__('os')", "open('x')", "x + 1", "().__class__"]:
        with pytest.raises(ToolError):
            calc.calculate(bad)


def test_calculate_sizes():
    # issue 002: the probe's disk_usage sizes, summed with their units (1024-based like disk_usage)
    assert calc.calculate("43.6 GB + 7.8 GB + 2.7 GB + 2.4 GB + 230 MB + 131 KB + 55 KB").startswith("56.72 GB (")
    assert calc.calculate("1.5gb - 200mb").startswith("1.3 GB") and calc.calculate("512 bytes + 1 kb") == "1.5 KB (1,536 bytes)"
    assert calc.calculate("(43.6 + 7.8) GB / 2").startswith("25.7 GB") and calc.calculate("100 b") == "100 B"
    assert calc.calculate("15% of 5.3 GB").startswith("814.08 MB")
    assert calc.calculate("2.5 GB / MB") == "2560" and calc.calculate("1 GB / 512 MB") == "2"  # size / size: a number
    for bad in ["5 GB + 3", "2 GB * 3 MB", "sqrt(4 GB)", "2 GB ** 2"]:
        with pytest.raises(ToolError):
            calc.calculate(bad)


def test_save_config_merges(sandbox):
    from alfred.tools.guards import config, save_config
    save_config({"max_calls": 5})
    save_config({"temperature": 0.2})
    assert config()["max_calls"] == 5 and config()["temperature"] == 0.2 and "folders" in config()
