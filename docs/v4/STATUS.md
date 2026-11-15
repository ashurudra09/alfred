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
| 1C Masking + frozen lists | in progress (claimed 2026-11-16, branch `v4-1C`) | 0 | worktree `.claude/worktrees/v4-1C` |
| 2 On-policy data | blocked | 1A, 1B | |
| 3 Mix + train | blocked | 2, 1C, owner's go per run | |
| 4D Grammar | blocked | 1A (step D2 also needs 4G's baselines) | |
| 4E Security | blocked | 1A, 1C | |
| 4F Unseen-tools eval | blocked | 1A, 1C | |
| 4G Reliability + baselines | blocked | 1A | |
| 5 Evaluate v4 | blocked | 3 (run A downloaded), 4D, 4E, 4F, 4G | |
| 6 Write-up | blocked | 5 | |

## Waiting on the owner
- Nothing yet. (Next: review ~30 benchmark tasks in step A7, once the A6 baseline has passed the headroom gate; try 5 semantic-search queries in track 1B.)

## Machine
- **Busy since 2026-11-16: track 1A, v3 baseline rerun on the hard suite from commit `562d51d`** (llama-server PIDs 2816 on :8081 and 20968 on :8082, logs `runs/v4/hard_v3_shard{0,1}.log`, ~30 min). No merges into or branch switches in the main checkout until this says idle. (Eval servers: :8081, :8082. The owner's UI server on :8080 is never touched.)

## Track 0: Setup

| Step | State | Date | Commit | Artifacts | Numbers / notes |
|---|---|---|---|---|---|
| 0.1 Branch, plan, status, references, tag | done | 2026-11-15 | this commit | `docs/v4/`, `docs/references.md`, tag `v3-final` | LoRA, APIGen/xLAM, When2Call, BFCL checked against their abstract pages |
| 0.2 Pinned clock `ALFRED_TODAY` | done | 2026-11-15 | 8775f07 | `guards.now()`; `tests/tools/test_tools.py::test_pinned_clock` | read by the system prompt, MCP instructions, notes, reminders, `modified_within_days` |
| 0.3 Sandbox trash `ALFRED_TRASH` | done | 2026-11-15 | 8775f07 | `journal.trash()`; `test_sandbox_trash_and_undo` | undo restores from the sandbox; tool text unchanged |
| 0.4 Frozen 25-tool list | done | 2026-11-15 | 8775f07 | `contracts/tools_1.2.json`; `eval.run --contracts 1.2` | hiding tool 26 in the e2e runner is step A4 |
| 0.5 Throughput probe | done | 2026-11-15 | this commit | `runs/v4/server_808*.log` | v3 Q4, 5 single-call e2e tasks: one server 75 s (15 s/task incl. tool-server start); two servers, 4 threads each: 10 tasks in 93 s (9.3 s/task, 1.6x). Use two servers for long jobs. Verdicts 5/5 = committed v3 report. Find eval servers by command line (`Get-CimInstance Win32_Process`): port lookups return PID 0 on this Windows build; PID 22924-style servers under Ollama are the embedder, never stop them. |
| Verify | done | 2026-11-15 | this commit | | pytest 150 passed with Ollama running (149 + the embedder test); `eval.results` leaves `RESULTS.md` unchanged; 5 e2e verdicts match |

## Track 1A: Benchmark + generator

| Step | State | Date | Commit | Artifacts | Numbers / notes |
|---|---|---|---|---|---|
| A1 Task families | done | 2026-11-15 | f221a3c | `eval/e2e/hard.py` | 12 shared: find_then_act, read_then_compute, pick_extreme, all_except, filtered_bulk, memory_then_act, two_part, recover_empty, ask_then_act, decline_then_continue, notes_and_reminders, count_and_size. 5 held-out: compare_files, act_on_list, deadline_reminder, conditional_act, bulk_rename. Scripted solutions take 1-5 calls (1 only for conditional_act's "just tell me" branch). |
| A2 Parametric templates | done | 2026-11-15 | f221a3c | `eval/e2e/hard.py` (`World`, `Turn`, `HardTask`) | One turn description gives the confirm policy (only the requested change is approved), the exact expected end state (every file), and the scripted agents. A proposal that was not asked for fails the task even though it is declined. |
| A3 Two pools | done | 2026-11-15 | f6f1252 | `hard.tasks("test")`, `hard.tasks("train", n)`; `eval/e2e/hard_test.jsonl` | Test 124 = 84 shared (7 per family) + 40 held-out (8 per family). Train: shared families, seeds from 1000, other file/folder vocabulary and phrasings. Max cosine of a train request to a test request 0.82 (guard limit 0.9), no shared 8-gram. |
| A4 Runner upgrades | done | 2026-11-15 | f221a3c | `eval/e2e/__main__.py` | `--suite --trials --temperature --url --contracts --shard --fresh --show --review`; cache with trajectories in `runs/e2e/<system>/<suite>_<commit>_*.jsonl`; hard tasks pin `ALFRED_TODAY` and use `ALFRED_TRASH`. A run with `--only` or a scripted agent no longer writes a report. |
| A5 Checker validation | done | 2026-11-15 | f221a3c | `tests/eval/test_hard.py`; `python -m eval.e2e --suite hard --system oracle\|null\|wrong\|extra` | oracle 124/124 with invariants 0; null 0/124; wrong 0/124; extra 0/124. pytest 157 passed (4.5 min; the hard tests add about 3 min because Windows scans each new fixture file). |
| A6 v3 baseline + headroom gate | done, failures of the second run not yet read | 2026-11-15 | 78fae0b | `eval/reports/hard_alfred-2b-v3-q4.{json,md}`; trajectories in `runs/e2e/alfred-2b-v3-q4/` | **v3 Q4: 78/124 (62.9%)**, shared 55/84, held-out 23/40, invariants 0/0/0: inside the 30-80% gate. First run (f6f1252) was 75/124; reading its failures found two suite flaws, fixed in 78fae0b for whole families: a prescribed zip name, and facts called 'access code' / 'booking reference' that v3 refused to read out. Still to do: read the 46 failures of the second run for checker false negatives (notes_and_reminders is still 4/7). |
| A7 Owner review (30+ tasks) | todo | | | `uv run python -m eval.e2e --suite hard --review` | ready once the A6 failure read is finished |
| A8 Freeze + dedup guard | todo | | | | current (not frozen) sha256 of `hard_test.jsonl` is printed by `python -m eval.e2e.hard --write` |
| B5 hand-over: semantic-search families | todo | | | | after track 1B step B1 freezes the tool |

## Notes for whoever works next
- Track branches cannot be named `v4/<track>` (git refuses while a branch `v4` exists); 1B uses `v4-1B`.
- A new hard-suite family is one function in `eval/e2e/hard.py` added to `SHARED` or `HELD_OUT`; then
  `python -m eval.e2e.hard --write` and the four scripted runs.
- Shell heredocs in Git Bash turn a double backslash into a single one: write files that contain backslashes (Windows paths in tests)
  with the editor tools, not with `cat <<EOF`.
- The three Phase 1 tracks are independent. 1A should add its semantic-search task families only after step B1
  has frozen the new tool's contract.
