# Requirements: Offline Laptop Assistant with a Fine-Tuned Small Model

Name: **Alfred**: a mini-butler for small laptop tasks (no company branding)
Status: **v3 draft, 21 Oct 2026**. Includes the owner's decisions on tools, memory, guardrails, reversibility, chat history, response timer and the Copilot comparison.
Owner: Ashutosh Rudrabhatla

> **What changed in v3**
> - **Final tool list: 25 tools** (Section 5), including explicit long-term memory (`remember` / `recall`), developer tools, `organize_folder` and `calculate`.
> - **Every destructive action is reversible:** no permanent delete, an action journal, and Undo (Section 6.2).
> - **Minimal guardrails in scope** (Section 6.3): refusal training, sensitive-path blocking, prompt-injection handling, and a safety eval before vs. after fine-tuning.
> - **Chat history** (view / continue / delete) and a **live response timer** (Section 6.4).
> - **A required "How does it compare to Copilot?" deliverable** (Section 8.5).
> - **A pilot gate for the synthetic data teacher** (Section 7.3).
>
> **Changes carried over from v2:** Qwen3.5-2B base model, When2Call dataset, SFT → DPO → GRPO, an open-weight teacher, tools as an MCP server, BFCL v4 for evaluation.

---

## 1. One-line summary
Fine-tune a small open model (Qwen3.5-2B) so it calls a fixed set of 25 laptop tools reliably, run it **fully offline on a laptop CPU** behind a minimal chat UI, and measure how close it gets to a large cloud model (and to Microsoft Copilot) on accuracy, latency, cost and privacy.

## 2. Why this project exists
- **As an engineering project:** real model training (SFT, DPO, GRPO, synthetic data, quantization) applied to agentic AI, with measured results rather than an API wrapper.
- **For a user:** a private assistant for everyday laptop chores. No files go to the cloud, there's no per-query cost, and every change it makes can be undone.
- **The research question:** *Can a small fine-tuned model match a large cloud model on tool calling for a fixed tool set, at a fraction of the size and cost, fully offline?*
- **Positioning vs. Microsoft Copilot:** not a competitor. Copilot is a general cloud product; this is a study of the small on-device model problem that Microsoft (Phi Silica on Copilot+ PCs), Google (FunctionGemma, Gemma 4 E2B) and PC makers are all working on. Section 8.5 makes the comparison concrete.

## 3. Users and example requests
**Primary user:** a CS student or engineer on a Windows laptop.

| Request | Expected behaviour | Category |
|---|---|---|
| "Find PDFs in Downloads from last week with 'transformer' in the name" | `search_files(...)` → list results | tool_call |
| "Which of my notes mention LoRA?" | `search_file_contents(...)` or `search_notes(...)` | tool_call |
| "Why is my C drive full?" | `disk_usage(path="C:\\", top_n=10)` → explain | tool_call |
| "What's running on port 3000?" | `port_in_use(port=3000)` → process name + PID | tool_call |
| "Summarise notes.txt in Documents" | `read_file(...)` → model summarises | tool_call (multi-step) |
| "Clean up my Downloads folder" | `organize_folder(...)` → **shows the plan, asks to confirm** → runs → Undo available | tool_call + confirm |
| "Delete old_resume.pdf" | `move_to_recycle_bin(...)` → **confirm** → restorable | tool_call + confirm |
| "Remember that my resume is in D:\docs\resume" | `remember(...)` | tool_call (memory) |
| "Zip my resume folder" (later chat) | `recall("resume folder")` → `zip_folder(...)` → confirm | multi-step + memory |
| "What's 18% GST on 34,999?" | `calculate(...)` | tool_call |
| "Tell me a joke" / "What's the capital of France?" | Answer directly, no tool | direct |
| "Book me a flight to Goa" | Politely say it can't: no tool fits | cannot_answer |
| "Move the file" | Ask which file and where | request_for_info |
| "How do I build a bomb?" / "What's this user's password?" | **Refuse** | refusal (guardrail) |

## 4. Scope

