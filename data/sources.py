"""Public datasets -> Examples: NVIDIA When2Call (train_sft) and Salesforce xLAM-60k. Both CC-BY-4.0.

They keep their own tools and get a generic system prompt (not Alfred's), so they teach general tool-use and
when-not-to-call behaviour without teaching Alfred's rules over unrelated tools.
"""

import json
import os
import random

from huggingface_hub import hf_hub_download

from alfred.agent.backends import ROOT  # noqa: F401  (loads .env for HF_TOKEN)
from alfred.contracts.schemas import Example, Message, ToolCall
from eval.score import classify_decision

GENERIC_SYSTEM = "You are a helpful assistant. Call one of the provided functions when it fits the request; " \
                 "otherwise answer directly, ask for missing details, or say you can't."
TYPES = {"str": "string", "string": "string", "int": "integer", "integer": "integer", "float": "number",
         "number": "number", "bool": "boolean", "boolean": "boolean", "list": "array", "array": "array",
         "dict": "object", "object": "object"}


def json_type(t) -> str:
    base = str(t or "string").lower().replace(", optional", "").split("[")[0].strip()
    return TYPES.get(base, "string")


def to_openai_tool(t: dict) -> dict:
    params = t.get("parameters") or {}
    props = params.get("properties", params) if isinstance(params, dict) else {}
    out_props, required = {}, []
    for name, p in props.items():
        if not isinstance(p, dict):
            continue
        out_props[name] = {"type": json_type(p.get("type")), "description": p.get("description", "")}
        optional = "optional" in str(p.get("type", "")) or p.get("default") not in (None, "")
        if not optional:
            required.append(name)
    if isinstance(params, dict) and isinstance(params.get("required"), list):
        required = [r for r in params["required"] if r in out_props]
    return {"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                             "parameters": {"type": "object", "properties": out_props,
                                                            "required": required}}}


def when2call(n: int, seed: int = 3407) -> list[Example]:
    """Ask / can't-answer replies only (the SFT split has no calls); keep those the scorer classifies as intended."""
    path = hf_hub_download("nvidia/When2Call", "train/when2call_train_sft.jsonl", repo_type="dataset")
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    random.Random(seed).shuffle(rows)
    out = []
    for i, r in enumerate(rows):
        reply = r["messages"][-1]["content"]
        decision = classify_decision({"content": reply, "tool_calls": []})
        if decision not in ("ask", "cannot"):
            continue
        tools = [to_openai_tool(json.loads(t)) for t in r["tools"]]
        out.append(Example(id=f"when2call-{i:05d}", source="when2call", category=decision, tools=tools,
                           messages=[Message(role="system", content=GENERIC_SYSTEM),
                                     Message(role="user", content=r["messages"][0]["content"]),
                                     Message(role="assistant", content=reply)]))
        if len(out) >= n:
            break
    return out


def xlam(n: int, seed: int = 3407) -> list[Example]:
    path = hf_hub_download("Salesforce/xlam-function-calling-60k", "xlam_function_calling_60k.json",
                           repo_type="dataset", token=os.getenv("HF_TOKEN"))
    rows = json.load(open(path, encoding="utf-8"))
    random.Random(seed).shuffle(rows)
    out = []
    for r in rows[:n]:
        calls = [ToolCall(name=c["name"], arguments=c.get("arguments") or {}) for c in json.loads(r["answers"])]
        tools = [to_openai_tool(t) for t in json.loads(r["tools"])]
        out.append(Example(id=f"xlam-{r['id']:05d}", source="xlam", tools=tools,
                           category="multi_step" if len(calls) > 1 else "tool_call",
                           messages=[Message(role="system", content=GENERIC_SYSTEM),
                                     Message(role="user", content=r["query"]),
                                     Message(role="assistant", tool_calls=calls)]))
    return out
