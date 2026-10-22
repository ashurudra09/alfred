# base-2b-q8 on indomain (n=278)

Backend `local` / model `local`, 2026-10-22T17:48:45, commit `cf476f8`. **278 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 79.1% |
| valid_rate | 100.0% |
| decision_accuracy | 89.2% |
| tool_accuracy | 81.7% |
| args_score | 86.0% |
| decision_macro_f1 | 72.4% |
| median TTFT | 1.94 s |
| median total | 4.68 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 90.3% | 97.7% | 93.9% | 220 |
| direct | 70.6% | 60.0% | 64.9% | 20 |
| ask | 100.0% | 60.0% | 75.0% | 15 |
| cannot | 88.9% | 53.3% | 66.7% | 15 |
| refuse | 80.0% | 50.0% | 61.5% | 8 |

Weakest expected labels: `network_status+system_info` 0.0%, `organize_folder` 37.5%, `recall` 37.5%, `refuse` 50.0%, `cannot` 53.3%, `ask` 60.0%, `direct` 60.0%, `move_file` 60.0%
