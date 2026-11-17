# alfred-2b-v2-q4 on unseen (n=80)

Backend `local` / model `local`, 2026-11-18T03:02:22, commit `1e3356a`. **80 items not yet owner-reviewed.**

| Metric | Value |
|---|---|
| accuracy | 96.2% |
| valid_rate | 100.0% |
| decision_accuracy | 97.5% |
| tool_accuracy | 97.5% |
| args_score | 97.9% |
| decision_macro_f1 | 93.0% |
| median TTFT | 1.27 s |
| median total | 3.33 s |

| Decision | precision | recall | F1 | n |
|---|---|---|---|---|
| tool_call | 98.6% | 98.6% | 98.6% | 72 |
| cannot | 87.5% | 87.5% | 87.5% | 8 |

Weakest expected labels: `clipboard_set` 80.0%, `cannot` 87.5%, `convertUnits` 87.5%, `calculate` 100.0%, `clipboard_get` 100.0%, `colorConvert` 100.0%, `copy_file` 100.0%, `countWords` 100.0%
