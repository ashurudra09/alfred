"""Spike 1c: can an open-weight teacher on a free tier return valid JSON training examples?

Asks each candidate for 10 examples, parses them and checks tool names + required args against the dummy schemas.
Usage: uv run python spikes/teacher.py
"""

import json
import os
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from common import TOOLS

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

CANDIDATES = [  # (label, base url, key env, model)
    ("groq/gpt-oss-120b", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    ("groq/qwen3.8-27b", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "qwen/qwen3.8-27b"),
    ("cerebras/gpt-oss-120b", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", "gpt-oss-120b"),
]
SCHEMAS = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}
PROMPT = f"""You write training data for a Windows laptop assistant. Tools (JSON schema):
{json.dumps([t['function'] for t in TOOLS if t['function']['name'] in ('search_files', 'disk_usage', 'port_in_use', 'calculate', 'remember')])}

Write 10 varied user requests (casual, terse, typos, some Hinglish) with the single correct tool call each.
Return only JSON: {{"examples": [{{"user": "...", "tool": "<name>", "arguments": {{...}}}}]}}"""


def ask(base, key, model):
    body = {"model": model, "messages": [{"role": "user", "content": PROMPT}], "temperature": 0.8,
            "response_format": {"type": "json_object"}}
    req = urllib.request.Request(base + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                                  "User-Agent": "alfred-spike"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def valid(ex):
    schema = SCHEMAS.get(ex.get("tool"))
    args = ex.get("arguments")
    return bool(schema and isinstance(args, dict) and ex.get("user")
                and all(k in args for k in schema["required"]) and set(args) <= set(schema["properties"]))


for label, base, env, model in CANDIDATES:
    key = os.getenv(env, "").strip()
    if not key:
        print(f"[skip] {label}: {env} empty")
        continue
    t0 = time.perf_counter()
    try:
        examples = json.loads(ask(base, key, model))["examples"]
    except Exception as e:
        print(f"[FAIL] {label}: {type(e).__name__}: {str(e)[:200]}")
        continue
    good = sum(map(valid, examples))
    print(f"[{'OK' if good >= 9 else 'XX'}] {label}: {good}/{len(examples)} valid in {time.perf_counter() - t0:.1f}s")
    for ex in examples[:3]:
        print(f"       {ex.get('user')!r} -> {ex.get('tool')}({json.dumps(ex.get('arguments'))})")
