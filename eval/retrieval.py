"""Retrieval evaluation for search_by_meaning (track 1B, step B4). No LLM involved.

Corpus and labels: seeded subsets of SciFact (Wadden et al. 2020) as packaged by BEIR (Thakur et al. 2021):
claims written by experts are the queries, the abstracts that support or refute them are the relevant documents.
Licences (github.com/allenai/scifact LICENSE.md, checked 2026-11-15): claims CC BY 4.0, abstracts ODC-By 1.0
(from S2ORC). Distractors are random other abstracts from the same corpus.

Two subsets of 300 abstracts each (plan amendment 2):
- dev: 150 test-split claims. The ranking method, the embedder prompts and the MIN_COS cut-off are chosen here.
- test: the other 150 test-split claims, run once those choices are fixed. RESULTS.md reports this one.
Each also has 75 unanswerable claims (from SciFact's train split, none of whose abstracts are in the subset) to
measure how often a cosine cut-off returns nothing when nothing fits. The rule, fixed before the test run: the
5th percentile, on dev, of the cosine of the first relevant chunk (0.346). It was tried and not shipped (plan
amendment 7), so `test` takes the tried value from TRIED_CUTOFF, not from the tool.

Answerable claims are also split by lexical overlap with their abstract (share of the claim's content words found
in it): the lower half is the "paraphrased" set, where keyword matching has the least to go on.

  uv run python -m eval.retrieval build <BEIR scifact dir>   # writes eval/testsets/retrieval_scifact_{dev,test}.jsonl
  uv run python -m eval.retrieval dev                        # needs Ollama; eval/reports/retrieval_scifact_dev.json
  uv run python -m eval.retrieval test                       # eval/reports/retrieval_scifact_test.json
"""

import json
import os
import random
import re
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SUBSET = str(ROOT / "eval" / "testsets" / "retrieval_scifact_{}.jsonl")
REPORT = str(ROOT / "eval" / "reports" / "retrieval_scifact_{}.json")
CACHE = ROOT / "runs" / "v4" / "embed_cache.db"  # gitignored
N_QUERIES, N_DOCS, N_NEG, SEED = 150, 300, 75, 1
MODES = ("keyword", "embedding", "fused")
TRIED_CUTOFF = 0.346
STOP = set("the and for with are was were that this from has have not but than into its their also can may".split())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[^\W_]+", text.casefold()) if len(w) > 2 and w not in STOP}


def overlap(query: str, doc: str) -> float:
    q = words(query)
    return len(q & words(doc)) / len(q) if q else 0.0


def qrels(path: Path) -> dict[str, list[str]]:
    rel: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        qid, did, _ = line.split("\t")
        rel.setdefault(qid, []).append(did)
    return rel


def build(beir: Path):
    rng = random.Random(SEED)
    corpus = {d["_id"]: d for d in map(json.loads, (beir / "corpus.jsonl").open(encoding="utf-8"))}
    queries = {q["_id"]: q["text"] for q in map(json.loads, (beir / "queries.jsonl").open(encoding="utf-8"))}
    rel, train = qrels(beir / "qrels" / "test.tsv"), qrels(beir / "qrels" / "train.tsv")
    text = lambda d: corpus[d]["title"] + " " + corpus[d]["text"]

    def subset(picked: list[str]) -> list[str]:
        docs = sorted({d for q in picked for d in rel[q]}, key=int)
        return docs + rng.sample(sorted(set(corpus) - set(docs), key=int), N_DOCS - len(docs))

    dev_q = sorted(rng.sample(sorted(rel, key=int), N_QUERIES), key=int)  # same draws as the first version of this file
    dev_docs = subset(dev_q)
    test_q = sorted(set(rel) - set(dev_q), key=int)
    test_docs = subset(test_q)
    used: set[str] = set()
    for name, picked, docs in (("dev", dev_q, dev_docs), ("test", test_q, test_docs)):
        free = [q for q in sorted(train, key=int) if q not in used and not set(train[q]) & set(docs)]
        neg = sorted(rng.sample(free, N_NEG), key=int)
        used |= set(neg)
        with open(SUBSET.format(name), "w", encoding="utf-8", newline="\n") as f:
            for d in sorted(docs, key=int):
                f.write(json.dumps({"doc": d, "title": corpus[d]["title"], "text": corpus[d]["text"]}) + "\n")
            for q in picked:
                f.write(json.dumps({"query": q, "text": queries[q], "relevant": rel[q],
                                    "overlap": round(max(overlap(queries[q], text(d)) for d in rel[q]), 3)}) + "\n")
            for q in neg:
                f.write(json.dumps({"query": q, "text": queries[q], "relevant": []}) + "\n")
        print(f"wrote {SUBSET.format(name)}: {len(docs)} documents, {len(picked)} claims, {len(neg)} unanswerable")


