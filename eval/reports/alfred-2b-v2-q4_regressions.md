# alfred-2b-v2-q4 on regressions (n=46)

Backend `local` / model `local`, 2026-10-25T23:46:10, commit `379a664`. **46 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 15.2% |
| valid_rate | 100.0% |
| decision_accuracy | 71.7% |
| tool_accuracy | 39.1% |
| args_score | 26.2% |
| decision_macro_f1 | 29.4% |
| median TTFT | 1.14 s |
| median total | 3.49 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 76.2% | 94.1% | 84.2% | 34 |
| direct | 50.0% | 25.0% | 33.3% | 4 |
| ask | 0.0% | 0.0% | 0.0% | 2 |
| cannot | 0.0% | 0.0% | 0.0% | 6 |

Weakest expected labels: `ask` 0.0%, `cannot` 0.0%, `list_directory` 0.0%, `search_files` 0.0%, `search_notes` 0.0%, `zip_folder` 0.0%, `calculate` 25.0%, `direct` 25.0%
