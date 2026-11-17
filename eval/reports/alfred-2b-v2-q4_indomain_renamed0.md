# alfred-2b-v2-q4 on indomain_renamed0 (n=276)

Backend `local` / model `local`, 2026-11-17T21:32:58, commit `83cb0eb`. **276 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 96.0% |
| valid_rate | 100.0% |
| decision_accuracy | 97.5% |
| tool_accuracy | 97.1% |
| args_score | 97.3% |
| decision_macro_f1 | 93.9% |
| median TTFT | 1.21 s |
| median total | 2.73 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 97.8% | 100.0% | 98.9% | 219 |
| direct | 100.0% | 84.2% | 91.4% | 19 |
| ask | 93.3% | 93.3% | 93.3% | 15 |
| cannot | 92.3% | 80.0% | 85.7% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `cannot` 80.0%, `direct` 84.2%, `network_status` 87.5%, `search_file_contents` 88.9%, `set_reminder` 88.9%, `search_files` 90.0%, `ask` 93.3%, `calculate` 100.0%
