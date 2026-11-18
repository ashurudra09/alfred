# Run A: why the gain over v3 is small, and what to change (2026-11-18)

Evidence from run A's local evals (STATUS Phase 5), v3's runs, the training data, a Q8 rerun and published work.
Every number here can be reproduced from the files named. Nothing in this note has been changed in code or data.

## What run A changed and what it moved

| Changed in run A | Measured effect |
|---|---|
| Name masking (10% of Alfred, 33% of xLAM / When2Call) | Renamed tools **85.9% vs 59.1%** (p < 0.001). The only large, significant gain. |
| 425 on-policy chats (25 per family, 7.5% of the supervised tokens) | Families with on-policy data: recover_empty 0 -> 3/7, notes_and_reminders 4 -> 7/7, decline_then_continue 4 -> 7/7; a few others -1 or -2 (n = 7, noise). Families without it: unchanged (held-out 18/40 both). |
| Tool 26 + 219 examples | Semantic-search tasks 22/25; occasionally chosen where a name search was needed (in-domain `search_notes-04`, hard `find_then_act-0000`). |
| 179 more injection examples | Security: user task done under attack 97% vs 89%; attacks 2/209 vs 1/209. |

**Run A fails the hard suite in the same ways v3 does.** Buckets from `runs/e2e/*/hard_*.jsonl`, first matching rule:

| Failure mode | v3 | run A |
|---|---|---|
| Refused or said "no tool for that" without trying | 12 | 15 |
| Path wrong (refused as outside the folders, or not found) | 10 | 12 |
| Empty result, did not try another way | 12 | 10 |
| Proposed a wrong change (scripted user declined) | 10 | 8 |
| Acted, wrong end state | 8 | 8 |

The training changes targeted other things (renaming, tool 26, injections), so the dominant failure modes were left
as they were. That is the main reason the gain is small.

## Findings, by expected payoff

### 1. Paths: the model builds long absolute paths by hand and gets them wrong
- 69% of path arguments in both v3's and run A's training data are absolute (`C:\Users\lucas\Documents\...`), so
  the model copies the known-folder root from the system prompt and joins it with what tools return.
- `list_directory` returns bare file names under a root line, so joining is left to the model. Failures seen:
  dropped segment (`...\117\shared\x.xlsx` for `...\117\Desktop\shared\x.xlsx`), misspelled root (`elfred`),
  invented folder (`...\38\recipes`).
- **Quantization makes it worse:** the same run A weights at Q8 pass the 50-task suite **47/50 against 43/50 at
  Q4**; four of the five path slips disappear. In-domain is unchanged (240/249 at both).
- **Fix (no new generation):** (a) tools print paths relative to a known folder (`Desktop\shared\x.xlsx`), every
  item with its full relative path; they already accept that form (MCP instructions); (b) rewrite path arguments
  in the existing training data to the relative form, deterministically; (c) evaluate on Q8, or build Q4 with an
  importance matrix (`llama-imatrix` on Alfred transcripts) and compare. (a) changes the eval environment, so v3
  must be rerun under it for a fair comparison.

### 2. False refusals on multi-item work (about a quarter of hard failures, both models)
- "Rename each file in Desktop\shared..." -> "I can't change file names: I don't have a tool for that" (rename_file
  exists). "Move exactly those files" -> "I won't move files from one folder to another: that can break your system".
- Only **1.5%** of Alfred examples call one write tool more than once (111 of 7,434), and 142 assistant turns
  have more than one call. The skill "repeat the action for every item" is almost absent, and the closest
  well-represented pattern is the `cannot` template ("I can't X: I don't have a tool for that. I can ...").
- Non-call categories (ask, cannot, refuse, direct) are about a third of the data, plus When2Call's 1,740.
  Hammer found an inverse relation between irrelevance-detection data and call accuracy, best at about 10%
  (Section 5.6).
