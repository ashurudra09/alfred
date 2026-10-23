"""Phase 9 on Kaggle (2x T4): the When2Call MCQ test for base vs. SFT, and an F16 GGUF of the SFT model.

Pushed with: kaggle kernels push -p eval/when2call   (inputs: dataset alfred-adapters = the v2 LoRA adapter)
Scoring is the official When2Call MCQ rule (lm-eval-harness `multiple_choice`, target_delimiter ""): each answer's
log-likelihood after the prompt; acc = argmax, acc_norm = argmax of loglik / len(answer in characters),
macro-F1 over the 4 answer types, tool hallucination rate (tool call chosen when no tools were given).
The prompt and the tool-call answer are rendered with the Qwen3.5 chat template (non-thinking), like the
official `when2call-qwen2_5` task does for Qwen2.5. Both models get exactly the same prompts.
LIMIT scores only the first N items (a probe run); EXPORT writes the F16 GGUF.
"""

import copy
import glob
import json
import os
import subprocess
import sys
import time

OUT = "/kaggle/working"
LIMIT = None  # None for the full run; a small number for a probe run
EXPORT = False  # the F16 GGUF came from the probe run (version 1); exporting again changes nothing
T0 = time.time()


def worker(which: str):
    import torch
    from huggingface_hub import hf_hub_download
    from unsloth import FastLanguageModel

    adapter = os.path.dirname(glob.glob("/kaggle/input/**/adapter_config.json", recursive=True)[0])
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter if which == "sft" else "unsloth/Qwen3.5-2B", max_seq_length=4096, dtype=torch.float32,
        load_in_4bit=False)
    tok = getattr(tokenizer, "tokenizer", tokenizer)
    tok_template = __import__("transformers").AutoTokenizer.from_pretrained(adapter)  # the training template
    FastLanguageModel.for_inference(model)
    model.eval()

    path = hf_hub_download("nvidia/When2Call", "test/when2call_test_mcq.jsonl", repo_type="dataset")
    items = [json.loads(line) for line in open(path, encoding="utf-8")][:LIMIT]

    def render(item):
        tools = [json.loads(t) for t in item["tools"]]
        msgs = [{"role": "user", "content": item["question"]}]
        kw = dict(tools=tools or None, tokenize=False, enable_thinking=False)
        prompt = tok_template.apply_chat_template(msgs, add_generation_prompt=True, **kw)
        names, choices = list(item["answers"]), []
        for name in names:
            text = item["answers"][name]
            if name == "tool_call":
                call = json.loads(text)
                full = tok_template.apply_chat_template(msgs + [{"role": "assistant", "content": "", "tool_calls": [
                    {"type": "function", "function": {"name": call["name"], "arguments": call["arguments"]}}]}], **kw)
                assert full.startswith(prompt), (prompt[-200:], full[-400:])
                text = full[len(prompt):].removesuffix("\n").removesuffix("<|im_end|>").rstrip("\n")
            choices.append(text)
        return prompt, names, choices

    @torch.no_grad()
    def logliks(prompt, choices, check=False):
        ctx = tok(prompt, add_special_tokens=False).input_ids
        out = model(input_ids=torch.tensor([ctx], device="cuda"), use_cache=True)
        last, cache = out.logits[0, -1:].float(), out.past_key_values
        lls = []
        for c in choices:  # lm-eval: continuation = enc(context + choice)[len(enc(context)):]
            cont = tok(prompt + c, add_special_tokens=False).input_ids[len(ctx):]
            o = model(input_ids=torch.tensor([cont], device="cuda"), past_key_values=copy.deepcopy(cache),
                      use_cache=True)
            logits = torch.cat([last, o.logits[0, :-1].float()]).log_softmax(-1)
            ll = logits[torch.arange(len(cont)), torch.tensor(cont, device="cuda")].sum().item()
            if check:  # the prefix-cache shortcut must equal one full forward pass
                f = model(input_ids=torch.tensor([ctx + cont], device="cuda")).logits[0].float().log_softmax(-1)
                full = f[torch.arange(len(ctx) - 1, len(ctx) + len(cont) - 1), torch.tensor(cont, device="cuda")]
                print(f"check {which}: cached {ll:.3f} vs full {full.sum().item():.3f}", flush=True)
                assert abs(ll - full.sum().item()) < 0.05 * max(1, abs(ll))
            lls.append(ll)
        return lls

    rows, t = [], time.time()
    for i, item in enumerate(items):
        prompt, names, choices = render(item)
        if i == 0:
            print("PROMPT\n" + prompt + "\nCHOICES", json.dumps(choices, indent=1), flush=True)
        lls = logliks(prompt, choices, check=i < 3)
        rows.append({"uuid": item["uuid"], "gold": names.index(item["correct_answer"]), "names": names,
                     "no_tools": len(item["tools"]) == 0, "lls": lls, "lens": [len(c) for c in choices]})
        if i % 200 == 0:
            print(which, i, len(items), f"{time.time() - t:.0f}s", flush=True)
    json.dump(rows, open(f"{OUT}/when2call_{which}.json", "w"))
    if which == "sft" and EXPORT:  # the unquantized SFT model for the quantization comparison
        model.save_pretrained_gguf(f"{OUT}/gguf_f16", tokenizer, quantization_method="f16")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        worker(sys.argv[1])
        sys.exit()
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "unsloth"], check=True)
    procs = [subprocess.Popen([sys.executable, __file__, w], env={**os.environ, "CUDA_VISIBLE_DEVICES": str(g)})
             for g, w in enumerate(("base", "sft"))]
    codes = [p.wait() for p in procs]
    subprocess.run("ls -laR /kaggle/working | head -40", shell=True)
    print("exit codes", codes, "total", round((time.time() - T0) / 60), "min", flush=True)
