"""Run a backend over a test set and write a scored report.

Usage: uv run python -m eval.run --backend local --system base-2b-q8 --set indomain [--limit N]
Writes eval/reports/<system>_<set>.json (+ .md summary). Raw outputs are cached in <...>.raw.jsonl, so an interrupted
or rate-limited run resumes where it stopped (delete the .raw.jsonl to rerun from scratch).
"""

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from alfred.agent.backends import BACKENDS, Backend, openai_messages
from alfred.contracts.export import openai_tools
from alfred.contracts.prompt import render_system_prompt
from alfred.contracts.schemas import TestItem
from eval.score import EVAL_DATE, EVAL_FOLDERS, aggregate, score_item

HERE = Path(__file__).parent
SETS = HERE / "testsets"
REPORTS = HERE / "reports"


def load_set(name: str) -> list[TestItem]:
    path = Path(name) if name.endswith(".jsonl") else SETS / f"{name}.jsonl"
    return [TestItem.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def unreviewed(name: str, items: list[TestItem]) -> int:
    from eval.review import item_hash, load_reviews
    done = load_reviews().get(name, {})
    return sum(done.get(i.id) != item_hash(i) for i in items)


def pct(x):
    return "–" if x is None else f"{100 * x:.1f}%"


def summary_md(r: dict) -> str:
    m, lat = r["metrics"], r["latency"]
    lines = [f"# {r['system']} on {r['set']} (n={m['n']})", "",
             f"Backend `{r['backend']}` / model `{r['model']}`, {r['date']}, commit `{r['commit']}`."
             + (f" **{r['unreviewed']} items not yet owner-reviewed.**" if r["unreviewed"] else ""), "",
             "| Metric | Value |", "|---|---|"]
    for k in ("accuracy", "valid_rate", "decision_accuracy", "tool_accuracy", "args_score", "decision_macro_f1"):
        lines.append(f"| {k} | {pct(m[k])} |")
    lines += [f"| median TTFT | {lat['ttft_median']} s |", f"| median total | {lat['total_median']} s |", "",
              "| Decision | precision | recall | F1 | n |", "|---|---|---|---|---|"]
    lines += [f"| {d} | {pct(v['precision'])} | {pct(v['recall'])} | {pct(v['f1'])} | {v['support']} |"
              for d, v in m["per_decision"].items() if v["support"]]
    worst = sorted(m["per_label_accuracy"].items(), key=lambda kv: kv[1])[:8]
    lines += ["", "Weakest expected labels: " + ", ".join(f"`{k}` {pct(v)}" for k, v in worst), ""]
    return "\n".join(lines)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # model replies contain emoji; cp1252 crashes
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=list(BACKENDS), default="local")
    ap.add_argument("--system", required=True, help="name of the system in the results table, e.g. base-2b-q8")
    ap.add_argument("--set", default="indomain")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    items = load_set(a.set)[: a.limit]
    set_name = Path(a.set).stem
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{a.system}_{set_name}.json"
    raw_path = out.with_suffix(".raw.jsonl")
    raw = {}
    if raw_path.exists():
        raw = {r["id"]: r for r in map(json.loads, raw_path.read_text(encoding="utf-8").splitlines())}
    backend, tools = Backend(a.backend), openai_tools()
    system = render_system_prompt(EVAL_FOLDERS, EVAL_DATE)

    with raw_path.open("a", encoding="utf-8") as f:
        for n, it in enumerate(items, 1):
            if it.id in raw and not raw[it.id]["output"].get("error"):
                continue
            res = backend.chat(openai_messages(it.messages, system), tools)
            raw[it.id] = {"id": it.id, "ttft": res.ttft, "total": round(res.total, 3),
                          "prompt_tokens": res.prompt_tokens, "cached_tokens": res.cached_tokens,
                          "output": {"content": res.content, "error": res.error,
                                     "tool_calls": [{"name": c.name, "arguments": c.arguments, "raw": c.raw}
                                                    for c in res.tool_calls]}}
            f.write(json.dumps(raw[it.id], ensure_ascii=False) + "\n")
            f.flush()
            calls = [c.name for c in res.tool_calls]
            print(f"[{n}/{len(items)}] {it.id} {res.total:5.1f}s {calls or (res.error or res.content)[:60]!r}")

    scores = [score_item(it, raw[it.id]["output"]) for it in items]
    rows = [raw[it.id] for it in items]
    ttfts = [r["ttft"] for r in rows if r["ttft"] is not None]
    report = {
        "system": a.system, "backend": a.backend, "model": backend.model, "set": set_name,
        "date": datetime.now().isoformat(timespec="seconds"),
        "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "unreviewed": unreviewed(set_name, items),
        "metrics": aggregate(scores, [it.expected_decision for it in items]),
        "latency": {"ttft_median": round(statistics.median(ttfts), 2) if ttfts else None,
                    "total_median": round(statistics.median(r["total"] for r in rows), 2),
                    "prompt_tokens_median": statistics.median(r["prompt_tokens"] or 0 for r in rows)},
        "items": [{**s, **r} for s, r in zip(scores, rows)],
    }
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    out.with_suffix(".md").write_text(summary_md(report), encoding="utf-8")
    print(summary_md(report))


if __name__ == "__main__":
    main()
