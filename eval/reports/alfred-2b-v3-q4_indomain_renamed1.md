# alfred-2b-v3-q4 on indomain_renamed1 (n=276)

Backend `local` / model `local`, 2026-11-17T19:35:40, commit `80018f1`. **276 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 59.1% |
| valid_rate | 100.0% |
| decision_accuracy | 98.2% |
| tool_accuracy | 60.1% |
| args_score | 50.0% |
| decision_macro_f1 | 96.8% |
| median TTFT | 2.85 s |
| median total | 5.07 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 99.1% | 98.6% | 98.9% | 219 |
| direct | 94.7% | 94.7% | 94.7% | 19 |
| ask | 100.0% | 93.3% | 96.5% | 15 |
| cannot | 88.2% | 100.0% | 93.8% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `calculate` 0.0%, `disk_usage` 0.0%, `network_status` 0.0%, `network_status+system_info` 0.0%, `open_app` 0.0%, `organize_folder` 0.0%, `remember` 0.0%, `search_files` 0.0%
