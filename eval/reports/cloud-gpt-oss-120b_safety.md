# cloud-gpt-oss-120b on safety (n=50)

Backend `groq` / model `openai/gpt-oss-120b`, 2026-10-22T17:49:04, commit `cf476f8`. **50 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 88.0% |
| valid_rate | 100.0% |
| decision_accuracy | 90.0% |
| tool_accuracy | 94.0% |
| args_score | 85.7% |
| decision_macro_f1 | 89.8% |
| median TTFT | 0.89 s |
| median total | 0.99 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 77.8% | 100.0% | 87.5% | 7 |
| direct | 100.0% | 80.0% | 88.9% | 15 |
| refuse | 92.9% | 92.9% | 92.9% | 28 |

Weakest expected labels: `move_to_recycle_bin` 0.0%, `direct` 80.0%, `refuse` 92.9%, `calculate` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `remember` 100.0%, `search_notes` 100.0%
