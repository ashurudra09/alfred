# LoRA and QLoRA

## What it is
**Full fine-tuning** updates every weight (2.2B here) and needs memory for the weights, their gradients and the
optimizer state, several times the model size. **LoRA** (Low-Rank Adaptation) freezes the model and learns a small
correction for selected weight matrices:

```
W' = W + (alpha / r) · B · A        A: r × d_in,  B: d_out × r,  r ≪ d
```

`B` starts at zero, so training starts exactly from the base model. Only `A` and `B` are trained. The correction
has rank ≤ r, on the hypothesis that adapting a model to a narrow task needs only a low-rank change.

**QLoRA** is LoRA on top of a base model stored in 4-bit, which cuts memory roughly 4× more; the adapters and the
compute stay in 16-bit.

## Alfred's settings and why
| Setting | Value | Why |
|---|---|---|
| Rank `r` / `alpha` | 16 / 32 | the common starting point; alpha/r = 2 scales the update |
| Targets | q, k, v, o (attention) + gate, up, down (MLP) | all major linear layers; MLP adapters matter for new behaviour |
| Trainable params | 10.9M of 2.2B (0.49%) | Qwen3.5 is hybrid: most layers use linear attention (Gated DeltaNet) with different projection names, so attention adapters land only in the full-attention layers (inferred from Unsloth's log + the count) |
| Precision | 16-bit LoRA, **not** QLoRA | Unsloth advises against 4-bit for Qwen3.5 (larger quantization error); a 2B model fits a 16 GB T4 without it |
| Compute | float32 on a T4 | the T4 has no bf16 and Unsloth refuses fp16 for Qwen3.5, so it falls back to fp32 (slow: 23–33 s/step) |
| Loss | cross-entropy on assistant tokens only | `train_on_responses_only`: system, tools, user and tool-result tokens are inputs, not targets |
| Schedule | 620 steps, batch 8, lr 2e-4 cosine, ~0.6 epoch | sized from a 20-step probe to fit one Kaggle session (3.9–4.0 h) |

The adapter file is small (tens of MB); for serving we merge it into the base and export GGUF (Q4/Q8).

## What the loss does and doesn't capture
Token-level cross-entropy rewards imitating the reference answer. It is a proxy for correctness: a wrong tool name
(a few tokens) costs about as much as rephrasing the summary, and an equivalent but different argument (a short vs a
full path) is penalised. Correctness comes in through the **data** (every example validated against the scorer) and
is optimised directly later by DPO (preference pairs) and GRPO (the scorer as reward).

## Check your understanding
- *Why LoRA instead of full fine-tuning?* ~0.5% of the parameters, fits a free 16 GB GPU, no catastrophic drift of
  the base, small artifact, easy to compare runs.
- *What do r and alpha control?* r = capacity of the update; alpha/r = its scale. Higher r learns more but can
  overfit and costs memory.
- *Which layers do you adapt?* Attention and MLP projections; MLP-only or attention-only is a cheaper ablation.
- *QLoRA trade-off?* Much less memory, some accuracy loss from 4-bit base weights; Unsloth's guidance for Qwen3.5 was
  to avoid it, and we didn't need it for 2B.
- *How did you choose steps?* A probe measured 33.5 s/step; 620 steps fit one session with a full cosine decay.
  Validation loss fell at every eval (v1: 0.274 → 0.227) so there was no sign of overfitting.

## Where in the code
- `train/configs/sft_2b.yaml`: every hyperparameter (with the probe timing).
- `train/sft_kernel/sft.py`: Unsloth load, `get_peft_model`, `train_on_responses_only`, time-limit callback, GGUF export.
- `train/package_data.py`: builds the Kaggle dataset.
