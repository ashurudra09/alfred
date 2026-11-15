"""Retrieval evaluation for search_by_meaning (track 1B, step B4). No LLM involved.

Corpus and labels: a seeded subset of SciFact (Wadden et al. 2020) as packaged by BEIR (Thakur et al. 2021):
claims written by experts are the queries, the abstracts that support or refute them are the relevant documents.
Licences (github.com/allenai/scifact LICENSE.md, checked 2026-11-15): claims CC BY 4.0, abstracts ODC-By 1.0
(from S2ORC). Distractors are random other abstracts from the same corpus.

Queries are split by lexical overlap with their relevant abstract (share of the query's content words found in
it): the lower half is the "paraphrased" set, where keyword matching has the least to go on.

  uv run python -m eval.retrieval build <BEIR scifact dir>   # writes eval/testsets/retrieval_scifact.jsonl
  uv run python -m eval.retrieval                            # needs Ollama; writes eval/reports/retrieval_scifact.json
"""

import json
import os
import random
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBSET = ROOT / "eval" / "testsets" / "retrieval_scifact.jsonl"
REPORT = ROOT / "eval" / "reports" / "retrieval_scifact.json"
N_QUERIES, N_DOCS, SEED = 150, 300, 1
MODES = ("keyword", "embedding", "fused")
STOP = set("the and for with are was were that this from has have not but than into its their also can may".split())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[^\W_]+", text.casefold()) if len(w) > 2 and w not in STOP}


def overlap(query: str, doc: str) -> float:
    q = words(query)
    return len(q & words(doc)) / len(q) if q else 0.0


def build(beir: Path):
    rng = random.Random(SEED)
    corpus = {d["_id"]: d for d in map(json.loads, (beir / "corpus.jsonl").open(encoding="utf-8"))}
    queries = {q["_id"]: q["text"] for q in map(json.loads, (beir / "queries.jsonl").open(encoding="utf-8"))}
    rel: dict[str, list[str]] = {}
    for line in (beir / "qrels" / "test.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        qid, did, _ = line.split("\t")
        rel.setdefault(qid, []).append(did)
    picked = sorted(rng.sample(sorted(rel, key=int), N_QUERIES), key=int)
    docs = sorted({d for q in picked for d in rel[q]}, key=int)
    docs += rng.sample(sorted(set(corpus) - set(docs), key=int), N_DOCS - len(docs))
    with SUBSET.open("w", encoding="utf-8", newline="\n") as f:
        for d in sorted(docs, key=int):
            f.write(json.dumps({"doc": d, "title": corpus[d]["title"], "text": corpus[d]["text"]}) + "\n")
        for q in picked:
            text = lambda d: corpus[d]["title"] + " " + corpus[d]["text"]
            f.write(json.dumps({"query": q, "text": queries[q], "relevant": rel[q],
                                "overlap": round(max(overlap(queries[q], text(d)) for d in rel[q]), 3)}) + "\n")
    print(f"wrote {SUBSET}: {len(docs)} documents, {len(picked)} queries")


def load():
    rows = [json.loads(line) for line in SUBSET.read_text(encoding="utf-8").splitlines()]
    return [r for r in rows if "doc" in r], [r for r in rows if "query" in r]


def metrics(ranks: list[int | None]) -> dict:
    """ranks: 1-based rank of the first relevant document per query (None = not in the results)."""
    n = len(ranks)
    return {"n": n, "recall@1": sum(r == 1 for r in ranks if r) / n, "recall@5": sum(r <= 5 for r in ranks if r) / n,
            "mrr": sum(1 / r for r in ranks if r) / n}


def run() -> dict:
    docs, queries = load()
    with tempfile.TemporaryDirectory() as tmp:
        folder, home = Path(tmp) / "Documents", Path(tmp) / "home"
        folder.mkdir()
        home.mkdir()
        (home / "config.json").write_text(json.dumps({"folders": {"Documents": str(folder)}}))
        os.environ["ALFRED_HOME"] = str(home)
        for d in docs:  # file names carry no title words, so only the text is matched
            (folder / f"{d['doc']}.txt").write_text(f"{d['title']}\n\n{d['text']}", encoding="utf-8")
        from alfred.tools import semantic
        if not semantic.embedder_up():
            sys.exit("Ollama (embeddinggemma) is not running")
        roots = [folder.resolve()]
        t = time.perf_counter()
        left, _ = semantic.update(roots, float("inf"))
        index_s = time.perf_counter() - t
        db = semantic._db()
        chunks = db.execute("SELECT count(*) FROM chunks").fetchone()[0]
        median = sorted(q["overlap"] for q in queries)[len(queries) // 2]
        out = {"documents": len(docs), "chunks": chunks, "queries": len(queries), "index_seconds": round(index_s, 1),
               "overlap_median": median, "zero_overlap": sum(q["overlap"] == 0 for q in queries), "modes": {}}
        for mode in MODES:
            ranks, lat = [], []
            for q in queries:
                t = time.perf_counter()
                got = [Path(p).stem for p, _ in semantic.rank(q["text"], roots, mode, db)]
                lat.append(time.perf_counter() - t)
                ranks.append(next((i for i, d in enumerate(got, 1) if d in q["relevant"]), None))
            low = [r for r, q in zip(ranks, queries) if q["overlap"] < median]
            out["modes"][mode] = {"all": metrics(ranks), "paraphrased": metrics(low),
                                  "query_ms": round(1000 * sum(lat) / len(lat))}
        db.close()
    return out


def main():
    if sys.argv[1:2] == ["build"]:
        return build(Path(sys.argv[2]))
    rep = run()
    REPORT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