### In scope (v1)
1. **25 tools** (Section 5), Windows-only, exposed as a **local MCP server** (stdio, no network).
2. **Explicit long-term memory** through `remember` / `recall`, stored locally; the user can view and delete memories.
3. **Reversible actions:** no permanent delete, an action journal, and Undo (Section 6.2).
4. **Minimal guardrails** (Section 6.3).
5. **Chat history** (view, continue, delete past chats) and a **live response timer** (Section 6.4).
6. A **training dataset**: synthetic examples for our tools (open-weight teacher) + public data (When2Call, xLAM-60k) + refusal/safety examples.
7. **Training: SFT → DPO → GRPO.** All three required, each compared in the results table.
8. **Quantized export** (GGUF) and local serving via **Ollama** on CPU.
9. An **agent client** connecting the local model to the MCP server, up to 3 tool calls per request.
10. A **CLI** and a **minimal local web chat UI** (e.g. Gradio).
11. An **evaluation harness** (Section 8), including the **Copilot comparison** (Section 8.5).
12. A public repo, model and dataset on the Hugging Face Hub, a README with results, and a short demo video.

### Out of scope (v1)
- **Permanent deletion** of any user file (the recycle bin only). Deleting the app's *own* data (chats, memories) at the user's request is allowed.
- Email, calendar, or anything needing OAuth / online accounts.
- Web browsing or search (it breaks the offline claim).
- Voice and vision input (we fine-tune text only).
- macOS/Linux (**Windows-only confirmed**).
- *Automatic* memory (the model deciding by itself what to remember): v1 memory is explicit only.
- Thinking/reasoning mode in the shipped model (too slow on CPU; only measured as a comparison).
- A full content-moderation system (guardrails are minimal; Section 6.3).

## 5. Tool set (final, 25 tools)

| # | Tool | Group | Effect | Confirm? | Undo? |
|---|---|---|---|---|---|
| 1 | `search_files(query, folder, extension?, modified_within_days?)` | Files | read | No | — |
| 2 | `search_file_contents(text, folder, extension?)` | Files | read | No | — |
| 3 | `list_directory(path)` | Files | read | No | — |
| 4 | `read_file(path, max_chars?)` (txt, md, pdf text) | Files | read | No | — |
| 5 | `disk_usage(path, top_n?)` | Files | read | No | — |
| 6 | `move_file(source, destination)` | Files | write | **Yes** | Yes |
| 7 | `rename_file(path, new_name)` | Files | write | **Yes** | Yes |
| 8 | `copy_file(source, destination)` (never overwrites) | Files | write | **Yes** | Yes (copy goes to the recycle bin) |
| 9 | `zip_folder(source, destination)` (never overwrites) | Files | write | **Yes** | Yes (zip goes to the recycle bin) |
| 10 | `organize_folder(path, strategy="by_type")` (shows the full plan first) | Files | write | **Yes** | Yes (all moves reversed) |
| 11 | `move_to_recycle_bin(path)` | Files | write | **Yes** | Yes (restore from the Recycle Bin) |
| 12 | `open_path(path)` (opens in the default app; refuses executables/scripts) | Open | side effect | No | — |
| 13 | `open_app(name)` (only apps found in the Start Menu) | Open | side effect | No | — |
| 14 | `system_info()` (CPU, RAM, battery, OS) | System | read | No | — |
| 15 | `top_processes(sort_by, n?)` | System | read | No | — |
| 16 | `network_status()` (Wi-Fi name, IP, connected?) | System | read | No | — |
| 17 | `port_in_use(port)` → process name + PID | Developer | read | No | — |
| 18 | `git_status(repo_path)` → branch, ahead/behind, changed files | Developer | read | No | — |
| 19 | `create_note(title, content)` (app-owned notes folder) | Productivity | app data | No | Yes |
| 20 | `search_notes(query)` | Productivity | read | No | — |
| 21 | `set_reminder(text, time)` (Windows notification) | Productivity | app data | No | Yes (cancel) |
| 22 | `list_reminders()` | Productivity | read | No | — |
| 23 | `remember(fact)` | Memory | app data | No | Yes (forget from the UI) |
| 24 | `recall(query)` → top matching memories | Memory | read | No | — |
| 25 | `calculate(expression)` (safe parser, no `eval`) | Utility | pure | No | — |

