"""Spike 1b: CPU latency of qwen3.5:2b with 25 tool schemas, cold (model unloaded) vs. warm (loaded, prefix cached).

Usage: uv run python spikes/latency.py
"""

import statistics

from common import chat, unload

REQUESTS = ["What's running on port 3000?", "Why is my C drive full?", "Zip my resume folder in Documents",
            "remember that my resume is in D:\\docs\\resume", "what's my battery at?"]


def run(label, cold):
    rows = []
    for user in REQUESTS:
        if cold:
            unload()
        _, _, st = chat(user)
        rows.append(st)
        print(f"  {label} ttft={st['ttft']:.2f}s total={st['total']:.2f}s load={st['load_s']:.2f}s "
              f"prompt_tok={st['prompt_tokens']} gen={st['gen_tokens']} {st['tok_per_s']:.1f} tok/s")
    med = lambda k: statistics.median(r[k] for r in rows)
    print(f"{label}: median ttft {med('ttft'):.2f}s, total {med('total'):.2f}s, {med('tok_per_s'):.1f} tok/s, "
          f"prompt {rows[0]['prompt_tokens']} tokens")
    return med("ttft")


cold = run("cold", True)
chat("hi")  # load + cache the shared prefix
warm = run("warm", False)
print(f"\nWarm TTFT {warm:.2f}s -> {'OK' if warm <= 8 else 'over 8 s: compact descriptions become a Phase 2 requirement'}")
