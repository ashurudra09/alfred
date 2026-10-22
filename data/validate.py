"""Validate training Examples (Phase 4). Writes <input>.valid.jsonl and prints error counts.

Usage: uv run python -m data.validate data/out/synthetic.jsonl
Exit code 1 if the input has unparseable lines (the gate is 0 errors in what goes into training).
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

from alfred.contracts.schemas import Example
from alfred.contracts.tools import REGISTRY
from data.gen.formats import DECLINED
from eval.score import VALIDATORS, classify_decision

SENSITIVE = re.compile(r"\.ssh|\\\.env|^\.env|appdata|\.kdbx|credential|user data|\.pem\b|id_rsa", re.I)
PERMA = re.compile(r"permanently delet", re.I)
NOT_PERMA = re.compile(r"\b(not|never|nothing|isn't|won't|instead of)\b[^.]{0,40}permanently delet", re.I)


def reply(content: str) -> dict:
    return {"content": content, "tool_calls": [], "error": None}


def check(ex: Example) -> list[str]:
    errs, msgs = [], ex.messages
    if msgs[0].role != "system" or msgs[1].role != "user":
        errs.append("must start with system + user")
    users = set(re.findall(r"C:\\Users\\([^\\\s]+)", msgs[0].content))
    pending, calls, first_reply, after_tool, prev = [], [], None, False, None
    for m in msgs[1:]:
        if prev is not None and prev.role == "assistant" and not prev.tool_calls and m.role != "user":
            errs.append("assistant reply not followed by a user turn")
        prev = m
        if m.role == "assistant" and m.tool_calls:
            if pending:
                errs.append("tool call before previous results")
            for c in m.tool_calls:
                calls.append(c)
                if c.name not in VALIDATORS:
                    errs.append(f"unknown tool {c.name}")
                elif not VALIDATORS[c.name].is_valid(c.arguments):
                    errs.append(f"schema-invalid args for {c.name}")
                if any(isinstance(v, str) and not v.strip() for v in c.arguments.values()):
                    errs.append("empty string argument")
                if c.name == "zip_folder" and re.search(r"\.[A-Za-z0-9]{2,4}$", str(c.arguments.get("source", ""))):
                    errs.append("zip_folder on a file")
                for v in map(str, c.arguments.values()):
                    if SENSITIVE.search(v) and ex.category != "refuse":
                        errs.append("sensitive path in arguments")
                    for u in re.findall(r"C:\\Users\\([^\\\s]+)", v):
                        if u not in users:
                            errs.append("unknown username in path")
                if after_tool and ex.category == "injection":
                    errs.append("tool call after injected content")
            pending = [c.name for c in m.tool_calls]
        elif m.role == "tool":
            if not pending or pending.pop(0) != m.name:
                errs.append("tool result does not match a pending call")
            after_tool = True
            if ex.category == "confirm_declined" and m.content.strip() != DECLINED:
                errs.append("declined example without the declined result")
        elif m.role == "assistant":
            if not m.content.strip():
                errs.append("empty assistant message")
            if first_reply is None:
                first_reply = m.content
            if PERMA.search(m.content) and not NOT_PERMA.search(m.content):
                errs.append("permanent-delete language")
        elif m.role == "user" and pending:
            errs.append("user turn before tool results")
    last = msgs[-1]
    if last.role != "assistant" or last.tool_calls or pending:
        errs.append("must end with an assistant reply")
    final = classify_decision(reply(last.content))
    cat = ex.category
    if cat in ("direct", "cannot", "refuse") and (calls or final != cat):
        errs.append(f"{cat} example classified as {'tool_call' if calls else final}")
    if cat == "ask" and classify_decision(reply(first_reply or "")) != "ask":
        errs.append("ask example's first reply is not classified as ask")
    if cat in ("tool_call", "confirm_declined", "injection") and not calls:
        errs.append(f"{cat} example without a tool call")
    if cat == "multi_step" and len(calls) < 2:
        errs.append("multi_step example with < 2 calls")
    if cat == "confirm_declined" and "/undo" in last.content:
        errs.append("declined example mentions undo")
    if cat not in ("refuse", "cannot") and any(REGISTRY[c.name]["needs_confirmation"] for c in calls
                                               if c.name in REGISTRY) and final in ("refuse", "cannot"):
        errs.append("write tool called but reply refuses")
    if len(last.content) > 1500:
        errs.append("final reply too long")
    return sorted(set(errs))


def main(path: str) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    src = Path(path)
    good, counts, bad_lines, n, by_cat, ok_cat = [], Counter(), 0, 0, Counter(), Counter()
    for line in src.read_text(encoding="utf-8").splitlines():
        n += 1
        obj = json.loads(line)
        if "error" in obj:
            bad_lines += 1
            counts["unparseable conversation"] += 1
            continue
        ex = Example.model_validate(obj)
        by_cat[ex.category] += 1
        errs = check(ex)
        counts.update(errs)
        if not errs:
            good.append(ex)
            ok_cat[ex.category] += 1
    out = src.with_suffix(".valid.jsonl")
    out.write_text("".join(e.model_dump_json() + "\n" for e in good), encoding="utf-8")
    print(f"{len(good)}/{n} valid ({100 * len(good) / max(n, 1):.1f}%) -> {out}")
    for cat in sorted(by_cat):
        print(f"  {cat:17} {ok_cat[cat]}/{by_cat[cat]}")
    for err, k in counts.most_common():
        print(f"  {k:5}  {err}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
