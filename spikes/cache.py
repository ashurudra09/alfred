"""Spike 1f: why is warm latency ~21 s? Checks prefix-cache reuse, thread count and compact schemas on Ollama.

Usage: uv run python spikes/cache.py
"""

import copy

from common import TOOLS, chat


def show(label, st):
    print(f"  {label:34} ttft={st['ttft']:5.2f}s prompt_tok={st['prompt_tokens']:5} prompt={st['prompt_s']:5.2f}s "
          f"({st['prompt_tokens'] / max(st['prompt_s'], 1e-9):5.0f} tok/s) gen={st['tok_per_s']:4.1f} tok/s")


def compact(tools, keep_desc=True):
    """Short descriptions; drop per-param descriptions (there are none here) and optional params' noise."""
    out = copy.deepcopy(tools)
    for t in out:
        f = t["function"]
        f["description"] = f["description"].split(".")[0][:40] if keep_desc else ""
    return out


print("1) prefix cache: identical request twice, then a different user message")
chat("hi")
for label, user in [("same as previous (repeat A)", "What's running on port 3000?"),
                    ("identical repeat A", "What's running on port 3000?"),
                    ("different user msg B", "Why is my C drive full?")]:
    show(label, chat(user)[2])

print("2) threads (different user message each time)")
for n in (4, 6, 8, 10, 12):
    chat("warm up", num_thread=n)
    show(f"num_thread={n}", chat(f"what's on port {3000 + n}?", num_thread=n)[2])

print("3) schema size")
for label, tools in [("25 full", TOOLS), ("25 short desc", compact(TOOLS)), ("25 no desc", compact(TOOLS, False)),
                     ("top-5 full", TOOLS[:5]), ("no tools", [])]:
    chat("warm up", tools)
    calls, content, st = chat("What's running on port 3000?", tools)
    show(label, st)
