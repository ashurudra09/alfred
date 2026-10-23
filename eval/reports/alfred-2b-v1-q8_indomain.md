# alfred-2b-v1-q8 on indomain (n=278)

Backend `local` / model `local`, 2026-10-23T07:25:16, commit `029d6da`.

| Metric | Value |
|---|---|
| accuracy | 90.6% |
| valid_rate | 100.0% |
| decision_accuracy | 93.2% |
| tool_accuracy | 92.1% |
| args_score | 95.7% |
| decision_macro_f1 | 78.7% |
| median TTFT | 1.32 s |
| median total | 3.26 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 92.4% | 99.6% | 95.8% | 220 |
| direct | 94.7% | 90.0% | 92.3% | 20 |
| ask | 100.0% | 6.7% | 12.5% | 15 |
| cannot | 100.0% | 86.7% | 92.9% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `ask` 6.7%, `top_processes` 75.0%, `cannot` 86.7%, `organize_folder` 87.5%, `git_status` 88.9%, `list_directory` 88.9%, `open_path` 88.9%, `search_file_contents` 88.9%
