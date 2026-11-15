"""Hard multi-step suite (v4 track 1A): parametric tasks whose ground truth is computed from the fixture.

A family is a function that fills a seeded `World` (files with sizes and dates, memories, notes) and returns the
turns: the request, the changes it asks for, and the facts the answer must contain. From that one description come
the confirm policy (only the requested change is approved), the expected end state (every file, compared exactly),
the scripted oracle and the scripted agents that must fail (null, wrong, extra).

Two pools share the shared families but nothing else: seeds, file names, folder names and phrasings are disjoint.
`test` also has held-out families that no training rollout uses. The families come from the failure classes in
data/to_fix.md (issues 004, 006-008, 011-018).

  uv run python -m eval.e2e.hard --write     # regenerate eval/e2e/hard_test.jsonl and print its SHA-256
"""

import hashlib
import json
import random
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

from alfred.agent.backends import RawCall, Result
from alfred.tools import memory, productivity
from alfred.tools.guards import known_folders
from eval.e2e.tasks import FOLDERS, Task

FROZEN = Path(__file__).with_name("hard_test.jsonl")
TRAIN_SEED0 = 1000  # test seeds are 0..7, train seeds start here
QUALS = ["2023", "2024", "2025", "q1", "q2", "q3", "march", "june", "october", "final", "signed", "draft", "old",
         "revised"]
EXTS = ["pdf", "xlsx", "jpg", "pptx", "png", "docx"]  # binary bodies; text files are written by the families
VOCAB = {
    "test": {
        "stems": ["invoice", "lease", "syllabus", "itinerary", "minutes", "roadmap", "thesis", "payslip", "warranty",
                  "recipe", "manual", "transcript", "proposal", "survey", "brochure", "contract", "newsletter",
                  "blueprint", "ledger", "permit"],
        "subs": ["archive", "scans", "clients", "housing", "travel", "coursework", "receipts", "shared", "inbox",
                 "keepsakes"],
        "words": ["indigo", "falcon", "cobalt", "maple", "quartz", "harbor", "lantern", "saffron"],
        "items": ["rent", "groceries", "fuel", "internet", "insurance", "gym", "books", "repairs"]},
    "train": {
        "stems": ["report", "budget", "voucher", "summary", "diagram", "receipt", "schedule", "agenda", "essay", "slides",
                  "ticket", "statement", "handbook", "memo", "checklist", "outline", "letter", "plan", "roster",
                  "quote"],
        "subs": ["work", "personal", "projects", "taxes", "school", "backup", "misc", "reports", "temp", "finance"],
        "words": ["amber", "otter", "nickel", "cedar", "garnet", "meadow", "beacon", "pepper"],
        "items": ["electricity", "water", "phone", "taxi", "software", "coffee", "parking", "laundry"]},
}


def P(rel: str) -> str:
    """Fixture path -> the Windows path a user would type: Downloads\\scans\\a.pdf."""
    return rel.replace("/", "\\")


def base(rel: str) -> str:
    return rel.rsplit("/", 1)[-1]


@dataclass
class Turn:
    text: str
    look: list = field(default_factory=list)  # read-only calls the oracle makes: (tool, args)
    ops: list = field(default_factory=list)  # changes the request asks for; the simulated user approves exactly these
    declined: list = field(default_factory=list)  # changes the user asked for and then says no to at the prompt
    facts: list = field(default_factory=list)  # the answer must contain each: text, a number, or a tuple of options
    notes: list = field(default_factory=list)  # (title, key text) notes this turn must create
    reminders: list = field(default_factory=list)  # "YYYY-MM-DD HH:MM" reminders this turn must set
    ask: bool = False  # the right move is a question; nothing may be proposed
    new_chat: bool = False

    def approve(self, data: dict) -> bool:
        return canon(data) in {key(o) for o in self.ops}


# --- changes: ("move"|"copy", src, dst) · ("recycle", path) · ("zip", (sources,), folder): the zip may have any name there; paths like Downloads/a.pdf

def key(op) -> tuple:
    return tuple(tuple(sorted(s.casefold() for s in x)) if isinstance(x, (tuple, list)) else x.casefold() for x in op)


def _rel(path) -> str:
    p = str(path).casefold()
    for name, root in known_folders().items():
        r = str(Path(root).resolve()).casefold()
        if p == r or p.startswith(r + "\\"):
            return (name.casefold() + p[len(r):]).replace("\\", "/")
    return p


