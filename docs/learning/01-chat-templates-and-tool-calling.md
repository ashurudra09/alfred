# Chat templates and tool calling

## What it is
A chat model only ever sees one long string of tokens. The **chat template** (a Jinja program shipped with the
model) turns a list of messages plus tool definitions into that string, with special tokens marking who speaks.
For Qwen3.5 a turn looks like `<|im_start|>assistant\n ... <|im_end|>`.

**Tool calling** is the same mechanism: the template writes the tool schemas into the system message ("You have
access to the following functions: <tools>…</tools>") and tells the model to answer with a fixed format. Qwen3.5
uses XML:

```
<tool_call>
<function=port_in_use>
<parameter=port>
3000
</parameter>
</function>
</tool_call>
```

The server (llama-server) parses that text back into a structured `tool_calls` field (OpenAI format). The agent
runs the tool and sends the result back as a `tool` message, which the template renders inside `<tool_response>`.
The model never "executes" anything; it only writes text that follows the format.

## Why it matters here
- **Training and inference must render identically.** If the model is trained on one string format and served with
  another, it sees prompts it never trained on. We render training data with the real Qwen3.5 tokenizer
  (`apply_chat_template`) and checked that llama-server's prompt for the same conversation is **byte-identical**
  (9,843 characters, via its `/apply-template` endpoint).
- **The tool prompt is long and fixed:** 25 schemas + rules ≈ 2.5k tokens on every request. Its order matters for
  caching: Qwen's template puts the tools before our system text, and our system prompt carries only the date (not
  the time), so the prefix is identical all day and llama-server serves it from cache (1,886–2,515 cached tokens,
  ~1–2 s to first token instead of ~20 s).
- **Thinking mode:** Qwen3.5 can "think" before answering. We ship non-thinking mode (`enable_thinking=False`); the
  template then starts each reply with an empty `<think>\n\n</think>\n\n` block.

## What happened in Alfred: the v1 "ask" bug
Qwen's template **removes that empty think block from assistant turns before the last user message**. Our
clarify-then-call examples have two user turns ("move the file" → "Which file?" → "resume.pdf" → call), so the
clarifying question was always an *earlier* turn and was rendered *without* the prefix. At inference every reply
starts after the prefix, and in Alfred's context the model had never seen a question there. Result: SFT v1 asked a
clarifying question 7–33% of the time (base: 60%) and instead invented arguments (it recycled a made-up file for
"move the file"). Fix (v2): also train each clarify example cut right after the question, so the question is the
final turn. Ask recall went to 93–100%.

Lesson: look at the **rendered training strings**, not just the message lists.

## Check your understanding
- *How does a model "call a function"?* It generates text in a format the template taught it; a parser turns it
  into a structured call; the runtime executes it and feeds the result back as a message.
- *Why fine-tune instead of prompting?* A 2B model with 25 tools in the prompt picks the wrong tool or invents
  arguments (base: 79.1%). Fine-tuning teaches this fixed tool set and our rules (confirm, ask, refuse).
- *What breaks if training and serving templates differ?* The model sees out-of-distribution prompts; accuracy drops
  in ways that look like a bad model. We diff the two renders before blaming the data or hyperparameters.
- *Why does prompt caching matter on CPU?* Prefill of ~2.5k tokens costs ~20 s on this laptop; generation is ~9
  tokens/s. Reusing the cached prefix is the difference between unusable and ~1 s.

## Where in the code
- `src/alfred/contracts/prompt.py`: the system prompt (date only, for caching).
- `src/alfred/contracts/export.py`: tool schemas → OpenAI `tools=` format (`openai_tools`).
- `src/alfred/agent/backends.py`: `openai_messages` (pairs calls and results, wraps tool output as untrusted),
  the XML fallback parser `parse_text_calls`, `serve` (llama-server).
- `data/mix.py`: `render` (training strings) and `ask_endings` (the v2 fix).
