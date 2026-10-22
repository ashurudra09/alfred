# cloud-gpt-oss-120b on indomain (n=278)

Backend `groq` / model `openai/gpt-oss-120b`, 2026-10-22T17:48:56, commit `cf476f8`. **278 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 87.8% |
| valid_rate | 98.9% |
| decision_accuracy | 95.0% |
| tool_accuracy | 89.6% |
| args_score | 86.9% |
| decision_macro_f1 | 89.1% |
| median TTFT | 0.9 s |
| median total | 0.93 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 99.5% | 95.9% | 97.7% | 220 |
| direct | 85.7% | 90.0% | 87.8% | 20 |
| ask | 79.0% | 100.0% | 88.2% | 15 |
| cannot | 92.9% | 86.7% | 89.7% | 15 |
| refuse | 77.8% | 87.5% | 82.3% | 8 |

Weakest expected labels: `network_status+system_info` 0.0%, `port_in_use+port_in_use` 0.0%, `recall` 25.0%, `move_file` 40.0%, `copy_file` 55.6%, `organize_folder` 75.0%, `remember` 75.0%, `search_file_contents` 77.8%
