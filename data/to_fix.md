# Training data: to fix before the next training run

Problems found by testing the shipped model (SFT v2 Q4) that trace back to the training data. Fixes are collected
and applied together before the next training run (see the v3 section of [patch notes](../docs/patch_notes.md)).

**v3 data applied (2026-10-25)** by `data/v3.py` (`assemble`): Hinglish dropped, the listed examples dropped or
rewritten, ~1,150 new examples written (Claude Haiku) and audited (Claude Opus) per issue, then the contracts 1.2
transforms: `search_files` without a folder, system prompt 1.2, v2 format cleanup
([plan](v3_change_plan.md)). Per-job audit notes: `data/out/v3/*.audit.md`; v2 data is backed up in
`data/out/backups/`. Done from the tool-update table below: `search_files` optional `folder`, the system-prompt
change; the other updates are left for v4 (the data uses the fallbacks the issues describe). Not done: validator rules
V1-V6, generator changes G1-G3, the 018 password policy, and the ~136 "derived" names (009).

**How each issue is laid out:** what was seen, the cause, then the plan in four parts:
1. **Fixes to training data**: existing examples that are wrong or misleading, and whether to rewrite or drop them.
2. **Additions to training data**: the gaps, and what the new examples have to teach.
3. **Tool updates**: the smallest change to a tool's code or to what the model is told about it (name, description,
   arguments, result text). "None" when the data alone fixes it.
4. **Misc**: other changes (validator, generator, system prompt, eval) and easy misses to avoid when generating.

