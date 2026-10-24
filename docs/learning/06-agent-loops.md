# Agent loops

## What it is
An **agent loop** turns one user message into a finished answer: call the model; if it asks for tools, run them,
append the results and call the model again; stop when it answers in text. Everything that makes an agent safe and
usable lives in this loop, not in the model: argument validation, limits, confirmations, how tool output is
presented, what history is sent, and timing.

## Alfred's loop
`agent/loop.run_turn` is a **generator of events**: `token`, `tool_call_proposed`, `confirm_required`,
`tool_result`, `retry`, `error`, `timing`, `done`. The CLI and the web UI just render events; neither contains agent
logic.

| Rule | How |
|---|---|
| Validate before running | arguments checked against the tool's JSON Schema; unknown tool / bad JSON / invalid args go back to the model as a tool error, **one retry**, then the turn ends with "could you rephrase?" |
| Bounded | at most **3 tool calls** per user turn |
| Confirm writes | for a tool flagged `needs_confirmation`, the loop computes the exact plan (`files.preview`, e.g. organize's full move list) and **yields** `confirm_required`; the caller answers with `gen.send(True/False)` |
| Safe default | a caller that just iterates sends `None`, which counts as **no** |
| Declines are explicit | the model gets "The user declined this change. Nothing was changed." (the exact training text) |
| Untrusted output | tool results are wrapped `<tool_output untrusted="true">` before the model sees them |
| Bounded history | continuing a chat sends only the latest whole turns within ~14k characters (~4k tokens) |
| Measured | total time, time to first token, per-tool time, tokens/s per turn, logged to `logs/<date>.jsonl` |

**Why a generator?** Confirmation needs the loop to *pause* mid-turn and wait for a human. In the CLI that's a
blocking `input()`. In the web UI the turn spans several HTTP events, so the UI keeps the paused generator and resumes
it when Confirm or Cancel is clicked. Same loop, no threads or callbacks.

## What happened here
- **End-to-end (50 tasks + 20 injection files, real tools and model):** 47/50, injection 20/20, and 0 unconfirmed
  writes / 0 overwrites / 0 permanent deletes. Median turn 9 s on the CPU, about two model calls per turn.
- **Confirmation caught real mistakes:** in the UI the model proposed zipping all of `AlfredTest` instead of
  `AlfredTest\Resume`. The preview showed the wrong path and Cancel left everything unchanged.
- **Timing bug:** the turn's total included the time the user spent deciding. The loop now subtracts the wait, so
  the CLI, UI and logs report Alfred's latency only.

## Check your understanding
- *Why cap tool calls?* Loops (call → error → call …) waste time and can compound damage; three covers every real
  task in the test set (chains like `recall` → `zip_folder`).
- *Why one retry and not more?* Most invalid calls are fixed once the model sees the schema error; more retries rarely
  help and slow the turn.
- *Where would you add a new safety rule?* In the loop or the tool server, never only in the prompt.
- *How do the CLI and UI share behaviour?* They consume the same event stream; tests drive the loop with a scripted
  fake model.

## Where in the code
- `src/alfred/agent/loop.py`: `run_turn`, `problems` (validation), `drive` (run to completion with a confirm callback).
- `src/alfred/agent/chats.py`: chat store and context budget. `timing.py`: per-turn timing and the JSONL log.
- `src/alfred/agent/cli.py` and `src/alfred/ui/app.py`: the two consumers.
- `tests/agent/test_loop.py`, `eval/e2e/`: unit tests (fake backend) and the end-to-end suite.
