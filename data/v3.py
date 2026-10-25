"""v3 data fixes (data/to_fix.md): drops, rewrites and new examples on top of the v2 synthetic set.

New and rewritten conversations are written by Claude agents (not the Groq/Cerebras teacher) into data/out/v3/, in
the teacher's format ({"conversations": [{"category", "messages"}]}, keyed by batch id), then audited.

Usage:
  uv run python -m data.v3 specs                 # data/out/v3/specs.json: user, folders, date, system prompt per batch
  uv run python -m data.v3 build <name>          # v3/<name>.gen.json -> v3/<name>.jsonl (+ validator errors)
  uv run python -m data.v3 assemble              # v2 valid - drops - Hinglish + rewrites + new, then the contracts 1.2
                                                 # transforms (data/v3_change_plan.md) -> synthetic.valid.jsonl
Run `assemble` after `data.validate` (which rewrites synthetic.valid.jsonl from the teacher output), then `data.mix`.
"""

import difflib
import json
import random
import re
import sys
import zlib
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from alfred.contracts.export import openai_tools
from alfred.contracts.prompt import render_system_prompt
from alfred.contracts.schemas import Example, Message
from data.gen.prompts import EXTRA, USERS
from data.validate import check

ROOT = Path(__file__).parent
OUT, V3 = ROOT / "out", ROOT / "out" / "v3"
BASE = V3 / "v2.valid.jsonl"  # the v2 synthetic.valid.jsonl, kept so assemble can be rerun
HINGLISH = {"kar", "karo", "kardo", "hai", "hain", "mein", "mujhe", "mera", "meri", "kya", "kitna", "kitni", "yaar",
            "bhai", "batao", "dikhao", "wala", "wali", "kahan", "kal", "aaj", "chahiye", "banao", "yaad", "sabse",
            "karna", "karke", "kaise", "abhi", "bata", "dikha", "daal", "nahi", "bhi", "usko", "isko", "jo", "ko",
            "ke", "ka", "ki", "se", "aur", "apna", "apni", "mere", "koi", "liye", "wale", "khol", "kholke", "dikhado",
            "dhoondo", "dhundo", "dekho", "dekh", "padho", "padh", "rakhna", "rakh", "hata", "bana", "karlo", "maine",
            "uska", "uske", "usme", "yeh", "ye", "kaun", "kaunsa", "bhaiya", "raha", "rahe", "sakte", "jaaye", "mil"}
# ids listed in to_fix.md, by the section they're listed under -> what v3 does with them
ACTIONS = {"001": "drop", "010 recall+copy_file": "drop", "010 recall+zip_folder": "drop",
           "010 search_files+move_file": "drop", "010, 017 recall+calculate": "drop", "010 read_file+create_note": "drop",
           "010 recall+open_path": "rewrite", "010 recall+git_status": "rewrite",
           "010 disk_usage+list_directory": "rewrite", "010 list_directory+read_file": "rewrite",
           "009 name": "drop", "009 extension": "drop", "009 where": "drop", "011 day": "rewrite",
           "011 every": "rewrite", "013": "rewrite", "014": "drop", "017": "rewrite"}
EXTRA_DROPS = {"single-zip_folder-0103-09": "004", "single-disk_usage-0054-06": "008",
               "multi-disk_usage+move_to_recycle_bin-0347-00": "001",  # missed by the 001 audit: deletes unasked
               "single-move_file-0068-01": "016",
               # found while auditing the cleanup: a guessed file name, a folder nobody named, an invented extension
               "multi-recall+copy_file-0322-00": "009", "multi-recall+copy_file-0322-04": "009",
               "single-search_file_contents-0012-09": "009", "single-search_file_contents-0012-00": "009",
               "single-search_file_contents-0020-07": "009"}
NOTE_WORDS = re.compile(r"\b(wrote|write|written|note|noted|jot|jotted)\b", re.I)


