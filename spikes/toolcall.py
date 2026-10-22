"""Spike 1a: does qwen3.5:2b with think=false return a structured tool call? 3 tools, then all 25.

Usage: uv run python spikes/toolcall.py
"""

from common import TOOLS, chat

three = [t for t in TOOLS if t["function"]["name"] in ("port_in_use", "disk_usage", "calculate")]
cases = [
    (three, "What's running on port 3000?", "port_in_use"),
    (TOOLS, "What's 18% GST on 34,999?", "calculate"),
    (TOOLS, "find pdfs in downloads with transformer in the name", "search_files"),
    (TOOLS, "What's the capital of France?", None),
]
ok = 0
for tools, user, want in cases:
    calls, content, st = chat(user, tools)
    got = calls[0]["function"]["name"] if calls else None
    ok += got == want
    print(f"[{'OK' if got == want else 'XX'}] {len(tools):2} tools | {user!r} -> "
          f"{calls[0]['function'] if calls else repr(content[:80])} ({st['total']:.1f}s)")
print(f"{ok}/{len(cases)} as expected")
assert any(chat("What's running on port 3000?", three)[0]), "no structured tool_calls returned"