def canon(d: dict) -> tuple:
    """A confirmation (name, args, preview) as a change in the form above. The preview has the resolved paths, so
    a rename and a move to the same place are the same change."""
    name, pv = d["name"], d["preview"]
    if name in ("move_file", "copy_file"):
        a, b = pv.split(" ", 1)[1].split(" → ")
        return name[:4], _rel(a), _rel(b)
    if name == "rename_file":
        a, b = pv.removeprefix("Rename ").split(" → ")
        return "move", _rel(a), _rel(Path(a).with_name(b))
    if name == "zip_folder":
        a, b = pv.removeprefix("Zip ").split(" → ")
        return "zip", tuple(sorted(map(_rel, a.split(", ")))), _rel(Path(b).parent)
    if name == "move_to_recycle_bin":
        return "recycle", _rel(pv.removeprefix("Move ").removesuffix(" to the Recycle Bin (restorable)"))
    return name, json.dumps(d["args"], sort_keys=True)


def apply(files: dict, op) -> None:
    """Carry out a change on {path: body}; a path may be a folder. A zip's name and content are not predicted."""
    if op[0] == "zip":
        files[f"{op[2]}/*.zip"] = None
        return
    for f in [f for f in files if f == op[1] or f.startswith(op[1] + "/")]:
        if op[0] != "recycle":
            files[op[2] + f[len(op[1]):]] = files[f]
        if op[0] != "copy":
            del files[f]


def call_for(op) -> tuple:
    if op[0] in ("move", "copy"):
        return f"{op[0]}_file", {"source": P(op[1]), "destination": P(op[2])}
    if op[0] == "recycle":
        return "move_to_recycle_bin", {"path": P(op[1])}
    first, *rest = op[1]
    return "zip_folder", {"source": P(first), "destination": P(op[2]), **({"extra_files": list(map(P, rest))} if rest else {})}


NUM = re.compile(r"(?<![\w.,-])\d[\d,]*(?:\.\d+)?(?!\d)")  # not the 2024 in lease_2024.pdf or the 11 in 2026-11-20


def has_fact(answer: str, fact) -> bool:
    # ponytail: a count is found if the number appears anywhere in the answer (a numbered list can supply it);
    # an LLM judge would be stricter and is not reproducible.
    if isinstance(fact, (tuple, list)):
        return any(has_fact(answer, f) for f in fact)
    if isinstance(fact, (int, float)):
        return any(abs(float(n.replace(",", "")) - fact) < 0.006 for n in NUM.findall(answer))
    return fact.casefold() in answer.casefold()


def state_diff(root: Path, want: dict) -> str | None:
    have = {str(p.relative_to(root)).replace("\\", "/").casefold(): p
            for f in FOLDERS for p in (root / f).rglob("*") if p.is_file()}
    want = {k.casefold(): v for k, v in want.items()}
    for k in [k for k, v in want.items() if v is None]:  # one new .zip in that folder, whatever it is called
        new = sorted(h for h in have.keys() - want.keys() if h.endswith(".zip") and h.rsplit("/", 1)[0] == k[:-6])
        if new:
            del want[k], have[new[0]]
    if have.keys() != want.keys():
        return (f"files differ: missing {sorted(want.keys() - have.keys())[:4]}, "
                f"unexpected {sorted(have.keys() - want.keys())[:4]}")
    bad = [k for k, v in want.items() if
           (have[k].read_text(encoding="utf-8") if isinstance(v, str) else have[k].read_bytes()) != v]
    return f"wrong content in {bad[:4]}" if bad else None


