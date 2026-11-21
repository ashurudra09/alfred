# References

Papers and projects Alfred builds on, and where each one is used. An entry is added when the code that uses it
lands.

| Reference | Used for | Where |
|---|---|---|
| Hu et al., [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685), 2021 | Fine-tuning method (rank 16 adapters on the attention and MLP projections) | `train/sft_kernel/sft.py`, `train/configs/sft_2b.yaml` |
| Liu et al., [APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets](https://arxiv.org/abs/2406.18518), 2024 | The xLAM function-calling 60k dataset, 15% of the training mix, for general tool calling on other APIs | `data/sources.py` (`xlam`), `data/mix.py` |
| Ross, Mahabaleshwarkar and Suhara, [When2Call: When (not) to Call Tools](https://arxiv.org/abs/2504.18851), NAACL 2025 | Training split for ask / can't-do replies (15% of the mix); held-out test split as a public benchmark | `data/sources.py` (`when2call`), `eval/when2call/bench.py` |
| Patil et al., [The Berkeley Function Calling Leaderboard (BFCL)](https://proceedings.mlr.press/v267/patil25a.html), ICML 2025 | Public check that fine-tuning did not hurt general function calling (v4 single-turn subset) | `eval/bfcl/run.py`, `eval/bfcl/kernel/` |
| Wadden et al., [Fact or Fiction: Verifying Scientific Claims](https://arxiv.org/abs/2004.14974), EMNLP 2020 | SciFact: expert-written claims and the abstracts that support or refute them, a 300-abstract subset as the retrieval test for semantic search (claims CC BY 4.0, abstracts ODC-By 1.0) | `eval/retrieval.py`, `eval/testsets/retrieval_scifact_{dev,test}.jsonl` |
| Thakur et al., [BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663), NeurIPS 2021 Datasets and Benchmarks | The packaged SciFact files (corpus, queries, test qrels) the subset is drawn from | `eval/retrieval.py` (`build`) |
| Cormack, Clarke and Büttcher, [Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf), SIGIR 2009 | Fusing the BM25 and embedding rankings, k = 60 as in the paper | `src/alfred/tools/semantic.py` (`rrf`) |
| Schechter Vera et al., [EmbeddingGemma: Powerful and Lightweight Text Representations](https://arxiv.org/abs/2509.20354), 2025 | The 300M embedder (via Ollama) for memory recall, semantic search and the contamination guard; its retrieval prompts (`task: search result \| query:`, `title: … \| text:`) from the model card | `src/alfred/tools/memory.py` (`embed_many`), `src/alfred/tools/semantic.py`, `data/dedup.py` |
| Lin et al., [Hammer: Robust Function-Calling for On-Device Language Models via Function Masking](https://arxiv.org/abs/2410.04587), 2024 (preprint) | Replacing tool and parameter names with random strings in part of the training data, so tools are chosen from descriptions; 0.33 is the paper's worked ratio (Section 5.5), its final ratio is not stated | `data/augment.py` |
| Debenedetti et al., [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352), 2024 (preprint; code MIT) | Attack wordings (`direct`, `ignore_previous`, `system_message`, `important_instructions`, `tool_knowledge`) and the train-allowed / test-only split of them | `eval/security/families.py` |
| Zhan et al., [InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents](https://arxiv.org/abs/2403.02691), ACL 2024 Findings | The reinforced "hacking prompt" wording (`injecagent` family) | `eval/security/families.py` |
| Yao, Shinn, Razavi and Narasimhan, [τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045), 2024 (preprint) | The pass^k metric: the chance that k trials of the same task all pass | `eval/e2e/__main__.py` (`--trials`), `eval/results.py` (hard-suite table) |
| Ross, Gordon and Bagnell, [A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning](https://arxiv.org/abs/1011.0686), AISTATS 2011 | Training on the distribution of states the learner's own policy induces (DAgger): v4's on-policy data runs the student through the real tools and has a teacher correct the turns it got wrong | `data/onpolicy.py` |
| Wilson, "Probable inference, the law of succession, and statistical inference", *JASA* 22(158), 1927 | 95% score interval on every accuracy | `eval/results.py` (`wilson`) |
| McNemar, "Note on the sampling error of the difference between correlated proportions or percentages", *Psychometrika* 12(2), 1947 | Exact paired test between two systems on the same items | `eval/results.py` (`mcnemar`) |

Software: [Unsloth](https://github.com/unslothai/unsloth) and [TRL](https://github.com/huggingface/trl) (training),
[llama.cpp](https://github.com/ggml-org/llama.cpp) (GGUF quantization and serving), the
[Model Context Protocol](https://modelcontextprotocol.io) Python SDK (tool server), [SQLite FTS5](https://sqlite.org/fts5.html) (BM25 keyword ranking in semantic search), Qwen3.5-2B (base model, Apache 2.0).
