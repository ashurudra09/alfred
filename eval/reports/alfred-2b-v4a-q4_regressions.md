# alfred-2b-v4a-q4 on regressions (n=46)

Backend `local` / model `local`, 2026-11-18T10:28:14, commit `224f7d4`. **46 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 69.6% |
| valid_rate | 100.0% |
| decision_accuracy | 91.3% |
| tool_accuracy | 84.8% |
| args_score | 74.0% |
| decision_macro_f1 | 87.8% |
| median TTFT | 1.44 s |
| median total | 3.44 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 94.3% | 97.1% | 95.7% | 34 |
| direct | 80.0% | 100.0% | 88.9% | 4 |
| ask | 100.0% | 100.0% | 100.0% | 2 |
| cannot | 100.0% | 50.0% | 66.7% | 6 |

Weakest expected labels: `search_notes` 0.0%, `calculate` 50.0%, `cannot` 50.0%, `list_directory` 50.0%, `read_file` 50.0%, `set_reminder` 50.0%, `zip_folder` 50.0%, `recall` 66.7%