- **Fix:** a generator family for list iteration that is not one of the held-out templates (e.g. "tag every
  photo", "copy each report", "recycle all the .tmp files"), with 3-8 calls each; contrastive near-misses next to
  the existing `cannot` examples (doable bulk request -> act; truly impossible -> cannot). Optionally a DPO/RPO
  pass with pairs (act = chosen, false refusal = rejected): When2Call's RPO beat SFT on both irrelevance and calls.

### 3. Not recovering after an empty result (about a fifth of hard failures)
- Typical: `search_by_meaning("2025 newsletter")` -> nothing -> "Want me to search for a phrase?" instead of
  `search_files`.
- On-policy data is the lever that worked: three families with ~24 examples each gained 3/7. At 425 examples it is
  7.5% of the supervised tokens.
- **Fix:** scale on-policy rollouts in the families still weak (find_then_act 2/7, pick_extreme 3/7,
  memory_then_act 3/7, recover_empty 3/7, all_except 4/7, ask_then_act 4/7) to ~75-100 each, from run A as the
  student (its errors, not v3's). The owner's 2026-11-17 decision already allows scaling per family after run A.

### 4. Training budget is spent on the tool list
- **2.7%** of run A's 24.6M training tokens carry loss (about 0.67M); the rest is the 26-tool list and the system
  prompt, re-read for every example. Validation loss was still falling at the 10.5 h stop (0.1738 -> 0.1722).
- LoRA capacity is not the limit at this size (LoRA Without Regret: rank matters only when the dataset exceeds the
  adapter's capacity; LR about 10x full fine-tuning, which 2e-4 already is; small batches preferred, 8 is fine).
- **Fix:** more passes over the same signal: resume from run A's checkpoint for a second epoch in a new Kaggle
  session, or give part of the examples a shorter tool list (the needed tools plus random distractors, as xLAM
  does) to cut tokens; keep enough full 26-tool examples to match the app.

### 5. Masking: keep it, measure its in-domain cost with run B
- Hammer reports that a large masking ratio slows learning of the in-domain task (Section 5.5, Qwen2-1.5B).
- Run A's in-domain loss against v3 (240 vs 246 of 249) is the size of the Q4/Q8 difference (6 items flip), so it
  may be noise. Run B (same data, unmasked) answers this. If run B is clearly better in-domain, mask only the
  public datasets.

### 6. The gate decision rests on single temperature-0 samples
- Q4 vs Q8 of the same weights flip 6 of 249 in-domain items; the 50-task score moves 43 -> 47. Gate comparisons
  should use the same quantization for both models (v3's Q4 was made by Unsloth on Kaggle, run A's locally) and,
  for the end-to-end suites, the planned pass^k runs.

## Suggested order
1. Cheap, no training: rerun v3 and run A at Q8 on the 50-task and hard suites; try an imatrix Q4 for run A.
2. Path fix in the tools + relative-path rewrite of the training data (rerun v3's baselines under the new tools).
3. List-iteration family + contrastive `cannot` examples; scale on-policy data in the weak families with run A as
   the student.
4. Next training run on that data, resumed or two epochs. Run B can run as planned for the masking attribution.

## Sources
- Hammer: Lin et al., ICLR 2025, [arXiv 2410.04587](https://arxiv.org/abs/2410.04587) (Sections 5.5, 5.6).
- [LoRA Without Regret](https://thinkingmachines.ai/blog/lora/), Thinking Machines, 2025.
- When2Call: Ross et al., NAACL 2025, [arXiv 2504.18851](https://arxiv.org/html/2504.18851v1).
- [On-Policy Distillation](https://www.thinkingmachines.ai/blog/on-policy-distillation/), Thinking Machines, 2025.
- Q8 reports (the analysis scripts were scratch and are not kept):
  `eval/reports/alfred-2b-v4a-q8_indomain.*`, `e2e_alfred-2b-v4a-q8.*`.
