# alfred-2b-v2-f16 on indomain (n=278)

Backend `local` / model `local`, 2026-10-23T23:32:57, commit `42cb001`.

| Metric | Value |
|---|---|
| accuracy | 95.7% |
| valid_rate | 100.0% |
| decision_accuracy | 97.8% |
| tool_accuracy | 97.1% |
| args_score | 96.5% |
| decision_macro_f1 | 94.9% |
| median TTFT | 2.07 s |
| median total | 6.04 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 98.7% | 99.6% | 99.1% | 220 |
| direct | 100.0% | 85.0% | 91.9% | 20 |
| ask | 88.2% | 100.0% | 93.8% | 15 |
| cannot | 92.9% | 86.7% | 89.7% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `search_file_contents` 77.8%, `direct` 85.0%, `cannot` 86.7%, `open_app` 87.5%, `git_status` 88.9%, `open_path` 88.9%, `set_reminder` 88.9%, `search_files` 90.0%
