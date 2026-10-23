"""Chat history (FR20, FR21): every chat saved locally in SQLite; continuing one sends only recent turns.

Deleting a chat never deletes memories (those live in tools/memory.py).
"""

import json
import sqlite3
from datetime import datetime

from alfred.contracts.schemas import Message
from alfred.tools.guards import home

CONTEXT_CHARS = 14000  # ~4k tokens of history; older turns stay in storage but aren't sent


def _db():
    db = sqlite3.connect(home() / "chats.db")
    db.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, title TEXT, created TEXT, updated TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, chat_id INTEGER, ts TEXT, "
               "message TEXT)")
    return db


def new_chat(title: str = "New chat") -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with _db() as db:
        return db.execute("INSERT INTO chats (title, created, updated) VALUES (?, ?, ?)", (title, now, now)).lastrowid


def list_chats() -> list[dict]:
    with _db() as db:
        rows = db.execute("SELECT c.id, c.title, c.updated, COUNT(m.id) FROM chats c LEFT JOIN messages m "
                          "ON m.chat_id = c.id GROUP BY c.id ORDER BY c.updated DESC").fetchall()
    return [{"id": i, "title": t, "updated": u, "messages": n} for i, t, u, n in rows]


def append(chat_id: int, messages: list[Message]):
    now = datetime.now().isoformat(timespec="seconds")
    with _db() as db:
        db.executemany("INSERT INTO messages (chat_id, ts, message) VALUES (?, ?, ?)",
                       [(chat_id, now, m.model_dump_json(exclude_none=True)) for m in messages])
        title = db.execute("SELECT title FROM chats WHERE id = ?", (chat_id,)).fetchone()
        first_user = next((m.content for m in messages if m.role == "user"), None)
        if title and title[0] == "New chat" and first_user:
            db.execute("UPDATE chats SET title = ? WHERE id = ?", (first_user[:60], chat_id))
        db.execute("UPDATE chats SET updated = ? WHERE id = ?", (now, chat_id))


def history(chat_id: int) -> list[Message]:
    with _db() as db:
        rows = db.execute("SELECT message FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,)).fetchall()
    return [Message.model_validate_json(r[0]) for r in rows]


def context(chat_id: int, budget: int = CONTEXT_CHARS) -> list[Message]:
    """The most recent whole turns (each starting at a user message) that fit the budget."""
    msgs, size, start = history(chat_id), 0, None
    for i in range(len(msgs) - 1, -1, -1):
        size += len(msgs[i].content) + len(json.dumps([c.model_dump() for c in msgs[i].tool_calls or []]))
        if size > budget:
            break
        if msgs[i].role == "user":
            start = i
    return msgs[start:] if start is not None else []


def delete_chat(chat_id: int) -> bool:
    with _db() as db:
        db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        return db.execute("DELETE FROM chats WHERE id = ?", (chat_id,)).rowcount > 0


def exists(chat_id: int) -> bool:
    with _db() as db:
        return db.execute("SELECT 1 FROM chats WHERE id = ?", (chat_id,)).fetchone() is not None
