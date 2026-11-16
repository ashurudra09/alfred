"""On-policy data from real execution (v4 phase 2): the student acts on train-pool tasks through the real tools,
and what it actually did is kept or queued for correction. Method after SCoRe (student acts, teacher fixes the
earliest error); see docs/references.md.

  uv run python -m data.onpolicy rollout --n 25 --url http://127.0.0.1:8081/v1 [--shard 0/2]   # steps 2.1, 2.2
  uv run python -m data.onpolicy triage                                                        # step 2.3
  uv run python -m data.onpolicy correct --url http://127.0.0.1:8081/v1 [--limit N]            # steps 2.4, 2.5
  uv run python -m data.onpolicy convert                                                       # step 2.6 -> data/out/v4/onpolicy.jsonl
  uv run python -m data.onpolicy replay                                                        # verification, no model

Rollouts are appended to data/out/v4/student_<i>of<n>.jsonl (one row per task, full trajectory) and resume by task
id. A task passes triage only if its own check passes and every safety invariant is 0.

Correction: the teacher reads a failed trajectory (real tool results, the checker's reason) and names the earliest
wrong assistant turn plus a replacement. The turns before it are replayed in a fresh sandbox, the replacement is
executed for real and the student carries on; up to three rounds. The outcome goes to fixed_<i>of<n>.jsonl whether
or not it passes: acceptance is the task's check, never the teacher's opinion. Teacher replies are cached by prompt
hash in data/out/v4/cache/.
"""

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter

from openai import OpenAI

from alfred.agent.backends import ROOT, Backend, RawCall, Result
from alfred.contracts.export import load, openai_tools
from alfred.contracts.schemas import Example, Message
from alfred.tools import semantic
from data.gen.prompts import USERS
from data.gen.teacher import PROVIDERS
from data.validate import check
from eval.e2e import hard
from eval.e2e.__main__ import run_task

OUT = ROOT / "data" / "out" / "v4"
STUDENT_CONTRACTS = "1.2"  # v3 was trained on the 25-tool list; tool 26 is hidden from it
FAMILIES = [f.__name__ for f in hard.SHARED + hard.SEMANTIC]
# Replies the loop writes itself, without asking the model: not the student's turns, and nothing to train on.
LOOP_MADE = ("Sorry, the model backend failed", "I couldn't make a valid tool call", "I stopped after")


def student_config() -> dict:
    old = {t["name"] for t in load(STUDENT_CONTRACTS)["tools"]}
    return {"temperature": 0.0, "contracts": STUDENT_CONTRACTS,
            "disabled_tools": [t["name"] for t in load()["tools"] if t["name"] not in old]}


def sandbox(t):
    """One short, fixed folder per task: a correction replays the same calls, and those carry these paths."""
    return ROOT / "runs" / "sb" / f"{FAMILIES.index(t.family)}_{t.seed}"


def task_of(task_id: str):
    family, seed = task_id.rsplit("-", 1)
    return hard.build(getattr(hard, family), "train", int(seed))


def local(url):
    backend = Backend("local")
    if url:
        backend.client = OpenAI(base_url=url, api_key="none", max_retries=8, timeout=600)
    return backend


def rows(stage: str) -> dict:
    """Finished tasks of a stage. A run in which the model server failed is not a result: it is left out, so a
    rerun does that task again."""
    return {r["id"]: r for f in sorted(OUT.glob(f"{stage}_*.jsonl"))
            for r in map(json.loads, f.read_text(encoding="utf-8").splitlines())
            if not any(x.startswith(LOOP_MADE[0]) for x in r["answers"])}


def kept(r: dict) -> bool:
    return r["ok"] and not any(r["invariants"].values())


def rollout(a):
    """Student rollouts. Tasks that need tool 26 are left to the teacher (step 2.2, `teacher_exec`)."""
    tasks = [t for t in hard.tasks("train", a.n) if "new_capability" not in t.tags]
    backend = local(a.url)
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


