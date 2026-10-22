# base-2b-q8 on safety (n=48)

Backend `local` / model `local`, 2026-10-22T19:26:00, commit `5d5f84d`.

| Metric | Value |
|---|---|
| accuracy | 66.7% |
| valid_rate | 100.0% |
| decision_accuracy | 68.8% |
| tool_accuracy | 68.8% |
| args_score | 85.7% |
| decision_macro_f1 | 62.1% |
| median TTFT | 1.35 s |
| median total | 5.06 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 33.3% | 100.0% | 50.0% | 7 |
| direct | 87.5% | 50.0% | 63.6% | 14 |
| refuse | 94.1% | 59.3% | 72.7% | 27 |

Weakest expected labels: `move_to_recycle_bin` 0.0%, `refuse` 63.0%, `direct` 64.3%, `calculate` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `remember` 100.0%, `search_notes` 100.0%
