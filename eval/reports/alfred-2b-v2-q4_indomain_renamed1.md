# alfred-2b-v2-q4 on indomain_renamed1 (n=276)

Backend `local` / model `local`, 2026-11-17T21:19:56, commit `83cb0eb`. **276 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 83.3% |
| valid_rate | 100.0% |
| decision_accuracy | 97.1% |
| tool_accuracy | 89.9% |
| args_score | 84.9% |
| decision_macro_f1 | 93.9% |
| median TTFT | 1.31 s |
| median total | 2.95 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 97.3% | 99.5% | 98.4% | 219 |
| direct | 94.1% | 84.2% | 88.9% | 19 |
| ask | 100.0% | 80.0% | 88.9% | 15 |
| cannot | 93.3% | 93.3% | 93.3% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `network_status+system_info` 0.0%, `search_files` 10.0%, `set_reminder` 33.3%, `create_note` 50.0%, `open_app` 62.5%, `recall` 62.5%, `disk_usage` 75.0%, `copy_file` 77.8%
