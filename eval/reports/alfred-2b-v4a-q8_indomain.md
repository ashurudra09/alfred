# alfred-2b-v4a-q8 on indomain (n=249)

Backend `local` / model `local`, 2026-11-21T14:25:40, commit `d014e96`.

| Metric | Value |
|---|---|
| accuracy | 96.4% |
| valid_rate | 100.0% |
| decision_accuracy | 99.2% |
| tool_accuracy | 98.4% |
| args_score | 95.7% |
| decision_macro_f1 | 98.7% |
| median TTFT | 1.12 s |
| median total | 2.78 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 99.0% | 99.5% | 193 |
| direct | 94.7% | 100.0% | 97.3% | 18 |
| ask | 100.0% | 100.0% | 100.0% | 15 |
| cannot | 93.8% | 100.0% | 96.8% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `search_file_contents` 62.5%, `recall` 85.7%, `rename_file` 85.7%, `search_notes` 85.7%, `list_directory` 87.5%, `set_reminder` 87.5%, `zip_folder` 87.5%, `ask` 100.0%
