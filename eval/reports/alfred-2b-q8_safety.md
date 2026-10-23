# alfred-2b-q8 on safety (n=48)

Backend `local` / model `local`, 2026-10-23T07:27:26, commit `029d6da`.

| Metric | Value |
|---|---|
| accuracy | 97.9% |
| valid_rate | 100.0% |
| decision_accuracy | 97.9% |
| tool_accuracy | 100.0% |
| args_score | 100.0% |
| decision_macro_f1 | 96.5% |
| median TTFT | 0.79 s |
| median total | 2.43 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 100.0% | 100.0% | 7 |
| direct | 87.5% | 100.0% | 93.3% | 14 |
| refuse | 100.0% | 92.6% | 96.2% | 27 |

Weakest expected labels: `refuse` 96.3%, `calculate` 100.0%, `direct` 100.0%, `move_to_recycle_bin` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `remember` 100.0%, `search_notes` 100.0%
