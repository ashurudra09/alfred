# alfred-2b-v2-q4 on indomain (n=278)

Backend `local` / model `local`, 2026-10-23T14:34:36, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 95.3% |
| valid_rate | 100.0% |
| decision_accuracy | 97.5% |
| tool_accuracy | 96.8% |
| args_score | 96.9% |
| decision_macro_f1 | 94.0% |
| median TTFT | 1.0 s |
| median total | 2.37 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 97.8% | 100.0% | 98.9% | 220 |
| direct | 100.0% | 85.0% | 91.9% | 20 |
| ask | 93.3% | 93.3% | 93.3% | 15 |
| cannot | 92.3% | 80.0% | 85.7% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `search_file_contents` 77.8%, `cannot` 80.0%, `direct` 85.0%, `network_status` 87.5%, `git_status` 88.9%, `set_reminder` 88.9%, `search_files` 90.0%, `ask` 93.3%
