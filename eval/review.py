"""Owner review of test items, and hand-rescoring of a report (Phase 3 gate).

  uv run python -m eval.review indomain             # y = keep, e = edit in Notepad, n = delete, s = skip, q = quit
  uv run python -m eval.review indomain --status
  uv run python -m eval.review indomain --owner     # your own review, kept apart from the AI agent's
  uv run python -m eval.review --rescore eval/reports/base-2b-q8_indomain.json [-n 20]
  uv run python -m eval.review --text [-n 100]      # blind-label text replies: does the keyword classifier agree?

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


def show(it: TestItem, expected: bool = True):
    print("\n" + "=" * 80 + f"\n{it.id}   tags: {', '.join(it.tags) or '-'}")
    for m in it.messages:
        if m.tool_calls:
            print("  assistant → " + "; ".join(f"{c.name}({json.dumps(c.arguments, ensure_ascii=False)})"
                                                for c in m.tool_calls))
        else:
            print(f"  {m.role}{f' [{m.name}]' if m.name else ''}: {m.content}")
    if not expected:
        return
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


def review(set_name: str, status_only: bool, owner: bool = False):
    from eval.run import SETS, load_set
    items, reviews = load_set(set_name), load_reviews()
    done = reviews.setdefault(set_name + (":owner" if owner else ""), {})  # the AI agent's review stays under set_name
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


TEXT_SOURCES = [(s, t) for s in ("base-2b-q8", "alfred-2b-v2-q4", "cloud-gpt-oss-120b") for t in ("indomain", "safety")]
TEXT_CLASSES = {"d": "direct", "a": "ask", "c": "cannot", "r": "refuse"}
TEXT_OUT = HERE / "reports" / "rescore_text.json"


def text_sample(n: int, seed: int = 0) -> list[dict]:
    """Text-only replies (no tool call) pooled over TEXT_SOURCES, n // 4 per scorer decision where available."""
    pool = []
    for system, test_set in TEXT_SOURCES:
        p = HERE / "reports" / f"{system}_{test_set}.json"
        for row in json.loads(p.read_text(encoding="utf-8"))["items"]:
            o = row["output"]
            if not o["tool_calls"] and not o["error"] and row["decision"] in TEXT_CLASSES.values():
                pool.append({"system": system, "set": test_set, "id": row["id"], "content": o["content"],
                             "scorer": row["decision"]})
    rng, out = random.Random(seed), []
    for cls in TEXT_CLASSES.values():
        group = [r for r in pool if r["scorer"] == cls]
        out += rng.sample(group, min(n // 4, len(group)))
    return out


def text_agreement(rows: list[dict]) -> dict:
    """Overall and per-class (by the human label) agreement between the scorer and the human."""
    per = {c: {"n": sum(r["human"] == c for r in rows),
               "agree": sum(r["human"] == c == r["scorer"] for r in rows)} for c in TEXT_CLASSES.values()}
    return {"n": len(rows), "agree": sum(r["human"] == r["scorer"] for r in rows), "per_class": per}


def rescore_text(n: int):
    """Blind check of the scorer's keyword classifier: you label each reply, it never shows its own answer first."""
    from eval.run import load_set
    sets = {s: {it.id: it for it in load_set(s)} for _, s in TEXT_SOURCES}
    saved = json.loads(TEXT_OUT.read_text(encoding="utf-8"))["items"] if TEXT_OUT.exists() else []
    done = {(r["system"], r["set"], r["id"]) for r in saved}
    todo = [r for r in text_sample(n) if (r["system"], r["set"], r["id"]) not in done]
    print(f"{len(saved)} labelled, {len(todo)} to go")
    for row in todo:
        show(sets[row["set"]][row["id"]], expected=False)
        print(f"MODEL REPLY: {row['content']}")
        k = ""
        while k not in TEXT_CLASSES and k != "q":
            k = input("What is this reply? [d]irect answer / [a]sk for info / [c]an't do it / [r]efuse / [q]uit > "
                      ).strip().lower()
        if k == "q":
            break
        saved.append(row | {"human": TEXT_CLASSES[k]})
        if TEXT_CLASSES[k] != row["scorer"]:
            print(f"  ↳ scorer said {row['scorer']}")
        TEXT_OUT.write_text(json.dumps({"agreement": text_agreement(saved), "items": saved}, indent=1,
                                       ensure_ascii=False) + "\n", encoding="utf-8")
    a = text_agreement(saved)
    print(f"\nscorer agrees with you on {a['agree']}/{a['n']}: "
          + ", ".join(f"{c} {v['agree']}/{v['n']}" for c, v in a["per_class"].items()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("set", nargs="?")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--owner", action="store_true", help="record the review as the owner's, apart from the AI review")
    ap.add_argument("--rescore")
    ap.add_argument("--text", action="store_true", help="blind-label text replies to check the scorer's classifier")
    ap.add_argument("-n", type=int, default=None)
    a = ap.parse_args()
    if a.text:
        rescore_text(a.n or 100)
    elif a.rescore:
        rescore(a.rescore, a.n or 20)
    else:
        review(a.set, a.status, a.owner)
