"""Semantic file search (contracts 1.3: search_by_meaning).

Index: SQLite in Alfred's home (semantic.db). `files` holds each indexed path and its mtime, the FTS5 table `chunks`
holds the text in ~1,000-character pieces (keyword ranking by BM25), and `vecs` holds one embedding per chunk.
Text comes from read_file's extractors, embeddings from the same Ollama embedder as memory. The index is updated
on every search, incrementally by mtime and within a time budget, so the first search of a big folder may say
it is still indexing; deleted files are purged. Files go through the same walk as search_files (sensitive and
hidden paths never seen) plus an extension allow-list and a size cap.

Ranking: BM25 and embedding cosine, fused by reciprocal rank (Cormack et al. 2009); keyword-only when Ollama is
not running, which the result says.
"""

import re
import sqlite3
import time
from pathlib import Path

import numpy as np

from alfred.tools import files, memory
from alfred.tools.guards import home, is_sensitive

EXTS = files.TEXT_EXT | {".pdf", ".docx"}
MAX_BYTES = 5_000_000
CHUNK, MAX_CHUNKS = 1000, 20  # characters per chunk, chunks per file
BUDGET = 20.0  # seconds of indexing per search
RRF_K, POOL, TOP = 60, 50, 5  # fusion constant, candidates per ranker, files returned
MIN_COS = 0.0  # embedding-only hits below this are dropped (calibrated in eval/retrieval.py)
QUERY, DOC = "task: search result | query: {}", "title: {} | text: {}"  # embeddinggemma's retrieval prompts


