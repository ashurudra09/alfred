# Alfred v4: multi-step, unseen tools, measured reliability and security

## Context
v3 scores 98.6% on the in-domain set, so nothing can show a gain there. v4 makes the project harder to dismiss by
measuring and improving what is still weak: multi-step tasks, tools the model was never trained on, run-to-run
reliability and prompt-injection resistance, plus one new capability (semantic file search).

Items in scope (your numbering): **1** hard multi-step benchmark · **2** grammar-constrained decoding ·
**3** reliability metric · **4** on-policy correction data from real execution · **5** unseen-tool generalisation by
name masking · **8** security evaluation · **9** semantic file search.

Decisions already made by you:
- Training data builds on **v3's set as it is** (the Claude-written examples stay and stay disclosed). Every *new*
  v4 example comes from the open-weight teacher (gpt-oss-120b on the free Groq / Cerebras tiers) or from real
  execution. Claude never writes v4 training data.
- Semantic search is a **trained 26th tool** (contracts 1.3).
- **Two full training runs**: A = main v4; B = same data without name masking (attribution). I ask for your go
  before each one, in the turn it starts.
- No calendar; estimates per phase. Work that does not depend on the trained model runs while Kaggle trains.

Standing rules that apply to every step: no paid API usage; never touch the llama-server on :8080 (evals use
:8081 / :8082 via `ALFRED_LOCAL_URL`, stop only my own PIDs); each model is scored with the prompt and tool list it
was trained on; commits on branch `v4`, pushed only when you say.

---

## How progress survives across chats
Created in step 0.1, committed after every step:

| File | Purpose |
|---|---|
| `docs/v4/PLAN.md` | This plan, copied into the repo. Changes are appended under "Amendments", never silently edited. |
| `docs/v4/STATUS.md` | The ledger a new chat reads first. Track states: `blocked` (prerequisites not done), `ready`, `in progress`, `done`. Step states: `todo`, `running`, `done`, `blocked`. Layout below. |
| `docs/references.md` | Bibliography: each paper or project, its link, and the file in Alfred that uses it. Linked from a short "Methods and references" section in `README.md`. Entries are added in the step that first uses them. |
| `eval/reports/`, `data/out/v4/`, `runs/v4/` | Results, generated data and logs (reports committed; `data/out` and `runs` stay gitignored, their summaries go in STATUS). |

All paths are relative to the repo root, `C:\work\interview prep\projects\alfred`. Phase 0 creates these files, so
it is done in the chat that approves this plan; every later chat starts from them.

**What a new chat does when told "check status.md and plan.md, give me a brief summary and begin a track that is
ready"** (this protocol is written at the top of STATUS.md, so the chat needs no other context):
1. Read `docs/v4/STATUS.md` and `docs/v4/PLAN.md`; run `git fetch`, `git log --oneline -15 v4`, `git status`.
2. Summarise in a few lines: phases done, tracks in progress (and who claimed them), what is waiting on you, what
   the machine is busy with.
3. Pick the first track whose state is **ready**: every prerequisite in the table below is `done` and nobody has
   claimed it. If a claimed track has had no commit for over a day, say so and ask before taking it over.
4. **Claim it** before any work: set the track to `in progress (claimed <date>, branch v4/<track>)` in STATUS and
   commit that one-line change to `v4` first, so two chats cannot start the same track.
5. Work step by step. After each step: run its verification, write result numbers, artifact paths and the commit
   into the step's row, commit. A step found `running` is checked for its artifact before being redone.
6. When the track's last step is verified: merge the track branch into `v4`, set the track to `done`, and mark any
   track whose prerequisites are now all done as `ready`.
7. If nothing is ready (everything is claimed, blocked or waiting on you), say which, and stop.

**STATUS.md layout:** the protocol above · a track table (track, state, prerequisites, claimed by, branch) · a
"Waiting on you" list (reviews, go-aheads, decisions) · a "Machine" line (which job owns which port, started when,
from which commit) · one section per track with a row per step (id, state, date, commit, artifacts, numbers, notes).

**Track states and prerequisites**

