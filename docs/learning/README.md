# Learning notes

One short note per concept: what it is, why Alfred uses it, what happened here (with our numbers), questions
to check your understanding, and where it is in the code.

**D1: "the model works"**
1. [Chat templates and tool calling](01-chat-templates-and-tool-calling.md)
2. [LoRA and QLoRA](02-lora-and-qlora.md)
3. [Synthetic data and contamination](03-synthetic-data-and-contamination.md)
4. [Evaluation metrics](04-eval-metrics.md)

**D2 (later):** MCP, agent loops, prompt injection, quantization/GGUF, BFCL/When2Call.
**D3 (later):** DPO, GRPO, reward design and reward hacking.

**The 2-minute version of phases 1–5.** We wanted a 2B model on a laptop CPU to call 25 local tools as well as a
large cloud model. A latency spike showed Ollama reprocessed the 1.9k-token tool prompt on every request (21 s);
llama-server reuses the cached prefix (2 s). We froze 25 tool contracts, built a scorer and 326 test items, and
measured the base model at 79.1% vs 88.5% for gpt-oss-120b. We generated ~6.4k training conversations with two
open-weight teachers, validated them against the same scorer, removed anything close to a test item, mixed in
When2Call and xLAM, and trained a LoRA adapter on a free Kaggle T4. v1 reached 93.5% but stopped asking clarifying
questions, because the chat template renders earlier turns differently; v2 fixed the data and reached 95.3%
in-domain (Q4, 1.3 GB, 1.0 s to first token), above the cloud model, with refusals up from 59% to 96%.
