# Alfred

An offline laptop butler for Windows. A small open model (Qwen3.5-2B), fine-tuned to call 25 local tools (files, system info, developer helpers, notes, reminders, memory), runs fully on the laptop CPU through llama.cpp (`llama-server`). Every change it makes can be undone.

The research question: can a small fine-tuned model match a large cloud model on tool calling for a fixed tool set, at a fraction of the size and cost, fully offline?

## Status
Phases 0–5 done. In-domain accuracy (278 reviewed test items): **Alfred SFT v2, Q4 on the laptop CPU: 95.3%** vs base Qwen3.5-2B 79.1% vs gpt-oss-120b 88.5%; safety 95.8% vs 66.7% (base); 1.0 s to first token. Details: [docs/decisions.md](docs/decisions.md). See [docs/PROGRESS.md](docs/PROGRESS.md).

## Docs
- [Requirements](docs/requirements.md): what is being built.
- [Implementation plan](docs/implementation-plan.md): phases, gates and how each is built.
- [Progress](docs/PROGRESS.md) (key numbers, open issues) and [decisions](docs/decisions.md).
- [Training data card](data/card.md).

## Setup
1. Install Git, [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com) (embeddings) and llama.cpp (`winget install ggml.llamacpp`, serves the chat model).
2. `copy .env.example .env` and fill in the keys. Save your Kaggle API token to `%USERPROFILE%\.kaggle\access_token`.
3. `uv sync`
4. `uv run python scripts/check_setup.py`: every required item should show ✓.
5. `uv run pytest`

## What runs today (M1)
The fine-tuned model, the evaluation, the tool server and the terminal assistant. The web UI comes in Phase 8.

**Serve a model** (port 8080; a `.gguf` path or an Ollama model name for the base):
```
uv run python -m alfred.agent.backends serve runs/sft_2b_v2/alfred-2b-v2-q4.gguf
```
The fine-tuned GGUFs are in the private Hugging Face repo `alfred-2b-sft` (`v2/alfred-2b-v2-q4.gguf`).

**Evaluate it:**
```
uv run python -m eval.run --backend local --system alfred-2b-v2-q4 --set indomain
uv run python -m eval.run --backend local --system alfred-2b-v2-q4 --set safety
uv run python -m eval.run --backend groq --system cloud-gpt-oss-120b --set indomain   # cloud reference
```
Reports land in `eval/reports/` (JSON + a markdown summary).

**Rebuild the training data** (teacher API keys in `.env`, Ollama running for the dedup embedder):
```
uv run python -m data.gen.teacher
uv run python -m data.validate data/out/synthetic.jsonl
uv run python -m data.mix
uv run python -m data.dedup --check
```

**Train** on Kaggle: `uv run python -m train.package_data --upload`, then `kaggle kernels push -p train/sft_kernel` (settings in `train/configs/sft_2b.yaml`).

## Talk to Alfred (terminal)
```
uv run alfred
```
It starts llama-server on the fine-tuned model if it isn't running, then answers in the terminal. Anything that
changes files (move, rename, copy, zip, organize, delete) shows the exact plan and waits for `y`; `/undo` reverses
the last change (`/actions` lists them). Other commands: `/new /chats /open <id> /delete <id> /memories /forget <id>`.

## Talk to Alfred (browser)
```
uv run alfred-ui
```
Opens a local page (http://127.0.0.1:7860, never exposed to the network, no analytics or web fonts): past chats
in the sidebar, streamed answers with a live timer, each tool call as a card, Confirm/Cancel with the exact plan for
any change, Undo with the recent actions, a Memory tab to view and forget memories, and timing under every reply.
Screenshots: [docs/ui/](docs/ui/).

**End-to-end tests** (needs the model served): `uv run python -m eval.e2e --system alfred-2b-v2-q4`.

## Run the tool server
The 25 tools as a local MCP server over stdio (no network). They work only inside your known folders (Documents,
Downloads, Desktop, Pictures, Music, Videos, plus any `extra_folders` in `%LOCALAPPDATA%\Alfred\config.json`).
```
uv run python -m alfred.tools.server
```
**Use it from Claude Desktop:** quit Claude Desktop completely (tray icon > Quit; it rewrites its config while
running), then run `uv run python scripts/add_to_claude_desktop.py`. It finds the config (on this machine it lives in
`%LOCALAPPDATA%\Claude-Data\<id>\claude_desktop_config.json`, not `%APPDATA%\Claude`), backs it up and adds the
`alfred` server. Reopen Claude Desktop and ask "what's my disk usage?".

**Inspect it:** `npx @modelcontextprotocol/inspector uv run python -m alfred.tools.server` (needs Node.js).

## Learn the concepts
Short notes on what each piece is, why it's here and questions to check your understanding: [docs/learning/](docs/learning/README.md).