def load(path: Path) -> list[Example]:
    return [Example.model_validate_json(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def users(ex: Example) -> str:
    return " ".join(m.content for m in ex.messages if m.role == "user")


def is_hinglish(ex: Example) -> bool:
    text = users(ex)
    return bool(re.search(r"[\u0900-\u097F]", text)) or len(HINGLISH & set(re.findall(r"[a-z]+", text.lower()))) >= 2


def listed() -> dict[str, str]:
    """id -> section key, from the tables in to_fix.md."""
    key, out = None, {}
    for line in (ROOT / "to_fix.md").read_text(encoding="utf-8").splitlines():
        if m := re.match(r"## Issue (\d{3})", line):
            key = m[1]
        elif m := re.match(r"<details><summary><b>([\d, ]+)</b>(.*)", line):
            if m[2].startswith(":"):  # "<b>009</b>: first call acts ..." -> "009 name"
                words = {"first": "name", "search": "extension", '"where': "where", "reminders": "day",
                         '"every': "every"}
                key = f"{m[1]} {words.get(m[2][2:].split()[0], '')}".strip()
            else:  # "<b>010</b> recall+copy_file: ..."
                key = f"{m[1]} {m[2].split(':')[0].strip()}"
        elif key and (m := re.match(r"\| `([a-z_+\-0-9]+-\d{4}-\d{2})` \|", line)):
            out[m[1]] = key
    return out


def recall_notes(exs: list[Example]) -> set[str]:
    """Issue 018: "where did I write/note X" answered with recall (moves to search_notes; dropped here)."""
    return {e.id for e in exs if any(c.name == "recall" for m in e.messages for c in (m.tool_calls or []))
            and NOTE_WORDS.search(users(e)) and not any(c.name == "search_notes" for m in e.messages
                                                         for c in (m.tool_calls or []))}


def specs(seed: int = 2610) -> list[dict]:
    """Batches for the new examples: an English-only style list and dates away from the eval date (2026-10-22)."""
    rng, out = random.Random(seed), []
    for k in range(420):  # 0-399 for the issues, 400-419 for the search_file_contents top-up
        u = rng.choice(USERS)
        folders = {n: f"C:\\Users\\{u}\\{n}" for n in ("Documents", "Downloads", "Desktop", "Pictures")}
        for name, path in rng.sample(EXTRA, rng.randint(1, 3)):
            folders[name] = path.format(u=u)
        day = date(2026, 1, 1) + timedelta(days=rng.randrange(365))
        if day == date(2026, 10, 22):
            day += timedelta(days=3)
        out.append({"id": f"v3-{k:03d}", "user": u, "folders": folders, "date": day.isoformat(),
                    "styles": rng.choice(["mostly normal, a few terse", "half casual/terse, some typos",
                                          "polite and wordy, some terse", "varied: normal, terse, typos"]),
                    "system": render_system_prompt(folders, day, "1.1")})  # the transform swaps in 1.2
    return out


def build(name: str) -> int:
    """v3/<name>.gen.json ({batch id or example id: [conversations]}) -> v3/<name>.jsonl of valid Examples."""
    sp = {s["id"]: s for s in json.loads((V3 / "specs.json").read_text(encoding="utf-8"))}
    base = {e.id: e for e in load(BASE)}
    gen = json.loads((V3 / f"{name}.gen.json").read_text(encoding="utf-8"))
    good, bad = [], []
    for key, convs in gen.items():
        for k, conv in enumerate(convs):
            if key in base:  # a rewrite keeps the id and system prompt of the example it replaces
                eid, system = key, base[key].messages[0].content
            else:
                eid, system = f"{key}-{name}-{k:02d}", sp[key]["system"]
            try:
                msgs = [Message.model_validate({**m, "content": m.get("content") or ""}) for m in conv["messages"]
                        if m.get("role") != "system"]
                ex = Example(id=eid, source="synthetic", category=conv["category"],
                             messages=[Message(role="system", content=system), *msgs], tools=openai_tools())
                errs = check(ex)
            except Exception as e:  # noqa: BLE001 - malformed agent output is counted, not fatal
                errs, ex = [f"{type(e).__name__}: {str(e)[:150]}"], None
            (bad if errs else good).append((eid, errs, ex))
    (V3 / f"{name}.jsonl").write_text("".join(ex.model_dump_json() + "\n" for _, _, ex in good), encoding="utf-8")
    print(f"{name}: {len(good)}/{len(good) + len(bad)} valid -> {V3 / (name + '.jsonl')}")
    for eid, errs, _ in bad:
        print(f"  {eid}: {'; '.join(errs)}")
    return 0


# --- contracts 1.2 transforms (data/v3_change_plan.md): folder-less search, system prompt, v2 format cleanup ----------

OLD_RULE = ("- Changes to files run only after the user confirms them in the app, so call the tool directly. "
            "Deleting always means move_to_recycle_bin.\n")
NEW_RULE = ("- When the user asks for a change, call the tool directly: the app asks them to confirm. Don't change anything "
            "they didn't ask for. Deleting always means move_to_recycle_bin.\n"
            "- Look things up before using them: never guess a file name, a number or a date.\n")
HIT = re.compile(r"^(.+) \((.+), modified (\d{4}-\d{2}-\d{2})\)$")
ALIASES = {"docs": "documents", "document": "documents", "download": "downloads", "picture": "pictures",
           "photos": "pictures", "photo": "pictures", "video": "videos", "movies": "videos"}
REL_WORDS = re.compile(r"\b(today|yesterday|tomorrow|tonight|ago|last week|this week|last month|this month)\b", re.I)
ISO = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
PLACEHOLDER = re.compile(r"\n[ \t]*(?:\d+\.[ \t]*)?\.\.\.[ \t]*(?=\n|$)")
SEARCH_KEY = lambda c: (c.arguments["query"], c.arguments.get("extension"), c.arguments.get("modified_within_days"))


def known(ex: Example) -> dict[str, str]:
    """Known folder name (casefolded) -> path (casefolded, no trailing slash), from the system prompt."""
    block = re.search(r"Known folders:\n(.*?)\n\n", ex.messages[0].content, re.S)[1]
    return {n.casefold(): p.strip().rstrip("\\").casefold() for n, p in (ln[2:].split(": ", 1) for ln in block.splitlines())}


def folder_name(folder: str | None, kn: dict[str, str]) -> str | None:
    f = (folder or "").strip().rstrip("\\").casefold()
    return f if f in kn else next((n for n, p in kn.items() if p == f), None)


def merge_results(results: list[str]) -> str:
    """Pool several search_files results into the one result a folder-less search prints (newest first)."""
    lines = sorted((ln for r in results for ln in r.splitlines()[1:] if HIT.match(ln)),
                   key=lambda ln: (HIT.match(ln)[3], ln), reverse=True)
    return "No matching files found." if not lines else f"{len(lines)} file{'s' if len(lines) != 1 else ''}:\n" + "\n".join(lines)


def merge_fanouts(ex: Example) -> Example | None:
    """T1: one search_files call per known folder (alone, or after a miss in the folder the user named) becomes one
    call without a folder. None if nothing changed."""
    kn, msgs, changed, seen = known(ex), list(ex.messages), False, {}
    i = 0
    while i < len(msgs):
        m = msgs[i]
        calls = [c for c in (m.tool_calls or []) if c.name == "search_files"]
        if m.role == "assistant" and len(calls) > 1 and len(calls) == len(m.tool_calls):
            results = msgs[i + 1:i + 1 + len(calls)]
            folders = {folder_name(c.arguments.get("folder"), kn) for c in calls} | seen.get(SEARCH_KEY(calls[0]), set())
            if len({SEARCH_KEY(c) for c in calls}) == 1 and folders == set(kn) and all(r.name == "search_files" for r in results):
                args = {k: v for k, v in calls[0].arguments.items() if k != "folder"}
                msgs[i:i + 1 + len(calls)] = [
                    m.model_copy(update={"tool_calls": [calls[0].model_copy(update={"arguments": args})]}),
                    results[0].model_copy(update={"content": merge_results([r.content for r in results])})]
                changed = True
        for c in msgs[i].tool_calls or []:
            if c.name == "search_files":
                seen.setdefault(SEARCH_KEY(c), set()).add(folder_name(c.arguments.get("folder"), kn))
        i += 1
    return ex.model_copy(update={"messages": msgs}) if changed else None


def unasked_folder(ex: Example) -> Example | None:
    """T2: the first search_files names a folder no user turn mentions -> leave it out. None if nothing changed."""
    kn, text = known(ex), users(ex).casefold()
    words = set(re.findall(r"[a-z]+", text))
    words |= {ALIASES[w] for w in words if w in ALIASES}
    words |= {f for w in words for f in difflib.get_close_matches(w, kn, 1, 0.8)}  # 'downlods'
    for k, m in enumerate(ex.messages):
        for c in m.tool_calls or []:
            if c.name != "search_files":
                continue
            f = folder_name(c.arguments.get("folder"), kn)
            if f is None or f in words or kn[f] in text or c.arguments.get("folder", "").casefold() in text:
                return None
            msgs = list(ex.messages)
            msgs[k] = m.model_copy(update={"tool_calls": [
                x.model_copy(update={"arguments": {a: v for a, v in x.arguments.items() if a != "folder"}}) if x is c else x
                for x in m.tool_calls]})
            return ex.model_copy(update={"messages": msgs})
    return None


PROC = re.compile(r"^.+ \d+% CPU, [\d.]+ [KMGT]?B$")
COUNT_HEAD = re.compile(r"^(\d+) (?:files?|notes?|upcoming)\b|\((\d+) items\)|^Top (\d+) by ")
# date positions that are metadata, not content: search_files "modified D", search_notes "Title (D):", recall "(saved D)"
META_DATE = {"search_files": re.compile(r"modified (\d{4}-\d{2}-\d{2})"), "search_notes": re.compile(r"\((\d{4}-\d{2}-\d{2})\):"),
             "recall": re.compile(r"saved (\d{4}-\d{2}-\d{2})")}


def hinglish_text(text: str) -> bool:
    return bool(re.search(r"[ऀ-ॿ]", text)) or len(HINGLISH & set(re.findall(r"[a-z]+", text.lower()))) >= 2


NOTE_ROW = re.compile(r"^(?:\d+\. )?(.+? \(\d{4}-\d{2}-\d{2}\): .*)$")
SIZE_WHOLE = re.compile(r"(?<![\d.,])(\d+) ([MGT]B)\b")
SFC_ROW = re.compile(r'^.+: "\.\.\..*\.\.\."$')


SIZE_UNITS = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}
DRIVES_GB = (237.9, 476.0, 953.9, 1863.0)
DU_ROW = re.compile(r"^(.+?) (?:≥ )?([\d.]+) ([KMGT]?B)$")


def to_bytes(num: str, unit: str) -> float:
    return float(num) * SIZE_UNITS[unit]


def disk_usage_fix(c: str, replies: str, lenient: bool) -> str | None:
    """disk_usage printed the way the tool does: a folder's first line is "<path>: drive X:\\ has A free of B." and
    "Largest:" lists direct children with sizes. v2 wrote "<path> T total, F free." for folders, with the folder's own
    size as T: that is not a drive, so the rewrite needs a drive big enough for what is listed. None = drop."""
    lines = c.splitlines()
    folder = re.match(r"^(?![A-Z]:\\ )(.+?\\[^\n]*?) ([\d.]+ [KMGT]?B) total, ([\d.]+) ([KMGT]?B) free\.$", lines[0])
    root = re.match(r"^([A-Z]:\\) [\d.]+ [KMGT]?B total, .* free\.$", lines[0])
    head_path = folder[1] if folder else root[1] if root else (lines[0].split(": drive ")[0] if ": drive " in lines[0] else None)
    rows = [ln for ln in lines[1:] if ln.strip() and ln != "Largest:"]
    if lenient or head_path is None:
        return c if lenient else None
    listed = 0.0
    for ln in rows:
        r = DU_ROW.match(ln)
        if not r:
            return None
        parent = r[1].rsplit("\\", 1)[0].rstrip("\\").casefold()
        if parent != head_path.rstrip("\\").casefold():
            return None
        listed += to_bytes(r[2], r[3])
    if folder:
        for quoted in {folder[2], re.sub(r"\.0 ", " ", folder[2])}:  # a reply quotes the old "total" (with or without .0)
            if re.search(re.escape(quoted).replace(r"\ ", r"[\s\u202f]"), replies):
                return None
        free = to_bytes(folder[3], folder[4])
        need = (free + listed) / 1024 ** 3 + 10
        total = next((d for d in DRIVES_GB if d >= need), None)
        if total is None:
            return None
        lines[0] = f"{folder[1]}: drive {folder[1][:3]} has {folder[3]} {folder[4]} free of {total:.1f} GB."
    return "\n".join(lines)


def fix_result(m: Message, replies: str, lenient: bool = False) -> Message | str | None:
    """One tool result: bring it to what the real tool prints (miss texts, row formats, sort order, size decimals), make
    a count header agree with its rows (or "drop" when a reply states the count). `lenient` = an injection example,
    whose rows may carry the injected text: only the safe rewrites. None if the result is fine as it is."""
    c, name = m.content, m.name
    if name == "search_files" and re.fullmatch(r"0 files found|No files found\.?|No matching files\.?", c):
        c = "No matching files found."
    if name == "search_file_contents" and re.match(r"0 files|No (matching )?files", c):
        c = "No matching files found."
    if name == "list_reminders" and not re.search(r"^\d+\. ", c, re.M):
        c = "No upcoming reminders."
    if name == "top_processes":  # v2 teacher formats -> the tool's "name 14% CPU, 2.4 GB"
        c = re.sub(r"^(.+?) ([\d.]+) ([KMGT]?B) RAM, (\d+)% CPU$",
                   lambda g: f"{g[1]} {g[4]}% CPU, {float(g[2]):.{0 if g[3] in ('B', 'KB') else 1}f} {g[3]}", c, flags=re.M)
        c = re.sub(r"^(?!.*% CPU)(.+?) ([\d.]+) ([KMGT]?B)$",  # memory-only rows get a small CPU share
                   lambda g: f"{g[1]} {zlib.crc32(g[0].encode()) % 6 + 1}% CPU, {g[2]} {g[3]}", c, flags=re.M)
    if name in ("top_processes", "search_files", "list_directory", "disk_usage", "zip_folder"):  # MB/GB/TB get a decimal
        c = SIZE_WHOLE.sub(lambda g: f"{g[1]}.0 {g[2]}", c)
    if name in ("search_files", "list_directory"):  # under 1 KB the tool prints bytes
        c = re.sub(r"\b0 KB\b", "0 B", c)
    if name == "search_file_contents":  # v2 teacher row shapes -> path: "...snippet..."
        c = re.sub(r"^(.+?) \(contains '(.*)'\)$", r'\1: "...\2..."', c, flags=re.M)
        c = re.sub(r'^(.+?): "(?!\.\.\.)(.*?)(?<!\.\.\.)"$', r'\1: "...\2..."', c, flags=re.M)
    if name == "disk_usage":
        c = disk_usage_fix(c, replies, lenient)
        if c is None:
            return "drop"
    if name == "read_file":  # the header's char count is the length of the text shown (when it isn't cut)
        head, _, body = c.partition("\n")
        body = body.rstrip("\n")
        stated = re.search(r"\(([\d,]+) chars\):?$", head)
        if stated and "more chars)" not in body and int(stated[1].replace(",", "")) != len(body):
            if re.search(rf"\b{re.escape(stated[1])}\b", replies):
                return "drop"
            c = head.replace(stated[1], f"{len(body):,}") + "\n" + body
    lines = c.splitlines()
    if name == "search_notes" and c != "No matching notes.":  # one numbered line per "Title (date): text"; other lines wrap
        notes = []
        for ln in lines[1:]:
            if NOTE_ROW.match(ln) or not notes:
                notes.append(NOTE_ROW.sub(r"\1", ln))
            else:
                notes[-1] = " ".join((notes[-1] + " " + ln).split())
        lines = [lines[0]] + [f"{i}. {n}" for i, n in enumerate(notes, 1)]
    rows = lines[1:] if len(lines) > 1 else []
    if lenient:
        out = "\n".join(lines)
        return m.model_copy(update={"content": out}) if out != m.content else None
    if name == "list_directory" and any(not re.fullmatch(r".+\\ \(folder\)|.+ \(\d+(\.\d)? [KMGT]?B\)|\(empty\)|\.\.\. and \d+ more", r)
                                         for r in rows if r.strip()):
        return "drop"
    if name == "list_directory" and rows and not any(r.startswith("(empty)") for r in rows):
        tail = [r for r in rows if r.startswith("... and ")]
        body = sorted((r for r in rows if r.strip() and not r.startswith("... and ")),
                      key=lambda r: (not r.endswith("(folder)"), r.split(" (")[0].rstrip("\\").casefold()))
        lines = [lines[0], *body, *tail]
    if name == "search_files" and c != "No matching files found.":
        if not rows or not all(HIT.match(ln) for ln in rows if not ln.startswith("... and ")):
            return "drop"
        hits = sorted((ln for ln in rows if HIT.match(ln)), key=lambda ln: (HIT.match(ln)[3], ln), reverse=True)
        lines = [lines[0], *hits, *(ln for ln in rows if ln.startswith("... and "))]
    if name == "search_file_contents" and c != "No matching files found." and not all(
            SFC_ROW.match(ln) for ln in rows if not ln.startswith("... and ")):
        return "drop"
    if name == "top_processes" and not all(PROC.match(ln) for ln in rows if ln.strip()):
        return "drop"
    head = COUNT_HEAD.search(lines[0]) if lines else None
    if head and name in ("search_files", "search_notes", "list_directory", "list_reminders", "top_processes",
                         "search_file_contents"):
        shown = [ln for ln in lines[1:] if ln.strip() and not ln.startswith("... and ")]
        stated = int(next(g for g in head.groups() if g))
        more = re.search(r"^\.\.\. and (\d+) more", c, re.M)
        total = len(shown) + (int(more[1]) if more else 0)
        if total != stated:
            if re.search(rf"\b{stated}\b", replies):
                return "drop"
            lines[0] = lines[0].replace(str(stated), str(total), 1)
            if name in ("search_files", "search_file_contents"):
                lines[0] = re.sub(r"^1 files", "1 file", re.sub(r"^(?!1 )(\d+) file:", r"\1 files:", lines[0]))
    out = "\n".join(lines)
    return m.model_copy(update={"content": out}) if out != m.content else None


def clean_format(ex: Example) -> Example | None | str:
    """C: results the real tools never print. Returns the fixed example, None if nothing to fix, "drop" if unfixable."""
    msgs, changed = list(ex.messages), False
    today = re.search(r"Today is (\d{4}-\d{2}-\d{2})", msgs[0].content)[1]
    replies = " ".join(m.content for m in msgs if m.role == "assistant")
    if hinglish_text(replies):
        return "drop"
    for k, m in enumerate(msgs):
        if m.role != "tool":
            continue
        if m.name == "disk_usage" and not re.search(r"(total, .* free\.|has .* free of )", m.content):
            return "drop"
        if re.search(r"[\\/][A-Z]:\\", m.content):
            return "drop"
        c = PLACEHOLDER.sub("", m.content)
        if m.name == "read_file" and c != m.content:  # the char count has to match what is left of the body
            head, _, body = c.partition("\n")
            stated = re.search(r"\(([\d,]+) chars\)", head)
            if not stated or re.search(rf"\b{re.escape(stated[1])}\b", replies):
                return "drop"
            c = head.replace(stated[1], f"{len(body):,}") + "\n" + body
        if c != m.content:
            msgs[k], changed = m.model_copy(update={"content": c}), True
        r = fix_result(msgs[k], replies, ex.category == "injection")
        if r == "drop":
            return "drop"
        if r is not None:
            msgs[k], changed = r, True
    # KB sizes print as whole numbers: rewrite every "1.2 KB" in results and replies
    kb = {x: (f"{int(float(x[:-3]) + 0.5)} KB" if float(x[:-3]) >= 0.5 else f"{round(float(x[:-3]) * 1024)} B")
          for m in msgs if m.role in ("tool", "assistant") for x in re.findall(r"\d+\.\d+ KB", m.content)}
    if kb:
        for k, m in enumerate(msgs):
            if m.role in ("tool", "assistant") and re.search(r"\d+\.\d+ KB", m.content):
                msgs[k] = m.model_copy(update={"content": re.sub(r"\d+\.\d+ KB", lambda g: kb[g[0]], m.content)})
        changed = True
    # dates after "today" in result metadata (v2 examples only; reminder results are future-dated by design): move
    # today to a few days after the newest one, if nothing else in the example depends on it, else drop
    tools = {m.name for m in msgs if m.role == "tool"}
    newest = max((d for m in msgs if m.role == "tool" and m.name in META_DATE for d in META_DATE[m.name].findall(m.content)),
                 default=today)
    if newest > today and not ex.id.startswith("v3-"):
        if tools & {"set_reminder", "list_reminders", "calculate"} or REL_WORDS.search(users(ex)) or any(
                REL_WORDS.search(m.content) for m in msgs if m.role == "assistant"):
            return "drop"
        d = date.fromisoformat(newest) + timedelta(days=1 + zlib.crc32(ex.id.encode()) % 6)
        if d == date(2026, 10, 22):  # the eval date stays out of the training data
            d += timedelta(days=1)
        msgs[0] = msgs[0].model_copy(update={"content": re.sub(r"Today is [^\n]*", f"Today is {d:%Y-%m-%d} ({d:%A}).",
                                                              msgs[0].content)})
        changed = True
    return ex.model_copy(update={"messages": msgs}) if changed else None


def transform(exs: list[Example]) -> tuple[list[Example], Counter]:
    """All of the above, in order, on the assembled synthetic set."""
    n, out = Counter(), []
    for e in exs:
        system = e.messages[0].content
        assert OLD_RULE in system or NEW_RULE in system, e.id
        if OLD_RULE in system:
            e = e.model_copy(update={"messages": [e.messages[0].model_copy(update={"content": system.replace(OLD_RULE, NEW_RULE)}),
                                                  *e.messages[1:]]})
            n["prompt rule swapped"] += 1
        for name, fn in (("T1 merged search fan-out", merge_fanouts), ("T2 unasked folder removed", unasked_folder),
                         ("C format cleaned", clean_format)):
            r = fn(e)
            if r == "drop":
                n["C dropped"] += 1
                e = None
                break
            if r is not None:
                e, n[name] = r, n[name] + 1
        if e is not None:
            calls = sum(len(m.tool_calls or []) for m in e.messages)
            if e.category == "multi_step" and calls < 2:  # a merged search can leave a single call
                e, n["multi_step -> tool_call"] = e.model_copy(update={"category": "tool_call"}), n["multi_step -> tool_call"] + 1
            out.append(e.model_copy(update={"tools": openai_tools()}))  # contracts 1.2 for every example
    return out, n


def assemble() -> int:
    base, ids = load(BASE), listed()
    hing = {e.id for e in base if is_hinglish(e)}
    notes = recall_notes(base)
    drops = {i for i, k in ids.items() if ACTIONS.get(k) == "drop"} | set(EXTRA_DROPS) | notes | hing
    rewrites = {}
    for f in sorted(V3.glob("rewrite*.audited.jsonl")):
        rewrites.update({e.id: e for e in load(f)})
    pending = {i for i, k in ids.items() if ACTIONS.get(k) == "rewrite"} - hing - set(rewrites)
    new = [e for f in sorted(V3.glob("issue*.audited.jsonl")) for e in load(f)]
    out = [rewrites.get(e.id, e) for e in base if e.id not in drops and e.id not in pending] + new
    out, counts = transform(out)
    (OUT / "synthetic.valid.jsonl").write_text("".join(e.model_dump_json() + "\n" for e in out), encoding="utf-8")
    print(f"v2 {len(base)}: dropped {len(drops & {e.id for e in base})} (Hinglish {len(hing)}, recall-for-notes "
          f"{len(notes - hing)}), rewritten {len(rewrites)}, rewrite missing so dropped {len(pending)}, "
          f"new {len(new)} -> {len(out)}")
    print("  new by category:", dict(Counter(e.category for e in new)))
    print("  transforms:", dict(counts), "->", len(out))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cmd = sys.argv[1]
    if cmd == "specs":
        V3.mkdir(parents=True, exist_ok=True)
        assert not (V3 / "specs.json").exists(), "specs.json is what the generated conversations were written against"
        (V3 / "specs.json").write_text(json.dumps(specs(), indent=1, ensure_ascii=False), encoding="utf-8")
    sys.exit(build(sys.argv[2]) if cmd == "build" else assemble() if cmd == "assemble" else 0)