Notes:
- All tools live in **one MCP server** (FastMCP, official MCP Python SDK). Each tool's JSON schema comes from its type hints and docstring and is the single source of truth for training prompts, validation and docs.
- **25 tools is deliberately a hard selection problem for a 2B model.** That makes fine-tuning gains easier to see, but it also lengthens the prompt (see the latency risk in Section 13).
- Answering directly, asking a clarifying question, saying it can't help, and refusing are behaviours the model learns. They are not tools.
- Undo is a **UI/CLI command** (`/undo` and an Undo button), not a model tool. Undo is the user's decision, not the model's.

## 6. Functional requirements

### 6.1 Core agent
| ID | Requirement | Priority |
|---|---|---|
| FR1 | Given a request and the tool schemas, the model outputs a tool call (name + JSON args), a direct answer, a clarifying question, a "can't do that", or a refusal. | P0 |
| FR2 | Tool calls are validated against the JSON schema before running; an invalid call is rejected and the model gets one retry with the error. | P0 |
| FR3 | Tool results go back to the model, which writes the final answer in plain language. | P0 |
| FR4 | Multi-step requests (e.g. recall → zip, search → read → summarise) are supported up to 3 tool calls per request. | P1 |
| FR5 | Every request, tool call, argument, result and timing is logged to a local JSONL file. | P1 |
| FR6 | The model backend is swappable via config (fine-tuned local / base local / cloud API), all through an OpenAI-compatible endpoint, so one harness compares them all. | P0 |

### 6.2 Reversibility ("every destructive action is reversible")
| ID | Requirement | Priority |
|---|---|---|
| FR7 | No tool can permanently delete a user file. "Delete" means `move_to_recycle_bin`. | P0 |
| FR8 | Tools marked "Confirm" show the exact action (and for `organize_folder`, the full list of planned moves) and run only after the user confirms (typing yes in the CLI, a button in the UI). | P0 |
| FR9 | No tool ever overwrites an existing file; if the destination exists, the tool fails with a clear error. | P0 |
| FR10 | Every write action is recorded in an **action journal** (what changed, from where to where, when). | P0 |
| FR11 | `/undo` (CLI) and an Undo button (UI) reverse the last action, or a chosen past action, using the journal. Created files (copies, zips) go to the recycle bin; moves and renames are reversed; recycled items are restored from the Recycle Bin (or the user is pointed there if a programmatic restore fails). | P1 |

### 6.3 Guardrails (minimal, in scope)
| ID | Requirement | Priority |
|---|---|---|
| FR12 | **Folder allow-list:** file tools only operate inside allowed folders (default: Documents, Downloads, Desktop, the app folder and user-added repo folders). | P0 |
| FR13 | **Sensitive-path block list:** even inside allowed folders, tools refuse `.ssh`, `.env` files, browser profile folders, credential/keychain stores, password-manager exports and similar. | P0 |
| FR14 | `open_path` refuses executables and scripts (`.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.msi`, `.lnk`, …); `open_app` only launches apps found in the Start Menu. | P0 |
| FR15 | **Refusal behaviour:** harmful requests (weapons, malware, etc.) and requests for credentials/passwords are refused. Refusal examples are part of the SFT data. | P0 |
| FR16 | **Prompt-injection handling:** text returned by tools (file contents, notes, memories) is passed to the model marked as untrusted data. Instructions inside it are not followed, and a write action triggered right after reading untrusted content still needs confirmation. | P1 |
| FR17 | **Safety eval:** ~50 harmful/sensitive prompts + ~20 prompt-injection files; report refusal rate and injection-resistance rate **for the base model vs. each fine-tuned model** (fine-tuning is known to weaken safety behaviour, so this must be measured, not assumed). | P1 |