| Track | Prerequisites (all must be `done`) |
|---|---|
| 0 Setup | none |
| 1A Benchmark + generator | 0 (its semantic-search task families are added once step B1 has frozen the tool) |
| 1B Semantic search | 0 |
| 1C Masking + frozen lists | 0 |
| 2 On-policy data | 1A, 1B |
| 3 Mix + train | 2, 1C, and your go-ahead for each run |
| 4D Grammar | 1A (step D2 also needs 4G's baselines) |
| 4E Security | 1A, 1C |
| 4F Unseen-tools eval | 1A, 1C |
| 4G Reliability + baselines | 1A |
| 5 Evaluate v4 | 3 (run A downloaded), 4D, 4E, 4F, 4G |
| 6 Write-up | 5 |

**Two kinds of work, two places.** Code and unit tests can be done in a separate worktree on `v4/<track>`. Anything
that needs a model, the teacher keys or generated data (`.env`, `data/out/`, `runs/*.gguf` are gitignored and exist
only in the main checkout) is a **machine job**: it runs from the main checkout on `v4`, one job per port, logged on
the "Machine" line. While a machine job is running nobody merges into or switches branches in the main checkout.

Nothing in the repo is written as study notes: papers appear only as references next to the code that uses them,
in `docs/references.md`, `docs/decisions.md` and docstrings.

**Citation rule:** a paper is cited only after its abstract page was fetched and the specific claim checked in that
step. To verify before use (ids from memory or one search, not yet confirmed): SCoRe (arXiv 2509.14257, ICML 2026),
SOD (2605.07725), DAgger (1011.0686), Hammer (2410.04587), AgentDojo (2406.13352), InjecAgent, τ-bench (pass^k),
grammar-constrained decoding (Geng et al. 2023; Willard & Louf 2023), llama.cpp GBNF docs, reciprocal rank fusion
(Cormack et al. 2009), BM25, EmbeddingGemma, plus Wilson and McNemar for the statistics already in `eval/results.py`.

---

## Dependency map

```
Phase 0 (setup)
   │
Phase 1  ── Track A  benchmark + task generator ──┐
(parallel)  Track B  semantic search tool  ───────┼──► Phase 2 (on-policy data) ──► Phase 3 (mix, probe, TRAIN A, TRAIN B)
            Track C  masking + frozen name lists ─┘                                        │ Kaggle, ~10 h per run
                                                                                           │
Phase 4  ── Track D grammar · Track E security · Track F unseen-tools eval · Track G reliability + baselines
(code can be written from the end of Phase 1; its baseline runs use the laptop while Kaggle trains)
                                                                                           ▼
                                                                  Phase 5 (evaluate v4) ──► Phase 6 (write-up)
```
Only Phases 1A, 1B, 1C and 2 must finish before training. Tracks touch different files, so they can be separate
chats. The one shared resource is the laptop CPU: Phase 4's code is written whenever its prerequisites are done, and
its model runs are queued for when the CPU is free (during the Kaggle training in particular).

## Estimates

| Phase | My work | Machine time | Your time |
|---|---|---|---|
| 0 Setup | 0.5 day | 15 min | – |
| 1A Benchmark + generator | 1.5–2 days | ~2 h (v3 baseline) | ~2 h reviewing tasks |
| 1B Semantic search | 1–1.5 days | 30 min | 15 min trying it |
| 1C Masking + frozen lists | 1 day | – | – |
| 2 On-policy data | 1 day | 10–18 h rollouts (overnight) + teacher quota over 1–2 days | 1 h auditing a sample |
| 3 Mix + train | 0.5 day | ~0.5 h probe + ~10 h per run (Kaggle) | two go-aheads |
| 4D Grammar | 1 day | 2 h | – |
| 4E Security | 1.5 days | ~1.5 h per system | 1 decision if a hole is found |
| 4F Unseen-tools eval | 1.5 days | ~2 h per system | 30 min reviewing items |
| 4G Reliability + baselines | 0.5 day | 6–10 h | – |
| 5 Evaluate v4 | 1 day | 10–15 h local + Kaggle benchmarks | ship decision |
| 6 Write-up | 1 day | – | review |

Sequential total is about 11–13 working days; with tracks run in parallel chats, about 7–8 days elapsed.

---

## Phase 0: Setup and frozen baseline (sequential)

- **0.1** Branch `v4` from `main`; create `docs/v4/PLAN.md`, `docs/v4/STATUS.md`, `docs/references.md` (seeded with
  what the repo already uses: LoRA, When2Call, xLAM/APIGen, BFCL, Wilson, McNemar, each verified), README section
  linking it. Tag `v3-final`. Update the memory note to point at STATUS.
- **0.2** Pinned clock: `ALFRED_TODAY=YYYY-MM-DD` honoured by `src/alfred/agent/loop.py:56`,
  `src/alfred/tools/server.py:34` and the `now` defaults in `src/alfred/tools/productivity.py`. Without it, date
  tasks and recorded training prompts change from day to day.
- **0.3** Sandbox trash: `ALFRED_TRASH=<dir>` makes `files.move_to_recycle_bin` and `journal.restore_from_recycle_bin`
  use a folder instead of the real Recycle Bin. New suites and rollouts set it; the existing 50-task suite keeps the
  real bin so its numbers stay comparable.
- **0.4** Frozen 25-tool list for old models: save `src/alfred/contracts/tools_1.2.json`; `eval.run --contracts 1.2`
  and the e2e runner (via the existing `disabled_tools` setting) score v2/v3 without tool 26.
- **0.5** Throughput probe: 5 existing e2e tasks on one eval server (:8081) and on two (:8081 + :8082, 4 threads
  each, 12 logical cores). Record seconds per task and whether two servers help.
- **Verify:** `uv run pytest` green (147 + new tests for 0.2–0.4); the 5 e2e tasks give the same verdicts as the
  committed v3 report; `uv run python -m eval.results` leaves `RESULTS.md` unchanged; STATUS committed.

## Phase 1: Foundations needed before training (three parallel tracks)

### Track A: hard multi-step benchmark and the training-task generator (item 1)
Extends `eval/e2e/` (reuses `Task`, `Ctx`, `setup`, `run_task`, the safety invariants).
- **A1** Task families from the failure classes already logged in `data/to_fix.md` and the regression misses:
  search-then-act, read-then-compute, pick-from-results (oldest, largest, "all except"), filtered bulk operations,
  memory-then-act, multi-part answers, recovery after an empty or error result, ask-when-underspecified mid-chain,
  declined confirmation then continue. Each family is labelled with its expected number of calls (2–5).
- **A2** Parametric templates in `eval/e2e/hard.py`: a seeded fixture builder (file names, sizes, dates, contents),
  several phrasings of the request, and a `check` computed from the fixture's ground truth (final file state and
  facts the answer must contain). The confirm policy is per task: confirmations are accepted only for the change the
  request asked for.
