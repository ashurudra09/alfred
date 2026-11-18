"""List-iteration family (run A finding 2, docs/v4/run_a_findings.md): one lookup, then the same write tool once
per item (one call per turn, as the agent runs them), then a short report. Only 1.5% of Alfred's examples repeated
a write tool, and both v3 and run A answered doable bulk requests with the `cannot` template ("I don't have a tool
for that"). Deterministic templates, no teacher.

Variants: a write that fails or that the user declines at the prompt (the rest still run, the report says which);
a follow-up the tools really can't do (the contrast: doable bulk work -> act, impossible -> cannot).
Kept apart from the held-out hard families: no whole-folder renames (bulk_rename) and no "read a list file, then
act" (act_on_list); names come from the hard suite's train vocabulary only.

  uv run python -m data.gen.iterate        # -> data/out/v4/iterate.jsonl, checked by data.validate
"""

import random
import sys
from datetime import date, timedelta

from alfred.contracts.export import openai_tools
from alfred.contracts.prompt import render_system_prompt
from alfred.contracts.schemas import Example, Message, ToolCall
from data.gen.formats import DECLINED
from data.gen.prompts import EXTRA, USERS
from eval.e2e.hard import VOCAB

V = VOCAB["train"]
OPS = {"recycle": ["delete", "trash", "get rid of", "bin", "throw out", "remove"],
       "move": ["move", "shift", "put", "transfer"],
       "copy": ["copy", "back up", "duplicate", "make copies of"]}
EXT = {"recycle": ["tmp", "log", "bak", "crdownload", "part"], "move": ["pdf", "docx", "xlsx", "jpg", "png", "pptx", "csv"],
       "copy": ["pdf", "docx", "xlsx", "jpg", "png", "pptx", "csv"]}
SELECT = {"ext": ["all the {ext} files in {src}", "every .{ext} in {src}", "each {ext} file in {src}",
                  "the .{ext} files sitting in {src}", "whatever {ext}s are in {src}"],
          "word": ["every file in {src} with '{w}' in its name", "all the {w} files in {src}",
                   "the files in {src} whose names mention {w}", "each {w} file from {src}"],
          "recent": ["the files in {src} changed in the last {d} days", "everything in {src} from the past {d} days",
                     "each file in {src} modified within {d} days"],
          "big": ["every file in {src} over {mb} MB", "the files in {src} bigger than {mb} MB",
                  "anything in {src} larger than {mb} MB"],
          "all": ["every file in {src}", "all the files in {src} (not the subfolders)", "each file inside {src}"]}
WRAP = ["{V} {S}{D}.", "Please {v} {S}{D}.", "Can you {v} {S}{D}?", "{v} {S}{D} pls", "Hey, {v} {S}{D}. Thanks!",
        "I need you to {v} {S}{D}.", "Could you {v} {S}{D}, one by one is fine?", "{v} {S}{D}", "Go ahead and {v} {S}{D}.",
        "Would you {v} {S}{D} for me?"]
DONE = {"recycle": "moved to the Recycle Bin", "move": "moved to {dest}", "copy": "copied to {dest}"}
CANNOT = [("now email them to my manager", "I can't send email: I work offline and have no email tool."),
          ("also upload them to Google Drive", "I can't upload to Google Drive: I have no internet or cloud tool."),
          ("print them too", "I can't print: I don't have a printer tool. I can open one so you print it from its app."),
          ("and change the files' created date to last Monday",
           "I can't change file dates: I don't have a tool for that."),
          ("then shrink the images to half size", "I can't resize images: I don't have an image-editing tool."),
          ("send them to my phone", "I can't reach other devices: I only work on this laptop."),
          ("and set them to read-only", "I can't change file permissions: I don't have a tool for that.")]


def size(rng) -> tuple[str, float]:
    mb = rng.choice([rng.uniform(0.01, 0.9)] * 3 + [rng.uniform(1, 25)] * 2 + [rng.uniform(25, 400)])
    return (f"{mb * 1024:.0f} KB" if mb < 1 else f"{mb:.1f} MB"), mb


