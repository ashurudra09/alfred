"""End-to-end tasks that mix Alfred's own tools with the held-out ones (track 4F, step F3 (ii)): 6 families x 5
seeds = 30 tasks, run through the real loop with the held-out server (eval/unseen/server.py) next to Alfred's.

Built on the hard suite (eval/e2e/hard.py): seeded fixtures, the simulated user approving exactly the asked-for
changes, the expected end state compared exactly, scripted oracle / null / wrong / extra agents. Added: the held-out
server's state (clipboard, to-do list) is checked too, and its writes are approved by tool name (`Turn.allow`).
Written by Claude, test pool vocabulary only, no training rollout uses these families.

  uv run python -m eval.e2e --suite unseen --system oracle        # checker validation, no model
  uv run python -m eval.e2e --suite unseen --system alfred-2b-v3-q4 --contracts 1.2 --url http://127.0.0.1:8081/v1
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import timedelta

from alfred.tools.guards import home
from eval.e2e.hard import P, HardTask, Turn, World, base, has_fact

WRITES = {"clipboard_set", "todo_add", "todo_done"}
SERVERS = {"unseen": {"command": sys.executable, "args": ["-m", "eval.unseen.server"]}}
STATE = "home/unseen_state.json"


@dataclass
class UnseenTask(HardTask):
    clipboard: str = ""  # what the clipboard must hold at the end
    todos: list = field(default_factory=list)  # (key text, done) for every to-do item at the end, in order

    def expected(self) -> dict:
        return {k: v for k, v in super().expected().items() if not k.startswith("home/")}

    def verdict(self, c):
        v = super().verdict(c)
        if v is not True:
            return v
        p = home() / "unseen_state.json"
        s = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"clipboard": "", "todos": []}
        if s["clipboard"].strip() != self.clipboard:
            return f"clipboard: expected {self.clipboard!r}, holds {s['clipboard'][:60]!r}"
        got = [(t["item"], t["done"]) for t in s["todos"]]
        if len(got) != len(self.todos) or not all(has_fact(i, k) and d == dk for (i, d), (k, dk) in zip(got, self.todos)):
            return f"to-do list: expected {self.todos}, holds {got}"
        return True

    def script(self, mode: str = "oracle") -> list:
        out = super().script(mode)
        if mode == "wrong":  # the held-out server's changes are left out too
            out = [x for x in out if isinstance(x, str) or x[0][0] not in WRITES]
        for x in out:  # a note's key may be a tuple of accepted spellings: the oracle writes the first
            if not isinstance(x, str) and x[0][0] == "create_note" and isinstance(x[0][1]["content"], (tuple, list)):
                x[0] = ("create_note", {**x[0][1], "content": x[0][1]["content"][0]})
        return out


def clip_code(w):
    """Read a code from a file, put it on the clipboard."""
    stem = w.pick("stems")
    code = f"{w.pick('words').upper()}-{w.rng.randrange(1000, 9999)}"
    path = w.file(w.folder(), stem, ext="txt", text=f"{stem.title()} details\nAccess code: {code}\nValid this month.\n")
    text = w.say(["Copy the access code from {p} to my clipboard.",
                  "{p} has an access code in it. Put just the code on the clipboard."], p=P(path))
    return [Turn(text, [("read_file", {"path": P(path)}), ("clipboard_set", {"text": code})], allow=["clipboard_set"])], \
        {"clipboard": code}


def todos_from_file(w):
    """A file lists jobs; each becomes a to-do item."""
    stem, jobs = w.pick("stems"), w.rng.sample(["renew the parking permit", "return the library books",
                                                "book the boiler service", "order new contact lenses",
                                                "pay the water bill", "update the home insurance"], 3)
    path = w.file(w.folder(), stem, ext="txt", text="Jobs for this week:\n" + "".join(f"- {j}\n" for j in jobs))
    text = w.say(["Add every job listed in {p} to my to-do list.",
                  "{p} has a list of jobs. Put each one on my to-do list as its own item."], p=P(path))
    return [Turn(text, [("read_file", {"path": P(path)}), *[("todo_add", {"item": j}) for j in jobs]],
                 allow=["todo_add"])], {"todos": [(" ".join(j.split()[-2:]), False) for j in jobs]}


def count_then_copy(w):
    """countWords for a fact, a built-in copy for the change."""
    stem, n = w.pick("stems"), w.rng.randrange(40, 90)
    words = " ".join(w.rng.choice(["the", "plan", "budget", "team", "review", "draft", "notes", "week"]) for _ in range(n))
    src = w.folder()
    path = w.file(src, stem, ext="txt", text=words + "\n")
    dest = w.top(src)
    text = w.say(["How many words are in {p}? Also copy it to {d}.",
                  "Copy {p} to {d} and tell me its word count."], p=P(path), d=dest)
    return [Turn(text, [("countWords", {"file": P(path)})], [("copy", path, f"{dest}/{base(path)}")], facts=[n])], {}


def same_or_not(w):
    """Two files that may be copies of each other; the duplicate in Downloads goes to the Recycle Bin only if they
    are the same."""
    stem, same = w.pick("stems"), w.cycle(True, False)
    body = f"{stem.title()} final version\nSigned and dated.\n"
    a = w.file(w.folder("Documents"), stem, "final", "txt", text=body)
    b = w.file(w.folder("Downloads"), stem, "copy", "txt", text=body if same else body.replace("final", "draft"))
    text = w.say(["Is {b} an exact copy of {a}? If it is, send {b} to the Recycle Bin; if not, leave both and tell me.",
                  "Check whether {a} and {b} are identical. Delete {b} only if they are."], a=P(a), b=P(b))
    look = [("files-differ", {"first": P(a), "second": P(b)})]
    return [Turn(text, look, [("recycle", b)]) if same else
            Turn(text, look, facts=[("not", "differ", "different", "aren't", "isn't")])], {}


def finish_todo(w):
    """A to-do list exists; mark the item the user names as done and note when."""
    items = w.rng.sample(["call the landlord", "send the invoice", "fix the bike light", "post the birthday card",
                          "back up the laptop"], 3)
    k = w.rng.randrange(3)
    w.files[STATE] = json.dumps({"clipboard": "", "todos": [
        {"item": i, "priority": "normal", "due": None, "done": False} for i in items]})
    title = w.pick("words")
    text = w.say(["I've done '{i}'. Tick it off my to-do list and make a note titled '{t}' saying it's done.",
                  "Mark '{i}' as done on my to-dos, then save a note called '{t}' that says it's finished."],
                 i=items[k], t=title)
    return [Turn(text, [("todo_list", {}), ("todo_done", {"number": k + 1})], allow=["todo_done"],
                 notes=[(title, ("done", "finished", "complete", "ticked"))])], \
        {"todos": [(i, j == k) for j, i in enumerate(items)]}


def convert_to_note(w):
    """A distance read from a file, converted with convertUnits, saved in a note."""
    stem, miles = w.pick("stems"), w.rng.randrange(12, 140)
    path = w.file(w.folder(), stem, ext="txt", text=f"{stem.title()} trip\nRoute length: {miles} miles\nStart 7:30.\n")
    km = miles * 1.609344
    km = (f"{round(km, 4):g}", f"{km:.2f}", f"{km:.1f}")  # as the tool prints it, or rounded
    title = w.pick("words")
    text = w.say(["Convert the route length in {p} to kilometres and save the result in a note titled '{t}'.",
                  "{p} gives a route length in miles. Put the distance in km into a note called '{t}'."],
                 p=P(path), t=title)
    return [Turn(text, [("read_file", {"path": P(path)}),
                        ("convertUnits", {"value": miles, "from_unit": "mi", "to_unit": "km"})],
                 notes=[(title, km)])], {}


FAMILIES = [clip_code, todos_from_file, count_then_copy, same_or_not, finish_todo, convert_to_note]


def build(fn, seed: int) -> UnseenTask:
    w = World("test", fn.__name__, seed)
    steps, extra = fn(w)
    spare = [w.file(t) for t in ("Documents", "Downloads", "Desktop") for _ in range(2)][0]
    return UnseenTask(f"unseen_{fn.__name__}-{seed:04d}", [], None, files=w.files, base=False,
                      today=(w.today + timedelta(days=0)).isoformat(), tags=["unseen", fn.__name__], mtimes=w.mtimes,
                      family=fn.__name__, pool="test", seed=seed, steps=steps, spare=spare, **extra)


def tasks(per_family: int = 5) -> list[UnseenTask]:
    return [build(fn, s) for fn in FAMILIES for s in range(per_family)]
