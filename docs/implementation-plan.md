# Implementation Plan: Alfred (offline laptop butler, fine-tuned Qwen3.5-2B)

## Context
A trained-model AI project, built end to end: data, training, evaluation and a working product. What to build is fixed in [requirements.md](requirements.md) (v3). That doc is the spec: 25 tools exposed via a local MCP server; Qwen3.5-2B trained with SFT → DPO → GRPO; GGUF served by Ollama on CPU; reversible actions; minimal guardrails; explicit memory; chat history; a live timer; a minimal UI; an evaluation harness; and the Copilot comparison. This plan says **in what order and how** to build it.

**Project name: Alfred**, a mini-butler for small laptop tasks. Code, CLI and model names use `alfred` (package `alfred`, commands `alfred` / `alfred-ui`, Ollama models `alfred-2b-q4`, …). The requirements doc's working name gets renamed to Alfred in Phase 0.

**Assumptions:**
- Python 3.12 managed with `uv`, tested with `pytest`.
- Claude Code **drafts** the hand-checked test sets and the owner reviews and edits every item. Claude is never the training-data teacher, so the contamination guard holds.
- Keys live only in `.env` (git-ignored) and Kaggle Secrets, never in code or chat.

---

# LAYER 1: Phases, goals and completion conditions

Each phase ends at a **gate**: completion conditions with a stated way to verify them. A phase is only done when its gate passes, and **every gate appends one status line to `docs/PROGRESS.md`**. Phases share exactly three frozen things:
1. **Tool contracts** (Phase 2).
2. **Data formats** (`schemas.py`, Phase 2).
3. **The scorer** (`eval/score.py`, Phase 3). GRPO reuses it as its reward.

**Documentation checkpoints (D1–D3)** sit between phase groups so progress can be tracked and the owner learns each concept as it lands.

