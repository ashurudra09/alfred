"""RESULTS.md from the committed reports (Phase 9): `uv run python -m eval.results`.

Deterministic: reads only eval/reports/ and eval/bfcl/score/, no timestamps, so rerunning it changes nothing.
"""

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from alfred.agent.backends import ROOT  # noqa: E402
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
    ("cloud-gpt-oss-120b", "gpt-oss-120b (cloud, Groq)"),
]


def report(system: str, test_set: str) -> dict | None:
    p = REPORTS / f"{system}_{test_set}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def indomain_table() -> list[str]:
    rows = ["| System | In-domain accuracy | Decision macro-F1 | Ask recall | Tool accuracy | Args score | "
            "Median first token | Report |", "|---|---|---|---|---|---|---|---|"]
    for name, desc in SYSTEMS:
        r = report(name, "indomain")
        if not r:
            continue
        m, lat = r["metrics"], r.get("latency", {})
        ttft = f"{lat['ttft_median']:.1f} s" if r["backend"] == "local" and lat.get("ttft_median") else "–"
        rows.append(f"| {desc} | {pct(m['accuracy'])} | {m['decision_macro_f1']:.3f} | "
                    f"{pct(m['per_decision']['ask']['recall'])} | {pct(m['tool_accuracy'])} | "
                    f"{m['args_score']:.3f} | {ttft} | [link](eval/reports/{name}_indomain.md) |")
    return rows


def safety_rows() -> list[str]:
    """Refusal rate on harmful requests, over-refusal on benign ones (incl. borderline), injection items."""
    expected = {t.id: t for t in load_set("safety")}
    rows = ["| System | Safety accuracy | Harmful refused | Benign over-refused | Injection items handled | Report |",
            "|---|---|---|---|---|---|"]
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
        rows.append(f"| {desc} | {pct(r['metrics']['accuracy'])} | {refused}/{len(harmful)} | {over}/{len(benign)} | "
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


def main():
    lines = ["# Results", "",
             "Generated by `uv run python -m eval.results` from the reports in `eval/reports/` and "
             "`eval/bfcl/score/`; every number links to its report. Laptop: Windows 11, CPU only (llama.cpp).", "",
             "## In-domain test set (278 items, our 25 tools)", ""] + indomain_table()
    lines += ["", "Quantization: compare the three **SFT v2** rows (F16 → Q8_0 → Q4_K_M).", "",
              f"![decision confusion matrix]({FIG.relative_to(ROOT).as_posix()})", "",
              "## Safety (48 items) and prompt injection", ""] + safety_rows()
    e2e = json.loads((REPORTS / "e2e_alfred-2b-v2-q4.json").read_text(encoding="utf-8"))
    lines += ["", f"End-to-end through the real tools (SFT v2 Q4): **{e2e['passed']}/{e2e['n']}** tasks, prompt-injection "
              f"files resisted **{e2e['injection_resisted']}/{e2e['injection_n']}**, unconfirmed writes / overwrites / "
              f"permanent deletes = {' / '.join(str(v) for v in e2e['invariants'].values())} "
              "([report](eval/reports/e2e_alfred-2b-v2-q4.md)).", ""]

    w = {k: when2call(k) for k in ("base", "sft")}
    if all(w.values()):
        lines += ["## When2Call MCQ test (public benchmark: call / ask / answer / can't)", "",
                  "| Model (full precision) | n | Accuracy | Acc-norm | Macro-F1 | Tool hallucination ↓ |",
                  "|---|---|---|---|---|---|"]
        for k, desc in (("base", "Qwen3.5-2B base"), ("sft", "SFT v2")):
            m = w[k]
            lines.append(f"| {desc} | {m['n']} | {pct(m['acc'])} | {pct(m['acc_norm'])} | {m['macro_f1']:.3f} | "
                         f"{pct(m['hallucination'])} |")
        lines += ["", "Log-likelihood scoring as in the official lm-eval task, Qwen3.5 chat template "
                  "([eval/when2call/bench.py](eval/when2call/bench.py)). SFT used When2Call's *train* split; "
                  "this is the held-out *test* split.", ""]

    b = {s: bfcl(s) for s in ("base-2b-q8", "alfred-2b-v2-q8")}
    if all(b.values()):
        lines += ["## BFCL v4 subset (general function calling: did fine-tuning hurt it?)", "",
                  "| Category | n | Base Q8_0 | SFT v2 Q8_0 |", "|---|---|---|---|"]
        for cat, _ in BFCL_CATS:
            (a0, n), (a1, _) = b["base-2b-q8"][cat], b["alfred-2b-v2-q8"][cat]
            lines.append(f"| {cat} | {n} | {pct(a0)} | {pct(a1)} |")
        mean = {s: sum(a for a, _ in v.values()) / len(v) for s, v in b.items()}
        lines += [f"| **unweighted mean** | | **{pct(mean['base-2b-q8'])}** | **{pct(mean['alfred-2b-v2-q8'])}** |", "",
                  "Pinned `bfcl-eval==2026.3.23`, non-thinking mode, AST checker; Qwen3.5 handler in "
                  "[eval/bfcl/run.py](eval/bfcl/run.py). Not comparable to the vendor's 43.6 (full BFCL v4, "
                  "thinking mode).", ""]

    confusion_png()
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.name} and {FIG.name}")


if __name__ == "__main__":
    main()
