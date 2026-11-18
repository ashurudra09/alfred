# alfred-2b-v4a-q4 on indomain_renamed1 (n=276)

Backend `local` / model `local`, 2026-11-18T11:11:11, commit `224f7d4`. **276 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 85.9% |
| valid_rate | 100.0% |
| decision_accuracy | 96.7% |
| tool_accuracy | 86.2% |
| args_score | 86.1% |
| decision_macro_f1 | 93.5% |
| median TTFT | 1.36 s |
| median total | 3.18 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 96.5% | 99.5% | 98.0% | 219 |
| direct | 94.4% | 89.5% | 91.9% | 19 |
| ask | 100.0% | 73.3% | 84.6% | 15 |
| cannot | 100.0% | 86.7% | 92.9% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `network_status+system_info` 0.0%, `recall` 0.0%, `system_info` 0.0%, `search_notes` 62.5%, `copy_file` 66.7%, `ask` 73.3%, `open_path` 77.8%, `set_reminder` 77.8%
