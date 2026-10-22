"""Owner review of test items, and hand-rescoring of a report (Phase 3 gate).

  uv run python -m eval.review indomain             # y = keep, e = edit in Notepad, n = delete, s = skip, q = quit
  uv run python -m eval.review indomain --status
  uv run python -m eval.review --rescore eval/reports/base-2b-q8_indomain.json [-n 20]

A review is stored as the item's hash in eval/testsets/reviews.json, so editing an item later makes it unreviewed.
"""

import argparse
import hashlib
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from alfred.contracts.schemas import TestItem

HERE = Path(__file__).parent
REVIEWS = HERE / "testsets" / "reviews.json"


def item_hash(it: TestItem) -> str:
    return hashlib.sha1(it.model_dump_json().encode()).hexdigest()[:12]


def load_reviews() -> dict:
    return json.loads(REVIEWS.read_text(encoding="utf-8")) if REVIEWS.exists() else {}


def save_reviews(r: dict):
    REVIEWS.write_text(json.dumps(r, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def show(it: TestItem):
    print("\n" + "=" * 80 + f"\n{it.id}   tags: {', '.join(it.tags) or '-'}")
    for m in it.messages:
        if m.tool_calls:
            print("  assistant → " + "; ".join(f"{c.name}({json.dumps(c.arguments, ensure_ascii=False)})"
                                                for c in m.tool_calls))
        else:
            print(f"  {m.role}{f' [{m.name}]' if m.name else ''}: {m.content}")
    print(f"EXPECTED: {it.expected_decision}")
    for c in it.expected_calls:
        print(f"  {c.name}({json.dumps(c.arguments, ensure_ascii=False)})")
    if it.arg_rules:
        print(f"  rules: {it.arg_rules}")


def edit(it: TestItem) -> TestItem | None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(it.model_dump_json(indent=2))
    while True:
        subprocess.run(["notepad", f.name])
        try:
            return TestItem.model_validate_json(Path(f.name).read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"invalid: {e}\nfix it and save again (or empty the file to cancel)")
            if not Path(f.name).read_text(encoding="utf-8").strip():
                return None


def review(set_name: str, status_only: bool):
    from eval.run import SETS, load_set
    items, reviews = load_set(set_name), load_reviews()
    done = reviews.setdefault(set_name, {})
    todo = [it for it in items if done.get(it.id) != item_hash(it)]
    print(f"{set_name}: {len(items) - len(todo)}/{len(items)} reviewed")
    if status_only:
        return
    for it in todo:
        show(it)
        choice = input("[y]es keep / [e]dit / [n]o delete / [s]kip / [q]uit > ").strip().lower()
        if choice == "q":
            break
        if choice == "e":
            new = edit(it)
            if new is None:
                continue
            items[items.index(it)] = it = new
            show(it)
        if choice in ("y", "e"):
            done[it.id] = item_hash(it)
        elif choice == "n":
            items.remove(it)
            done.pop(it.id, None)
        (SETS / f"{set_name}.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items), encoding="utf-8")
        save_reviews(reviews)
    print(f"{set_name}: {sum(done.get(i.id) == item_hash(i) for i in items)}/{len(items)} reviewed")


def rescore(report_path: str, n: int, seed: int = 0):
    from eval.run import load_set
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    items = {it.id: it for it in load_set(report["set"])}
    sample = random.Random(seed).sample(report["items"], min(n, len(report["items"])))
    agree, rows = 0, []
    for row in sample:
        show(items[row["id"]])
        o = row["output"]
        print("MODEL: " + ("; ".join(f"{c['name']}({json.dumps(c['arguments'], ensure_ascii=False)})"
                                     for c in o["tool_calls"]) or o["error"] or o["content"]))
        human = input("Is the model's answer fully correct? [y/n] > ").strip().lower() == "y"
        agree += human == row["ok"]
        rows.append({"id": row["id"], "human_ok": human, "scorer_ok": row["ok"]})
        if human != row["ok"]:
            print(f"  ↳ disagreement (scorer said {row['ok']})")
    out = Path(report_path).with_name("rescore_" + Path(report_path).name)
    out.write_text(json.dumps({"report": report_path, "agree": agree, "n": len(rows), "items": rows}, indent=1),
                   encoding="utf-8")
    print(f"\nscorer agrees with you on {agree}/{len(rows)} items → {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("set", nargs="?")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--rescore")
    ap.add_argument("-n", type=int, default=20)
    a = ap.parse_args()
    rescore(a.rescore, a.n) if a.rescore else review(a.set, a.status)
