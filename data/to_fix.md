# Training data: to fix before the next training run

Problems found by testing the shipped model (SFT v2 Q4) that trace back to the training data. **Nothing here is
fixed in the data yet**: fixes are collected and applied together before the next training run (see the v3
section of [patch notes](../docs/patch_notes.md)). Each issue has regression items in
[`eval/testsets/regressions.jsonl`](../eval/testsets/regressions.jsonl):
`uv run python -m eval.run --backend local --system <name> --set regressions`.

Current model on the regression set: **2/4** (`eval/reports/alfred-2b-v2-q4_regressions.md`).

| Issue | Found | Symptom | Cause | Regression items | Status |
|---|---|---|---|---|---|
| [001](#issue-001-unrequested-delete-after-disk_usage) | 2026-10-24 | asked which folder is biggest; the model trashed it | 19 bad training examples | `regress-001-*` | to fix |
| [002](#issue-002-sizes-added-without-units) | 2026-10-24 | added 43.6 GB + 230 MB + 131 KB as 43.6 + 230 + 131 | no training example of the pattern | `regress-002-*` | to fix |

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
