# alfred-2b-v4c-q8 on unseen (n=71)

Backend `local` / model `local`, 2026-11-21T20:05:24, commit `2ec2306`. **71 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 81.7% |
| valid_rate | 100.0% |
| decision_accuracy | 98.6% |
| tool_accuracy | 85.9% |
| args_score | 82.0% |
| decision_macro_f1 | 96.7% |
| median TTFT | 1.44 s |
| median total | 3.56 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 98.4% | 99.2% | 63 |
| cannot | 88.9% | 100.0% | 94.1% | 8 |

Weakest expected labels: `todo_list` 0.0%, `colorConvert` 50.0%, `hashFile` 66.7%, `clipboard_set` 75.0%, `todo_done` 75.0%, `countWords` 83.3%, `convertUnits` 85.7%, `calculate` 100.0%
