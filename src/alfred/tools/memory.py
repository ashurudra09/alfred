"""Explicit long-term memory (FR18, FR19): remember / recall, plus list / forget for the CLI and UI.
Embeddings come from the local Ollama embedder chosen in Phase 1 (embeddinggemma); without Ollama, recall falls
back to keyword matching.
"""

import json
import math
import re
import sqlite3
import urllib.request
import numpy as np

from mcp.server.fastmcp.exceptions import ToolError

from alfred.tools import journal
from alfred.tools.guards import config, home, now

EMBED_URL, MODEL = "http://127.0.0.1:11434/api/embed", "embeddinggemma"
MIN_SCORE = 0.5  # embeddinggemma: related 0.52-0.69, unrelated up to 0.47 (measured 2026-10-23)


def _db():
    db = sqlite3.connect(home() / "memory.db")
    db.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, ts TEXT, text TEXT, embedding TEXT)")
    return db


def embed_many(texts: list[str], timeout: float = 600) -> np.ndarray:
    """Unit-normalised embeddings, one row per text, in batches of 64. Raises if Ollama is not reachable.
    Shared by recall, semantic search (tools/semantic.py) and the contamination guard (data/dedup.py)."""
    out = []
    for i in range(0, len(texts), 64):
        req = urllib.request.Request(EMBED_URL, json.dumps({"model": MODEL, "input": texts[i:i + 64]}).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out += json.load(r)["embeddings"]
    v = np.array(out, dtype=np.float32).reshape(len(out), -1)
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


def embed(text: str) -> list[float] | None:
    try:
        return embed_many([text], timeout=30)[0].tolist()
    except Exception:
        return None


def remember(fact):
    fact = " ".join(fact.split())
    if not fact:
        raise ToolError("Nothing to remember.")
    vec = embed(fact)
    with _db() as db:
        mid = db.execute("INSERT INTO memories (ts, text, embedding) VALUES (?, ?, ?)",
                         (now().isoformat(timespec="seconds"), fact, json.dumps(vec) if vec else None)).lastrowid
    journal.record("remember", "memory", None, None, {"id": mid})
    return f"Saved memory {mid}: {fact}"


def all_memories() -> list[dict]:
    with _db() as db:
        rows = db.execute("SELECT id, ts, text, embedding FROM memories ORDER BY id").fetchall()
    return [{"id": i, "ts": ts, "text": t, "embedding": json.loads(e) if e else None} for i, ts, t, e in rows]


def forget(mid: int) -> bool:
    with _db() as db:
        return db.execute("DELETE FROM memories WHERE id = ?", (mid,)).rowcount > 0


def _cos(a, b):
    return sum(x * y for x, y in zip(a, b)) / ((math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))) or 1)


def _keyword(query: str, text: str) -> float:
    """Share of the query's words found in the text ('wifi' matches 'Wi-Fi')."""
    q = {w for w in re.findall(r"\w+", query.casefold().replace("-", "")) if len(w) > 2}
    t = set(re.findall(r"\w+", text.casefold().replace("-", "")))
    return len(q & t) / len(q) if q else 0.0


def recall(query):
    mems = all_memories()
    if not mems:
        return "No matching memories."
    qv = embed(query)
    scored = []
    for m in mems:
        s = _keyword(query, m["text"])
        if qv and m["embedding"]:
            s = max(s, _cos(qv, m["embedding"]))
        scored.append((s, m))
    hits = [(s, m) for s, m in sorted(scored, key=lambda x: -x[0]) if s >= config().get("min_score", MIN_SCORE)][:3]
    if not hits:
        return "No matching memories."
    return "\n".join(f"{i}. {m['text']} (saved {m['ts'][:10]})" for i, (_, m) in enumerate(hits, 1))
