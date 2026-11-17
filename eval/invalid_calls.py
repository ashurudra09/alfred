"""How often the model's tool calls fail the loop's validation (track 4D, step D2): unknown tool, arguments that are
not JSON or break the schema, a disabled tool. The loop rejects such a call, tells the model why and allows one
retry (agent/loop.py, FR2); a second failure ends the turn with "I couldn't make a valid tool call".

Reads trajectory files written by the e2e runner or data.onpolicy ({"trajectory": [{"system", "messages"}]}).

  uv run python -m eval.invalid_calls runs/e2e/alfred-2b-v3-q4/hard_b93fc93_*.jsonl
"""

import glob
import json
import sys
from collections import Counter

REJECT = ("Error: Unknown tool", "Error: The arguments were not valid JSON", "Error: Invalid arguments", "Error: Tool '")
GAVE_UP = "I couldn't make a valid tool call"
TEXT_CALL = ("<tool_call>", "<function=", "</parameter>", '{"name":')


def count(rows: list[dict]) -> dict:
    """Assistant messages with calls, how many were rejected, tasks with a reject, tasks that gave up; and why."""
    c, why = Counter(), Counter()
    for r in rows:
        hit = False
        for chat in r["trajectory"]:
            msgs = chat["messages"]
            for i, m in enumerate(msgs):
                if m["role"] == "assistant" and m.get("tool_calls"):
                    c["call messages"] += 1
                    results = [x["content"] for x in msgs[i + 1:i + 1 + len(m["tool_calls"])] if x["role"] == "tool"]
                    bad = [x for x in results if x.startswith(REJECT)]
                    if bad:
                        c["rejected"] += 1
                        hit = True
                        why.update(x.split(":", 2)[1].strip().split(" ")[0] if x.startswith("Error: Tool '")
                                   else x[7:40] for x in bad)
                if m["role"] == "assistant" and (m.get("content") or "").startswith(GAVE_UP):
                    c["gave up"] += 1
                # llama-server's grammar starts at <tool_call>: call syntax written as text escapes it and is never run
                if m["role"] == "assistant" and any(t in (m.get("content") or "") for t in TEXT_CALL):
                    c["call written as text"] += 1
        c["tasks"] += 1
        c["tasks with a reject"] += hit
    return dict(c) | {"why": dict(why)}


def main(patterns: list[str]):
    rows = [json.loads(line) for p in patterns for f in sorted(glob.glob(p))
            for line in open(f, encoding="utf-8") if line.strip()]
    print(json.dumps(count(rows), indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
