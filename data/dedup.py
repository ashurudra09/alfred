"""Contamination guard: drop training examples too close to any test item.

Embeds user messages with the memory embedder (Ollama embeddinggemma, chosen in Phase 1; no torch needed) and
drops a training example when any of its user messages has cosine > THRESHOLD to a test-set user message, or
shares an 8-word sequence with one.

Usage: uv run python -m data.dedup --check     # checks data/out/train.jsonl + val.jsonl, exit 1 on any hit
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np

from alfred.contracts.schemas import Example
from eval.run import load_set

THRESHOLD = 0.9
NGRAM = 8
EMBED_URL, MODEL = "http://127.0.0.1:11434/api/embed", "embeddinggemma"


def embed(texts: list[str]) -> np.ndarray:
    """Unit-normalised embeddings, one row per text."""
    out = []
    for i in range(0, len(texts), 64):
        req = urllib.request.Request(EMBED_URL, json.dumps({"model": MODEL, "input": texts[i:i + 64]}).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            out += json.load(r)["embeddings"]
    v = np.array(out, dtype=np.float32)
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


def ngrams(text: str) -> set[tuple]:
    w = re.findall(r"\w+", text.casefold())
    return {tuple(w[i:i + NGRAM]) for i in range(len(w) - NGRAM + 1)}


class Guard:
    def __init__(self):
        self.tests = sorted({m.content for s in ("indomain", "safety") for it in load_set(s)
                             for m in it.messages if m.role == "user"})
        self.vecs = embed(self.tests)
        self.grams = set().union(*map(ngrams, self.tests))

    def scores(self, texts: list[str]) -> list[tuple[float, str]]:
        """For each text: (max cosine to a test message, that test message)."""
        sims = embed(texts) @ self.vecs.T
        best = sims.argmax(axis=1)
        return [(float(sims[i, j]), self.tests[j]) for i, j in enumerate(best)]

    def filter(self, examples: list[Example]) -> tuple[list[Example], list[dict]]:
        users = [[m.content for m in e.messages if m.role == "user"] for e in examples]
        flat = sorted({u for us in users for u in us})
        sc = dict(zip(flat, self.scores(flat)))
        keep, dropped = [], []
        for e, us in zip(examples, users):
            cos, near = max((sc[u] for u in us), default=(0.0, ""))
            gram = any(ngrams(u) & self.grams for u in us)
            if cos > THRESHOLD or gram:
                dropped.append({"id": e.id, "cos": round(cos, 3), "ngram": gram, "user": us[0], "test": near})
            else:
                keep.append(e)
        return keep, dropped


def main() -> int:
    from data.mix import OUT
    guard, hits = Guard(), 0
    for name in ("train", "val"):
        rows = [json.loads(line) for line in (OUT / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]
        exs = [Example.model_validate(r["example"]) for r in rows]
        _, dropped = guard.filter(exs)
        hits += len(dropped)
        print(f"{name}: {len(exs)} examples, {len(dropped)} near-duplicates of test items")
        for d in dropped[:10]:
            print("  ", d)
    return 1 if hits else 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(main())
    print(__doc__)
