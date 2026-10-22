# Progress

Each phase gate adds one line to the log below. Full detail for each phase is in [implementation-plan.md](implementation-plan.md).

## Phase status

| # | Phase | Milestone | Status | Gate passed | Evidence |
|---|---|---|---|---|---|
| 0 | Repo & accounts setup | M1 | done | 2026-10-22 | `scripts/check_setup.py`: all 10 required + 3 optional checks OK |
| 1 | Feasibility spikes | M1 | done (latency open) | 2026-10-22 | `spikes/*.py`; numbers in decisions.md |
| 2 | Tool contracts | M1 | not started | | |
| 3 | Eval harness, test sets & baselines | M1 | not started | | |
| 4 | Training dataset | M1 | not started | | |
| 5 | SFT + export | M1 | not started | | |
| D1 | Docs checkpoint 1: "the model works" | M1 (24 Oct) | not started | | |
| 6 | Tool server | M2 | not started | | |
| 7 | Agent runtime + CLI | M2 | not started | | |
| 8 | Minimal web UI | M2 | not started | | |
| 9 | Benchmarks, safety & ablations | M2 / M3 | not started | | |
| D2 | Docs checkpoint 2: "the product works" | M2 (31 Oct) | not started | | |
| 10 | DPO | M3 | not started | | |
| 11 | GRPO | M3 | not started | | |
| D3 | Docs checkpoint 3: "training story complete" | M3 | not started | | |
| 12 | Copilot comparison & release | M3 (Dec) | not started | | |

## Gate log
<!-- One line per gate: YYYY-MM-DD · phase · result · evidence -->
- 2026-10-22 · Phase 0 · passed · `uv run python scripts/check_setup.py` → all required checks OK (git, GitHub remote, uv, Ollama 0.40.8, HF write token, gated xLAM + FunctionGemma access, Kaggle API, Groq, Cerebras, 80 GB free); optional Gemini, Node, Claude Desktop OK. A bad key was confirmed to fail the check.
- 2026-10-22 · Phase 1 · passed with an open issue · tool calling 4/4, teacher 10/10 valid on 3 candidates, embedder embeddinggemma, Kaggle 2× T4; warm TTFT 20.9 s with 25 schemas (> 8 s rule → compact schemas required in Phase 2; latency fix pending owner decision)
