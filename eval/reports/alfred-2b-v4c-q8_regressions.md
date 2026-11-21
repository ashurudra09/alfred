# alfred-2b-v4c-q8 on regressions (n=46)

Backend `local` / model `local`, 2026-11-21T20:00:36, commit `2ec2306`. **46 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 84.8% |
| valid_rate | 100.0% |
| decision_accuracy | 95.7% |
| tool_accuracy | 91.3% |
| args_score | 88.7% |
| decision_macro_f1 | 94.6% |
| median TTFT | 1.27 s |
| median total | 3.48 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 97.1% | 100.0% | 98.6% | 34 |
| direct | 100.0% | 100.0% | 100.0% | 4 |
| ask | 100.0% | 100.0% | 100.0% | 2 |
| cannot | 100.0% | 66.7% | 80.0% | 6 |

Weakest expected labels: `list_directory` 50.0%, `cannot` 66.7%, `recall` 66.7%, `calculate` 75.0%, `set_reminder` 75.0%, `ask` 100.0%, `direct` 100.0%, `disk_usage` 100.0%
