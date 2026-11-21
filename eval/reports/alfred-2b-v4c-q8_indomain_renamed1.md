# alfred-2b-v4c-q8 on indomain_renamed1 (n=249)

Backend `local` / model `local`, 2026-11-21T20:33:36, commit `2ec2306`. **249 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 93.6% |
| valid_rate | 100.0% |
| decision_accuracy | 99.2% |
| tool_accuracy | 94.0% |
| args_score | 91.3% |
| decision_macro_f1 | 98.7% |
| median TTFT | 1.41 s |
| median total | 3.35 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 99.5% | 99.5% | 99.5% | 193 |
| direct | 94.7% | 100.0% | 97.3% | 18 |
| ask | 100.0% | 93.3% | 96.5% | 15 |
| cannot | 100.0% | 100.0% | 100.0% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `network_status+system_info` 0.0%, `system_info` 0.0%, `git_status` 71.4%, `recall` 71.4%, `list_directory` 87.5%, `open_path` 87.5%, `move_file` 88.9%, `ask` 93.3%
