"""One OpenAI-compatible backend for every model: local llama-server, Groq, Cerebras (requirements FR6).

`Backend.stream()` yields events and ends with the parsed result; `Backend.chat()` just returns the result.
Also: `python -m alfred.agent.backends serve [ollama-model-or-gguf]` starts llama-server for the local model.
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

LOCAL_URL = "http://127.0.0.1:8080/v1"
NO_THINK = {"chat_template_kwargs": {"enable_thinking": False}}
BACKENDS = {  # name -> (base_url, key env, model, extra_body, max requests/minute or None)
    "local": (LOCAL_URL, None, "local", NO_THINK, None),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b", {}, 25),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", "gpt-oss-120b", {}, 25),
}


@dataclass
class RawCall:
    name: str
    arguments: dict | None  # None = the model's arguments were not valid JSON
    raw: str = ""


@dataclass
class Result:
    content: str = ""
    tool_calls: list[RawCall] = field(default_factory=list)
    ttft: float | None = None  # seconds to the first content or tool-call token
    total: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cached_tokens: int | None = None
    error: str | None = None


XML_CALL = re.compile(r"<tool_call>\s*<function=([\w.-]+)>(.*?)</function>\s*</tool_call>", re.S)
XML_PARAM = re.compile(r"<parameter=([\w.-]+)>\n?(.*?)\n?</parameter>", re.S)
JSON_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def _value(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return text


def parse_text_calls(content: str) -> tuple[str, list[RawCall]]:
    """Fallback when the server didn't parse the calls: Qwen3.5's XML format, or Qwen2.5-style JSON in <tool_call>."""
    calls = [RawCall(name, {k: _value(v) for k, v in XML_PARAM.findall(body)}, m)
             for m, (name, body) in ((m.group(0), m.groups()) for m in XML_CALL.finditer(content))]
    for m in JSON_CALL.finditer(content):
        obj = _value(m.group(1))
        if isinstance(obj, dict) and "name" in obj:
            calls.append(RawCall(obj["name"], obj.get("arguments") if isinstance(obj.get("arguments"), dict) else None,
                                 m.group(0)))
    if calls:
        content = JSON_CALL.sub("", XML_CALL.sub("", content))
    return content.strip(), calls


def wrap_tool_output(text: str) -> str:
    """Tool results reach the model marked as untrusted data (FR16). Eval, training data and the agent all use this."""
    return f'<tool_output untrusted="true">\n{text}\n</tool_output>'


def openai_messages(messages: list, system: str | None = None) -> list[dict]:
    """contracts.schemas.Message list -> OpenAI chat messages, pairing tool results with call ids in order."""
    out = [{"role": "system", "content": system}] if system else []
    pending, n = [], 0
    for m in messages:
        if m.role == "assistant" and m.tool_calls:
            ids = [f"call_{n + i}" for i in range(len(m.tool_calls))]
            n += len(ids)
            pending += ids
            out.append({"role": "assistant", "content": m.content or "", "tool_calls": [
                {"id": i, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                for i, c in zip(ids, m.tool_calls)]})
        elif m.role == "tool":
            out.append({"role": "tool", "tool_call_id": pending.pop(0) if pending else f"call_{n}",
                        "content": wrap_tool_output(m.content)})
        else:
            out.append({"role": m.role, "content": m.content})
    return out


class Backend:
    def __init__(self, name: str = "local"):
        url, key_env, self.model, self.extra_body, rpm = BACKENDS[name]
        self.name = name
        self.client = OpenAI(base_url=url, api_key=os.getenv(key_env, "") if key_env else "none", max_retries=8,
                             timeout=600)
        self.min_gap = 60 / rpm if rpm else 0.0
        self._last = 0.0

    def stream(self, messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.0):
        """Yields ("token", text) while generating, then ("done", Result)."""
        if self.min_gap:  # stay under free-tier rate limits
            time.sleep(max(0.0, self._last + self.min_gap - time.monotonic()))
            self._last = time.monotonic()
        res, parts, t0 = Result(), {}, time.perf_counter()
        try:
            stream = self.client.chat.completions.create(
                model=self.model, messages=messages, tools=tools or None, temperature=temperature, stream=True,
                stream_options={"include_usage": True}, extra_body=self.extra_body)
            for chunk in stream:
                if chunk.usage:
                    res.prompt_tokens, res.completion_tokens = chunk.usage.prompt_tokens, chunk.usage.completion_tokens
                    details = getattr(chunk.usage, "prompt_tokens_details", None)
                    res.cached_tokens = getattr(details, "cached_tokens", None)
                timings = getattr(chunk, "timings", None)  # llama-server extension
                if timings:
                    res.cached_tokens = timings.get("cache_n", res.cached_tokens)
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if res.ttft is None and (delta.content or delta.tool_calls):
                    res.ttft = time.perf_counter() - t0
                if delta.content:
                    res.content += delta.content
                    yield "token", delta.content
                for tc in delta.tool_calls or []:
                    p = parts.setdefault(tc.index, {"name": "", "args": ""})
                    p["name"] += (tc.function and tc.function.name) or ""
                    p["args"] += (tc.function and tc.function.arguments) or ""
        except Exception as e:  # report, don't crash a 250-item eval run
            res.error = f"{type(e).__name__}: {e}"[:500]
        for p in parts.values():
            args = _value(p["args"] or "{}")
            res.tool_calls.append(RawCall(p["name"], args if isinstance(args, dict) else None, p["args"]))
        if not res.tool_calls and "<tool_call>" in res.content:
            res.content, res.tool_calls = parse_text_calls(res.content)
        res.total = time.perf_counter() - t0
        yield "done", res

    def chat(self, messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.0) -> Result:
        for kind, value in self.stream(messages, tools, temperature):
            if kind == "done":
                return value


def gguf_path(model: str) -> str:
    """A .gguf path as-is, or the GGUF blob behind an Ollama model name (e.g. qwen3.5:2b, Q8_0)."""
    if model.endswith(".gguf"):
        return model
    out = subprocess.run(["ollama", "show", model, "--modelfile"], capture_output=True, text=True, check=True).stdout
    return next(line.split(" ", 1)[1].strip() for line in out.splitlines() if line.startswith("FROM "))


def serve(model: str = "qwen3.5:2b", port: int = 8080) -> subprocess.Popen:
    """Start llama-server (winget ggml.llamacpp) with prefix-cache checkpoints; see decisions.md (Phase 1)."""
    slots = ROOT / "runs" / "slots"
    slots.mkdir(parents=True, exist_ok=True)
    cmd = ["llama-server", "-m", gguf_path(model), "-c", "8192", "-t", "4", "--port", str(port),
           "--slot-save-path", str(slots)]
    return subprocess.Popen(cmd)


if __name__ == "__main__":
    if sys.argv[1:2] == ["serve"]:
        serve(*sys.argv[2:3]).wait()
    else:
        print("usage: python -m alfred.agent.backends serve [ollama-model | path.gguf]")
