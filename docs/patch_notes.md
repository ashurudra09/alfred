# Patch notes

Model versions of Alfred (Qwen3.5-2B + LoRA). Every number is from a report in `eval/reports/`; details in
[decisions.md](decisions.md).

## v3 (planned, not trained)
Data fixes collected from testing, applied together before the next training run. Full write-ups, affected example
ids and regression items: [data/to_fix.md](../data/to_fix.md).

| Issue | Problem in v2 | Planned fix |
|---|---|---|
| 001 | Asked which folder is biggest, then proposed moving it to the Recycle Bin unasked (19 bad training examples) | validator rule "writes only when the user asked", drop the 19, counter-examples, system-prompt rule |
| 002 | Added sizes without converting units (230 MB counted as 230 GB) | `disk_usage` → `calculate` chains that keep the units (`calculate` now takes them); realistic size formats in the generator |
| 003 | "make a folder … name it temp" proposed `organize_folder` on all of Documents (no tool makes empty folders) | `cannot` examples for file actions with no tool; option: a `create_folder` tool |
| 004 | "move all the pdfs" moved the whole Downloads folder; "except"/"every" requests act on the whole folder | search-then-act-per-file examples; "except" → list or `cannot` |
| 005 | Date-only searches put junk in `query` and report "none" | `query="*"` date searches |
| 006 | Date math wrong ("days until christmas" = 341) | day counts built from today's date |
| 007 | "X, and what % of Y" answered only X | `top_processes`/`system_info` → `calculate` chains |
| 008 | "Which folder has more files" compared free space | count with `list_directory` |
| 009 | Invented `extension`/date filters, assumed a folder | filters only when asked; search first |
| 010 | Moved and read a file as asked, then trashed it unasked | as 001; chains that end with an answer |
| 011 | Reminders on the wrong weekday; "every monday" set once on a Sunday (12/28 training weekdays wrong) | validator weekday check; weekday times; "N before X"; "won't repeat" |
| 012 | Saved memories not recalled in a new chat | `recall` first for "my boss/my project folder" questions |
| 013 | Tool arguments copied from the request (note text = the request), conditions not checked | lookup → write chains; check-then-act |
| 014 | Can't pick from results: invented "oldest" file names, size threshold, "leave out", "zip those" | list/search then pick; `extra_files` |
| 015 | Answers claim more than the tool result says | answers that restate the result |
| 016 | "move it" with nothing to refer to → invented a file; "clean up my computer" → organized Downloads | `ask` examples for missing referents and whole-computer requests |
| 017 | "add up my expenses in expenses.txt" → `calculate` on invented numbers, file never read (14 training examples name a file but carry the numbers) | `read_file` → `calculate` chains; fix the 14 |
| 018 | Saved a note, later "where did I say…" → `recall` only → "can't find it" (29/29 "where did I" examples use `recall`) | `search_notes` for note lookups; `recall` miss → `search_notes` |

**Code fixes found in the same testing (done 2026-10-24; they need no retraining):**
- `move_file`, `rename_file` and their confirmation previews refuse a main folder as the source. In a probe,
  "move all the pdfs" had moved the whole Downloads folder. `move_to_recycle_bin` now refuses it before asking,
  not after.
- Tool calls per request raised from 3 to 8 (FR4); 3 made acting on more than 2 files impossible.
- `set_reminder` reads compound durations ("in 3 hours 45 minutes", "in 1 hour and 30 min", "in 2h30m").
- `list_directory` and file search skip Windows Hidden/System items (`desktop.ini`, the `My Music` junctions),
  matching Explorer. `disk_usage` skips links, which counted a folder twice, but keeps hidden files because they take
  real space (e.g. `pagefile.sys`).
- The agent doesn't rerun a call that already failed or was declined in the same request (it returns "Not run"
  instead). A probe looped on one failing `move_to_recycle_bin` until the call limit.
- "Not found … Similar names" marks folders with a trailing `\`; a probe moved a whole `resume` folder after the hint
  listed it like a file.

**Contract changes (contracts v1.1; the v3 data should use them):**
- `zip_folder` takes `extra_files`, so several files go into one .zip ("zip notes.txt and budget.xlsx").
- `set_reminder` reads weekdays ("friday 17:00", "next monday 9am"), so the model doesn't do weekday maths.
- `calculate` accepts sizes with units (B, KB, MB, GB, TB, 1024-based like `disk_usage`): `2.4 GB + 230 MB` →
  `2.62 GB (…bytes)`; size ÷ size is a plain number (`2.5 GB / MB` = 2560); a size plus a bare number is an error.
- Scorer: new `time` argument rule (same reminder time, any accepted format).

Also in the same run: the completed data top-up (finished 2026-10-24; the set grew from 8,963 to 10,037 train and
471 to 529 val examples; every tool except `list_reminders` (199) now has ≥ 200).
**Gate for v3:** the regression set passes, and in-domain, safety, e2e, When2Call and BFCL don't regress.
v2 on the regression set: 7/46.

## v2 (shipped, 2026-10-23)
- **Fix: clarifying questions.** v1 almost stopped asking ("move the file" → it recycled an invented file; ask recall
  6.7–33%). The chat template drops the empty `<think></think>` block from earlier turns, so every clarify example was
  trained in a form the model never sees at inference. v2 adds each clarify example cut right after the question
  (538 extra), so the question is trained as the final turn.
- Same training settings as v1 (LoRA r=16, 620 steps, one Kaggle T4, 3.9 h); train 8,963 / val 471 examples.
- **Results:** in-domain 95.3% (Q4) / 95.7% (Q8), ask recall 93% / 100%, safety 95.8%. Later: When2Call 65.7%,
  BFCL subset 77.2%, end to end 47/50 with 20/20 injection files resisted.
- Scorer v1.1 (an omitted argument that equals the tool's default counts as right) rescored every report.

## v1 (2026-10-23, superseded)
- First SFT: in-domain 91.7% (Q8) / 93.5% (Q4) vs 79.1% for the base model; safety 97.9%.
- Regression found: ask recall fell from 60% (base) to 6.7% (Q8), fixed in v2.