### 6.4 Memory, chat history and timer
| ID | Requirement | Priority |
|---|---|---|
| FR18 | **Explicit memory:** `remember` stores a fact with a timestamp in a local SQLite database; `recall` finds the most relevant memories by embedding similarity (a small local embedding model served by Ollama) with a keyword fallback. | P1 |
| FR19 | Memories are viewable and deletable in the UI (a memory panel) and the CLI (`/memories`, `/forget <id>`). Deleting a chat does **not** delete memories. | P1 |
| FR20 | **Chat history:** every chat is saved locally (SQLite). The UI shows a list of past chats (title, date); the user can open one to read it, continue it, or delete it (with confirmation). The CLI has `/chats`, `/open <id>` and `/delete <id>`. | P1 |
| FR21 | When a chat is continued, recent turns are sent to the model up to a context budget (e.g. last N turns / ~4k tokens), so CPU latency stays bounded; older turns are kept in storage but not sent. | P1 |
| FR22 | **Live response timer:** while the assistant is working, the UI shows a running elapsed-time counter (updating ~10×/s), and the CLI shows a spinner with elapsed seconds. Responses are streamed. | P1 |
| FR23 | After each response, show a **timing breakdown**: total time, time to first token, each tool call's duration, and tokens/sec. The same numbers feed the latency metrics (Section 8.2). | P1 |

### 6.5 UI
| ID | Requirement | Priority |
|---|---|---|
| FR24 | A **minimal local web UI** (e.g. Gradio): chat box, streamed answers, a running timer, tool calls shown as they happen, Confirm/Cancel buttons for write actions, an Undo button, a chat-history sidebar and a memory panel. | P1 |
| FR25 | A **CLI** with the same core behaviour (confirmations, `/undo`, `/chats`, `/memories`, timer). | P0 |

## 7. ML requirements

### 7.1 Base model (decided)

| Role | Model | Why | Licence |
|---|---|---|---|
| **Primary (decided)** | **Qwen3.5-2B** (non-thinking mode) | Best documented tool use under ~2B: BFCL-V4 43.6, TAU2 48.8 (vendor-reported, thinking mode). In Ollama with a `tools` tag (~2.7–3.1 GB). Unsloth has a 2B notebook. | Apache 2.0 |
| Size ablation | **Qwen3.5-0.8B** | Same family, BFCL-V4 25.3 → lots of room for fine-tuning gains; fast on CPU (~1.2 GB) | Apache 2.0 |
| Extreme-small ablation | **FunctionGemma-270M** | Google's function-calling-only model; Google reports 58% → 85% after fine-tuning on Mobile Actions | Gemma licence |
| Considered, not chosen | Gemma 4 E2B | Native function calling, but 5.1B total params (2.3B "effective") → heavier on laptop RAM; Tau2 24.5 | Apache 2.0 |
| Considered, not chosen | LiquidAI LFM2.5-1.2B | Fast on-device, but no verified tool benchmark and a custom licence | LFM licence |

Session 1 still measures **our own** baseline scores and CPU latency (not vendor numbers).

### 7.2 Training data

| Source | Size used | Purpose | Licence |
|---|---|---|---|
| **Synthetic examples for our 25 tools** (open-weight teacher, 7.3) | 5,000–8,000 (more tools → more data) | In-domain tool selection, argument filling, multi-step traces including memory (`recall` → action) | Ours (teacher is Apache 2.0) |
| **Refusal / safety examples** (synthetic + hand-written) | ~300–500 | Harmful requests, credential requests, prompt-injection-in-file cases (FR15–16) | Ours |
| **NVIDIA When2Call** `train_sft` (15k) and `train_pref` (9k) | ~3,000 SFT + preference pairs for DPO | When *not* to call: answer directly, ask for info, can't answer | CC-BY-4.0, commercial use OK |
| **Salesforce xLAM-function-calling-60k** | 2,000–5,000 | General tool-calling ability; reduces overfitting to our schemas | CC-BY-4.0 (gated: accept terms + cite APIGen) |
| NousResearch hermes-function-calling-v1 | optional | Extra multi-turn examples | check card |
| Dropped: ToolACE | — | Licence unclear (paper is CC-BY-NC-ND) | — |

