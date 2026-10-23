# Synthetic data and contamination

## What it is
**Synthetic data**: a large "teacher" model writes training examples for a small "student". It's how you get
thousands of examples for *your* 25 tools, which no public dataset has.

**Contamination**: test items (or near-copies) leaking into training data. The model then "remembers" answers and
the score overstates real ability. With a teacher writing the data, a second risk is that the teacher and the test
writer share phrasing habits.

## How Alfred builds it
1. **512 + 72 batches** (`data/gen/prompts.py`): scenario × focus tools: single calls, clarify-then-call,
   declined confirmations, multi-step chains (`recall` → `zip_folder`, search → read), parallel calls, look-alike
   tools, direct answers, "can't do that", refusals, prompt injection inside tool results. Each batch gets a random
   username, folders and date, and Alfred's real system prompt.
2. **Open-weight teachers only** (gpt-oss-120b, Qwen3.8-27B, both Apache 2.0): closed-model terms usually forbid
   training on their outputs.
3. **Pilot gate** (~100 examples): ≥ 90% auto-valid and ≥ 90% correct by hand. First pilot failed (42/50: the
   assistant asked a question and then called a tool without waiting); fixed the prompt and the validator; re-run
   93.9% / 48/50.
4. **Validator** (`data/validate.py`): tool exists, arguments pass the schema, tool results match their calls, a
   question waits for the answer, declined changes don't claim success, no permanent-delete wording, no sensitive
   paths outside refusals, **and every text reply is classified by the eval scorer as its category**, so training
   never pulls the model toward replies the scorer would grade as a different decision. 96.7% of 6,363 passed.
5. **Public data** (15% each): When2Call (ask / can't, filtered the same way) and xLAM (general calling, other APIs).
6. **Dedup** (`data/dedup.py`): drop a training example if any user message has cosine > 0.9 (embeddinggemma) to a
   test message or shares an 8-word sequence. 171 dropped, several word-for-word ("What's running on port 3000?").
7. **Final**: 8,963 train / 471 val, median 2.7k tokens (most of it the fixed tool prompt).

## Contamination guards
- Test items were drafted by Claude, training data by gpt-oss / Qwen: **different sources**.
- Embedding + n-gram dedup against every test message; `python -m data.dedup --check` must print 0.
- Honest caveat: the in-domain set was drafted *and* reviewed by Claude models (owner-approved), so it is not
  independent of Claude.

## Practical lessons from this run
- Free tiers have hidden limits: Groq counted `max_tokens` against an 8k tokens/min budget, gpt-oss had 200k
  tokens/day, Groq's qwen 1k output tokens/min, Cerebras stopped at its $4.29 credit (402, no billing). Prompts were
  trimmed (full schemas only for the batch's tools), a second teacher was added, scarce scenarios were scheduled
  first, and the cache is keyed by batch id so a prompt tweak doesn't throw work away.
- Teachers invent exact file names for vague requests ("my report" → `report_final.docx`); we added a prompt rule
  and the eval checks clarifying behaviour.

## Check your understanding
- *How do you know synthetic data is good?* Pilot gate with a manual check, automatic validation, and the
  downstream eval on a test set the teacher never wrote.
- *How do you avoid test leakage?* Different author for test vs train, embedding + n-gram dedup, a `--check` that
  must be 0, and a fixed eval context.
- *Why mix in public datasets?* To keep general tool-calling and "when not to call" behaviour, and reduce
  overfitting to our 25 schemas (checked later with BFCL).
- *What would you do with more budget?* More examples for the 13 under-200 tools, a second validation by a
  different model, and human review of a larger sample.

## Where in the code
`data/gen/` (prompts, teacher, result formats), `data/validate.py`, `data/sources.py`, `data/dedup.py`,
`data/mix.py`, `data/card.md`, `data/stats.md`.
