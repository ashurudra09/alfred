"""Call the open-weight teacher (gpt-oss-120b on Groq, Cerebras as a second worker) for every batch in
`prompts.batches()`. Responses are cached by prompt hash in data/out/cache/, so runs resume and reruns are free.

Usage: uv run python -m data.gen.teacher [--pilot] [--limit N]
Writes data/out/synthetic.jsonl (or synthetic_pilot.jsonl): unvalidated Examples, system prompt included.
"""

import argparse
import hashlib
import json
import os
import queue
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI

from alfred.agent.backends import ROOT  # also loads .env
from alfred.contracts.export import openai_tools
from alfred.contracts.schemas import Example, Message
from data.gen.prompts import batches, pilot, prompt, system_prompt

OUT = ROOT / "data" / "out"
CACHE = OUT / "cache"
# (name, url, key env, model, max_tokens, workers, extra_body). Groq's free tier counts max_tokens against its 8k
# tokens/minute, so its requests stay small. Both teachers are open-weight, Apache 2.0 (decisions.md, Phase 4).
GROQ, CEREBRAS = "https://api.groq.com/openai/v1", "https://api.cerebras.ai/v1"
PROVIDERS = [("groq", GROQ, "GROQ_API_KEY", "openai/gpt-oss-120b", 6000, 1, {"reasoning_effort": "low"}),
             ("cerebras", CEREBRAS, "CEREBRAS_API_KEY", "gpt-oss-120b", 12000, 2, {"reasoning_effort": "low"}),
             ("groq-qwen", GROQ, "GROQ_API_KEY", "qwen/qwen3.8-27b", 6000, 1, {"reasoning_effort": "none"}),
             ("cerebras-qwen", CEREBRAS, "CEREBRAS_API_KEY", "qwen-3.8-27b", 12000, 2, {})]
# scarce scenarios first, so a run cut short by rate limits still covers every behaviour
PRIORITY = ["refuse", "injection", "borderline", "cannot", "direct", "declined", "parallel", "multi", "confusable",
            "ask", "single"]
CATEGORY = {"single": "tool_call", "ask": "ask", "declined": "confirm_declined", "multi": "multi_step",
            "parallel": "multi_step", "confusable": "tool_call", "direct": "direct", "cannot": "cannot",
            "refuse": "refuse", "injection": "injection"}
_lock = threading.Lock()


def cache_path(text: str) -> Path:
    return CACHE / (hashlib.sha256(text.encode()).hexdigest()[:24] + ".json")


_by_id: dict[str, Path] = {}


def cached(spec: dict) -> Path | None:
    """The batch's cache file: exact prompt hash, else the newest file for the same batch id (so a prompt tweak
    doesn't throw away finished batches; they keep the prompt version they were made with)."""
    exact = cache_path(prompt(spec))
    if exact.exists():
        return exact
    if not _by_id:
        for f in sorted(CACHE.glob("*.json"), key=lambda f: f.stat().st_mtime):
            _by_id[json.loads(f.read_text(encoding="utf-8"))["spec"]["id"]] = f
    return _by_id.get(spec["id"])


def generate(spec: dict, worker: tuple) -> dict:
    provider, client, model, max_tokens, extra = worker
    text = prompt(spec)
    path = cache_path(text)
    if old := cached(spec):
        return json.loads(old.read_text(encoding="utf-8"))
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": text}], temperature=0.9, max_tokens=max_tokens,
                response_format={"type": "json_object"}, extra_body=extra)
            raw = r.choices[0].message.content
            convs = json.loads(raw)["conversations"]
            rec = {"spec": spec, "provider": provider, "model": model, "conversations": convs}
            path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            return rec
        except Exception as e:  # bad JSON or an API error after the client's own retries
            with _lock:
                print(f"  {spec['id']} attempt {attempt + 1} via {provider}: {type(e).__name__}: {str(e)[:150]}")
            time.sleep(5 * (attempt + 1))
    return {"spec": spec, "provider": provider, "model": model, "conversations": [], "failed": True}


def to_examples(rec: dict) -> list[Example | dict]:
    """Teacher conversations -> Examples. Unparseable ones come back as {"id", "error"} for the validator to count."""
    spec, out = rec["spec"], []
    sys_msg = Message(role="system", content=system_prompt(spec))
    for k, conv in enumerate(rec["conversations"]):
        eid = f"{spec['id']}-{k:02d}"
        try:
            msgs = [Message.model_validate({**m, "content": m.get("content") or ""}) for m in conv["messages"]]
            calls = any(m.tool_calls for m in msgs)
            cat = CATEGORY.get(spec["scenario"]) or ("tool_call" if calls else "direct")
            out.append(Example(id=eid, source="synthetic", category=cat, messages=[sys_msg, *msgs],
                               tools=openai_tools()))
        except Exception as e:
            out.append({"id": eid, "error": f"{type(e).__name__}: {str(e)[:200]}"})
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--limit", type=int, help="generate at most N missing batches")
    ap.add_argument("--providers", default=",".join(p[0] for p in PROVIDERS))
    ap.add_argument("--sample", action="store_true", help="one missing batch per scenario (teacher pilot)")
    a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    specs = pilot(batches()) if a.pilot else batches()
    todo = sorted((s for s in specs if not cached(s)), key=lambda s: PRIORITY.index(s["scenario"]))
    if a.sample:
        todo = list({s["scenario"]: s for s in reversed(todo)}.values())
    todo = todo[: a.limit]
    names = a.providers.split(",")
    workers = [(name, OpenAI(base_url=url, api_key=os.environ[key], max_retries=10, timeout=300), model, mt, extra)
               for name, url, key, model, mt, n, extra in PROVIDERS if name in names and os.getenv(key)
               for _ in range(n)]
    jobs, done = queue.Queue(), [0]
    for s in todo:
        jobs.put(s)

    def work(worker):
        while True:
            try:
                spec = jobs.get_nowait()
            except queue.Empty:
                return
            rec = generate(spec, worker)
            with _lock:
                done[0] += 1
                print(f"[{done[0]}/{len(todo)}] {spec['id']} {len(rec['conversations'])} conversations via "
                      f"{rec['provider']}")

    print(f"{len(specs) - len(todo)} batches cached, generating {len(todo)} with {len(workers)} workers")
    with ThreadPoolExecutor(len(workers)) as pool:
        list(pool.map(work, workers))
    _by_id.clear()
    recs = [json.loads(p.read_text(encoding="utf-8")) for s in specs if (p := cached(s))]
    if a.sample:
        recs = [r for r in recs if r["spec"]["id"] in {s["id"] for s in todo}]
    examples = [e for rec in recs for e in to_examples(rec)]
    out = OUT / ("synthetic_pilot.jsonl" if a.pilot else "synthetic_sample.jsonl" if a.sample else "synthetic.jsonl")
    with out.open("w", encoding="utf-8") as f:
        for e in examples:
            f.write((e.model_dump_json() if isinstance(e, Example) else json.dumps(e)) + "\n")
    print(f"{len(examples)} examples from {len(recs)}/{len(specs)} batches -> {out}")


if __name__ == "__main__":
    main()