def name_list(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def example(k: int, op: str, sel: str, rng: random.Random) -> Example:
    u = rng.choice(USERS)
    folders = {n: f"C:\\Users\\{u}\\{n}" for n in ("Documents", "Downloads", "Desktop", "Pictures")}
    for name, path in rng.sample(EXTRA, rng.randint(0, 2)):
        folders[name] = path.format(u=u)
    day = date(2026, 1, 1) + timedelta(days=rng.randrange(365))
    names = list(folders)
    top = rng.choice(names)
    src = top + ("\\" + rng.choice(V["subs"]) if rng.random() < 0.6 else "")
    dest = rng.choice([x for x in names if x != top]) + ("\\" + rng.choice(V["subs"]) if rng.random() < 0.5 else "")
    n = rng.randint(3, 6)
    ext, w, d, mb = rng.choice(EXT[op]), rng.choice(V["stems"]), rng.choice([3, 5, 7, 10, 14, 30]), rng.choice([5, 10, 50, 100])

    def fname(e=None, stem=None):
        q = rng.choice(["", "_" + rng.choice(["2025", "2026", "q1", "q3", "v2", "old", "final", "draft", "copy"])])
        return f"{stem or rng.choice(V['stems'])}{q}{rng.randint(1, 99) if rng.random() < 0.3 else ''}.{e or rng.choice(EXT[op])}"

    hits = set()
    while len(hits) < n:
        hits.add(fname(ext if sel == "ext" else None, w if sel == "word" else None))
    hits = sorted(hits, key=lambda _: rng.random())
    when = sorted((day - timedelta(days=rng.randrange(0, d if sel == "recent" else 300)) for _ in hits), reverse=True)
    if sel in ("ext", "word", "recent"):
        args = {"query": w if sel == "word" else "*", "folder": src}
        args |= {"extension": ext} if sel == "ext" else {"modified_within_days": d} if sel == "recent" else {}
        look = ToolCall(name="search_files", arguments=args)
        res = f"{n} files:\n" + "\n".join(f"{src}\\{h} ({size(rng)[0]}, modified {t})" for h, t in zip(hits, when))
    else:  # a listing (folder first, then names A-Z, as the tool prints it): only some files fit 'big'
        fit = n if sel == "all" else rng.randint(2, n - 1)
        mbs = {h: size(rng)[1] if sel == "all" else rng.uniform(mb * 1.2, mb * 6) if i < fit else
               rng.uniform(0.02, mb * 0.8) for i, h in enumerate(hits)}
        hits = sorted(hits, key=str.casefold)
        look = ToolCall(name="list_directory", arguments={"path": src})
        res = f"{src} ({n + 1} items):\n{src}\\{rng.choice(V['subs'])}\\ (folder)\n" + "\n".join(
            f"{src}\\{h} ({mbs[h] * 1024:.0f} KB)" if mbs[h] < 1 else f"{src}\\{h} ({mbs[h]:.1f} MB)" for h in hits)
        hits = [h for h in hits if sel == "all" or mbs[h] > mb]
    verb = rng.choice(OPS[op])
    text = rng.choice(WRAP).format(V=verb[0].upper() + verb[1:], v=verb, S=rng.choice(SELECT[sel]).format(
        ext=ext, src=src, w=w, d=d, mb=mb), D="" if op == "recycle" else rng.choice([" to ", " into "]) + dest)
    msgs = [Message(role="system", content=render_system_prompt(folders, day)), Message(role="user", content=text),
            Message(role="assistant", tool_calls=[look]), Message(role="tool", name=look.name, content=res)]
    bad = rng.randrange(len(hits)) if len(hits) > 2 and rng.random() < 0.3 else None
    declined = op == "recycle" or rng.random() < 0.5  # a recycle can't collide, so its failure is a "no"
    done, missed = [], None
    for i, h in enumerate(hits):
        p = f"{src}\\{h}"
        call = {"recycle": ToolCall(name="move_to_recycle_bin", arguments={"path": p}),
                "move": ToolCall(name="move_file", arguments={"source": p, "destination": dest}),
                "copy": ToolCall(name="copy_file", arguments={"source": p, "destination": dest})}[op]
        out = {"recycle": f"Moved {p} to the Recycle Bin. Undo: /undo", "move": f"Moved {p} to {dest}\\{h}. Undo: /undo",
               "copy": f"Copied {p} to {dest}\\{h}. Undo: /undo"}[op]
        if i == bad:
            out = DECLINED if declined else f"Refused: {dest}\\{h} already exists, and Alfred never overwrites files."
            missed = h
        else:
            done.append(h)
        msgs += [Message(role="assistant", tool_calls=[call]), Message(role="tool", name=call.name, content=out)]
    what = DONE[op].format(dest=dest)
    them = what.replace("moved to", "moved them to").replace("copied to", "copied them to")
    report = rng.choice([f"Done: {len(done)} files {what}: {name_list(done)}.",
                         f"{len(done)} files {what}: {name_list(done)}.",
                         f"All set. I {them} ({len(done)} files): {name_list(done)}."])
    if missed:
        report += (f" I left {missed} alone because you said no to it." if declined else
                   f" {missed} wasn't {op}d: {dest} already has a file with that name.").replace("copyd", "copied")
    if sel in ("big", "all"):
        report += " The subfolder" + (" and the smaller files were" if sel == "big" else " was") + " left as is."
    msgs.append(Message(role="assistant", content=report))
    if rng.random() < 0.15:
        ask, reply = rng.choice(CANNOT)
        msgs += [Message(role="user", content=ask), Message(role="assistant", content=reply)]
    return Example(id=f"iterate-{op}-{sel}-{k:03d}", source="iterate", category="multi_step", messages=msgs,
                   tools=openai_tools())


def build(per: int = 32, seed: int = 1118) -> list[Example]:
    rng = random.Random(seed)
    return [example(k, op, sel, rng) for op in OPS for sel in SELECT for k in range(per)]


def main():
    from data.mix import OUT
    from data.validate import check
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    exs, bad = build(), 0
    with (OUT / "v4" / "iterate.jsonl").open("w", encoding="utf-8") as f:
        for e in exs:
            core = e.model_copy(update={"messages": e.messages[:-2]}) if e.messages[-2].role == "user" else e
            if errs := check(core):  # the validator reads the last reply; a contrast follow-up is a templated cannot
                bad += 1
                print(e.id, errs)
                continue
            f.write(e.model_dump_json() + "\n")
    print(f"{len(exs) - bad} written, {bad} failed the validator")


if __name__ == "__main__":
    main()
