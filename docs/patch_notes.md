# Patch notes

Model versions of Alfred (Qwen3.5-2B + LoRA). Every number is from a report in `eval/reports/`; details in
[decisions.md](decisions.md).

## v3 (planned, not trained)
Data fixes collected from testing, applied together before the next training run. Full write-ups, affected example
ids and regression items: [data/to_fix.md](../data/to_fix.md).

| Issue | Problem in v2 | Planned fix |
|---|---|---|
| 001 | Asked which folder is biggest, then proposed moving it to the Recycle Bin unasked (19 bad training examples) | validator rule "writes only when the user asked", drop the 19, counter-examples, system-prompt rule |
| 002 | Added sizes without converting units (230 MB counted as 230 GB) | `disk_usage` → `calculate` chains with mixed units; realistic size formats in the generator |

Also in the same run: the completed data top-up (finished 2026-10-24; the set grew from 8,963 to 10,037 train and
471 to 529 val examples; every tool except `list_reminders` (199) now has ≥ 200).
**Gate for v3:** the regression set passes, and in-domain, safety, e2e, When2Call and BFCL don't regress.
v2 on the regression set: 2/4.

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
