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


def _word_in(word: str, text: str) -> bool:
    """'grocery' finds 'groceries', 'meetings' finds 'meeting': compare a stem for longer words."""
    return word in text or (len(word) >= 5 and word[:max(4, len(word) - 2)] in text)


def search_notes(query):
    words = [w for w in re.findall(r"\w+", query.casefold()) if len(w) > 1]
    notes = all_notes()
    if not words or query.strip().casefold() in ("all", "everything", "*", "all notes", "notes"):
        words, notes = [], notes[-10:][::-1]  # list the latest notes
    scored = []
    for n in notes:
        text = f"{n['title']} {n['body']}".casefold()
        score = sum(_word_in(w, text) for w in words) if words else 1
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


UNITS = {"sec": 1 / 60, "secs": 1 / 60, "second": 1 / 60, "seconds": 1 / 60, "s": 1 / 60,
         "min": 1, "minute": 1, "minutes": 1, "mins": 1, "m": 1, "hour": 60, "hours": 60, "hr": 60, "hrs": 60,
         "h": 60, "day": 1440, "days": 1440, "week": 10080, "weeks": 10080}
CLOCK = r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?"


def _clock(hour: str, minute: str | None, ampm: str | None) -> tuple[int, int] | None:
    h, mi, ap = int(hour), int(minute or 0), (ampm or "").replace(".", "")
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return (h, mi) if h < 24 and mi < 60 else None


def parse_time(text: str, now: datetime | None = None) -> datetime:
    """'in 20 minutes', 'YYYY-MM-DD HH:MM' (any ISO form, with T, seconds or a timezone), 'tomorrow at 9am',
    'today 18:30', 'at 6pm', '18:30' (today, or tomorrow if that time has passed)."""
    now = now or datetime.now()
    t = re.sub(r"\s+", " ", text.strip().casefold())
    m = re.fullmatch(r"in (an?|\d+(?:\.\d+)?) ?([a-z]+)", t)
    if m and m.group(2) in UNITS:
        n = 1 if m.group(1) in ("a", "an") else float(m.group(1))
        return now + timedelta(minutes=n * UNITS[m.group(2)])
    try:
        when = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        return when.astimezone().replace(tzinfo=None) if when.tzinfo else when
    except ValueError:
        pass
    m = re.fullmatch(rf"(today|tomorrow|tonight)?(?: at)? ?{CLOCK}(?: (today|tomorrow))?", t.removeprefix("at "))
    if m and (hm := _clock(m.group(2), m.group(3), m.group(4))):
        day = m.group(1) or m.group(5)
        when = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
        if day == "tomorrow" or (day is None and when <= now):
            when += timedelta(days=1)
        return when
    raise ToolError(f"Can't read the time '{text}'. Use 'YYYY-MM-DD HH:MM', 'in 20 minutes' or 'tomorrow at 9am'.")


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
        ["powershell", "-NoProfile", "-Command", TOAST_PS.format(text=text.replace("'", "''"))], timeout=30,
        capture_output=True, stdin=subprocess.DEVNULL))  # never touch the server's stdio: it carries MCP
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
