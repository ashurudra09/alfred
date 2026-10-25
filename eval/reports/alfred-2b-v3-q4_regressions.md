# alfred-2b-v3-q4 on regressions (n=46)

Backend `local` / model `local`, 2026-10-25T23:32:19, commit `379a664`. **46 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 73.9% |
| valid_rate | 100.0% |
| decision_accuracy | 93.5% |
| tool_accuracy | 84.8% |
| args_score | 75.7% |
| decision_macro_f1 | 85.9% |
| median TTFT | 0.96 s |
| median total | 2.56 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 97.1% | 97.1% | 97.1% | 34 |
| direct | 80.0% | 100.0% | 88.9% | 4 |
| ask | 100.0% | 50.0% | 66.7% | 2 |
| cannot | 100.0% | 83.3% | 90.9% | 6 |

Weakest expected labels: `search_notes` 0.0%, `ask` 50.0%, `list_directory` 50.0%, `set_reminder` 50.0%, `zip_folder` 50.0%, `recall` 66.7%, `calculate` 75.0%, `cannot` 83.3%
