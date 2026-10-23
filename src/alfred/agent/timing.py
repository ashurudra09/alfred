"""Per-turn timing (FR22, FR23) and the JSONL request log (FR5)."""

import json
import time
from datetime import datetime
from pathlib import Path

from alfred.agent.backends import ROOT

LOGS = ROOT / "logs"


class TurnTimer:
    def __init__(self):
        self.t0 = time.perf_counter()
        self.ttft: float | None = None
        self.tools: list[dict] = []
        self.gen_tokens, self.gen_secs = 0, 0.0

    def llm(self, result):
        """Record one model call (a backends.Result)."""
        if self.ttft is None and result.ttft is not None:
            self.ttft = time.perf_counter() - self.t0 - (result.total - result.ttft)
        if result.completion_tokens:
            self.gen_tokens += result.completion_tokens
            self.gen_secs += max(result.total - (result.ttft or 0), 1e-6)

    def tool(self, name: str, secs: float):
        self.tools.append({"tool": name, "secs": round(secs, 3)})

    def summary(self) -> dict:
        return {"total": round(time.perf_counter() - self.t0, 2), "ttft": self.ttft and round(self.ttft, 2),
                "tools": self.tools, "tok_per_s": round(self.gen_tokens / self.gen_secs, 1) if self.gen_secs else None}


def log_turn(record: dict, logs: Path = LOGS):
    logs.mkdir(exist_ok=True)
    with (logs / f"{datetime.now():%Y-%m-%d}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), **record}, ensure_ascii=False) + "\n")


def format_timing(t: dict) -> str:
    tools = ", ".join(f"{x['tool']} {x['secs']:.1f}s" for x in t["tools"])
    parts = [f"total {t['total']:.1f}s"]
    if t["ttft"] is not None:
        parts.append(f"first token {t['ttft']:.1f}s")
    if tools:
        parts.append(tools)
    if t["tok_per_s"]:
        parts.append(f"{t['tok_per_s']:.0f} tok/s")
    return " · ".join(parts)
