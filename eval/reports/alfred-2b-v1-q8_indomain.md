# alfred-2b-v1-q8 on indomain (n=276)

Backend `local` / model `local`, 2026-10-23T14:34:29, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 92.4% |
| valid_rate | 100.0% |
| decision_accuracy | 93.1% |
| tool_accuracy | 92.4% |
| args_score | 97.4% |
| decision_macro_f1 | 78.6% |
| median TTFT | 1.32 s |
| median total | 3.26 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 92.4% | 99.5% | 95.8% | 219 |
| direct | 94.4% | 89.5% | 91.9% | 19 |
| ask | 100.0% | 6.7% | 12.5% | 15 |
| cannot | 100.0% | 86.7% | 92.9% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `ask` 6.7%, `cannot` 86.7%, `list_directory` 88.9%, `open_path` 88.9%, `direct` 89.5%, `search_files` 90.0%, `calculate` 100.0%, `copy_file` 100.0%
