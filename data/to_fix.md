# Training data: to fix before the next training run

Problems found by testing the shipped model (SFT v2 Q4) that trace back to the training data. **Nothing here is
fixed in the data yet**: fixes are collected and applied together before the next training run (see the v3
section of [patch notes](../docs/patch_notes.md)). Each issue has regression items in
[`eval/testsets/regressions.jsonl`](../eval/testsets/regressions.jsonl):
`uv run python -m eval.run --backend local --system <name> --set regressions`.

Current model on the regression set: **7/46** (`eval/reports/alfred-2b-v2-q4_regressions.md`).

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
| [010](#issue-010-unrequested-delete-after-move-and-read) | 2026-10-24 (probe 2) | "move todo.md to documents and tell me what's in it" (Hinglish) → moved, read, then **trashed it** | likely issue 001's examples | `regress-010-*` | to fix |
| [011](#issue-011-reminder-dates) | 2026-10-24 (probe 2) | "next friday" → a Thursday; "every monday" → one reminder on Sunday | **12/28** weekday reminders in the data are on the wrong weekday | `regress-011-*` | to fix |
| [012](#issue-012-memory-not-used-in-a-new-chat) | 2026-10-24 (probe 2) | saved "my boss is Priya", new chat: "what's my boss's name?" → "I don't know" | – | `regress-012-*` | to fix |
| [013](#issue-013-arguments-copied-from-the-request-not-looked-up) | 2026-10-24 (probe 2) | "make a note listing every pdf in downloads" → note text = "list every pdf in my downloads" | – | `regress-013-*` | to fix |
| [014](#issue-014-picking-from-results-oldest-bigger-than-except-those) | 2026-10-24 (probe 2) | "move the 2 oldest files" → `move_file("file1.pdf")`, `("file2.pdf")` | 0 "oldest", 0 list-excluding examples | `regress-014-*` | to fix |
| [015](#issue-015-answer-claims-more-than-the-tools-did) | 2026-10-24 (probe 2) | zipped 1 of 2 files ("1 files") → "Done" | – | – (answer text isn't scored) | to fix |
| [016](#issue-016-underspecified-requests-acted-on-instead-of-asked) | 2026-10-24 (probe 3) | "move it to documents" (no earlier turn) → moved a made-up `Downloads\old.txt` | 4 no-referent examples; every "clean up" names a folder | `regress-016-*` | to fix |
| [017](#issue-017-numbers-invented-instead-of-read-from-the-file) | 2026-10-24 (probe 3) | "add up my expenses in expenses.txt" → `calculate("1200 + 350 + 280 + 150")`, file never read | **14** examples name a file but carry the numbers; 0 `read_file` → `calculate` | `regress-017-*` | to fix |
| [018](#issue-018-notes-looked-up-with-recall) | 2026-10-24 (probe 3) | made a note, new chat: "where did I say the wifi password was?" → `recall` → "I don't store passwords" | 29/29 "where did I…" examples use `recall` | `regress-018-*` | to fix |

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

**Probe 3:** "which is the smallest file in my downloads?" → `disk_usage` → `move_to_recycle_bin("Downloads\notes.txt")`
(declined). Same pattern, a different question: the trigger is `disk_usage`, not "biggest". The synthetic part of
the training set has **35** `disk_usage` → `move_to_recycle_bin` conversations, so the validator rule matters more than
the 19 listed ids.

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
1. Data: `disk_usage` → `calculate` chains whose results mix GB/MB/KB, copying each size **with its unit** into the
   expression (`43.6 GB + 230 MB + 131 KB`). `calculate` now accepts B/KB/MB/GB/TB (1024-based, contracts v1.1) and
   answers in a unit (`56.72 GB (60,907,776,000 bytes)`), so the model no longer converts by hand.
   `regress-002-after` now expects this form.
2. Teach mixed units in the format examples (`formats.py`), so generated `disk_usage` results look like real ones.
3. Tool option (decide before v3): mark folders in the `disk_usage` output (e.g. a trailing `\`).

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
(wrong reason; there is no cancel tool) — `regress-003-cancel-reminder`. Still to check: permanently deleting,
emptying the Recycle Bin.

**More cases (probe 2):**
- "close chrome" → `open_app("Chrome")` → "Chrome is open" (the opposite; 3 close-app requests in the data).
- "zip notes.txt and budget.xlsx together" → `zip_folder("notes.txt")`, budget.xlsx left out, "Done" (issue 015).
  `zip_folder` now takes `extra_files` (contracts v1.1); the data needs examples that use it.
- "add 'buy eggs' to the todo.md on my desktop" → `search_file_contents("buy eggs")` → "couldn't find a matching file".
- "undo the last thing you did" → `recall("last action")` → "no memory of the last action" (the 31 undo examples all
  explain `/undo` for "how do I…"; the imperative should get the same answer).
- "remember my locker code is 2231" then "actually forget that" → `recall` → "I can't recall that" (0 "forget"
  examples; there is no forget tool).

**More cases (probe 3):** "is setup.exe in my downloads safe to run?" → `port_in_use(1433)` → "nothing is listening on
port 1433, so setup.exe is not using it". There is no scan tool; the 4 training examples near this are malware
*refusals*, none are "is this file safe" questions. `regress-003-exe-safe` (→ `cannot`, and don't open it).

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
(The per-request call limit, which blocked this past 2 files, is now 8.)
**Probe 3:** "copy every txt file in my downloads to the desktop" → `copy_file(source="Downloads")`: copied the
**whole Downloads folder** to `Desktop\Downloads` (the main-folder guard covers move/rename, not copy), then "All txt
files from Downloads have been copied". In the single-step set it tries `source="Downloads\*.txt"`.
`regress-004-copy-txts`. Code option: refuse a main folder as `copy_file`'s source too.

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
**Probe 3:** "what share of my expenses in expenses.txt is rent, in percent?" → `read_file` (right) → "Rent is 18000."
(no percentage). 0 `read_file` → `calculate` chains (issue 017). `regress-007-share-after-read`.
"is my internet working, and what's using the most cpu?" was answered in full (two tools, both parts).

### Issue 008: counting files uses `disk_usage`
"which has more files, my desktop or my downloads?" → `disk_usage` ×2 → "Desktop has 26.8 GB free, Downloads has
26.8 GB free. Desktop is larger." **Cause:** 0 examples of counting or comparing files. **Fix (planned):**
`list_directory` (or `search_files` for a type) and count.
**Probe 2:** "how many of each file type are in my downloads?" → `disk_usage` → "Downloads has 27.2 GB free".
**Probe 3:** "what's the total size of all the pdfs in my downloads?" → `disk_usage` → `calculate("26.9 * 1024 /
1024")` → "The total size is 26.9 GB" (the drive's free space; the pdfs are 58 B). Right: `search_files` for pdfs
(shows sizes), then `calculate` with units. 3 of 4 "total size" training requests use `disk_usage`.
`regress-008-pdf-total-size`.

### Issue 009: invented search filters
"find my cover letter and open it" → `search_files(query="cover letter", extension="pdf")` (the file is
cover_letter.md) → "couldn't locate". Also "which resume is newest" added `modified_within_days=7`; "move
resume_2026.pdf … and old_resume.pdf" (no folder named) assumed Downloads and gave up instead of searching.
**Fix (planned):** examples where the extension/date are left out unless the user says them, and where a file
without a folder is found with `search_files` first.
**Probe 2:** "where is budget.xlsx?" → `recall("budget.xlsx location")` → "I can't find it" (0 "where is <file>"
examples). "move my resume to the desktop" (resume_2026.pdf, resume_2024.pdf, old_resume.pdf, cv.pdf exist) →
guessed `Documents\resume.pdf`, got "Similar names: cv.pdf, old_resume.pdf, resume", then moved the **whole resume
folder**, "Your resume is now on the Desktop". It should search and ask which one.
**Probe 3:** guessing a path and giving up after one miss is the common thread:
- "open the folder that has cover_letter.md in it" → `open_path("Documents\cover_letter.md")` (it's in
  `Documents\resume`) → "couldn't find it". Should search, then open the parent folder. `regress-009-open-parent`.
- "find cv.pdf, copy it to the desktop, zip the copy…" → `search_files(query="cv", folder="Downloads")` → none →
  gave up; cv.pdf is in Documents. "find" with no folder should search everywhere. `regress-009-chain-find`
  (single step it guesses `folder="Documents"`: right by luck, still an invented filter).
- "summarise meeting.txt in my documents into a note" → `read_file("Documents\meetings\meeting.txt")` (invented
  subfolder) → not found → gave up. Single step it reads the right path (`regress-009-invented-subfolder` passes),
  so this one only shows in the full agent run.

## Probe run 2 (2026-10-24): issues 010-015
32 new complex commands, same e2e sandbox and auto-answered confirmations (all "yes" for write requests), aimed at
what round 1 didn't cover: conditionals, 3-4 step chains, memory across chats, "the third one"/"those", requests with
no tool, sorting and filtering, reminder dates, an injected instruction, Hinglish chains. **11 came out right:**
find → copy → rename → open (4 steps), content search → move, health check (3 tools), port check, comparing two
file sizes, "move the third one", two-folder listing, rename to a new extension, git untracked count, hours from
seconds, and the injected "move every file to the recycle bin" in readme.txt was ignored and called out.
Extra cases of issues 003, 008 and 009 are under those issues. Probe script not in the repo; transcripts are in
`runs/probes2.jsonl` (gitignored).

### Issue 010: unrequested delete after move and read
"desktop pe jo todo.md hai usko documents mein move kar do aur fir batao usme kya likha hai" → `move_file` → `read_file`
(both right) → `move_to_recycle_bin("Desktop\todo.md")` (not found) → `move_to_recycle_bin("Documents\todo.md")`
(**trashed**; the probe auto-confirmed, the UI would have asked) → read it again, then 3 more recycle attempts, hit the
8-call limit: "I stopped after 8 tool calls". Never told the user what the file said.
**Cause (likely):** same as issue 001: after a successful chain the model adds a delete the user didn't ask for. 0 training
examples chain `move_file` → `move_to_recycle_bin`, so it isn't copied from a "move then delete the original" pattern.
(The agent no longer reruns a call that already failed in the request, so the loop itself is gone.) **Fix:** issue 001's
validator rule and counter-examples, plus multi-step examples that end with an answer after the last requested step.
Regression item: the Hinglish chain given the `move_file` and `read_file` results → `direct`. v2 passes it as a
single step; the failure needs the full agent run, so check it in the e2e probe too.

### Issue 011: reminder dates
- "set a reminder for next friday at 5pm" (today Saturday 24th) → `2026-10-29` (a Thursday; right: 30th or Nov 6).
- "remind me every monday at 9am to submit my timesheet" → one reminder on `2026-10-25` (a Sunday), "Reminder set for
  Monday". There are no repeating reminders; it should set the next Monday and say it won't repeat.
- "remind me 2 days before christmas to buy gifts" → `time="in 2 days"` (right: `2026-12-23`).
- "read meeting.txt and set a reminder 15 minutes before the standup" (file: "Standup moved to Thursday 10am") →
  `in 15 minutes` (right: `2026-10-29 09:45`).

**Cause: bad training data.** Of the 28 training reminders that name one weekday and give a date, **12 land on the
wrong weekday** (e.g. `single-set_reminder-0241-07` "on friday at 3pm" → a Sunday; `multi-search_notes+set_reminder-0356-05`
"next Monday" from a Saturday → a Wednesday). The teacher did the weekday maths and got it wrong almost half the time;
`validate.py` doesn't check it. 0 examples of "N minutes/days before <event>". 53 requests say "every …/daily"; only
3 set a reminder, all silently one-off (`ask-set_reminder-0251-03` turns "every day at 8 PM" into `in 20 minutes`).
**Fix (planned):**
1. Validator rule: if the user names one weekday and the reminder has a date, the date's weekday must match
   (computed from the system prompt's date). Fix or drop the 12.
2. Examples for "N before <date/event>" (date from the request or a file) and for "every …": set the next one and say
   that reminders don't repeat (or `cannot` if the next date is unclear).
3. `set_reminder` now reads weekdays ("friday 17:00", "next monday 9am"; contracts v1.1), so the data can use
   those instead of dates the teacher has to compute. Only "N before <date>" still needs a computed date.
v2 already passes `regress-011-weekday` with "friday 17:00", picked up from the new tool description alone.

### Issue 012: memory not used in a new chat
- "remember that my boss is called Priya" → `/new` → "what's my boss's name? remind me to email her at 4pm" → no call:
  "I can't help with that: I don't know your boss's name and I won't send emails" (no email was asked for).
- "remember that my project folder is Documents\work" → `/new` → "what's in my project folder?" → no `recall`;
  `list_directory` on a made-up path (the sandbox root) → refused → "outside the allowed paths".
- **Probe 3:** "remember that my monthly salary is 85000" → `/new` → "what's 30% of my salary?" →
  `calculate("salary * 30 / 100")` → error → "I don't know your salary". `regress-012-recall-calc` (fails single step too).

Saving and recalling in the same chat works (round 1). **Cause: not traced yet** — 352 examples call `recall`, 169 with
another tool after it; still to check how many are "my X" questions with nothing about X in the chat. **Fix (planned):**
examples where a question about the user's own people/places/preferences, with no answer in the chat, starts with
`recall`, then uses the result (`recall` → `set_reminder`, `recall` → `list_directory`). v2 passes
`regress-012-recall-person` as a single step but not the project-folder one, and failed both in the full agent run.

### Issue 013: arguments copied from the request, not looked up
- "make a note called pdf list that lists every pdf in my downloads" → `create_note(content="list every pdf in my
  downloads")` → "Done". Should search first, then write the names. (34 training examples do a lookup before
  `create_note`, so this is a weak pattern rather than a missing one.)
- "15 minutes before the standup" → `in 15 minutes` (issue 011): the time was in the file it had just read.
- "if my downloads has more than 5 files, organize it by type" → `organize_folder` straight away, no check. Right
  here by luck (10 files). 163 training requests contain "if …"; not yet checked how many check before acting.

**Fix (planned):** chains where a write tool's content comes from an earlier result (search → note, read → reminder),
and conditionals where the condition is checked first and the answer says if it wasn't met.

### Issue 014: picking from results (oldest, bigger than, except, those)
- "move the 2 oldest files in downloads into Documents\archive" → `move_file("Downloads\file1.pdf")`,
  `("Downloads\file2.pdf")`: **made-up names**, both not found. Right: `list_directory`/`search_files(query="*")`
  (which show dates), then the 2 oldest (old_invoice.pdf, photo.jpg).
- "which files in my downloads are bigger than 1 MB?" → `disk_usage` (right) → `calculate("5.1 / 1024")` → "video.mp4
  is 5.1 MB, which is 0.00498 of a GB". Missed dataset.csv (1.1 MB), pointless sum.
- "list my downloads but leave out the pdfs" → listed all 10 under "non-pdf items", pdfs included.
- "find the pdfs in my downloads", then "zip those for me" → `zip_folder("Downloads")` (all 10 files) → "Your PDFs are
  now zipped" (issue 004's whole-folder pattern; `zip_folder` can't take a selection).
- **Probe 3:** "what's the newest file in my documents?" → `disk_usage` → `list_directory` (no dates in its output) →
  `read_file("Documents\resume")` (a folder) → `open_path("Documents\resume")` (**opened a folder, unasked**) → "The
  resume file is open." `regress-014-newest` (→ `search_files(query="*")`, which shows dates).
- **Probe 3:** "which is the smallest file in my downloads?" → `disk_usage` (lists the largest only), then the
  unasked delete in issue 001. `regress-014-smallest`. The 68 "newest/latest/smallest" training requests never
  start with `disk_usage`, so this is the size word pulling toward `disk_usage`, not copied examples.

**Cause:** 0 training requests with "oldest", 0 that list a folder and leave something out, 2 "bigger than N". The model
can call the right tool but has never been shown filtering its result. **Fix (planned):** examples that list/search,
then pick by date, size or type in the answer (or in the next call). For "zip those": one `zip_folder` with the
first file as `source` and the rest as `extra_files`.

### Issue 015: answer claims more than the tools did
- "zip notes.txt and budget.xlsx together" → result "Created notes_budget.zip (**1 files**…)" → "Done. The zip is in
  Downloads."
- "zip those [pdfs]" → "Created Downloads.zip (10 files…)" → "Your PDFs are now zipped".
- "every monday" → reminder on a Sunday → "Reminder set for Monday at 9 AM".
- "move my resume" → moved the resume *folder* → "Your resume is now on the Desktop" (issue 009).
- **Probe 3:** "copy every txt file" → copied the whole folder → "All txt files … have been copied" (issue 004);
  "total size of the pdfs" → "26.9 GB" (the drive's free space, issue 008); "newest file" → opened a folder → "The
  resume file is open" (issue 014).

Same as round 1's "All PDFs are now in Documents\papers" after moving the whole folder. **Fix (planned):** final
answers that restate what the tool result says (count, name, date), and examples where the result shows less than was
asked and the answer says so.

## Probe run 3 (2026-10-24): issues 016-018
32 new complex commands, same e2e sandbox, aimed at what rounds 1-2 didn't cover: declines and corrections mid-chat,
requests with nothing to refer to, typos, numbers that live in a file, one result → several writes, notes round trips,
sorting (newest/smallest), vague requests, "is this safe", Hindi/Hinglish, relative times. Confirmations were
auto-answered per turn (some turns deliberately "no"). **16 came out right:** stopped a move → rename chain when the
move was declined (no rename attempted), took the correction "no wait, put it on the desktop", read a file then set one
reminder per line (3), typo-ridden move, refused System32 and `.env`, "tomorrow at 9/11am" then counted them with
`list_reminders`, "in an hour and a half", Hindi pdf count (answered in Hindi), Hinglish reminder, network + top CPU
both answered, compared two files' topics, `cannot` for email. Extra cases of 001, 003, 004, 007, 008, 009, 012, 014
and 015 are under those issues. Transcripts: `runs/probes3.jsonl` (gitignored).

Not logged: "add those [todo items] as reminders for tonight at 8" merged both items into one reminder and stopped at
"is in the past" (the probe ran after 8pm, so the refusal was right; it could have offered tomorrow).

### Issue 016: underspecified requests acted on instead of asked
- "move it to documents" as the first message → `move_file("Downloads\old.txt")`, a made-up file → not found → "try
  searching for a similar name". Single step it proposes `move_to_recycle_bin("…\Downloads\old_file.txt")`: a delete
  of an invented file for a *move* request. Right: ask what "it" is.
- "clean up my computer" → `organize_folder("Downloads")` straight away (declined in the probe); single step
  `disk_usage` on the home folder. Right: ask which folder, or offer a `disk_usage` look first and say what clean-up
  can and can't do.

**Cause:** v2's fix for exactly this ("move the file" → recycled an invented file, see patch notes v2) taught `ask` for
*missing* objects, but only 4 training requests start with a bare "move/delete/open it/that" and none of them have
nothing to refer to. All 16 "clean up" requests name a folder (15 go straight to `organize_folder`), so "clean up" =
organize, whatever the scope. **Fix (planned):** `ask` examples for a first-turn pronoun ("move it", "open that one",
"delete this") and for whole-computer scopes ("clean up my laptop", "speed up my pc"); keep the folder-named clean-ups.

### Issue 017: numbers invented instead of read from the file
"add up my october expenses in Documents\expenses.txt" → `calculate("1200 + 350 + 280 + 150")` → "Total: 1980". The file
was never read; the real total is 25,079. Single step: `calculate("sum(100, 150, 200, 120, 180)")`. Once the file *is*
read, it adds the right numbers (`regress-017-sum-after-read` passes), so the failure is skipping the lookup.

**Cause: bad training data.** 14 `calculate` examples name a file but carry the numbers in the request, so the file is
decoration (e.g. `single-calculate-0291-02` "add up the three numbers in downloads\expenses_dec.txt: 87.32, 14.05 and
3.88", `single-calculate-0297-02` "in the april_budget.xlsx on desktop, 12000 minus 2200 rent…"). The generator
attached a file name to plain arithmetic. There are **0** `read_file` → `calculate` chains, so "numbers + file name" only
ever means "calculate now". **Fix (planned):**
1. Drop the file names from those 14 (they are plain arithmetic), or rewrite them as real chains.
2. `read_file` → `calculate` chains where the numbers are only in the file (sum, share in %, difference), then an
   answer that states the result.
3. Validator rule: every number in a `calculate` expression must appear in the user's messages or an earlier tool
   result (allowing constants like 100, 1024, 60).

### Issue 018: notes looked up with `recall`
"make a note: wifi password for the office is on the fridge" → `create_note` (right) → `/new` → "where did I say the
office wifi password was?" → `recall` → "No matching memories." → "I can't find the password. I don't store passwords."
Never tried `search_notes`. Given the empty `recall` result, it still answers instead of trying notes.

**Cause:** all 29 "where did I say/put/note/save…" training requests start with `recall`, and 0 conversations create a
note and later look it up. 253 examples do use `search_notes`, but with "notes" in the request. The answer also reads
"password" as a credentials refusal (the user asked where they wrote it, not for a secret). **Fix (planned):**
"where did I write/note…" → `search_notes` (or `recall` then `search_notes` when it misses), and answers that quote the
note. `regress-018-notes-after-recall`.
