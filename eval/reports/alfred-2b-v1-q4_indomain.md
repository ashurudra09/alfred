# alfred-2b-v1-q4 on indomain (n=276)

Backend `local` / model `local`, 2026-10-23T14:34:32, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 93.8% |
| valid_rate | 100.0% |
| decision_accuracy | 94.9% |
| tool_accuracy | 94.6% |
| args_score | 97.8% |
| decision_macro_f1 | 86.9% |
| median TTFT | 1.04 s |
| median total | 2.46 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 94.4% | 99.5% | 96.9% | 219 |
| direct | 94.7% | 94.7% | 94.7% | 19 |
| ask | 100.0% | 33.3% | 50.0% | 15 |
| cannot | 100.0% | 86.7% | 92.9% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `ask` 33.3%, `cannot` 86.7%, `list_directory` 88.9%, `search_file_contents` 88.9%, `set_reminder` 88.9%, `search_files` 90.0%, `direct` 94.7%, `calculate` 100.0%
