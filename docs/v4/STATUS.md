# Alfred v4: status

The plan is [PLAN.md](PLAN.md). This file is the ledger: read it first, update it after every step.

## Protocol for a new chat
1. Read this file and `docs/v4/PLAN.md`; run `git fetch`, `git log --oneline -15 v4`, `git status`.
2. Summarise in a few lines: phases done, tracks in progress (and who claimed them), what is waiting on the owner,
   what the machine is busy with.
3. Pick the first track below whose state is **ready** (all prerequisites `done`, nobody has claimed it). If a
   claimed track has had no commit for over a day, say so and ask before taking it over.
4. **Claim it before any work:** set its state to `in progress (claimed <date>, branch v4/<track>)` and commit that
   one-line change to `v4` first.
5. Work step by step. After each step: run its verification, fill the step's row (date, commit, artifacts, numbers),
   commit. A step found `running` is checked for its artifact before being redone.
6. When the track's last step is verified: merge the track branch into `v4`, set the track to `done`, and set any
   track whose prerequisites are now all done to `ready`.
7. If nothing is ready, say what is claimed, blocked or waiting on the owner, and stop.

Rules that always apply: no paid API usage (Groq free tier, Cerebras signup credit only); no training run without
the owner's go in that turn; never stop or reuse the llama-server on :8080 (evals use :8081 / :8082 through
`ALFRED_LOCAL_URL`, stop only your own PID); score each model with the prompt and tool list it was trained on
(v2: prompt 1.1, contracts 1.2; v3: prompt 1.2, contracts 1.2); push only when the owner says so.

Code and unit tests may be done in a worktree on `v4/<track>`. Anything needing a model, the teacher keys or
generated data (`.env`, `data/out/`, `runs/` are gitignored and exist only in the main checkout) is a machine job:
main checkout, branch `v4`, one job per port, logged on the Machine line. No merges or branch switches in the main
checkout while a machine job runs.

## Tracks

| Track | State | Prerequisites | Claimed by / branch |
|---|---|---|---|
| 0 Setup | done (2026-11-15) | none | |
| 1A Benchmark + generator | in progress (claimed 2026-11-15) | 0 | main checkout, branch `v4` directly: git cannot create `v4/1A` while a branch named `v4` exists |
| 1B Semantic search | in progress (claimed 2026-11-15, branch `v4-1B`) | 0 | worktree `.claude/worktrees/v4-1B` (`v4/1B` is impossible while `v4` exists) |
| 1C Masking + frozen lists | ready | 0 | |
| 2 On-policy data | blocked | 1A, 1B | |
| 3 Mix + train | blocked | 2, 1C, owner's go per run | |
| 4D Grammar | blocked | 1A (step D2 also needs 4G's baselines) | |
| 4E Security | blocked | 1A, 1C | |
| 4F Unseen-tools eval | blocked | 1A, 1C | |
| 4G Reliability + baselines | blocked | 1A | |
| 5 Evaluate v4 | blocked | 3 (run A downloaded), 4D, 4E, 4F, 4G | |
| 6 Write-up | blocked | 5 | |

## Waiting on the owner
- Nothing yet. (Later: review ~30 benchmark tasks in step A7; try 5 semantic-search queries in track 1B.)

## Machine
- Idle. (Eval servers: :8081, :8082. The owner's UI server on :8080 is never touched.)

## Track 0: Setup

| Step | State | Date | Commit | Artifacts | Numbers / notes |
|---|---|---|---|---|---|
| 0.1 Branch, plan, status, references, tag | done | 2026-11-15 | this commit | `docs/v4/`, `docs/references.md`, tag `v3-final` | LoRA, APIGen/xLAM, When2Call, BFCL checked against their abstract pages |
| 0.2 Pinned clock `ALFRED_TODAY` | done | 2026-11-15 | 8775f07 | `guards.now()`; `tests/tools/test_tools.py::test_pinned_clock` | read by the system prompt, MCP instructions, notes, reminders, `modified_within_days` |
| 0.3 Sandbox trash `ALFRED_TRASH` | done | 2026-11-15 | 8775f07 | `journal.trash()`; `test_sandbox_trash_and_undo` | undo restores from the sandbox; tool text unchanged |
| 0.4 Frozen 25-tool list | done | 2026-11-15 | 8775f07 | `contracts/tools_1.2.json`; `eval.run --contracts 1.2` | hiding tool 26 in the e2e runner is step A4 |
| 0.5 Throughput probe | done | 2026-11-15 | this commit | `runs/v4/server_808*.log` | v3 Q4, 5 single-call e2e tasks: one server 75 s (15 s/task incl. tool-server start); two servers, 4 threads each: 10 tasks in 93 s (9.3 s/task, 1.6x). Use two servers for long jobs. Verdicts 5/5 = committed v3 report. Find eval servers by command line (`Get-CimInstance Win32_Process`): port lookups return PID 0 on this Windows build; PID 22924-style servers under Ollama are the embedder, never stop them. |
| Verify | done | 2026-11-15 | this commit | | pytest 150 passed with Ollama running (149 + the embedder test); `eval.results` leaves `RESULTS.md` unchanged; 5 e2e verdicts match |

## Track 1B: Semantic search (branch `v4-1B`, worktree `.claude/worktrees/v4-1B`)

| Step | State | Date | Commit | Artifacts | Numbers / notes |
|---|---|---|---|---|---|
| B1 Contract 1.3 `search_by_meaning(query, folder=None)` | done | 2026-11-15 | 82a9eff | `contracts/tools.py`, `tools.json` (26 tools, v1.3), `data/gen/formats.py` | read-only, group files. Prompt + tools 2525 tokens (was ~2440); guard raised to 2600. Tool list frozen from here: 1A may add its families. |
| B2 Index `tools/semantic.py` | done | 2026-11-15 | 82a9eff | `ALFRED_HOME/semantic.db`; `tests/tools/test_semantic.py` (6 tests) | FTS5 + vectors per 1,000-char chunk (max 20 per file); incremental by mtime, 20 s indexing budget per call, deleted files purged; `files.walk` guards + extension allow-list + 5 MB cap. Embedder moved to `memory.embed_many`, used by recall, semantic, `data/dedup.py`. |
| B3 RRF ranking + fallback | done | 2026-11-15 | 82a9eff | `semantic.rank(mode=fused/keyword/embedding)` | RRF k=60, 50 candidates per ranker, top 5 files; result says when it fell back to keywords or is still indexing. `MIN_COS` = 0 until B4 calibrates it. |
| B4 Retrieval eval | todo | | | | corpus source needs the owner's OK (download + licence) |
| B5 Hand families to 1A | todo | | | | |
| Verify | todo | | | | pytest 156 passed (worktree, Ollama running) |

Ripples handled in this track: `agent/loop.py` reads `config.json` `"contracts"` (set `"1.2"` to keep v2/v3 on their
25 tools in the UI; without it the UI now sends 26); `data/v3.py` pinned to contracts 1.2.

## Notes for whoever works next
- Shell heredocs in Git Bash turn a double backslash into a single one: write files that contain backslashes (Windows paths in tests)
  with the editor tools, not with `cat <<EOF`.
- The three Phase 1 tracks are independent. 1A should add its semantic-search task families only after step B1
  has frozen the new tool's contract.
