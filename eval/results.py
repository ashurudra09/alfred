"""RESULTS.md from the committed reports (Phase 9): `uv run python -m eval.results`.

Deterministic: reads only eval/reports/ and eval/bfcl/score/, no timestamps, so rerunning it changes nothing.
"""

import json
import math
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from alfred.agent.backends import ROOT  # noqa: E402
from alfred.contracts.tools import REGISTRY  # noqa: E402
from eval.run import load_set  # noqa: E402

REPORTS = ROOT / "eval" / "reports"
BFCL_SCORE = ROOT / "eval" / "bfcl" / "score"
OUT = ROOT / "RESULTS.md"
FIG = ROOT / "docs" / "confusion_alfred-2b-v2-q4.png"
DECISIONS = ["tool_call", "direct", "ask", "cannot", "refuse"]
BFCL_CATS = [("simple_python", "non_live"), ("multiple", "non_live"), ("parallel", "non_live"),
             ("irrelevance", "non_live"), ("live_relevance", "live")]
SYSTEMS = [  # (report name, description) in table order
    ("base-2b-q8", "Qwen3.5-2B base, Q8_0"),
    ("alfred-2b-v1-q8", "SFT v1, Q8_0"),
    ("alfred-2b-v1-q4", "SFT v1, Q4_K_M"),
    ("alfred-2b-v2-f16", "SFT v2, F16 (unquantized)"),
    ("alfred-2b-v2-q8", "SFT v2, Q8_0"),
    ("alfred-2b-v2-q4", "SFT v2, Q4_K_M (shipped)"),
    ("alfred-2b-v3-q4", "SFT v3, Q4_K_M"),
    ("cloud-gpt-oss-120b", "gpt-oss-120b (cloud, Groq)"),
]


def report(system: str, test_set: str) -> dict | None:
    p = REPORTS / f"{system}_{test_set}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n (better than ±1.96·SE near 0% or 100%)."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    mid, half = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (mid - half) / (1 + z * z / n), (mid + half) / (1 + z * z / n)


def ci(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{100 * lo:.1f}–{100 * hi:.1f}"


def ci_items(items) -> str:
    return ci(sum(i["ok"] for i in items), len(items))


def mcnemar(a: list[bool], b: list[bool]) -> tuple[int, int, float]:
    """Exact (binomial) McNemar test on paired outcomes. Returns (only a right, only b right, two-sided p)."""
    only_a = sum(x and not y for x, y in zip(a, b))
    only_b = sum(y and not x for x, y in zip(a, b))
    n = only_a + only_b
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(only_a, only_b) + 1)) / 2 ** n) if n else 1.0
    return only_a, only_b, p


PAIRS = [  # (system a, system b, test set, what it shows)
    ("alfred-2b-v2-q4", "base-2b-q8", "indomain", "fine-tuning helps"),
    ("alfred-2b-v2-q4", "cloud-gpt-oss-120b", "indomain", "student vs its 120B teacher"),
    ("alfred-2b-v3-q4", "alfred-2b-v2-q4", "indomain", "v3 vs v2"),
    ("alfred-2b-v2-q4", "alfred-2b-v2-q8", "indomain", "Q4 quantization cost"),
    ("alfred-2b-v3-q4", "alfred-2b-v2-q4", "safety", "v3 vs v2"),
    ("alfred-2b-v3-q4", "alfred-2b-v2-q4", "regressions", "v3 vs v2"),
]


def paired() -> list[tuple]:
    out = []
    for a, b, s, what in PAIRS:
        ra, rb = report(a, s), report(b, s)
        if ra and rb:
            ok_a, ok_b = ({i["id"]: i["ok"] for i in r["items"]} for r in (ra, rb))
            ids = [i for i in ok_a if i in ok_b]
            out.append((a, b, s, what) + mcnemar([ok_a[i] for i in ids], [ok_b[i] for i in ids]))
    return out


def paired_rows(pairs) -> list[str]:
    desc = dict(SYSTEMS)
    return ["| A | B | Set | Question | A right, B wrong | B right, A wrong | Exact McNemar p |",
            "|---|---|---|---|---|---|---|"] + [
        f"| {desc[a]} | {desc[b]} | {s} | {what} | {x} | {y} | {p:.2g} |" for a, b, s, what, x, y, p in pairs]


LOOK = ("list_directory", "search_files")


def look_first(items) -> list[dict]:
    """Misses where a write tool was expected and the model called a read-only listing/search first instead."""
    return [i for i in items if not i["ok"] and i["label"] in LOOK
            and REGISTRY.get(i["expected_label"], {}).get("needs_confirmation")]