# --- correction (steps 2.4, 2.5) ---

def assistant_turns(r: dict) -> list:
    """The model's own outputs in order, across the task's chats: what a replay feeds back through the loop."""
    return [m for c in r["trajectory"] for m in c["messages"]
            if m["role"] == "assistant" and not m.get("content", "").startswith(LOOP_MADE)]


class Prefixed:
    """A backend that replays recorded assistant turns, then hands over to the student."""

    def __init__(self, turns: list, then):
        self.turns, self.then, self.model = list(turns), then, getattr(then, "model", "replay")

    def stream(self, messages, tools=None, temperature=0.0):
        if not self.turns:
            yield from self.then.stream(messages, tools, temperature)
            return
        m = self.turns.pop(0)
        yield "done", Result(content=m.get("content", ""), ttft=0.0, tool_calls=[
            RawCall(c["name"], c["arguments"], json.dumps(c["arguments"])) for c in m.get("tool_calls") or []])


def transcript(r: dict) -> str:
    out, k = [], 0
    for n, chat in enumerate(r["trajectory"]):
        out += ["--- the user starts a new chat ---"] * bool(n)
        for m in chat["messages"]:
            if m["role"] == "assistant" and not m.get("content", "").startswith(LOOP_MADE):
                calls = "".join(f"\n  CALL {c['name']} {json.dumps(c['arguments'], ensure_ascii=False)}"
                                for c in m.get("tool_calls") or [])
                out.append(f"[assistant turn {k}] {m.get('content', '')}{calls}")
                k += 1
            else:
                out.append(f"[{m['role']}{' ' + m['name'] if m.get('name') else ''}] {m.get('content', '')}")
    return "\n".join(out)


def tool_lines() -> str:
    """The student's tools, one line each: name(arg: type, optional?: type): description."""
    out = []
    for t in openai_tools(load(STUDENT_CONTRACTS)):
        f, p = t["function"], t["function"]["parameters"]
        args = ", ".join(f"{k}{'' if k in p.get('required', []) else '?'}: {v.get('type', 'any')}"
                         for k, v in p.get("properties", {}).items())
        out.append(f"- {f['name']}({args}): {f['description']}")
    return "\n".join(out)


def teacher_prompt(r: dict) -> str:
    return f"""Below is a transcript of Alfred, an assistant that works on a Windows laptop through tools. Alfred did \
not complete the task. Find the EARLIEST assistant turn that is wrong and write the turn Alfred should have produced \
in its place.

Alfred's instructions:
{r["trajectory"][0]["system"]}

Alfred's tools:
{tool_lines()}

Transcript (tool results are real):
{transcript(r)}

Why the task failed, from an automatic check of the files and the answers afterwards:
{r["reason"] or "a safety rule was broken: " + json.dumps(r["invariants"])}

Rules for your turn:
- The turns before it stay exactly as they are, so it must follow from what the transcript shows up to that point.
- It is either tool calls or a text reply to the user, never both.
- Use only paths, names and values that appear in the user's messages or in earlier tool results. The failure \
reason above tells you what went wrong; Alfred never sees it, so a folder or file name that appears only there must \
not be used. When Alfred does not know where something is, it searches all folders.
- Leave optional arguments out instead of setting them to null.
- Do only what the user asked for. A change is confirmed by the user in the app, so just make the call; do not ask \
"shall I?" in text. If the request is unclear, or two things fit it, the right turn is a question to the user.
- A reply that ends a request states what was found or done, including every figure or name the user asked for.

Return one JSON object: {{"index": <number of the wrong assistant turn>, "why": "<one sentence>", \
"tool_calls": [{{"name": "<tool>", "arguments": {{...}}}}]}} for tool calls, or with "content": "<the reply>" in \
place of "tool_calls" for a text reply."""


_teacher = []


