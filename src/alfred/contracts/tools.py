"""The 25 frozen tool contracts (requirements Section 5). Signatures, docstrings and flags only; bodies live in
`alfred.tools` (Phase 6), which registers each implementation under the contract's signature.

Docstrings become the model-facing descriptions, so they are short and say how to tell look-alike tools apart.
Changing anything here means bumping CONTRACTS_VERSION and regenerating training data.
"""

from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import Field

CONTRACTS_VERSION = "1.0"

GROUPS = ("files", "open", "system", "developer", "productivity", "memory", "utility")
REGISTRY: dict[str, dict] = {}


def contract(group: str, *, read_only: bool = False, destructive: bool = False, confirm: bool = False):
    """Register a contract. `confirm` = the agent must get the user's yes before running it."""
    assert group in GROUPS

    def wrap(fn: Callable) -> Callable:
        REGISTRY[fn.__name__] = {"fn": fn, "group": group, "read_only": read_only, "destructive": destructive,
                                 "needs_confirmation": confirm}
        return fn

    return wrap


# Paths may be full Windows paths or start with a known folder name; the system prompt says so once, not per argument.
Path = str
Folder = str
Ext = Annotated[str | None, Field(description="File extension without the dot, e.g. 'pdf'")]


# --- Files -----------------------------------------------------------------------------------------------------

@contract("files", read_only=True)
def search_files(
    query: Annotated[str, Field(description="Text the file NAME should contain")],
    folder: Folder,
    extension: Ext = None,
    modified_within_days: Annotated[int | None, Field(ge=1, description="Only files changed in the last N days")] = None,
):
    """Find files by their name. To search inside file text use search_file_contents; for notes use search_notes."""


@contract("files", read_only=True)
def search_file_contents(
    text: Annotated[str, Field(description="Text the file CONTENTS should contain")],
    folder: Folder,
    extension: Ext = None,
):
    """Find files whose text contains a phrase (txt, md, pdf, code)."""


@contract("files", read_only=True)
def list_directory(path: Path):
    """List the files and folders directly inside a folder."""


@contract("files", read_only=True)
def read_file(path: Path, max_chars: Annotated[int, Field(ge=100, le=20000)] = 4000):
    """Read the text of a txt, md or pdf file."""


@contract("files", read_only=True)
def disk_usage(path: Path, top_n: Annotated[int, Field(ge=1, le=50)] = 10):
    """Show free space and the largest folders/files under a path."""


@contract("files", destructive=True, confirm=True)
def move_file(source: Path, destination: Annotated[str, Field(description="Target folder or full new path")]):
    """Move a file or folder. Never overwrites."""


@contract("files", destructive=True, confirm=True)
def rename_file(path: Path, new_name: Annotated[str, Field(description="New file name only, no folder")]):
    """Rename a file or folder in place. Never overwrites."""


@contract("files", confirm=True)
def copy_file(source: Path, destination: Annotated[str, Field(description="Target folder or full new path")]):
    """Copy a file. Never overwrites."""


@contract("files", confirm=True)
def zip_folder(
    source: Path,
    destination: Annotated[str | None, Field(description="Path of the .zip; default: next to the folder")] = None,
):
    """Compress a folder into a .zip. Never overwrites."""


@contract("files", destructive=True, confirm=True)
def organize_folder(path: Path, strategy: Literal["by_type", "by_date"] = "by_type"):
    """Sort a folder's loose files into subfolders by type or by month. Shows the full plan before running."""


@contract("files", destructive=True, confirm=True)
def move_to_recycle_bin(path: Path):
    """Delete a file or folder by moving it to the Recycle Bin (restorable). The only way to delete."""


# --- Open ------------------------------------------------------------------------------------------------------

@contract("open")
def open_path(path: Path):
    """Open a file or folder in its default app. Refuses programs and scripts."""


@contract("open")
def open_app(name: Annotated[str, Field(description="App name as in the Start Menu, e.g. 'Spotify'")]):
    """Launch an installed app from the Start Menu."""


# --- System ----------------------------------------------------------------------------------------------------

@contract("system", read_only=True)
def system_info():
    """CPU, RAM, battery and Windows version."""


@contract("system", read_only=True)
def top_processes(sort_by: Literal["cpu", "memory"] = "cpu", n: Annotated[int, Field(ge=1, le=25)] = 5):
    """The processes using the most CPU or memory right now."""


@contract("system", read_only=True)
def network_status():
    """Whether the laptop is online, the Wi-Fi name and the local IP address."""


# --- Developer -------------------------------------------------------------------------------------------------

@contract("developer", read_only=True)
def port_in_use(port: Annotated[int, Field(ge=1, le=65535)]):
    """Which process (name and PID) is using a TCP port."""


@contract("developer", read_only=True)
def git_status(repo_path: Path):
    """A git repo's branch, commits ahead/behind and changed files."""


# --- Productivity ----------------------------------------------------------------------------------------------

@contract("productivity")
def create_note(title: str, content: str):
    """Save a new note in Alfred's notes folder."""


@contract("productivity", read_only=True)
def search_notes(query: str):
    """Search the notes saved with create_note."""


@contract("productivity")
def set_reminder(
    text: str,
    time: Annotated[str, Field(description="'YYYY-MM-DD HH:MM' (24h, local) or relative like 'in 20 minutes'")],
):
    """Show a Windows notification at a time (while Alfred is running)."""


@contract("productivity", read_only=True)
def list_reminders():
    """List upcoming reminders."""


# --- Memory ----------------------------------------------------------------------------------------------------

@contract("memory")
def remember(fact: Annotated[str, Field(description="One self-contained fact, e.g. 'Resume folder is D:\\docs\\resume'")]):
    """Save a fact the user asked Alfred to remember, for later chats."""


@contract("memory", read_only=True)
def recall(query: str):
    """Look up saved facts relevant to the query (e.g. where something is)."""


# --- Utility ---------------------------------------------------------------------------------------------------

@contract("utility", read_only=True)
def calculate(expression: Annotated[str, Field(description="Arithmetic, e.g. '34999 * 18 / 100'")]):
    """Evaluate an arithmetic expression exactly. Supports + - * / % ** ( ) and sqrt, round, abs."""
