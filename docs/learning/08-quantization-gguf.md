# Quantization and GGUF

## What it is
**Quantization** stores weights with fewer bits: 16-bit floats → 8-bit or ~4-bit integers plus scale factors.
The model gets 2–4× smaller, and because CPU inference is limited by **memory bandwidth** (every generated token reads
all the weights), smaller also means faster. The cost is rounding error, which can lower accuracy.

**GGUF** is llama.cpp's single-file model format: weights, tokenizer, chat template and metadata together.
Common types:
- **F16:** unquantized 16-bit (the reference).
- **Q8_0:** 8-bit integers in blocks of 32 weights, one scale per block; nearly lossless.
- **Q4_K_M:** "k-quants": ~4-bit weights in super-blocks with per-block scales and minimums; the "M" mix keeps some
  sensitive tensors at higher precision. About 4.5–5 bits per weight on average.

## Alfred's numbers (SFT v2, in-domain test set)
| Format | Size | In-domain accuracy | Median time to first token |
|---|---|---|---|
| F16 | 3.9 GB | 95.7% | 2.1 s |
| Q8_0 | 2.1 GB | 95.7% | 1.3 s |
| **Q4_K_M (shipped)** | **1.3 GB** | **95.3%** | **1.0 s** |

Q8_0 lost nothing; Q4_K_M lost 0.4 points (one item out of 278) and is the fastest, so it ships.

## Serving: llama.cpp and the prefix cache
Every request repeats a ~2.5k-token prefix (system prompt + 25 tool schemas). Phase 1 found Ollama reprocessed it on
every request (21 s to first token with 25 schemas); `llama-server` keeps the processed prefix in its KV cache and
reuses it (~2 s, then ~1 s with Q4), and can save it to disk so a restart is fast too. Prefix caching mattered more
than any quantization choice.

## Check your understanding
- *Why does a smaller model generate faster on a CPU?* Each token reads every weight from RAM; fewer bytes per weight
  means less memory traffic per token.
- *Why is Q8 almost lossless and Q4 not quite?* 256 levels per block vs ~16; the error at 4 bits is large enough to
  flip a few borderline decisions.
- *What else could you quantize?* The KV cache, and activations (needs hardware support); not done here.
- *How do you check a quantized model?* Run the same evaluation at each precision; don't assume.

## Where in the code
- `train/sft_kernel/sft.py`: Unsloth's `save_pretrained_gguf` (Q4_K_M, Q8_0). `eval/when2call/bench.py` exported F16.
- `src/alfred/agent/backends.py`: `serve()` starts `llama-server` with the cache settings.
- `eval/reports/alfred-2b-v2-{f16,q8,q4}_indomain.md`: the three reports. `spikes/llamaserver.py`, `spikes/cache.py`:
  the Phase 1 latency experiments.