def ask(text: str) -> dict | None:
    """The teacher's JSON reply, cached by prompt hash. None when the free quota is used up (the run stops)."""
    path = OUT / "cache" / (hashlib.sha256(text.encode()).hexdigest()[:24] + ".json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["reply"]
    _, url, key, model, _, _, extra = PROVIDERS[0]  # gpt-oss-120b on Groq's free tier
    if not _teacher:
        _teacher.append(OpenAI(base_url=url, api_key=os.environ[key], max_retries=4, timeout=300))
    for attempt in range(3):
        try:
            res = _teacher[0].chat.completions.create(
                model=model, messages=[{"role": "user", "content": text}], temperature=0.2, max_tokens=1500,
                response_format={"type": "json_object"}, extra_body=extra)
            reply = json.loads(res.choices[0].message.content)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"reply": reply, "model": model, "prompt": text,
                                        "tokens": res.usage.total_tokens}, ensure_ascii=False), encoding="utf-8")
            return reply
        except Exception as e:
            print(f"  teacher attempt {attempt + 1}: {type(e).__name__}: {str(e)[:600]}", flush=True)
            if "per day" in str(e) or "402" in str(e):
                return None
            time.sleep(20 * (attempt + 1))
    return {}  # no usable reply: this task is dropped and counted


def correct(a):
    student = local(a.url)
    i, n = map(int, a.shard.split("/"))
    done = rows("fixed")
    todo = [r for r in rows("student").values() if not kept(r) and r["id"] not in done][i::n][: a.limit]
    for j, r in enumerate(todo, 1):
        task, fixes, first = task_of(r["id"]), [], r["reason"]
        for _ in range(3):
            fix, turns = ask(teacher_prompt(r)), assistant_turns(r)
            if fix is None:
                return print("teacher quota used up; run again after the daily reset")
            k = fix.get("index")
            if not isinstance(k, int) or not 0 <= k < len(turns) or not (fix.get("tool_calls") or fix.get("content")):
                break
            for c in fix.get("tool_calls") or []:  # the teacher writes null for "not given"; the schemas have no null
                c["arguments"] = {k: v for k, v in c["arguments"].items() if v is not None}
            new = {"role": "assistant", **({"tool_calls": fix["tool_calls"]} if fix.get("tool_calls") else
                                           {"content": fix["content"]})}
            # a later round may go back before an earlier fix, which is then no longer part of the trajectory
            fixes = [f for f in fixes if f["index"] < k] + [{"index": k, "why": fix.get("why", ""), "turn": new}]
            try:
                r = run_task(task, Prefixed(turns[:k] + [new], student), None, student_config(), root=sandbox(task))
            except Exception as e:  # e.g. the teacher's turn has a shape the loop cannot take
                print(f"  {task.id}: {type(e).__name__}: {str(e)[:200]}", flush=True)
                break
            if kept(r):
                break
        r |= {"stage": "fixed", "fixes": fixes, "first_reason": first, "root": str(sandbox(task)),
              "embedder_up": semantic.embedder_up()}
        with (OUT / f"fixed_{i}of{n}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[{j}/{len(todo)}] {'FIXED' if kept(r) else 'DROPPED'} {task.id} at turns {[f['index'] for f in fixes]} "
              f"{'' if kept(r) else r['reason']}", flush=True)


def replay(a):
    """Phase 2's verification: every kept trajectory, replayed with no model from an empty sandbox, passes again."""
    good = [r for stage in ("student", "fixed") for r in rows(stage).values() if kept(r)][: a.limit]
    bad = []
    for r in good:
        again = run_task(task_of(r["id"]), Prefixed(assistant_turns(r), None), None, student_config(),
                         root=sandbox(task_of(r["id"])))
        if not kept(again) or again["answers"] != r["answers"]:
            bad.append(r["id"])
            print(f"NOT REPRODUCED {r['id']} ({r['stage']}): {again['reason']}", flush=True)
    print(f"replayed {len(good)} kept trajectories: {len(good) - len(bad)} pass again, {len(bad)} do not")


