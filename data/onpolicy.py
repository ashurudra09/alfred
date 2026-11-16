"""On-policy data from real execution (v4 phase 2): the student acts on train-pool tasks through the real tools,
and what it actually did is kept or queued for correction. Method after SCoRe (student acts, teacher fixes the
earliest error); see docs/references.md.

  uv run python -m data.onpolicy rollout --n 25 --url http://127.0.0.1:8081/v1 [--shard 0/2]   # steps 2.1, 2.2
  uv run python -m data.onpolicy triage                                                        # step 2.3

Rollouts are appended to data/out/v4/student_<i>of<n>.jsonl (one row per task, full trajectory) and resume by task
id. A task passes triage only if its own check passes and every safety invariant is 0.
"""

import argparse
import json
import subprocess
import sys
from collections import Counter

from openai import OpenAI

from alfred.agent.backends import ROOT, Backend
from alfred.contracts.export import load
from alfred.tools import semantic
from eval.e2e import hard
from eval.e2e.__main__ import run_task

OUT = ROOT / "data" / "out" / "v4"
STUDENT_CONTRACTS = "1.2"  # v3 was trained on the 25-tool list; tool 26 is hidden from it
FAMILIES = [f.__name__ for f in hard.SHARED + hard.SEMANTIC]


def student_config() -> dict:
    old = {t["name"] for t in load(STUDENT_CONTRACTS)["tools"]}
    return {"temperature": 0.0, "contracts": STUDENT_CONTRACTS,
            "disabled_tools": [t["name"] for t in load()["tools"] if t["name"] not in old]}


def sandbox(t):
    """One short, fixed folder per task: a correction replays the same calls, and those carry these paths."""
    return ROOT / "runs" / "sb" / f"{FAMILIES.index(t.family)}_{t.seed}"


def rows(stage: str) -> dict:
    return {r["id"]: r for f in sorted(OUT.glob(f"{stage}_*.jsonl"))
            for r in map(json.loads, f.read_text(encoding="utf-8").splitlines())}


def kept(r: dict) -> bool:
    return r["ok"] and not any(r["invariants"].values())


def rollout(a):
    """Student rollouts. Tasks that need tool 26 are left to the teacher (step 2.2, `teacher_exec`)."""
    tasks = [t for t in hard.tasks("train", a.n) if "new_capability" not in t.tags]
    backend = Backend("local")
    if a.url:
        backend.client = OpenAI(base_url=a.url, api_key="none", max_retries=8, timeout=600)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    i, n = map(int, a.shard.split("/"))
    OUT.mkdir(parents=True, exist_ok=True)
    done, mine = rows("student"), tasks[i::n]
    for j, t in enumerate(mine, 1):
        if t.id in done:
            continue
        try:
            r = run_task(t, backend, None, student_config(), root=sandbox(t))
        except Exception as e:  # a tool server that did not start must not end an overnight run; the task is retried on a rerun
            print(f"[{j}/{len(mine)}] ERROR {t.id} {type(e).__name__}: {str(e)[:200]}", flush=True)
            continue
        r |= {"stage": "student", "root": str(sandbox(t)), "commit": commit, "embedder_up": semantic.embedder_up()}
        with (OUT / f"student_{i}of{n}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[{j}/{len(mine)}] {'PASS' if kept(r) else 'FAIL'} {t.id} {r['turn_secs']} {r['calls']} "
              f"{r['reason'] or ''}", flush=True)


def triage():
    rs = list(rows("student").values())
    by = Counter((r["tags"][1], kept(r)) for r in rs)
    print(f"{len(rs)} rollouts: {sum(map(kept, rs))} kept, {len(rs) - sum(map(kept, rs))} to correct; "
          f"invariant hits {sum(any(r['invariants'].values()) for r in rs)}; "
          f"embedder down in {sum(not r['embedder_up'] for r in rs)}; "
          f"median task {sorted(sum(r['turn_secs']) for r in rs)[len(rs) // 2]:.0f} s")
    for fam in FAMILIES:
        if by[fam, True] + by[fam, False]:
            print(f"  {fam}: {by[fam, True]}/{by[fam, True] + by[fam, False]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rollout", "triage"])
    ap.add_argument("--n", type=int, default=25, help="tasks per family (25 = the 300-task pilot)")
    ap.add_argument("--url", help="the eval server, e.g. http://127.0.0.1:8081/v1")
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args()
    rollout(a) if a.cmd == "rollout" else triage()
