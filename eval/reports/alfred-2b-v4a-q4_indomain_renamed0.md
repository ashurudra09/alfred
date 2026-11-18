# alfred-2b-v4a-q4 on indomain_renamed0 (n=276)

Backend `local` / model `local`, 2026-11-18T10:55:18, commit `224f7d4`. **276 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 95.7% |
| valid_rate | 100.0% |
| decision_accuracy | 98.6% |
| tool_accuracy | 96.7% |
| args_score | 96.1% |
| decision_macro_f1 | 97.3% |
| median TTFT | 1.27 s |
| median total | 2.7 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 98.2% | 100.0% | 99.1% | 219 |
| direct | 100.0% | 89.5% | 94.4% | 19 |
| ask | 100.0% | 93.3% | 96.5% | 15 |
| cannot | 100.0% | 93.3% | 96.5% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `network_status` 87.5%, `recall` 87.5%, `rename_file` 87.5%, `search_notes` 87.5%, `copy_file` 88.9%, `search_file_contents` 88.9%, `set_reminder` 88.9%, `zip_folder` 88.9%
