# Decisions

Each decision with its date and reason. Newest at the bottom.

## 2026-10-21/22: Scope (from requirements v3)
- **Name: Alfred.** A mini-butler for small laptop tasks; no company branding.
- **Base model: Qwen3.5-2B** (non-thinking mode). Best documented tool use under ~2B (BFCL-V4 43.6, vendor-reported); Apache 2.0; available in Ollama. Ablations: Qwen3.5-0.8B and FunctionGemma-270M.
- **Training: SFT → DPO → GRPO, all required.** Each is a separate, comparable result.
- **25 tools, final list in requirements Section 5.** Deliberately hard for a 2B model, so fine-tuning gains are visible.
- **Every destructive action is reversible.** No permanent delete (Recycle Bin only), no overwrites, an action journal and Undo. Undo is a user command, not a model tool.
- **Minimal guardrails in scope:** folder allow-list, sensitive-path blocks, refusals in training data, untrusted tool output, and a safety eval before vs. after fine-tuning (fine-tuning can weaken safety behaviour).
- **Explicit memory** (`remember` / `recall`); automatic memory is out of scope.
- **Chat history + a live response timer + a minimal web UI**, alongside a CLI.
- **Windows-only.**
- **Teacher for synthetic data: an open-weight model.** Closed-model terms restrict training on their outputs, and the Gemini free tier was cut in 2026. A pilot gate in Phase 4 checks quality.
- **Claude drafts test sets; the owner reviews every item.** Claude is never the training-data teacher, so the test set stays independent of training data.
- **Copilot comparison is a required deliverable:** a frontier model with the same tools, a 20-task manual case study, and a capability table.
- **Tools as a local MCP server over stdio.** No network needed, and the tools also work from Claude Desktop.

## 2026-10-22: Phase 0
- **Repo:** `github.com/ashurudra09/alfred`.
- **Kaggle uses the new `KGAT_` access token** stored in `%USERPROFILE%\.kaggle\access_token` (not the old `kaggle.json`). The Kaggle CLI is installed as a uv tool, not a project dependency.
- **Dependencies are added in the phase that first uses them.** Phase 0 only needs `huggingface_hub` and `python-dotenv`.
- **Backup teacher API: Cerebras.**

## 2026-10-22: Phase 1 (feasibility spikes, `spikes/`)
- **Laptop:** i7-1255U (10 cores / 12 threads), 15.7 GB RAM, Iris Xe (no CUDA). Ollama 0.40.8.
- **Tool calling works:** `qwen3.5:2b`, `think=false`, returns structured `tool_calls` (`spikes/toolcall.py`: 4/4, incl. a direct answer with 25 tools loaded).
- **Latency with 25 dummy schemas (~1,880 prompt tokens)** (`spikes/latency.py`, median of 5): cold TTFT 70.4 s (load ~7 s), **warm TTFT 20.9 s**, generation ~8–9 tok/s. Warm is over the ~8 s rule, so **compact tool descriptions are a Phase 2 requirement**. Most of the warm time is prompt processing, so the shared prefix does not appear to be reused between requests (unconfirmed; suspected cause: Qwen3.5's hybrid linear-attention layers limit llama.cpp prefix-cache reuse). Investigated below.
- **Teacher:** all candidates returned 10/10 schema-valid JSON in 2–3 s (`spikes/teacher.py`). Primary **Groq `openai/gpt-oss-120b`** (Apache 2.0); backup Cerebras `gpt-oss-120b`; alternative Groq `qwen/qwen3.8-27b` (most casual phrasing). Teacher paths were inconsistent (`%USERNAME%`, one `AppData` path), so Phase 4 prompts must supply the known folders. The pilot gate in Phase 4 decides the final teacher.
- **Cloud reference model:** Groq `openai/gpt-oss-120b` with the same tools (Gemini optional).
- **Embedder: `embeddinggemma`** (768-d, 6/6 top-1 recall on the sanity set, 38 ms/query); `nomic-embed-text` also 6/6 but slower (43 ms).
- **Kaggle GPU: 2× Tesla T4, 15 GB each** (`spikes/kaggle_gpu`, private kernel). Weekly quota is on the Kaggle settings page (not readable from the CLI).

## 2026-10-22: Phase 1 latency investigation (`spikes/cache.py`, `spikes/llamaserver.py`)
- **Root cause: Ollama never reuses a shared prefix for `qwen3.5:2b`.** An *identical* prompt is served from cache (0.28 s prompt time), but a different user message after the same system prompt + tools reprocesses all ~1,880 tokens (~16 s). Qwen3.5's hybrid linear-attention layers keep a recurrent state that cannot be rolled back to a prefix without checkpoints, and Ollama does not make them.
- **Ollama knobs don't help:** `num_thread` 4 is best but only by ~1 s (4: 19.6 s … 12: 24.0 s). Shorter or no descriptions save little (1,879 → 1,561 tokens, no TTFT gain). Odd scaling: 5 tools (639 tokens) still ~17 s, no tools 3.3 s.
- **llama.cpp `llama-server` (b11815, CPU build, same Ollama Q8_0 GGUF, `-c 8192 -t 4`, default flags) reuses the prefix via context checkpoints:** 1,886 of ~1,905 tokens come from the cache, **warm TTFT median 2.1 s** (5 requests, 1.6–2.3 s), generation ~9 tok/s, all 5 tool calls sensible. Under the 5 s target.
- **Cold start:** the one-time prefill of the shared prefix is ~57 s. `--slot-save-path` + `POST /slots/0?action=save|restore` persists it (104 MB file, save/restore ~125 ms); after a server restart + restore, the first request's TTFT was 1.6–1.9 s.
- **Compact schemas are not needed for latency** with llama-server (schema size only affects the one-time, persisted prefill); still kept short for context budget.
- **Proposed (owner to confirm): serve the chat model with `llama-server` instead of Ollama** (requirements 7.5 already allows it). It loads the GGUF directly (no Modelfile/TEMPLATE step in Phase 5), speaks the same OpenAI-compatible API the harness uses, and restores the saved prefix at startup. Ollama stays for the `embeddinggemma` embedder. Install: `winget install ggml.llamacpp`. Note: Ollama's default `qwen3.5:2b` is Q8_0, not Q4.
