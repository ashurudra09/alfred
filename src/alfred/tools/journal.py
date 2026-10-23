"""Action journal and undo (FR10, FR11). A library used by the CLI/UI `/undo`, deliberately not an MCP tool:
undo is the user's decision, not the model's.
"""

import json
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from send2trash import send2trash

from alfred.tools.guards import home


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(home() / "journal.db")
    db.execute("CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY, ts TEXT, tool TEXT, op TEXT, src TEXT,"
               " dst TEXT, extra TEXT, undone INTEGER DEFAULT 0)")
    return db


def record(tool: str, op: str, src=None, dst=None, extra=None) -> int:
    with _db() as db:
        cur = db.execute("INSERT INTO actions (ts, tool, op, src, dst, extra) VALUES (?, ?, ?, ?, ?, ?)",
                         (datetime.now().isoformat(timespec="seconds"), tool, op, src and str(src),
                          dst and str(dst), json.dumps(extra) if extra is not None else None))
        return cur.lastrowid


def recent(n: int = 20) -> list[dict]:
    with _db() as db:
        rows = db.execute("SELECT id, ts, tool, op, src, dst, extra, undone FROM actions ORDER BY id DESC LIMIT ?",
                          (n,)).fetchall()
    keys = ("id", "ts", "tool", "op", "src", "dst", "extra", "undone")
    return [dict(zip(keys, r)) | {"extra": json.loads(r[6]) if r[6] else None} for r in rows]


def _move_back(src: Path, dst: Path):
    if not dst.exists():
        raise RuntimeError(f"{dst} is gone, so it can't be moved back")
    if src.exists():
        raise RuntimeError(f"{src} exists again, so moving back would overwrite it")
    src.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dst), str(src))


RESTORE_PS = r"""
$sh = New-Object -ComObject Shell.Application; $rb = $sh.Namespace(10)
$want = '{path}'; $folder = Split-Path $want; $leaf = Split-Path $want -Leaf
$items = @($rb.Items() | Where-Object {{ $_.ExtendedProperty('System.Recycle.DeletedFrom') -eq $folder -and
  (($_.Name -eq $leaf) -or ($_.Name -eq [IO.Path]::GetFileNameWithoutExtension($leaf))) }})
if ($items.Count -eq 0) {{ exit 2 }}
$item = $items | Sort-Object {{ $_.ExtendedProperty('System.Recycle.DateDeleted') }} | Select-Object -Last 1
$item.InvokeVerb('undelete'); Start-Sleep -Milliseconds 500
if (Test-Path -LiteralPath $want) {{ exit 0 }} else {{ exit 3 }}
"""


def restore_from_recycle_bin(path: Path) -> bool:
    script = RESTORE_PS.format(path=str(path).replace("'", "''"))
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True,
                       timeout=60)
    return r.returncode == 0 and path.exists()


def undo(action_id: int | None = None) -> str:
    """Reverse the latest action that isn't undone yet, or a chosen one. Returns a message for the user."""
    with _db() as db:
        q = ("SELECT id, tool, op, src, dst, extra FROM actions WHERE undone = 0 " +
             ("AND id = ?" if action_id else "ORDER BY id DESC LIMIT 1"))
        row = db.execute(q, (action_id,) if action_id else ()).fetchone()
    if not row:
        return "Nothing to undo." if not action_id else f"No action {action_id} to undo."
    aid, tool, op, src, dst, extra = row
    src, dst, extra = src and Path(src), dst and Path(dst), json.loads(extra) if extra else None
    try:
        if op in ("move", "rename"):
            _move_back(src, dst)
            msg = f"Moved {dst} back to {src}."
        elif op == "create":  # copy / zip: the created file goes to the Recycle Bin
            send2trash(str(dst))
            msg = f"Moved the created {dst} to the Recycle Bin."
        elif op == "organize":
            for s, d in reversed(extra["moves"]):
                _move_back(Path(s), Path(d))
            for d in extra.get("created", []):  # folders organize made; only removed if still empty
                if Path(d).is_dir() and not any(Path(d).iterdir()):
                    Path(d).rmdir()
            msg = f"Moved {len(extra['moves'])} files back to {src}."
        elif op == "recycle":
            if not restore_from_recycle_bin(src):
                return (f"I couldn't restore {src} automatically. It's in the Recycle Bin: open it, right-click "
                        f"{src.name} and choose Restore.")
            msg = f"Restored {src} from the Recycle Bin."
        elif op == "note":
            dst.unlink(missing_ok=True)
            msg = f"Deleted note {dst.stem}."
        elif op == "reminder":
            from alfred.tools.productivity import cancel_reminder
            cancel_reminder(extra["id"])
            msg = f"Cancelled reminder {extra['id']}."
        elif op == "memory":
            from alfred.tools.memory import forget
            forget(extra["id"])
            msg = f"Forgot memory {extra['id']}."
        else:
            return f"Action {aid} ({tool}) can't be undone."
    except Exception as e:
        return f"Couldn't undo action {aid} ({tool}): {e}"
    with _db() as db:
        db.execute("UPDATE actions SET undone = 1 WHERE id = ?", (aid,))
    return msg