Data rules:
- Varied phrasing (Hinglish, typos, casual and terse requests) so the model doesn't learn templates.
- Every example is validated automatically (tool exists, args pass the schema, confirmation flow is correct) before it enters training.
- All sources are converted to **one chat format**: the Qwen3.5 chat template with `tools=[...]`.
- A dataset card with sources, licences, generation prompts and counts per category and per tool.

### 7.3 Synthetic data teacher
- **Use an open-weight teacher** (Apache 2.0 or similar), so there's no licence question about training on its outputs. Closed-model terms (Anthropic, Google, OpenAI) generally restrict using their outputs to train models. **Closed-model outputs are only used if the owner has checked that the provider's current terms allow it.**
- **Candidates:** a large current open-weight model served through Groq / Cerebras / OpenRouter free tiers, or self-hosted on Kaggle (e.g. Qwen3.6-35B-A3B on 2×T4; feasibility to confirm in session 1).
- **Don't depend on the Gemini free tier** (limits were cut in April 2026, and free-tier prompts may be used for training).
- **Pilot gate (session 1):** generate ~100 examples, then check:
  - ≥ 90% pass automatic validation;
  - ≥ 90% are correct in a 50-example manual spot-check;
  - phrasing is visibly varied.
  If the gate fails, try a larger open-weight teacher before considering anything else.
- **Efficiency:** 10–20 examples per request in JSON, cache everything, dedupe.
- **The test set is NOT generated by the teacher** (Section 8.1).

### 7.4 Training
**Stage 1: SFT (P0)**
- QLoRA (4-bit base + LoRA adapters) with **Unsloth** (on top of Hugging Face TRL/PEFT) on a **Kaggle 2×T4 / P100**.
- Loss only on assistant/tool-call tokens.
- Log hyperparameters, seed and train/val loss curves; keep the best checkpoint by validation.
- Budget: each run ≤ 2 GPU-hours.

**Stage 2a: DPO (P1, done first)**
- DPO on When2Call `train_pref` + our own rejected samples (wrong tool, hallucinated args, needless tool call, missing confirmation, complying with a harmful request), starting from the SFT model.
- Cost is similar to SFT: offline pairs, no generation during training.

**Stage 2b: GRPO (P1, after DPO; required)**
- Reinforcement learning with a verifiable reward, starting from the SFT model (and, as a variant, from SFT+DPO). Reward components:
  - schema-valid (+);
  - correct tool (+);
  - argument match with partial credit (token-F1 rather than all-or-nothing exact match, which 2026 small-agent RL work found trains better);
  - correct abstain/clarify/refuse (+);
  - penalties for needless abstains.
- Short runs (a few hundred steps), 4–8 samples per prompt, KL penalty on. Watch for reward hacking.
- Report **SFT vs. SFT+DPO vs. SFT+GRPO** (and SFT+DPO+GRPO if time allows).

### 7.5 Export and serving
- Merge LoRA → export **GGUF** with Unsloth → quantize (Q4_K_M; Q8_0 for comparison) → serve with **Ollama** (or llama.cpp `llama-server`) on CPU.
- Keep the tool-schema system prompt **identical across requests** so the server can reuse its cached prefix (prompt caching) and avoid reprocessing 25 schemas every time.
- Report the accuracy lost to quantization (bf16 vs. Q8 vs. Q4).

## 8. Evaluation requirements

### 8.1 Test sets
1. **In-domain held-out set**: ~400 examples covering all 25 tools (≥ 10 each), multi-step memory cases, and direct / clarify / can't-answer cases.
   - **Contamination guard:** hand-written or hand-edited, *not* produced by the training teacher; deduplicated against training data by embedding similarity; every example hand-checked.
2. **BFCL v4** subset via the pinned `bfcl-eval` package (simple, multiple, parallel, relevance, irrelevance). Checks general ability didn't regress.
3. **When2Call test** (3,652 multiple-choice + 300 LLM-judged): a public benchmark for the call / ask / abstain decision.
4. **Safety set** (FR17): ~50 harmful/sensitive prompts + ~20 prompt-injection files.
5. **End-to-end tasks**: ~30 scripted tasks against a sandbox folder with known files (including undo, memory and organize flows), judged on the final state and the answer.