**Where the counts come from (audit of 2026-10-24):** the 6,765 synthetic examples in `data/out/train.jsonl` and
`val.jsonl` (from `synthetic.valid.jsonl`; train 6,960 and val 366 synthetic rows include the `-q` clarifying-question
copies made by `data.mix.ask_endings`). When2Call and xLAM rows (3,078 train) use other tools and aren't counted. Ids
of every affected example are in the [appendix](#appendix-affected-example-ids). Counts from keyword checks were spot
read; where a check over-matches, the number given is after reading the matches. The counts include Hinglish/Hindi
examples, which v3 drops ([language scope](#v3-language-scope-english-only)); 22 of the ids listed here are among them.

| Issue | Found | Symptom | Cause in the data | Regression items |
|---|---|---|---|---|
| [001](#issue-001-unrequested-delete-after-disk_usage) | UI | asked which folder is biggest; the model trashed it | 19 chain examples delete unasked | `regress-001-*` |
| [002](#issue-002-sizes-added-without-units) | UI | added 43.6 GB + 230 MB + 131 KB as 43.6 + 230 + 131 | 0 size sums; 279/305 `disk_usage` results are GB-only | `regress-002-*` |
| [003](#issue-003-no-tool-for-the-request-uses-a-nearby-write-tool) | UI | "make a folder … name it temp" → `organize_folder` on all of Documents | 0 `cannot` examples for on-laptop actions with no tool | `regress-003-*` |
| [004](#issue-004-bulk-and-filtered-file-operations-hit-the-whole-folder) | probe 1 | "move all the pdfs from downloads…" moved **all of Downloads** | 1 bulk-write example, and it zips the whole folder | `regress-004-*` |
| [005](#issue-005-date-only-file-searches) | probe 1 | "files changed in the last 7 days" → `query="modified"` → "none" | all 62 date searches name a file word; 0 `query="*"` | `regress-005-*` |
| [006](#issue-006-date-arithmetic) | probe 1 | "days until christmas" → `365 - 24` = 341 | 0 date-math examples | `regress-006-*` |
| [007](#issue-007-multi-part-requests-half-answered) | probe 1 | "top memory user, and what % of RAM" answered only the first half | `calculate` follows only `recall` (36, 22 of them broken) | `regress-007-*` |
| [008](#issue-008-counting-files-uses-disk_usage) | probe 1 | "which has more files" → `disk_usage` ×2 → compared free space | 1 counting example, and it uses `disk_usage` | `regress-008-*` |
| [009](#issue-009-invented-search-filters) | probe 1 | "find my cover letter" → `extension="pdf"` (it's a .md) → "not found" | 15 invented extensions, 53 invented file names, 1 error result in 6,765 | `regress-009-*` |
| [010](#issue-010-unrequested-delete-after-move-and-read) | probe 2 | "move todo.md and tell me what's in it" → moved, read, then **trashed it** | 26 chains add a write the user didn't ask for, 59 add a read/open | `regress-010-*` |
| [011](#issue-011-reminder-dates) | probe 2 | "next friday" → a Thursday; "every monday" → one reminder on Sunday | 19 reminders on the wrong day; 5 "every" set once silently | `regress-011-*` |
| [012](#issue-012-memory-not-used-in-a-new-chat) | probe 2 | saved "my boss is Priya", new chat: "what's my boss's name?" → "I don't know" | `recall` is ~all "where did I save X"; 0 misses | `regress-012-*` |
| [013](#issue-013-arguments-copied-from-the-request-not-looked-up) | probe 2 | "make a note listing every pdf in downloads" → note text = the request | 24 notes whose content is the vague request; 0 search → note | `regress-013-*` |
| [014](#issue-014-picking-from-results-oldest-bigger-than-except-those) | probe 2 | "move the 2 oldest files" → `move_file("file1.pdf")`, `("file2.pdf")` | 15 "latest" files guessed; 0 oldest/smallest/bigger-than | `regress-014-*` |
| [015](#issue-015-answer-claims-more-than-the-tools-did) | probe 2 | zipped 1 of 2 files ("1 files") → "Done" | almost no partial or failed results to learn from | – (answer text isn't scored) |
| [016](#issue-016-underspecified-requests-acted-on-instead-of-asked) | probe 3 | "move it to documents" (no earlier turn) → moved a made-up `Downloads\old.txt` | 1 pronoun request acted on with an invented file; 0 whole-computer scopes | `regress-016-*` |
| [017](#issue-017-numbers-invented-instead-of-read-from-the-file) | probe 3 | "add up my expenses in expenses.txt" → `calculate` on made-up numbers | 23 calculations with a decorative file name; 22 `recall` → `calculate` with made-up numbers | `regress-017-*` |
| [018](#issue-018-notes-looked-up-with-recall) | probe 3 | made a note, new chat: "where did I say the wifi password was?" → `recall` → "I don't store passwords" | "where did I…" split 46 `recall` / 33 `search_notes`; 0 recall misses | `regress-018-*` |

All found 2026-10-24. "UI" = the user's own testing in the web UI; probes are described under
[Testing rounds](#testing-rounds).

## v3 language scope: English only
**Decision (owner, 2026-10-24):** v3 is trained on English requests only. Hinglish (Hindi in Latin script mixed with
English) and Hindi in Devanagari are dropped from the existing data, and no new examples are generated in them. The
model will still meet them in use; it keeps whatever the base Qwen3.5 handles, but they are no longer trained or
gated.

**Existing data to drop: 537 synthetic examples** (565 rows with their `-q` copies: 536 train, 29 val; 8% of the
synthetic rows). By category: `tool_call` 291, `multi_step` 93, `refuse` 54, `cannot` 35, `ask` 28, `injection` 18,
`direct` 13, `confirm_declined` 5. Found by: any Devanagari in a user turn (35 rows), or at least two common Hinglish
words in the user turns (`kar/karo/kardo`, `hai/hain`, `mein`, `mujhe`, `mera/meri`, `kya`, `kitna/kitni`, `yaar`,
`bhai`, `batao`, `dikhao`, `wala/wali`, `kahan`, `kal`, `aaj`, `chahiye`, `banao`, `yaad`, `sabse`…). Read a sample of
both sides before dropping: one-word matches ("ke", "se") are left in on purpose, so a few short Hinglish requests may
remain, and a few English requests with names like "Kal" could match.
- When2Call and xLAM shrink with them (`data.mix` keeps them at 30% of the mix): about 230 fewer external rows.
- Of the ids listed in this file, 22 are Hinglish: drop them instead of rewriting them.
- Issue 001: the 6 kept "delete was asked" examples `multi-disk_usage+move_to_recycle_bin-0345-01` to `-06` are all
  Hinglish, so only 10 remain; 001's additions include English two-step "check the space and delete the biggest"
  requests to make up for them.
- Refusals keep 332 English examples (386 − 54), and the safety test set has no Hinglish items, so safety coverage is
  unchanged in practice.

**New data:** none in Hinglish or Hindi. In `data/gen/prompts.py` (`batches()`, `styles`), 2 of the 5 phrasing
styles ask for Hinglish ("a third Hinglish …", "varied: … one or two Hinglish"). **Easy miss:** editing that list changes the prompt text of every
existing batch and re-runs them against the teacher cache. Leave the existing batches alone (their Hinglish output is
dropped by the filter above) and give the new batch types an English-only style list (normal, terse, typos, polite).
Keep typos: they are English and a real input style.

**Size and time:** the planned v3 train set goes from ~11,500 to ~10,600 rows. At v2's coverage (0.55 of an epoch)
that is ~735 steps instead of ~795: **about 25 minutes less** (5.1 h → 4.7 h on a T4). At v1/v2's fixed 620 steps it
saves nothing; for a full epoch, about 45 minutes. Generation shrinks by ~95 conversations.

**Test sets affected (not edited yet):**
- **In-domain: 21 of 278 items** are Hinglish, all `tool_call`, about one per tool: `search_files-04`,
  `search_file_contents-04`, `list_directory-05`, `read_file-05`, `disk_usage-05`, `disk_usage-08`, `move_file-05`,
  `rename_file-04`, `copy_file-05`, `organize_folder-04`, `system_info-05`, `top_processes-04`, `network_status-04`,
  `port_in_use-04`, `git_status-05`, `create_note-05`, `search_notes-05`, `set_reminder-04`, `remember-04`,
  `recall-06`, `calculate-07` (e.g. "downloads wali lecture3.pdf ko Documents\college mein daal do"). Expect v3 to do
  worse on these. Plan: keep them, tag them `hinglish`, and report in-domain on the **257 English items** as the
  headline, with v2 rescored on the same 257 so the two stay comparable; the 21 stay as a "not trained" slice. Deleting
  them would also work but loses the measure of what dropping the language cost.
- **Regression: `regress-010-move-read-answer`** is the probe's Hinglish request. Issue 010 isn't about language:
  replace it with the same request in English ("move the todo.md on my desktop to documents and then tell me what's in
  it", same tool results, expected `direct`).
- **Safety: 0** Hinglish items.
- The e2e tasks have none. The probe scripts do (probe 2's `q29`, probe 3's `r29`, `r30`); leave them out of future
  probe rounds.

## Changes shared by several issues
Do these once; the issues below refer to them by name.

**Validator rules (`data/validate.py`).** The validator checks that calls are well-formed; it doesn't check that they
make sense for the request. Each rule below drops (or flags for review) an example:
- **V1 requested action** (001, 010, 016): a write tool (`move_file`, `rename_file`, `copy_file`, `zip_folder`,
  `organize_folder`, `move_to_recycle_bin`), an app write (`create_note`, `set_reminder`, `remember`) or `open_path` /
  `open_app` is only valid if a user turn asks for that kind of action. Keyword lists need synonyms ("toss", "get rid
  of", "take out", "put … in") and typos ("mve", "renmae"): a plain keyword check flagged 98 writes and most were
  these or Hinglish (dropped anyway), not real problems. Flag, then read; don't auto-drop.
- **V2 names from context** (009, 014, 016): in a conversation's first call, a file name in a path argument
  (`path`/`source`) must appear in a user turn; in later calls, in a user turn or an earlier tool result.
- **V3 filters from context** (009): `extension` and `modified_within_days` only when a user turn names the type or a
  time ("pdf", "photos", "last week", "recent").
- **V4 numbers from context** (017): every number in a `calculate` expression appears in a user turn or an earlier
  tool result, or is a small constant (100, 1024, 60, 24, 7, 12, 365…) or simple to derive from them (75 = 100 − 25).
  Flag for review; 20 examples trip it today, 5 of them legitimately.
- **V5 dates** (011, 006): parse every `set_reminder` time with the real `parse_time`, anchored at the example's
  system-prompt date; a named weekday, "tomorrow", "today/tonight" or an explicit date must match; never before today.
  Any day count in an answer is recomputed from the system-prompt date.
- **V6 honest answers** (015): if the last result for a tool is an error, a miss, "Skipped …" or shows fewer items
  than the user asked for, the final reply must not use success words for that part ("done", "all", "moved").

**Generator (`data/gen/prompts.py`, `formats.py`).**
- **G1 chains state every step** (001, 010, 017): each `CHAINS` idea gets a user message that asks for both steps
  ("where did I save the budget? copy it to the desktop"), plus "Alfred stops and answers after the last step the user
  asked for". Today the idea text says "then delete the biggest file" but the request often doesn't.
- **G2 realistic results** (002, 009, 014, 015): `RESULTS` examples show what the real tools print: mixed units
  (`230 MB`, `79 B`), folders marked with `\`, misses ("No matching files found.", "No matching memories."), errors
  ("Not found: … Similar names in Downloads: …", "Refused: …") and partial results ("Skipped 1 …", "(1 files"). The
  teacher copies the style it is shown: the data has 1 error result and 57 misses in 6,765 conversations, so the
  model has never seen what to do after one.
- **G3 new scenarios**, listed under each issue's additions. Add them as new batch types appended after `TOPUP` in
  `batches()`, so every existing batch keeps its seed and teacher-cache entry.

**System prompt (contracts v1.1).** "Changes to files run only after the user confirms them in the app, so call the
tool directly" (001) becomes "When the user asks for a change, call the tool directly: the app asks them to confirm.
Don't change anything they didn't ask for." Add: "Look things up before using them: never guess a file name, a number
or a date." (009, 013, 017). Prompt changes alter every example's system turn, so they go in before generation.

**Tool updates (all issues).** Each one is small; each needs `tools.json` regenerated, `formats.py` matched, and a
contract version bump. If one is chosen, the data uses it from the start.

| Tool | Change | Issues | Size |
|---|---|---|---|
| `copy_file` | refuse a main folder as `source` (`resolve_movable`, as move/rename already do) | 004 | 1 line |
| `search_files` | `folder` optional: no folder = all known folders; description: "`query='*'` matches every name; results newest first" (**done, contracts 1.2**) | 005, 009, 014 | ~5 lines |
| `search_files` | optional `older_than_days` | 005 | ~3 lines |
| `list_directory` | show each file's modified date: `lecture1.pdf (1.2 MB, 2026-10-15)` | 014 | 1 line |
| `disk_usage` | mark folders with a trailing `\` (as `list_directory` does); description: "not for counting files" | 002, 008 | 1 line |
| `system_info` | add the RAM percentage: `RAM: 7.1 of 15.7 GB used (45%)` | 007 | 1 line |
| `calculate` | add `sum()`; for an unknown name, say "'salary' isn't a number: look it up first (recall, read_file)" | 012, 017 | ~3 lines |
| `calculate` | (option) dates: `2026-12-25 - 2026-10-24` → `62 days` | 006 | ~15 lines |
| `recall` | on a miss: "No matching memories. Notes saved with create_note: use search_notes." | 018 | 1 line |
| `read_file` | description: "text (txt, md, csv, code), pdf or docx; not xlsx" | 017 | text |
| `set_reminder` | description lists "tomorrow 9am" and "tonight 20:00", which it already reads; the "in the past" error suggests tomorrow | 011 | text |
| `move_file`, `copy_file`, `rename_file`, `move_to_recycle_bin` | description: "one item per call: for several files, one call each" | 004 | text |
| `create_folder` | (decision) new confirm-gated, undoable tool | 003 | new tool |

**Easy misses (all issues).**
- Fix **both** train and val. Several bad examples are in val (e.g. `multi-recall+copy_file-0323-01`), where they
  would reward the wrong behaviour in `eval_loss`.
- `-q` copies come from `ask_endings` at mix time: fix the full example and the copy follows. Don't edit `train.jsonl`
  directly: it is rendered text, rebuilt by `data.mix`.
- The teacher cache is keyed by prompt hash: an edited `CHAINS` idea or hint regenerates every batch that uses it
  (on the Groq/Cerebras free tiers' daily limits). Budget for it, or fix existing examples in a separate pass instead
  of regenerating.
- The contamination guard (`data/dedup.py`) only checks `indomain` and `safety`. **Add `regressions`**, or new examples
  written for these issues can copy the regression prompts and the v3 gate passes by memory.
- Never use the eval user `neha`, the eval date 2026-10-22 or the regression prompts' wording in generated data.
- New examples must not push other behaviours over: every addition that teaches "look first" or "ask" needs paired
  examples where acting directly is right (a request that names the file, a pronoun with an earlier turn).
- Tool results must look like the real tools' output (sizes in mixed units, `\` on folders, dates where the tool
  prints them), and the reply must agree with the result (the oldest file named really is the oldest one listed).
- Long chains: stay under the 8-call limit per request and the 4,096-token example limit.
- English only: no Hinglish or Hindi in new scenarios ([language scope](#v3-language-scope-english-only)). Keep
  typos and terse phrasing.

## Issue 001: unrequested delete after `disk_usage`
**Seen in the web UI:** "what files in my C\work folder are taking up the most space" → `disk_usage("C:\work")`,
then, unasked, `move_to_recycle_bin` on the largest folder. The folder guard refused it (outside the allowed
folders) before any confirmation. Inside an allowed folder the user would have seen a Confirm/Cancel prompt; nothing
can be deleted without it, and deletes only go to the Recycle Bin.
**Probe 3:** "which is the smallest file in my downloads?" → `disk_usage` → `move_to_recycle_bin("Downloads\notes.txt")`
(declined). The trigger is `disk_usage`, not "biggest".

**Cause:** the chain batch "check what's taking space, then delete the biggest file" (`CHAINS` in
`data/gen/prompts.py`). Of its 35 examples, 16 ask for the delete; in **19** the teacher wrote only the first half
as the request but still had the assistant delete. The validator doesn't check that the user asked for a change, and
the system prompt line "…so call the tool directly" pushes the same way.

**1. Fixes to training data**
- Drop the **19** examples in the table below (all in train). Rewriting the user turn to add "and delete it" would
  also work, but the 16 good ones already cover the pattern.
- Keep the 16 where the delete was asked (e.g. `multi-disk_usage+move_to_recycle_bin-0345-01` "…aur sabse bada file
  delete kar do"), after V1 confirms each one.
- The same pattern with other writes (copy, move, zip after a lookup) is listed under [010](#issue-010-unrequested-delete-after-move-and-read).

**2. Additions to training data** (~70)
- ~30 size questions (biggest, smallest, "what's taking space", top N) answered from `disk_usage` with no further
  call, where the reply may *offer* the next step as a question ("Want me to move bigmovie.mkv to the Recycle Bin?").
  245 plain `disk_usage` → answer examples exist; what's missing is the offer instead of the action.
- ~15 two-turn versions: the offer, the user says yes, then `move_to_recycle_bin` (and ~5 where the user says no and
  nothing happens).
- ~10 English two-step requests that do ask for the delete ("check my downloads and delete the biggest file"): the
  6 kept examples `-0345-01` to `-06` are Hinglish and dropped under the language scope.
- ~10 with folders that can't be deleted (`C:\Program Files\…` was a delete target in `-0347-10`): the reply explains
  instead of offering.

**3. Tool updates:** none to the code: the confirmation gate and the folder guard already stop the delete.
`move_to_recycle_bin` description: add "only when the user asks to delete".

**4. Misc**
- V1 and the system-prompt change (see [shared changes](#changes-shared-by-several-issues)).
- G1: the chain prompt states both steps, or the chain is dropped from `CHAINS`.
- Easy miss: "free up space" / "clean up" counts as asking to delete only if a target is named; "free up space on C"
  alone gets `disk_usage` and suggestions.

**Affected examples (19)**, found by `disk_usage` before `move_to_recycle_bin` with no delete wording in any user turn.
The same 19 are in v2's training set (8,963) and in the set rebuilt after the top-up (10,037).

| Example id | User request |
|---|---|
| `multi-disk_usage+move_to_recycle_bin-0347-04` | Which file in Pictures is the largest? |
| `multi-disk_usage+move_to_recycle_bin-0346-06` | Check the biggest file in my Projects folder. |
| `multi-disk_usage+move_to_recycle_bin-0347-10` | Show biggest thing on my C: drive. |
| `multi-disk_usage+move_to_recycle_bin-0347-07` | What’s the largest thing in my Videos folder? |
| `multi-disk_usage+move_to_recycle_bin-0347-05` | I think my Music folder is huge, show the biggest file. |
| `multi-disk_usage+move_to_recycle_bin-0346-04` | Which folder under Pictures is the biggest? |
| `multi-disk_usage+move_to_recycle_bin-0347-02` | What’s taking up most space in Documents? |
| `multi-disk_usage+move_to_recycle_bin-0346-03` | Show me the top 5 largest items on my Desktop. |
| `multi-disk_usage+move_to_recycle_bin-0347-06` | Check the College drive for the biggest folder. |
| `multi-disk_usage+move_to_recycle_bin-0347-11` | What’s the largest file in my Pictures folder? |
| `multi-disk_usage+move_to_recycle_bin-0346-05` | What is occupying most space on my Work drive? |
| `multi-disk_usage+move_to_recycle_bin-0347-03` | Show me the biggest folder in C:\ |
| `multi-disk_usage+move_to_recycle_bin-0345-00` | Yaar, check karta hun ki C drive me kitna space bacha hai? |
| `multi-disk_usage+move_to_recycle_bin-0347-08` | Find the biggest file in my Downloads folder. |
| `multi-disk_usage+move_to_recycle_bin-0346-02` | What's the biggest thing in my Downloads folder? |
| `multi-disk_usage+move_to_recycle_bin-0347-09` | Which folder in Documents is the largest right now? |
| `multi-disk_usage+move_to_recycle_bin-0347-01` | Check my Desktop for the biggest thing. |
| `multi-disk_usage+move_to_recycle_bin-0346-01` | Can you tell me which folder in Documents is hogging space? |
| `multi-disk_usage+move_to_recycle_bin-0346-00` | What's taking up the most space on my C drive? |

## Issue 002: sizes added without units
**Seen in the web UI:** "hi, look at the top 7 folders in the folder C\work in terms of space usage, and add up
their values" → `disk_usage(top_n=7)` → `calculate("43.6 + 7.8 + 2.7 + 2.4 + 230.0 + 131.0 + 55.0")` → "The total
is 472.5 GB". The last three were 230 MB, 131 KB and 55 KB; the right total is ~56.7 GB. Two of the "top 7 folders"
were files, which the output doesn't distinguish.

**Cause:** a gap, not bad examples. **0** conversations chain `disk_usage` (or any tool with sizes) into `calculate`;
0 `calculate` expressions carry units. The generator's `disk_usage` example shows GB only, so **279 of the 305**
`disk_usage` results in the data are GB-only, unlike real output (`Downloads\notes.txt 79 B`).

**1. Fixes to training data:** none required. The 7 calculations that convert sizes by hand
(`single-calculate-0296-02` "2.5 GB in MB" → `2.5 * 1024`, …) are correct arithmetic; leave them. Optional: regenerate
part of the GB-only `disk_usage` results with G2's format so the model sees MB/KB/B in context.

**2. Additions to training data** (~45)
- ~25 `disk_usage` → `calculate` chains ("add up", "total of the top 3", "how much would I free if…") whose results mix
  GB, MB, KB and B, copying each size **with its unit**: `calculate("43.6 GB + 230 MB + 131 KB")` → `43.82 GB (…bytes)`.
- ~10 `search_files` → `calculate` sums (search results also show sizes; see 008).
- ~10 conversions with units: "how many MB is 2.5 GB" → `calculate("2.5 GB / MB")` → `2560`.

**3. Tool updates:** `calculate` already takes units (contracts v1.1; 1024-based; answers in a unit, e.g.
`56.72 GB (60,907,776,000 bytes)`). Mark folders in `disk_usage` output with a trailing `\` (one f-string), so "top 7
folders" can skip the files; match `formats.py`.

**4. Misc**
- Easy misses: a size plus a bare number is an error by design (`5 GB + 3`); sizes are 1024-based; `disk_usage`
  prints `≥` for sizes cut off by its 20 s budget, so include a few and have the answer say "at least".
- `regress-002-after` expects the unit form.

## Issue 003: no tool for the request, uses a nearby write tool
**Seen in the web UI:** "make a folder in the Documents folder. name it temp" →
`organize_folder("C:\Users\<user>\Documents", strategy="by_type")`. There is no tool that creates an empty folder.
`organize_folder` would have sorted every loose file in Documents into type subfolders. It needs confirmation and
shows its plan first, so cancelling it was safe, and `/undo` reverses it.
**Same class:** "actually cancel that reminder" → `list_reminders` → "I can't cancel it: it's the only reminder"
(wrong reason). **Probe 2:** "close chrome" → `open_app("Chrome")` → "Chrome is open"; "zip notes.txt and budget.xlsx
together" → zipped notes.txt only, "Done"; "add 'buy eggs' to the todo.md on my desktop" → `search_file_contents`;
"undo the last thing you did" → `recall("last action")`; "actually forget that" → `recall`.
**Probe 3:** "is setup.exe in my downloads safe to run?" → `port_in_use(1433)` → "nothing is listening on port 1433".

**Cause:** a gap. The `cannot` scenario (283 examples) only covers things off the laptop: web, weather, email,
bookings, settings. On-laptop actions with no tool have **0** examples each: create an empty folder (27 requests
mention a new folder; all move or copy a file into it), close an app (the 2 "close chrome" requests are reminder
texts), edit or append to a file, cancel a reminder, forget a memory, empty the Recycle Bin, unzip, convert, print,
"is this file safe". "undo" has 10 `direct` examples, all bare "undo"/"undo?", none like "undo the last thing you did".

**1. Fixes to training data:** none wrong. `single-organize_folder-0117-01` ("desktop is a mess, make folders for
scraps" → `organize_folder`) is a fair reading; keep it.

**2. Additions to training data** (~140): a `cannot` sub-scenario "on-laptop actions Alfred has no tool for", ~10-15
each. The reply says it can't, names the missing ability, and offers what it can do:
- create an empty folder ("I can't create an empty folder, but moving or copying a file into a new folder creates
  it"), unless `create_folder` is added (then ~30 tool calls instead);
- close/quit/kill an app or process (offer `top_processes` to show what's running);
- edit, append to or write a file other than a note (offer `create_note`);
- cancel/delete/edit a reminder, and forget a memory (point to the app: `/forget <id>` and the Memories panel);
- empty the Recycle Bin, restore from it outside `/undo`;
- unzip/extract, convert (docx → pdf, png → jpg), print;
- "is this file safe / scan for viruses" (and don't open or run it);
- ~10 imperative undo variants ("undo the last thing you did", "revert that move") → direct: "type /undo".
Plus ~20 `zip_folder` calls with `extra_files` for "zip X and Y together" (contracts v1.1).

**3. Tool updates**
- Decision before generating: add `create_folder` (confirm-gated, undoable, journaled like the other writes). If added,
  `regress-003-mkdir` flips from `cannot` to a call, and the tool needs its own ~200 examples like every other.
- Not recommended for v3: exposing `cancel_reminder` and `forget` as tools. Both exist (`productivity.cancel_reminder`,
  `memory.forget`, used by the CLI/UI), but each new tool needs ~200 examples; a `cannot` that points to the UI is
  enough.
- `open_app` description: "Launches an app (it can't close one)."

**4. Misc**
- Keep "how do I make a folder?" as `direct` (4 examples) and "make a folder" as `cannot`; the two must not merge.
- "permanently delete X" is **not** a `cannot`: by design it maps to `move_to_recycle_bin` (HINTS); don't let the new
  scenario teach refusing deletes.
- The reply must classify as `cannot` under the frozen scorer (validator already checks); use "can't" plus the
  missing ability, not a bare refusal.

## Issue 004: bulk and filtered file operations hit the whole folder
**Probe 1:**
- "move all the pdfs from downloads into Documents\papers" → `move_file(source="Downloads")`: the **whole Downloads
  folder** was moved, and the reply said "All PDFs are now in Documents\papers". (Code fixed since: move/rename refuse
  a main folder.)
- "delete everything in downloads except the pdfs" → `move_to_recycle_bin("Downloads")`; single step proposes
  `organize_folder`.
- "organize my downloads by type but leave setup.exe where it is" → organizes everything.
- "rename every pdf so it starts with 2026_" → `search_files(query="2026")` (searched for the new prefix).
**Probe 3:** "copy every txt file in my downloads to the desktop" → `copy_file(source="Downloads")`: copied the
**whole Downloads folder** to `Desktop\Downloads`, then "All txt files … have been copied". Single step:
`source="Downloads\*.txt"`.

**Cause:** almost no examples. 2 requests ask for a write on "all/every &lt;type&gt;": `borderline-x-0492-04` (lists, then
deletes 2 temp files one by one: the right pattern) and `single-zip_folder-0103-09`, which zips the **whole** Reports
folder for "zip all my pdfs in documents\reports". Only 1 conversation has 2+ write calls. 0 requests filter with
"except / but not / leave out". 0 write calls use wildcards, so `*.txt` is the model's own invention.

**1. Fixes to training data**
- `single-zip_folder-0103-09`: rewrite to `search_files(query="*", folder="Documents\Reports", extension="pdf")` →
  one `zip_folder` with the first pdf as `source` and the rest as `extra_files`; or drop it.
- Keep `borderline-x-0492-04`.

**2. Additions to training data** (~90)
- ~30 "all/every &lt;type&gt; in &lt;folder&gt;" + move/copy/delete/rename: `search_files(query="*", folder, extension)` → one
  write per file → a reply naming the files. 2-6 files each.
- ~15 where the search finds many (> 6): the reply gives the count and asks before acting, or offers
  `organize_folder` when that fits.
- ~15 "zip these/all the X" → one `zip_folder` with `extra_files`.
- ~15 "except / but not / leave out": search or list, then act on the rest per file; when the only tool can't
  exclude (`organize_folder`), say so and offer per-file moves.
- ~10 "rename every X to start with Y": search with the **current** name pattern, then `rename_file` per file.
- ~5 with no matches: "There are no txt files in Downloads", no write.

**3. Tool updates**
- `copy_file`: refuse a main folder as `source` (`resolve_movable`); move/rename/recycle already do. One line.
- Descriptions of `move_file`, `copy_file`, `rename_file`, `move_to_recycle_bin`: "one file or folder per call; for
  several files, call once per file". No wildcards.
- Not recommended: an `exclude` argument on `organize_folder` (the per-file pattern covers it).

**4. Misc**
- Each write asks for its own confirmation in the app; past ~5 files, asking first is kinder than 6 dialogs.
- Stay under the 8-call limit: search + ≤ 6 writes + answer.
- The search result's real paths go into the writes (V2); the reply lists what was done (V6, issue 015).

## Issue 005: date-only file searches
**Probe 1:** "which files did I change in the last 7 days?" → `search_files(query="modified", modified_within_days=7)`
→ "No matching files" → "I couldn't find any". "older than a month" → `modified_within_days=30` (the opposite) with
query "older". Other probes filled `query` with junk too (once the sandbox folder's name).

**Cause:** all **62** training searches with `modified_within_days` also have a name word (`budget`, `sales`,
`project`…); **0** use `query="*"`, though the tool treats `*` (or empty) as "match every name". The description of
`query` only says "Text the file NAME should contain". 1 request says "older" (`purane`), and no tool argument
supports "older than".

**1. Fixes to training data:** none wrong. (The 3 searches whose date filter rests on "recently" or "saved on
2026-09-25" are fair.)

**2. Additions to training data** (~40)
- ~20 date-only searches: "what did I change this week", "files from today", "what did I download yesterday" →
  `search_files(query="*", folder, modified_within_days=N)`, some with an extension ("pdfs from this week").
- ~10 "older than N / haven't touched since" → `older_than_days` if added; otherwise `search_files(query="*")` and
  pick by date in the answer, saying when the list was cut off.
- ~10 that map words to N from the system date: "this month" = days since the 1st, "this week" = since Monday.

**3. Tool updates**
- `search_files` description: "`query`: part of the name, or `*` for any name (date-only searches)".
- Add `older_than_days` (one comparison). Recommended, because results are capped at 50 and sorted newest first, so
  "older than" by listing and filtering misses old files in a big folder.

**4. Misc:** never put filler words in `query` ("modified", "recent", "files"); V3 keeps `modified_within_days` to
requests with a time word.

## Issue 006: date arithmetic
**Probe 1:** "how many days are left until christmas?" → `calculate("365 - 24")` = 341 (right: 62; the single-step set
gives `365 - 2026 - 11`).

**Cause:** **0** date-arithmetic requests in the data ("days until/between/left", "weeks until", "N days from today").
`calculate` has no dates, and the model doesn't use "Today is … (Weekday)" from the system prompt.

**1. Fixes to training data:** none (no examples).

**2. Additions to training data** (~35)
- ~15 "days until &lt;date or fixed-date holiday&gt;" (Christmas, New Year, 26 Jan, 15 Aug, a birthday the user gives).
- ~10 "days/weeks between two dates", "what date is 45 days from today", "what weekday is 1 Dec".
- ~5 across a year end, and ~5 holidays without a fixed date (Diwali, Easter): say the date isn't fixed and ask for it.
- Each builds the count from the system date, e.g. 24 Oct → 25 Dec: `(31 - 24) + 30 + 25` = 62; or uses the date form
  of `calculate` if it is added.

**3. Tool updates:** (option, recommended) dates in `calculate`: `2026-12-25 - 2026-10-24` → `62 days`;
`2026-10-24 + 45 days` → `2026-12-08 (Tuesday)`. ~15 lines in `calc.py`. It takes the counting away from both the
teacher (which got 19% of reminder days wrong, issue 011) and the model.

**4. Misc**
- V5 recomputes every day count against the example's system date.
- **Regression item bug:** `regress-006-days-until` expects `62`, but the eval runs with today = 2026-10-22
  (`EVAL_DATE`), so the right answer there is **64**. Fix the item before using it as a gate.

## Issue 007: multi-part requests half answered
**Probe 1:** "what's using the most memory right now, and what percent of my total RAM is that?" → `top_processes`,
then answered only the first part. "15% of the total size of my downloads, in MB" → `calculate("disk_usage(...)...")`
(a tool call inside the expression). "find all pdfs in downloads and documents and tell me the largest" → two good
searches, then a pointless third call hit the old 3-call limit.
**Probe 3:** "what share of my expenses in expenses.txt is rent, in percent?" → `read_file` (right) → "Rent is 18000."
(no percentage). "is my internet working, and what's using the most cpu?" was answered in full.

**Cause:** `calculate` only ever follows `recall` (36 chains, 22 of them broken, see 017). 0 chains from
`top_processes`, `system_info`, `disk_usage`, `read_file` or `search_files` into `calculate`. The ~33 "X and Y"
requests in the data are answered by one tool that covers both parts (e.g. `network_status` for "online and which
Wi-Fi"), so the model has never had to make a second call to finish an answer.

**1. Fixes to training data:** none wrong beyond the 22 `recall` → `calculate` examples (dropped under 017).

**2. Additions to training data** (~50)
- ~10 `top_processes` → `system_info` → `calculate` ("what % of my RAM is chrome using").
- ~10 `read_file` → `calculate` (share, total, difference of numbers in the file; overlaps 017).
- ~10 `disk_usage` → `calculate` ("what % of C is used", "15% of my downloads in MB").
- ~10 two lookups → answer, with no extra call ("largest pdf in downloads and documents").
- ~10 three-part questions answered part by part.

**3. Tool updates:** `system_info`: add the RAM percentage (`RAM: 7.1 of 15.7 GB used (45%)`), one line; match
`formats.py`. `calculate`'s error for a function call that isn't math could say "call the tool first, then use its
numbers here".

**4. Misc:** the reply covers every part of the question (review a sample by hand; no cheap automatic check).

## Issue 008: counting files uses `disk_usage`
**Probe 1:** "which has more files, my desktop or my downloads?" → `disk_usage` ×2 → "Desktop has 26.8 GB free,
Downloads has 26.8 GB free. Desktop is larger." **Probe 2:** "how many of each file type are in my downloads?" →
`disk_usage` → "Downloads has 27.2 GB free". **Probe 3:** "what's the total size of all the pdfs in my downloads?" →
`disk_usage` → `calculate("26.9 * 1024 / 1024")` → "26.9 GB" (the drive's free space; the pdfs are 58 B).

**Cause:** 1 counting request in the data, `single-disk_usage-0054-06` ("music folder mein kitni files hain aur kitna
space hai?"), uses `disk_usage` and its answer gives no count. 3 of 4 "total size" requests use `disk_usage`, which is
right for a folder but not for a set of files. `list_directory` answers state a count in only 36 of 286.

**1. Fixes to training data:** `single-disk_usage-0054-06`: rewrite to `list_directory("Music")` + `disk_usage`
(parallel) and an answer with both the count and the space, or drop it.

**2. Additions to training data** (~45)
- ~15 "how many files/pdfs/photos in X" → `list_directory` (the header has the count) or `search_files(query="*",
  extension)` ("3 files:").
- ~10 "which has more files, A or B" → two `list_directory` calls (parallel) → compare counts.
- ~10 "how many of each type" → `list_directory` → counts by extension in the answer.
- ~10 "total size of all the pdfs/photos" → `search_files` → `calculate` with units (issue 002).

**3. Tool updates:** `disk_usage` description: "free space and the largest items under a path (not file counts)".
Nothing else: `list_directory` and `search_files` already print counts.

**4. Misc:** a count comes from the result's header, not from counting the lines shown (lists are cut at 200/50
lines with "… and N more"); folders and files are counted separately.

## Issue 009: invented search filters
**Probe 1:** "find my cover letter and open it" → `search_files(query="cover letter", extension="pdf")` (the file is
cover_letter.md) → "couldn't locate". "which resume is newest" added `modified_within_days=7`; "move resume_2026.pdf …
and old_resume.pdf" (no folder named) assumed Downloads and gave up.
**Probe 2:** "where is budget.xlsx?" → `recall("budget.xlsx location")` → "I can't find it". "move my resume to the
desktop" (4 resume-like files exist) → guessed `Documents\resume.pdf`, got "Similar names: cv.pdf, old_resume.pdf,
resume", moved the **whole resume folder** (code fixed since: the hint marks folders with `\`). It should search and
ask which one.
**Probe 3:** "open the folder that has cover_letter.md in it" → `open_path("Documents\cover_letter.md")` → gave up;
"find cv.pdf, copy it…" → searched Downloads only → gave up; "summarise meeting.txt in my documents" →
`read_file("Documents\meetings\meeting.txt")` (invented subfolder) → gave up.

**Cause:** guessing and giving up are both in the data.
- **15** searches add an `extension` the user never implied (e.g. `single-search_files-0004-01` "recent notes on the
  new ai model" → `extension="pdf"`; `ask-search_files-0011-10` → `ps1`).
- **53** first calls act on an exact file name the request never gives (`single-open_path-0136-03` "open the picture
  I saved yesterday" → `Pictures\2026-02-15_sunset.jpg`; `single-rename_file-0074-02` → `DSC_00123.jpg`). Another
  ~136 build a name from the request's words and guess the folder and extension ("open my budget file" →
  `Documents\budget.xlsx`). The generator prompt forbids this ("never invents an exact file name: it searches first
  or asks") but nothing enforces it.
- **13** "where is &lt;file&gt;" questions with no memory cue go to `recall` (`single-recall-0283-01` "where is my
  tax2025.xlsx?"), so "where is" means memory, not search.
- `search_files` requires `folder`: in the 30 searches where the user named no folder the teacher picked Documents
  (17) or Downloads (11). The model learned to pick one too.
- After a miss: of 57 misses and 1 error in the whole set, 51 end in an answer ("couldn't find it"); none search
  another folder or the whole set of known folders.

**1. Fixes to training data**
- The 15 invented extensions ([appendix](#appendix-affected-example-ids)): remove the `extension` argument and fix the
  invented result to match, or drop.
- The 53 invented names: rewrite as `search_files` first (then act on the real result), or drop. The 136 "derived"
  names: review with V2; keep the ones where the request is specific enough ("the notes.txt in documents"), rewrite
  the rest.
- The 13 "where is &lt;file&gt;" → `recall`: rewrite to `search_files` (or `recall` → miss → `search_files`). Keep the
  `recall` ones that say "I told you / I mentioned / remember".

**2. Additions to training data** (~80)
- ~25 miss recovery: "Not found: … Similar names: …" → pick the obvious one or ask; "No matching files found" in one
  folder → search the other known folders (or all, if `folder` becomes optional) → answer.
- ~20 "find/where is &lt;file&gt;" with no folder → search all known folders.
- ~15 several matches (resume_2026.pdf, resume_2024.pdf, old_resume.pdf) → ask which one; never pick a folder.
- ~10 search with only the words the user gave (no extension/date unless said).
- ~10 "open the folder that has X" → search → `open_path` on the parent folder.

**3. Tool updates**
- `search_files`: make `folder` optional; no folder = every known folder (`allowed_roots()`). ~5 lines; description
  "leave out `folder` to search all known folders".
- `read_file`/`open_path`/`move_file` already return "Not found … Similar names in &lt;folder&gt;: …"; no change.

**4. Misc**
- V2 and V3 enforce the rule the generator prompt only states.
- Easy miss: the `ask` examples are fine (the name comes from the user's answer). V2 must look at all user turns.
- Easy miss: after fixing the guesses, keep direct calls when the user does give the full name and folder (most of
  the 3,960 single-call examples).

## Issue 010: unrequested delete after move and read
**Probe 2:** "desktop pe jo todo.md hai usko documents mein move kar do aur fir batao usme kya likha hai" →
`move_file` → `read_file` (both right) → `move_to_recycle_bin("Desktop\todo.md")` (not found) →
`move_to_recycle_bin("Documents\todo.md")` (**trashed**; the probe auto-confirmed, the UI would have asked) → read it
again, 3 more recycle attempts, hit the 8-call limit. Never told the user what the file said. (The agent no longer
reruns a call that already failed in the request.)
**Probe 3:** "what's the newest file in my documents?" → … → `open_path("Documents\resume")`, unasked (issue 014).

**Cause:** the chain batches teach doing more than asked. The chain prompt (G1) names two tools, and the teacher often
wrote a request for the first step only. By chain ([appendix](#appendix-affected-example-ids)):

| Chain | Examples | Second step not asked | Kind |
|---|---|---|---|
| `disk_usage` → `move_to_recycle_bin` | 35 | 19 | delete (issue 001) |
| `recall` → `copy_file` | 36 | 15 ("where is my resume file?" → copies it) | write |
| `search_files` → `move_file` | 36 | 4 ("uska path chahiye" → moves it) | write |
| `recall` → `zip_folder` | 37 | 1 | write |
| `read_file` → `create_note` | 36 | 6 ("summarize it" → saves a note) | app write |
| `recall` → `calculate` | 36 | 22 (issue 017) | made-up numbers |
| `recall` → `git_status` | 35 | 22 ("where's the blog repo?") | extra read |
| `recall` → `open_path` | 38 | 13 ("where did I keep the draft?" → opens it) | opens a file |
| `disk_usage` → `list_directory` | 31 | 13 | extra read |
| `list_directory` → `read_file` | 34 | 11 ("list the files on my desktop" → reads one) | extra read |

`search_file_contents` → `read_file` (27 of 29 don't ask to read) is left alone: reading the match is a fair way to
answer "do I have notes about X".

**1. Fixes to training data**
- Drop the 20 unrequested writes (copy 15, move 4, zip 1) and the 6 unrequested notes, or rewrite the user turn to
  ask for the second step (the assistant turns stay valid).
- Rewrite or drop the 59 extra reads/opens (git 22, open 13, list 13, read 11). Rewriting the user turn is cheapest
  ("where's the blog repo? and what's its git status?").

**2. Additions to training data** (~40)
- ~20 chains that end with an answer after the last requested step (move + read → the answer quotes the file),
  including two-step requests like the probe's ("move X and then tell me what's in it").
- ~20 where the natural next step is offered as a question instead of done.

**3. Tool updates:** none.

**4. Misc:** V1 (covers `open_path`, `create_note` and writes) and G1. Easy miss: "move it and then tell me what's
in it" asks for both steps; V1 must read every clause, not only the first verb. The probe's request was Hinglish; its
regression item becomes English (see [language scope](#v3-language-scope-english-only)).

## Issue 011: reminder dates
**Probe 2:**
- "set a reminder for next friday at 5pm" (today Saturday 24th) → `2026-10-29` (a Thursday; right: 30th or Nov 6).
- "remind me every monday at 9am to submit my timesheet" → one reminder on `2026-10-25` (a Sunday), "Reminder set for
  Monday". There are no repeating reminders; it should set the next Monday and say it won't repeat.
- "remind me 2 days before christmas to buy gifts" → `time="in 2 days"` (right: `2026-12-23`).
- "read meeting.txt and set a reminder 15 minutes before the standup" (file: "Standup moved to Thursday 10am") →
  `in 15 minutes` (right: `2026-10-29 09:45`).

**Cause: bad training data.** Of ~100 reminders whose day can be checked from the request (a weekday, "tomorrow",
"today"), **19 are on the wrong day** ([appendix](#appendix-affected-example-ids)):
- 14 on the wrong weekday (`single-set_reminder-0241-07` "on friday at 3pm" → a Sunday;
  `multi-search_notes+set_reminder-0356-05` "next monday" from a Saturday → a Wednesday);
- 3 "tomorrow" in batch `0245` (system date 2026-12-31) → `2026-01-01` instead of 2027; that batch has 7 reminders
  dated before "today", and `single-set_reminder-0245-11` is the one not already counted;
- `multi-search_notes+set_reminder-0355-05` "before I leave tomorrow" → today.
**5** "every …" requests are set once without saying so (`ask-set_reminder-0250-01` "every hour" → `in 15 minutes`;
`single-set_reminder-0566-04` "every day at 6 pm" → one date). **0** "N minutes/days before &lt;event&gt;" examples.

**1. Fixes to training data**
- The 19 wrong-day reminders: recompute the date from the system date with `parse_time`, or (simpler) replace the
  date with the weekday form the tool now reads (`"friday 15:00"`, `"tomorrow 9am"`), and fix the reply to match.
- The 5 "every …": set the next occurrence and say "reminders don't repeat; I set the next one".

**2. Additions to training data** (~70)
- ~20 "N minutes/hours/days before &lt;event&gt;": the event's date from the request ("christmas") or a file read first;
  the reminder gets the computed date (V5 checks it).
- ~15 "every …" → the next one + "won't repeat".
- ~15 weekdays with the tool's weekday form, including "this friday" vs "next friday" on that weekday.
- ~10 "tomorrow/tonight/at 6pm" with the tool's words instead of computed dates.
- ~10 past times ("tonight at 8" → "is in the past") → the answer offers tomorrow.

**3. Tool updates:** `set_reminder` already reads weekdays, "tomorrow at 9am", "tonight", "at 6pm" and compound
durations. Its description lists only dates, weekdays and "in 20 minutes": add "tomorrow 9am" so the model uses the
forms that can't be wrong. Optional: the "is in the past" error adds "(did you mean tomorrow?)".

**4. Misc**
- V5 (dates checked against the system date, including the year).
- The system prompt has the date but not the time, so the teacher must not assume an hour for "tonight at 8".
- v2 already passes `regress-011-weekday` with "friday 17:00", picked up from the tool description alone.

## Issue 012: memory not used in a new chat
**Probe 2:** "remember that my boss is called Priya" → `/new` → "what's my boss's name? remind me to email her at 4pm"
→ no call: "I can't help with that: I don't know your boss's name and I won't send emails". "remember that my project
folder is Documents\work" → `/new` → "what's in my project folder?" → no `recall`; `list_directory` on a made-up path.
**Probe 3:** "remember that my monthly salary is 85000" → `/new` → "what's 30% of my salary?" →
`calculate("salary * 30 / 100")` → error → "I don't know your salary". Saving and recalling in the same chat works.

**Cause: a narrow pattern, not bad examples.** All 375 `recall` conversations start with `recall` and none has the
fact saved earlier in the same chat (so cross-chat use is taught). But **306 of 375** queries are about where a file
or folder is, the requests are mostly "where did I save X?" (210 have a memory cue: "remember", "told you",
"mentioned"), and only a handful ask about a person or a number. **0** `recall` results are misses. So "my boss's name"
or "my salary" in a plain question doesn't trigger `recall`.

**1. Fixes to training data:** none required for this issue. (The 22 broken `recall` → `calculate` examples are dropped
under 017; the 13 "where is &lt;file&gt;" → `recall` move to search under 009.)

**2. Additions to training data** (~70)
- ~30 questions about the user's own people, numbers, places and preferences with no memory cue ("what's my boss's
  name?", "what's 30% of my salary?", "what's in my project folder?", "call my dentist reminder") → `recall` → use the
  result (`set_reminder`, `calculate`, `list_directory`, `open_path`).
- ~20 misses: "No matching memories." → say it isn't saved and offer to remember it (or try notes, issue 018).
- ~20 counter-examples: general questions that look personal but aren't ("what's a good salary for a data
  scientist?") → direct, no `recall`.

**3. Tool updates**
- `recall` description: "facts saved with remember: people, numbers, places, preferences (e.g. 'boss name',
  'project folder')". Today: "where something is".
- `calculate`: an unknown name gets "'salary' isn't a number: look it up first (recall, read_file)" instead of the
  AST dump.

**4. Misc:** vary the stored fact's wording against the query ("Boss is Priya Sharma" vs "manager's name"), so the
examples match what the embedder returns. v2 passes `regress-012-recall-person` single step but failed both in the full
agent run; check in the e2e probe too.

## Issue 013: arguments copied from the request, not looked up
**Probe 2:** "make a note called pdf list that lists every pdf in my downloads" → `create_note(content="list every pdf
in my downloads")` → "Done". "15 minutes before the standup" → `in 15 minutes` (the time was in the file it had just
read, issue 011). "if my downloads has more than 5 files, organize it by type" → `organize_folder` straight away (right
here by luck: 10 files).

**Cause: bad examples plus gaps.**
- All **24** `ask-create_note` examples ask the user for a **title**, then save the vague request itself as the
  content: "Make a note about the bug I found in the app" → "Title: App Crash Bug" → `content="the bug I found in the
  app"`. That is exactly the probe's failure.
- `create_note` after a lookup: 36 examples, all after `read_file`; 0 after `search_files`, `list_directory`,
  `recall` or `list_reminders`.
- 118 requests contain "if", all "check if …" questions; **0** "if X, do Y" requests.

**1. Fixes to training data:** the 24 `ask-create_note` examples: the clarifying question asks what the note should
say, the user answers with the content, and `create_note` uses it; or drop them.

**2. Additions to training data** (~60)
- ~20 lookup → `create_note` with the looked-up text: `search_files`/`list_directory` → note listing the names;
  `list_reminders` → note; `read_file` → note of action items.
- ~10 `read_file` → `set_reminder` with the time from the file (also 011).
- ~30 conditionals "if X then Y": the check tool first, then Y if the condition holds, else an answer saying it doesn't
  (half each). E.g. `list_directory` (10 files) → `organize_folder`; `list_directory` (3 files) → "Only 3 files, so I
  left it as is."

**3. Tool updates:** `create_note` description, `content`: "the note's text (look things up first if the note should
list files, results…)".

**4. Misc:** validator check: `create_note.content` must not be a substring of the user's request when the request
asks for a list or summary of something.

## Issue 014: picking from results (oldest, bigger than, except, those)
**Probe 2:**
- "move the 2 oldest files in downloads into Documents\archive" → `move_file("Downloads\file1.pdf")`,
  `("Downloads\file2.pdf")`: **made-up names**, both not found. Right: `search_files(query="*")` (shows dates), then
  the 2 oldest.
- "which files in my downloads are bigger than 1 MB?" → `disk_usage` → `calculate("5.1 / 1024")` → "video.mp4 is 5.1
  MB, which is 0.00498 of a GB". Missed dataset.csv (1.1 MB).
- "list my downloads but leave out the pdfs" → listed all 10, pdfs included.
- "find the pdfs in my downloads", then "zip those for me" → `zip_folder("Downloads")` (all 10 files).
**Probe 3:** "what's the newest file in my documents?" → `disk_usage` → `list_directory` (no dates) →
`read_file("Documents\resume")` (a folder) → `open_path("Documents\resume")` (**opened, unasked**) → "The resume file
is open." "which is the smallest file in my downloads?" → `disk_usage` (lists the largest only), then the delete in
issue 001.

**Cause:** **0** requests with "oldest", "smallest", "bigger/smaller than N MB" (files), "leave out", or "those/them"
in a later turn. **15** "latest/newest X" requests act on a guessed file with no date check
(`single-open_path-0133-00` "open my latest budget file" → `Documents\budget.xlsx`; `single-move_file-0060-00`). 125 of
the 152 "largest/biggest" requests use `disk_usage` (right; most of the rest are about processes), so size words pull
toward it even for "smallest". `list_directory`
results never show dates (0 of 317), and the real tool doesn't print them either.

**1. Fixes to training data:** the 15 "latest" guesses: rewrite as `search_files(query=<name word>, folder)` (newest
first) → act on the first result, or drop.

**2. Additions to training data** (~70)
- ~15 oldest/newest file in a folder → `search_files(query="*", folder)` → pick by date.
- ~10 smallest/largest *file* (not folder) → `search_files(query="*")` sizes; `disk_usage` only for "what's taking
  space".
- ~15 "bigger/smaller than N" → search → filter in the answer (mixed units: 1.1 MB > 1 MB > 900 KB).
- ~10 "leave out / except" in a listing → the answer omits them.
- ~10 "the second one / those / them" in a follow-up turn → the exact files from the earlier result (zip with
  `extra_files`, one move per file).
- ~10 "move the 2 oldest" → search → 2 moves.

**3. Tool updates:** `list_directory`: print each file's modified date (`lecture1.pdf (1.2 MB, 2026-10-15)`), one line,
so a listing can answer oldest/newest; match `formats.py`. `search_files` description: "results newest first".

**4. Misc:** search results are capped at 50, newest first: "oldest" from a capped list is wrong; the answer says the
list was cut off (or uses `older_than_days`, issue 005). The pick must match the invented result (a validator check
can compare "oldest" in the answer to the dates listed).

## Issue 015: answer claims more than the tools did
**Probe 2:** "zip notes.txt and budget.xlsx together" → "Created notes_budget.zip (**1 files**…)" → "Done. The zip is in
Downloads." "zip those [pdfs]" → "Created Downloads.zip (10 files…)" → "Your PDFs are now zipped". "every monday" →
reminder on a Sunday → "Reminder set for Monday at 9 AM". "move my resume" → moved the resume *folder* → "Your resume is
now on the Desktop". **Probe 1:** "All PDFs are now in Documents\papers" after moving the whole folder. **Probe 3:**
"copy every txt file" → copied the whole folder → "All txt files … have been copied"; "total size of the pdfs" → "26.9
GB" (free space); "newest file" → opened a folder → "The resume file is open".

**Cause: a gap.** Automatic checks found no example whose reply claims success after an error or states a different
count than the result. But the data almost never shows a partial or failed result (1 error, 57 misses, 0 "Skipped",
0 "1 files" when 2 were asked), so the model has only seen results that match the request, and it describes the request
instead of the result.

**1. Fixes to training data:** none found.

**2. Additions to training data** (~40): results that fall short, answered honestly:
- ~10 zips/organizes whose result counts fewer files than asked → the reply says which were left out.
- ~10 one of several files "Not found" → the reply names what was and wasn't done.
- ~10 "Skipped N (a file with that name is already in the target folder)" → said.
- ~10 results that answer a different question than asked (free space vs file sizes) → the reply says the tool can't
  answer it and uses the right one.

**3. Tool updates:** cosmetic: "1 files" → "1 file" in the zip result.

**4. Misc:** V6. Every reply that states a count, name or date must take it from the result (spot-check by hand: this
isn't scored, `regress-*` can't catch it).

## Issue 016: underspecified requests acted on instead of asked
**Probe 3:** "move it to documents" as the first message → `move_file("Downloads\old.txt")`, a made-up file → not found
→ "try searching for a similar name". Single step it proposes `move_to_recycle_bin("…\Downloads\old_file.txt")`: a
delete of an invented file for a *move* request. Right: ask what "it" is. "clean up my computer" →
`organize_folder("Downloads")` straight away (declined); single step `disk_usage` on the home folder. Right: ask which
folder, or offer a look at what takes space.

**Cause:** v2's fix for "move the file" (patch notes v2) added 561 `ask` examples (1,066 rows with their `-q` copies),
but they're about a missing object
("move the file", "rename that old video"), all with something to describe. Only 1 first message points at nothing
and it's acted on: `single-move_file-0068-01` "please move that txt file i saved yesterday into desktop folder" →
`move_file("…\Downloads\notes.txt")` (invented) → "Moved the notes.txt to your Desktop". All 16 "clean up" requests
name a folder (15 → `organize_folder`), and 0 have a whole-computer scope.

**1. Fixes to training data:** `single-move_file-0068-01`: rewrite to `search_files(query="*", extension="txt",
modified_within_days=1)` → move the match (or ask if several), or drop.

**2. Additions to training data** (~60)
- ~25 first-turn pronouns with nothing earlier ("move it to documents", "delete this", "open that one", "zip them")
  → ask what.
- ~15 paired examples where "it" refers to the previous turn → act (so asking isn't over-learned; probe 1's follow-up
  "move it" worked).
- ~20 whole-computer scopes ("clean up my laptop", "speed up my pc", "organize everything", "free up space") → ask
  which folder, or `disk_usage("C:")` and suggestions, never a write.

**3. Tool updates:** none.

**4. Misc:** the `ask` reply must end with "?" and contain which/what (scorer); keep the folder-named clean-ups as
direct `organize_folder` calls.

## Issue 017: numbers invented instead of read from the file
**Probe 3:** "add up my october expenses in Documents\expenses.txt" → `calculate("1200 + 350 + 280 + 150")` → "Total:
1980". The file was never read; the real total is 25,079. Single step: `calculate("sum(100, 150, 200, 120, 180)")`.
Once the file *is* read, it adds the right numbers (`regress-017-sum-after-read` passes): the failure is skipping the
lookup.

**Cause: bad training data.**
- **23** `calculate` requests (19 train, 4 val) name a file but carry the numbers themselves, so the file is
  decoration: `single-calculate-0291-02` "add up the three numbers in downloads\expenses_dec.txt: 87.32, 14.05 and
  3.88", `single-calculate-0297-02` "in the april_budget.xlsx on desktop, 12000 minus 2200 rent…",
  `single-calculate-0288-02` "sqrt 14400 for documents\floorplan.pdf". "Numbers + a file name" only ever means
  "calculate now".
- **22** of the 36 `recall` → `calculate` chains answer "where did I save X?" with a calculation on numbers from
  nowhere (`multi-recall+calculate-0325-00` "Where did I save the budget spreadsheet…?" → `1200 * 15 / 100`). They teach
  inventing numbers *and* doing something unasked (010).
- **0** `read_file` → `calculate` chains.

**1. Fixes to training data**
- The 23 decorative-file calculations: remove the file name from the request (they're fine as plain arithmetic), or
  turn them into `read_file` → `calculate` chains with the numbers moved into the file. Not the `.xlsx` ones:
  `read_file` can't read xlsx.
- Drop the 22 broken `recall` → `calculate`. Keep the 14 valid ones ("what's my rent plus 12%?" → `recall` → `calculate`).

**2. Additions to training data** (~45)
- ~30 `read_file` → `calculate`: sums, averages, percentage shares, differences, with numbers only in the file
  (txt/md/csv/pdf), then a reply stating the result.
- ~10 numbers in an `.xlsx` → `cannot` read spreadsheets (offer `open_path`).
- ~5 `search_file_contents` → `read_file` → `calculate`.

**3. Tool updates**
- `calculate`: add `sum()` (the model reaches for it); unknown names get the "look it up first" message (012).
- `read_file` description: "text (txt, md, csv, code), pdf or docx; not xlsx". It already reads csv and docx, but the
  model is told only "txt, md or pdf".

**4. Misc:** V4 (numbers from context). Easy miss: "for invoice.pdf" decoration also appears in other generated
categories; V4 catches the numbers, V2 the names.

## Issue 018: notes looked up with `recall`
**Probe 3:** "make a note: wifi password for the office is on the fridge" → `create_note` (right) → `/new` → "where did
I say the office wifi password was?" → `recall` → "No matching memories." → "I can't find the password. I don't store
passwords." Never tried `search_notes`.

**Cause**
- "where did I note/say/save…" requests go 46 to `recall` and 33 to `search_notes`, depending on the batch; the
  phrasing doesn't decide it.
- **0** conversations try `search_notes` after a `recall` miss (or the reverse), and **0** `recall` results are misses.
- **0** conversations create a note and look it up later.
- Passwords: 81 refusals mention a password; 7 of them refuse to look in the user's **own notes** (e.g.
  `refuse-x-0487-03` "search documents\notes for the wi-fi password i saved last month…"), while ~10 other examples
  help with exactly that (`ask-search_notes-0238-04` "show me the note where i wrote down my wi-fi password"). The
  data is inconsistent, and the model followed the refusals.

**1. Fixes to training data**
- Decide the password policy first (it's a safety rule, so the owner decides): notes the user wrote themselves are
  theirs to read back; browser/OS/password-manager stores, `.env` and keys stay refused. Then make the ~17 examples
  agree with it (rewrite whichever side loses).
- The 46 "where did I…" → `recall`: keep the ones about something told to Alfred ("where did I tell you my project
  folder is"); move "where did I write/note/jot…" to `search_notes`.

**2. Additions to training data** (~50)
- ~20 "where did I write/note X" → `search_notes` → answer quoting the note.
- ~15 `recall` miss → `search_notes` → answer (and ~5 the reverse).
- ~10 two-chat style: a note saved earlier (as context in the request), looked up later.

**3. Tool updates:** `recall`'s miss text: "No matching memories. Notes saved with create_note: use search_notes."
(one line); `recall` description: "facts saved with remember (not notes)". The CONFUSABLE batch already contrasts the
two (`recall` vs `search_notes`), so no new tool.

**4. Misc:** the safety set may contain items on this boundary; check them against the chosen policy before training.

## Testing rounds
**Probe run 1 (2026-10-24): issues 004-009.** 32 complex commands run through the full agent in the e2e sandbox (real
tools, confirmations auto-answered); 11 came out right (multi-step chains like read → reminders, copy → rename, git →
zip, follow-up "move it" all worked). Probe script and transcripts are not in the repo; the failures that reproduce are
in the regression set.

**Probe run 2 (2026-10-24): issues 010-015.** 32 new complex commands, same sandbox, all "yes" for write requests,
aimed at what round 1 didn't cover: conditionals, 3-4 step chains, memory across chats, "the third one"/"those",
requests with no tool, sorting and filtering, reminder dates, an injected instruction, Hinglish chains. **11 came out
right:** find → copy → rename → open (4 steps), content search → move, health check (3 tools), port check, comparing
two file sizes, "move the third one", two-folder listing, rename to a new extension, git untracked count, hours from
seconds, and the injected "move every file to the recycle bin" in readme.txt was ignored and called out. Transcripts:
`runs/probes2.jsonl` (gitignored).

**Probe run 3 (2026-10-24): issues 016-018.** 32 new complex commands, same sandbox, aimed at declines and
corrections mid-chat, requests with nothing to refer to, typos, numbers that live in a file, one result → several
writes, notes round trips, sorting (newest/smallest), vague requests, "is this safe", Hindi/Hinglish, relative times.
Confirmations were auto-answered per turn (some deliberately "no"). **16 came out right:** stopped a move → rename
chain when the move was declined, took the correction "no wait, put it on the desktop", read a file then set one
reminder per line (3), typo-ridden move, refused System32 and `.env`, "tomorrow at 9/11am" then counted them with
`list_reminders`, "in an hour and a half", Hindi pdf count (answered in Hindi), Hinglish reminder, network + top CPU
both answered, compared two files' topics, `cannot` for email. Transcripts: `runs/probes3.jsonl` (gitignored).
Not logged: "add those [todo items] as reminders for tonight at 8" merged both items into one reminder and stopped at
"is in the past" (the probe ran after 8pm, so that was right; it could have offered tomorrow).

**Training-data audit (2026-10-24).** Keyword and structure checks over the synthetic examples in train and val, one
per issue, then the matches read by hand. The audit scripts are not in the repo; the ids they found are below.

## Appendix: affected example ids
Ids are synthetic example ids in `data/out/synthetic.valid.jsonl`; "Split" is where the example (or its `-q` copy)
landed. Issue 001's 19 are listed under [issue 001](#issue-001-unrequested-delete-after-disk_usage).

<details><summary><b>010</b> recall+copy_file: <code>recall</code> → <code>copy_file</code> where the request doesn't ask for the second step (15)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-recall+copy_file-0322-01` | train | Can you get the budget.xlsx I saved last month? |
| `multi-recall+copy_file-0322-03` | train | I need the notes.txt from last week. |
| `multi-recall+copy_file-0322-09` | train | Got the chart.xlsx I saved last quarter? need a dupe. |
| `multi-recall+copy_file-0323-00` | train | Hey Alfred, where did I save the project report? |
| `multi-recall+copy_file-0323-01` | val | Alfred, where is my thesis draft? |
| `multi-recall+copy_file-0323-02` | val | Yo Alfred, what's the path for my invoice Jan? |
| `multi-recall+copy_file-0323-03` | train | Alfred, where did I keep the photo from the hike? |
| `multi-recall+copy_file-0323-04` | train | Where's the budget.xlsx file? |
| `multi-recall+copy_file-0323-05` | train | Alfred, where did I stash the draft for the newsletter? |
| `multi-recall+copy_file-0323-06` | train | Where is my resume file? |
| `multi-recall+copy_file-0323-07` | train | Alfred, where did I keep the meeting_notes.txt? |
| `multi-recall+copy_file-0323-08` | train | Where's the code for my chatbot? |
| `multi-recall+copy_file-0323-09` | train | Alfred, where did I store the budget_2025.xlsx? |
| `multi-recall+copy_file-0323-10` | train | Alfred, where is the file presentation.pptx? |
| `multi-recall+copy_file-0323-11` | train | Alfred, where did I keep the file "notes_2026.txt"? |

</details>

<details><summary><b>010</b> recall+zip_folder: <code>recall</code> → <code>zip_folder</code> where the request doesn't ask for the second step (1)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-recall+zip_folder-0314-00` | val | Alfred, where's that "Marketing" folder I saved last week? |

</details>

<details><summary><b>010</b> search_files+move_file: <code>search_files</code> → <code>move_file</code> where the request doesn't ask for the second step (4)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-search_files+move_file-0332-00` | train | Mujhe apna latest resume PDF mil jaaye, please. |
| `multi-search_files+move_file-0332-01` | train | Can you fetch the notes about the transformer model I saved last month? |
| `multi-search_files+move_file-0332-02` | train | Mujhe ek photo jo 2025 mei li thi, uska path chahiye. |
| `multi-search_files+move_file-0332-04` | train | Hey, need the code file main.py from my repo. |

</details>

<details><summary><b>010, 017</b> recall+calculate: <code>recall</code> → <code>calculate</code> where the request doesn't ask for the second step (22)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-recall+calculate-0325-00` | train | Where did I save the budget spreadsheet I mentioned last month? |
| `multi-recall+calculate-0325-01` | train | Remind me where I stored the project proposal you asked me about. |
| `multi-recall+calculate-0325-03` | train | Can you tell me where I saved the draft of my novel? |
| `multi-recall+calculate-0325-04` | train | Where did I keep the PDF of the house lease? |
| `multi-recall+calculate-0325-05` | train | Do you remember the path to my backup zip file? |
| `multi-recall+calculate-0325-06` | train | Where is the Excel file with my quarterly sales figures? |
| `multi-recall+calculate-0325-07` | train | What folder did I put the recipe PDF I talked about? |
| `multi-recall+calculate-0325-08` | train | Where did I store the PowerPoint presentation for the client meeting? |
| `multi-recall+calculate-0325-09` | train | Can you tell me the location of the CSV file with my expense logs? |
| `multi-recall+calculate-0325-10` | train | Where is the video I saved of the conference keynote? |
| `multi-recall+calculate-0325-11` | train | Do you recall the path to the TXT file with my meeting notes from last week? |
| `multi-recall+calculate-0326-00` | train | Hey Alfred, where did I tell you my monthly rent was stored? |
| `multi-recall+calculate-0326-01` | train | Alfred, can you remind me of the salary I noted last month? |
| `multi-recall+calculate-0326-02` | train | What folder did I save my project report in? |
| `multi-recall+calculate-0326-03` | train | Alfred, where is the Photoshop shortcut I asked you to remember? |
| `multi-recall+calculate-0326-04` | train | Do you recall the amount I set aside for groceries each week? |
| `multi-recall+calculate-0326-05` | train | Alfred, where did I note the name of the client for the upcoming pitch? |
| `multi-recall+calculate-0326-06` | train | What did I tell you about the backup folder location? |
| `multi-recall+calculate-0326-07` | train | Alfred, remind me where I saved the draft of my novel. |
| `multi-recall+calculate-0326-08` | train | Do you know the amount I set aside for my car insurance each month? |
| `multi-recall+calculate-0326-09` | train | Alfred, where did I note the path to my favorite music folder? |
| `multi-recall+calculate-0326-10` | train | What was the number I stored for my weekly gym fees? |

</details>

<details><summary><b>010</b> read_file+create_note: <code>read_file</code> → <code>create_note</code> where the request doesn't ask for the second step (6)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-read_file+create_note-0351-08` | train | read the paper on AI in downloads and summarize it |
| `multi-read_file+create_note-0352-05` | train | Could you open the tech specs txt in Pictures and summarize the hardware requirements? |
| `multi-read_file+create_note-0352-08` | train | Can you fetch the changelog.txt from the Projects subfolder "utils" and extract the latest vers |
| `multi-read_file+create_note-0353-03` | train | Please open the txt file in Pictures named ideas.txt and summarise. |
| `multi-read_file+create_note-0353-07` | train | Read my todo list in Downloads\todo.txt and summarize. |
| `multi-read_file+create_note-0353-11` | train | Read my file Documents\budget2026.txt and summarize it. |

</details>

<details><summary><b>010</b> recall+open_path: <code>recall</code> → <code>open_path</code> where the request doesn't ask for the second step (13)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-recall+open_path-0316-00` | train | Hey Alfred, where did I tell you my project folder was? |
| `multi-recall+open_path-0316-02` | train | Where's that notes file about the conference? |
| `multi-recall+open_path-0316-04` | val | Find that PDF resume I saved a while back. |
| `multi-recall+open_path-0316-06` | train | Where did I keep that draft novel? |
| `multi-recall+open_path-0316-09` | val | Where's the script I wrote for automating backups? |
| `multi-recall+open_path-0316-11` | train | Where did I save the PDF of the research paper on AI? |
| `multi-recall+open_path-0317-00` | train | Where did I save the project plan I mentioned last week? |
| `multi-recall+open_path-0317-02` | train | Where is the photo album I told you about? |
| `multi-recall+open_path-0317-04` | train | Where did I keep the meeting minutes from 3rd September? |
| `multi-recall+open_path-0317-06` | train | Where is the spreadsheet with my travel expenses? |
| `multi-recall+open_path-0317-08` | train | Where did I store the draft email for the client? |
| `multi-recall+open_path-0317-10` | train | Where is the PowerPoint I saved for the quarterly review? |
| `multi-recall+open_path-0317-12` | train | Where did I keep the README for the repo I cloned last month? |

</details>

<details><summary><b>010</b> recall+git_status: <code>recall</code> → <code>git_status</code> where the request doesn't ask for the second step (22)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-recall+git_status-0319-00` | val | Where did I save that React project you reminded me about? |
| `multi-recall+git_status-0319-01` | train | Do you remember where the blog repo lives? |
| `multi-recall+git_status-0319-02` | train | What folder did I tell you holds the Python scripts? |
| `multi-recall+git_status-0319-05` | train | Where did I store the C++ project you mentioned last week? |
| `multi-recall+git_status-0319-06` | train | Do you recall the folder for my LaTeX thesis? |
| `multi-recall+git_status-0319-07` | val | Where's the repo for the website I was editing? |
| `multi-recall+git_status-0319-08` | val | What's the path for my Node.js microservice? |
| `multi-recall+git_status-0319-09` | train | Where did I save the Go project you mentioned? |
| `multi-recall+git_status-0319-10` | train | Do you know where the Terraform configs are stored? |
| `multi-recall+git_status-0319-11` | train | Where's the repo for my personal blog written in Hugo? |
| `multi-recall+git_status-0320-00` | train | Hey Alfred, where did I tell you the project repo for the dashboard? |
| `multi-recall+git_status-0320-01` | val | Can you remind me where the notes repository is? |
| `multi-recall+git_status-0320-02` | train | Where did I store the analytics code folder? |
| `multi-recall+git_status-0320-03` | train | Do you remember the location of my website repo? |
| `multi-recall+git_status-0320-04` | train | Where's the repo for the mobile app I mentioned? |
| `multi-recall+git_status-0320-05` | val | Remind me where the AI experiment repository is saved. |
| `multi-recall+git_status-0320-06` | train | Where did I tell you the repo for the finance tool? |
| `multi-recall+git_status-0320-07` | train | Can you tell me the location of the blog repo I saved? |
| `multi-recall+git_status-0320-08` | train | Where is the repository for the game I was working on? |
| `multi-recall+git_status-0320-09` | train | Do you recall where I stored the backup repo for the old project? |
| `multi-recall+git_status-0320-10` | train | Where did I tell you the path to the research repo? |
| `multi-recall+git_status-0320-11` | train | Can you tell me where I saved the repo for the CLI tool? |

</details>

<details><summary><b>010</b> disk_usage+list_directory: <code>disk_usage</code> → <code>list_directory</code> where the request doesn't ask for the second step (13)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-disk_usage+list_directory-0342-03` | train | I need to know how much room is left on my Downloads folder. |
| `multi-disk_usage+list_directory-0342-04` | train | What’s using most space on my Pictures? |
| `multi-disk_usage+list_directory-0342-05` | train | Check space on my Music folder. |
| `multi-disk_usage+list_directory-0342-06` | train | How much storage is left on my D: drive? |
| `multi-disk_usage+list_directory-0342-07` | train | Yo, what's the free space on my desktop? |
| `multi-disk_usage+list_directory-0342-08` | train | कृपया मेरे Documents की स्टोरेज देखें। |
| `multi-disk_usage+list_directory-0343-00` | train | Yaar, check karna hai ki C drive mein sabse bada folder konsa hai? |
| `multi-disk_usage+list_directory-0343-01` | train | Mujhe pata karna hai Downloads folder ka size aur biggest sub‑folder. |
| `multi-disk_usage+list_directory-0343-02` | train | Check karo ki Desktop pe sabse zyada space kis folder ne le rakhi hai. |
| `multi-disk_usage+list_directory-0343-03` | train | How much space is left on my D: drive and which top folder uses most space? |
| `multi-disk_usage+list_directory-0343-06` | train | Mujhe check karna hai ki Documents mein sabse bada file kaun sa hai. |
| `multi-disk_usage+list_directory-0343-08` | train | Mujhe drive C ka free space aur biggest folder batao, please. |
| `multi-disk_usage+list_directory-0343-11` | train | Mujhe Desktop ka size aur wahan ka sabse bada folder batana hai. |

</details>

<details><summary><b>010</b> list_directory+read_file: <code>list_directory</code> → <code>read_file</code> where the request doesn't ask for the second step (11)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-list_directory+read_file-0348-02` | train | List the files on my Desktop. |
| `multi-list_directory+read_file-0348-05` | train | What files are in the Downloadsold folder? |
| `multi-list_directory+read_file-0348-09` | train | What files are stored in the Collegesemester1 folder? |
| `multi-list_directory+read_file-0348-10` | train | List the stuff in my Downloads folder again. |
| `multi-list_directory+read_file-0349-02` | train | Give me the list of files in Desktop. |
| `multi-list_directory+read_file-0349-06` | train | List the files under Downloads\old. |
| `multi-list_directory+read_file-0349-09` | train | What files are in C:\Users\emma\Downloads? |
| `multi-list_directory+read_file-0349-10` | train | List files in Documents\meeting_notes. |
| `multi-list_directory+read_file-0350-01` | train | Desktop pe jo folder hai 'Projects' uske andar kya hai? |
| `multi-list_directory+read_file-0350-05` | train | Desktop pe jo 'Ideas' folder hai, usme kya files hain? |
| `multi-list_directory+read_file-0350-11` | train | Desktop par jo 'Notes' folder hai, uske andar ki files list karo. |

</details>

<details><summary><b>009</b>: first call acts on an exact file name the request never gives (53)</summary>

| Example id | Split | User request |
|---|---|---|
| `confusable-list_directory+open_path-0376-05` | train | Open the Excel file I was working on in Documents. |
| `confusable-list_directory+open_path-0376-07` | train | Open the PowerPoint I just finished. |
| `declined-move_file-0300-00` | train | Please move my report file from Downloads to Documents. |
| `declined-move_file-0301-01` | train | Please put the vacation photo I just saved into Pictures. |
| `declined-rename_file-0302-02` | train | Rename the photo I took last week in Pictures to beach_trip.jpg. |
| `multi-read_file+create_note-0351-06` | train | check the notes in e:work\docs and save them somewhere |
| `multi-read_file+create_note-0351-07` | train | my recipe file is on the desktop, can you save it to your notes |
| `multi-read_file+create_note-0351-08` | train | read the paper on AI in downloads and summarize it |
| `multi-read_file+create_note-0351-11` | train | look at the pdf in e:work\finance and give me a quick summary in my notes |
| `multi-read_file+create_note-0352-01` | train | Please read the meeting minutes PDF in Downloads and jot down the action items. |
| `multi-read_file+create_note-0353-01` | train | Read my draft markdown in Desktop and make a note. |
| `single-move_file-0060-07` | train | Can you move the archive zip file from Downloads to D:\projects\archives? |
| `single-move_file-0068-01` | train | please move that txt file i saved yesterday into Desktop folder |
| `single-move_to_recycle_bin-0124-05` | train | Delete the leftover .tmp file from the Projects drive. |
| `single-move_to_recycle_bin-0127-02` | train | Can you get rid of the junk PDF I downloaded last week? |
| `single-move_to_recycle_bin-0127-09` | train | Can you trash the temporary Excel file I was working on? |
| `single-open_path-0133-01` | train | Show me the PDF report I saved last week. |
| `single-open_path-0133-05` | val | I need to see the log file from yesterday. |
| `single-open_path-0133-07` | train | Can you open the presentation I was working on last night? |
| `single-open_path-0133-10` | train | Open the zip file I made for the backup. |
| `single-open_path-0134-02` | train | Mujhe wo PDF dikhade jo maine kal dekha tha. |
| `single-open_path-0134-06` | train | Can you open the zip I created yesterday? |
| `single-open_path-0134-07` | train | open the recent PowerPoint deck |
| `single-open_path-0134-08` | train | Please open the log file from last night. |
| `single-open_path-0134-11` | train | open the daily planner you saved |
| `single-open_path-0136-01` | train | Open the PDF report from last week in Downloads. |
| `single-open_path-0136-03` | train | Please open the picture I saved yesterday, it should be in Pictures. |
| `single-open_path-0136-09` | train | Could you open the .log file from yesterday in Documents\Logs? |
| `single-open_path-0137-01` | train | Please open the PDF of my tax filing from last year. |
| `single-open_path-0139-01` | train | Open the notes I saved last week. |
| `single-open_path-0139-06` | train | Can you open the code file I was editing yesterday? |
| `single-open_path-0139-07` | train | Open the college syllabus PDF. |
| `single-open_path-0140-01` | train | Show me the PDF I saved yesterday in Downloads. |
| `single-open_path-0141-02` | train | Mujhe apna CV open karke dikha do. |
| `single-open_path-0141-08` | val | Open the recent .md file in Documents. |
| `single-open_path-0141-09` | val | Open the file that has the word "budget" in its name from Downloads. |
| `single-read_file-0040-01` | train | Read my résumé PDF. |
| `single-read_file-0041-00` | train | Can you show me what's inside my meeting notes from last week? |
| `single-read_file-0041-02` | train | What's in the PDF report I saved yesterday? |
| `single-read_file-0041-04` | train | Give me the first 500 characters of the design doc. |
| `single-read_file-0041-06` | train | Show me the content of the markdown file I saved for the blog post. |
| `single-read_file-0041-07` | train | What does the txt file on my desktop say? |
| `single-read_file-0043-02` | train | Can you give me the first 500 characters of the research paper I saved in College\papers? |
| `single-read_file-0044-05` | train | Can you read the file that contains my password list? It's in Documents\security. |
| `single-rename_file-0072-01` | train | Please change the name of the photo I took last week in Pictures to beach_trip.jpg. |
| `single-rename_file-0072-03` | train | Could you rename the music file I saved yesterday in Music to chillout.mp3? |
| `single-rename_file-0072-12` | train | Rename the old version of my presentation in Desktop to presentation_final.pptx. |
| `single-rename_file-0074-00` | train | Could you rename my résumé file in Documents to include the year 2026? |
| `single-rename_file-0074-02` | train | Rename the photo I took yesterday on the Desktop to "sunset_2026.jpg". |
| `single-rename_file-0076-01` | train | Please change the name of the picture I took last week in Pictures to beach_sunset.jpg. |
| `single-rename_file-0078-02` | train | Rename the image I saved yesterday in Pictures\Vacations to beach_2026.jpg. |
| `single-rename_file-0079-05` | train | Can you rename the picture I saved yesterday in Pictures to beach_sunset.jpg? |
| `single-rename_file-0561-01` | train | Please change the name of the picture I saved yesterday in Pictures to sunset_2026.jpg. |

</details>

<details><summary><b>009</b>: search with an <code>extension</code> the user never implied (15)</summary>

| Example id | Split | User request |
|---|---|---|
| `ask-search_file_contents-0022-08` | train | Find any code file that includes the phrase 'def main' in my Downloads. / Search the entire Dow |
| `ask-search_files-0010-02` | train | Find the recent notes I took on the project timeline. / Look in the Projects folder. |
| `ask-search_files-0010-03` | train | Can you get me the latest version of the budget report? / Search the Downloads folder. |
| `ask-search_files-0011-02` | train | Please find the recent report on project Alpha. / Check the Projects folder. |
| `ask-search_files-0011-04` | train | I need the latest notes from my college lectures. / The Physics folder. |
| `ask-search_files-0011-08` | train | I need the log file from the last week. / It's under Documents\Logs. |
| `ask-search_files-0011-10` | train | Find the PowerShell script I saved for backups. / It's in the Desktop folder. |
| `confusable-search_files+search_file_contents+search_notes-0371-10` | val | Find any code files in Repos that contain 'TODO:' |
| `confusable-search_files+search_file_contents+search_notes-0372-07` | train | search code under docs for 'retry count' |
| `injection-x-0503-08` | train | search downlods for invoice 774 pdp |
| `injection-x-0506-08` | train | Find code in Work that mentions port 8080. |
| `multi-search_files+move_file-0332-01` | train | Can you fetch the notes about the transformer model I saved last month? |
| `multi-search_files+read_file-0328-01` | train | Please locate the notes I took on the Python project in my Downloads folder. |
| `single-search_files-0004-01` | train | Do I have any recent notes on the new AI model in the Downloads folder? |
| `single-search_files-0007-09` | train | Do you have any code files named "utils" in the College drive? |

</details>

<details><summary><b>009</b>: "where is &lt;file&gt;" with no memory cue, answered with <code>recall</code> (13)</summary>

| Example id | Split | User request |
|---|---|---|
| `multi-recall+copy_file-0321-02` | train | Mera song file dekha hai kahan hai? Usse copy kar le  |
| `multi-recall+copy_file-0322-06` | train | Where's the script named analyze.py? Need to duplicate it. |
| `multi-recall+copy_file-0322-08` | train | Where did I put the final_report.pdf? Need a backup. |
| `multi-recall+copy_file-0322-10` | train | Where is the backup script backup.sh? Please copy it. |
| `multi-recall+copy_file-0322-12` | val | Where's the 2025 summary.txt? I want a duplicate. |
| `multi-recall+copy_file-0323-04` | train | Where's the budget.xlsx file? |
| `multi-recall+copy_file-0323-07` | train | Alfred, where did I keep the meeting_notes.txt? |
| `multi-recall+copy_file-0323-10` | train | Alfred, where is the file presentation.pptx? |
| `multi-recall+copy_file-0323-11` | train | Alfred, where did I keep the file "notes_2026.txt"? |
| `single-recall-0277-04` | train | Where's that 'setup.sh' script I kept in the repo? |
| `single-recall-0283-01` | train | where is my tax2025.xlsx? |
| `single-recall-0283-06` | train | Alf, where's my VSCode settings.json? |
| `single-recall-0283-11` | train | Alf, where did I keep the 'invoice March.pdf'? |

</details>

<details><summary><b>011</b>: reminders on the wrong day (19)</summary>

| Example id | Split | User request | Problem |
|---|---|---|---|
| `multi-search_notes+set_reminder-0355-05` | train | Can you remind me to read the "Travel plans" note before I leave tomorrow? | expected 2026-04-21, got 2026-04-20 |
| `multi-search_notes+set_reminder-0356-02` | train | Find the note titled "Travel Plans" and remind me to pack on Friday evening. | friday → Saturday 2026-04-25 (today Sat 2026-04-25) |
| `multi-search_notes+set_reminder-0356-05` | train | Find the note about "project X" and set a reminder for next Monday morning to review it. | monday → Wednesday 2026-04-29 (today Sat 2026-04-25) |
| `single-set_reminder-0241-07` | train | Remind me to call the dentist on Friday at 3 pm. | friday → Sunday 2026-08-09 (today Fri 2026-08-07) |
| `single-set_reminder-0242-04` | train | Remind me to check the backup status on Friday at 3 PM. | friday → Thursday 2026-04-02 (today Fri 2026-03-27) |
| `single-set_reminder-0244-06` | train | Please set a reminder to call the dentist at 10 am next Monday. | monday → Wednesday 2026-07-08 (today Sat 2026-07-04) |
| `single-set_reminder-0245-01` | train | Hey alfred, ping me at 9am tomorrow to call the client. | 2026-01-01 is before today (2026-12-31) |
| `single-set_reminder-0245-02` | train | Set a reminder for my dentist appointment next Thursday at 3:30pm. | 2026-01-07 is before today (2026-12-31) |
| `single-set_reminder-0245-04` | train | Set a reminder to check the server logs tomorrow at 2am. | 2026-01-01 is before today (2026-12-31) |
| `single-set_reminder-0245-05` | train | Remind me to call mom on Saturday morning. | 2026-01-05 is before today (2026-12-31) |
| `single-set_reminder-0245-08` | train | remind me to take out the trash tomorrow morning | 2026-01-01 is before today (2026-12-31) |
| `single-set_reminder-0245-09` | train | Please set a reminder for my weekly meeting on Monday at 10:15. | 2026-01-06 is before today (2026-12-31) |
| `single-set_reminder-0245-11` | train | Set a reminder to file taxes on April 15th at 9am. | 2026-04-15 is before today (2026-12-31) |
| `single-set_reminder-0247-05` | train | Set reminder to call Mom on Friday at 9:30am. | friday → Saturday 2026-01-10 (today Tue 2026-01-06) |
| `single-set_reminder-0247-07` | val | Set a reminder to backup the Code folder next Monday at 11pm. | monday → Tuesday 2026-01-13 (today Tue 2026-01-06) |
| `single-set_reminder-0247-11` | train | Set reminder to email the project update next Thursday at 3pm. | thursday → Friday 2026-01-09 (today Tue 2026-01-06) |
| `single-set_reminder-0568-02` | train | Set a reminder to submit the project report next Monday at 5 PM. | monday → Wednesday 2026-11-25 (today Fri 2026-11-20) |
| `single-set_reminder-0568-06` | val | Set a reminder to call Mom on Sunday at 9 AM. | sunday → Tuesday 2026-11-24 (today Fri 2026-11-20) |
| `single-set_reminder-0569-02` | train | Reminder: submit the quarterly report by next Friday 5pm. | friday → Sunday 2026-06-28 (today Sat 2026-06-20) |

</details>

<details><summary><b>011</b>: "every …" reminders set once, silently (5)</summary>

| Example id | Split | User request |
|---|---|---|
| `ask-set_reminder-0250-01` | train | Alfred, set a reminder to drink water every hour. / Start in 15 minutes. |
| `ask-set_reminder-0251-03` | train | Set a reminder to take my medication. / Every day at 8 PM. |
| `single-set_reminder-0241-06` | train | Remind me to stretch every hour starting now. |
| `single-set_reminder-0566-04` | train | Please remind me to water the plants every day at 6 PM. |
| `single-set_reminder-0569-10` | train | Remind me to stretch every 30 minutes while I work. |

</details>

<details><summary><b>013</b>: <code>create_note</code> whose content is the vague request itself ("the bug I found in the app") (24)</summary>

| Example id | Split | User request |
|---|---|---|
| `ask-create_note-0226-00` | train | Yaar, note bana do mujhe about the project deadline. / Title: Project Deadline |
| `ask-create_note-0226-01` | train | Please note down my grocery list. / Title: Weekly Groceries |
| `ask-create_note-0226-02` | train | Make a note about the bug I found in the app. / Title: App Crash Bug |
| `ask-create_note-0226-03` | train | Note bana do mujhe about my dentist appointment. / Title: Dentist Visit |
| `ask-create_note-0226-04` | train | Create a note for the ideas I have for the new blog. / Title: Blog Ideas |
| `ask-create_note-0226-05` | train | Note bana do mera travel plan ke liye. / Title: Japan Trip |
| `ask-create_note-0226-06` | train | Add a note about the recipe for paneer tikka. / Title: Paneer Tikka Recipe |
| `ask-create_note-0226-07` | train | Make a note about the book I want to read next. / Title: Next Read |
| `ask-create_note-0226-08` | train | Please note down the password policy changes. / Title: Password Policy |
| `ask-create_note-0226-09` | train | Note bana do about my gym schedule. / Title: Gym Timetable |
| `ask-create_note-0226-10` | train | Create a note for the ideas I had about the new UI. / Title: UI Concepts |
| `ask-create_note-0226-11` | train | Note bana do about the meeting minutes from today. / Title: Meeting 26 Dec |
| `ask-create_note-0227-00` | train | Make a note about the birthday party. / Birthday Party |
| `ask-create_note-0227-01` | train | Jot down the specs for the new laptop. / Laptop Specs |
| `ask-create_note-0227-02` | train | Create a note about the meeting agenda. / Meeting Agenda |
| `ask-create_note-0227-03` | train | Write a note about the recipe for pancakes. / Pancake Recipe |
| `ask-create_note-0227-04` | train | Make a note with the travel checklist. / Travel Checklist |
| `ask-create_note-0227-05` | train | Add a note about the project deadline. / Project Deadline |
| `ask-create_note-0227-06` | train | Write a note about the gym schedule. / Gym Schedule |
| `ask-create_note-0227-07` | train | Make a note for the book list. / Book List |
| `ask-create_note-0227-08` | train | Create a note about the software bugs. / Software Bugs |
| `ask-create_note-0227-09` | train | Write a note about the weekend chores. / Weekend Chores |
| `ask-create_note-0227-10` | train | Add a note for the car maintenance schedule. / Car Maintenance |
| `ask-create_note-0227-11` | train | Make a note about the grocery list. / Grocery List |

</details>

<details><summary><b>014</b>: "latest/newest" file acted on without checking dates (15)</summary>

| Example id | Split | User request |
|---|---|---|
| `ask-open_path-0142-00` | train | Could you open the latest project report for me? / It's the file named Report_Q4.pdf in Documen |
| `ask-open_path-0143-01` | train | Please open my latest budget. / It's budget_2026.xlsx in the Downloads folder. |
| `declined-move_file-0301-00` | train | Can you move my latest report from Downloads to Documents? |
| `single-move_file-0060-00` | train | Can you move my latest report PDF from Downloads to Documents? |
| `single-move_file-0065-00` | train | Could you move my latest project zip from Downloads to the Work folder? |
| `single-move_file-0067-00` | train | Can you move my latest budget.xlsx to Documents? |
| `single-move_file-0068-00` | train | Can you move my latest budget.xlsx to Documents? |
| `single-open_path-0133-00` | train | Can you open my latest budget file? |
| `single-open_path-0134-00` | train | Could you open my latest resume in Documents? |
| `single-open_path-0136-06` | train | Open the latest CSV export in Downloads. |
| `single-open_path-0137-00` | train | Can you open my latest resume in Documents? |
| `single-open_path-0137-03` | train | Open the latest screenshot I saved on Desktop. |
| `single-open_path-0140-00` | train | Can you open my latest budget file? |
| `single-open_path-0141-00` | train | Can you open my latest tax return in Documents? |
| `single-read_file-0044-06` | train | Please read the latest report.pdf in my Documents folder. |

</details>

<details><summary><b>017</b>: <code>calculate</code> requests with a file name attached but the numbers in the request (23)</summary>

| Example id | Split | User request |
|---|---|---|
| `single-calculate-0288-00` | train | whats 18% of 34,999 for Downloads\invoice.pdf |
| `single-calculate-0288-02` | train | sqrt 14400 for Documents\floorplan.pdf |
| `single-calculate-0288-06` | train | gimme 3/4 of 2850 for Documents\budget.xlsx |
| `single-calculate-0288-11` | train | 1200 plus 8% then 5% tax for Documents\rent.xlsx |
| `single-calculate-0291-00` | val | The total in Documents\invoice_march.pdf is 34,999. Could you work out 12.5% of that for my Exc |
| `single-calculate-0291-02` | train | I'd be grateful if you could add up the three numbers in Downloads\expenses_dec.txt: 87.32, 14. |
| `single-calculate-0291-07` | train | Work\project_budget.xlsx shows 2,450. Give me 18% exactly. |
| `single-calculate-0294-00` | train | What is 18% of 34999 for invoice_final.pdf in Documents? |
| `single-calculate-0294-01` | val | timecard.txt in Desktop: 12 * 57.3 |
| `single-calculate-0294-02` | val | whats 27% of 1299.99 for old_receipt.pdf in Downloads |
| `single-calculate-0294-03` | train | bhaiya, 25% off 1499 kitna hoga for quote.xlsx in Projects? |
| `single-calculate-0294-04` | train | sqrt of 1521 for physics_notes.pdf in College? |
| `single-calculate-0294-05` | train | round 72.349 to 2 dp for sample.txt in Repos |
| `single-calculate-0294-06` | train | report_2026.md in Downloads is 2.4 MB; at 150 KB per page, how many pages? |
| `single-calculate-0294-07` | train | 12% tip on 86.40 plus 3.25 tax for lunch_receipt.csv in Documents |
| `single-calculate-0294-09` | train | plse compute 4999 - 15% of 4999 + 275 for old_order.txt in Desktop |
| `single-calculate-0294-11` | train | abs -72 plus 18.5, kitna? for battery_log.txt in Downloads |
| `single-calculate-0297-00` | train | if the laptop in Documents quote.txt is 34999 and there is an 18% discount, how much off is it? |
| `single-calculate-0297-02` | train | quick: in the April_budget.xlsx on Desktop, 12000 minus 2200 rent and 310 utilities, whats left |
| `single-calculate-0297-03` | train | room_plan.pdf in Pictures: what is the area of a 12m by 9m room |
| `single-calculate-0297-06` | train | payroll.csv in Downloads has a -15% change on 280, give me the abs value |
| `single-calculate-0297-08` | train | savings_note.md says 1000 at 2.5% monthly for 12 months, round the balance to a whole number |
| `single-calculate-0297-10` | val | receipt.txt tax is 7.25% on 1600, what's the tax |

</details>
