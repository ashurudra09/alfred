# Alfred

An offline laptop butler for Windows. A small open model (Qwen3.5-2B), fine-tuned to call 25 local tools (files, system info, developer helpers, notes, reminders, memory), runs fully on the laptop CPU through Ollama. Every change it makes can be undone.

The research question: can a small fine-tuned model match a large cloud model on tool calling for a fixed tool set, at a fraction of the size and cost, fully offline?

## Status
Phases 0–1 done (Phase 1 left CPU latency as an open issue); next is Phase 2 (tool contracts). See [docs/PROGRESS.md](docs/PROGRESS.md).

## Docs
- [Requirements](docs/requirements.md): what is being built.
- [Implementation plan](docs/implementation-plan.md): phases, gates and how each is built.
- [Progress](docs/PROGRESS.md) and [decisions](docs/decisions.md).

## Setup
1. Install Git, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com).
2. `copy .env.example .env` and fill in the keys. Save your Kaggle API token to `%USERPROFILE%\.kaggle\access_token`.
3. `uv sync`
4. `uv run python scripts/check_setup.py`: every required item should show ✓.