def look_first_rows() -> list[str]:
    rows = ["| System | Misses | Looked first (write expected, listed/searched instead) | Accuracy | "
            "Accuracy counting a look-first as right | 95% CI |", "|---|---|---|---|---|---|"]
    for name in ("alfred-2b-v2-q4", "alfred-2b-v3-q4", "cloud-gpt-oss-120b"):
        items = report(name, "indomain")["items"]
        ok, n, look = sum(i["ok"] for i in items), len(items), len(look_first(items))
        rows.append(f"| {dict(SYSTEMS)[name]} | {n - ok} | {look} | {pct(ok / n)} | {pct((ok + look) / n)} | "
                    f"{ci(ok + look, n)} |")
    return rows


def indomain_table() -> list[str]:
    rows = ["| System | In-domain accuracy | 95% CI | Decision macro-F1 | Ask recall | Tool accuracy | Args score | "
            "Median first token | Report |", "|---|---|---|---|---|---|---|---|---|"]
    for name, desc in SYSTEMS:
        r = report(name, "indomain")
        if not r:
            continue
        m, lat = r["metrics"], r.get("latency", {})
        ttft = f"{lat['ttft_median']:.1f} s" if r["backend"] == "local" and lat.get("ttft_median") else "–"
        rows.append(f"| {desc} | {pct(m['accuracy'])} | {ci_items(r['items'])} | {m['decision_macro_f1']:.3f} | "
                    f"{pct(m['per_decision']['ask']['recall'])} | {pct(m['tool_accuracy'])} | "
                    f"{m['args_score']:.3f} | {ttft} | [link](eval/reports/{name}_indomain.md) |")
    return rows


def regression_rows() -> list[str]:
    rows = ["| System | Regression accuracy | 95% CI | Decision accuracy | Args score | Report |",
            "|---|---|---|---|---|---|"]
    for name, desc in SYSTEMS:
        r = report(name, "regressions")
        if r:
            m = r["metrics"]
            rows.append(f"| {desc} | {pct(m['accuracy'])} | {ci_items(r['items'])} | {pct(m['decision_accuracy'])} | "
                        f"{m['args_score']:.3f} | "
                        f"[link](eval/reports/{name}_regressions.md) |")
    return rows


def safety_rows() -> list[str]:
    """Refusal rate on harmful requests, over-refusal on benign ones (incl. borderline), injection items."""
    expected = {t.id: t for t in load_set("safety")}
    rows = ["| System | Safety accuracy | 95% CI | Harmful refused | Benign over-refused | Injection items handled | "
            "Report |", "|---|---|---|---|---|---|---|"]
    for name, desc in SYSTEMS:
        r = report(name, "safety")
        if not r:
            continue
        items = r["items"]
        harmful = [i for i in items if expected[i["id"]].expected_decision == "refuse"]
        benign = [i for i in items if expected[i["id"]].expected_decision != "refuse"]
        inj = [i for i in items if "injection" in expected[i["id"]].tags]
        refused = sum(i["decision"] == "refuse" for i in harmful)
        over = sum(i["decision"] == "refuse" for i in benign)
        rows.append(f"| {desc} | {pct(r['metrics']['accuracy'])} | {ci_items(items)} | {refused}/{len(harmful)} | "
                    f"{over}/{len(benign)} | "
                    f"{sum(i['ok'] for i in inj)}/{len(inj)} | [link](eval/reports/{name}_safety.md) |")
    return rows


def when2call(which: str) -> dict | None:
    """Official When2Call MCQ metrics from the per-item log-likelihoods (eval/when2call/bench.py)."""
    p = REPORTS / f"when2call_{which}.json"
    if not p.exists():
        return None
    rows = json.loads(p.read_text(encoding="utf-8"))
    pred = [max(range(4), key=lambda k: r["lls"][k]) for r in rows]
    pred_norm = [max(range(4), key=lambda k: r["lls"][k] / r["lens"][k]) for r in rows]
    gold = [r["gold"] for r in rows]
    f1s = []
    for c in range(4):  # macro-F1 over answer types, from the unnormalized prediction (lm-eval's f1 pairs)
        tp = sum(p == g == c for p, g in zip(pred, gold))
        fp = sum(p == c != g for p, g in zip(pred, gold))
        fn = sum(g == c != p for p, g in zip(pred, gold))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0)
    no_tools = [p for p, r in zip(pred, rows) if r["no_tools"] and r["names"][r["gold"]] == "cannot_answer"]
    return {"n": len(rows), "acc": sum(p == g for p, g in zip(pred, gold)) / len(rows),
            "acc_norm": sum(p == g for p, g in zip(pred_norm, gold)) / len(rows), "macro_f1": sum(f1s) / 4,
            "hallucination": sum(p == 1 for p in no_tools) / len(no_tools) if no_tools else None,
            "pred": Counter(rows[0]["names"][p] for p in pred)}


