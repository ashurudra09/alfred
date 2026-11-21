# alfred-2b-v4c-q8 on safety (n=48)

Backend `local` / model `local`, 2026-11-21T19:57:44, commit `2ec2306`.

| Metric | Value |
|---|---|
| accuracy | 97.9% |
| valid_rate | 100.0% |
| decision_accuracy | 100.0% |
| tool_accuracy | 97.9% |
| args_score | 85.7% |
| decision_macro_f1 | 98.2% |
| median TTFT | 0.72 s |
| median total | 2.44 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 100.0% | 100.0% | 7 |
| direct | 93.3% | 100.0% | 96.5% | 14 |
| refuse | 100.0% | 96.3% | 98.1% | 27 |

Weakest expected labels: `move_to_recycle_bin` 0.0%, `calculate` 100.0%, `direct` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `refuse` 100.0%, `remember` 100.0%, `search_notes` 100.0%
