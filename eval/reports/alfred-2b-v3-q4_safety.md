# alfred-2b-v3-q4 on safety (n=48)

Backend `local` / model `local`, 2026-10-25T23:45:05, commit `379a664`.

| Metric | Value |
|---|---|
| accuracy | 100.0% |
| valid_rate | 100.0% |
| decision_accuracy | 100.0% |
| tool_accuracy | 100.0% |
| args_score | 100.0% |
| decision_macro_f1 | 98.2% |
| median TTFT | 0.62 s |
| median total | 1.87 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 100.0% | 100.0% | 7 |
| direct | 93.3% | 100.0% | 96.5% | 14 |
| refuse | 100.0% | 96.3% | 98.1% | 27 |

Weakest expected labels: `calculate` 100.0%, `direct` 100.0%, `move_to_recycle_bin` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `refuse` 100.0%, `remember` 100.0%, `search_notes` 100.0%
