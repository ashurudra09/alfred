# alfred-2b-v2-q4 on safety (n=48)

Backend `local` / model `local`, 2026-10-23T14:34:50, commit `c3500c0`.

| Metric | Value |
|---|---|
| accuracy | 95.8% |
| valid_rate | 100.0% |
| decision_accuracy | 95.8% |
| tool_accuracy | 95.8% |
| args_score | 100.0% |
| decision_macro_f1 | 91.5% |
| median TTFT | 0.61 s |
| median total | 1.79 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 77.8% | 100.0% | 87.5% | 7 |
| direct | 92.3% | 85.7% | 88.9% | 14 |
| refuse | 100.0% | 96.3% | 98.1% | 27 |

Weakest expected labels: `direct` 85.7%, `calculate` 100.0%, `move_to_recycle_bin` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `refuse` 100.0%, `remember` 100.0%, `search_notes` 100.0%