@dataclass
class HardTask(Task):
    family: str = ""
    pool: str = ""
    seed: int = 0
    steps: list = field(default_factory=list)
    spare: str = ""  # a file no request touches: the `extra` agent tries to delete it

    def __post_init__(self):
        self.turns = [x for s in self.steps for x in ([("/new", False)] if s.new_chat else []) + [(s.text, s.approve)]]
        self.check = self.verdict

    @property
    def n_calls(self) -> int:
        return sum(len(s.look) + len(s.ops) + len(s.declined) + len(s.notes) + len(s.reminders) for s in self.steps)

    def expected(self) -> dict:
        want = dict(self.files)
        for s in self.steps:
            for o in s.ops:
                apply(want, o)
        return want

    def verdict(self, c):
        for i, (s, (events, answer)) in enumerate(zip(self.steps, c.turns), 1):
            allowed = {key(o) for o in [*s.ops, *s.declined]}
            for e in events:
                if e.kind == "confirm_required" and canon(e.data) not in allowed:
                    return f"turn {i}: proposed a change that was not asked for ({e.data['preview']})"
            if s.ask and "?" not in answer:
                return f"turn {i}: did not ask"
        if diff := state_diff(c.root, self.expected()):
            return diff
        made, want = productivity.all_notes()[len(self.notes):], [n for s in self.steps for n in s.notes]
        if len(made) != len(want) or not all(any(has_fact(n["title"], t) and has_fact(n["body"], k) for n in made)
                                             for t, k in want):
            return f"notes: expected {want}, made {[(n['title'], n['body'][:60]) for n in made]}"
        set_, due = sorted(r["when"].replace("T", " ") for r in productivity._load()), \
            sorted(r for s in self.steps for r in s.reminders)
        if set_ != due:
            return f"reminders: expected {due}, set {set_}"
        if len(memory.all_memories()) != len(self.memories):
            return "saved a memory nobody asked for"
        for i, (s, (_, answer)) in enumerate(zip(self.steps, c.turns), 1):
            if miss := [f for f in s.facts if not has_fact(answer, f)]:
                return f"turn {i}: the answer lacks {miss}"
        return True

    def script(self, mode: str = "oracle") -> list:
        """Model outputs for a scripted agent: a list of calls per step, then the answer, for each turn.
        oracle: does the task. null: does nothing. wrong: leaves out the last change, the app writes and the facts,
        and acts where it should ask. extra: the oracle plus one delete nobody asked for."""
        out = []
        for i, s in enumerate(self.steps):
            if mode == "null":
                out.append("Done.")
                continue
            wrong = mode == "wrong"
            ops = (self.steps[i + 1].ops[:1] if s.ask else s.ops[:-1]) if wrong else s.ops
            calls = [*s.look, *map(call_for, [*s.declined, *ops])]
            if not wrong:
                calls += [("create_note", {"title": t, "content": k}) for t, k in s.notes]
                calls += [("set_reminder", {"text": "as asked", "time": r}) for r in s.reminders]
            if mode == "extra" and i == 0:
                calls.append(("move_to_recycle_bin", {"path": P(self.spare)}))
            out += [[c] for c in calls]
            said = [] if wrong else [str(f[0] if isinstance(f, (tuple, list)) else f) for f in s.facts]
            out.append(" ".join(said + ["Which one do you mean?"] * s.ask) or "Done.")
        return out

    def spec(self) -> dict:
        """The task as JSON: what the frozen test file holds and what --show prints."""
        return {"id": self.id, "family": self.family, "held_out": "held_out" in self.tags, "today": self.today,
                "n_calls": self.n_calls,
                "turns": [{k: v for k, v in asdict(s).items() if v} for s in self.steps],
                "files": {f: b if isinstance(b, str) else {"bytes": len(b)} for f, b in sorted(self.files.items())},
                "mtimes": self.mtimes, "memories": self.memories, "notes": self.notes,
                "expected_files": sorted(self.expected())}


class Scripted:
    """A backend that replays `HardTask.script()` through the real loop and tools: validates the checkers with no model."""
    model = "scripted"

    def __init__(self, steps: list):
        self.steps = list(steps)

    def stream(self, messages, tools=None, temperature=0.0):
        s = self.steps.pop(0)
        yield "done", (Result(content=s, ttft=0.0) if isinstance(s, str) else
                       Result(tool_calls=[RawCall(n, a, json.dumps(a)) for n, a in s], ttft=0.0))


