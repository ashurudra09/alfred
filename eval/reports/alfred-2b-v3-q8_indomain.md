# alfred-2b-v3-q8 on indomain (n=249)

Backend `local` / model `local`, 2026-11-21T18:01:30, commit `ca16fb9`.

| Metric | Value |
|---|---|
| accuracy | 99.2% |
| valid_rate | 100.0% |
| decision_accuracy | 99.2% |
| tool_accuracy | 99.2% |
| args_score | 97.7% |
| decision_macro_f1 | 98.7% |
| median TTFT | 1.18 s |
| median total | 2.87 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 99.0% | 99.5% | 193 |
| direct | 100.0% | 100.0% | 100.0% | 18 |
| ask | 100.0% | 100.0% | 100.0% | 15 |
| cannot | 88.2% | 100.0% | 93.8% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `copy_file` 87.5%, `search_file_contents` 87.5%, `ask` 100.0%, `calculate` 100.0%, `cannot` 100.0%, `create_note` 100.0%, `direct` 100.0%, `disk_usage` 100.0%
