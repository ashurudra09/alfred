# cloud-gpt-oss-120b on indomain (n=278)

Backend `groq` / model `openai/gpt-oss-120b`, 2026-10-23T14:34:39, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 88.5% |
| valid_rate | 99.6% |
| decision_accuracy | 95.7% |
| tool_accuracy | 90.3% |
| args_score | 87.8% |
| decision_macro_f1 | 89.2% |
| median TTFT | 0.9 s |
| median total | 0.93 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 99.5% | 96.8% | 98.2% | 220 |
| direct | 85.7% | 90.0% | 87.8% | 20 |
| ask | 79.0% | 100.0% | 88.2% | 15 |
| cannot | 92.9% | 86.7% | 89.7% | 15 |
| refuse | 77.8% | 87.5% | 82.3% | 8 |

Weakest expected labels: `network_status+system_info` 0.0%, `port_in_use+port_in_use` 0.0%, `recall` 25.0%, `move_file` 40.0%, `copy_file` 55.6%, `organize_folder` 75.0%, `remember` 75.0%, `cannot` 86.7%
