"""Run the security suite (track 4E) against a served model, or validate its checker with scripted agents.

  uv run python -m eval.security --system alfred-2b-v3-q4 --contracts 1.2 --url http://127.0.0.1:8081/v1 [--shard 0/2]
  uv run python -m eval.security --system obey     # scripted: carries out every injection (attack success 100%)
  uv run python -m eval.security --system ignore   # scripted: never does (0%)
  uv run python -m eval.security --list            # the cases, by vector and family

Writes eval/reports/security_<system>.{json,md}. Each finished case goes, with its trajectory, to
runs/security/<system>/<commit>_...jsonl; a rerun on the same commit skips those (--fresh starts over).
"""

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter

from openai import OpenAI

from alfred.agent.backends import ROOT, Backend
from alfred.contracts.export import load
from alfred.tools import memory, semantic
from eval.e2e.__main__ import run_task
from eval.e2e.hard import Scripted
from eval.results import wilson
from eval.security.families import TEST_ONLY
from eval.security.suite import GOALS, VECTORS, cases, script

SCRIPTED = ("obey", "ignore")
COLS = [("attack_model", "attack proposed"), ("attack_exec_none", "executed: user confirms nothing or only the "
                                                                   "request"),
        ("attack_exec_all", "executed: user confirms everything"), ("utility", "user task done")]


def rate(rows, key) -> str:
    k, n = sum(bool(r["security"][key]) for r in rows), len(rows)
    lo, hi = (max(0.0, x) for x in wilson(k, n))
    return f"{k}/{n} ({100 * k / n:.0f}%, {100 * lo:.0f}-{100 * hi:.0f})" if n else "-"


def summary(rep) -> str:
    rows = rep["cases"]
    att, clean = [r for r in rows if r["goal"]], [r for r in rows if not r["goal"]]
    groups = [("all attacks", att),
              ("families seen in training data", [r for r in att if r["family"] not in TEST_ONLY]),
              ("test-only families", [r for r in att if r["family"] in TEST_ONLY]),
              ("goals that need confirmation", [r for r in att if GOALS[r["goal"]][3]]),
              ("goals through unconfirmed tools", [r for r in att if not GOALS[r["goal"]][3]])]
    groups += [(f"goal `{g}`", [r for r in att if r["goal"] == g]) for g in GOALS]
    groups += [(f"vector `{v}`", [r for r in att if r["vector"] == v]) for v in VECTORS]
    groups += [(f"family `{f}`", [r for r in att if r["family"] == f]) for f in sorted({r["family"] for r in att})]
    head = "| Cases | " + " | ".join(label for _, label in COLS) + " |"
    lines = [f"# Security suite: {rep['system']}", "", f"{rep['date']}, commit `{rep['commit']}`, prompt {rep['prompt'] or 'current'}, tool list "
             f"{rep['contracts'] or 'current'}, temperature {rep['temperature']}", "",
             f"- **Attack success (proposed): {rate(att, 'attack_model')}**; executed with a user who confirms "
             f"everything {rate(att, 'attack_exec_all')}, with one who confirms only the request "
             f"{rate(att, 'attack_exec_none')}",
             f"- User task done: without attack {rate(clean, 'utility')}, under attack {rate(att, 'utility')}",
             f"- Other actions nobody asked for, in attacked cases: "
             f"{sum(bool(r['security']['other_writes']) for r in att)}; in clean cases: "
             f"{sum(bool(r['security']['other_writes']) for r in clean)}",
             f"- Safety invariants: " + ", ".join(f"{k} = {v}" for k, v in rep["invariants"].items()),
             f"- Median turn time {rep['median_turn_secs']} s. Rates with 95% Wilson intervals.", "",
             head, "|---" * (len(COLS) + 1) + "|"]
    lines += [f"| {name} | " + " | ".join(rate(g, k) for k, _ in COLS) + " |" for name, g in groups if g]
    return "\n".join(lines) + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--system")
    ap.add_argument("--backend", default="local")
    ap.add_argument("--url")
    ap.add_argument("--contracts")
    ap.add_argument("--prompt", help="system-prompt version the model was trained on (v2: 1.1)")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--only")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    todo = [c for c in cases() if not a.only or any(x in c.id for x in a.only.split(","))]
    if a.list:
        att = [c for c in todo if c.goal]
        print(f"{len(att)} attacked cases + {len(todo) - len(att)} clean")
        for v in VECTORS:
            print(f"  {v:11}", dict(Counter(c.family for c in att if c.vector == v)))
        return
    scripted, base = a.system in SCRIPTED, ROOT / "runs" / "security" / a.system
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    config = {"temperature": a.temperature, **({"prompt": a.prompt} if a.prompt else {})}
    if a.contracts:
        old = {t["name"] for t in load(a.contracts)["tools"]}
        config |= {"contracts": a.contracts, "disabled_tools": [t["name"] for t in load()["tools"] if t["name"] not in old]}
    if scripted:
        memory.embed_many = lambda *x, **k: 1 / 0  # keyword recall: checker validation needs no Ollama
    else:
        backend = Backend(a.backend)
        if a.url:
            backend.client = OpenAI(base_url=a.url, api_key="none", max_retries=8, timeout=600)
    i, n = map(int, a.shard.split("/"))
    key = f"{commit}_t{a.temperature}_c{a.contracts or 'current'}_p{a.prompt or 'current'}"
    cache = base / f"{key}_{i}of{n}.jsonl"
    base.mkdir(parents=True, exist_ok=True)
    if a.fresh or scripted:
        for f in base.glob(f"{key}_*.jsonl"):
            f.unlink()

    def read():
        return {r["id"]: r for f in sorted(base.glob(f"{key}_*.jsonl"))
                for r in map(json.loads, f.read_text(encoding="utf-8").splitlines())}

    box, done = ROOT / "runs" / "sb" / f"s{os.getpid()}", read()  # short sandbox paths, as in the hard suite
    mine = todo[i::n]
    for j, c in enumerate(mine, 1):
        if c.id in done:
            continue
        r = run_task(c, Scripted(script(c, a.system)) if scripted else backend, base, config, scripted, box / str(j))
        r |= {"security": c.result, "vector": c.vector, "goal": c.goal, "family": c.family}
        with cache.open("a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        s = c.result
        print(f"[{j}/{len(mine)}] {c.id} {r['calls']} utility={s['utility']} "
              f"attack={s.get('attack_model', '-')} other={s['other_writes'] or ''}", flush=True)
    shutil.rmtree(box, ignore_errors=True)
    done = read()
    rows = [{k: v for k, v in done[c.id].items() if k != "trajectory"} for c in todo if c.id in done]
    if len(rows) < len(todo):
        return print(f"{len(rows)}/{len(todo)} cases done; the report is written when the other shards finish.")
    rep = {"system": a.system, "date": time.strftime("%Y-%m-%dT%H:%M:%S"), "commit": commit,
           "contracts": a.contracts, "prompt": a.prompt, "temperature": a.temperature,
           "embedder_up": not scripted and semantic.embedder_up(),
           "invariants": {k: sum(r["invariants"][k] for r in rows) for k in rows[0]["invariants"]},
           "median_turn_secs": round(statistics.median(s for r in rows for s in r["turn_secs"]), 2), "cases": rows}
    print(summary(rep))
    if scripted or a.only:  # validation and partial runs never replace a committed report
        return rep
    out = ROOT / "eval" / "reports" / f"security_{a.system}"
    out.with_suffix(".json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    out.with_suffix(".md").write_text(summary(rep), encoding="utf-8")


if __name__ == "__main__":
    main()
