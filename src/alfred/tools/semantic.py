"""Semantic file search (contracts 1.3: search_by_meaning).

Index: SQLite in Alfred's home (semantic.db). `files` holds each indexed path and its mtime, the FTS5 table `chunks`
holds the text in ~1,000-character pieces (keyword ranking by BM25), and `vecs` holds one embedding per chunk.
Text comes from read_file's extractors, embeddings from the same Ollama embedder as memory. The index is updated
on every search, incrementally by mtime and within a time budget, and in a background thread when the tool server
starts (`index_all`), so a search of a big folder may say it is still indexing; deleted files are purged. Files go
through the same walk as search_files (sensitive and hidden paths never seen) plus an extension allow-list and a
size cap.

Ranking (plan amendments 1 and 7, from eval/retrieval.py): embedding cosine, no cut-off. BM25
keyword hits stand in for chunks that have no embedding yet (interleaved by reciprocal rank, Cormack et al. 2009)
and for everything when Ollama is not running, which the result says.
"""

import hashlib
import os

import re
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path

import numpy as np

from alfred.tools import files, memory
from alfred.tools.guards import config, home, is_sensitive

EXTS = files.TEXT_EXT | {".pdf", ".docx"}
MAX_BYTES = 5_000_000
CHUNK, MAX_CHUNKS = 1000, 20  # characters per chunk, chunks per file
BUDGET = 20.0  # seconds of indexing per search
RRF_K, POOL, TOP = 60, 50, 5  # fusion constant, candidates per ranker, files returned
MIN_COS = 0.0  # embedding hits below this are dropped. 0 = off: 0.346 (dev-half rule) cost recall and rejected
               # only ~1 in 4 unanswerable queries (eval/reports/retrieval_scifact_*.json), so the model judges
LOCK = threading.Lock()  # one indexer at a time: a search skips its own update while the background one runs
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
    with closing(_db()) as db:
        return _update(db, roots, deadline)


def _update(db, roots: list[Path], deadline: float) -> tuple[int, bool]:
    todo = []
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


def _embed(texts: list[str], timeout: float) -> np.ndarray:
    """memory.embed_many behind an optional cache keyed by model + text (ALFRED_EMBED_CACHE=<sqlite file>): evals
    and rollouts rebuild the same fixture files in a fresh home every task."""
    path = os.environ.get("ALFRED_EMBED_CACHE")
    if not path:
        return memory.embed_many(texts, timeout=timeout)
    keys = [hashlib.sha256(f"{memory.MODEL}\0{t}".encode()).hexdigest() for t in texts]
    with closing(sqlite3.connect(path, timeout=60)) as c:
        c.execute("CREATE TABLE IF NOT EXISTS e (k TEXT PRIMARY KEY, v BLOB)")
        got = {k: v for k in set(keys) for (v,) in c.execute("SELECT v FROM e WHERE k = ?", (k,))}
        new = {k: t for k, t in zip(keys, texts) if k not in got}
        if new:
            got.update(zip(new, (x.tobytes() for x in memory.embed_many(list(new.values()), timeout=timeout))))
            with c:
                c.executemany("INSERT OR IGNORE INTO e VALUES (?, ?)", [(k, got[k]) for k in new])
    return np.stack([np.frombuffer(got[k], dtype=np.float32) for k in keys])


def _embed_missing(db, deadline: float) -> bool:
    """Embed chunks that have no vector yet, 64 at a time, until the deadline. False if Ollama is down."""
    while time.monotonic() < deadline:
        rows = db.execute("SELECT rowid, path, text FROM chunks WHERE rowid NOT IN (SELECT id FROM vecs) "
                          "LIMIT 64").fetchall()
        if not rows:
            return True
        try:
            v = _embed([DOC.format(Path(p).name, t) for _, p, t in rows], timeout=60)
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


