# alfred-2b-v3-q8 on indomain_renamed1 (n=249)

Backend `local` / model `local`, 2026-11-21T21:18:01, commit `2ec2306`. **249 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 67.1% |
| valid_rate | 100.0% |
| decision_accuracy | 98.8% |
| tool_accuracy | 67.5% |
| args_score | 57.7% |
| decision_macro_f1 | 98.0% |
| median TTFT | 1.43 s |
| median total | 2.99 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 99.5% | 99.0% | 99.2% | 193 |
| direct | 94.7% | 100.0% | 97.3% | 18 |
| ask | 100.0% | 93.3% | 96.5% | 15 |
| cannot | 93.8% | 100.0% | 96.8% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `calculate` 0.0%, `disk_usage` 0.0%, `network_status+system_info` 0.0%, `open_app` 0.0%, `open_path` 0.0%, `organize_folder` 0.0%, `search_files` 0.0%, `set_reminder` 0.0%
