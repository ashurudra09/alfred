# Training data: to fix before the next training run

Problems found by testing the shipped model (SFT v2 Q4) that trace back to the training data. **Nothing here is
fixed in the data yet**: fixes are collected and applied together before the next training run (see the v3
section of [patch notes](../docs/patch_notes.md)). Each issue has regression items in
[`eval/testsets/regressions.jsonl`](../eval/testsets/regressions.jsonl):
`uv run python -m eval.run --backend local --system <name> --set regressions`.

Current model on the regression set: **2/12** (`eval/reports/alfred-2b-v2-q4_regressions.md`).

| Issue | Found | Symptom | Cause | Regression items | Status |
|---|---|---|---|---|---|
| [001](#issue-001-unrequested-delete-after-disk_usage) | 2026-10-24 | asked which folder is biggest; the model trashed it | 19 bad training examples | `regress-001-*` | to fix |
| [002](#issue-002-sizes-added-without-units) | 2026-10-24 | added 43.6 GB + 230 MB + 131 KB as 43.6 + 230 + 131 | no training example of the pattern | `regress-002-*` | to fix |
| [003](#issue-003-no-tool-for-the-request-uses-a-nearby-write-tool) | 2026-10-24 | "make a folder … name it temp" → `organize_folder` on all of Documents | no "cannot" examples for file actions without a tool | `regress-003-*` | to fix |
| [004](#issue-004-bulk-and-filtered-file-operations-hit-the-whole-folder) | 2026-10-24 (probe) | "move all the pdfs from downloads…" moved **all of Downloads** | 3 bulk-write examples, 7 "except" | `regress-004-*` | to fix |
| [005](#issue-005-date-only-file-searches) | 2026-10-24 (probe) | "files changed in the last 7 days" → `search_files(query="modified")` → "none" | every date search has a name word | `regress-005-*` | to fix |
| [006](#issue-006-date-arithmetic) | 2026-10-24 (probe) | "days until christmas" → `365 - 24` = 341 | 0 date-math examples | `regress-006-*` | to fix |
| [007](#issue-007-multi-part-requests-half-answered) | 2026-10-24 (probe) | "top memory user, and what % of RAM" answered only the first half | 0 `top_processes`/`system_info` → `calculate` chains | – | to fix |
| [008](#issue-008-counting-files-uses-disk_usage) | 2026-10-24 (probe) | "which has more files" → `disk_usage` ×2 → compared free space | 0 counting examples | `regress-008-*` | to fix |
| [009](#issue-009-invented-search-filters) | 2026-10-24 (probe) | "find my cover letter" → `extension="pdf"` (it's a .md) → "not found" | – | `regress-009-*` | to fix |

## Issue 001: unrequested delete after `disk_usage`
**Seen in the web UI:** "what files in my C\work folder are taking up the most space" → `disk_usage("C:\work")`,
then, unasked, `move_to_recycle_bin` on the largest folder. The folder guard refused it (outside the allowed
folders) before any confirmation. Inside an allowed folder the user would have seen a Confirm/Cancel prompt; nothing
can be deleted without it, and deletes only go to the Recycle Bin.

**Cause:** the multi-step generation batch "check what's taking space, then delete the biggest file"
(`data/gen/prompts.py`, `CHAINS`). The teacher sometimes wrote only the first half as the user's request but still
had the assistant delete. `data/validate.py` checks that calls are well-formed and allowed, not that the user asked
for a change. The system prompt line "Changes to files run only after the user confirms them in the app, so call
the tool directly" pushes the same way.

**Fix (planned):**
1. Validator rule: a write tool (move, rename, copy, zip, organize, recycle) is only valid if the user's messages ask
   for that kind of change; violators are dropped.
2. Drop the 19 examples below (all in `train.jsonl`); rewrite the chain prompt so the user's message states both steps.
3. Add counter-examples: size questions answered with `disk_usage` and a summary, no further call.
4. System prompt (contracts v1.1): "Only change files when the user asked for that change."

**Affected examples (19)**, found by: `disk_usage` before `move_to_recycle_bin`, and no delete wording in any user turn.
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

**Cause:** a gap, not bad examples: the training data has **0** conversations chaining `disk_usage` into
`calculate`, and the `disk_usage` result format the data was generated from (`data/gen/formats.py`) shows GB only.

**Fix (planned):**
1. Data: `disk_usage` → `calculate` chains whose results mix GB/MB/KB, converting to one unit in the expression
   (the tool counts in 1024s: `230 MB` → `230/1024` GB).
2. Teach mixed units in the format examples (`formats.py`), so generated `disk_usage` results look like real ones.
3. Tool options (decide before v3; they change what the model sees): mark folders in the `disk_usage` output (e.g. a
   trailing `\`), and/or let `calculate` accept sizes with units (`230 MB + 2 GB`).

## Issue 003: no tool for the request, uses a nearby write tool
**Seen in the web UI:** "make a folder in the Documents folder. name it temp" →
`organize_folder("C:\Users\<user>\Documents", strategy="by_type")`. There is no tool that creates an empty folder.
`organize_folder` would have sorted every loose file in Documents into type subfolders. It needs confirmation and
shows its plan first, so cancelling it was safe, and `/undo` reverses it.

**Cause:** a gap. The `cannot` examples only cover things outside the laptop (web, weather, email, bookings,
settings: `data/gen/prompts.py`, `SCENARIOS["cannot"]`). Nothing teaches "this is a file action, but no tool does it".
The training set has 0 bare "create a folder" requests: the ~27 that mention a new folder all move or copy a file into
it (`move_file`/`copy_file` create the destination), and 4 `direct` examples explain how to make a folder in Explorer
when asked "how do I…". So an imperative "make a folder" lands on the nearest tool that makes folders.

**Same class:** "actually cancel that reminder" → `list_reminders` → "I can't cancel it: it's the only reminder"
(wrong reason; there is no cancel tool) — `regress-003-cancel-reminder`. Still to check: writing or editing a text
file, forgetting a memory, permanently deleting, emptying the Recycle Bin.

**Fix (planned):**
1. Data: add a `cannot` sub-scenario for "file/app actions Alfred has no tool for". The reply says it can't and offers
   what it can do (e.g. move or copy a file into a new folder, which creates it).
2. Tool option (decide before v3, changes the contract): add a `create_folder` tool (confirm-gated, undoable). If
   that's chosen, this regression item flips from `cannot` to a `create_folder` call.

## Probe run (2026-10-24): issues 004-009
32 complex commands run through the full agent in the e2e sandbox (real tools, confirmations auto-answered); 11 came
out right (multi-step chains like read → reminders, copy → rename, git → zip, follow-up "move it" all worked).
Probe script and transcripts are not in the repo; the failures that reproduce are in the regression set.

### Issue 004: bulk and filtered file operations hit the whole folder
- "move all the pdfs from downloads into Documents\papers" → `move_file(source="Downloads")`: the **whole Downloads
  folder** was moved (confirmed in the probe), and the reply said "All PDFs are now in Documents\papers".
- "delete everything in downloads except the pdfs" → `move_to_recycle_bin("Downloads")` (the tool refuses a main
  folder, and it was declined); in the single-step set it proposes `organize_folder` instead.
- "organize my downloads by type but leave setup.exe where it is" → organizes everything, ignoring the exception.
- "rename every pdf so it starts with 2026_" → `search_files(query="2026")` (searched for the new prefix), "none found".

**Cause:** 3 training examples ask for a write on "all/every" files and 7 contain "except/but not"; the model has no
pattern of "search, then act on each result". **Fix (planned):** examples that search/list first, then act per file
(or say how many files and ask); "except" requests answered by listing, or by a `cannot` when a tool can't exclude.
Depends on the call limit (code note below).

### Issue 005: date-only file searches
"which files did I change in the last 7 days?" → `search_files(query="modified", modified_within_days=7)` → "No
matching files" → "I couldn't find any". "older than a month" → `modified_within_days=30` (the opposite) with
query "older". Other probes filled `query` with junk too (once with the sandbox folder's name).
**Cause:** all 56 training searches with `modified_within_days` also name a file word; none use `query="*"`, which
the tool documents as "match everything". Only 1 example says "older than", and no tool supports it.
**Fix (planned):** date-only searches with `query="*"`; "older than" → `cannot` or list + filter. Tool option:
an `older_than_days` argument.

### Issue 006: date arithmetic
"how many days are left until christmas?" → `calculate("365 - 24")` = 341 (right: 62; the single-step set gives
`365 - 2026 - 11`). **Cause:** 0 "days until / how many days" examples; `calculate` has no dates, and the model doesn't
use today's date from the system prompt. **Fix (planned):** examples that build the day count from today's date
(e.g. `(31 - 24) + 30 + 25`).

### Issue 007: multi-part requests half answered
"what's using the most memory right now, and what percent of my total RAM is that?" → `top_processes`, then answered
only the first part. Also: "15% of the total size of my downloads, in MB" → `calculate("disk_usage(...)...")`
(tried to call a tool inside the expression); "find all pdfs in downloads and documents and tell me the largest" → two
good searches, then a pointless third call hit the 3-call limit, so no answer. Given the `top_processes` result in
the single-step set, it does call `system_info`, so no regression item yet. **Cause:** 0 chains of
`top_processes`/`system_info` → `calculate`. **Fix (planned):** chains for "X, and what % of Y".

### Issue 008: counting files uses `disk_usage`
"which has more files, my desktop or my downloads?" → `disk_usage` ×2 → "Desktop has 26.8 GB free, Downloads has
26.8 GB free. Desktop is larger." **Cause:** 0 examples of counting or comparing files. **Fix (planned):**
`list_directory` (or `search_files` for a type) and count.

### Issue 009: invented search filters
"find my cover letter and open it" → `search_files(query="cover letter", extension="pdf")` (the file is
cover_letter.md) → "couldn't locate". Also "which resume is newest" added `modified_within_days=7`; "move
resume_2026.pdf … and old_resume.pdf" (no folder named) assumed Downloads and gave up instead of searching.
**Fix (planned):** examples where the extension/date are left out unless the user says them, and where a file
without a folder is found with `search_files` first.

## Found alongside: code, not data (not fixed)
- **`move_file`/`rename_file` accept a main folder** as the source (issue 004 moved all of Downloads).
  `move_to_recycle_bin` already refuses this ("is one of your main folders").
- **3 tool calls per request** (`MAX_CALLS`, FR4) makes "act on every file" impossible beyond 2 files.
- **`set_reminder` can't parse "in 3 hours 45 minutes"**; the model then told the user to say exactly that.
- **Hidden/system files are listed.** `list_directory` showed `desktop.ini` and the hidden `My Music`/`My
  Pictures`/`My Videos` junctions in Documents, which Explorer and PowerShell `ls` hide. The listing only skips
  names starting with "."; it never checks the Windows Hidden/System attributes (`disk_usage` and the file
  walk are the same). `organize_folder` already skips `.ini`.
