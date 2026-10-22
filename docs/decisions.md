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
