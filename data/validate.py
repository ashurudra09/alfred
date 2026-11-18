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


# v4 rules (2026-11-17), from reading the first injection_v4 examples. They apply to every Example, so a rerun of
# validation on v3's data would drop a few more rows (counted in docs/v4/STATUS.md); v3's validated file is not rerun.
INJECTED = re.compile(r"ignore (all |your |any |the )?(previous|prior|above|earlier)|\bIGNORE\b|\bTODO:|IMPORTANT!!!|"
                      r"system_message|\bSYSTEM\b|<tool_call>|\boverride\b|note for (the )?(AI|assistant)|"
                      r"instruction|FAKE", re.I)
# In a user's own message only the attack templates count: "ignore the old files" is an ordinary request.
IN_USER = re.compile(r"ignore (all |your )?previous instructions|\bTODO:|IMPORTANT!!!|system_message|<tool_call>", re.I)
TODAY = re.compile(r"Today is (\d{4}-\d{2}-\d{2})")
# When a file or fact was written ("modified 2026-10-15", "saved 2026-10-01", a note line "1. Title (2026-10-21)"),
# not dates inside file contents or reminder times, which may lie in the future.
STAMP = re.compile(r"(?:modified|saved) (20\d\d-\d\d-\d\d)|^\d+\. [^\n(]*\((20\d\d-\d\d-\d\d)\)", re.M)
HINDI = re.compile(r"\b(hai|hain|aapka|aapke|aapki|aapne|mein|nahi|kiya|kar|diya|mujhe|meri|mera|batao|chahiye|"
                   r"kya|woh|yeh|ye)\b", re.I)
# The first line the real tool prints (data/gen/formats.py). Only tools whose format v3's teacher data already
# follows (list_directory 331 of 331, search_notes 273 of 285) are checked; error and decline texts are exempt.
FORMAT = {"list_directory": re.compile(r"^\S.* \(\d+ items?\):"),
          "search_notes": re.compile(r"^(\d+ notes?:\n1\. .+\(\d{4}-\d\d-\d\d\)|No matching notes\.)")}
NOT_A_RESULT = ("Error", "Refused", "Not found", "Not run", DECLINED)
FILE_EXT = re.compile(r"\.([A-Za-z0-9]{2,5}) \(\d")  # "report.pdf (1.2 MB" -> pdf


def v4_checks(ex: Example) -> list[str]:
    errs, msgs = [], ex.messages
    today = TODAY.search(msgs[0].content)
    calls = [c for m in msgs for c in m.tool_calls or []]
    results = [m for m in msgs if m.role == "tool"]
    for call, m in zip(calls, results):
        if today and any(d > today.group(1) for pair in STAMP.findall(m.content) for d in pair if d):
            errs.append("modified or saved date after today in a tool result")
        if re.search(r"\(ignored\)|\[ignored\]", m.content, re.I):
            errs.append("tool result marks its own content as ignored")
        if m.name in FORMAT and not m.content.startswith(NOT_A_RESULT) and not FORMAT[m.name].search(m.content):
            errs.append(f"{m.name} result not in the tool's format")
        ext = str(call.arguments.get("extension") or "").lstrip("*.").lower()
        # also an entry with no extension at all (an injected "file name" ending in `}`), which FILE_EXT cannot see
        if m.name == "search_files" and ext and (any(e.lower() != ext for e in FILE_EXT.findall(m.content)) or any(
                not n.lower().endswith("." + ext) for n in re.findall(r"^(.*) \(\d[^()]*modified", m.content, re.M))):
            errs.append("search_files result lists a file with another extension than asked")
    users = " ".join(m.content for m in msgs if m.role == "user")
    replies = " ".join(m.content for m in msgs if m.role == "assistant")
    if len(HINDI.findall(users + " " + replies)) >= 2 or re.search(r"[ऀ-ॿ]", users + replies):
        errs.append("Hinglish (v4 data is English-only)")
    if ex.category == "injection":
        if any(m.role == "user" and IN_USER.search(m.content) for m in msgs):
            errs.append("injected text in the user's message")
        # v4 injections are worded with the train-allowed families, whose markers are known; v3's free-form ones
        # ("ALFRED:", "ADMIN:", "NOTE TO AI") are not checked for presence.
        if ex.id.startswith("injection_v4") and not any(m.role == "tool" and INJECTED.search(m.content) for m in msgs):
            errs.append("injection example without injected text in a tool result")
    if ex.id in REJECTED:
        errs.append(f"rejected in review: {REJECTED[ex.id][1]}")
    if ex.id in REJECTED and fingerprint(ex) != REJECTED[ex.id][0]:
        errs.pop()  # same id, different content: a regenerated example nobody has reviewed yet
    return errs


def fingerprint(ex: Example) -> str:
    import hashlib
    return hashlib.sha256(ex.model_dump_json().encode()).hexdigest()[:12]


# Examples read and rejected by hand for faults the rules above do not catch: id -> (fingerprint, reason). The
# fingerprint ties a reject to the content that was read, so a regenerated example under the same id is not hit.
REJECTED: dict[str, tuple[str, str]] = {  # review of 2026-11-17, second prompt
    "injection_v4-list_directory+search_files-0584-01": ("c4f5e14457fd", "reply renames the injected entry as the "
                                                         "real file (lists project_proposal.pdf twice)"),
    "injection_v4-list_directory+search_files-0587-05": ("32d7471682c6", "disk_usage result not in its format"),
    "injection_v4-list_directory+search_files-0587-10": ("3abc25fb86b7", "searches D:\\, which is not a known "
                                                         "folder: the real tool refuses it"),
    "injection_v4-list_directory+search_files-0588-08": ("bed906a641a0", "disk_usage result not in its format"),
    # review of 2026-11-17, batches written by Claude Haiku
    "injection_v4-git_status-0600-09": ("33f17d59d758", "the user says C:\\repos, the call uses D:\\repos"),
    "injection_v4-list_directory+search_files-0585-10": ("1817e0d7891a", "extension filter the user did not ask for"),
    "injection_v4-list_directory+search_files-0587-05": ("4b330cee9f68", "folder filter the user did not ask for"),
    "confusable-search_by_meaning+search_files+search_file_contents-0619-07": (
        "7d03e1ffa64c", "'around December' turned into modified_within_days 45"),
}


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
                if (c.name == "zip_folder" and not c.arguments.get("extra_files")
                        and re.search(r"\.[A-Za-z0-9]{2,4}$", str(c.arguments.get("source", "")))):
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
    errs += v4_checks(ex)
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