def bfcl(system: str) -> dict | None:
    out = {}
    for cat, group in BFCL_CATS:
        p = BFCL_SCORE / system / group / f"BFCL_v4_{cat}_score.json"
        if not p.exists():
            return None
        head = json.loads(p.read_text(encoding="utf-8").splitlines()[0])
        out[cat] = (head["accuracy"], head["total_count"])
    return out


def confusion_png(system="alfred-2b-v2-q4"):
    r = report(system, "indomain")
    expected = {t.id: t.expected_decision for t in load_set("indomain")}
    counts = Counter((expected[i["id"]], i["decision"]) for i in r["items"])
    labels = [d for d in DECISIONS if any(k[0] == d or k[1] == d for k in counts)]
    grid = [[counts[(t, p)] for p in labels] for t in labels]
    fig, ax = plt.subplots(figsize=(5, 4.2), dpi=120)
    ax.imshow(grid, cmap="Blues")
    for y, row in enumerate(grid):
        for x, v in enumerate(row):
            ax.text(x, y, v, ha="center", va="center", color="white" if v > max(map(max, grid)) / 2 else "black")
    ax.set_xticks(range(len(labels)), labels, rotation=30), ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("predicted decision"), ax.set_ylabel("expected decision")
    ax.set_title(f"{system}: in-domain decisions (n={len(r['items'])})")
    fig.tight_layout()
    fig.savefig(FIG, metadata={"Software": None})  # no version string: the PNG is byte-stable
    plt.close(fig)


def review_lines() -> list[str]:
    """Who reviewed the in-domain set, and how well the keyword classifier agrees with a blind human label."""
    from eval.review import TEXT_OUT, item_hash, load_reviews
    items, reviews = load_set("indomain"), load_reviews()
    count = {k: sum(reviews.get(k, {}).get(i.id) == item_hash(i) for i in items) for k in ("indomain", "indomain:owner")}
    out = [f"Test-set review: in-domain items checked by an AI agent {count['indomain']}/{len(items)}; second pass "
           f"by an AI agent, with the owner deciding the items it flagged as ambiguous, "
           f"{count['indomain:owner']}/{len(items)}. The two parallel items (`multi-17`, `multi-18`) need both "
           f"calls in one turn, so a system that makes them one after the other fails them."]
    if TEXT_OUT.exists():
        a = json.loads(TEXT_OUT.read_text(encoding="utf-8"))["agreement"]
        out.append(f"Scorer check: on {a['n']} text replies labelled by an AI agent (the owner deciding borderline ones), "
                   f"the keyword classifier agrees "
                   f"on **{a['agree']}/{a['n']}** ({ci(a['agree'], a['n'])}% CI); per class "
                   + ", ".join(f"{c} {v['agree']}/{v['n']}" for c, v in a["per_class"].items()) + ".")
    else:
        out.append("Scorer check: 20 hand-rescored items agreed 20/20 (no refusals in that sample); a blind 100-reply "
                   "check (`uv run python -m eval.review --text`) is not done yet.")
    return out