class World:
    """The fixture under construction. `pick` hands out vocabulary reserved for the family; clutter uses the rest."""

    def __init__(self, pool: str, family: str, seed: int):
        self.rng = r = random.Random(f"{pool}/{family}/{seed}")
        self.pool, self.seed = pool, seed
        v = {k: r.sample(words, len(words)) for k, words in VOCAB[pool].items()}
        self.own, self.spare_stems, self.v = v["stems"][:5], v["stems"][5:], v
        self.today = date(2026, 1, 5) + timedelta(days=r.randrange(600))
        self.files, self.mtimes, self.memories, self.notes, self.names = {}, {}, [], [], set()

    def pick(self, kind: str) -> str:
        return (self.own if kind == "stems" else self.v[kind]).pop()

    def cycle(self, *options):
        """The variant for this seed: consecutive seeds cover every variant."""
        return options[self.seed % len(options)]

    def top(self, *avoid: str) -> str:
        return self.rng.choice([t for t in FOLDERS if t not in {a.split("/")[0] for a in avoid}])

    def folder(self, top: str | None = None, n: int = 2) -> str:
        """A new subfolder holding n clutter files."""
        rel = f"{top or self.top()}/{self.pick('subs')}"
        for _ in range(n):
            self.file(rel)
        return rel

    def file(self, folder, stem=None, qual=None, ext=None, text=None, kb=None, days=None, name=None) -> str:
        """Add a file; every base name is unique in the fixture, so a move can never collide by accident."""
        r = self.rng
        while True:
            n = name or f"{stem or r.choice(self.spare_stems)}_{qual or r.choice(QUALS)}.{ext or r.choice(EXTS)}"
            if n not in self.names:
                break
        rel = f"{folder}/{n}"
        size = (kb or r.randrange(2, 60)) * 1024
        self.names.add(n)
        self.files[rel] = text if text is not None else (f"{rel}|".encode() * (size // len(rel) + 1))[:size]
        self.mtimes[rel] = days if days is not None else r.randrange(20, 400)
        return rel

    def say(self, test: list, train: list = (), **kw) -> str:
        return self.rng.choice(test if self.pool == "test" else train).format(**kw)


# --- shared families (both pools) ---

def find_then_act(w):  # issue 013: the path has to be looked up, not copied from the request
    stem, (q, q2), ext = w.pick("stems"), w.rng.sample(QUALS, 2), w.rng.choice(["pdf", "xlsx", "pptx"])
    src = w.folder()
    dest = w.top(src)
    target = w.file(src, stem, q, ext)
    w.file(w.folder(), stem, q2, ext)  # a look-alike somewhere else
    kind = w.cycle("move", "copy", "recycle")
    op = ("recycle", target) if kind == "recycle" else (kind, target, f"{dest}/{base(target)}")
    text = {
        "move": w.say(["Find the {q} {stem} file and move it to my {dest} folder.",
                       "I can't remember where my {q} {stem} is. Track it down and put it in {dest}."],
                      ["locate my {stem} ({q}) and move it into {dest}",
                       "there's a {q} {stem} somewhere on this laptop, please shift it to {dest}"],
                      q=q, stem=stem, dest=dest),
        "copy": w.say(["Find the {q} {stem} file and put a copy of it in {dest}.",
                       "I need a copy of my {q} {stem} in {dest}, but I don't know which folder it's in."],
                      ["locate my {stem} ({q}) and copy it into {dest}",
                       "duplicate the {q} {stem} into {dest}, wherever it currently is"],
                      q=q, stem=stem, dest=dest),
        "recycle": w.say(["Find the {q} {stem} file and delete it.",
                          "I don't need my {q} {stem} any more. Look for it and send it to the recycle bin."],
                         ["locate my {stem} ({q}) and trash it", "wherever the {q} {stem} is, get rid of it"],
                         q=q, stem=stem)}[kind]
    return [Turn(text, [("search_files", {"query": f"{stem} {q}"})], [op])]


def read_then_compute(w):  # issue 017: numbers read from the file, then calculated
    stem, kind = w.pick("stems"), w.cycle("total", "percent")
    items = w.rng.sample(w.v["items"], 4)
    amounts = [w.rng.randrange(120, 9800) + (0.5 if kind == "total" and w.rng.random() < 0.5 else 0) for _ in items]
    path = w.file(w.folder(), stem, ext="txt",
                  text=f"{stem.title()} items\n" + "".join(f"{i}: {a:,.2f}\n" for i, a in zip(items, amounts)))
    total, expr = sum(amounts), " + ".join(map(str, amounts))
    if kind == "total":
        fact = total
        text = w.say(["Add up the amounts listed in {p}.", "What do the line items in {p} come to altogether?"],
                     ["total the figures in {p} for me", "sum every amount in {p}"], p=P(path))
    else:
        pct = w.rng.choice([12, 15, 18, 28, 35])
        fact, expr = round(total * pct / 100, 2), f"({expr}) * {pct} / 100"
        text = w.say(["What is {pct}% of the total of the amounts in {p}?",
                      "Work out the sum of the amounts in {p}, then tell me {pct}% of it."],
                     ["take the figures in {p}, total them and give me {pct} percent of that",
                      "how much is {pct} percent of everything listed in {p} combined"], p=P(path), pct=pct)
    return [Turn(text, [("read_file", {"path": P(path)}), ("calculate", {"expression": expr})], facts=[fact])]


def pick_extreme(w):  # issue 014: oldest / newest / largest / smallest from a listing
    folder = w.folder(n=0)
    dest = w.top(folder)
    sizes, ages = w.rng.sample(range(20, 900, 37), 5), w.rng.sample(range(10, 300, 13), 5)
    files = [w.file(folder, kb=k, days=d) for k, d in zip(sizes, ages)]
    crit = w.cycle("oldest", "largest", "newest", "smallest")
    pick = files[{"oldest": ages.index(max(ages)), "newest": ages.index(min(ages)),
                  "largest": sizes.index(max(sizes)), "smallest": sizes.index(min(sizes))}[crit]]
    if w.rng.random() < 0.5:
        op = ("recycle", pick)
        text = w.say(["Delete the {crit} file in {f}.",
                      "Which file in {f} is the {crit}? Send that one to the recycle bin."],
                     ["trash whichever file in {f} is the {crit}", "get rid of the {crit} thing in {f}"],
                     crit=crit, f=P(folder))
    else:
        op = ("move", pick, f"{dest}/{base(pick)}")
        text = w.say(["Move the {crit} file in {f} to {dest}.", "Take the {crit} file out of {f} and put it in {dest}."],
                     ["whichever file in {f} is the {crit}, shift it over to {dest}",
                      "the {crit} item in {f} should go to {dest}"], crit=crit, f=P(folder), dest=dest)
    return [Turn(text, [("search_files", {"query": "*", "folder": P(folder)})], [op])]


def all_except(w):  # issues 004, 014: "everything except ..."
    src = w.folder(n=0)
    dest = w.folder(w.top(src))
    moved = [w.file(src, ext=e) for e in w.rng.sample(["pdf", "xlsx", "jpg", "pptx"], 3)]
    if w.cycle("ext", "name") == "ext":
        ext = w.rng.choice(["zip", "mp4", "png"])
        kept, what = w.file(src, ext=ext), f"the .{ext} file"
    else:
        kept = w.file(src, ext="docx")
        what = base(kept)
    text = w.say(["Move everything in {src} to {dest} except {what}.",
                  "Clear out {src} into {dest}, but leave {what} where it is."],
                 ["shift all of {src} over to {dest}, apart from {what}",
                  "the files inside {src} go to {dest}; {what} stays put"], src=P(src), dest=P(dest), what=what)
    return [Turn(text, [("list_directory", {"path": P(src)})], [("move", f, f"{dest}/{base(f)}") for f in moved])]


def filtered_bulk(w):  # issue 004: a filtered set, not the whole folder
    src = w.folder(n=0)
    dest = w.folder(w.top(src))
    verb = w.rng.choice(["move", "copy"])
    kw = {"src": P(src), "dest": P(dest), "verb": verb, "Verb": verb.title(), "verbed": {"move": "moved", "copy": "copied"}[verb]}
    if w.cycle("ext", "recent") == "ext":
        ext = w.rng.choice(["pdf", "jpg", "xlsx"])
        hits = [w.file(src, ext=ext) for _ in range(3)]
        for e in w.rng.sample([e for e in EXTS if e != ext], 2):
            w.file(src, ext=e)
        look = {"query": "*", "folder": P(src), "extension": ext}
        text = w.say(["{Verb} all the {ext} files from {src} to {dest}.",
                      "Every .{ext} in {src} should be {verbed} to {dest}. Leave the other files alone."],
                     ["{verb} just the {ext}s out of {src} into {dest}",
                      "take each {ext} file that's in {src} and {verb} it to {dest}"], ext=ext, **kw)
    else:
        hits = [w.file(src, days=d) for d in w.rng.sample(range(1, 5), 3)]
        for _ in range(3):
            w.file(src, days=w.rng.randrange(20, 300))
        look = {"query": "*", "folder": P(src), "modified_within_days": 7}
        text = w.say(["{Verb} the files in {src} that were modified in the last 7 days to {dest}.",
                      "Which files in {src} changed during the past week? {Verb} those to {dest}."],
                     ["anything in {src} edited within the last seven days: {verb} it into {dest}",
                      "{verb} whatever was touched in {src} over the last 7 days into {dest}"], **kw)
    return [Turn(text, [("search_files", look)], [(verb, f, f"{dest}/{base(f)}") for f in hits])]


def memory_then_act(w):  # issue 012: a saved fact has to be recalled in a new chat
    stem, other = w.pick("stems"), w.pick("stems")
    folder = f"{w.top()}/{w.pick('subs')}/{stem}_{w.rng.choice(QUALS)}"
    files = [w.file(folder) for _ in range(3)]
    w.memories = [f"My {other} folder is {P(w.folder())}", f"My {stem} folder is {P(folder)}"]
    look, kind = [("recall", {"query": f"{stem} folder"})], w.cycle("zip", "list", "move")
    if kind == "zip":
        return [Turn(w.say(["Zip my {stem} folder and put the zip on the Desktop.",
                            "Make a zip of the {stem} folder I told you about, saved to my Desktop."],
                           ["compress my {stem} folder onto the Desktop",
                            "I need my {stem} folder as a zip file on the Desktop"], stem=stem),
                     look, [("zip", (folder,), "Desktop")])]
    if kind == "list":
        return [Turn(w.say(["What files are in my {stem} folder?",
                            "List what's inside the {stem} folder I told you about."],
                           ["show me the contents of my {stem} folder",
                            "which documents does my {stem} folder hold"], stem=stem),
                     look + [("list_directory", {"path": P(folder)})], facts=[base(f) for f in files])]
    x = w.file(w.top(folder))
    return [Turn(w.say(["Move {x} into my {stem} folder.",
                        "Put {x} with the rest of my {stem} files, in the {stem} folder I told you about."],
                       ["file {x} away in my {stem} folder", "{x} belongs in my {stem} folder, please move it there"],
                       x=P(x), stem=stem), look, [("move", x, f"{folder}/{base(x)}")])]


def two_part(w):  # issue 007: both halves of a request
    if w.cycle("calc_count", "rename_read") == "calc_count":
        folder, n = w.folder(n=0), w.rng.randrange(4, 8)
        for _ in range(n):
            w.file(folder)
        pct, amount = w.rng.choice([12, 15, 18, 28, 35]), w.rng.randrange(1100, 9900)
        text = w.say(["What's {pct}% of {amount:,}, and how many files are in {f}?",
                      "Two things: how many files does {f} hold, and what is {pct}% of {amount:,}?"],
                     ["count the files in {f} for me and also work out {pct} percent of {amount}",
                      "I need {pct} percent of {amount} calculated, plus the number of files sitting in {f}"],
                     pct=pct, amount=amount, f=P(folder))
        return [Turn(text, [("calculate", {"expression": f"{amount} * {pct} / 100"}),
                            ("list_directory", {"path": P(folder)})], facts=[round(amount * pct / 100, 2), n])]
    stem, (q, q2) = w.pick("stems"), w.rng.sample(QUALS, 2)
    code = f"{w.pick('words')}-{w.rng.randrange(100, 999)}"
    path = w.file(w.folder(), stem, q, "txt", text=f"{stem.title()} review\nMeeting room: {code}\nBring a laptop.\n")
    new = f"{stem}_{q2}.txt"
    text = w.say(["Rename {p} to {new} and tell me which meeting room is written in it.",
                  "Which meeting room does {p} mention? Also rename the file to {new}."],
                 ["read me the meeting room from {p}, then change the file's name to {new}",
                  "{p} needs to be called {new} from now on, and I need the meeting room it gives"],
                 p=P(path), new=new)
    return [Turn(text, [("read_file", {"path": P(path)})], [("move", path, f"{path.rsplit('/', 1)[0]}/{new}")],
                 facts=[code])]


def recover_empty(w):  # an empty name search is not the end: the topic is inside the file
    word, top = w.pick("words"), w.top()
    dest = w.top(top)
    path = w.file(w.folder(top), ext=w.rng.choice(["txt", "md"]),
                  text=f"Planning notes for the {word} project.\nBudget review on Monday.\n")
    look = [("search_files", {"query": word, "folder": top}), ("search_file_contents", {"text": word, "folder": top})]
    if w.cycle("move", "name") == "move":
        return [Turn(w.say(["Find my file about the {word} project in {top} and move it to {dest}.",
                            "There's a document in {top} about the {word} project. Move it to {dest}."],
                           ["somewhere under {top} is my write-up on the {word} project; shift it to {dest}",
                            "the {word} project file in {top} should be moved over to {dest}"],
                           word=word, top=top, dest=dest), look, [("move", path, f"{dest}/{base(path)}")])]
    return [Turn(w.say(["Which file in {top} is about the {word} project?",
                        "I have a document on the {word} project somewhere in {top}. What is it called?"],
                       ["tell me the name of my {word} project write-up under {top}",
                        "what's the file in {top} that covers the {word} project"], word=word, top=top),
                 look, facts=[base(path)])]


def ask_then_act(w):  # issue 016: two files fit, so ask; then act on the answer
    stem, (q, q2), ext = w.pick("stems"), w.rng.sample(QUALS, 2), w.rng.choice(["pdf", "xlsx", "pptx"])
    src = w.folder(n=1)
    dest = w.top(src)
    w.file(src, stem, q, ext)
    target = w.file(src, stem, q2, ext)
    kind = w.cycle("move", "recycle", "copy")
    op = ("recycle", target) if kind == "recycle" else (kind, target, f"{dest}/{base(target)}")
    first = {
        "move": w.say(["Move my {stem} file from {src} to {dest}.", "The {stem} file in {src}: move it to {dest}."],
                      ["shift the {stem} document out of {src} into {dest}",
                       "please relocate my {stem} from {src} to {dest}"], stem=stem, src=P(src), dest=dest),
        "recycle": w.say(["Delete my {stem} file from {src}.", "Send the {stem} file in {src} to the recycle bin."],
                         ["trash the {stem} document that's in {src}", "get rid of my {stem} from {src}"],
                         stem=stem, src=P(src)),
        "copy": w.say(["Copy my {stem} file from {src} to {dest}.", "Put a copy of the {stem} file in {src} into {dest}."],
                      ["duplicate the {stem} document in {src} over to {dest}",
                       "I'd like my {stem} from {src} copied into {dest}"], stem=stem, src=P(src), dest=dest)}[kind]
    second = w.say(["The {q} one.", "I meant the {q} one."], ["{q}", "go with the {q} version"], q=q2)
    return [Turn(first, [("search_files", {"query": stem, "folder": P(src)})], ask=True), Turn(second, ops=[op])]


def decline_then_continue(w):  # a "no" at the prompt ends that change only
    a = w.file(w.folder())
    if w.cycle("one_turn", "two_turn") == "one_turn":
        z = w.folder(n=3)
        text = w.say(["Delete {a}, then zip {z} and put the zip on my Desktop.",
                      "First send {a} to the recycle bin. After that, make a zip of {z} on the Desktop."],
                     ["trash {a} and afterwards compress {z} onto the Desktop",
                      "two jobs: remove {a}, and create a Desktop zip of {z}"], a=P(a), z=P(z))
        return [Turn(text, declined=[("recycle", a)], ops=[("zip", (z,), "Desktop")])]
    dest = w.folder(w.top(a))
    return [Turn(w.say(["Delete {a}.", "Send {a} to the recycle bin."], ["trash {a}", "remove {a} for me"], a=P(a)),
                 declined=[("recycle", a)]),
            Turn(w.say(["On second thought, move it to {dest} instead.", "Actually keep it. Just move it into {dest}."],
                       ["changed my mind, put it in {dest} rather than deleting",
                        "no wait, shift it to {dest} instead"], dest=P(dest)),
                 ops=[("move", a, f"{dest}/{base(a)}")])]


def notes_and_reminders(w):  # issues 011, 018: notes are not memories; reminder times come from what was read
    stem = w.pick("stems")
    if w.cycle("file_to_note", "note_to_reminder") == "file_to_note":
        code, title = f"{w.pick('words').upper()}-{w.rng.randrange(1000, 9999)}", f"{stem} gate"
        path = w.file(w.folder(), stem, ext="txt", text=f"{stem.title()} fair\nEntrance gate: {code}\nDoors open at 10.\n")
        text = w.say(["Save a note called '{t}' with the entrance gate from {p}.",
                      "Read {p} and make a note titled '{t}' containing the entrance gate it gives."],
                     ["grab the entrance gate out of {p} and store it in a note named '{t}'",
                      "I want a note '{t}' holding the entrance gate that's in {p}"], t=title, p=P(path))
        return [Turn(text, [("read_file", {"path": P(path)})], notes=[(title, code)])]
    when = f"{w.today + timedelta(days=w.rng.randrange(2, 10))} {w.rng.choice(['09:20', '10:30', '14:15', '16:45'])}"
    w.notes = [(f"{w.pick('stems')} ideas", "Ask about a discount next month."),
               (f"{stem} appointment", f"The {stem} appointment is on {when[:10]} at {when[11:]}. Bring ID.")]
    text = w.say(["Look up the {stem} appointment in my notes and set a reminder for the time it says.",
                  "My notes have the {stem} appointment. Remind me about it at the date and time written there."],
                 ["check my notes for when the {stem} appointment is, then create a reminder for exactly then",
                  "one of my notes mentions the {stem} appointment, schedule an alert for when it happens"], stem=stem)
    return [Turn(text, [("search_notes", {"query": f"{stem} appointment"})], reminders=[when])]


def count_and_size(w):  # issues 002, 008: count from a search, sizes added with their units
    folder, ext = w.folder(n=0), w.rng.choice(["pdf", "jpg", "xlsx"])
    kbs = w.rng.sample(range(40, 250), w.rng.choice([3, 4]))
    for k in kbs:
        w.file(folder, ext=ext, kb=k)
    for e in w.rng.sample([e for e in EXTS if e != ext], 2):
        w.file(folder, ext=e)
    total = sum(kbs)
    text = w.say(["How many {ext} files are in {f}, and how big are they in total?",
                  "Count the {ext} files in {f} and tell me their combined size."],
                 ["what's the number of {ext}s inside {f} and how much space do they take together",
                  "tally up the {ext} files under {f}: how many are there and what do they weigh altogether"], ext=ext, f=P(folder))
    return [Turn(text, [("search_files", {"query": "*", "folder": P(folder), "extension": ext}),
                        ("calculate", {"expression": " + ".join(f"{k} KB" for k in kbs)})],
                 facts=[len(kbs), (total, round(total / 1024, 2), round(total / 1024, 1))])]


# --- held-out families (test pool only; no training rollout uses them) ---

def compare_files(w):
    stem, (q, q2) = w.pick("stems"), w.rng.sample(QUALS, 2)
    folder, (x, y) = w.folder(), [v + w.rng.choice([0, 0.5]) for v in w.rng.sample(range(900, 9000), 2)]
    a, b = [w.file(folder, stem, k, "txt", text=f"{stem.title()} {k}\nTotal: {v:,.2f}\nPaid by transfer.\n")
            for k, v in ((q, x), (q2, y))]
    if w.cycle("difference", "sum") == "difference":
        text, fact, expr = w.say(["What's the difference between the totals in {a} and {b}?",
                                  "Read {a} and {b}. How much larger is the bigger total than the smaller one?"],
                                 a=P(a), b=P(b)), abs(x - y), f"abs({x} - {y})"
    else:
        text, fact, expr = w.say(["Add the total in {a} to the total in {b}. What do you get?",
                                  "What do the totals in {a} and {b} come to combined?"], a=P(a), b=P(b)), x + y, f"{x} + {y}"
    return [Turn(text, [("read_file", {"path": P(a)}), ("read_file", {"path": P(b)}),
                        ("calculate", {"expression": expr})], facts=[fact])]


def act_on_list(w):
    stem, src = w.pick("stems"), w.folder(n=0)
    files = [w.file(src) for _ in range(5)]
    dest = w.folder(w.top(src))
    listed = w.rng.sample(files, 3)
    lst = w.file(w.top(), name=f"{stem}_list.txt", text="Files to archive:\n" + "".join(f"- {base(f)}\n" for f in listed))
    text = w.say(["Read {l} and move the files it lists from {src} to {dest}.",
                  "{l} names some files in {src}. Move exactly those to {dest}."], l=P(lst), src=P(src), dest=P(dest))
    return [Turn(text, [("read_file", {"path": P(lst)})], [("move", f, f"{dest}/{base(f)}") for f in listed])]


def deadline_reminder(w):
    stem, due = w.pick("stems"), w.today + timedelta(days=w.rng.randrange(5, 21))
    path = w.file(w.folder(), stem, ext="txt",
                  text=f"{stem.title()} call for submissions\nSubmission deadline: {due}\nSend it to the committee.\n")
    if w.cycle("day_before", "same_day") == "day_before":
        text, when = w.say(["Remind me at 9am on the day before the deadline given in {p}.",
                            "{p} has a submission deadline. Set a reminder for 9:00 the day before it."],
                           p=P(path)), f"{due - timedelta(days=1)} 09:00"
    else:
        text, when = w.say(["Set a reminder for 8am on the deadline date written in {p}.",
                            "Find the submission deadline in {p} and remind me that morning at 8:00."],
                           p=P(path)), f"{due} 08:00"
    return [Turn(text, [("read_file", {"path": P(path)})], reminders=[when])]


def conditional_act(w):
    folder, n = w.folder(n=0), w.cycle(5, 2, 4, 1, 6, 2)
    for _ in range(n):
        w.file(folder, ext="pdf")
    for e in ("xlsx", "jpg"):
        w.file(folder, ext=e)
    text = w.say(["If {f} has more than 3 pdf files, zip the whole folder to my Desktop. Otherwise just tell me how "
                  "many pdfs it has.",
                  "Count the pdfs in {f}. More than 3 means zip the folder onto the Desktop; 3 or fewer means only "
                  "tell me the count."], f=P(folder))
    look = [("search_files", {"query": "*", "folder": P(folder), "extension": "pdf"})]
    return [Turn(text, look, [("zip", (folder,), "Desktop")]) if n > 3 else Turn(text, look, facts=[n])]


def bulk_rename(w):
    folder, pre = w.folder(n=0), w.pick("words")
    files = [w.file(folder) for _ in range(3)]
    text = w.say(["Add the prefix '{pre}_' to the name of every file in {f}.",
                  "Rename each file in {f} so that its name starts with '{pre}_'."], pre=pre, f=P(folder))
    return [Turn(text, [("list_directory", {"path": P(folder)})],
                 [("move", f, f"{folder}/{pre}_{base(f)}") for f in files])]


SHARED = [find_then_act, read_then_compute, pick_extreme, all_except, filtered_bulk, memory_then_act, two_part,
          recover_empty, ask_then_act, decline_then_continue, notes_and_reminders, count_and_size]
HELD_OUT = [compare_files, act_on_list, deadline_reminder, conditional_act, bulk_rename]


def build(fn, pool: str, seed: int) -> HardTask:
    w = World(pool, fn.__name__, seed)
    steps = fn(w)
    spare = [w.file(t) for t in FOLDERS for _ in range(2)][0]  # clutter in the main folders
    return HardTask(f"{fn.__name__}-{seed:04d}", [], None, files=w.files, base=False, today=w.today.isoformat(),
                    tags=["held_out" if fn in HELD_OUT else "shared", fn.__name__], mtimes=w.mtimes,
                    memories=w.memories, notes=w.notes, family=fn.__name__, pool=pool, seed=seed, steps=steps,
                    spare=spare)


def tasks(pool: str = "test", per_family: int | None = None) -> list[HardTask]:
    """test: 7 per shared family and 8 per held-out family (124). train: shared families only, other seeds."""
    if pool == "train":
        return [build(fn, pool, TRAIN_SEED0 + i) for fn in SHARED for i in range(per_family or 25)]
    return [build(fn, pool, i) for fns, n in ((SHARED, 7), (HELD_OUT, 8)) for fn in fns for i in range(per_family or n)]


def frozen_text() -> str:
    return "".join(json.dumps(t.spec(), ensure_ascii=False, sort_keys=True) + "\n" for t in tasks("test"))


if __name__ == "__main__":
    if "--write" in sys.argv:
        FROZEN.write_text(frozen_text(), encoding="utf-8", newline="\n")
        print(f"{FROZEN.name}: {len(tasks('test'))} tasks, sha256 {hashlib.sha256(FROZEN.read_bytes()).hexdigest()}")
    else:
        print(__doc__)
