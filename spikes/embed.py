"""Spike 1d: pick the memory embedding model. Times each Ollama embedder and checks recall top-1 on a tiny set.

Usage: uv run python spikes/embed.py
"""

import json
import math
import time

from common import post

MODELS = ["embeddinggemma", "nomic-embed-text"]
FACTS = ["My resume is in D:\\docs\\resume", "My sister's birthday is 14 March", "I use VS Code for Python",
         "The project repo is at C:\\work\\alfred", "My Wi-Fi at home is called Batcave",
         "I prefer dark mode", "Tax documents are in Documents\\taxes 2026"]
QUERIES = [("where's my CV folder", 0), ("when is my sister's bday", 1), ("which editor do I use", 2),
           ("alfred repo location", 3), ("home wifi name", 4), ("tax papers", 6)]


def embed(model, texts):
    with post("/api/embed", {"model": model, "input": texts}) as r:
        return json.load(r)["embeddings"]


def cos(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.hypot(*a) * math.hypot(*b))


for model in MODELS:
    embed(model, ["warm up"])
    t0 = time.perf_counter()
    fv = embed(model, FACTS)
    t_batch = time.perf_counter() - t0
    t0 = time.perf_counter()
    qv = [embed(model, [q])[0] for q, _ in QUERIES]
    t_query = (time.perf_counter() - t0) / len(QUERIES)
    hits = sum(max(range(len(FACTS)), key=lambda i: cos(v, fv[i])) == want for v, (_, want) in zip(qv, QUERIES))
    print(f"{model}: dim {len(fv[0])}, top-1 {hits}/{len(QUERIES)}, {t_query * 1000:.0f} ms/query, "
          f"{t_batch * 1000:.0f} ms for {len(FACTS)} facts")
