# cloud-gpt-oss-120b on indomain (n=276)

Backend `groq` / model `openai/gpt-oss-120b`, 2026-10-23T14:34:39, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 89.5% |
| valid_rate | 99.6% |
| decision_accuracy | 96.7% |
| tool_accuracy | 90.6% |
| args_score | 88.2% |
| decision_macro_f1 | 92.7% |
| median TTFT | 0.9 s |
| median total | 0.93 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 99.5% | 97.3% | 98.4% | 219 |
| direct | 85.7% | 94.7% | 90.0% | 19 |
| ask | 83.3% | 100.0% | 90.9% | 15 |
| cannot | 100.0% | 93.3% | 96.5% | 15 |
| refuse | 87.5% | 87.5% | 87.5% | 8 |

Weakest expected labels: `network_status+system_info` 0.0%, `port_in_use+port_in_use` 0.0%, `recall` 25.0%, `move_file` 40.0%, `copy_file` 55.6%, `organize_folder` 75.0%, `remember` 75.0%, `list_reminders` 87.5%
