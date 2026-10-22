# Alfred

An offline laptop butler for Windows. A small open model (Qwen3.5-2B), fine-tuned to call 25 local tools (files, system info, developer helpers, notes, reminders, memory), runs fully on the laptop CPU through Ollama. Every change it makes can be undone.

The research question: can a small fine-tuned model match a large cloud model on tool calling for a fixed tool set, at a fraction of the size and cost, fully offline?

## Status
Phases 0–3 done. Baseline in-domain accuracy: base Qwen3.5-2B 79.1% vs gpt-oss-120b 88.5%; safety 66.7% vs 95.8%. Next: Phase 4 (training dataset). See [docs/PROGRESS.md](docs/PROGRESS.md).

## Docs
- [Requirements](docs/requirements.md): what is being built.
- [Implementation plan](docs/implementation-plan.md): phases, gates and how each is built.
- [Progress](docs/PROGRESS.md) and [decisions](docs/decisions.md).

## Setup
1. Install Git, [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com) (embeddings) and llama.cpp (`winget install ggml.llamacpp`, serves the chat model).
2. `copy .env.example .env` and fill in the keys. Save your Kaggle API token to `%USERPROFILE%\.kaggle\access_token`.
3. `uv sync`
4. `uv run python scripts/check_setup.py`: every required item should show ✓.
5. `uv run pytest`

## Evaluate a model
```
uv run python -m alfred.agent.backends serve          # llama-server on the base model, port 8080
uv run python -m eval.run --backend local --system base-2b-q8 --set indomain
uv run python -m eval.run --backend groq --system cloud-gpt-oss-120b --set indomain
uv run python -m eval.review indomain                 # owner review of test items
```
