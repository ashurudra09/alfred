# alfred-2b-v3-q8 on unseen (n=71)

Backend `local` / model `local`, 2026-11-21T20:52:03, commit `2ec2306`. **71 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 81.7% |
| valid_rate | 100.0% |
| decision_accuracy | 98.6% |
| tool_accuracy | 83.1% |
| args_score | 80.4% |
| decision_macro_f1 | 96.7% |
| median TTFT | 1.27 s |
| median total | 3.63 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 98.4% | 99.2% | 63 |
| cannot | 88.9% | 100.0% | 94.1% | 8 |

Weakest expected labels: `todo_list` 0.0%, `clipboard_set` 50.0%, `colorConvert` 50.0%, `countWords` 66.7%, `todo_done` 75.0%, `convertUnits` 85.7%, `calculate` 100.0%, `cannot` 100.0%
