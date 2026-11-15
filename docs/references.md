# References

Papers and projects Alfred builds on, and where each one is used. An entry is added when the code that uses it
lands.

| Reference | Used for | Where |
|---|---|---|
| Hu et al., [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685), 2021 | Fine-tuning method (rank 16 adapters on the attention and MLP projections) | `train/sft_kernel/sft.py`, `train/configs/sft_2b.yaml` |
| Liu et al., [APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets](https://arxiv.org/abs/2406.18518), 2024 | The xLAM function-calling 60k dataset, 15% of the training mix, for general tool calling on other APIs | `data/sources.py` (`xlam`), `data/mix.py` |
| Ross, Mahabaleshwarkar and Suhara, [When2Call: When (not) to Call Tools](https://arxiv.org/abs/2504.18851), NAACL 2025 | Training split for ask / can't-do replies (15% of the mix); held-out test split as a public benchmark | `data/sources.py` (`when2call`), `eval/when2call/bench.py` |
| Patil et al., [The Berkeley Function Calling Leaderboard (BFCL)](https://proceedings.mlr.press/v267/patil25a.html), ICML 2025 | Public check that fine-tuning did not hurt general function calling (v4 single-turn subset) | `eval/bfcl/run.py`, `eval/bfcl/kernel/` |
| Wilson, "Probable inference, the law of succession, and statistical inference", *JASA* 22(158), 1927 | 95% score interval on every accuracy | `eval/results.py` (`wilson`) |
| McNemar, "Note on the sampling error of the difference between correlated proportions or percentages", *Psychometrika* 12(2), 1947 | Exact paired test between two systems on the same items | `eval/results.py` (`mcnemar`) |

Software: [Unsloth](https://github.com/unslothai/unsloth) and [TRL](https://github.com/huggingface/trl) (training),
[llama.cpp](https://github.com/ggml-org/llama.cpp) (GGUF quantization and serving), the
[Model Context Protocol](https://modelcontextprotocol.io) Python SDK (tool server), Qwen3.5-2B (base model, Apache 2.0).
