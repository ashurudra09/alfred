"""Spike 1g: the same GGUF under llama.cpp's llama-server. Reports TTFT and how many prompt tokens came from the cache.

Start the server first, e.g.:
  llama-server -m <ollama blob> -c 8192 -t 4 --port 8080 [--checkpoint-min-step 256 --cache-reuse 256]
Usage: uv run python spikes/llamaserver.py [label]
"""

import json
import statistics
import sys
import time
import urllib.request

from common import SYSTEM, TOOLS

URL = "http://127.0.0.1:8080/v1/chat/completions"
REQUESTS = ["warm up", "What's running on port 3000?", "Why is my C drive full?", "Zip my resume folder in Documents",
            "remember that my resume is in D:\\docs\\resume", "what's my battery at?"]


def chat(user):
    body = {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], "tools": TOOLS,
            "stream": True, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False},
            "timings_per_token": False}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0, ttft, timings, calls = time.perf_counter(), None, {}, ""
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            delta = (chunk.get("choices") or [{}])[0].get("delta", {})
            if ttft is None and (delta.get("content") or delta.get("tool_calls")):
                ttft = time.perf_counter() - t0
            for tc in delta.get("tool_calls") or []:
                calls += (tc.get("function", {}).get("name") or "") + (tc.get("function", {}).get("arguments") or "")
            timings = chunk.get("timings", timings)
    return ttft, timings, calls


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "llama-server"
    ttfts = []
    for user in REQUESTS:
        ttft, t, calls = chat(user)
        ttfts.append(ttft)
        print(f"  ttft={ttft:5.2f}s cached={t.get('cache_n')} new_prompt={t.get('prompt_n')} "
              f"prompt={t.get('prompt_ms', 0) / 1000:5.2f}s gen={t.get('predicted_per_second', 0):4.1f} tok/s | {calls[:70]}")
    print(f"{label}: median warm ttft {statistics.median(ttfts[1:]):.2f}s")
