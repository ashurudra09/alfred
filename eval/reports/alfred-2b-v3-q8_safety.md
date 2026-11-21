# alfred-2b-v3-q8 on safety (n=48)

Backend `local` / model `local`, 2026-11-21T20:44:36, commit `2ec2306`.

| Metric | Value |
|---|---|
| accuracy | 97.9% |
| valid_rate | 100.0% |
| decision_accuracy | 97.9% |
| tool_accuracy | 100.0% |
| args_score | 100.0% |
| decision_macro_f1 | 97.6% |
| median TTFT | 0.74 s |
| median total | 2.43 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 100.0% | 100.0% | 7 |
| direct | 93.3% | 100.0% | 96.5% | 14 |
| refuse | 100.0% | 92.6% | 96.2% | 27 |

Weakest expected labels: `refuse` 96.3%, `calculate` 100.0%, `direct` 100.0%, `move_to_recycle_bin` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `remember` 100.0%, `search_notes` 100.0%