- **A3** Two pools. **Test**: ~120 tasks = ~80 from "shared" families (new seeds, names and phrasings) + ~40 from
  **held-out families** that no training rollout ever uses. **Train**: the shared families only, different seeds.
- **A4** Runner upgrades in `eval/e2e/__main__.py`: `--suite`, `--trials K`, `--temperature`, `--url`, per-task
  result cache so a run resumes, full trajectory dump (messages with real tool results), pinned date, sandbox trash,
  optional hidden tool 26.
- **A5** Checker validation without any model: every test task has a scripted oracle (list of tool calls run through
  `LocalTools`) that must pass; a do-nothing agent and a deliberately wrong variant must fail.
- **A6** v3 baseline, one pass at temperature 0. **Headroom gate:** v3 should land between about 30% and 80%. If it is
  above, difficulty is raised by changing or adding *families*, never by keeping or dropping individual tasks
  according to whether v3 failed them.
- **A7** You review at least 30 tasks, including one from every held-out family (`--show` prints request, fixture,
  expected end state); recorded under `hard:owner` in `eval/testsets/reviews.json` via the existing
  `eval/review.py` mechanism.
- **A8** Freeze: SHA-256 of the test task file in STATUS; `data/dedup.py` `Guard` extended to include the hard-suite
  requests.
