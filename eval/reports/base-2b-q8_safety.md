# base-2b-q8 on safety (n=50)

Backend `local` / model `local`, 2026-10-22T17:48:59, commit `cf476f8`. **50 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 68.0% |
| valid_rate | 100.0% |
| decision_accuracy | 70.0% |
| tool_accuracy | 70.0% |
| args_score | 85.7% |
| decision_macro_f1 | 65.4% |
| median TTFT | 1.35 s |
| median total | 5.02 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 33.3% | 100.0% | 50.0% | 7 |
| direct | 100.0% | 53.3% | 69.6% | 15 |
| refuse | 94.7% | 64.3% | 76.6% | 28 |

Weakest expected labels: `move_to_recycle_bin` 0.0%, `refuse` 64.3%, `direct` 66.7%, `calculate` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `remember` 100.0%, `search_notes` 100.0%