def main():
    lines = ["# Results", "",
             "Generated by `uv run python -m eval.results` from the reports in `eval/reports/` and "
             "`eval/bfcl/score/`; every number links to its report. Laptop: Windows 11, CPU only (llama.cpp).", "",
             f"## In-domain test set ({len(load_set('indomain'))} items, our 25 tools)", ""] + indomain_table()
    lines += [""] + [x for line in review_lines() for x in (line, "")][:-1]
    lines += ["", "Quantization: compare the three **SFT v2** rows (F16 → Q8_0 → Q4_K_M). 95% CI = Wilson score "
              "interval on accuracy; one run per system (greedy decoding), so it covers test-set sampling only, not "
              "training seeds.", "",
              "### Why the cloud model scores lower", "",
              "gpt-oss-120b is the teacher that wrote most of the synthetic training data, run zero-shot. Many of its "
              "misses are a reasonable habit the test set marks wrong: asked to move or copy a file, it lists or "
              "searches the folder before acting.", ""] + look_first_rows()
    v2, cloud = (report(s, "indomain")["items"] for s in ("alfred-2b-v2-q4", "cloud-gpt-oss-120b"))
    acc = lambda items, extra=0: 100 * (sum(i["ok"] for i in items) + extra) / len(items)  # noqa: E731
    raw_gap, fair_gap = acc(v2) - acc(cloud), acc(v2) - acc(cloud, len(look_first(cloud)))
    lines += ["", f"Forgiving that habit shrinks the gap from {raw_gap:.1f} to {fair_gap:.1f} points and the intervals "
              "overlap: on this "
              "tool set the fine-tuned 2B is **on par with** its 120B teacher, not clearly better. Part of the raw gap "
              "is the test set's one-call convention, which the student was trained on.", "",
              "### Paired comparisons (same items, exact McNemar test)", ""] + paired_rows(pairs := paired())
    weak = [f"{what} ({s}, p={p:.2g})" for _, _, s, what, _, _, p in pairs if p >= 0.05]
    lines += ["", "A p-value under 0.05 means the difference is unlikely to be item-sampling luck. **Not significant:** "
              + "; ".join(weak) + ".", "",
              f"![decision confusion matrix]({FIG.relative_to(ROOT).as_posix()})", "",
              "## Safety (48 items) and prompt injection", ""] + safety_rows()
    lines.append("")
    for v in ("v2", "v3"):
        e2e = json.loads((REPORTS / f"e2e_alfred-2b-{v}-q4.json").read_text(encoding="utf-8"))
        lines += [f"End-to-end through the real tools (SFT {v} Q4): **{e2e['passed']}/{e2e['n']}** tasks "
                  f"(95% CI {ci(e2e['passed'], e2e['n'])}%), "
                  f"prompt-injection files resisted **{e2e['injection_resisted']}/{e2e['injection_n']}**, unconfirmed "
                  f"writes / overwrites / permanent deletes = {' / '.join(str(v) for v in e2e['invariants'].values())} "
                  f"([report](eval/reports/e2e_alfred-2b-{v}-q4.md)).", ""]
    lines += ["## Regression set (46 items from UI testing and probe runs, data/to_fix.md)", "",
              "Each model is scored with the system prompt it was trained on (v2: 1.1, v3: 1.2).", ""]
    lines += regression_rows() + [""]

    w = {k: when2call(k) for k in ("base", "sft", "v3")}
    if all(w.values()):
        lines += ["## When2Call MCQ test (public benchmark: call / ask / answer / can't)", "",
                  "| Model (full precision) | n | Accuracy | Acc-norm | Macro-F1 | Tool hallucination ↓ |",
                  "|---|---|---|---|---|---|"]
        for k, desc in (("base", "Qwen3.5-2B base"), ("sft", "SFT v2"), ("v3", "SFT v3")):
            m = w[k]
            lines.append(f"| {desc} | {m['n']} | {pct(m['acc'])} | {pct(m['acc_norm'])} | {m['macro_f1']:.3f} | "
                         f"{pct(m['hallucination'])} |")
        lines += ["", "Log-likelihood scoring as in the official lm-eval task, Qwen3.5 chat template "
                  "([eval/when2call/bench.py](eval/when2call/bench.py)). SFT used When2Call's *train* split; "
                  "this is the held-out *test* split.", ""]

    b = {s: bfcl(s) for s in ("base-2b-q8", "alfred-2b-v2-q8", "alfred-2b-v3-q8")}
    if all(b.values()):
        lines += ["## BFCL v4 subset (general function calling: did fine-tuning hurt it?)", "",
                  "| Category | n | Base Q8_0 | SFT v2 Q8_0 | SFT v3 Q8_0 |", "|---|---|---|---|---|"]
        for cat, _ in BFCL_CATS:
            n = b["base-2b-q8"][cat][1]
            lines.append(f"| {cat} | {n} | " + " | ".join(pct(v[cat][0]) for v in b.values()) + " |")
        mean = [sum(a for a, _ in v.values()) / len(v) for v in b.values()]
        lines += ["| **unweighted mean** | | " + " | ".join(f"**{pct(m)}**" for m in mean) + " |", "",
                  "Pinned `bfcl-eval==2026.3.23`, non-thinking mode, AST checker; Qwen3.5 handler in "
                  "[eval/bfcl/run.py](eval/bfcl/run.py). Not comparable to the vendor's 43.6 (full BFCL v4, "
                  "thinking mode).", ""]

    confusion_png()
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.name} and {FIG.name}")


if __name__ == "__main__":
    main()
