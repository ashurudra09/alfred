# Patch notes

Model versions of Alfred (Qwen3.5-2B + LoRA), newest first. Every number is from a report in `eval/reports/`; details in
[decisions.md](decisions.md).

## v4 (shipped, 2026-11-21: run C, Q8_0)
Plan and every step: [docs/v4/PLAN.md](v4/PLAN.md), [docs/v4/STATUS.md](v4/STATUS.md). Decision:
[decisions.md](decisions.md) 2026-11-21.
- **What changed:** 26 tools (new `search_by_meaning`: embedding search over file contents, contracts 1.3); tool
  results print paths relative to their known folder; on-policy training data (the student's own runs through the
  real tools, failing turns rewritten by a teacher, kept only when the check passes on the final files); a
  list-iteration family (one lookup, then one write per file); tool and argument names masked in a third of the
  general examples; English only. Training: run A (fresh LoRA, 1,340 steps), then run C = run A's adapter plus one
  epoch on mix C (1,398 steps, lr 1e-4).
- **Results (Q8_0, vs v3 Q8_0 on its own tool list, same commit, t=0):** hard multi-step suite **104/124 vs
  76/124** (p = 2e-6); 50-task suite **50/50** vs 49/50; in-domain 246 vs 247 of 249; injection suite 0/209 attacks
  succeed for both, user task under attack 209/209 vs 203/209; 0 unconfirmed writes, overwrites or permanent
  deletes everywhere. Sampled 5 times at t=0.7, every trial of a task passes for 62.1% of tasks (pass^5; v3 Q4 34.7%). All tables: [RESULTS.md](../RESULTS.md).
- **Fixed since v3 (hard-suite families, v3 -> v4):** recover after an empty result 0/7 -> 7/7, recall a memory
  then act 1/7 -> 7/7, find then act 4/7 -> 7/7, decline then continue 4/7 -> 7/7, the train-family tasks 55/84 ->
  79/84.
- **Known failures (all 23 hard-suite misses at t=0, read one by one: 20 of the 124 shared tasks and 3 of the 25 semantic-search tasks):**

| Family | Misses | What goes wrong |
|---|---|---|
| act_on_list (held out) | 6/8 | Reads the list file, then moves the list file itself instead of the files it names (4), or moves the right files to the wrong folder (2) |
| bulk_rename (held out) | 3/8 | Renames files outside the asked set, or keeps the old name pattern |
| conditional_act | 3/8 | Checks the condition, then stops before the zip (2), or zips when the condition is false (1) |
| topic_then_read | 3/5 | Finds the right note or file by topic but answers without reading it (the number or word asked for is missing) |
| compare_files | 2/8 | Reads both files, then the answer lacks the computed difference |
| pick_extreme | 2/7 | Acts on the right file, but the answer does not name it |
| ask_then_act | 2/7 | After the user's answer, acts on one file more than asked |
| all_except | 1/7 | Moves the right files to the wrong folder |
| deadline_reminder | 1/8 | Reads the deadline, then sets no reminder |

Two of these families (act_on_list, bulk_rename) are held out of training on purpose, so they measure transfer.
- **Regressed vs v3: calling a tool when none fits.** When2Call tool hallucination 6.2% vs 3.1% (16 vs 8 of 258,
  p = 0.008) and BFCL irrelevance 75.0% vs 90.4% (41 vs 4 items, p = 9e-9), though When2Call accuracy rose to
  71.5% (v3 69.0%). Likely from the act-heavy on-policy and iteration data; the fix is more no-tool and
  irrelevant-tool examples in the next mix.
- **Not done for v4:** the masking ablation (run B), a Q4_K_M build.

## v3 (trained 2026-10-25/26; superseded by v4)
The planned fixes below went into v3's data; v3 reached 98.6% in-domain (276 items) and 49/50 end to end ([decisions.md](decisions.md)).

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
| 011 | Reminders on the wrong weekday; "every monday" set once on a Sunday (19 training reminders on the wrong day) | validator weekday check; weekday times; "N before X"; "won't repeat" |
| 012 | Saved memories not recalled in a new chat | `recall` first for "my boss/my project folder" questions |
| 013 | Tool arguments copied from the request (note text = the request), conditions not checked | lookup → write chains; check-then-act |
| 014 | Can't pick from results: invented "oldest" file names, size threshold, "leave out", "zip those" | list/search then pick; `extra_files` |
| 015 | Answers claim more than the tool result says | answers that restate the result |
| 016 | "move it" with nothing to refer to → invented a file; "clean up my computer" → organized Downloads | `ask` examples for missing referents and whole-computer requests |
| 017 | "add up my expenses in expenses.txt" → `calculate` on invented numbers, file never read (23 training calculations name a file but carry the numbers; 22 `recall` → `calculate` use made-up numbers) | `read_file` → `calculate` chains; fix the 23, drop the 22 |
| 018 | Saved a note, later "where did I say…" → `recall` only → "can't find it" ("where did I…" examples split 46 `recall` / 33 `search_notes`; 0 recall misses) | `search_notes` for note lookups; `recall` miss → `search_notes` |

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

**Contracts 1.2 (decided 2026-10-25; v3 trains on these, see `data/v3_change_plan.md`):**
- `search_files`: `folder` is optional (none = every known folder, one shared scan budget, results pooled newest
  first); `query="*"` matches any name. The v3 data merges its one-call-per-folder searches into one folder-less call.
- System prompt 1.2: "When the user asks for a change, call the tool directly: the app asks them to confirm. Don't
  change anything they didn't ask for." plus "Look things up before using them: never guess a file name, a number or
  a date." replaces "…so call the tool directly" (a cause of issues 001 and 010). SFT v1/v2 were trained on prompt
  1.1: `python -m eval.run --prompt 1.1` scores them with it, and v3 with 1.2 (each model gets the prompt it was
  trained on; the tool list is always the current one).
- v2-derived examples were cleaned to the real tools' output: placeholder lines, KB sizes, impossible dates,
  count headers, sort order, `top_processes` and `search_notes` formats (about 550 fixed, 170 dropped).
- Not in 1.2, left for v4: dates in `list_directory`, RAM % in `system_info`, `recall` miss hint, `sum()` and dates in
  `calculate`, `older_than_days`.

Also in the same run: the completed data top-up (finished 2026-10-24; the set grew from 8,963 to 10,037 train and
471 to 529 val examples; every tool except `list_reminders` (199) now has ≥ 200).
**Language scope:** v3 is English only. The 537 Hinglish/Hindi synthetic examples are dropped and none are
generated; in-domain is reported on its 257 English items (21 Hinglish items kept as an untrained slice).
**Gate for v3:** the regression set passes, and in-domain, safety, e2e, When2Call and BFCL don't regress.
v2 on the regression set: 7/46.

## v2 (2026-10-23; the headline model until v4)
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