def _db() -> sqlite3.Connection:
    db = sqlite3.connect(home() / "semantic.db")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, mtime REAL);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(path UNINDEXED, text);
        CREATE TABLE IF NOT EXISTS vecs (id INTEGER PRIMARY KEY, vec BLOB);  -- id = chunks.rowid
    """)
    return db


def split(text: str) -> list[str]:
    """Paragraphs packed into chunks of at most CHUNK characters; longer paragraphs are cut."""
    out, cur = [], ""
    for para in (" ".join(p.split()) for p in re.split(r"\n\s*\n", text)):
        for piece in (para[i:i + CHUNK] for i in range(0, len(para), CHUNK)):
            if cur and len(cur) + len(piece) + 1 > CHUNK:
                out.append(cur)
                cur = ""
            cur = f"{cur} {piece}".strip()
    return (out + [cur] if cur else out)[:MAX_CHUNKS]


def _under(path: str, roots: list[Path]) -> bool:
    p = Path(path)
    return any(r == p or r in p.parents for r in roots)


def update(roots: list[Path], deadline: float) -> tuple[int, bool]:
    """Bring the index up to date for these roots until the deadline. Returns (files still to index, embedder up)."""
    db, todo = _db(), []
    known = dict(db.execute("SELECT path, mtime FROM files"))
    for root in roots:
        for p in files.walk(root):
            if p.suffix.lower() in EXTS and (st := p.stat()).st_size <= MAX_BYTES and known.get(str(p)) != st.st_mtime:
                todo.append((p, st.st_mtime))
    with db:
        for path in known:
            if _under(path, roots) and not Path(path).exists():
                _drop(db, path)
    for i, (p, mtime) in enumerate(todo):
        if time.monotonic() > deadline:
            return len(todo) - i, _embed_missing(db, deadline)
        try:
            pieces = split(files._text(p))
        except Exception:
            pieces = []  # unreadable: remembered by mtime so it isn't retried every search
        with db:
            _drop(db, str(p))
            db.execute("INSERT INTO files VALUES (?, ?)", (str(p), mtime))
            db.executemany("INSERT INTO chunks (path, text) VALUES (?, ?)", [(str(p), c) for c in pieces])
    return 0, _embed_missing(db, deadline)


def _drop(db, path: str):
    db.execute("DELETE FROM vecs WHERE id IN (SELECT rowid FROM chunks WHERE path = ?)", (path,))
    db.execute("DELETE FROM chunks WHERE path = ?", (path,))
    db.execute("DELETE FROM files WHERE path = ?", (path,))


def _embed_missing(db, deadline: float) -> bool:
    """Embed chunks that have no vector yet, 64 at a time, until the deadline. False if Ollama is down."""
    while time.monotonic() < deadline:
        rows = db.execute("SELECT rowid, path, text FROM chunks WHERE rowid NOT IN (SELECT id FROM vecs) "
                          "LIMIT 64").fetchall()
        if not rows:
            return True
        try:
            v = memory.embed_many([DOC.format(Path(p).name, t) for _, p, t in rows], timeout=60)
        except Exception:
            return False
        with db:
            db.executemany("INSERT INTO vecs VALUES (?, ?)", [(r[0], x.tobytes()) for r, x in zip(rows, v)])
    return embedder_up()


def embedder_up() -> bool:
    try:
        memory.embed_many(["ping"], timeout=5)
        return True
    except Exception:
        return False


def keyword_rank(db, query: str, roots: list[Path]) -> list[int]:
    words = {w for w in re.findall(r"[^\W_]+", query.casefold()) if len(w) > 2}
    if not words:
        return []
    rows = db.execute("SELECT rowid, path FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT 500",
                      (" OR ".join(f'"{w}"' for w in words),)).fetchall()
    return [i for i, p in rows if _under(p, roots)][:POOL]


def embedding_rank(db, query: str, roots: list[Path]) -> list[int]:
    rows = [(i, v) for i, p, v in db.execute("SELECT c.rowid, c.path, v.vec FROM chunks c JOIN vecs v ON v.id = c.rowid")
            if _under(p, roots)]
    if not rows:
        return []
    sims = np.frombuffer(b"".join(v for _, v in rows), dtype=np.float32).reshape(len(rows), -1) \
        @ memory.embed_many([QUERY.format(query)], timeout=30)[0]
    best = np.argsort(-sims)[:POOL]
    return [rows[j][0] for j in best if sims[j] >= MIN_COS]


def rrf(*rankings: list[int]) -> list[int]:
    """Reciprocal rank fusion: score = sum of 1 / (RRF_K + rank) over the rankings an item appears in."""
    score: dict[int, float] = {}
    for ranking in rankings:
        for r, i in enumerate(ranking, 1):
            score[i] = score.get(i, 0.0) + 1 / (RRF_K + r)
    return sorted(score, key=lambda i: -score[i])


def rank(query: str, roots: list[Path], mode: str = "fused", db=None) -> list[tuple[str, str]]:
    """Files best matching the query as (path, best chunk), best first. mode: fused, keyword or embedding;
    fused falls back to keyword when the embedder is down."""
    db = db or _db()
    kw = keyword_rank(db, query, roots) if mode != "embedding" else []
    try:
        em = embedding_rank(db, query, roots) if mode != "keyword" else []
    except Exception:
        if mode == "embedding":
            raise
        em = []
    chunk_ids = kw if mode == "keyword" else em if mode == "embedding" else rrf(kw, em)
    out, seen = [], set()
    for i in chunk_ids:
        path, text = db.execute("SELECT path, text FROM chunks WHERE rowid = ?", (i,)).fetchone()
        if path not in seen and not is_sensitive(Path(path)):
            seen.add(path)
            out.append((path, text))
    return out


def snippet(text: str, query: str, width: int = 160) -> str:
    words = [w for w in re.findall(r"[^\W_]+", query.casefold()) if len(w) > 2]
    at = min((i for w in words if (i := text.casefold().find(w)) >= 0), default=0)
    start = max(0, at - width // 3)
    return " ".join(text[start:start + width].split())


def search_by_meaning(query, folder=None):
    roots = files._search_roots(folder)
    left, up = update(roots, time.monotonic() + BUDGET)
    hits = rank(query, roots)[:TOP]
    out = files.listing("", [f'{p}: "...{snippet(t, query)}..."' for p, t in hits])
    if not up:
        out += "\n(Matched by keywords only: the embedding model isn't running.)"
    if left:
        out += f"\n(Still indexing: {left} files not searched yet. Ask again in a minute.)"
    return out
