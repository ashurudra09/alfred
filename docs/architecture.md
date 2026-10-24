# Architecture

Alfred has three parts that meet at two interfaces: the **model** (behind an OpenAI-compatible HTTP API served by
llama.cpp) and the **tools** (behind MCP). The agent loop in the middle owns every safety rule.

## Components
```mermaid
flowchart TB
    subgraph FE[Front ends]
        CLI[alfred: terminal app<br/>agent/cli.py]
        UI[alfred-ui: Gradio web UI<br/>ui/app.py]
        CD[Claude Desktop<br/>any MCP client]
    end
    subgraph AG[Agent: agent/]
        LOOP[run_turn: event generator<br/>validate · retry · ≤3 calls · confirm]
        CH[(chats.db<br/>chat history)]
        TM[timing + JSONL log]
    end
    subgraph MD[Model]
        LS[llama-server :8080<br/>prefix cache]
        GG[alfred-2b-v2-q4.gguf<br/>Qwen3.5-2B + LoRA, Q4_K_M]
    end
    subgraph TS[MCP tool server: tools/]
        SRV[server.py<br/>25 tools under frozen contracts]
        GD[guards.py<br/>known folders · secrets · executables · no overwrite]
        JR[(journal.db<br/>undo)]
        MEM[(memory.db<br/>+ Ollama embeddinggemma)]
    end
    OS[(Files, apps, system info,<br/>notes, reminders)]

    CLI --> LOOP
    UI --> LOOP
    LOOP <--> CH
    LOOP --> TM
    LOOP <-->|OpenAI chat API, streamed| LS
    LS --- GG
    LOOP <-->|MCP over stdio| SRV
    CD <-->|MCP over stdio| SRV
    SRV --> GD --> OS
    SRV --> JR
    SRV --> MEM
```

## One turn with a write
```mermaid
sequenceDiagram
    actor U as User
    participant F as CLI / UI
    participant L as Agent loop
    participant M as Model (llama-server)
    participant T as Tool server (MCP)
    U->>F: "move notes.txt to Documents"
    F->>L: run_turn(chat, text)
    L->>M: history + system prompt + 25 tool schemas
    M-->>L: tool call move_file(source, destination)
    L->>L: validate args against the schema
    L->>T: preview (resolve paths, check guards)
    L-->>F: confirm_required("Move C:\…\notes.txt → C:\…\Documents\notes.txt")
    F->>U: Confirm / Cancel
    U->>F: Confirm
    F->>L: send(True)
    L->>T: tools/call move_file
    T->>T: guards → move → journal entry
    T-->>L: "Moved … Undo: /undo"
    L->>M: tool result (wrapped as untrusted)
    M-->>L: "Moved notes.txt to Documents."
    L-->>F: tokens, timing, done
    Note over U,T: /undo (CLI) or the Undo button reads the journal and reverses the move
```
On Cancel the loop sends the model "The user declined this change. Nothing was changed." and nothing runs.

## Training and evaluation pipeline
```mermaid
flowchart LR
    C[contracts v1.0<br/>25 tools · prompt] --> G[data/gen<br/>teacher gpt-oss-120b]
    G --> V[data/validate<br/>same scorer as eval]
    V --> X[data/mix<br/>+ When2Call + xLAM · dedup vs test]
    X --> K[Kaggle T4<br/>LoRA SFT · Unsloth]
    K --> Q[GGUF<br/>F16 · Q8_0 · Q4_K_M]
    Q --> E[eval: in-domain · safety · e2e<br/>BFCL · When2Call]
    E --> R[RESULTS.md]
```

## Where things live
| Path | What |
|---|---|
| `src/alfred/contracts/` | tool contracts, JSON schemas (`tools.json`), system prompt, message schemas |
| `src/alfred/tools/` | MCP server, tool implementations, guards, undo journal, memory |
| `src/alfred/agent/` | agent loop, model backends, MCP client, chats, timing, CLI |
| `src/alfred/ui/` | web UI (consumes the loop's events only) |
| `data/`, `train/` | dataset generation and validation, Kaggle training |
| `eval/` | scorer, test sets, runners, e2e suite, BFCL and When2Call, `results.py` |
| `%LOCALAPPDATA%\Alfred\` | user data: `chats.db`, `journal.db`, `memory.db`, `notes\`, `reminders.json`, `config.json` |
