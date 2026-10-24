# alfred-2b-v2-q4 on regressions (n=4)

Backend `local` / model `local`, 2026-10-24T20:27:51, commit `e84ae85`. **4 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 50.0% |
| valid_rate | 100.0% |
| decision_accuracy | 75.0% |
| tool_accuracy | 75.0% |
| args_score | 66.7% |
| decision_macro_f1 | 42.9% |
| median TTFT | 2.87 s |
| median total | 6.11 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 75.0% | 100.0% | 85.7% | 3 |
| direct | 0.0% | 0.0% | 0.0% | 1 |

Weakest expected labels: `calculate` 0.0%, `direct` 0.0%, `disk_usage` 100.0%