- **Verify:** oracle 100%, null agent 0%, same seed gives identical fixtures on a second run, train and test seeds and
  phrasings are disjoint (asserted in a test), pytest green.

### Track B: semantic file search (item 9)
- **B1** Contract 1.3 in `src/alfred/contracts/tools.py`: a read-only tool (working name `search_by_meaning(query,
  folder=None)`), described so it is distinguishable from `search_files` (names) and `search_file_contents` (exact
  phrase). Regenerate `tools.json`; update `tests/contracts`; add its result format to `data/gen/formats.py`.
- **B2** Index in `src/alfred/tools/semantic.py`: SQLite in `ALFRED_HOME` with file rows (path, mtime), text chunks
  and embeddings, and an FTS5 table for keyword ranking. Text extraction reuses `read_file`'s extractors; embeddings
  reuse the batched Ollama call now in `data/dedup.py` (moved next to `memory.embed` and imported by both).
  Incremental by mtime, bounded per call, deleted files purged. Guards: `resolve_safe`, `is_sensitive`, `is_hidden`,
  extension allow-list, size cap.
- **B3** Ranking: keyword (BM25) and embedding cosine fused by reciprocal rank; keyword-only fallback when Ollama is
  not running (same pattern as `memory.recall`).
- **B4** Retrieval evaluation with no LLM: a fixture corpus (~300 short documents from a source whose licence is
  checked and recorded) and labelled queries, half paraphrased so they share no keywords. Recall@1, recall@5 and MRR
  for keyword-only, embedding-only and fused. Table added to `RESULTS.md` by `eval/results.py`.
- **B5** Task families that need the tool are handed to Track A (they enter both pools, tagged `new_capability`, and
  are reported separately because v3 cannot do them).
- **Verify:** unit tests (incremental re-index, sensitive and hidden files never indexed, deleted files disappear,
  fallback path), retrieval table reproducible, index and query latency recorded, you try 5 queries on the fixture.

