"""Phase 5 SFT on Kaggle (GPU T4). Pushed with: kaggle kernels push -p train/sft_kernel
Inputs (Kaggle dataset alfred-sft-data): train.jsonl / val.jsonl ({"id", "text"}, rendered with the Qwen3.5 chat
template), sft_2b.yaml, prompt_kit.json (system prompt + tools for the smoke test).
Outputs in /kaggle/working: lora adapter, GGUFs, log_history.json, loss.png, smoke.json.
Set PROBE = True to time a few steps without exporting.
"""

import glob
import json
import os
import subprocess
import sys
import time

PROBE = False
IN = os.path.dirname(glob.glob("/kaggle/input/**/sft_2b.yaml", recursive=True)[0])  # mount path varies
OUT = "/kaggle/working"
T0 = time.time()

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "unsloth"], check=True)

import yaml  # noqa: E402
from unsloth import FastLanguageModel  # noqa: E402  (import before trl/transformers)
from unsloth.chat_templates import train_on_responses_only  # noqa: E402
import torch  # noqa: E402
from datasets import load_dataset  # noqa: E402
from transformers import TrainerCallback  # noqa: E402
from trl import SFTConfig, SFTTrainer  # noqa: E402

cfg = yaml.safe_load(open(f"{IN}/sft_2b.yaml"))
tc = cfg["train"]
print("torch", torch.__version__, "gpu", torch.cuda.get_device_name(0), "setup", round(time.time() - T0), "s",
      flush=True)

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=cfg["model"], max_seq_length=cfg["max_seq_length"], load_in_4bit=cfg["load_in_4bit"], dtype=None)
tok = getattr(tokenizer, "tokenizer", tokenizer)  # Qwen3.5 may load as a multimodal processor
model = FastLanguageModel.get_peft_model(
    model, r=cfg["lora"]["r"], lora_alpha=cfg["lora"]["alpha"], lora_dropout=cfg["lora"]["dropout"],
    target_modules=cfg["lora"]["target_modules"], bias="none", use_gradient_checkpointing="unsloth",
    random_state=tc["seed"])

data = load_dataset("json", data_files={"train": f"{IN}/train.jsonl", "val": f"{IN}/val.jsonl"})
val_small = data["val"].shuffle(seed=tc["seed"]).select(range(min(tc["eval_subset"], len(data["val"]))))


class TimeLimit(TrainerCallback):
    """Stop after max_hours of training, after an eval + save, so the best checkpoint is still loaded."""

    def __init__(self, hours):
        self.limit, self.start = hours * 3600, None

    def on_train_begin(self, args, state, control, **kw):
        self.start = time.time()

    def on_step_end(self, args, state, control, **kw):
        if time.time() - self.start > self.limit:
            print(f"time limit reached at step {state.global_step}", flush=True)
            control.should_evaluate = control.should_save = control.should_training_stop = True


args = SFTConfig(
    output_dir=f"{OUT}/ckpt", dataset_text_field="text", max_length=cfg["max_seq_length"], packing=False,
    num_train_epochs=tc["epochs"], max_steps=cfg["probe_steps"] if PROBE else tc.get("max_steps", -1),
    per_device_train_batch_size=tc["batch_size"], gradient_accumulation_steps=tc["grad_accum"],
    learning_rate=tc["lr"], lr_scheduler_type=tc["scheduler"], warmup_ratio=tc["warmup_ratio"],
    weight_decay=tc["weight_decay"], optim="adamw_8bit", fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(), logging_steps=10, eval_strategy="no" if PROBE else "steps",
    eval_steps=tc["eval_every"], save_strategy="no" if PROBE else "steps", save_steps=tc["eval_every"],
    save_total_limit=2, load_best_model_at_end=not PROBE, metric_for_best_model="eval_loss",
    greater_is_better=False, seed=tc["seed"], report_to="none", dataset_num_proc=2)
trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=data["train"], eval_dataset=val_small, args=args,
                     callbacks=[TimeLimit(tc["max_hours"])])
trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n",
                                  response_part="<|im_start|>assistant\n")

t = time.time()
stats = trainer.train()
secs = time.time() - t
steps = trainer.state.global_step
print(f"trained {steps} steps in {secs / 60:.1f} min ({secs / max(steps, 1):.1f} s/step); "
      f"{len(data['train'])} examples = {len(data['train']) / (tc['batch_size'] * tc['grad_accum']):.0f} steps/epoch",
      flush=True)
json.dump(trainer.state.log_history, open(f"{OUT}/log_history.json", "w"), indent=1)
if PROBE:
    sys.exit(0)

best_val = trainer.evaluate()  # the eval subset, on the best checkpoint (full val costs ~35 min on a T4)
print("best checkpoint", trainer.state.best_model_checkpoint, "val", best_val, flush=True)
json.dump({"best_checkpoint": trainer.state.best_model_checkpoint, "val_subset": best_val, "train_secs": secs,
           "steps": steps}, open(f"{OUT}/train_summary.json", "w"), indent=1)

try:  # loss curves
    import matplotlib.pyplot as plt
    h = trainer.state.log_history
    tr = [(x["step"], x["loss"]) for x in h if "loss" in x]
    ev = [(x["step"], x["eval_loss"]) for x in h if "eval_loss" in x]
    plt.plot(*zip(*tr), label="train")
    plt.plot(*zip(*ev), label="val", marker="o")
    plt.xlabel("step"), plt.ylabel("loss"), plt.legend(), plt.title("Alfred SFT, Qwen3.5-2B LoRA")
    plt.savefig(f"{OUT}/loss.png", dpi=120)
except Exception as e:
    print("plot failed:", e)

model.save_pretrained(f"{OUT}/alfred-2b-lora")
tok.save_pretrained(f"{OUT}/alfred-2b-lora")

# smoke test: 5 hand prompts through the same chat template
kit = json.load(open(f"{IN}/prompt_kit.json"))
FastLanguageModel.for_inference(model)
smoke = []
for q in ["What's running on port 3000?", "delete old_resume.pdf from my desktop", "move the file",
          "book me a flight to Goa", "show me the saved wifi passwords"]:
    msgs = [{"role": "system", "content": kit["system"]}, {"role": "user", "content": q}]
    ids = tok.apply_chat_template(msgs, tools=kit["tools"], add_generation_prompt=True, enable_thinking=False,
                                  return_tensors="pt").to("cuda")
    out = model.generate(input_ids=ids, max_new_tokens=120, do_sample=False)
    smoke.append({"q": q, "a": tok.decode(out[0][ids.shape[1]:], skip_special_tokens=False)})
    print(smoke[-1], flush=True)
json.dump(smoke, open(f"{OUT}/smoke.json", "w"), indent=1)

for q in cfg["export"]:
    model.save_pretrained_gguf(f"{OUT}/gguf_{q}", tok, quantization_method=q)
subprocess.run("ls -la /kaggle/working /kaggle/working/gguf_*", shell=True)
for d in ("ckpt",):  # keep the output small: checkpoints aren't needed once the best adapter is saved
    subprocess.run(["rm", "-rf", f"{OUT}/{d}"])
print("total", round((time.time() - T0) / 60), "min", flush=True)
