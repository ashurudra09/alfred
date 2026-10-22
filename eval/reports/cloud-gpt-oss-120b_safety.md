# cloud-gpt-oss-120b on safety (n=48)

Backend `groq` / model `openai/gpt-oss-120b`, 2026-10-22T19:26:03, commit `5d5f84d`.

| Metric | Value |
|---|---|
| accuracy | 95.8% |
| valid_rate | 100.0% |
| decision_accuracy | 95.8% |
| tool_accuracy | 95.8% |
| args_score | 100.0% |
| decision_macro_f1 | 92.7% |
| median TTFT | 0.91 s |
| median total | 1.01 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 77.8% | 100.0% | 87.5% | 7 |
| direct | 93.3% | 100.0% | 96.5% | 14 |
| refuse | 100.0% | 88.9% | 94.1% | 27 |

Weakest expected labels: `refuse` 92.6%, `calculate` 100.0%, `direct` 100.0%, `move_to_recycle_bin` 100.0%, `port_in_use` 100.0%, `read_file` 100.0%, `remember` 100.0%, `search_notes` 100.0%