### 8.2 Metrics
| Metric | Definition |
|---|---|
| Valid-call rate | Output parses and passes schema validation |
| Tool selection accuracy | Correct tool name, or correctly no tool (+ per-tool confusion matrix) |
| Argument accuracy | BFCL-style AST match; normalised match for free text |
| Decision accuracy / F1 | Tool call vs. direct vs. ask vs. can't-answer vs. refuse |
| Refusal rate / injection resistance | On the safety set (FR17) |
| End-to-end success rate | Scripted task completed correctly (and correctly undone where tested) |
| Latency | Time to first token, time to first tool call, total time on the laptop CPU; tokens/sec (from FR23 timings) |
| Footprint | Model size on disk, peak RAM |
| Cost | ₹/$ per 1,000 requests (local ≈ 0; cloud at list price) |
| Safety invariants | Write actions run without confirmation and files overwritten or permanently deleted (**all must be 0**) |

### 8.3 Comparisons (the results table)
| System | Purpose |
|---|---|
| Qwen3.5-2B base, same prompt | Baseline: what fine-tuning adds |
| **Qwen3.5-2B SFT** (Q4, CPU) | Stage-1 product |
| **Qwen3.5-2B SFT + DPO** (Q4, CPU) | Does preference tuning help? |
| **Qwen3.5-2B SFT + GRPO** (Q4, CPU) | Does RL with a verifiable reward help, and how does it compare with DPO? |
| Same model at bf16 / Q8 | Quantization cost |
| Qwen3.5-0.8B base → fine-tuned | Size ablation |
| FunctionGemma-270M base → fine-tuned | Extreme-small ablation |
| Large cloud model with the same 25 tools | Upper-bound reference (also part of 8.5) |

### 8.4 Error analysis
- Confusion matrix over tools and decision categories.
- Top 3 failure categories, each with examples and a hypothesis.

### 8.5 Comparison with Microsoft Copilot (required deliverable)
**Requirement:** the README contains a section **"How does it compare to Microsoft Copilot?"** that answers the question with evidence, in three parts:

1. **Quantitative: same tools, frontier model.** Run the in-domain test set and the end-to-end tasks with a frontier cloud model given the **same 25 tools**, and compare accuracy, latency and cost per 1,000 requests against our local model. (Copilot has no API to send it 400 scripted requests, so this is the fair automatic comparison.)
2. **Hands-on case study: Copilot vs. ours.** 20 fixed real tasks drawn from Section 3 (e.g. find a file, explain disk usage, check port 3000, organize Downloads, delete with undo). Do each one by hand in Windows Copilot and in our assistant, and record:
   - success / partial / fail;
   - time taken;
   - number of user steps;
   - whether the task needed the internet.
   Screen-record it, and describe it honestly as a small case study (n = 20).
3. **Capability table:** works offline? · data leaves the device? · cost per request · can act on local files? · reversible actions/undo? · custom tools? · model size · runs without an account?

## 9. Non-functional requirements
| Area | Requirement |
|---|---|
| Cost | ₹0: Kaggle free GPU (~30 h/week, ≤ 12 h sessions; check your own quota in Kaggle settings), free API tiers, open models |
| Offline | After install, the assistant works with networking off (shown in the demo). MCP runs over stdio and Ollama on localhost, so no network is needed |
| Hardware | Runs on an 8–16 GB RAM laptop CPU, no GPU |
| Latency target | Measured and reported; target < 5 s to the first tool call on CPU with a warm prompt cache |
| Safety | Section 6.2 and 6.3 invariants hold; checked by the safety eval and end-to-end tests |
| Privacy | Chats, memories, notes and logs stay on the device in the app folder; the user can delete any of them |
| Reproducibility | Seeds, pinned requirements (`mcp<2`, pinned `bfcl-eval`, Unsloth version), scripts for data / train / eval; model and dataset on the HF Hub |
| Licences | Every dataset and model licence recorded in the README; no closed-model outputs in training data unless their terms allow it |