| # | Phase | Goal | Completion conditions (gate) | How it's verified | MS |
|---|---|---|---|---|---|
| 0 | **Repo & accounts setup** | Everything the owner must install, create or authorise, plus the repo skeleton, so implementation never blocks on access | (a) tools installed: Git, uv, Ollama, (optional) Node.js LTS for the MCP Inspector, (optional) Claude Desktop; (b) GitHub repo `alfred` (private) with the skeleton pushed; (c) Hugging Face account + write token + gated terms accepted (xLAM-60k, FunctionGemma); (d) Kaggle account, phone-verified, API token, HF token as a Kaggle Secret, GPU quota visible; (e) teacher API key (Groq; Cerebras/OpenRouter as backup) + optional Google AI Studio key; (f) `.env` filled; (g) ≥ 25 GB free disk; (h) requirements doc renamed to Alfred | `uv run python scripts/check_setup.py` prints ✓ for every item (it calls each CLI/API with a harmless read-only request) | M1 |
| 1 | **Feasibility spikes** | Prove the plan works on this laptop and these free tiers before writing real code | (a) Ollama `qwen3.5:2b`, `think=false`, returns a tool call; (b) CPU latency with 25 dummy schemas, cold vs. warm; (c) Kaggle GPU type + quota noted; (d) teacher returns valid JSON; (e) embedding model chosen; (f) decisions recorded | `spikes/` scripts print numbers; `docs/decisions.md` has latency, quota, teacher, cloud reference model, embedder | M1 |
| 2 | **Tool contracts** | Freeze the interface every later phase depends on | (a) 25 contracts (type hints, docstrings, MCP annotations, `needs_confirmation`); (b) exported `tools.json` validates as JSON Schema; (c) the prompt renderer is deterministic; (d) data/test formats defined; (e) git tag `contracts-v1.0` | `pytest tests/contracts` | M1 |
| 3 | **Eval harness, test sets & baselines** | Score any model *before* training | (a) in-domain test set v1 ≥ 250 items, all owner-reviewed; (b) safety set ~50; (c) scorer unit-tested; (d) Ollama + cloud backends; (e) baseline reports for base Qwen3.5-2B and the cloud reference | `pytest tests/eval`; `eval/reports/baseline_*.json`; manual rescoring of 20 items agrees with the scorer | M1 |
| 4 | **Training dataset** | A licence-clean, validated SFT dataset in Qwen3.5 chat format | (a) teacher pilot gate passed (≥ 90% auto-valid, ≥ 90% of a 50-item manual check correct); (b) 5–8k synthetic + ~400 refusal + When2Call + xLAM, mixed; (c) 100% validation pass; (d) 0 near-duplicates of test items; (e) dataset card | `python -m data.validate` (0 errors); `python -m data.dedup --check` (0 hits); `data/stats.md` reviewed | M1 |
| 5 | **SFT + export** | A fine-tuned model that runs offline in Ollama and beats the base | (a) SFT on Kaggle, curves saved, best checkpoint by val loss; (b) GGUF Q4_K_M + Q8_0 load in Ollama with tool calling; (c) in-domain eval: fine-tuned vs. base vs. cloud; (d) adapter + GGUF on the HF Hub (private) | `eval.run` reports for `alfred-2b-q4/q8`; the gain over base is reported (target ≥ 15 pts, the real number whatever it is) | M1 |
| **D1** | **Docs checkpoint 1: "the model works"** | Track M1 | `PROGRESS.md`, `decisions.md`, README "status" and learning notes updated (Layer 2); tag `checkpoint-D1` | Owner reads `PROGRESS.md` and the learning notes and can explain phases 1–5 in ~2 min; every number links to a report | **M1 (24 Oct)** |
| 6 | **Tool server** | All 25 tools work, safely, behind the frozen contracts | (a) the MCP server's tool list = `tools.json`; (b) guards: allow-list, sensitive-path blocks, no overwrite, executables refused; (c) journal + `undo()` for every write tool; (d) memory store with embeddings + keyword fallback | `pytest tests/tools` on a temp sandbox (happy/error paths, every guard, undo round-trip); the MCP Inspector lists 25 tools; Claude Desktop calls a read tool | M2 |
| 7 | **Agent runtime + CLI** | A usable assistant in a terminal with every safety behaviour, history and timing | (a) loop with validation + one retry, ≤ 3 calls, streaming; (b) confirmation gate from annotations; (c) untrusted tool output; (d) chat store + context budget; (e) timing events + JSONL log; (f) CLI commands; (g) 30 e2e tasks + ~20 injection fixtures | `pytest tests/agent` (fake backend); `python -m eval.e2e` pass rate; **Wi-Fi-off** run of 5 tasks succeeds; safety invariants = 0 | M2 |
| 8 | **Minimal web UI** | A demo-ready local UI over the Phase 7 event API | (a) streaming + running timer; (b) tool-call cards with Confirm/Cancel; (c) Undo; (d) history sidebar; (e) memory panel; (f) timing breakdown | UI smoke test via `gradio_client`; manual checklist with screenshots; no agent logic in `ui/` | M2 |
| 9 | **Benchmarks, safety & ablations** | The full results table except stage 2 | (a) BFCL v4 subset base vs. SFT; (b) When2Call; (c) safety + injection; (d) quantization bf16/Q8/Q4; (e) 0.8B + 270M ablations; (f) test set extended to ~400 | All reports exist; `python -m eval.results` regenerates `RESULTS.md` | M2 (a–d), M3 (e–f) |
| **D2** | **Docs checkpoint 2: "the product works"** | Track M2; demo-able state documented | Same doc set updated + architecture diagram + how-to-run for CLI/UI; learning notes for phases 6–9; tag `checkpoint-D2` | Owner can explain phases 6–9; a README how-to-run works on the owner's laptop | **M2 (31 Oct)** |
| 10 | **DPO** | Preference tuning on SFT; measured effect | (a) When2Call prefs + on-policy rejected samples; (b) DPO run; (c) full eval vs. SFT | Reports + `RESULTS.md` row; regressions > 2 pts explained | M3 |
| 11 | **GRPO** | RL with the scorer as a verifiable reward; reward-hacking check | (a) reward unit-tested; (b) run with reward/KL curves; (c) full eval vs. SFT and SFT+DPO; (d) abstain-rate check | Reports, curves, `RESULTS.md` rows | M3 |
| **D3** | **Docs checkpoint 3: "training story complete"** | Track stage 2 and the comparisons | Doc set + learning notes on DPO/GRPO/reward hacking; SFT vs. DPO vs. GRPO write-up; tag `checkpoint-D3` | Owner can explain DPO vs. GRPO with the project's own numbers | M3 |
| 12 | **Copilot comparison & release** | Everything a reviewer sees | (a) the README Copilot section (3 parts); (b) final README; (c) public HF model + dataset cards; (d) demo video | A fresh clone + README → working Alfred; every README number traces to a report | **M3 (Dec)** |