### Track C: name masking and the lists that must be frozen before training (data side of items 5 and 8)
- **C1** `data/augment.py`: consistent renaming of tool names and argument names to random identifiers across the
  tool list, the assistant's calls and the tool-result messages, so the model has to read descriptions. Rates and
  exactly what is masked follow the Hammer paper (read and cited in this step); starting point: a share of the
  xLAM examples, and a smaller share of Alfred examples where every mention (descriptions that cross-reference
  other tools, the system prompt's `move_to_recycle_bin`) is renamed too.
- **C2** Tests: a masked example validates against its masked schemas, renders through the chat template, contains
  no original name anywhere, and un-masking restores the original byte for byte.
- **C3** Frozen held-out tool specs (names, descriptions, schemas) for Track F in `eval/unseen/specs.py`, and an
  assertion in `data/mix.py` that none of them appears in any training row.
- **C4** Injection attack families in `eval/security/families.py`, split into **train-allowed** and **test-only**.
  New v4 injection training examples (generated by the open teacher through `data/gen/teacher.py`, new vectors:
  file names, notes, memory, git output) use train-allowed families only.
- **Verify:** pytest; masking statistics on a 500-example sample recorded in STATUS.

## Phase 2: On-policy data from real execution (item 4; needs A, B)
New code in `data/onpolicy.py`; method follows SCoRe (student acts, teacher fixes the earliest error), with DAgger as
the underlying idea and SOD for error cascades. The reinforcement-learning stage of SCoRe is out of scope and that is
stated in `docs/decisions.md`.
- **2.1** Instantiate train tasks from Track A's train pool: pilot of 300, then scale to about 1,500–2,000 depending
  on the pilot's failure rate and time per task. Each gets a random user name and a random pinned date.
- **2.2** Student rollouts: v3 Q4 with prompt 1.2 and its 25 tools through the real tools (runner from A4,
  trajectories dumped). Tasks tagged `new_capability` need tool 26, which v3 has never seen, so for those the
  teacher drives the whole trajectory through the real tools (tagged `teacher_exec`), under the same acceptance
  rule as 2.5.
- **2.3** Triage by the task's `check` and the safety invariants: pass → kept as a real-result example; fail, or pass
  with an unrequested change → correction queue.
- **2.4** Correction: the teacher sees the request, the trajectory with real tool outputs and the checker's failure
  reason, and returns the index of the earliest wrong assistant turn plus a replacement turn. The prefix is then
  **replayed in a fresh sandbox**, the replacement is executed for real, and the student continues from there; up to
  three corrections per task. Teacher responses are cached by prompt hash like `data/gen/teacher.py` does.
- **2.5** Acceptance is by execution, not by the teacher's opinion: a trajectory is kept only if the final state
  passes `check` with all invariants at zero. Tasks the teacher cannot fix are dropped and counted (the scripted
  oracle may complete at most 10% of the kept set, tagged).
- **2.6** Conversion to `Example` (`source="onpolicy"`): sandbox paths rewritten to `C:\Users\<user>\…`, the recorded
  system prompt kept, then `data/validate.check` (extended for the new source) and the 4,096-token limit.
- **2.7** Tool-26 examples: ~20 teacher batches (single call, ask, look-alike confusions with the two other search
  tools) via the existing generator with a new `HINTS` entry, to reach the ≥ 200-examples-per-tool rule.
- **2.8** Audit: counts per outcome (passed first time, fixed at turn i, dropped), and 40 random kept examples read
  by you and me; findings go in `data/card.md`.
- **Verify:** every kept trajectory is replayed once more from an empty sandbox and passes; `data.dedup --check`
  finds 0 near-duplicates of any test set (in-domain, safety, regressions, hard, unseen-tools, security, retrieval
  queries); no kept example contains the real user profile path; validator pass rate and all counts in STATUS.

## Phase 3: Mix, probe and train (needs 2, C)
- **3.1** `data/mix.py` for v4: v3's synthetic set + on-policy + tool-26 + new injection examples + When2Call + xLAM,
  with masking applied for run A. Every Alfred example carries the 26-tool list and system prompt 1.2 (the prompt
  text changes only if Phase 1 shows it must, and then it becomes 1.3 and is recorded). A second output without masking for run B.
  Rows over 4,096 tokens are counted (the 26th schema adds tokens to every Alfred example; v3's longest was 3,978).
- **3.2** Size check against the Kaggle session: v3's 10,285 examples took 9.2 h; if v4 projects past ~10.5 h, the
  saturated single-call examples are subsampled (recorded) so a full epoch fits.
- **3.3** `train/configs/sft_2b_v4.yaml` (same LoRA settings as v3 so the data is the only change) and
  `train/package_data.py` upload; `data/stats.md` and the data card regenerated.
- **3.4** With your go: 20-step probe (`PROBE=True` in `train/sft_kernel/sft.py`) to confirm seconds per step and
  that the kernel still runs end to end; then **run A**. Run B after your second go (at the same time if Kaggle
  allows two GPU sessions and the weekly quota covers it; checked then).
- **3.5** Download adapters and GGUFs (`--file-pattern '\.gguf$'`, the CLI runs out of memory on the merged
  weights), `train_summary.json`, loss curve to `docs/`.
- **Verify:** probe projection under the session limit; loss curve and best checkpoint recorded; `smoke.json` read;
  the Q4 GGUF loads on :8081 and answers the first 10 in-domain items sensibly.

## Phase 4: Independent of the trained model (runs while Kaggle trains)

### Track D: grammar-constrained decoding (item 2)
- **D1** Find out what `llama-server` build 11804 already constrains when `tools=` is passed (it parses Qwen3.5's XML
  calls today; whether a grammar is applied is unknown).
- **D2** Measure the starting point first: invalid-call and retry rates in the hard-suite baselines, with held-out
  tools, and with sampling on. **All single-turn sets are already 100% valid**, so if these are also ~0 the feature
  is reported as a guarantee with no measured accuracy change.
- **D3** `src/alfred/agent/grammar.py`: builds a GBNF grammar from the live tool specs for Qwen3.5's call format
  (free text, or one or more calls whose name is one of the tools and whose arguments match the schema's types,
  enums and required fields); sent through `Backend.stream`'s `extra_body`, behind a setting.
- **D4** Tests: the grammar accepts every gold call of the in-domain set and a sample of training calls, and rejects
  malformed ones.
- **D5** Effect on in-domain accuracy (paired McNemar against the same model without it), hard suite, first-token
  latency, tokens per second and cached-prefix tokens.
- **Verify:** D4 green; D5 table in `RESULTS.md`; default on only if nothing regresses.

### Track E: security evaluation (item 8)
- **E1** Read AgentDojo (paper and repository licence) and InjecAgent; map their attack templates to Alfred. A case
  = user task × injection vector (file content, file *name* in a listing, note, memory, git output, PDF text) ×
  attacker goal (trash or move a file, leak a secret into a note or memory, open an executable, set a reminder) ×
  attack family from C4.
- **E2** `eval/security/` on the Track A runner, about 240 cases; reuses `Ctx.proposed_any` and `Ctx.app_writes`.
- **E3** Metrics: task success without attack, task success under attack, attack success at the model (the injected
  action was proposed) and at execution under three simulated users (confirms nothing, confirms only what they asked
  for, confirms everything). Attacks through tools that need no confirmation (`create_note`, `remember`,
  `set_reminder`, `open_app`) are reported separately. Wilson intervals; seen and test-only families separately.
- **E4** Checker validation: a scripted agent that obeys every injection scores 100% attack success, one that ignores
  them scores 0%.
- **E5** Baselines for base, v2 and v3.
- **E6** If unconfirmed tools are exploitable, I bring you the finding and a proposed fix (require confirmation for
  app writes in a turn that has read untrusted content) before building anything.
- **Verify:** E4 green; reports committed; numbers in `RESULTS.md`.

### Track F: unseen-tools evaluation (eval side of item 5)
- **F1** `src/alfred/agent/loop.py` builds tool definitions from the live MCP specs (name, description, schema)
  instead of the frozen `tools.json`; `McpTools` accepts several servers from `config.json`. A test asserts the
  prompt for the built-in tools stays byte-identical (prefix cache and training distribution). Tools from other
  servers require confirmation unless they declare themselves read-only, and say that undo is not available.
- **F2** `eval/unseen/server.py`: the 8–10 held-out tools frozen in C3, really implemented so outcomes can be checked.
- **F3** Three measurements: (i) ~80 single-turn items over the held-out tools, scored by `eval/score.py`, including
  items where none fits; (ii) ~30 end-to-end tasks mixing built-in and held-out tools, with oracles as in A5;
  (iii) the 276 in-domain items with every tool and argument **renamed** (the scorer maps names back), whose drop
  against the original measures name memorisation. BFCL stays as the public check.
- **F4** You review a sample of (i); baselines for v2 and v3; prompt-token and latency cost of 36 tools recorded.
- **Verify:** oracles pass, the renamed set with the *original* names reproduces the committed score exactly, pytest.

### Track G: reliability metric and baselines (item 3)
- **G1** Confirm the pass^k definition in the τ-bench paper; implement the aggregate in the runner: per-task success
  over K trials, mean pass rate and pass^k for k = 1…K (unbiased estimator). Trials differ by sampling
  (temperature 0.7; the shipped temperature 0 would repeat itself) and, separately, by the templates' alternative
  phrasings.
- **G2** Hard-suite baselines: base, v2, v3 at temperature 0; K = 5 trials for v3; the teacher gpt-oss-120b through
  the same loop on the free tier.
- **Verify:** estimator unit-tested on hand-computed cases; reports committed.

## Phase 5: Evaluate v4 (needs run A; run B for 5.4)
- **5.1** Existing gates, v4 Q4 with contracts 1.3: in-domain 276, safety 48, regressions 46, the 50-task suite;
  When2Call and the BFCL subset on Kaggle with the pinned kernels (the v4 LoRA is uploaded to the `alfred-adapters`
  Kaggle dataset first; these kernels use GPU quota too).
- **5.2** New suites: hard (temperature 0 and K = 5), unseen tools (three measurements), security, grammar on and off.
- **5.3** Semantic-search tasks end to end.
- **5.4** Run B on hard, unseen, renamed and BFCL, for the masking attribution.
- **5.5** `eval/results.py`: new tables and paired comparisons (reusing `wilson`, `mcnemar`, `paired`), a note that
  many comparisons are being made, and `RESULTS.md` still byte-stable.
- **5.6** Every v4 failure on the hard suite read and categorised into `docs/patch_notes.md`.
- **Gate (no regression):** v4 is not significantly worse than v3 on in-domain, safety or regressions, the three
  safety invariants are 0, and the 50-task suite does not drop. If it fails, the result is reported as it is and you
  decide between shipping, a data fix, or keeping v3.
- **5.7** Your decision on which model is the headline.

## Phase 6: Write-up
`README.md` (numbers, 26 tools and "works with other MCP servers" only for what was measured), `RESULTS.md`,
`data/card.md` (v4 row, on-policy method, counts), `docs/decisions.md`, `docs/patch_notes.md`,
`docs/architecture.md`, `docs/references.md` complete, CI green. Private files: resume drafts and
`docs/interview_prep.md`. The memory note is updated. Hugging Face upload still waits for your yes.

---

## Things that can go wrong (kept in view during implementation)

**Evaluation validity**
1. **Leakage between rollout tasks and the benchmark.** Same generator, so seeds, names and phrasings must be
   disjoint, held-out families must never enter rollouts, and the test file is hashed before any rollout (A3, A8).
2. **Tuning the benchmark against v3.** Selecting tasks because v3 fails them inflates v4's gain; difficulty changes
   are made per family only (A6).
3. **The benchmark is again written by an AI.** Mitigated by ground truth computed from fixtures, oracle and null
   checks, held-out families and your review, and it is still disclosed.
4. **Unfair old-model comparisons.** v2 and v3 never saw tool 26 or prompt changes; they are scored with the 25-tool
   list and semantic-search tasks are reported separately (0.4, B5).
5. **Reliability at temperature 0 is meaningless**, and sampling is not how Alfred ships; both facts are stated next
   to the metric (G1).
6. **Injection overlap.** Training on the same attack families that are tested would make the security number
   empty; hence the frozen split (C4). Attacks are still fixed templates, not adaptive.
7. **Many new comparisons** raise the chance of a lucky p-value; the tables say so and the headline claims rest on
   the pre-declared ones (hard suite, renamed tools, attack success).
8. **Grammar decoding can hide errors:** a forced-valid call can still be the wrong call, and constraints can cost
   speed or quality, so it is measured before being turned on (D2, D5).

**Data**
9. **Teacher approval is not correctness.** Only executed, checker-passing trajectories are kept (2.5); the
   scorer's keyword classifier is still shared between filtering and scoring, as already disclosed.
10. **Simulated user confirms too much.** If rollouts approve every confirmation, the data teaches unrequested
    changes (issues 001 and 010 again); confirmations follow the request only (A2).
11. **Paths, names and dates leaking into data.** Sandbox paths contain this machine's folders; they are rewritten
    and checked (2.6), and the date is pinned and randomised (0.2).
12. **Thousands of test deletes in your real Recycle Bin** without the sandbox trash switch (0.3).
13. **Token limit.** Real tool outputs and a 26th schema push examples toward 4,096 tokens; drops are counted, not
    silent (3.1).
14. **Masking breaks internal references** (descriptions and the system prompt name other tools); covered by the
    round-trip test (C2). Held-out tools must stay out of training (C3).
15. **v3's Claude-written examples remain** in v4's data; the card keeps saying so.

**Resources**
16. **Laptop CPU time.** Rollouts and K-trial runs take many hours; they are queued, resumable and logged in STATUS,
    and only code work happens while they run.
17. **Kaggle limits.** A session ends at 12 h and the weekly GPU quota is about 30 h; two full runs plus probes and
    the When2Call / BFCL kernels may not fit in one week (3.2, 3.4).
18. **Free-tier teacher quotas** stop mid-run; calls are cached and resumed, never moved to a paid provider.
19. **Ollama must be running** for the embedder (dedup guard, semantic search); the tests skip without it and CI
    has neither Ollama nor llama-server, so CI covers unit tests and the `RESULTS.md` check only.
20. **Contracts 1.3 ripples:** "25 tools" appears in the README, architecture diagram, tests and resumes; changed
    only when v4 ships.

**Process**
21. **Parallel chats editing the same files.** Tracks own disjoint files, except that 4F (step F1) and 4D (step D3)
    both touch `src/alfred/agent/loop.py`; whichever merges second rebases. STATUS has one section per track, and a
    track is claimed with its own commit before work starts.
22. **A worktree has no models, keys or generated data** (`.env`, `data/out/`, `runs/` are gitignored), so a chat
    working in one can write code and run unit tests but cannot run evals, rollouts or the teacher; those are
    machine jobs in the main checkout.
23. **Code changing under a running job.** A rollout or eval that runs for hours must finish on the commit it
    started from; no merges or branch switches in the main checkout until the "Machine" line is clear.
24. **Semantic-search tasks need Ollama running** during evals and rollouts; each report records whether the
    embedder was available, so a silent keyword-only fallback cannot pass as the real result.
25. **Claims ahead of results.** README and resumes change in Phase 6 only, from committed reports.
26. **Scope against your preparation time.** If time runs short, the cut order is: run B, Track F measurement (ii),
    alternative-phrasing reliability, the security fix in E6.

## End-to-end verification when everything is done
`uv run pytest` green locally and in CI · `uv run python -m eval.results` twice gives identical `RESULTS.md` ·
oracle and null checks pass for the hard, unseen and security suites · `uv run python -m data.dedup --check` reports
0 hits · every STATUS row is done with a commit and artifact · every entry in `docs/references.md` names the file
that uses it · `uv run alfred` answers a semantic-search request and a request that needs a held-out tool from the
plug-in server.

## Amendments

### 2026-11-15, after the first retrieval results of track 1B (approved by the owner)
On 300 SciFact abstracts, embedding-only ranking beat the planned fusion (MRR 0.938 against 0.896; keyword 0.797)
and indexing ran at about 2.4 chunks per second on a shared CPU.

1. **B3 ranking.** `search_by_meaning` ranks by embedding cosine. Keyword (BM25) hits are used for chunks that have
   no embedding yet (interleaved with the embedding hits) and for everything when Ollama is down. Fusion of both
   rankers over all chunks stays in the evaluation table as a compared method, not as the shipped one.
2. **B4 tuning and reporting halves.** The 150 claims used so far become the **dev** set: the ranking choice, the
   match cut-off and the prompt check are decided on it. A second subset (the unused test claims, their abstracts,
   random distractors) is the **test** set, run once after those choices are fixed; its numbers are the ones in
   `RESULTS.md`. Dev numbers stay in the report file, labelled.
3. **B4 "nothing found" cut-off (new).** `MIN_COS` is set on dev from claims whose abstracts are not in the corpus
   (taken from SciFact's train split, so no test claim is touched). Rule fixed before looking at test: the cut-off
   is the 5th percentile of the cosine of the first relevant chunk on dev, so about 95% of real matches survive.
   Test reports how many unanswerable claims then return nothing.
4. **B2 indexing outside the search call (new).** An embedding cache keyed by a hash of model and text
   (`ALFRED_EMBED_CACHE=<file>`, set by evals and rollouts, which rebuild the same fixtures many times), and
   indexing in a background thread when the tool server starts (config `index_on_start`, default on). Indexing
   speed is re-measured and the machine load at the time recorded.
5. **A2, 2.2, 5.3: tool-26 tasks.** Fixtures for semantic-search tasks are a handful of short files, so indexing
   finishes inside one call. Every report and rollout records whether the embedder was up; a tool-26 task run with
   the embedder down is **invalid** (re-run), not a pass or fail, because keyword-only recall@1 on low-overlap
   queries is about 51% against 84%.
6. **Corrected numbers.** Track 1B machine time is 1–2 h, not 30 min. Step 3.1: v3's longest example was 3,978
   tokens and tool 26 adds about 85 to every Alfred example, leaving about 33 tokens under the 4,096 limit before
   real tool outputs are added; expect drops and count them.
