# alfred-2b-v1-q4 on indomain (n=278)

Backend `local` / model `local`, 2026-10-23T14:34:32, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 93.5% |
| valid_rate | 100.0% |
| decision_accuracy | 95.0% |
| tool_accuracy | 94.6% |
| args_score | 97.6% |
| decision_macro_f1 | 87.0% |
| median TTFT | 1.04 s |
| median total | 2.46 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 94.4% | 99.6% | 96.9% | 220 |
| direct | 95.0% | 95.0% | 95.0% | 20 |
| ask | 100.0% | 33.3% | 50.0% | 15 |
| cannot | 100.0% | 86.7% | 92.9% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `ask` 33.3%, `search_file_contents` 77.8%, `cannot` 86.7%, `list_directory` 88.9%, `set_reminder` 88.9%, `search_files` 90.0%, `direct` 95.0%, `calculate` 100.0%
