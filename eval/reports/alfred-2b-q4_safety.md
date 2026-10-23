# alfred-2b-q4 on safety (n=48)

Backend `local` / model `local`, 2026-10-23T07:41:35, commit `029d6da`.

| Metric | Value |
|---|---|
| accuracy | 97.9% |
| valid_rate | 100.0% |
| decision_accuracy | 97.9% |
| tool_accuracy | 97.9% |
| args_score | 100.0% |
| decision_macro_f1 | 94.8% |
| median TTFT | 0.64 s |
| median total | 1.86 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 87.5% | 100.0% | 93.3% | 7 |
| direct | 92.9% | 92.9% | 92.9% | 14 |
| refuse | 100.0% | 96.3% | 98.1% | 27 |

Weakest expected labels: `direct` 92.9%, `calculate` 100.0%, `move_to_recycle_bin` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `refuse` 100.0%, `remember` 100.0%, `search_notes` 100.0%
