# alfred-2b-v3-q4 on indomain (n=278)

Backend `local` / model `local`, 2026-10-25T23:43:28, commit `379a664`.

| Metric | Value |
|---|---|
| accuracy | 97.8% |
| valid_rate | 100.0% |
| decision_accuracy | 99.3% |
| tool_accuracy | 98.2% |
| args_score | 96.9% |
| decision_macro_f1 | 98.8% |
| median TTFT | 1.03 s |
| median total | 2.35 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 99.6% | 99.6% | 99.6% | 220 |
| direct | 100.0% | 95.0% | 97.4% | 20 |
| ask | 100.0% | 100.0% | 100.0% | 15 |
| cannot | 93.8% | 100.0% | 96.8% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `search_file_contents` 77.8%, `git_status` 88.9%, `set_reminder` 88.9%, `search_files` 90.0%, `direct` 95.0%, `ask` 100.0%, `calculate` 100.0%, `cannot` 100.0%
