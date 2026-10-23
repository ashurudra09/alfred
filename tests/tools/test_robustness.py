"""Inputs a model plausibly sends that the first version of the tools mishandled (found by probing, 2026-10-23)."""

import zipfile
from datetime import datetime

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from alfred.tools import calc, dev, files, guards, journal, memory, productivity


@pytest.mark.parametrize("spelling", ["My Documents", "documents folder", "the Documents", "docs", "document",
                                      "`Documents`", "'Documents'", "Documents/"])
def test_folder_name_spellings(sandbox, spelling):
    assert guards.resolve_safe(spelling) == sandbox["Documents"].resolve()


def test_guessed_username_maps_to_real_folder(sandbox):
    out = files.list_directory(r"C:\Users\someone\Downloads")
    assert "notes.txt" in out


def test_wildcards_explain_themselves(sandbox):
    with pytest.raises(ToolError, match="Wildcards"):
        files.move_to_recycle_bin("Downloads\\*.tmp")


def test_missing_extension_resolves_or_suggests(sandbox):
    assert "LoRA" in files.read_file("Downloads\\notes")  # notes -> notes.txt (the only match)
    with pytest.raises(ToolError, match="Similar names.*notes.txt"):
        files.read_file("Downloads\\note.txt")


def test_read_text_without_extension_utf16_docx_and_binary(sandbox):
    d = sandbox["Downloads"]
    (d / "README").write_text("plain text")
    (d / "u16.txt").write_text("hello utf16", encoding="utf-16")
    with zipfile.ZipFile(d / "letter.docx", "w") as z:
        z.writestr("word/document.xml", "<w:p><w:t>Dear Neha,</w:t></w:p><w:p><w:t>Offer attached.</w:t></w:p>")
    assert "plain text" in files.read_file("Downloads\\README")
    assert "hello utf16" in files.read_file("Downloads\\u16.txt")
    assert "Dear Neha" in files.read_file("Downloads\\letter.docx")
    assert "letter.docx" in files.search_file_contents("offer attached", "Downloads")
    with pytest.raises(ToolError, match="Can't read"):
        files.read_file("Downloads\\budget.xlsx")


def test_search_words_and_wildcards(sandbox):
    assert "attention_transformer.pdf" in files.search_files("transformer attention", "Downloads")
    assert "attention_transformer.pdf" in files.search_files("*.pdf", "Downloads")
    assert "attention_transformer.pdf" in files.search_files("", "Downloads", extension="*.PDF")


def test_move_to_missing_folder_does_not_create_a_file(sandbox):
    with pytest.raises(ToolError, match="Folder not found"):
        files.move_file("Downloads\\notes.txt", "Documents\\taxes 2026")
    assert (sandbox["Downloads"] / "notes.txt").exists() and not (sandbox["Documents"] / "taxes 2026").exists()
    files.move_file("Downloads\\notes.txt", "Documents\\lora-notes.txt")  # an explicit new file name still works
    assert (sandbox["Documents"] / "lora-notes.txt").exists()


def test_rename_keeps_extension_and_allows_case_change(sandbox):
    files.rename_file("Downloads\\notes.txt", "lora")
    assert (sandbox["Downloads"] / "lora.txt").exists()
    files.rename_file("Downloads\\lora.txt", "LoRA.txt")
    assert "LoRA.txt" in [p.name for p in sandbox["Downloads"].iterdir()]


def test_zip_single_file(sandbox):
    out = files.zip_folder("Downloads\\notes.txt")
    assert (sandbox["Downloads"] / "notes.zip").exists() and "1 files" in out
    assert "Moved the created" in journal.undo()


def test_organize_leaves_shortcuts_and_system_files(sandbox):
    desk = sandbox["Desktop"]
    for name in ("Chrome.lnk", "desktop.ini", "~$draft.docx", "report.pdf"):
        (desk / name).write_bytes(b"x")
    files.organize_folder("Desktop")
    assert all((desk / n).exists() for n in ("Chrome.lnk", "desktop.ini", "~$draft.docx"))
    assert (desk / "PDFs" / "report.pdf").exists()


def test_organize_skips_locked_files_and_undo_is_exact(sandbox, monkeypatch):
    real_move = files.shutil.move

    def flaky(src, dst):
        if src.endswith("photo.jpg"):
            raise PermissionError(13, "The file is in use")
        return real_move(src, dst)
    monkeypatch.setattr(files.shutil, "move", flaky)
    out = files.organize_folder("Downloads")
    assert "Couldn't move 1" in out and "photo.jpg" in out
    monkeypatch.setattr(files.shutil, "move", real_move)
    journal.undo()
    assert (sandbox["Downloads"] / "attention_transformer.pdf").exists() and not (sandbox["Downloads"] / "PDFs").exists()


def test_recycle_refuses_drives_without_recycle_bin(sandbox, monkeypatch):
    monkeypatch.setattr(files.ctypes.windll.kernel32, "GetDriveTypeW", lambda root: 2)  # 2 = removable
    with pytest.raises(ToolError, match="no Recycle Bin"):
        files.move_to_recycle_bin("Downloads\\notes.txt")
    assert (sandbox["Downloads"] / "notes.txt").exists()


def test_file_in_use_is_a_clear_error(sandbox, monkeypatch):
    monkeypatch.setattr(files.shutil, "move", lambda *a: (_ for _ in ()).throw(PermissionError(13, "in use")))
    with pytest.raises(ToolError, match="Couldn't move notes.txt: in use"):
        files.move_file("Downloads\\notes.txt", "Documents")


@pytest.mark.parametrize("expr,want", [("18% of 34999", "6299.82"), ("34999 * 18%", "6299.82"), ("3 x 4", "12"),
                                       ("1,00,000 * 2", "200000"), ("₹34,999 * 0.18", "6299.82"), ("10 % 3", "1"),
                                       ("min(3,4)", "3"), ("round(2.567, 2)", "2.57")])
def test_calculate_everyday_notation(expr, want):
    assert calc.calculate(expr) == want


@pytest.mark.parametrize("text,want", [("2026-12-01T09:00:00", "2026-12-01 09:00"), ("tomorrow at 9am", "2026-10-24 09:00"),
                                       ("at 6pm", "2026-10-24 18:00"), ("today at 21:15", "2026-10-23 21:15"),
                                       ("18:30", "2026-10-24 18:30"), ("in 90 seconds", "2026-10-23 20:01"),
                                       ("12am", "2026-10-24 00:00")])
def test_reminder_times(text, want):
    assert f"{productivity.parse_time(text, datetime(2026, 10, 23, 20, 0)):%Y-%m-%d %H:%M}" == want


def test_search_notes_plural_and_list_all(sandbox):
    productivity.create_note("Groceries", "rice, dal")
    productivity.create_note("Meeting", "standup at 10")
    assert "Groceries" in productivity.search_notes("grocery")
    assert productivity.search_notes("all").startswith("2 notes:")


def test_recall_hyphens_and_no_false_matches(sandbox, monkeypatch):
    monkeypatch.setattr(memory, "embed", lambda t: None)
    memory.remember("My home Wi-Fi is called Batcave")
    assert "Batcave" in memory.recall("wifi name")
    assert memory.recall("favourite pizza") == "No matching memories."


def test_git_status_outside_known_folders(sandbox):
    import subprocess
    repo = sandbox["root"] / "outside" / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    assert dev.git_status(str(repo)).startswith("Branch main")
