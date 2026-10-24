# Public benchmarks: BFCL and When2Call

## Why they're here
The in-domain test set measures Alfred's 25 tools, written by the same project that wrote the training data. Public
benchmarks answer two other questions: **did fine-tuning on our tools hurt general function calling?** (BFCL) and
**does the model know when *not* to call a tool?** (When2Call). They also make the result comparable with other work.

## BFCL (Berkeley Function Calling Leaderboard), v4 subset
Each item gives functions and a question; the model's call is parsed and checked against the allowed answers
(**AST matching**: right function, right argument names, values of the right type and in the allowed set).
Categories used: `simple_python` (one function), `multiple` (pick one of several), `parallel` (several calls),
`irrelevance` (no function fits: must not call), `live_relevance` (real user-contributed prompts where a call fits).

| Category | n | Base | SFT v2 |
|---|---|---|---|
| simple_python | 400 | 74.8% | 83.8% |
| multiple | 200 | 84.0% | 87.0% |
| parallel | 200 | 50.5% | 85.5% |
| irrelevance | 240 | 57.5% | 73.8% |
| live_relevance | 16 | 93.8% | 56.2% |
| mean | | 72.1% | 77.2% |

- **Harness work:** the pinned `bfcl-eval` had no Qwen3.5 handler. Ours uses the model's real chat template and types
  each XML parameter by the function's schema, as vLLM's parser does (otherwise `True` fails the boolean check).
- **Reading it:** big gains on parallel (the base model often explained the formula in prose instead of calling) and
  irrelevance; a drop on live_relevance (n = 16): SFT sometimes declines a relevant call, the cost of its caution.
- **Not the vendor's 43.6:** that's the full BFCL v4 (multi-turn, agentic) in thinking mode; this is the single-turn
  part in non-thinking mode.

## When2Call (NVIDIA)
3,652 test questions, each with four candidate answers: a **tool call**, a **direct answer**, a **request for more
information** and **"I can't"**. Scoring is multiple choice by **log-likelihood**: the model reads the prompt, we
compute the probability of each candidate answer, and the most likely one is its choice. No text is generated, so
there's no parsing.
- **acc** = argmax of the summed log-probability; **acc-norm** = argmax after dividing by the answer's length
  (long answers have lower total probability); **macro-F1** averages F1 over the four answer types (punishes always
  picking one type); **tool hallucination** = how often it picks the tool call when no tools were given.
- **Results, base → SFT:** accuracy 41.2% → 65.7%, macro-F1 0.228 → 0.480, hallucination 14.7% → 3.1%.
- **Contamination check:** When2Call's *train* split is in our SFT mix; this is the held-out *test* split.

## Check your understanding
- *Why log-likelihood instead of generating an answer?* No parsing, deterministic, and it measures the model's
  preference directly; the trade-off is it doesn't test the model's own wording.
- *Why report macro-F1 and not just accuracy?* The answer types are imbalanced; a model that always calls a tool can
  get decent accuracy and a poor macro-F1.
- *Why did live_relevance drop while irrelevance rose?* They pull in opposite directions: more caution helps
  "don't call" items and hurts "do call" items. With n = 16, the drop is 6 items.
- *Why run these at all if in-domain is 95%?* To catch overfitting to our tools and our test writer.

## Where in the code
- `eval/bfcl/run.py` (handler), `eval/bfcl/kernel/bfcl_kernel.py` (Kaggle: build llama.cpp with CUDA, serve, run).
- `eval/when2call/bench.py` (Kaggle: log-likelihood scoring with a cached prompt), `eval/results.py` (metrics,
  `RESULTS.md`), `tests/eval/test_results.py`.