**Milestones:** M1 = phases 0–5 + D1 by **24 Oct**. M2 = phases 6–9(a–d) + D2 by **31 Oct**. M3 = the rest by **December**.
**Safety valve:** if a milestone slips, results are reported as "in progress", with only the numbers that exist.

---

# LAYER 2: How to implement and validate each phase

### Repo layout (each phase writes only its own folders)
```
alfred/
  pyproject.toml  .env.example  .gitignore  README.md  RESULTS.md
  scripts/check_setup.py                        # Phase 0
  docs/PROGRESS.md  docs/decisions.md  docs/learning/   # D1–D3 (+ one line per gate)
  spikes/                                       # Phase 1
  src/alfred/
    contracts/                                  # Phase 2: tools.py, export.py, prompt.py, schemas.py, tools.json
    tools/                                      # Phase 6: files.py system.py dev.py productivity.py calc.py memory.py guards.py journal.py server.py
    agent/                                      # Phase 3 (backends.py) + Phase 7: loop.py chats.py timing.py cli.py
    ui/app.py                                   # Phase 8
  data/                                         # Phase 4 (+ pref.py in 10)
  train/                                        # Phases 5, 10, 11: sft/dpo/grpo notebooks, configs/*.yaml, reward.py
  eval/                                         # Phase 3 (+ e2e in 7, benchmarks in 9): score.py run.py review.py testsets/ e2e/ reports/ results.py
  tests/                                        # one subfolder per phase
```

