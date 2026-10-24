# alfred-2b-v2-q4 on regressions (n=12)

Backend `local` / model `local`, 2026-10-24T20:49:18, commit `674ffd5`. **12 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 16.7% |
| valid_rate | 100.0% |
| decision_accuracy | 75.0% |
| tool_accuracy | 50.0% |
| args_score | 37.0% |
| decision_macro_f1 | 28.6% |
| median TTFT | 1.93 s |
| median total | 4.65 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 75.0% | 100.0% | 85.7% | 9 |
| direct | 0.0% | 0.0% | 0.0% | 1 |
| cannot | 0.0% | 0.0% | 0.0% | 2 |

Weakest expected labels: `calculate` 0.0%, `cannot` 0.0%, `direct` 0.0%, `list_directory` 0.0%, `search_files` 0.0%, `disk_usage` 100.0%
