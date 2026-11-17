# alfred-2b-v3-q4 on unseen (n=80)

Backend `local` / model `local`, 2026-11-17T18:58:03, commit `80018f1`. **80 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 80.0% |
| valid_rate | 100.0% |
| decision_accuracy | 98.8% |
| tool_accuracy | 81.2% |
| args_score | 78.5% |
| decision_macro_f1 | 96.7% |
| median TTFT | 1.93 s |
| median total | 5.28 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 98.6% | 99.3% | 72 |
| cannot | 88.9% | 100.0% | 94.1% | 8 |

Weakest expected labels: `todo_list` 0.0%, `colorConvert` 14.3%, `clipboard_set` 60.0%, `todo_done` 80.0%, `countWords` 85.7%, `files-differ` 85.7%, `convertUnits` 87.5%, `calculate` 100.0%