## 10. Deliverables
1. GitHub repo: `tools/` (MCP server), `agent/` (client, journal/undo, memory, chat store), `ui/` (web UI) and the CLI, `data/` (generation + validation), `train/` (SFT, DPO, GRPO notebooks/scripts), `eval/` (harness + results), README.
2. Hugging Face model card (LoRA adapters + GGUF) and dataset card.
3. README with: the problem, architecture diagram, results table (8.3), safety results, error analysis, **"How does it compare to Microsoft Copilot?" (8.5)**, limitations, how to run.
4. A 60–90 s demo video: networking off → request with a live timer → tool call → confirmation → result → Undo → continuing a past chat with memory.

## 11. Success criteria (targets; report the real numbers whatever they are)
| Criterion | Target |
|---|---|
| Fine-tuned vs. base, in-domain tool + argument accuracy | Clear gain (≥ 15 points; expected larger for 0.8B and 270M) |
| Fine-tuned vs. cloud model (same tools) | Within ~5 points in-domain |
| Valid-call rate | ≥ 98% |
| Decision accuracy (call / ask / abstain / refuse) | ≥ 85% in-domain; improvement over base on When2Call |
| BFCL v4 subset | No more than a small drop vs. base |
| Stage 2 (DPO and GRPO, each) | Measurable gain over SFT-only on decision accuracy, or a documented negative result with an explanation |
| Refusal rate on the safety set | No worse than the base model; ≥ 95% on harmful prompts |
| Safety invariants (8.2) | All 0 |
| Copilot comparison (8.5) | Published, all three parts |
| Runs fully offline on CPU | Yes |

## 12. Milestones
- **M1 (24 Oct):** dataset (including refusal examples), the SFT model, and in-domain numbers (base vs. fine-tuned vs. cloud). Anything unfinished is reported as in progress.
- **M2 (31 Oct):**
  - MCP server with all 25 tools;
  - agent client with journal/undo and guardrails;
  - CLI and minimal UI with chat history, memory and the live timer;
  - BFCL, When2Call and safety numbers;
  - quantization comparison.
- **M3 (December):**
  - DPO, then GRPO;
  - size ablations;
  - the Copilot comparison (8.5);
  - demo video, error analysis, model/dataset cards;
  - the owner can explain every component.

## 13. Risks
| Risk | Mitigation |
|---|---|
| **25 tool schemas make the prompt long → slow first response on CPU** | Compact schemas (fine-tuning lets descriptions be short); identical system prompt for prefix caching; measure in session 1; P2 fallback: retrieve only the top-k relevant tools per request |
| More tools → more data needed and more confusion between similar tools (e.g. `search_files` vs. `search_file_contents` vs. `search_notes`) | ≥ 200 examples per tool; targeted examples of easily-confused pairs; per-tool confusion matrix |
| Free API limits slow down data generation | Open-weight teacher, self-hosted on Kaggle as fallback; batch 10–20 examples per call; cache |
| Teacher quality too low | Pilot gate (7.3); automatic validation drops bad examples; larger open model as fallback |
| Kaggle quota / session limits | ≤ 2 h runs; checkpoint often; Colab as backup |
| No Unsloth Kaggle notebook for Qwen3.5 | Adapt Unsloth's Kaggle *Qwen2.5-Coder Tool Calling* notebook; Colab 2B notebook as fallback |
| Qwen3.5's thinking mode loops / is slow | Ship in non-thinking mode |
| Fine-tuning weakens the base model's safety behaviour | Refusal data in SFT and DPO; safety eval before vs. after (FR17) |
| Prompt injection via file contents | FR16 + injection test files + confirmation still required for writes |
| GRPO is slow on a T4 | Short runs, 4–8 samples per prompt, small prompt subset; DPO first, so a stage-2 result exists anyway |
| GRPO reward hacking / instability | Partial-credit reward, penalties for needless abstains, track reward and eval accuracy together, KL penalty on |
| Recycle Bin restore is fiddly to do from code on Windows | Undo falls back to telling the user where the file is in the Recycle Bin; covered by end-to-end tests |
| Test contamination | Hand-written tests, different source than training, similarity dedup |
| BFCL harness doesn't talk to Ollama directly | Serve via vLLM on Kaggle for BFCL runs |
| Overclaiming | Only measured numbers; Section 12 rule |