def load(name: str):
    rows = [json.loads(line) for line in Path(SUBSET.format(name)).read_text(encoding="utf-8").splitlines()]
    return ([r for r in rows if "doc" in r], [r for r in rows if r.get("relevant")],
            [r for r in rows if r.get("relevant") == []])


def metrics(ranks: list[int | None]) -> dict:
    """ranks: 1-based rank of the first relevant document per query (None = not in the results)."""
    n = len(ranks)
    return {"n": n, "recall@1": sum(r == 1 for r in ranks if r) / n, "recall@5": sum(r <= 5 for r in ranks if r) / n,
            "mrr": sum(1 / r for r in ranks if r) / n}


def cached() -> int:
    if not CACHE.exists():
        return 0
    with closing(sqlite3.connect(CACHE)) as c:
        return c.execute("SELECT count(*) FROM e").fetchone()[0]


def run(name: str, prompts: bool = True, cutoff: float | None = None) -> dict:
    """Index the subset in a temporary home and score it. cutoff=None: also derive the cut-off (dev)."""
    from alfred.tools import semantic
    docs, queries, negatives = load(name)
    if not prompts:
        semantic.QUERY, semantic.DOC = "{}", "{1}"
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    os.environ["ALFRED_EMBED_CACHE"] = str(CACHE)
    with tempfile.TemporaryDirectory() as tmp:
        folder, home = Path(tmp) / "Documents", Path(tmp) / "home"
        folder.mkdir()
        home.mkdir()
        (home / "config.json").write_text(json.dumps({"folders": {"Documents": str(folder)}}))
        os.environ["ALFRED_HOME"] = str(home)
        for d in docs:  # file names carry no title words, so only the text is matched
            (folder / f"{d['doc']}.txt").write_text(f"{d['title']}\n\n{d['text']}", encoding="utf-8")
        if not semantic.embedder_up():
            sys.exit("Ollama (embeddinggemma) is not running")
        roots, before, t = [folder.resolve()], cached(), time.perf_counter()
        semantic.update(roots, float("inf"))
        index_s, fresh = time.perf_counter() - t, cached() - before
        with closing(semantic._db()) as db:
            chunks = db.execute("SELECT count(*) FROM chunks").fetchone()[0]
            doc_of = {i: Path(p).stem for i, p in db.execute("SELECT rowid, path FROM chunks")}
            median = sorted(q["overlap"] for q in queries)[len(queries) // 2]
            out = {"set": name, "prompts": prompts, "documents": len(docs), "chunks": chunks, "queries": len(queries),
                   "unanswerable": len(negatives), "index_seconds": round(index_s, 1), "chunks_embedded_fresh": fresh,
                   "overlap_median": median, "modes": {}}
            if fresh:
                out["chunks_per_second"] = round(fresh / index_s, 2)

            def score(mode: str) -> dict:
                ranks, lat = [], []
                for q in queries:
                    t = time.perf_counter()
                    got = [Path(p).stem for p, _ in semantic.rank(q["text"], roots, mode, db)]
                    lat.append(time.perf_counter() - t)
                    ranks.append(next((i for i, d in enumerate(got, 1) if d in q["relevant"]), None))
                low = [r for r, q in zip(ranks, queries) if q["overlap"] < median]
                return {"all": metrics(ranks), "paraphrased": metrics(low), "query_ms": round(1000 * sum(lat) / len(lat))}

            semantic.MIN_COS = 0.0
            for mode in MODES:
                out["modes"][mode] = score(mode)
            # cosine of the first relevant chunk (answerable) and of the top chunk (unanswerable)
            rel_cos = [next((c for i, c in semantic.embedding_scores(db, q["text"], roots) if doc_of[i] in q["relevant"]),
                            None) for q in queries]
            neg_top = [semantic.embedding_scores(db, q["text"], roots)[0][1] for q in negatives]
            found = [c for c in rel_cos if c is not None]
            if cutoff is None:
                cutoff = round(float(np.percentile(found, 5)), 3)
                out["cutoff_rule"] = "5th percentile of the first relevant chunk's cosine on this set"
            semantic.MIN_COS = out["cutoff"] = cutoff
            out["cosine"] = {"relevant_median": round(float(np.median(found)), 3),
                             "unanswerable_top_median": round(float(np.median(neg_top)), 3)}
            out["with_cutoff"] = score("auto") | {
                "answerable_returning_nothing": sum(not semantic.rank(q["text"], roots, "auto", db) for q in queries),
                "unanswerable_returning_nothing": sum(c < cutoff for c in neg_top)}
    return out


def main():
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        return build(Path(sys.argv[2]))
    if cmd == ["dev"]:
        rep = run("dev")
        rep["no_prompts"] = run("dev", prompts=False)  # ablation: the same index without embeddinggemma's prompts
    elif cmd == ["test"]:
        rep = run("test", cutoff=TRIED_CUTOFF)
    else:
        sys.exit(__doc__)
    Path(REPORT.format(cmd[0])).write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
