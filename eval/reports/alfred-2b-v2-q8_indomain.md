# alfred-2b-v2-q8 on indomain (n=276)

Backend `local` / model `local`, 2026-10-23T14:34:34, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 96.4% |
| valid_rate | 100.0% |
| decision_accuracy | 97.8% |
| tool_accuracy | 97.5% |
| args_score | 97.1% |
| decision_macro_f1 | 94.8% |
| median TTFT | 1.31 s |
| median total | 3.16 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 98.6% | 99.5% | 99.1% | 219 |
| direct | 100.0% | 84.2% | 91.4% | 19 |
| ask | 88.2% | 100.0% | 93.8% | 15 |
| cannot | 92.9% | 86.7% | 89.7% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `direct` 84.2%, `cannot` 86.7%, `open_app` 87.5%, `open_path` 88.9%, `search_file_contents` 88.9%, `set_reminder` 88.9%, `search_files` 90.0%, `ask` 100.0%
