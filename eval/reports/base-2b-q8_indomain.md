# base-2b-q8 on indomain (n=276)

Backend `local` / model `local`, 2026-10-23T14:34:27, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 79.7% |
| valid_rate | 100.0% |
| decision_accuracy | 89.5% |
| tool_accuracy | 81.9% |
| args_score | 86.4% |
| decision_macro_f1 | 73.3% |
| median TTFT | 1.94 s |
| median total | 4.68 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 90.3% | 97.7% | 93.9% | 219 |
| direct | 70.6% | 63.2% | 66.7% | 19 |
| ask | 100.0% | 60.0% | 75.0% | 15 |
| cannot | 100.0% | 53.3% | 69.6% | 15 |
| refuse | 80.0% | 50.0% | 61.5% | 8 |

Weakest expected labels: `network_status+system_info` 0.0%, `organize_folder` 37.5%, `recall` 37.5%, `refuse` 50.0%, `cannot` 53.3%, `ask` 60.0%, `move_file` 60.0%, `direct` 63.2%