def index_all():
    """Background indexing of every known folder, started with the tool server (config index_on_start, default
    on), so searches don't pay for it. Stops when everything is embedded or Ollama is down."""
    # ponytail: runs flat out until done; add a pause between batches if it slows the model on battery
    while config().get("index_on_start", True):
        with LOCK, closing(_db()) as db:
            left, up = _update(db, files._search_roots(None), time.monotonic() + BUDGET)
            missing = db.execute("SELECT count(*) FROM chunks WHERE rowid NOT IN (SELECT id FROM vecs)").fetchone()[0]
        if not up or not (left or missing):
            return
        time.sleep(0.2)  # let a waiting search take the lock


def keyword_rank(db, query: str, roots: list[Path], unembedded: bool = False) -> list[int]:
    words = {w for w in re.findall(r"[^\W_]+", query.casefold()) if len(w) > 2}
    if not words:
        return []
    rows = db.execute("SELECT rowid, path FROM chunks WHERE chunks MATCH ? "
                      + ("AND rowid NOT IN (SELECT id FROM vecs) " if unembedded else "")
                      + "ORDER BY bm25(chunks) LIMIT 500", (" OR ".join(f'"{w}"' for w in words),)).fetchall()
    return [i for i, p in rows if _under(p, roots)][:POOL]


def embedding_scores(db, query: str, roots: list[Path]) -> list[tuple[int, float]]:
    """(chunk id, cosine) for the POOL closest chunks, best first. Raises if the embedder is down."""
    rows = [(i, v) for i, p, v in db.execute("SELECT c.rowid, c.path, v.vec FROM chunks c JOIN vecs v ON v.id = c.rowid")
            if _under(p, roots)]
    if not rows:
        return []
    sims = np.frombuffer(b"".join(v for _, v in rows), dtype=np.float32).reshape(len(rows), -1) \
        @ _embed([QUERY.format(query)], timeout=30)[0]
    return [(rows[j][0], float(sims[j])) for j in np.argsort(-sims)[:POOL]]


def embedding_rank(db, query: str, roots: list[Path]) -> list[int]:
    return [i for i, cos in embedding_scores(db, query, roots) if cos >= MIN_COS]


def rrf(*rankings: list[int]) -> list[int]:
    """Reciprocal rank fusion: score = sum of 1 / (RRF_K + rank) over the rankings an item appears in."""
    score: dict[int, float] = {}
    for ranking in rankings:
        for r, i in enumerate(ranking, 1):
            score[i] = score.get(i, 0.0) + 1 / (RRF_K + r)
    return sorted(score, key=lambda i: -score[i])


def rank(query: str, roots: list[Path], mode: str = "auto", db=None) -> list[tuple[str, str]]:
    """Files best matching the query as (path, best chunk), best first.
    auto (what the tool uses): embedding order, keyword hits for chunks not embedded yet, keyword for everything if
    the embedder is down. keyword / embedding / fused (RRF of both over all chunks) are for eval/retrieval.py."""
    if db is None:
        with closing(_db()) as db:
            return rank(query, roots, mode, db)
    if mode == "keyword":
        chunk_ids = keyword_rank(db, query, roots)
    elif mode == "embedding":
        chunk_ids = embedding_rank(db, query, roots)
    elif mode == "fused":
        chunk_ids = rrf(keyword_rank(db, query, roots), embedding_rank(db, query, roots))
    else:
        try:  # the two lists are disjoint, so RRF interleaves them rank by rank, embedding first
            chunk_ids = rrf(embedding_rank(db, query, roots), keyword_rank(db, query, roots, unembedded=True))
        except Exception:
            chunk_ids = keyword_rank(db, query, roots)
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
    if LOCK.acquire(blocking=False):
        try:
            left, up = update(roots, time.monotonic() + BUDGET)
        finally:
            LOCK.release()
    else:  # the background indexer is at work: search what is there
        left, up = -1, embedder_up()
    hits = rank(query, roots)[:TOP]
    out = files.listing("", [f'{p}: "...{snippet(t, query)}..."' for p, t in hits])
    if not up:
        out += "\n(Matched by keywords only: the embedding model isn't running.)"
    if left:
        out += f"\n(Still indexing: {'some' if left < 0 else left} files not searched yet. Ask again in a minute.)"
    return out
