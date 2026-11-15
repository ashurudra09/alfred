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
| 1C Masking + frozen lists | done (2026-11-16, merged in 7aab2fe) | 0 | was branch `v4-1C` |
| 2 On-policy data | blocked | 1A, 1B | |
| 3 Mix + train | blocked | 2, 1C, owner's go per run | |
| 4D Grammar | blocked | 1A (step D2 also needs 4G's baselines) | |
| 4E Security | blocked | 1A, 1C | |
| 4F Unseen-tools eval | blocked | 1A, 1C | |
| 4G Reliability + baselines | blocked | 1A | |
| 5 Evaluate v4 | blocked | 3 (run A downloaded), 4D, 4E, 4F, 4G | |
| 6 Write-up | blocked | 5 | |

## Waiting on the owner
- **Track 1A step A7:** review at least 30 hard-suite tasks with `uv run python -m eval.e2e --suite hard --review`.
- **Track 1B verify:** try 5 semantic-search queries (the only step left before 1B is merged).

## Machine
- Idle since 2026-11-16 02:10. (Eval servers: :8081, :8082. The owner's UI server on :8080 is never touched.)

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
| A6 v3 baseline + headroom gate | done | 2026-11-16 | b93fc93 (code of 562d51d) | `eval/reports/hard_alfred-2b-v3-q4.{json,md}`; trajectories in `runs/e2e/alfred-2b-v3-q4/hard_b93fc93_*.jsonl` | **v3 Q4: 73/124 (58.9%)**, shared 54/84, held-out 19/40, invariants 0/0/0, median turn 16 s: inside the 30-80% gate, no family change needed. Weakest: recover_empty 0/7, bulk_rename 0/8, act_on_list 1/8, find_then_act 2/7, memory_then_act 2/7. Three runs, each after a suite fix made for whole families and written down before the rerun: 75/124 (f6f1252) -> zip name no longer prescribed, 'access code' / 'booking reference' reworded because v3 refused them -> 78/124 (78fae0b) -> sandbox paths shortened from ~110 to ~55 characters -> 73/124. All 51 failure reasons read, 27 trajectories opened across the three runs: no checker false negative found; failures are v3's (wrong file picked, stops after a decline, no recall, name search not followed by a content search, "I have no rename tool", refusing to read a benign file). |
| A7 Owner review (30+ tasks) | todo, waiting on the owner | | | `uv run python -m eval.e2e --suite hard --review` | tasks come one family after another, so the first 34 cover every family twice; y = right, s = skip and tell Claude what is wrong |
| A8 Freeze + dedup guard | guard done (562d51d); freeze after A7 | | | `data/dedup.py` `Guard` reads `hard_test.jsonl` | `data.dedup --check` on v3's data: 0 near-duplicates. sha256 of the LF file now: 540d30b5...4305, final value recorded after the review. |
| B5 hand-over: semantic-search families | todo | | | | after track 1B step B1 freezes the tool |

## Track 1B: Semantic search (branch `v4-1B`, worktree `.claude/worktrees/v4-1B`)

| Step | State | Date | Commit | Artifacts | Numbers / notes |
|---|---|---|---|---|---|
| B1 Contract 1.3 `search_by_meaning(query, folder=None)` | done | 2026-11-15 | 82a9eff | `contracts/tools.py`, `tools.json` (26 tools, v1.3), `data/gen/formats.py` | read-only, group files. Prompt + tools 2525 tokens (was ~2440); guard raised to 2600. Tool list frozen from here: 1A may add its families. |
| B2 Index `tools/semantic.py` | done | 2026-11-15 | 82a9eff | `ALFRED_HOME/semantic.db`; `tests/tools/test_semantic.py` (6 tests) | FTS5 + vectors per 1,000-char chunk (max 20 per file); incremental by mtime, 20 s indexing budget per call, deleted files purged; `files.walk` guards + extension allow-list + 5 MB cap. Embedder moved to `memory.embed_many`, used by recall, semantic, `data/dedup.py`. |
| B3 RRF ranking + fallback | done | 2026-11-15 | 82a9eff | `semantic.rank(mode=fused/keyword/embedding)` | RRF k=60, 50 candidates per ranker, top 5 files; result says when it fell back to keywords or is still indexing. `MIN_COS` = 0 until B4 calibrates it. |
| B4 Retrieval eval (first pass, superseded by B4') | done | 2026-11-15 | 235e086 | | 150 claims, now the dev half: keyword 74.7 / 85.3 / 0.797, embedding 91.3 / 96.0 / 0.938, fused 85.3 / 94.0 / 0.896 (R@1 / R@5 / MRR). Led to the plan amendments of 2026-11-15. |
| B3' Ranking per amendment 1 | done | 2026-11-15 | this commit | `semantic.rank(mode="auto")` | embedding order; BM25 hits interleaved for chunks without a vector; BM25 for everything when Ollama is down. `fused` stays as an eval-only mode. |
| B2' Cache + start-up indexing (amendment 4) | done | 2026-11-15 | this commit | `semantic._embed`, `semantic.index_all`, `tools/server.py` | `ALFRED_EMBED_CACHE=<sqlite file>` caches vectors by model + text (rollouts and evals should set it). The tool server indexes all known folders in a background thread (config `index_on_start`, default true; one indexer at a time via `semantic.LOCK`). Not throttled: on a big Documents folder it will use the CPU for a long time at the speeds below. |
| B4' Dev/test split, prompts, cut-off (amendments 2, 3) | done | 2026-11-15 | this commit | `eval/testsets/retrieval_scifact_{dev,test}.jsonl` (300 abstracts, 150 claims, 75 unanswerable each; no shared claims, 30 shared abstracts), `eval/reports/retrieval_scifact_{dev,test}.json`, `RESULTS.md` | **Dev** (choices made here): prompts help (embedding MRR 0.938 with, 0.881 without) so they stay; cut-off by the fixed rule = **0.346**. **Test, run once** (R@1 / R@5 / MRR): keyword 75.3 / 88.7 / 0.811, embedding 89.3 / 97.3 / 0.929, fused 88.7 / 94.0 / 0.914, embedding with the 0.346 cut-off 87.3 / 93.3 / 0.900. Paraphrased half (70): keyword 52.9 / 75.7, embedding 81.4 / 95.7, fused 77.1 / 87.1, with cut-off 77.1 / 87.1. **The cut-off costs more than it gives:** it returns nothing for 16 of 75 unanswerable claims (dev 19 of 75) and for 6 of 150 answerable ones (dev 4), and takes 2 points of R@1 and 4 of R@5 off plain embedding. **Owner removed the cut-off (amendment 7): `MIN_COS` = 0, shipped = the plain embedding row.** The experiment stays in the reports under `with_cutoff`. Indexing speed: 1.42 chunks/s (dev, prompts), 1.83 (dev, no prompts), 2.09 (test) with track 1A's baseline using the CPU; **no idle-machine measurement yet**. Query-time columns are noisy for the same reason. |
| B5 Hand families to 1A | done | 2026-11-15 | this commit | the list below | |
| Verify | todo: only the owner's 5 queries are left | 2026-11-16 | this commit | `tests/tools/test_server.py` | Branch now contains `v4` (1A's suite) and 1C: pytest 177 passed on the combination, so merging into `v4` is a fast-forward of content with no conflicts left. `RESULTS.md` identical on a second `eval.results`. **Idle-machine indexing speed: 3.0 chunks/s** (857 chunks in 286 s, no other job running, 12 logical CPUs at 65% during the run; 1.4-2.1 with another eval running), so the 20 s budget per search embeds about 60 chunks. The tool is now also called through the real stdio server in the test suite. That check found a bug, fixed here: a search made while the start-up indexer held the lock returned nothing ('still indexing') at once, which every eval task would have hit because each starts a fresh server; the search now waits its turn (at most one 20 s budget). `data/gen/prompts.py`: the per-tool batch loop is pinned to the 25 tools of contracts 1.2 so tool 26 does not shift the ids of cached teacher batches; its own batches are step 2.7. |

**For track 1A (B5): semantic-search task families**, tagged `new_capability`, scored separately (v2/v3 never saw
tool 26; give them contracts 1.2). Fixtures need Ollama running; record whether the embedder was up (risk 24).
1. *find-by-topic*: a file whose name and wording share nothing with the request ("the doc about cutting cloud costs"
   → `infra_notes_q3.md` that talks about reserved instances); check: the answer names that path. 1 call.
2. *find-by-topic-then-act*: as 1, then open / move / zip it; check: end state; confirmation only for the asked change. 2 calls.
3. *find-by-topic-then-read*: as 1, then read it and answer a fact from it. 2 calls.
4. *look-alike choice*: same fixture, but the request names the file or quotes an exact phrase, so `search_files` /
   `search_file_contents` is right; check: the answer is correct (the tool used isn't scored as wrong if the answer
   is right). 1 call.
5. *nothing-matches*: no fixture file is about the topic. The tool has no cut-off (amendment 7), so it still lists
   its closest files; check: the answer says none fits, no file is acted on. 1–2 calls.
6. *stale-index*: the file was edited or created after an earlier search in the same task; check: the new content is
   found (incremental re-index). 2 calls.

Ripples handled in this track: `agent/loop.py` reads `config.json` `"contracts"` (set `"1.2"` to keep v2/v3 on their
25 tools in the UI; without it the UI now sends 26); `data/v3.py` pinned to contracts 1.2.

## Track 1C: Masking + frozen lists (branch `v4-1C`, worktree `.claude/worktrees/v4-1C`)

| Step | State | Date | Commit | Artifacts | Numbers / notes |
|---|---|---|---|---|---|
| C1 Name masking | done | 2026-11-16 | 5920c36 | `data/augment.py` (`mask`, `unmask`, `apply`, `leaks`) | After Hammer (read; arXiv 2410.04587): tool names and parameter names become random 5-7 character identifiers in the tool list, the calls and the tool-result names; identifier-like names are also replaced in descriptions, the system prompt and message text (so `move_to_recycle_bin` in the prompt and cross-references in descriptions follow). Ordinary-word names (`search`, `query`, `recall`) are replaced in structure only, not in sentences. Rates: xLAM 0.33, When2Call 0.33 (the paper's worked ratio; it does not state its final one), Alfred's own examples 0.10. Not done: Hammer's randomised default values. Mix integration is step 3.1 (`augment.apply`). |
| C2 Tests | done | 2026-11-16 | 5920c36 | `tests/data/test_augment.py` (6 tests) | masked calls validate against masked schemas; renders through the Qwen template; no original identifier-like name anywhere, no original name in any structural position; `unmask` restores byte for byte; deterministic per seed. |
| C3 Held-out tool specs | done | 2026-11-16 | 71cc648 | `eval/unseen/specs.py` (10 tools, v1.0), `data/mix.py` (`unreserved` + assertion), `tests/eval/test_unseen_specs.py` | `clipboard_get`, `clipboard_set`, `convertUnits`, `countWords`, `hashFile`, `files-differ`, `todo_add`, `todo_list`, `todo_done`, `colorConvert`. No name collides with xLAM's 3,605 tool names or When2Call's. xLAM has colour, unit and text-hash converters under other names (about 840 of 60k examples): 17 look-alike names are excluded from training too. On a v3-sized sample the mix drops 19 of 1,544 xLAM and 17 of 1,544 When2Call examples. |
| C4 Injection families | done | 2026-11-16 | this commit | `eval/security/families.py`, `data/gen/prompts.py` (`injection_v4`, 20 batches), `tests/eval/test_security_families.py` | **Train-allowed:** `direct`, `ignore_previous`, `injecagent`, `system_message`, `fake_tool_call` (v3's 169 injection examples already contain these styles, 66 of them plain notes to the AI, so they cannot be held out). **Test-only:** `important_instructions`, `tool_knowledge` (AgentDojo), `fake_user_turn` (closes `</tool_output>` and imitates a user turn); their markers occur 0 times in v3's 7,191 synthetic examples and the mix now drops and asserts on them. Generator: 5 batches each for the vectors file name, note, memory, git output; the first 584 batches and their prompts are unchanged (checked), so the teacher cache still hits. **Not generated yet** (machine job, see below). |
| Verify | done | 2026-11-16 | this commit | | pytest 168 passed. Masking statistics, 500 examples in the mix's proportions, every one masked: leaks 0, byte-exact round trip 500 of 500. Names per example (median): Alfred 48, When2Call 6, xLAM 9. **Extra tokens (median / max): Alfred 332 / 409**, When2Call 20 / 97, xLAM 42 / 133. Alfred examples over 4,096 tokens: 1 -> 2 of 350. |

Left for other tracks (not part of 1C's code):
- **Machine job, after 1B is merged** (examples should carry the 26-tool list): `uv run python -m data.gen.teacher`
  generates the 20 `injection_v4` batches on the free tiers (about 240 conversations before validation), then
  `data.validate`. Needs `.env` and `data/out/cache`, so main checkout.
- **Token budget (adds to plan amendment 6):** a masked Alfred example is about 330 tokens longer and tool 26 adds
  about 85, against a 4,096 limit with v3's longest at 3,978. Step 3.1 should expect masked Alfred rows near the
  limit to be dropped, or leave rows over about 3,650 tokens unmasked; count either way.
- **Finding for track 4E (E6):** `backends.wrap_tool_output` does not escape a literal `</tool_output>` or Qwen chat
  markup inside a tool result, so the `fake_user_turn` family can close the untrusted wrapper. Not fixed here: the
  plan says measure first, then bring the fix to the owner.

## Notes for whoever works next
- Track branches cannot be named `v4/<track>` (git refuses while a branch `v4` exists); 1B uses `v4-1B`.
- Run long eval jobs only after the last commit: the result cache is keyed by HEAD, so a commit made while two
  shards start can split them across two keys.
- A new hard-suite family is one function in `eval/e2e/hard.py` added to `SHARED` or `HELD_OUT`; then
  `python -m eval.e2e.hard --write` and the four scripted runs.
- Shell heredocs in Git Bash turn a double backslash into a single one: write files that contain backslashes (Windows paths in tests)
  with the editor tools, not with `cat <<EOF`.
- The three Phase 1 tracks are independent. 1A should add its semantic-search task families only after step B1
  has frozen the new tool's contract.