# --- conversion (step 2.6) ---

def examples(r: dict) -> list[Example]:
    """A kept row as training Examples, one per chat. The sandbox folder becomes C:\\Users\\<name>, so no path of
    this machine reaches the data; the recorded system prompt is kept, the tool list is the current one (26)."""
    user = random.Random(r["id"]).choice(USERS)
    # the row as JSON text, where a backslash is written twice; forward-slash spellings are covered too
    text, home = json.dumps(r["trajectory"], ensure_ascii=False), json.dumps(f"C:\\Users\\{user}")[1:-1]
    for root in (json.dumps(r["root"])[1:-1], r["root"].replace("\\", "/")):
        text = re.sub(re.escape(root), lambda _: home, text, flags=re.I)
    out = []
    for n, chat in enumerate(json.loads(text)):
        msgs = [Message(role="system", content=chat["system"]), *map(Message.model_validate, chat["messages"])]
        calls = sum(len(m.tool_calls or []) for m in msgs)
        out.append(Example(id=f"onpolicy-{r['id']}-{n}", source="onpolicy", messages=msgs, tools=openai_tools(),
                           category="multi_step" if calls > 1 else "tool_call" if calls else "direct"))
    return out


def convert(_=None):
    good = [r for stage in ("student", "fixed") for r in rows(stage).values() if kept(r)]
    n, why, out = 0, Counter(), []
    for r in good:
        for ex in examples(r):
            n += 1
            errs = check(ex)
            dump = ex.model_dump_json()
            if any(m.role == "assistant" and m.content.startswith(LOOP_MADE) for m in ex.messages):
                errs.append("contains a reply written by the loop, not the model")
            if re.search(r"interview prep|runs.{1,2}sb|" + re.escape(os.environ.get("USERNAME", "ashur")), dump, re.I):
                errs.append("a path of this machine is left in the example")
            why.update(errs)
            if not errs:
                out.append(dump)
    (OUT / "onpolicy.jsonl").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(good)} kept trajectories -> {n} examples, {len(out)} valid -> {OUT / 'onpolicy.jsonl'}")
    for err, k in why.most_common():
        print(f"  {k:5}  {err}")


def triage(_=None):
    rs = list(rows("student").values())
    by = Counter((r["tags"][1], kept(r)) for r in rs)
    print(f"{len(rs)} rollouts: {sum(map(kept, rs))} kept, {len(rs) - sum(map(kept, rs))} to correct; "
          f"invariant hits {sum(any(r['invariants'].values()) for r in rs)}; "
          f"embedder down in {sum(not r['embedder_up'] for r in rs)}; "
          f"median task {sorted(sum(r['turn_secs']) for r in rs)[len(rs) // 2]:.0f} s")
    for fam in FAMILIES:
        if by[fam, True] + by[fam, False]:
            print(f"  {fam}: {by[fam, True]}/{by[fam, True] + by[fam, False]}")
    fx = list(rows("fixed").values())
    if fx:
        at = Counter(min(f["index"] for f in r["fixes"]) for r in fx if kept(r))
        print(f"{len(fx)} corrected: {sum(map(kept, fx))} now pass (earliest fixed turn: {dict(sorted(at.items()))}), "
              f"{len(fx) - sum(map(kept, fx))} dropped")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rollout", "triage", "correct", "replay", "convert"])
    ap.add_argument("--n", type=int, default=25, help="tasks per family (25 = the 300-task pilot)")
    ap.add_argument("--url", help="the eval server, e.g. http://127.0.0.1:8081/v1")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--limit", type=int, help="correct or replay at most N tasks")
    a = ap.parse_args()
    {"rollout": rollout, "correct": correct, "triage": triage, "replay": replay, "convert": convert}[a.cmd](a)
