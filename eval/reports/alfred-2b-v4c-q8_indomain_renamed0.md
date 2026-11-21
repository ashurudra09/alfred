# alfred-2b-v4c-q8 on indomain_renamed0 (n=249)

Backend `local` / model `local`, 2026-11-21T20:18:50, commit `2ec2306`. **249 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 98.8% |
| valid_rate | 100.0% |
| decision_accuracy | 99.6% |
| tool_accuracy | 99.2% |
| args_score | 97.5% |
| decision_macro_f1 | 99.4% |
| median TTFT | 1.32 s |
| median total | 3.12 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 100.0% | 99.5% | 99.7% | 193 |
| direct | 94.7% | 100.0% | 97.3% | 18 |
| ask | 100.0% | 100.0% | 100.0% | 15 |
| cannot | 100.0% | 100.0% | 100.0% | 15 |
| refuse | 100.0% | 100.0% | 100.0% | 8 |

Weakest expected labels: `list_directory` 87.5%, `open_path` 87.5%, `set_reminder` 87.5%, `ask` 100.0%, `calculate` 100.0%, `cannot` 100.0%, `copy_file` 100.0%, `create_note` 100.0%
