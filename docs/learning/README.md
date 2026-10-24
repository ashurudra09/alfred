# Learning notes

One short note per concept: what it is, why Alfred uses it, what happened here (with our numbers), questions
to check your understanding, and where it is in the code.

**D1: "the model works"**
1. [Chat templates and tool calling](01-chat-templates-and-tool-calling.md)
2. [LoRA and QLoRA](02-lora-and-qlora.md)
3. [Synthetic data and contamination](03-synthetic-data-and-contamination.md)
4. [Evaluation metrics](04-eval-metrics.md)

**D2: "the product works"**
5. [MCP: tools as a server](05-mcp.md)
6. [Agent loops](06-agent-loops.md)
7. [Prompt injection](07-prompt-injection.md)
8. [Quantization and GGUF](08-quantization-gguf.md)
9. [Public benchmarks: BFCL and When2Call](09-public-benchmarks.md)

**D3 (later):** DPO, GRPO, reward design and reward hacking.

**The 2-minute version of phases 1–5.** We wanted a 2B model on a laptop CPU to call 25 local tools as well as a
large cloud model. A latency spike showed Ollama reprocessed the 1.9k-token tool prompt on every request (21 s);
llama-server reuses the cached prefix (2 s). We froze 25 tool contracts, built a scorer and 326 test items, and
measured the base model at 79.1% vs 88.5% for gpt-oss-120b. We generated ~6.4k training conversations with two
open-weight teachers, validated them against the same scorer, removed anything close to a test item, mixed in
When2Call and xLAM, and trained a LoRA adapter on a free Kaggle T4. v1 reached 93.5% but stopped asking clarifying
questions, because the chat template renders earlier turns differently; v2 fixed the data and reached 95.3%
in-domain (Q4, 1.3 GB, 1.0 s to first token), above the cloud model, with refusals up from 59% to 96%.

**The 2-minute version of phases 6–9.** The 25 tools became an MCP server whose tool list is generated from the frozen
contracts, so the model sees exactly what it was trained on, and any MCP client (Claude Desktop included) can use
them. Guards keep every tool inside the known folders, away from secrets and executables, and never overwrite or
permanently delete; every write is journaled so it can be undone. The agent loop validates each call against its
schema, retries once, caps a turn at three calls, wraps tool output as untrusted and pauses for the user's
confirmation before any write. That pause is a generator `yield`, which let one loop drive both the terminal app and
a Gradio web UI. End to end, the shipped Q4 model passed 47/50 real tasks and resisted 20/20 prompt-injection files
with zero unconfirmed writes. On public benchmarks, fine-tuning raised When2Call accuracy from 41.2% to 65.7%
(tool hallucination 14.7% → 3.1%) and the BFCL subset from 72.1% to 77.2%, at the cost of a few missed calls on
live_relevance. Q8 matched F16 exactly and Q4 lost 0.4 points while being the fastest.
