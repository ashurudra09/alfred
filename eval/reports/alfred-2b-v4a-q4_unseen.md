# alfred-2b-v4a-q4 on unseen (n=80)

Backend `local` / model `local`, 2026-11-18T10:42:27, commit `224f7d4`. **80 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 75.0% |
| valid_rate | 100.0% |
| decision_accuracy | 98.8% |
| tool_accuracy | 80.0% |
| args_score | 74.8% |
| decision_macro_f1 | 96.7% |
| median TTFT | 1.49 s |
| median total | 3.3 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 98.6% | 99.3% | 72 |
| cannot | 88.9% | 100.0% | 94.1% | 8 |

Weakest expected labels: `colorConvert` 28.6%, `files-differ` 42.9%, `todo_list` 50.0%, `hashFile` 57.1%, `todo_done` 60.0%, `countWords` 71.4%, `clipboard_set` 80.0%, `convertUnits` 87.5%
