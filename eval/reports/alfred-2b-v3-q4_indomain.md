# alfred-2b-v3-q4 on indomain (n=276)

Backend `local` / model `local`, 2026-10-25T23:43:28, commit `379a664`.

| Metric | Value |
|---|---|
| accuracy | 98.6% |
| valid_rate | 100.0% |
| decision_accuracy | 99.3% |
| tool_accuracy | 98.6% |
| args_score | 97.5% |
| decision_macro_f1 | 98.7% |
| median TTFT | 1.03 s |
| median total | 2.35 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 99.5% | 99.5% | 99.5% | 219 |
| direct | 100.0% | 94.7% | 97.3% | 19 |
| ask | 100.0% | 100.0% | 100.0% | 15 |
| cannot | 93.8% | 100.0% | 96.8% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `search_file_contents` 77.8%, `search_files` 90.0%, `direct` 94.7%, `ask` 100.0%, `calculate` 100.0%, `cannot` 100.0%, `copy_file` 100.0%, `create_note` 100.0%
