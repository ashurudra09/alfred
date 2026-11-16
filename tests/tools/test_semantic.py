import ctypes
import os
import re
import sqlite3
from contextlib import closing

import numpy as np
import pytest

from alfred.tools import files, memory, semantic

SYN = {"car": "vehicle", "automobile": "vehicle", "upkeep": "maintenance", "servicing": "maintenance"}


def fake_embed(texts, timeout=0):
    """Hashed bag of words with a few synonyms folded together: paraphrases match, keywords don't."""
    v = np.zeros((len(texts), 64), dtype=np.float32)
    for i, t in enumerate(texts):
        for w in re.findall(r"[a-z]+", t.split("text: ")[-1].split("query: ")[-1].lower()):
            v[i, hash(SYN.get(w, w)) % 64] += 1
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


@pytest.fixture
def docs(sandbox, monkeypatch):
    monkeypatch.setattr(memory, "embed_many", fake_embed)
    d = sandbox["Documents"]
    (d / "auto.md").write_text("Automobile servicing: change the oil every 10,000 km.")
    (d / "recipe.txt").write_text("Bake the bread at 220 degrees for forty minutes.")
    return sandbox


def indexed() -> set[str]:
    with closing(sqlite3.connect(semantic.home() / "semantic.db")) as db:
        return {os.path.basename(p) for (p,) in db.execute("SELECT path FROM files")}


def test_paraphrase_found_and_fused(docs):
    out = semantic.search_by_meaning("car upkeep", "Documents")
    assert out.splitlines()[1].startswith(str(docs["Documents"] / "auto.md")) and "keywords only" not in out
    roots = [docs["Documents"].resolve()]
    assert semantic.rank("car upkeep", roots, "keyword") == []  # no shared words
    assert semantic.rank("bread", roots, "keyword")[0][0].endswith("recipe.txt")


def test_incremental_reindex(docs, monkeypatch):
    roots = [docs["Documents"].resolve()]
    semantic.update(roots, float("inf"))
    reads = []
    monkeypatch.setattr(files, "_text", lambda p: reads.append(p.name) or p.read_text())
    semantic.update(roots, float("inf"))
    assert reads == []  # nothing changed, nothing re-read
    (docs["Documents"] / "recipe.txt").write_text("Knead the dough twice.")
    os.utime(docs["Documents"] / "recipe.txt", (1, 1))
    semantic.update(roots, float("inf"))
    assert reads == ["recipe.txt"]
    assert semantic.rank("bread", roots, "keyword") == [] and semantic.rank("dough", roots, "keyword")


def test_sensitive_hidden_and_deleted(docs):
    d = docs["Documents"]
    (d / "secret_note.txt").write_text("hidden car notes")
    ctypes.windll.kernel32.SetFileAttributesW(str(d / "secret_note.txt"), 0x2)  # FILE_ATTRIBUTE_HIDDEN
    semantic.search_by_meaning("car", "Documents")
    names = indexed()
    assert {"auto.md", "recipe.txt", "cv.md"} <= names
    assert not names & {".env", "id_rsa", "secret_note.txt"}
    (d / "auto.md").unlink()
    assert "auto.md" not in semantic.search_by_meaning("car upkeep", "Documents") and "auto.md" not in indexed()


def test_budget_and_size_cap(docs, monkeypatch):
    (docs["Documents"] / "big.txt").write_text("x" * (semantic.MAX_BYTES + 1))
    monkeypatch.setattr(semantic, "BUDGET", -1)  # deadline already passed: nothing indexed yet
    assert "Still indexing" in semantic.search_by_meaning("car", "Documents")
    monkeypatch.setattr(semantic, "BUDGET", 20)
    semantic.search_by_meaning("car", "Documents")
    assert "big.txt" not in indexed()


def test_keyword_fallback_without_embedder(docs, monkeypatch):
    def down(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(memory, "embed_many", down)
    out = semantic.search_by_meaning("bread recipe", "Documents")
    assert "recipe.txt" in out and "keywords only" in out
    monkeypatch.setattr(memory, "embed_many", fake_embed)  # embedder back: missing vectors are filled in
    assert "keywords only" not in semantic.search_by_meaning("car upkeep", "Documents")


def test_split():
    assert semantic.split("a\n\nb") == ["a b"]
    chunks = semantic.split("word " * 1000)
    assert all(len(c) <= semantic.CHUNK for c in chunks) and len(chunks) == 5
    assert semantic.rrf([1, 2], [2, 3]) == [2, 1, 3]


def test_unembedded_chunks_found_by_keyword(docs, monkeypatch):
    """A file indexed while the embedder was down is still found (by keyword) once it is back, next to embedding hits."""
    roots = [docs["Documents"].resolve()]
    semantic.update(roots, float("inf"))
    monkeypatch.setattr(semantic, "_embed_missing", lambda db, deadline: True)  # new files get text but no vector
    (docs["Documents"] / "tax.txt").write_text("Income tax return deadline is in July.")
    semantic.update(roots, float("inf"))
    names = lambda mode: [os.path.basename(p) for p, _ in semantic.rank("tax deadline", roots, mode)]
    assert "tax.txt" in names("auto")[:2]  # interleaved: best embedding hit, then best keyword hit
    assert "tax.txt" not in names("embedding")


def test_min_cos_gives_no_match(docs, monkeypatch):
    monkeypatch.setattr(semantic, "MIN_COS", 0.99)
    assert semantic.search_by_meaning("quarterly earnings forecast", "Documents") == "No matching files found."


def test_embed_cache_and_background_index(docs, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(memory, "embed_many", lambda texts, timeout=0: calls.append(len(texts)) or fake_embed(texts))
    monkeypatch.setenv("ALFRED_EMBED_CACHE", str(tmp_path / "cache.db"))
    semantic.index_all()  # indexes every known folder, then returns
    assert {"auto.md", "recipe.txt", "notes.txt"} <= indexed() and sum(calls) > 0
    (semantic.home() / "semantic.db").unlink()  # a fresh home with the same files: every vector comes from the cache
    calls.clear()
    semantic.index_all()
    assert calls == [] and "auto.md" in semantic.search_by_meaning("car upkeep", "Documents")