## 14. Resources by step

**Models**
- Qwen3.5-2B: https://huggingface.co/Qwen/Qwen3.5-2B · Ollama: https://ollama.com/library/qwen3.5
- Qwen3.5 small-series release coverage: https://gigazine.net/gsc_news/en/20260303-qwen-3-5-small
- FunctionGemma-270M: https://huggingface.co/google/functiongemma-270m-it · fine-tuning guide (Mobile Actions): https://ai.google.dev/gemma/docs/mobile-actions
- Gemma 4 model card: https://ai.google.dev/gemma/docs/core/model_card_4
- LFM2.5-1.2B: https://featherless.ai/models/LiquidAI/LFM2.5-1.2B-Instruct

**Datasets**
- When2Call (data + paper + code): https://huggingface.co/datasets/nvidia/When2Call · https://arxiv.org/abs/2504.18851
- xLAM function-calling 60k: https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k · APIGen paper: https://arxiv.org/abs/2406.18518
- Hermes function calling v1: https://huggingface.co/datasets/NousResearch/hermes-function-calling-v1
- Magnet (multi-turn synthesis method, for ideas): https://arxiv.org/abs/2503.07826

**Training**
- Unsloth notebooks index (Kaggle "Qwen2.5-Coder 1.5B Tool Calling", FunctionGemma "Reason before Tool Calling", Qwen3.5 0.8B/2B, GRPO notebooks): https://unsloth.ai/docs/get-started/unsloth-notebooks
- Unsloth Qwen3.5 fine-tuning guide: https://unsloth.ai/docs/models/qwen3.5/fine-tune
- NVIDIA NeMo FunctionGemma + xLAM LoRA recipe (reference): https://docs.nvidia.com/nemo/automodel/recipes-e2e-examples/function-calling
- GRPO background: https://towardsdatascience.com/how-grpo-trains-small-language-models-with-verifiable-rewards/ · RL with verifiable rewards for small (0.8B Qwen3.5) agents: https://arxiv.org/abs/2609.28765 · VerlTool / ToolRL reward design: https://arxiv.org/abs/2509.01055
- Safety erosion from fine-tuning (why FR17 exists): Qi et al., "Fine-tuning Aligned Language Models Compromises Safety" (2023), https://arxiv.org/abs/2310.03693

**Tools / agent runtime**
- MCP Python SDK (FastMCP; pin `mcp<2`): https://pypi.org/project/mcp/
- Example: MCP client with a local Ollama model: https://pypi.org/project/ollmcp/

**Evaluation**
- BFCL dataset: https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard · harness: https://github.com/ShishirPatil/gorilla · how to run it (EvalScope): https://evalscope.readthedocs.io/en/latest/third_party/bfcl_v3.html
- Small-model BFCL study on edge devices: https://arxiv.org/abs/2511.22138
- τ²-bench (reference only): https://github.com/sierra-research/tau2-bench

**Free compute / APIs**
- Free GPU overview 2026 (Kaggle ~30 h/week): https://gpuperhour.com/blog/free-cloud-gpus-and-credits
- Free LLM API comparison 2026: https://openrouter.ai/blog/tutorials/free-llm-apis-compared/
- Gemini API rate limits (check AI Studio for your quota): https://ai.google.dev/gemini-api/docs/rate-limits

## 15. Decisions and open questions

**Decided (21 Oct 2026)**
- Primary model: **Qwen3.5-2B**.
- Training: **SFT → DPO → GRPO, all required.**
- UI: **minimal local web UI** plus the CLI, with **chat history** and a **live response timer**.
- OS: **Windows-only.**
- Tools: **the final 25-tool list** in Section 5.
- **Explicit long-term memory** (`remember` / `recall`).
- **Every destructive action is reversible** (recycle bin, journal, Undo; no overwrites).
- **Minimal guardrails in scope**, with a safety eval.
- **The Copilot comparison is a required deliverable** (8.5).
- Teacher: **open-weight**, gated by the session-1 pilot.

- Name: **Alfred**.

**Still open**
- Nothing. Implementation follows `docs/implementation-plan.md`.
