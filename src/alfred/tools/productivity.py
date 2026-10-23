"""Productivity tools (contracts 19-22): notes and reminders, stored in Alfred's home folder."""

import json
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta

from mcp.server.fastmcp.exceptions import ToolError

from alfred.tools import journal
from alfred.tools.guards import home

_lock = threading.Lock()


def notes_dir():
    d = home() / "notes"
    d.mkdir(exist_ok=True)
    return d


def create_note(title, content):
    d = notes_dir()
    nid = 1 + max((int(p.stem.split("-")[0]) for p in d.glob("*.md") if p.stem.split("-")[0].isdigit()), default=0)
    slug = re.sub(r"[^\w]+", "-", title.casefold()).strip("-")[:40] or "note"
    path = d / f"{nid}-{slug}.md"
    path.write_text(f"# {title}\n{datetime.now():%Y-%m-%d}\n\n{content}\n", encoding="utf-8")
    journal.record("create_note", "note", None, path)
    return f"Saved note '{title}' (note {nid})."


def all_notes() -> list[dict]:
    out = []
    for p in sorted(notes_dir().glob("*.md"), key=lambda p: int(p.stem.split("-")[0]) if p.stem.split("-")[0].isdigit() else 0):
        lines = p.read_text(encoding="utf-8").splitlines()
        out.append({"id": p.stem.split("-")[0], "title": lines[0].lstrip("# ").strip() if lines else p.stem,
                    "date": lines[1] if len(lines) > 1 else "", "body": "\n".join(lines[3:]).strip()})
    return out


def search_notes(query):
    words = [w for w in re.findall(r"\w+", query.casefold()) if len(w) > 1]
    scored = []
    for n in all_notes():
        text = f"{n['title']} {n['body']}".casefold()
        score = sum(w in text for w in words)
        if score:
            scored.append((score, n))
    if not scored:
        return "No matching notes."
    scored.sort(key=lambda s: -s[0])
    lines = [f"{i}. {n['title']} ({n['date']}): {' '.join(n['body'].split())[:120]}"
             for i, (_, n) in enumerate(scored[:10], 1)]
    return f"{len(lines)} note{'s' if len(lines) != 1 else ''}:\n" + "\n".join(lines)


def _store():
    return home() / "reminders.json"


def _load() -> list[dict]:
    return json.loads(_store().read_text(encoding="utf-8")) if _store().exists() else []


def _save(items: list[dict]):
    _store().write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")


UNITS = {"min": 1, "minute": 1, "minutes": 1, "mins": 1, "m": 1, "hour": 60, "hours": 60, "hr": 60, "hrs": 60,
         "h": 60, "day": 1440, "days": 1440}


def parse_time(text: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    t = text.strip().casefold()
    m = re.fullmatch(r"in\s+(an?|\d+(?:\.\d+)?)\s*([a-z]+)", t)
    if m and m.group(2) in UNITS:
        n = 1 if m.group(1) in ("a", "an") else float(m.group(1))
        return now + timedelta(minutes=n * UNITS[m.group(2)])
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            pass
    raise ToolError(f"Can't read the time '{text}'. Use 'YYYY-MM-DD HH:MM' or 'in 20 minutes'.")


def set_reminder(text, time):
    when = parse_time(time)
    if when <= datetime.now():
        raise ToolError(f"{when:%Y-%m-%d %H:%M} is in the past.")
    with _lock:
        items = _load()
        rid = 1 + max((r["id"] for r in items), default=0)
        items.append({"id": rid, "text": text, "when": when.isoformat(timespec="minutes"), "done": False})
        _save(items)
    journal.record("set_reminder", "reminder", None, None, {"id": rid})
    return f"Reminder set for {when:%Y-%m-%d %H:%M}: {text} (reminder {rid})."


def cancel_reminder(rid: int):
    with _lock:
        _save([r for r in _load() if r["id"] != rid])


def list_reminders():
    upcoming = sorted((r for r in _load() if not r["done"]), key=lambda r: r["when"])
    if not upcoming:
        return "No upcoming reminders."
    lines = [f"{i}. {r['when'].replace('T', ' ')} {r['text']}" for i, r in enumerate(upcoming, 1)]
    return f"{len(lines)} upcoming:\n" + "\n".join(lines)


TOAST_PS = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $x.GetElementsByTagName('text'); $t.Item(0).AppendChild($x.CreateTextNode('Alfred reminder')) | Out-Null
$t.Item(1).AppendChild($x.CreateTextNode('{text}')) | Out-Null
$app = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""


def fire_due(now: datetime | None = None, notify=None) -> list[dict]:
    """Mark due reminders done and show a Windows toast for each. Returns the ones fired."""
    now = now or datetime.now()
    notify = notify or (lambda text: subprocess.run(
        ["powershell", "-NoProfile", "-Command", TOAST_PS.format(text=text.replace("'", "''"))], timeout=30))
    with _lock:
        items, fired = _load(), []
        for r in items:
            if not r["done"] and datetime.fromisoformat(r["when"]) <= now:
                r["done"] = True
                fired.append(r)
        if fired:
            _save(items)
    for r in fired:
        notify(r["text"])
    return fired


def reminder_loop(interval: float = 20):
    # ponytail: reminders fire only while the Alfred server is running; use Windows Task Scheduler if they must
    # fire with Alfred closed.
    while True:
        try:
            fire_due()
        except Exception:
            pass
        time.sleep(interval)