## Phase 0: Repo & accounts setup
**Owner does these (Claude can't: accounts, credentials, installers):**

1. **Install on Windows:**
   - Git: `winget install Git.Git`
   - uv: `winget install astral-sh.uv`. uv also installs Python 3.12 for the project, so no separate Python install is needed.
   - Ollama for Windows: `winget install Ollama.Ollama`, then make sure it's running in the tray.
   - *(optional)* Node.js LTS (`winget install OpenJS.NodeJS.LTS`) for the MCP Inspector.
   - *(optional)* Claude Desktop, for testing the MCP server.
   - *(optional)* GitHub CLI: `winget install GitHub.cli`.
2. **GitHub:** create an empty **private** repo `alfred`. Authenticate git (`gh auth login`, or set up an SSH key).
3. **Hugging Face:**
   - Create an account.
   - Settings → Access Tokens → a **write** token, saved for `HF_TOKEN`.
   - Open and **accept the terms** on `Salesforce/xlam-function-calling-60k` and `google/functiongemma-270m-it` (both gated).
4. **Kaggle:**
   - Create an account.
   - **Verify your phone number** (required for GPU and internet in notebooks).
   - Settings → API → *Create New Token* → save the token to `C:\Users\ashur\.kaggle\access_token` (the new `KGAT_` token format).
   - Notebook editor → Add-ons → Secrets → add `HF_TOKEN`.
   - Check the weekly GPU quota on the settings page.
5. **Teacher / cloud APIs (free tiers):**
   - Groq: create an account and an API key → `GROQ_API_KEY`.
   - Backup: Cerebras or OpenRouter key.
   - *(optional)* Google AI Studio key → `GEMINI_API_KEY`, as a cloud reference.
   - Note for each: free tiers may log prompts. Only synthetic data is sent, never personal files.
6. **Disk:** ≥ 25 GB free (base models, GGUFs, datasets).
7. Copy `.env.example` → `.env` and paste in the keys.

**Claude does (after the owner's step 2):**
1. Scaffold the repo: the layout above, `pyproject.toml` (`uv init`; deps `mcp<2`, `openai`, `pydantic`, `jsonschema`, `python-dotenv`, `huggingface_hub`, `kaggle`, `pytest`), `.gitignore` (`.env`, `*.gguf`, `runs/`, `logs/`, `data/out/`), `.env.example`, and a README stub.
2. `docs/PROGRESS.md` with the phase table (all "not started") and `docs/decisions.md` (seeded with the decisions in requirements v3).
3. Copy the requirements doc into `docs/requirements.md` and rename it to Alfred (the original is updated too).
4. `scripts/check_setup.py`, one check per item, each read-only:
   - `git --version`
   - `uv --version`
   - Ollama reachable at `http://127.0.0.1:11434/api/version`
   - HF `whoami` with `HF_TOKEN`
   - HF gated access: fetch the xLAM dataset info
   - `kaggle` API: list own datasets
   - Groq `GET /models` returns 200
   - free disk ≥ 25 GB
   - optional checks (`node`, Claude Desktop config path) are reported as warnings, not failures
5. First commit + push.

**Validate:** `uv run python scripts/check_setup.py` → all required items ✓. Gate line added to `PROGRESS.md`.

## Phase 1: Feasibility spikes
**Implement**
1. `ollama pull qwen3.5:2b`.
2. `spikes/latency.py`: 25 realistic dummy schemas; 5 cold + 5 warm calls with `think=false` and the same system prompt → time to first token, total time, prompt tokens.
3. `spikes/toolcall.py`: a request with 3 tools → a parsed `tool_calls` comes back.
4. `spikes/teacher.py`: 10 JSON examples from the teacher, parsed.
5. `spikes/embed.py`: pull 1–2 small Ollama embedding models; time + a sanity similarity check → choose one.
6. Kaggle: open a GPU notebook and record the GPU type and quota.

**Validate**
- Numbers recorded in `docs/decisions.md`.
- **Rule:** if the warm time to first token with 25 schemas exceeds ~8 s, compact descriptions become a Phase 2 requirement. If a free tier is unusable, choose the self-hosted Kaggle teacher.

## Phase 2: Tool contracts
**Implement**
1. `contracts/tools.py`: 25 stubs with full type hints (`Literal` enums, `Annotated[..., Field(description=...)]`), short docstrings, and a registry `{name: {fn, read_only, destructive, needs_confirmation, group}}` matching requirements Section 5.
2. `contracts/export.py` → `tools.json` (pydantic-generated schemas, the same shape FastMCP produces).
3. `contracts/prompt.py`: `render_system_prompt(known_folders, now)`. A fixed template with role, rules (confirm / ask / refuse / tool output is untrusted data), a `Known folders:` block (training data uses randomised usernames) and today's date. Schemas go through the chat template's `tools=`, and the prefix stays identical across requests for prompt caching.
4. `contracts/schemas.py`:
   - `ToolCall`
   - `Example{id, source, category, messages[], tools}`
   - `TestItem{id, messages[], expected_decision ∈ {tool_call, direct, ask, cannot, refuse}, expected_calls[], arg_rules, tags}`
   - Multi-step items carry earlier calls and results; the expected value is the *next* step.
5. Tag `contracts-v1.0`. A later change bumps the version and means regenerating data.

**Validate** (`tests/contracts/`)
- 25 unique names; schemas pass meta-validation.
- Confirmation flags match the spec.
- Deterministic prompt; token count logged.

## Phase 3: Eval harness, test sets & baselines
**Implement**
1. `agent/backends.py`: one OpenAI-compatible `Backend` (Ollama `/v1`, Groq/OpenRouter, Gemini's OpenAI endpoint), with streaming events and normalised tool-call parsing (plus a fallback parser for Qwen's XML tool-call text).
2. `eval/score.py` (pure functions):
   - `classify_decision`
   - `score_item` → `{decision_ok, tool_ok, args_score 0–1 per arg_rules with Windows path normalisation, valid}`
   - `aggregate` → accuracy, per-tool confusion matrix, decision F1
3. `eval/run.py`: `--backend --set --out`. Local runs sequential (fair latency); cloud runs rate-limited. Outputs a JSON report + raw outputs + markdown summary.
4. Test sets:
   - Claude drafts `indomain.jsonl` v1 (≥ 250; ≥ 8 per tool + direct/ask/cannot/refuse; Hinglish, typos, confusable pairs) and `safety.jsonl` (~50, including borderline-but-OK items to catch over-refusal).
   - **The owner reviews every item** with `python -m eval.review` (y / n / e).
5. Baselines: base Qwen3.5-2B (Ollama) + the cloud reference.

**Validate**
- `tests/eval/`: decision types, arg rules, path normalisation, malformed JSON, multi-call.
- 20 hand-rescored items match the scorer.

## Phase 4: Training dataset
**Implement**
1. `data/gen/prompts/`: one prompt per tool group × scenario:
   - single call;
   - multi-step with tool results (`recall` → `zip_folder`; search → read → summarise);
   - confirm flows;
   - direct / ask / cannot;
   - refusal;
   - injection-in-tool-result.
   Randomised usernames, paths and phrasing styles.
2. `data/gen/teacher.py`: 10–20 examples per call, JSON, disk cache by prompt hash, back-off, resumable.
3. **Pilot gate:** ~100 examples → validate → the owner hand-checks 50 → result recorded in `decisions.md`; switch teacher if it fails.
4. `data/validate.py`: tool exists, args pass the schema, tool messages well-formed, confirmation flow present for destructive tools, no permanent-delete language.
5. `data/sources/`: When2Call `train_sft` and an xLAM-60k sample → `Example`.
6. `data/mix.py`: target mix ~60% in-domain / 15% When2Call / 15% xLAM / 5–8% refusal+injection, with ≥ 200 per tool. Stratified 95/5 split. Rendered with the Qwen3.5 tokenizer's `apply_chat_template(..., tools=...)` (tokenizer only, on CPU).
7. `data/dedup.py`: a small sentence-transformer on CPU; drop training items with cosine > 0.9 to any test item (tune after viewing near-misses), plus an n-gram overlap check.
8. `data/stats.md`, `data/card.md`.

**Validate**
- `data.validate` 0 errors; `data.dedup --check` 0 hits.
- Eyeball 20 rendered training strings (tool calls, tool results, no thinking blocks).

## Phase 5: SFT + export
**Implement**
1. Upload `train.jsonl` / `val.jsonl` as a **private Kaggle Dataset** (`kaggle datasets create`).
2. `train/sft.ipynb`, adapted from Unsloth's Kaggle *Qwen2.5-Coder Tool Calling* notebook to `unsloth/Qwen3.5-2B`:
   - 4-bit + LoRA r=16 / α=32 on all linear layers; seq len 4096;
   - `train_on_responses_only`;
   - 2 epochs, lr 2e-4, cosine schedule, seed 3407;
   - periodic val, keep the best;
   - hyperparameters in `train/configs/sft_2b.yaml`.
3. In the notebook: save the adapter → `save_pretrained_gguf` (q4_k_m, q8_0) → push to the HF Hub (private).
4. Locally: download the GGUF; `Modelfile` with `FROM ./alfred-2b-q4.gguf` + the TEMPLATE copied from `ollama show qwen3.5:2b --modelfile` → `ollama create alfred-2b-q4` (and `-q8`).
5. `eval.run` on both → compare with the baselines.

**Validate**
- Sane curves.
- Structured `tool_calls` on 5 hand prompts.
- Reports exist.
- If the fine-tuned model is worse than base: diff a rendered training example against a rendered inference prompt (template mismatch) before touching the data or hyperparameters.

## D1: Docs checkpoint 1, "the model works" (also D2, D3, same recipe)
**Implement**
1. `docs/PROGRESS.md`: phase table (status, gate date, evidence link), current key numbers, open issues, next steps.
2. `docs/decisions.md`: decisions since the last checkpoint, each with the reason.
3. `README.md`: status section + how to run what exists so far.
4. `docs/learning/`: one short note per concept introduced, written for the owner (what it is, why it's used here, self-check questions, where in the code):
   - **D1:** chat templates & tool calling, LoRA/QLoRA, synthetic data + contamination, eval metrics.
   - **D2:** MCP, agent loops, prompt injection, quantization/GGUF, BFCL/When2Call.
   - **D3:** DPO, GRPO, reward design and hacking.
5. Commit + tag `checkpoint-D1`.

**Validate**
- A link checker over `docs/` passes.
- Every number points to a file in `eval/reports/`.
- The owner reads it and can explain the phases covered.

## Phase 6: Tool server
**Implement**
1. `tools/guards.py`:
   - `resolve_safe(path)`: expand known folders, `Path.resolve()` (follows junctions), allow-list check, sensitive block list (`.ssh`, `.env*`, browser profile dirs under `AppData`, `*.kdbx`, `Credentials`, …);
   - `assert_no_overwrite`;
   - `is_executable`.
2. `tools/journal.py`: SQLite `actions(id, ts, tool, op, src, dst, extra, undone)`.
   - `record()` / `undo(action_id=None)`:
     - move/rename → move back;
     - copy/zip → the created file goes to the recycle bin;
     - organize → reverse all of its moves;
     - note/reminder/memory → delete the record;
     - recycle → shell restore, falling back to telling the user where the file is in the Recycle Bin.
   - A library function, **not** an MCP tool.
3. Tool bodies:
   - `psutil` (processes, ports, battery, network);
   - `send2trash`;
   - `pypdf`;
   - `zipfile` / `shutil` / `os.startfile`;
   - Start Menu `.lnk` scan for `open_app`;
   - `git status --porcelain=v2 --branch`;
   - `calc.py`: an `ast`-based evaluator (numbers, + − × ÷ % **, parentheses, a few math functions);
   - reminders: a JSON store + a Windows toast while Alfred is running (*ponytail: in-process timer; Task Scheduler if it ever needs to fire while Alfred is closed*).
4. `tools/memory.py`: SQLite `memories(id, ts, text, embedding)`; Ollama embedder (chosen in Phase 1); cosine top-k; keyword fallback.
5. `tools/server.py`: FastMCP over stdio, registering each implementation with the **contract's** signature, docstring and annotations (imported from `contracts`, never redefined).
6. A test: the server's `list_tools()` equals `tools.json`.

**Validate**
- `tests/tools/` with a `tmp_path` sandbox as the allow-list root:
  - happy + error path for each tool;
  - every guard;
  - an undo round-trip for every write tool (folder snapshot before = after undo);
  - `calculate` rejects names, attributes and `__import__`.
- `mcp dev` Inspector lists 25 tools; Claude Desktop answers "what's my disk usage?" through Alfred's server.

## Phase 7: Agent runtime + CLI
**Implement**
1. `agent/loop.py`: `run_turn(chat, user_msg) -> Iterator[Event]`. Events: `token`, `tool_call_proposed`, `confirm_required`, `tool_result`, `error`, `timing`, `done`. This is the **only** interface the CLI and UI use.
   - Schema validation + one retry; ≤ 3 calls per turn.
   - Destructive tools wait for the caller's decision.
   - Tool output wrapped as `<tool_output untrusted="true">`.
   - MCP client session over stdio.
2. `agent/chats.py`: SQLite chats/messages; list/open/continue/delete; a context budget of the last turns within ~4k tokens.
3. `agent/timing.py`: time to first token, per-tool duration, total, tokens/sec → `timing` events + `logs/*.jsonl`.
4. `agent/cli.py` (`alfred` entry point): streaming; a `rich` spinner with elapsed seconds; y/n confirmation; `/undo [id] /chats /open /delete /memories /forget /new /quit`.
5. `eval/e2e/`:
   - 30 tasks `{setup files, request, check(final state, answer)}`, including undo, memory across chats, organize, and denied confirmations;
   - ~20 injection fixtures.

**Validate**
- `tests/agent/` with a scripted fake backend: deny → no disk change; retry; 3-call cap; untrusted wrapping; chat continue/delete; timing events.
- `python -m eval.e2e --backend alfred-2b-q4` → pass rate + invariants all 0.
- **Wi-Fi off:** 5 tasks succeed.

## Phase 8: Minimal web UI
**Implement**
1. `ui/app.py` (Gradio Blocks, bound to 127.0.0.1):
   - sidebar chat list (new / open / delete with confirm);
   - streaming Chatbot;
   - live timer via a 0.1 s `gr.Timer` while a turn runs;
   - tool-call cards;
   - Confirm/Cancel on `confirm_required`;
   - an Undo button + recent actions;
   - a Memory tab;
   - a per-response timing footer.
2. The UI only consumes `run_turn` events and calls the `chats` / `journal` / `memory` functions.
3. `alfred-ui` entry point.

**Validate**
- `tests/ui/test_smoke.py` (fake backend, `gradio_client`: one message → reply + timing).
- Manual checklist with screenshots: timer, confirm, cancel = no change, undo, continue an old chat, delete a chat, memory forget.

## Phase 9: Benchmarks, safety & ablations
**Implement**
1. **BFCL v4:** vLLM on Kaggle serving the bf16 base / SFT models; pinned `bfcl-eval` on the simple, multiple, parallel, relevance and irrelevance categories.
2. **When2Call:** the official scoring on the MCQ test, base vs. SFT.
3. **Safety:** `eval.run --set safety` + the e2e injection suite → refusal, over-refusal, injection resistance.
4. **Quantization:** bf16 vs. Q8 vs. Q4 on in-domain.
5. **Ablations:**
   - `configs/sft_0.8b.yaml`;
   - `configs/sft_fg270m.yaml` (FunctionGemma needs its own chat-format renderer in `mix.py`);
   - evaluate base and fine-tuned for each.
6. Extend `indomain.jsonl` to ~400 (same review flow); rerun the key systems.
7. `eval/results.py` → `RESULTS.md` (tables + confusion matrix PNG).

**Validate**
- All reports present.
- `RESULTS.md` regeneration is deterministic.
- The base model's BFCL score is plausibly near the vendor-reported 43.6 (not exact: different mode and subset).

## D2: Docs checkpoint 2, "the product works"
Same recipe as D1, plus an architecture diagram and CLI/UI how-to-run. Tag `checkpoint-D2`.

## Phase 10: DPO
**Implement**
1. `data/pref.py`:
   - When2Call `train_pref` → (prompt, chosen, rejected).
   - On-policy pairs: sample the SFT model (temperature 0.8, ×4) on ~2k training prompts and score with `eval/score.py`; gold = chosen, failed sample = rejected.
   - Dedup against the test sets.
2. `train/dpo.ipynb`: Unsloth + TRL `DPOTrainer` from the SFT adapter (β 0.1, lr 5e-6, 1 epoch, `configs/dpo_2b.yaml`); GGUF export as in Phase 5.
3. Full eval → `RESULTS.md` row.

**Validate**
- The reward margin rises and chosen log-probs don't collapse.
- Regressions > 2 pts get an error-analysis note.

## Phase 11: GRPO
**Implement**
1. `train/reward.py` (imports `eval/score.py`):
   - 0.2·valid + 0.3·tool_ok + 0.4·args_score + 0.1·decision_ok;
   - −0.3 for a needless abstain/refusal;
   - −1 for an unconfirmed destructive call.
2. `train/grpo.ipynb`: TRL `GRPOTrainer` via Unsloth from SFT (variant: SFT+DPO); 4–8 generations per prompt; ~1–2k stratified prompts; a few hundred steps; KL β > 0; reward components logged separately.
3. Evaluate on a 100-item validation slice every ~50 steps. Stop if accuracy falls while reward rises.
4. Export, full eval, `RESULTS.md` rows.

**Validate**
- `pytest tests/train/test_reward.py`.
- Curves saved (total reward, each component, KL, abstain rate).
- Reward-hacking check documented.

## D3: Docs checkpoint 3, "training story complete"
Same recipe as D1, plus the SFT vs. DPO vs. GRPO write-up. Tag `checkpoint-D3`.

## Phase 12: Copilot comparison & release
**Implement**
1. **Quantitative:** the cloud reference with the same 25 tools on in-domain + e2e (from the existing harness) + cost per 1k requests.
2. **Case study:** 20 tasks in `docs/copilot_tasks.md`. The owner runs them in Windows Copilot and in Alfred with a screen recording → `docs/copilot_results.csv` (success, time, steps, internet needed).
3. **Capability table.**
4. Final README:
   - problem, architecture, setup;
   - results, safety, error analysis;
   - Copilot section;
   - limitations, licences.
5. Public HF model + dataset cards.
6. Demo video (60–90 s): Wi-Fi off → live timer → confirm → undo → continue an old chat using memory.

**Validate**
- Clean-clone run following only the README.
- Every README number traces to a report.

---

## Time plan (approximate)
| When | Phases |
|---|---|
| 22 Oct (today) | 0 (owner setup ~1 h, in parallel with Claude scaffolding), 1, 2, start 3 |
| 23 Oct | finish 3 (owner reviews tests), 4 (generation runs in the background), start 5 on Kaggle |
| 24 Oct | finish 5 → D1 |
| 25–31 Oct | 6, 7, 8, 9(a–d), D2 |
| Nov – early Dec | 9(e–f), 10, 11, D3, 12 |

## End-to-end verification (whole project)
1. `uv run pytest`: all green (contracts, eval, tools, agent, ui, train).
2. `uv run python -m eval.run --backend alfred-2b-q4 --set indomain` reproduces the `RESULTS.md` numbers within noise.
3. `uv run python -m eval.e2e` with Wi-Fi off: reported pass rate, safety invariants all 0.
4. `alfred-ui` manual checklist passes.
5. A clean clone following the README gives a working Alfred.
